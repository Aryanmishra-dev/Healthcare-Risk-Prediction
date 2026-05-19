#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import numpy as np
import warnings
import os
warnings.filterwarnings("ignore")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))

df = pd.read_sas(os.path.join(ROOT, "data", "raw", "LLCP2015.XPT"))
print(f"Raw data shape: {df.shape}")
print(f"Columns: {df.shape[1]}")
print(f"Rows: {df.shape[0]:,}")


# In[ ]:


## Step 2 - Create Heart Disease Target Variable
#
# Combine two BRFSS columns:
# - `CVDINFR4` -> Heart attack history (1 = Yes)
# - `CVDCRHD4` -> Coronary heart disease (1 = Yes)
#
# Target: `heart_disease` = 1 if either condition is present, 0 otherwise.


# In[2]:


# Preview raw heart disease columns
print("Raw value counts:")
print("CVDINFR4 (Heart attack):", dict(df["CVDINFR4"].value_counts().head()))
print("CVDCRHD4 (Coronary HD):", dict(df["CVDCRHD4"].value_counts().head()))

# Create binary target: 1 = heart disease present, 0 = no heart disease
df["heart_disease"] = (
    (df["CVDINFR4"] == 1) |
    (df["CVDCRHD4"] == 1)
).astype(int)

print(f"\nTarget distribution:")
print(df["heart_disease"].value_counts())
print(f"\nHeart disease prevalence: {df['heart_disease'].mean():.3f} ({df['heart_disease'].mean()*100:.1f}%)")


# In[ ]:


## Step 3 - Select Features
#
# 14 medically relevant predictors for heart disease risk:
# _AGEG5YR, SEX, _BMI5, _RFHYPE5, _RFCHOL, SMOKE100, _TOTINDA,
# _FRTLT1, _VEGLT1, _RFDRHV5, GENHLTH, MENTHLTH, PHYSHLTH, DIABETE3.


# In[3]:


features = [
    "_AGEG5YR",   # Age group
    "SEX",        # Gender
    "_BMI5",      # Body mass index
    "_RFHYPE5",   # High blood pressure
    "_RFCHOL",    # High cholesterol
    "SMOKE100",   # Smoking history
    "_TOTINDA",   # Physical activity
    "_FRTLT1",    # Fruit consumption
    "_VEGLT1",    # Vegetable consumption
    "_RFDRHV5",   # Heavy alcohol drinking
    "GENHLTH",    # General health rating
    "MENTHLTH",   # Mental health days
    "PHYSHLTH",   # Physical health days
    "DIABETE3",   # Diabetes diagnosis
]

target = "heart_disease"
df_model = df[features + [target]].copy()

print(f"Selected features: {len(features)}")
print(f"Model dataframe shape: {df_model.shape}")
df_model.head()


# In[ ]:


## Step 4 - Missing Value Handling
#
# BRFSS uses special codes for missing data:
# - `7` = "Don't know / Not sure"
# - `9` = "Refused"
# Replace these with `NaN` and drop rows with any remaining missing values.


# In[4]:


print(f"Before cleaning: {df_model.shape}")
print(f"Missing values per column:\n{df_model.isnull().sum()}\n")

# Replace BRFSS missing-value codes
df_model = df_model.replace({7: None, 9: None})

# Drop rows with any NaN
df_model = df_model.dropna()

print(f"After cleaning: {df_model.shape}")
print(f"Rows dropped: {df.shape[0] - df_model.shape[0]:,}")

# Validation: dataset should have >200k rows
assert df_model.shape[0] > 200_000, f"Dataset too small: {df_model.shape[0]} rows"
print(f"\n✓ Validation passed: {df_model.shape[0]:,} rows (>200k required)")


# In[ ]:


## Step 5 - Feature Engineering
#
# BMI: BRFSS stores BMI x 100 (e.g., 4018 -> 40.18). Divide by 100.
# Binary features: BRFSS uses 1=Yes, 2=No. Recode to 1/0.
# Gender: 1=Male, 2=Female -> 1=Male, 0=Female.
# DIABETE3: recode diabetes diagnosis to binary.
# MENTHLTH / PHYSHLTH: 88 = "None" -> recode to 0.


# In[5]:


# ── BMI: scale from ×100 ─────────────────────────────────────────
df_model["_BMI5"] = df_model["_BMI5"] / 100

# ── Binary features: BRFSS 1=Yes, 2=No → 1/0 ──────────────────
binary_cols = ["_RFHYPE5", "_RFCHOL", "SMOKE100", "_TOTINDA", "_FRTLT1", "_VEGLT1", "_RFDRHV5"]
for col in binary_cols:
    df_model[col] = df_model[col].map({1: 1, 2: 0})

# ── Gender: 1=Male, 2=Female → 1/0 ─────────────────────────────
df_model["SEX"] = df_model["SEX"].map({1: 1, 2: 0})

# ── Diabetes: 1=Yes, 3=No, 2=Pregnancy, 4=Borderline → binary ──
df_model["DIABETE3"] = df_model["DIABETE3"].map({1: 1, 2: 1, 3: 0, 4: 1})

# ── Mental/Physical health: 88="None" → 0, 77/99 → NaN ─────────
for col in ["MENTHLTH", "PHYSHLTH"]:
    df_model[col] = df_model[col].replace({88: 0, 77: pd.NA, 99: pd.NA})

# ── Age group: 14="Don't know" → drop ──────────────────────────
df_model["_AGEG5YR"] = df_model["_AGEG5YR"].replace(14, pd.NA)

# Drop any new NaNs from recoding
df_model = df_model.dropna()

print(f"After feature engineering: {df_model.shape}")
print(f"\nFeature value ranges:")
for col in features:
    print(f"  {col:.<20} min={df_model[col].min():.1f}  max={df_model[col].max():.1f}")


# In[ ]:


## Step 6 — Data Validation


# In[6]:


X = df_model.drop(columns=["heart_disease"])
y = df_model["heart_disease"]

# Ensure all features are numeric
X = X.apply(pd.to_numeric, errors="coerce")

print("=" * 50)
print("DATA VALIDATION CHECKS")
print("=" * 50)

# Check 1: Dataset size
print(f"\n1. Dataset size: {X.shape[0]:,} rows, {X.shape[1]} features")
assert X.shape[0] > 200_000, "Dataset too small"
print("   ✓ >200k rows")

# Check 2: Feature count
assert X.shape[1] == 14, f"Expected 14 features, got {X.shape[1]}"
print(f"   ✓ 14 features")

# Check 3: No missing values
assert X.isnull().sum().sum() == 0, "Missing values found"
print("   ✓ No missing values")

# Check 4: All numeric types
non_numeric = X.select_dtypes(exclude=["int", "float", "bool"]).columns.tolist()
assert len(non_numeric) == 0, f"Non-numeric columns: {non_numeric}"
print("   ✓ All features numeric")

# Check 5: Target distribution
print(f"\n2. Target distribution:")
print(f"   Healthy (0): {(y == 0).sum():,}")
print(f"   Disease (1): {(y == 1).sum():,}")
print(f"   Imbalance ratio: {(y == 0).sum() / (y == 1).sum():.1f} : 1")
print(f"   Prevalence: {y.mean():.3f} ({y.mean()*100:.1f}%)")

# Check 6: Data types
print(f"\n3. Data types:")
print(X.dtypes.value_counts().to_string())


# In[ ]:


## Step 7 - Train / Test Split
#
# Stratified 80/20 split to preserve class distribution.


# In[7]:


from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    stratify=y,
    random_state=42,
)

# Ensure float64 for consistency
X_train = X_train.astype(np.float64)
X_test = X_test.astype(np.float64)
y_train = y_train.astype(np.float64)
y_test = y_test.astype(np.float64)

# Compute scale_pos_weight for class imbalance
neg = (y_train == 0).sum()
pos = (y_train == 1).sum()
scale_pos_weight = neg / pos

print(f"Train: {X_train.shape}   Test: {X_test.shape}")
print(f"Positive (disease=1): {pos:,}")
print(f"Negative (healthy=0): {neg:,}")
print(f"scale_pos_weight: {scale_pos_weight:.2f}")


# In[ ]:


## Step 8 - Train XGBoost with Class Imbalance Handling
#
# Use `scale_pos_weight` to compensate for the class imbalance.


# In[ ]:


from xgboost import XGBClassifier

model = XGBClassifier(
    n_estimators=400,
    max_depth=5,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    scale_pos_weight=scale_pos_weight,
    eval_metric="auc",
    random_state=42,
    n_jobs=-1,
    early_stopping_rounds=30,
)

model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    verbose=50,
)

print(f"\nBest iteration: {model.best_iteration}")
print(f"Best AUC: {model.best_score:.4f}")


# In[ ]:


## Step 9 - Evaluate Model Performance
#
# Assess the trained model on the held-out test set using ROC-AUC,
# classification report, and confusion matrix.


# In[ ]:


from sklearn.metrics import roc_auc_score, classification_report, confusion_matrix
import matplotlib.pyplot as plt

y_pred = model.predict(X_test)
y_prob = model.predict_proba(X_test)[:, 1]

auc = roc_auc_score(y_test, y_prob)
print(f"ROC-AUC: {auc:.4f}\n")
print(classification_report(y_test, y_pred, target_names=["No Heart Disease", "Heart Disease"]))

# Confusion matrix
cm = confusion_matrix(y_test, y_pred)
fig, ax = plt.subplots(figsize=(5, 4))
ax.matshow(cm, cmap="Blues", alpha=0.7)
for i in range(cm.shape[0]):
    for j in range(cm.shape[1]):
        ax.text(j, i, f"{cm[i, j]:,}", ha="center", va="center", fontsize=14)
ax.set_xlabel("Predicted")
ax.set_ylabel("Actual")
ax.set_title("Confusion Matrix")
ax.set_xticks([0, 1])
ax.set_yticks([0, 1])
ax.set_xticklabels(["No HD", "HD"])
ax.set_yticklabels(["No HD", "HD"])
plt.tight_layout()
plt.show()


# In[ ]:


## Step 10 - Feature Importance Validation
#
# Inspect the top features by XGBoost's built-in "gain" importance.


# In[ ]:


importances = model.get_booster().get_score(importance_type="gain")
imp_df = (
    pd.DataFrame.from_dict(importances, orient="index", columns=["gain"])
    .sort_values("gain", ascending=True)
)

fig, ax = plt.subplots(figsize=(8, 6))
imp_df.plot.barh(ax=ax, legend=False, color="steelblue")
ax.set_title("Feature Importance (Gain)")
ax.set_xlabel("Mean Gain")
plt.tight_layout()
plt.show()

print("\nTop 5 features:")
for feat, gain in imp_df.sort_values("gain", ascending=False).head().iterrows():
    print(f"  {feat}: {gain['gain']:.1f}")


# In[ ]:


## Step 11 - Isotonic Probability Calibration
#
# Use isotonic regression to map raw probabilities to calibrated ones.


# In[ ]:


from sklearn.isotonic import IsotonicRegression

calibrator = IsotonicRegression(y_min=0, y_max=1, out_of_bounds="clip")
calibrator.fit(y_prob, y_test)

cal_prob = calibrator.predict(y_prob)
cal_auc = roc_auc_score(y_test, cal_prob)

print(f"Raw probabilities   — mean: {y_prob.mean():.4f}, std: {y_prob.std():.4f}")
print(f"Calibrated probs    — mean: {cal_prob.mean():.4f}, std: {cal_prob.std():.4f}")
print(f"Actual positive rate: {y_test.mean():.4f}")
print(f"Calibrated AUC: {cal_auc:.4f}")


# In[ ]:


## Step 12 - Post-Calibration Evaluation
#
# Re-evaluate using the calibrated model.


# In[ ]:


cal_pred = (cal_prob >= 0.5).astype(int)

print(f"Pre-calibration  ROC-AUC: {auc:.4f}")
print(f"Post-calibration ROC-AUC: {cal_auc:.4f}\n")
print(classification_report(y_test, cal_pred, target_names=["No Heart Disease", "Heart Disease"]))


# In[ ]:


## Step 13 - Save Model Artifacts
#
# Export the XGBoost model, isotonic calibrator, and feature list for FastAPI inference.


# In[ ]:


import joblib

models_dir = os.path.join(ROOT, "ml", "models")
os.makedirs(models_dir, exist_ok=True)

model_path = os.path.join(models_dir, "heart_disease_xgboost.pkl")
calibrator_path = os.path.join(models_dir, "heart_disease_calibrator.pkl")
features_path = os.path.join(models_dir, "heart_disease_features.pkl")

joblib.dump(model, model_path)
joblib.dump(calibrator, calibrator_path)
joblib.dump(X.columns.tolist(), features_path)

print(f"Saved model      → {model_path}  ({os.path.getsize(model_path) / 1024:.0f} KB)")
print(f"Saved calibrator → {calibrator_path}  ({os.path.getsize(calibrator_path) / 1024:.0f} KB)")
print(f"Saved features   → {features_path}")
print(f"Features ({len(X.columns)}): {X.columns.tolist()}")


# In[ ]:


## Step 14 - Quick Sanity Check
#
# Reload the saved model and run a test prediction to verify the artifact.


# In[ ]:


# Reload and verify
loaded_model = joblib.load(model_path)
loaded_calibrator = joblib.load(calibrator_path)
loaded_features = joblib.load(features_path)

# Test with a sample from the test set
sample = X_test.iloc[[0]]
raw_prob = loaded_model.predict_proba(sample)[:, 1][0]
cal_prob_val = loaded_calibrator.predict([raw_prob])[0]
risk = "High" if cal_prob_val >= 0.6 else ("Moderate" if cal_prob_val >= 0.3 else "Low")

print("=== Sanity Check ===")
print(f"Sample features: {sample.values[0]}")
print(f"Raw probability:        {raw_prob:.4f}")
print(f"Calibrated probability: {cal_prob_val:.4f}")
print(f"Risk category: {risk}")
print(f"\n✅ Heart disease model pipeline complete!")
print(f"   Model:      {model_path}")
print(f"   Calibrator: {calibrator_path}")
print(f"   Features:   {loaded_features}")
