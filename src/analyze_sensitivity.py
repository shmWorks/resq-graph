"""
analyze_sensitivity.py – Sprint 10 (US-040)

Generates plots and the Markdown report from the sensitivity sweep CSVs.
"""
from __future__ import annotations

import os
import sys
import pandas as pd

# Ensure src is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.rendering.visualizer import plot_sensitivity_lambda, plot_sensitivity_fleet, plot_sensitivity_hdbscan_art, plot_sensitivity_hdbscan_churn

class SensitivityAnalyser:
    def __init__(self, lambda_csv: str | None, fleet_csv: str | None, hdbscan_csv: str | None):
        self.lambda_df  = pd.read_csv(lambda_csv) if lambda_csv and os.path.exists(lambda_csv) else None
        self.fleet_df   = pd.read_csv(fleet_csv) if fleet_csv and os.path.exists(fleet_csv) else None
        self.hdbscan_df = pd.read_csv(hdbscan_csv) if hdbscan_csv and os.path.exists(hdbscan_csv) else None

    def generate_all_plots(self, figures_dir: str) -> None:
        os.makedirs(figures_dir, exist_ok=True)
        if self.lambda_df is not None:
            plot_sensitivity_lambda(self.lambda_df, os.path.join(figures_dir, "sensitivity_lambda.png"))
        if self.fleet_df is not None:
            plot_sensitivity_fleet(self.fleet_df, os.path.join(figures_dir, "sensitivity_fleet_size.png"))
        if self.hdbscan_df is not None:
            plot_sensitivity_hdbscan_art(self.hdbscan_df, os.path.join(figures_dir, "sensitivity_hdbscan_art.png"))
            plot_sensitivity_hdbscan_churn(self.hdbscan_df, os.path.join(figures_dir, "sensitivity_hdbscan_churn.png"))

    def recommend_hdbscan_config(self) -> dict:
        if self.hdbscan_df is None:
            return {}
        df = self.hdbscan_df
        filtered = df[
            (df["mean_rebalance_count"] <= df["mean_rebalance_count"].median()) &
            (df["mean_noise_fraction"] <= 0.30)
        ]
        if filtered.empty:
            return df.loc[df["mean_art"].idxmin()].to_dict()
        return filtered.loc[filtered["mean_art"].idxmin()].to_dict()

    def generate_report(self, output_path: str) -> None:
        # For US-037, we only do a basic report for lambda. US-040 expands this.
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# ResQ-Graph: Sensitivity Analysis Report\n\n")
            f.write("Generated from latest sweep results.\n\n")

            if self.lambda_df is not None:
                f.write("## 1. Event Rate (Lambda) Sensitivity\n\n")
                f.write("![Lambda Sensitivity](figures/sensitivity_lambda.png)\n\n")

            if self.fleet_df is not None:
                f.write("## 2. Fleet Size Sensitivity\n\n")
                f.write("![Fleet Size Sensitivity](figures/sensitivity_fleet_size.png)\n\n")

            if self.hdbscan_df is not None:
                rec = self.recommend_hdbscan_config()
                f.write("## 3. HDBSCAN Parameter Sensitivity\n\n")
                f.write(f"Recommended: min_cluster_size={rec.get('min_cluster_size')}, ")
                f.write(f"min_samples={rec.get('min_samples')}, ")
                f.write(f"rebalance_interval={rec.get('rebalance_interval')}\n\n")
                f.write("![HDBSCAN ART Heatmap](figures/sensitivity_hdbscan_art.png)\n")
                f.write("![HDBSCAN Churn vs ART](figures/sensitivity_hdbscan_churn.png)\n")
        
        print(f"[Sensitivity] Report written -> {output_path}")

def main():
    analyser = SensitivityAnalyser(
        "outputs/sensitivity/lambda_sweep.csv",
        "outputs/sensitivity/fleet_sweep.csv",
        "outputs/sensitivity/hdbscan_sweep.csv"
    )
    analyser.generate_all_plots("outputs/figures/")
    analyser.generate_report("outputs/sensitivity_report.md")

if __name__ == "__main__":
    main()
