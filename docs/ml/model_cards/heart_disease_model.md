# Model Card: Heart Disease Risk Prediction

## Model Details
- **Developer:** Healthcare Risk Prediction Team
- **Model Date:** March 2026
- **Model Version:** 1.0
- **Model Type:** Extreme Gradient Boosting (XGBoost) classifier.
- **Information:** Predicts the risk of heart disease (Coronary Heart Disease or Myocardial Infarction) based on clinical and lifestyle inputs.

## Intended Use
- **Primary Use Cases:** Early risk identification. Intended for use in assistive diagnostic workflows or general health guidance.
- **Out-of-Scope Uses:** Definitive clinical diagnosis, standalone medical decision-making without physician oversight.

## Factors
- **Demographic:** Age, Sex
- **Clinical:** BMI, High Blood Pressure, High Cholesterol
- **Lifestyle:** Smoker status, Physical Activity (Yes/No)

## Metrics
- **Performance Measures:** Validated primarily using ROC-AUC and F1-score due to potential class imbalances.
- **Thresholds:** Evaluated via precision-recall curves. Currently deployed with continuous calibrated probability outputs.

## Training Data
- **Dataset:** 2015 Behavioral Risk Factor Surveillance System (BRFSS).
- **Preprocessing:** Selected subset of features closely related to cardiovascular conditions. Balanced or weighted during training to handle the relatively low prevalence of heart disease in the general sample.

## Ethical Considerations
- Gender and Age are significant risk factors for heart disease; the model ensures that while these are predictive, the application does not unjustly deny services based on demographic inputs.

## Caveats and Recommendations
- As with diabetes, BRFSS data is self-reported.
- Risk prediction is strongly coupled with age. Users should be aware that the model heavily weighs advanced age as a risk factor.
