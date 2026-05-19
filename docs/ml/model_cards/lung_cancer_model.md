# Model Card: Lung Cancer Risk Prediction

## Model Details
- **Developer:** Healthcare Risk Prediction Team
- **Model Date:** March 2026
- **Model Version:** 1.0
- **Model Type:** Scikit-Learn based standard classifier (Random Forest or similar ensemble), appropriately scaled.
- **Information:** Assesses lung cancer risk using self-reported symptoms and smoking history.

## Intended Use
- **Primary Use Cases:** Pre-screening and alerting individuals with high symptom burdens (e.g., chronic coughing, shortness of breath, smoking history) to seek medical attention.
- **Out-of-Scope Uses:** Definitive diagnosis of lung cancer. Not a replacement for imaging (e.g., low-dose CT) or biopsy.

## Factors
- **Demographic:** Age, Gender
- **Clinical/Symptomatic:** Yellow fingers, Chronic disease, Fatigue, Wheezing, Shortness of breath
- **Lifestyle:** Smoking

## Metrics
- **Performance Measures:** ROC-AUC, Sensitivity (Recall) prioritized to minimize false negatives in a high-risk condition.
- **Thresholds:** Model outputs continuous probabilities interpreted alongside SHAP explanations.

## Training Data
- **Dataset:** Synthetic or anonymized clinical datasets mimicking lung cancer risk factors and early symptoms.
- **Preprocessing:** Features mapped to binary or ordinal scales matching the frontend forms.

## Ethical Considerations
- High stakes: False negatives can lead to a false sense of security. The UI must mandate clear disclaimers that this is an informational tool.
- False positives may cause unnecessary anxiety, so SHAP values are provided to contextualize exactly *why* a risk appears elevated.

## Caveats and Recommendations
- Smoking is a known dominant predictor. If a patient is a non-smoker but presents with severe symptoms, they may receive an underestimated risk compared to purely clinical settings. Consult medical professionals.
