#!/usr/bin/env python3
"""
Subgroup Fairness evaluation script to compute Equalized Odds and Disparate Impact
metrics across demographic segments.
"""

import pandas as pd
import numpy as np
from sklearn.metrics import confusion_matrix

def calculate_equalized_odds(y_true, y_pred, sensitive_attribute):
    """
    Computes False Positive Rate (FPR) and True Positive Rate (TPR)
    across different subgroups defined by the sensitive attribute.
    """
    results = {}
    groups = np.unique(sensitive_attribute)
    
    for group in groups:
        mask = (sensitive_attribute == group)
        tn, fp, fn, tp = confusion_matrix(y_true[mask], y_pred[mask]).ravel()
        
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        
        results[group] = {"FPR": fpr, "TPR": tpr}
        
    return results

def calculate_disparate_impact(y_pred, sensitive_attribute):
    """
    Computes the Disparate Impact Ratio (positive prediction rate ratio).
    """
    groups = np.unique(sensitive_attribute)
    rates = {}
    
    for group in groups:
        mask = (sensitive_attribute == group)
        positive_rate = np.mean(y_pred[mask])
        rates[group] = positive_rate
        
    return rates

def main():
    print("Subgroup Fairness Evaluation Metric Checker\n")
    # Simulate Evaluation DataFrame
    np.random.seed(42)
    n = 1000
    df = pd.DataFrame({
        "gender": np.random.choice(["Male", "Female", "Non-binary"], size=n),
        "y_true": np.random.randint(0, 2, size=n),
        "y_pred": np.random.randint(0, 2, size=n)
    })
    
    # 1. Equalized Odds
    eq_odds = calculate_equalized_odds(df["y_true"], df["y_pred"], df["gender"])
    print("Equalized Odds (FPR/TPR by Group):")
    for group, metrics in eq_odds.items():
        print(f"  {group:>10}: FPR={metrics['FPR']:.3f}, TPR={metrics['TPR']:.3f}")
        
    # 2. Disparate Impact
    di_rates = calculate_disparate_impact(df["y_pred"], df["gender"])
    print("\nDisparate Impact (Positive Prediction Rate):")
    base_rate = di_rates.get("Male", 0.01) # Baseline
    for group, rate in di_rates.items():
        if base_rate > 0:
            ratio = rate / base_rate
            print(f"  {group:>10}: Rate={rate:.3f} | Impact Ratio (vs Male): {ratio:.3f}")
            
    print("\nEvaluation complete. Adjust models to ensure FPR differences < 0.1 between groups.")

if __name__ == "__main__":
    main()
