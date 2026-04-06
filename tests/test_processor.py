
import sys
import os
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch

# Add parent directory to path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import processor
import utils

# --- FIXTURES ---

@pytest.fixture
def mock_reader():
    """Mock the reader module to avoid reading real files"""
    with patch('reader.read_complex_excel_structure') as mock:
        yield mock

@pytest.fixture
def sample_df_happy_path():
    """Create a standard dataframe mimicking Excel structure"""
    data = {
        'NGÀY': ['01/01/2024', '01/01/2024'],
        'SỐ MÁY': ['M01', 'M01'],
        'SỐ THỨ TỰ': [1, 2],
        'TỔNG SẢN PHẨM': [1000, 2000],
        'TỔNG SP LỖI': [50, 100],  # Explicit Total Fail column
        'Lỗi A': [10, 20],
        'Lỗi B': [40, 80],
        'QUAI (Sửa)': [5, 10], # Repairable
        'GHI CHÚ': ['', 'Note']
    }
    return pd.DataFrame(data)

@pytest.fixture
def sample_df_edge_cases():
    """Create a dataframe with edge cases: nulls, zeros, negatives, strings"""
    data = {
        'NGÀY': ['01/01/2024', pd.NaT],
        'SỐ MÁY': ['M02', 'M02'],
        'SỐ THỨ TỰ': [1, 2],
        'TỔNG SẢN PHẨM': ['1,000', None], # String format, Null
        'TỔNG SP LỖI': [-50, 0], # Negative (Logic should handle or expose), Zero
        'Lỗi A': [0, None],
        'Lỗi B': ['10%', '0'],
        'QUAI (Sửa)': [0, 0],
        'GHI CHÚ': [None, None]
    }
    return pd.DataFrame(data)

# --- TESTS ---

def test_happy_path_processing(mock_reader, sample_df_happy_path):
    """
    Test normal data processing.
    Expect:
    - Dataframe returned not None.
    - KPIs calculated correctly.
    """
    # Setup Mock
    mock_reader.return_value = (sample_df_happy_path, None)
    
    # Run
    input_data = [{"file": "dummy.xlsx", "sheet_name": "Sheet1", "display_name": "TestFile"}]
    df_res, logs, legend = processor.process_uploaded_new_form_data(input_data)
    
    # Assertions
    assert df_res is not None, "Result DataFrame should not be None"
    assert not df_res.empty, "Result DataFrame should not be empty"
    
    # Check KPIs
    # Unique rows for Roll Level KPIs (processor logic maps KPI to melted rows)
    # We need to drop duplicates to check roll totals
    df_rolls = df_res.drop_duplicates(subset=['Unique_Row_Key'])
    assert len(df_rolls) == 2, "Should have 2 unique rolls"
    
    # Check Roll 1
    r1 = df_rolls[df_rolls['SỐ THỨ TỰ CUỘN'] == 1].iloc[0]
    assert r1['KPI_Roll_Production'] == 1000
    assert r1['KPI_Roll_Fail'] == 50
    
    # Check Roll 2
    r2 = df_rolls[df_rolls['SỐ THỨ TỰ CUỘN'] == 2].iloc[0]
    assert r2['KPI_Roll_Production'] == 2000
    assert r2['KPI_Roll_Fail'] == 100

def test_missing_defect_columns(mock_reader):
    """Test when no defect columns are found (only system columns)"""
    df_empty = pd.DataFrame({'NGÀY': ['01/01/2024'], 'SỐ MÁY': ['M1']}) # Only system cols
    mock_reader.return_value = (df_empty, None)
    
    input_data = [{"file": "dummy.xlsx", "sheet_name": "Sheet1", "display_name": "TestEmpty"}]
    df_res, logs, l = processor.process_uploaded_new_form_data(input_data)
    
    # Assert
    assert df_res is None, "Should return None if no defect columns found"

def test_edge_cases_processing(mock_reader, sample_df_edge_cases):
    """
    Test edge cases: Nulls, Formatting, Zeroes.
    INVARIANTS: Total Fail/Production must be >= 0.
    """
    mock_reader.return_value = (sample_df_edge_cases, None)
    input_data = [{"file": "dummy.xlsx", "sheet_name": "Sheet1", "display_name": "TestEdge"}]
    df_res, logs, legend = processor.process_uploaded_new_form_data(input_data)
    
    assert df_res is not None
    
    # We added Invariant Check in Processor (max(0, val))
    # Check that negative input (-50) became 0
    
    df_rolls = df_res.drop_duplicates(subset=['Unique_Row_Key'])
    assert not df_rolls.empty
    
    # Retrieve Roll 1
    r1_list = df_rolls[df_rolls['SỐ THỨ TỰ CUỘN'] == 1]
    if not r1_list.empty:
        r1 = r1_list.iloc[0]
        assert r1['KPI_Roll_Production'] == 1000, "Should handle '1,000'"
        assert r1['KPI_Roll_Fail'] == 0, "[Invariant] Negative Fail (-50) should be clamped to 0"
    
    # Roll 2 (Null Prod -> 0)
    r2_list = df_rolls[df_rolls['SỐ THỨ TỰ CUỘN'] == 2]
    if not r2_list.empty:
        r2 = r2_list.iloc[0]
        assert r2['KPI_Roll_Production'] == 0, "Null production should be 0"

