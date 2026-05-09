import pytest
import pandas as pd
import os
import shutil
from src.analyze_sensitivity import SensitivityAnalyser

def test_recommend_hdbscan_config_basic():
    # Create a dummy CSV
    csv_path = "tests/dummy_hdbscan.csv"
    df = pd.DataFrame({
        "min_cluster_size": [3, 5, 8],
        "min_samples": [2, 3, 5],
        "rebalance_interval": [25, 50, 100],
        "mean_art": [25.0, 20.0, 30.0],
        "mean_rebalance_count": [10, 5, 2],
        "mean_noise_fraction": [0.1, 0.2, 0.4]
    })
    df.to_csv(csv_path, index=False)
    
    analyser = SensitivityAnalyser(None, None, csv_path)
    rec = analyser.recommend_hdbscan_config()
    
    # It should pick mcs=5 because it has lower ART than 3 and lower noise than 8 (noise <= 0.3)
    assert rec["min_cluster_size"] == 5
    os.remove(csv_path)

def test_generate_report_creates_file():
    report_path = "tests/test_report.md"
    analyser = SensitivityAnalyser(None, None, None)
    analyser.generate_report(report_path)
    assert os.path.exists(report_path)
    os.remove(report_path)
