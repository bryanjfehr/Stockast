import pandas as pd
import numpy as np
import pytest
from textbackend.utils.rgb_processor import to_rgb_chart

@pytest.fixture
def sample_df():
    """Create a sample DataFrame for testing."""
    data = {
        'timestamp': pd.to_datetime(pd.date_range('2023-01-01', periods=100)),
        'open': np.random.uniform(95, 105, 100),
        'high': np.random.uniform(100, 110, 100),
        'low': np.random.uniform(90, 100, 100),
        'close': np.random.uniform(98, 108, 100),
        'volume': np.random.uniform(1000, 5000, 100),
        'sentiment_pct': np.random.rand(100)
    }
    return pd.DataFrame(data).set_index('timestamp')

def test_to_rgb_chart_output_shape_and_columns(sample_df):
    """Test the output shape and columns of to_rgb_chart."""
    df_rgb, hex_colors = to_rgb_chart(sample_df)
    
    assert isinstance(df_rgb, pd.DataFrame)
    assert isinstance(hex_colors, list)
    assert df_rgb.shape[0] == sample_df.shape[0]
    assert len(hex_colors) == sample_df.shape[0]
    
    expected_columns = ['R', 'G', 'B', 'line_val', 'hex_color']
    for col in expected_columns:
        assert col in df_rgb.columns

def test_rgb_values_are_in_range(sample_df):
    """Test that R, G, B values are within the 0-255 range."""
    df_rgb, _ = to_rgb_chart(sample_df)
    
    assert df_rgb['R'].min() >= 0
    assert df_rgb['R'].max() <= 255
    assert df_rgb['G'].min() >= 0
    assert df_rgb['G'].max() <= 255
    assert df_rgb['B'].min() >= 0
    assert df_rgb['B'].max() <= 255

def test_line_val_is_normalized(sample_df):
    """Test that line_val is normalized between 0 and 1."""
    df_rgb, _ = to_rgb_chart(sample_df)
    
    assert df_rgb['line_val'].min() >= 0.0
    assert df_rgb['line_val'].max() <= 1.0

def test_hex_colors_format(sample_df):
    """Test the format of the generated hex colors."""
    _, hex_colors = to_rgb_chart(sample_df)
    
    for color in hex_colors:
        assert isinstance(color, str)
        assert color.startswith('#')
        assert len(color) == 7

def test_empty_dataframe_input():
    """Test function with an empty DataFrame."""
    df_rgb, hex_colors = to_rgb_chart(pd.DataFrame())
    
    assert df_rgb.empty
    assert hex_colors == []