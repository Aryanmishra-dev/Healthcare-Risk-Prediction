"""
Lung Cancer Prediction — Complete ML Pipeline
==============================================
Trains, evaluates, tunes, and saves a production-ready lung cancer model.
Run from the project root:
    python -m ml.pipelines.training.train_lung_cancer_model
"""

import os
import warnings

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import (
    GridSearchCV,
    StratifiedKFold,
    cross_validate,
    train_test_split,
)
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")
np.random.seed(42)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
DATA_PATH = os.path.join(ROOT, "data", "raw", "survey_lung_cancer.csv")
MODEL_DIR = os.path.join(ROOT, "ml", "models")
PLOT_DIR = os.path.join(ROOT, "ml", "experiments", "lung_cancer_plots")
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(PLOT_DIR, exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════
#  STEP 1 — DATA PREPROCESSING
# ══════════════════════════════════════════════════════════════════════════

print("=" * 70)
print("STEP 1 — DATA PREPROCESSING")
print("=" * 70)

df = pd.read_csv(DATA_PATH)
print(f"\nRaw data shape: {df.shape}")
print(f"Duplicates: {df.duplicated().sum()}")

# Drop duplicates
df = df.drop_duplicates().reset_index(drop=True)
print(f"After dropping duplicates: {df.shape}")

# Encode Gender: Male=1, Female=0
df["Gender"] = df["Gender"].map({"Male": 1, "Female": 0})

# Encode target: YES=1, NO=0
df["LUNG_CANCER"] = df["LUNG_CANCER"].map({"YES": 1, "NO": 0})

# Drop low-value features
df = df.drop(columns=["Anxiety", "Allergy"])
print(f"After dropping Anxiety & Allergy: {df.shape}")
print(f"\nClass distribution:\n{df['LUNG_CANCER'].value_counts()}")
print(
    f"Class balance: {df['LUNG_CANCER'].value_counts(normalize=True).to_dict()}"
)

# Separate features and target
FEATURE_COLS = [c for c in df.columns if c != "LUNG_CANCER"]
X = df[FEATURE_COLS].copy()
y = df["LUNG_CANCER"].copy()

# Scale Age only (rest are already binary)
scaler = StandardScaler()
X["Age"] = scaler.fit_transform(X[["Age"]])

print(f"\nFeature columns ({len(FEATURE_COLS)}): {FEATURE_COLS}")
print(f"X shape: {X.shape}, y shape: {y.shape}")

# Stratified 80/20 split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)
print(f"Train: {X_train.shape}, Test: {X_test.shape}")


# ══════════════════════════════════════════════════════════════════════════
#  STEP 2 & 3 — TRAIN MODELS + EVALUATION METRICS
# ══════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("STEP 2 & 3 — TRAINING & EVALUATION")
print("=" * 70)

models = {
    "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
    "Decision Tree": DecisionTreeClassifier(random_state=42),
    "Random Forest": RandomForestClassifier(n_estimators=200, random_state=42),
    "XGBoost": XGBClassifier(
        n_estimators=200,
        learning_rate=0.1,
        max_depth=5,
        eval_metric="logloss",
        random_state=42,
        use_label_encoder=False,
    ),
    "KNN": KNeighborsClassifier(n_neighbors=5),
    "SVM": SVC(kernel="rbf", probability=True, random_state=42),
    "Naive Bayes": GaussianNB(),
}

results = []
trained_models = {}

for name, model in models.items():
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_prob)
    cm = confusion_matrix(y_test, y_pred)

    results.append(
        {
            "Model": name,
            "Accuracy": acc,
            "Precision": prec,
            "Recall": rec,
            "F1": f1,
            "ROC-AUC": auc,
        }
    )
    trained_models[name] = {"model": model, "cm": cm}

    print(f"\n--- {name} ---")
    print(f"  Accuracy:  {acc:.4f}")
    print(f"  Precision: {prec:.4f}")
    print(f"  Recall:    {rec:.4f}")
    print(f"  F1 Score:  {f1:.4f}")
    print(f"  ROC-AUC:   {auc:.4f}")
    print(f"  Confusion Matrix:\n{cm}")

# Comparison table
results_df = pd.DataFrame(results).sort_values("Recall", ascending=False)
print("\n\n" + "=" * 70)
print("MODEL COMPARISON TABLE (sorted by Recall)")
print("=" * 70)
print(results_df.to_string(index=False, float_format="%.4f"))

# Save confusion matrix plots
fig, axes = plt.subplots(2, 4, figsize=(20, 10))
axes = axes.flatten()
for idx, (name, info) in enumerate(trained_models.items()):
    if idx >= 7:
        break
    sns.heatmap(info["cm"], annot=True, fmt="d", cmap="Blues", ax=axes[idx])
    axes[idx].set_title(name, fontsize=10, fontweight="bold")
    axes[idx].set_xlabel("Predicted")
    axes[idx].set_ylabel("Actual")
if len(trained_models) < 8:
    axes[7].axis("off")
plt.tight_layout()
plt.savefig(os.path.join(PLOT_DIR, "confusion_matrices.png"), dpi=150)
plt.close()
print("\nConfusion matrix plots saved.")


# ══════════════════════════════════════════════════════════════════════════
#  STEP 4 — BEST MODEL SELECTION
# ══════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("STEP 4 — BEST MODEL SELECTION")
print("=" * 70)

# Select best by Recall + ROC-AUC combined score
results_df["Combined"] = results_df["Recall"] + results_df["ROC-AUC"]
best_row = results_df.loc[results_df["Combined"].idxmax()]
best_name = best_row["Model"]
best_model = trained_models[best_name]["model"]

print(f"\nBest Model: {best_name}")
print(
    f"  Reason: Highest combined Recall ({best_row['Recall']:.4f}) + ROC-AUC ({best_row['ROC-AUC']:.4f})"
)
print(f"\nFull Classification Report for {best_name}:")
y_pred_best = best_model.predict(X_test)
print(classification_report(y_test, y_pred_best))


# ══════════════════════════════════════════════════════════════════════════
#  STEP 5 — FEATURE IMPORTANCE PLOT
# ══════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("STEP 5 — FEATURE IMPORTANCE")
print("=" * 70)

if hasattr(best_model, "feature_importances_"):
    importances = best_model.feature_importances_
elif hasattr(best_model, "coef_"):
    importances = np.abs(best_model.coef_[0])
else:
    # For models without native feature importances, use permutation importance
    from sklearn.inspection import permutation_importance

    perm = permutation_importance(
        best_model, X_test, y_test, n_repeats=10, random_state=42
    )
    importances = perm.importances_mean

feat_imp = pd.DataFrame(
    {"Feature": FEATURE_COLS, "Importance": importances}
).sort_values("Importance", ascending=False)
print(feat_imp.to_string(index=False))

plt.figure(figsize=(10, 6))
sns.barplot(data=feat_imp, x="Importance", y="Feature", palette="viridis")
plt.title(f"Feature Importances — {best_name}", fontweight="bold")
plt.tight_layout()
plt.savefig(os.path.join(PLOT_DIR, "feature_importances.png"), dpi=150)
plt.close()
print("Feature importance plot saved.")


# ══════════════════════════════════════════════════════════════════════════
#  STEP 6 — CROSS VALIDATION
# ══════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("STEP 6 — 5-FOLD STRATIFIED CROSS VALIDATION")
print("=" * 70)

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
cv_results = cross_validate(
    best_model,
    X,
    y,
    cv=cv,
    scoring=["accuracy", "f1"],
    return_train_score=False,
)
print(
    f"Accuracy — Mean: {cv_results['test_accuracy'].mean():.4f}, Std: {cv_results['test_accuracy'].std():.4f}"
)
print(
    f"F1 Score — Mean: {cv_results['test_f1'].mean():.4f}, Std: {cv_results['test_f1'].std():.4f}"
)


# ══════════════════════════════════════════════════════════════════════════
#  STEP 7 — HYPERPARAMETER TUNING
# ══════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("STEP 7 — HYPERPARAMETER TUNING")
print("=" * 70)

# Define param grid based on best model type
if isinstance(best_model, XGBClassifier):
    param_grid = {
        "n_estimators": [100, 200, 300],
        "max_depth": [3, 5, 7],
        "learning_rate": [0.05, 0.1, 0.2],
        "subsample": [0.8, 1.0],
    }
    tuning_model = XGBClassifier(
        eval_metric="logloss", random_state=42, use_label_encoder=False
    )
elif isinstance(best_model, RandomForestClassifier):
    param_grid = {
        "n_estimators": [100, 200, 300],
        "max_depth": [None, 10, 20],
        "min_samples_split": [2, 5],
        "min_samples_leaf": [1, 2],
    }
    tuning_model = RandomForestClassifier(random_state=42)
elif isinstance(best_model, GradientBoostingClassifier):
    param_grid = {
        "n_estimators": [100, 200, 300],
        "max_depth": [3, 5, 7],
        "learning_rate": [0.05, 0.1, 0.2],
    }
    tuning_model = GradientBoostingClassifier(random_state=42)
elif isinstance(best_model, LogisticRegression):
    param_grid = {
        "C": [0.01, 0.1, 1, 10],
        "solver": ["lbfgs", "liblinear"],
    }
    tuning_model = LogisticRegression(max_iter=1000, random_state=42)
elif isinstance(best_model, DecisionTreeClassifier):
    param_grid = {
        "max_depth": [3, 5, 10, None],
        "min_samples_split": [2, 5, 10],
    }
    tuning_model = DecisionTreeClassifier(random_state=42)
elif isinstance(best_model, KNeighborsClassifier):
    param_grid = {
        "n_neighbors": [3, 5, 7, 9, 11],
        "weights": ["uniform", "distance"],
    }
    tuning_model = KNeighborsClassifier()
else:
    # SVM or Naive Bayes
    param_grid = {
        "C": [0.1, 1, 10],
        "kernel": ["rbf", "linear"],
    }
    tuning_model = SVC(probability=True, random_state=42)

grid_search = GridSearchCV(
    tuning_model, param_grid, cv=5, scoring="recall", n_jobs=-1, verbose=0
)
grid_search.fit(X_train, y_train)
tuned_model = grid_search.best_estimator_

print(f"Best Parameters: {grid_search.best_params_}")
print(f"Best CV Recall:  {grid_search.best_score_:.4f}")

y_pred_tuned = tuned_model.predict(X_test)
y_prob_tuned = tuned_model.predict_proba(X_test)[:, 1]
print(f"\nTuned Model Metrics on Test Set:")
print(f"  Accuracy:  {accuracy_score(y_test, y_pred_tuned):.4f}")
print(f"  Precision: {precision_score(y_test, y_pred_tuned):.4f}")
print(f"  Recall:    {recall_score(y_test, y_pred_tuned):.4f}")
print(f"  F1 Score:  {f1_score(y_test, y_pred_tuned):.4f}")
print(f"  ROC-AUC:   {roc_auc_score(y_test, y_prob_tuned):.4f}")
print(
    f"\nClassification Report:\n{classification_report(y_test, y_pred_tuned)}"
)


# ══════════════════════════════════════════════════════════════════════════
#  STEP 8 — SAVE THE MODEL
# ══════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("STEP 8 — SAVING MODEL & SCALER")
print("=" * 70)

model_path = os.path.join(MODEL_DIR, "lung_cancer_model.pkl")
scaler_path = os.path.join(MODEL_DIR, "lung_cancer_scaler.pkl")
features_path = os.path.join(MODEL_DIR, "lung_cancer_features.pkl")

joblib.dump(tuned_model, model_path)
joblib.dump(scaler, scaler_path)
joblib.dump(FEATURE_COLS, features_path)

print(f"Model saved:    {model_path}")
print(f"Scaler saved:   {scaler_path}")
print(f"Features saved: {features_path}")


# ══════════════════════════════════════════════════════════════════════════
#  STEP 9 — PREDICT ON NEW INPUT
# ══════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("STEP 9 — PREDICT ON NEW INPUT")
print("=" * 70)


def predict_lung_cancer(patient: dict) -> dict:
    """
    Predict lung cancer risk for a single patient.

    Parameters
    ----------
    patient : dict with keys:
        Age, Gender, Smoking, Yellow Fingers, Chronic Disease,
        Fatigue, Wheezing, Shortness of Breath

    Returns
    -------
    dict with 'prediction' (str) and 'probability' (float %).
    """
    loaded_model = joblib.load(model_path)
    loaded_scaler = joblib.load(scaler_path)
    loaded_features = joblib.load(features_path)

    # Encode gender
    gender_val = 1 if patient.get("Gender", "Male") == "Male" else 0

    row = {
        "Age": patient["Age"],
        "Gender": gender_val,
        "Smoking": patient.get("Smoking", 0),
        "Yellow Fingers": patient.get("Yellow Fingers", 0),
        "Chronic Disease": patient.get("Chronic Disease", 0),
        "Fatigue": patient.get("Fatigue", 0),
        "Wheezing": patient.get("Wheezing", 0),
        "Shortness of Breath": patient.get("Shortness of Breath", 0),
    }

    df_input = pd.DataFrame([row])[loaded_features]
    df_input["Age"] = loaded_scaler.transform(df_input[["Age"]])

    prob = loaded_model.predict_proba(df_input)[:, 1][0]
    risk_pct = round(prob * 100, 1)

    if prob >= 0.5:
        label = "HIGH RISK - Lung Cancer Detected"
    else:
        label = "LOW RISK - No Lung Cancer Detected"

    return {"prediction": label, "probability": risk_pct}


# Test with example patient
test_patient = {
    "Age": 65,
    "Gender": "Male",
    "Smoking": 1,
    "Yellow Fingers": 1,
    "Chronic Disease": 1,
    "Fatigue": 1,
    "Wheezing": 1,
    "Shortness of Breath": 1,
}

result = predict_lung_cancer(test_patient)
print(f"\nTest Patient: {test_patient}")
print(f"Prediction:   {result['prediction']}")
print(f"Probability:  {result['probability']}%")


# ══════════════════════════════════════════════════════════════════════════
#  FINAL SUMMARY
# ══════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("PIPELINE SUMMARY")
print("=" * 70)
print(f"Dataset:            data/raw/survey_lung_cancer.csv")
print(f"Clean rows:         {len(df)}")
print(f"Features used:      {FEATURE_COLS}")
print(f"Models evaluated:   {len(models)}")
print(f"Best model:         {best_name}")
print(f"Tuned model:        {type(tuned_model).__name__}")
print(f"Best params:        {grid_search.best_params_}")
print(f"Test Recall:        {recall_score(y_test, y_pred_tuned):.4f}")
print(f"Test ROC-AUC:       {roc_auc_score(y_test, y_prob_tuned):.4f}")
print(f"Saved artifacts:    model, scaler, features -> ml/models/")
print(f"Plots saved:        {PLOT_DIR}/")
print("=" * 70)
print("PIPELINE COMPLETE")
print("=" * 70)
