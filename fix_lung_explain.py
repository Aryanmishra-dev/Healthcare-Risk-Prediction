import re

with open("app/main.py", "r") as f:
    code = f.read()

code = code.replace(
    '    from fastapi_backend.model_loader import _lung_features\n    df = pd.DataFrame([row])[_lung_features].astype(np.float64)',
    '    f = request.app.state.models.get("lung_features")\n    df = pd.DataFrame([row])[f].astype(np.float64)'
)

with open("app/main.py", "w") as f:
    f.write(code)

