import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def train_hrm(*args, **kwargs):
    """
    This training function is deprecated.
    The primary training entry point is now the more advanced `ml/HRM/pretrain.py` script,
    which is orchestrated by `scripts/build_and_train.py`.
    """
    error_message = "The `train_hrm` function is deprecated. Please run `python scripts/build_and_train.py` to train the model."
    logging.error(error_message)
    raise NotImplementedError(error_message)