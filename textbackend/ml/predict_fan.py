import torch
import pandas as pd
import numpy as np
from typing import Literal, TYPE_CHECKING

# Assuming data_sampler is in the same `ml` package.
# These functions are expected to be in `ml/data_sampler.py`.
try:
    from .data_sampler import flatten_to_matrix_sequence, flatten_to_polynomial_sequence
except ImportError:
    # Fallback for running as a script
    from data_sampler import flatten_to_matrix_sequence, flatten_to_polynomial_sequence

if TYPE_CHECKING:
    # This helps type checkers understand the model argument
    from torch.nn import Module as TorchModule

def feed_to_hrm_flattened(
    grid: torch.Tensor,
    model: "TorchModule",
    flatten_mode: Literal['matrix', 'polynomial'] = 'matrix',
    horizon_len: int = 24
) -> pd.DataFrame:
    """
    Embeds/forwards a grid through a flattened HRM model and reconstructs the future slice into a fan DataFrame.

    This function takes a data grid, flattens it into a 1D sequence, feeds it to the provided
    HRM model, and processes the model's output to generate a DataFrame representing a fan chart
    of predictions (median, 5th percentile, and 95th percentile).

    This function is designed to work with 4D grid tensors (T, S, H, A) as produced by `build_4d_from_histories`,
    which are built from underlying data including RGB signals. It can also be adapted for simpler tensor
    formats like the (batch, seq_len, features) used for training, provided the `flatten_mode` logic
    is appropriate for that shape.

    Args:
        grid (torch.Tensor): The input data grid. For 'polynomial' and 'matrix' modes based on
                             `data_sampler`, this is expected to be a 4D tensor of shape (T, S, H, A).
                             The future part of the tensor (the last `horizon_len` steps) should be NaN.
        model (torch.nn.Module): The trained HRM model. The model is expected to take a 1D tensor
                                 and output a 2D tensor of shape (horizon_len, num_samples)
                                 representing the predicted distribution for a single signal.
        flatten_mode (Literal['matrix', 'polynomial']): The method to use for flattening the grid.
                                                       'matrix' for row-major flattening,
                                                       'polynomial' for Legendre polynomial coefficient fitting.
        horizon_len (int): The number of future time steps the model is expected to predict.

    Returns:
        pd.DataFrame: A DataFrame with columns ['median', 'low_5', 'high_95'], where each row
                      corresponds to a time step in the prediction horizon.
    """
    if grid.dim() == 4:
        lookback_len = grid.shape[0] - horizon_len
        if lookback_len < 0:
            raise ValueError("Grid length is smaller than horizon_len. No data available for prediction.")
        
        # 1. Flatten the grid into a 1D sequence
        if flatten_mode == 'matrix':
            # Flatten only the valid (lookback) part of the grid.
            valid_grid = grid[:lookback_len]
            sequence = flatten_to_matrix_sequence(valid_grid, mode='row_major')
        elif flatten_mode == 'polynomial':
            # The polynomial fitter can handle NaNs, so we can pass the whole grid.
            sequence = flatten_to_polynomial_sequence(grid, degree=3)
        else:
            raise ValueError(f"Unsupported flatten_mode for 4D grid: {flatten_mode}")
    
    elif grid.dim() == 3: # Support for (batch, seq_len, features)
        # Assuming batch size is 1 for prediction
        if grid.shape[0] != 1:
            raise ValueError(f"For 3D tensors, batch size must be 1 for prediction, but got {grid.shape[0]}")
        # Simple flatten for now, can be made more sophisticated
        sequence = grid.flatten()
    
    else:
        raise ValueError(f"Unsupported grid dimension: {grid.dim()}. Expected 3D or 4D tensor.")


    # 2. Feed the sequence to the HRM model
    model.eval()
    with torch.no_grad():
        predicted_distribution = model(sequence)

    # 3. Reconstruct the future slice into a fan DataFrame
    if not isinstance(predicted_distribution, torch.Tensor) or predicted_distribution.dim() != 2:
        raise ValueError(f"Model output must be a 2D tensor (horizon_len, num_samples), but got shape: {predicted_distribution.shape}")

    if predicted_distribution.shape[0] != horizon_len:
        raise ValueError(f"Model output length ({predicted_distribution.shape[0]}) does not match horizon_len ({horizon_len})")

    # Calculate percentiles across the samples dimension (dim=1)
    median = torch.quantile(predicted_distribution, 0.5, dim=1)
    low_5 = torch.quantile(predicted_distribution, 0.05, dim=1)
    high_95 = torch.quantile(predicted_distribution, 0.95, dim=1)

    fan_df = pd.DataFrame({
        'median': median.numpy(),
        'low_5': low_5.numpy(),
        'high_95': high_95.numpy(),
    })

    return fan_df

if __name__ == '__main__':
    # This block demonstrates how to use the function with mock data and a mock model.

    # 1. Define a mock HRM model for demonstration
    class MockHRM(torch.nn.Module):
        def __init__(self, horizon_len=24, num_samples=100):
            super().__init__()
            self.horizon_len = horizon_len
            self.num_samples = num_samples
            # Dummy layer; a real model would be more complex and not depend on input size this way
            self.fc = torch.nn.Linear(1, self.horizon_len * self.num_samples)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            # A real model would perform complex computations.
            # Here, we just generate a plausible-looking output distribution.
            # We'll ignore the input `x` and return a tensor of the correct shape.
            
            # Simulate a random walk for the median
            base_prediction = torch.randn(self.horizon_len).cumsum(0) * 0.1
            
            # Add noise to create a distribution of samples
            noise = torch.randn(self.horizon_len, self.num_samples) * 0.5
            
            # Shape: (horizon_len, num_samples)
            return base_prediction.unsqueeze(1) + noise

    # 2. Create mock input data
    
    # --- Example with a 4D grid ---
    print("--- Testing with 4D Grid ---")
    T, S, H, A = 84, 8, 3, 10  # Timesteps, Signals, Hierarchy, Assets
    lookback, horizon = 60, 24
    
    mock_grid_4d = torch.randn(T, S, H, A)
    # Mask the future part with NaNs, as it would be in a real scenario
    mock_grid_4d[lookback:] = float('nan')
    
    # 3. Instantiate model and run prediction
    mock_model = MockHRM(horizon_len=horizon)
    
    try:
        fan_df_4d = feed_to_hrm_flattened(
            grid=mock_grid_4d,
            model=mock_model,
            flatten_mode='polynomial', # or 'matrix'
            horizon_len=horizon
        )
        print("Successfully generated fan DataFrame from 4D grid:")
        print(fan_df_4d.head())
    except Exception as e:
        print(f"An error occurred during 4D grid test: {e}")


    # --- Example with a 3D RGB-style sequence ---
    print("\n--- Testing with 3D RGB-style Sequence ---")
    batch, seq_len, features = 1, 60, 4
    mock_grid_3d = torch.randn(batch, seq_len, features)

    try:
        # Note: The mock model doesn't actually use the input, so this works.
        # A real model would need to be trained on this type of flattened input.
        fan_df_3d = feed_to_hrm_flattened(
            grid=mock_grid_3d,
            model=mock_model,
            horizon_len=horizon
        )
        print("Successfully generated fan DataFrame from 3D sequence:")
        print(fan_df_3d.head())
    except Exception as e:
        print(f"An error occurred during 3D sequence test: {e}")
