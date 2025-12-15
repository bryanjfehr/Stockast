# build_chart_dataset.py
import os
import json
import numpy as np
from tqdm import tqdm
from argdantic import ArgParser
from pydantic import BaseModel

from common import PuzzleDatasetMetadata, dihedral_transform  # Reuse from HRM repo

cli = ArgParser()

class DataProcessConfig(BaseModel):
    input_dir: str = "hrm_1000_grids"  # Your generated dir
    output_dir: str = "data/chart-60x60-1k"
    train_ratio: float = 0.8
    aug: bool = True  # Dihedral + flips

def flip_grid(grid):
    """Horizontal flip for charts (time reverse simulation)."""
    return np.fliplr(grid)

def convert_dataset(config: DataProcessConfig):
    # Load all grids + generate labels (next up/down)
    all_files = [f for f in os.listdir(config.input_dir) if f.endswith('_grids.npy')]
    all_grids = []
    all_labels = []  # Binary: 1 up, 0 down (generate placeholder or from klines DB)
    
    for file in all_files:
        grids = np.load(os.path.join(config.input_dir, file))
        all_grids.extend(grids)
        # Placeholder labels (random for demo; replace with real next-candle from DB)
        labels = np.random.randint(0, 2, size=len(grids))  # TODO: Load real from klines next close
        all_labels.extend(labels)
    
    all_grids = np.array(all_grids)  # (N, 60, 60)
    all_labels = np.array(all_labels)
    
    # Split train/test
    split_idx = int(len(all_grids) * config.train_ratio)
    train_grids, test_grids = all_grids[:split_idx], all_grids[split_idx:]
    train_labels, test_labels = all_labels[:split_idx], all_labels[split_idx:]
    
    for split_name, grids, labels in [("train", train_grids, train_labels), ("test", test_grids, test_labels)]:
        results = {"inputs": [], "labels": [], "puzzle_indices": [0], "group_indices": [0], "puzzle_identifiers": []}
        example_id = 0
        puzzle_id = 0
        
        for grid, label in tqdm(zip(grids, labels), total=len(grids), desc=f"Processing {split_name}"):
            # Augmentations
            augs = 8 if (split_name == "train" and config.aug) else 1
            for aug_idx in range(augs):
                aug_grid = dihedral_transform(grid, aug_idx)
                if random.random() < 0.5 and config.aug:  # Extra flip
                    aug_grid = flip_grid(aug_grid)
                
                results["inputs"].append(aug_grid.flatten())
                results["labels"].append(label)  # Broadcast label (or predict next grid section)
                example_id += 1
                puzzle_id += 1
                results["puzzle_indices"].append(example_id)
                results["puzzle_identifiers"].append(0)  # Single task
            
            results["group_indices"].append(puzzle_id)
        
        # To numpy (uint8 for grids, int for labels)
        results["inputs"] = np.array(results["inputs"], dtype=np.uint8)
        results["labels"] = np.array(results["labels"], dtype=np.int32)
        results["group_indices"] = np.array(results["group_indices"], dtype=np.int32)
        results["puzzle_indices"] = np.array(results["puzzle_indices"], dtype=np.int32)
        results["puzzle_identifiers"] = np.array(results["puzzle_identifiers"], dtype=np.int32)
        
        # Metadata
        metadata = PuzzleDatasetMetadata(
            seq_len=3600,  # 60x60
            vocab_size=11,  # 0-9 + PAD
            pad_id=0,
            ignore_label_id=-100,  # For classification, use cross-entropy
            blank_identifier_id=0,
            num_puzzle_identifiers=1,
            total_groups=len(results["group_indices"]) - 1,
            mean_puzzle_examples=1,
            sets=["all"]
        )
        
        save_dir = os.path.join(config.output_dir, split_name)
        os.makedirs(save_dir, exist_ok=True)
        
        with open(os.path.join(save_dir, "dataset.json"), "w") as f:
            json.dump(metadata.model_dump(), f)
        
        for k, v in results.items():
            np.save(os.path.join(save_dir, f"all__{k}.npy"), v)
        
        logging.info(f"Saved {split_name} dataset: {len(grids)} base samples")

@cli.command()
def preprocess_data(config: DataProcessConfig = DataProcessConfig()):
    convert_dataset(config)

if __name__ == "__main__":
    cli()