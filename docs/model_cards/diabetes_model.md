# Model Card: Diabetes Risk Prediction

## Model Details
- **Developer:** Healthcare Risk Prediction Team
- **Model Date:** March 2026
- **Model Version:** 1.0
- **Model Type:** Extreme Gradient Boosting (XGBoost) classifier, with isotonic calibration.
- **Information:** This model predicts the likelihood of an individual having or developing diabetes based on demographic, lifestyle, and clinical health indicators.

## Intended Use
- **Primary Use Cases:** Screening and early risk identification for individuals. Intended to be used as an assistive tool for healthcare providers or as a personal informational tool.
- **Out-of-Scope Uses:** This model is **not** a diagnostic tool. It should not be used as a replacement for professional medical advice, diagnosis, or treatment.

## Factors
- **Demographic:** Age (categorized)
- **Clinical:** BMI, High Blood Pressure, High Cholesterol, General Health, Mental Health Days
- **Lifestyle:** Smoker status, Physical Activity
- **Fairness & Bias:** The model was evaluated for age and gender biases, attempting to minimize disparate impact across protected groups.

## Metrics
- **Performance Measures:** ROC-AUC, Brier Score (for calibration), Precision, Recall, F1-Score.
- **Thresholds:** A default threshold of 0.5 is used, but outputs are primarily delivered as calibrated probabilities (0-100%).

## Training Data
- **Dataset:** 2015 Behavioral Risk Factor Surveillance System (BRFSS) dataset provided by the CDC.
- **Preprocessing:** Records with missing critical target values were dropped or imputed. Outliers were clamped or removed based on physiological bounds.

## Ethical Considerations
- Care should be taken to ensure that the system does not over-penalize minority or underrepresented demographics in the BRFSS dataset. Continuous monitoring of drift and fairness metrics is recommended.

## Caveats and Recommendations
- The model relies on self-reported data (BRFSS), which is inherently subject to recall bias.
- Predictions include SHAP-based feature importance to ensure transparency in how a risk score was achieved.
