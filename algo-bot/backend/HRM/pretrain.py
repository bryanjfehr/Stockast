from typing import Optional, Any, Sequence, List
from dataclasses import dataclass
import os
import math
import yaml
import shutil
import signal
import sys

# Global flag to prevent re-entry into the signal handler
_SHUTDOWN_CALLED = False
# Global flag to indicate that a graceful save should be performed by the main loop
_SHOULD_SAVE_ON_EXIT = False

import torch
import torch.distributed as dist
from torch import nn
from torch.utils.data import DataLoader

import tqdm
import wandb
import coolname
import hydra
import pydantic
from omegaconf import DictConfig

from puzzle_dataset import PuzzleDataset, PuzzleDatasetConfig, PuzzleDatasetMetadata
from utils.functions import load_model_class, get_model_source_path
from models.sparse_embedding import CastedSparseEmbeddingSignSGD_Distributed


class LossConfig(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra='allow')
    
    name: str


class ArchConfig(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra='allow')

    name: str
    loss: LossConfig
    precision: Optional[str] = None
    gradient_accumulation_steps: int = 1


class PretrainConfig(pydantic.BaseModel):
    # Config
    arch: ArchConfig
    # Data
    data_path: str

    # Hyperparams
    global_batch_size: int
    epochs: int

    lr: float
    lr_min_ratio: float
    lr_warmup_steps: int
    lr_scheduler: str = "cosine"

    weight_decay: float
    beta1: float
    beta2: float

    # Puzzle embedding
    puzzle_emb_lr: float
    puzzle_emb_weight_decay: float

    # Names
    project_name: Optional[str] = None
    run_name: Optional[str] = None
    checkpoint_path: Optional[str] = None

    # Extras
    resume: bool = False
    seed: int = 0
    checkpoint_every_eval: bool = False
    eval_interval: Optional[int] = None
    eval_save_outputs: List[str] = []


@dataclass
class TrainState:
    model: nn.Module
    optimizers: Sequence[torch.optim.Optimizer]
    optimizer_lrs: Sequence[float]
    carry: Any

    step: int
    total_steps: int


def create_dataloader(config: PretrainConfig, split: str, rank: int, world_size: int, **kwargs):
    dataset = PuzzleDataset(PuzzleDatasetConfig(
        seed=config.seed,

        dataset_path=config.data_path,

        rank=rank,
        num_replicas=world_size,
        
        **kwargs
    ), split=split)
    dataloader = DataLoader(
        dataset,
        batch_size=None,

        num_workers=1,
        prefetch_factor=8,

        pin_memory=True,
        persistent_workers=True
    )
    return dataloader, dataset.metadata


def create_model(config: PretrainConfig, train_metadata: PuzzleDatasetMetadata, world_size: int):
    model_cfg = dict(
        **config.arch.__pydantic_extra__,  # type: ignore

        batch_size=config.global_batch_size // world_size,

        vocab_size=train_metadata.vocab_size,
        seq_len=train_metadata.seq_len,
        num_puzzle_identifiers=train_metadata.num_puzzle_identifiers,
        causal=False  # Non-autoregressive
    )

    # Instantiate model with loss head
    model_cls = load_model_class(config.arch.name)
    loss_head_cls = load_model_class(config.arch.loss.name)

    with torch.device("cuda"):
        model: nn.Module = model_cls(model_cfg)
        model = loss_head_cls(model, **config.arch.loss.__pydantic_extra__)  # type: ignore
        if "DISABLE_COMPILE" not in os.environ:
            model = torch.compile(model, dynamic=False)  # type: ignore

        # Broadcast parameters from rank 0
        if world_size > 1:
            with torch.no_grad():
                for param in list(model.parameters()) + list(model.buffers()):
                    dist.broadcast(param, src=0)

    # Optimizers and lr
    optimizers = [
        CastedSparseEmbeddingSignSGD_Distributed(
            model.model.puzzle_emb.buffers(),  # type: ignore
            
            lr=0,  # Needs to be set by scheduler
            weight_decay=config.puzzle_emb_weight_decay,

            world_size=world_size
        ),
        torch.optim.AdamW(
            model.parameters(),

            lr=0,  # Needs to be set by scheduler
            weight_decay=config.weight_decay,
            betas=(config.beta1, config.beta2)
        )
    ]
    optimizer_lrs = [
        config.puzzle_emb_lr,
        config.lr
    ]

    return model, optimizers, optimizer_lrs


def cosine_schedule_with_warmup_lr_lambda(
    current_step: int, *, base_lr: float, num_warmup_steps: int, num_training_steps: int, min_ratio: float = 0.0, num_cycles: float = 0.5
):
    if current_step < num_warmup_steps:
        return base_lr * float(current_step) / float(max(1, num_warmup_steps))

    progress = float(current_step - num_warmup_steps) / float(max(1, num_training_steps - num_warmup_steps))
    return base_lr * (min_ratio + max(0.0, (1 - min_ratio) * 0.5 * (1.0 + math.cos(math.pi * float(num_cycles) * 2.0 * progress))))


def init_train_state(config: PretrainConfig, train_metadata: PuzzleDatasetMetadata, world_size: int):
    # Estimated total training steps
    total_steps = int(config.epochs * train_metadata.total_groups * train_metadata.mean_puzzle_examples / config.global_batch_size)

    # Model
    model, optimizers, optimizer_lrs = create_model(config, train_metadata, world_size=world_size)

    return TrainState(
        step=0,
        total_steps=total_steps,

        model=model,
        optimizers=optimizers,
        optimizer_lrs=optimizer_lrs,
        carry=None
    )


def perform_graceful_save(config: PretrainConfig, train_state: TrainState, train_loader: DataLoader, resume_file_path: str, RANK: int, WORLD_SIZE: int, wandb_run_id: Optional[str]):
    """
    Performs the actual checkpoint saving and cleanup.
    This should be called from the main loop, not directly from a signal handler.
    """
    print(f"\n[Rank {RANK}] Initiating graceful save from main loop.")

    if RANK == 0 and config.checkpoint_path is not None:
        os.makedirs(config.checkpoint_path, exist_ok=True)
        resume_pt_path_for_save = os.path.join(config.checkpoint_path, "resume.pt")
        print(f"[Rank 0] Saving resume checkpoint to {resume_pt_path_for_save}")
        
        # Create CPU-based copies of the state for saving. This is a safer pattern than
        # modifying the live, GPU-based training state in-place, which can lead to
        # unexpected performance degradation on resume, especially with torch.compile.
        model_state_dict_cpu = {k: v.cpu() for k, v in train_state.model.state_dict().items()}
        
        carry_cpu = None
        if train_state.carry is not None and isinstance(train_state.carry, dict):
            carry_cpu = {k: v.cpu() for k, v in train_state.carry.items()}
        else:
            carry_cpu = train_state.carry # Fallback for non-dict or None carry

        state_to_save = {
            'step': train_state.step,
            'carry': carry_cpu,
            'model_state_dict': model_state_dict_cpu,
            'optimizers_state_dict': [opt.state_dict() for opt in train_state.optimizers],
            'puzzle_dataset_iters': train_loader.dataset._iters, # type: ignore
            'wandb_run_id': wandb_run_id
        }
        torch.save(state_to_save, resume_pt_path_for_save)

        with open(resume_file_path, "w") as f:
            f.write(config.checkpoint_path)
        
        print("[Rank 0] Resume state saved.")
    
    if WORLD_SIZE > 1: dist.barrier()
    if wandb.run: wandb.finish()
    if dist.is_initialized(): dist.destroy_process_group()
    sys.exit(0) # Exit after saving and cleanup

def save_train_state(config: PretrainConfig, train_state: TrainState):
    # FIXME: Only saved model.
    if config.checkpoint_path is None:
        return

    os.makedirs(config.checkpoint_path, exist_ok=True)
    torch.save(train_state.model.state_dict(), os.path.join(config.checkpoint_path, f"step_{train_state.step}"))


def compute_lr(base_lr: float, config: PretrainConfig, train_state: TrainState):
    return cosine_schedule_with_warmup_lr_lambda(
        current_step=train_state.step,
        base_lr=base_lr,
        num_warmup_steps=round(config.lr_warmup_steps),
        num_training_steps=train_state.total_steps,
        min_ratio=config.lr_min_ratio
    )


def train_batch(config: PretrainConfig, train_state: TrainState, batch: Any, global_batch_size: int, rank: int, world_size: int):
    train_state.step += 1
    if train_state.step > train_state.total_steps:  # At most train_total_steps
        return

    # To device
    batch = {k: v.cuda() for k, v in batch.items()}

    # The loss function expects labels to be broadcastable to the logits shape.
    # This unsqueezes the labels tensor to make it compatible.
    if "labels" in batch and batch["labels"].dim() == 1:
        batch["labels"] = batch["labels"].unsqueeze(-1)

    # Init carry if it is None
    if train_state.carry is None:
        with torch.device("cuda"):
            train_state.carry = train_state.model.initial_carry(batch)  # type: ignore

    # Forward
    train_state.carry, loss, metrics, _, _ = train_state.model(carry=train_state.carry, batch=batch, return_keys=[])

    ((1 / global_batch_size) * loss).backward()

    # Allreduce
    if world_size > 1:
        for param in train_state.model.parameters():
            if param.grad is not None:
                dist.all_reduce(param.grad)
            
    # Apply optimizer
    lr_this_step = None    
    for optim, base_lr in zip(train_state.optimizers, train_state.optimizer_lrs):
        lr_this_step = compute_lr(base_lr, config, train_state)

        for param_group in optim.param_groups:
            param_group['lr'] = lr_this_step
            
        optim.step()
        optim.zero_grad()

    # Reduce metrics
    if len(metrics):
        assert not any(v.requires_grad for v in metrics.values())

        metric_keys = list(sorted(metrics.keys()))  # Sort keys to guarantee all processes use the same order.
        # Reduce and reconstruct
        metric_values = torch.stack([metrics[k] for k in metric_keys])
        if world_size > 1:
            dist.reduce(metric_values, dst=0)

        if rank == 0:
            metric_values = metric_values.cpu().numpy()
            reduced_metrics = {k: metric_values[i] for i, k in enumerate(metric_keys)}
            
            # Postprocess
            count = max(reduced_metrics["count"], 1)  # Avoid NaNs
            reduced_metrics = {f"train/{k}": v / (global_batch_size if k.endswith("loss") else count) for k, v in reduced_metrics.items()}

            reduced_metrics["train/lr"] = lr_this_step
            return reduced_metrics


def evaluate(config: PretrainConfig, train_state: TrainState, eval_loader: torch.utils.data.DataLoader, eval_metadata: PuzzleDatasetMetadata, rank: int, world_size: int):
    with torch.inference_mode():
        set_ids = {k: idx for idx, k in enumerate(eval_metadata.sets)}
        
        all_preds = {}

        metric_keys = []
        metric_values = None
        metric_global_batch_size = [0 for _ in range(len(set_ids))]
        
        carry = None
        for set_name, batch, global_batch_size in eval_loader:
            # To device
            batch = {k: v.cuda() for k, v in batch.items()}

            # The loss function expects labels to be broadcastable to the logits shape.
            # This unsqueezes the labels tensor to make it compatible.
            if "labels" in batch and batch["labels"].dim() == 1:
                batch["labels"] = batch["labels"].unsqueeze(-1)

            with torch.device("cuda"):
                carry = train_state.model.initial_carry(batch)  # type: ignore

            # Forward
            while True:
                carry, _, metrics, preds, all_finish = train_state.model(carry=carry, batch=batch, return_keys=config.eval_save_outputs)
                
                if all_finish:
                    break

            for collection in (batch, preds):
                for k, v in collection.items():
                    if k in config.eval_save_outputs:
                        all_preds.setdefault(k, [])
                        all_preds[k].append(v.cpu())  # Move to CPU for saving GPU memory
                        
            del carry, preds, batch, all_finish

            # Aggregate
            set_id = set_ids[set_name]
            
            if metric_values is None:
                metric_keys = list(sorted(metrics.keys()))  # Sort keys to guarantee all processes use the same order.
                metric_values = torch.zeros((len(set_ids), len(metrics.values())), dtype=torch.float32, device="cuda")
                
            metric_values[set_id] += torch.stack([metrics[k] for k in metric_keys])
            metric_global_batch_size[set_id] += global_batch_size

        if len(all_preds) and config.checkpoint_path is not None:
            all_preds = {k: torch.cat(v, dim=0) for k, v in all_preds.items()}

            os.makedirs(config.checkpoint_path, exist_ok=True)
            torch.save(all_preds, os.path.join(config.checkpoint_path, f"step_{train_state.step}_all_preds.{rank}"))

        # Logging
        # Reduce to rank 0
        if metric_values is not None:
            if world_size > 1:
                dist.reduce(metric_values, dst=0)
            
            if rank == 0:
                reduced_metrics = metric_values.cpu().numpy()
                reduced_metrics = {set_name: {metric_name: reduced_metrics[set_id, metric_id] for metric_id, metric_name in enumerate(metric_keys)}
                                   for set_id, set_name in enumerate(set_ids)}
                
                # Postprocess
                for set_name, metrics in reduced_metrics.items():
                    count = metrics.pop("count")
                    reduced_metrics[set_name] = {k: v / count for k, v in metrics.items()}

                return reduced_metrics


def save_code_and_config(config: PretrainConfig):
    if config.checkpoint_path is None or wandb.run is None:
        return

    os.makedirs(config.checkpoint_path, exist_ok=True)

    # Copy code
    code_list = [
        get_model_source_path(config.arch.name),
        get_model_source_path(config.arch.loss.name)
    ]
    for code_file in code_list:
        if code_file is not None:
            code_name = os.path.basename(code_file)

            shutil.copy(code_file, os.path.join(config.checkpoint_path, code_name))

    # Dump config as yaml
    config_file = os.path.join(config.checkpoint_path, "all_config.yaml")
    with open(config_file, "wt") as f:
        yaml.dump(config.model_dump(), f)

    # Log code
    wandb.run.log_code(config.checkpoint_path)


def load_synced_config(hydra_config: DictConfig, rank: int, world_size: int) -> PretrainConfig:
    objects = [None]
    if rank == 0:
        config = PretrainConfig(**hydra_config)  # type: ignore


        # Naming
        if config.project_name is None:
            config.project_name = f"{os.path.basename(config.data_path).capitalize()} ACT-torch"
        if config.run_name is None:
            config.run_name = f"{config.arch.name.split('@')[-1]} {coolname.generate_slug(2)}"
        if config.checkpoint_path is None:
            config.checkpoint_path = os.path.join("checkpoints", config.project_name, config.run_name)

        objects = [config]

    if world_size > 1:
        dist.broadcast_object_list(objects, src=0)

    return objects[0]  # type: ignore


@hydra.main(config_path="config", config_name="cfg_pretrain", version_base=None)
def launch(hydra_config: DictConfig):
    RANK = 0
    WORLD_SIZE = 1

    # Initialize distributed training if in distributed environment (e.g. torchrun)
    if "LOCAL_RANK" in os.environ:
        # Initialize distributed, default device and dtype
        dist.init_process_group(backend="nccl")

        RANK = dist.get_rank()
        WORLD_SIZE = dist.get_world_size()

        torch.cuda.set_device(int(os.environ["LOCAL_RANK"]))

    # Load sync'ed config
    config = load_synced_config(hydra_config, rank=RANK, world_size=WORLD_SIZE)

    # Seed RNGs to ensure consistency
    torch.random.manual_seed(config.seed + RANK)

    # Dataset
    train_epochs_per_iter = config.eval_interval if config.eval_interval is not None else config.epochs
    total_iters = config.epochs // train_epochs_per_iter

    assert config.epochs % train_epochs_per_iter == 0, "Eval interval must be a divisor of total epochs."

    train_loader, train_metadata = create_dataloader(config, "train", rank=RANK, world_size=WORLD_SIZE, test_set_mode=False, epochs_per_iter=train_epochs_per_iter, global_batch_size=config.global_batch_size)
    eval_loader,  eval_metadata  = create_dataloader(config, "test", test_set_mode=True, epochs_per_iter=1, global_batch_size=config.global_batch_size, rank=RANK, world_size=WORLD_SIZE)

    # Train state
    train_state = init_train_state(config, train_metadata, world_size=WORLD_SIZE)

    # Resume logic
    wandb_run_id = None
    resume_file_path = os.path.join(config.data_path, ".resume")
    resume_info = {'should_resume': False, 'checkpoint_dir': None}

    if RANK == 0 and config.resume:
        if os.path.exists(resume_file_path):
            resume_info['should_resume'] = True
            with open(resume_file_path, "r") as f:
                resume_checkpoint_dir = f.read().strip()
            resume_info['checkpoint_dir'] = resume_checkpoint_dir
        else:
            print("`resume=True` but no resume file found. Starting new training.")

    if WORLD_SIZE > 1:
        broadcast_list = [resume_info]
        dist.broadcast_object_list(broadcast_list, src=0)
        resume_info = broadcast_list[0]
    
    if resume_info['should_resume']:
        resume_checkpoint_dir = resume_info['checkpoint_dir']
        resume_pt_path = os.path.join(resume_checkpoint_dir, "resume.pt")
        
        if os.path.exists(resume_pt_path):
            print(f"[Rank {RANK}] Loading resume checkpoint from {resume_pt_path}")
            
            map_location = f'cuda:{RANK}' if torch.cuda.is_available() else 'cpu'
            # In PyTorch >= 2.6, weights_only defaults to True for security.
            # Since we are saving custom objects (like the 'carry' state),
            # we must set weights_only=False to allow unpickling of these objects.
            # This is safe as we are loading a checkpoint we created ourselves.
            checkpoint = torch.load(resume_pt_path, map_location=map_location, weights_only=False)
            
            try:
                train_state.model.load_state_dict(checkpoint['model_state_dict'])
            except RuntimeError:
                # Handle torch.compile wrapper
                print(f"[Rank {RANK}] Failed to load state_dict directly, trying to unwrap compiled model.")
                train_state.model.load_state_dict({k.removeprefix("_orig_mod."): v for k, v in checkpoint['model_state_dict'].items()})

            for opt, state_dict in zip(train_state.optimizers, checkpoint['optimizers_state_dict']):
                opt.load_state_dict(state_dict)
            
            train_state.step = checkpoint['step']
            train_state.carry = checkpoint['carry']
            if train_state.carry is not None:
                # Move carry to current device. Handle both dict and object cases.
                if isinstance(train_state.carry, dict):
                    train_state.carry = {k: v.to(map_location, non_blocking=True) for k, v in train_state.carry.items()}
                # Handle generic objects that might contain tensors
                elif hasattr(train_state.carry, '__dict__'):
                    for attr, value in vars(train_state.carry).items():
                        if isinstance(value, torch.Tensor):
                            setattr(train_state.carry, attr, value.to(map_location, non_blocking=True))
            train_loader.dataset._iters = checkpoint['puzzle_dataset_iters']
            wandb_run_id = checkpoint.get('wandb_run_id')
            
            config.checkpoint_path = resume_checkpoint_dir
            
            if RANK == 0:
                os.remove(resume_file_path)
                print("[Rank 0] Resume state loaded. Removed resume file.")
        else:
            if RANK == 0:
                print(f"[Rank 0] Resume file found, but checkpoint {resume_pt_path} does not exist. Starting new training.")
                os.remove(resume_file_path) # remove stale resume file

    # Signal handler for graceful shutdown
    def graceful_shutdown_handler(signum, frame):
        global _SHUTDOWN_CALLED
        global _SHOULD_SAVE_ON_EXIT # Declare global for assignment
        if _SHUTDOWN_CALLED:
            return
        _SHUTDOWN_CALLED = True
        _SHOULD_SAVE_ON_EXIT = True # Set the flag for the main loop

        print(f"\n[Rank {RANK}] Caught signal {signum}. Setting save flag. Shutdown will occur on next iteration.")
        # Do not exit here. Let the main loop handle the shutdown on the next iteration.

    signal.signal(signal.SIGINT, graceful_shutdown_handler)
    signal.signal(signal.SIGTERM, graceful_shutdown_handler)

    # Progress bar and logger
    progress_bar = None
    if RANK == 0:
        progress_bar = tqdm.tqdm(total=train_state.total_steps, initial=train_state.step)

        wandb.init(project=config.project_name, name=config.run_name, config=config.model_dump(), settings=wandb.Settings(_disable_stats=True), resume="allow" if wandb_run_id else None, id=wandb_run_id)  # type: ignore
        wandb.log({"num_params": sum(x.numel() for x in train_state.model.parameters())}, step=0)
        save_code_and_config(config)

    # Training Loop
    for _iter_id in range(total_iters):
        print (f"[Rank {RANK}, World Size {WORLD_SIZE}]: Epoch {_iter_id * train_epochs_per_iter}")

        ############ Train Iter
        if _SHOULD_SAVE_ON_EXIT:
            # Check before starting a new iteration/epoch
            perform_graceful_save(config, train_state, train_loader, resume_file_path, RANK, WORLD_SIZE, wandb_run_id)

        train_state.model.train()
        for set_name, batch, global_batch_size in train_loader:
            metrics = train_batch(config, train_state, batch, global_batch_size, rank=RANK, world_size=WORLD_SIZE)

            if RANK == 0 and metrics is not None:
                wandb.log(metrics, step=train_state.step)
                progress_bar.update(train_state.step - progress_bar.n)  # type: ignore
            
            # Check after each batch
            if _SHOULD_SAVE_ON_EXIT:
                perform_graceful_save(config, train_state, train_loader, resume_file_path, RANK, WORLD_SIZE, wandb_run_id)

        ############ Evaluation
        train_state.model.eval()
        metrics = evaluate(config, train_state, eval_loader, eval_metadata, rank=RANK, world_size=WORLD_SIZE)

        if RANK == 0 and metrics is not None:
            wandb.log(metrics, step=train_state.step)
            
        ############ Checkpointing
        if RANK == 0 and (config.checkpoint_every_eval or (_iter_id == total_iters - 1)):
            save_train_state(config, train_state)

if __name__ == "__main__":
    launch()
