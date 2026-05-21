import re

with open("backend/app/main.py", "r") as f:
    content = f.read()

# 1. Update imports
import_user_dep = "from backend.app.auth.dependencies import get_current_user\nfrom backend.app.models.core import User, PredictionResult"
content = content.replace("from backend.app.models.prediction import PredictionAuditLog", import_user_dep)

# 2. Update log_prediction_to_db
old_log_def = """def log_prediction_to_db(db: Session, request: Request, model_name: str, payload: dict, risk_pct: float, risk_level: str, source: str):
    \"\"\"Log prediction result and inputs to the audit database.\"\"\"
    try:
        log_entry = PredictionAuditLog(
            request_id=getattr(request.state, "request_id", "-"),
            client_ip=request.client.host if request.client else "unknown",
            disease_model=model_name,
            input_features=json.dumps(payload),
            risk_percentage=risk_pct,
            risk_level=risk_level,
            source=source
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        logger.error("audit_log_failed", error=str(e), model=model_name)"""

new_log_def = """def log_prediction_to_db(db: Session, request: Request, model_name: str, payload: dict, risk_pct: float, risk_level: str, source: str, current_user: User = None):
    \"\"\"Log prediction result to PredictionResult table.\"\"\"
    try:
        risk_score = int(risk_pct)
        upload_id = getattr(request.state, "upload_id", None)
        
        log_entry = PredictionResult(
            user_id=current_user.id if current_user else None,
            disease_type=model_name,
            input_features=payload,
            risk_score=risk_score,
            risk_level=risk_level,
            model_version="v3.0.0",
            upload_id=upload_id
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        logger.error("audit_log_failed", error=str(e), model=model_name)"""

content = content.replace(old_log_def, new_log_def)

# 3. Add current_user to endpoints that have db: Session = Depends(get_db)
# Many endpoints have this format, let's just do a regex replace for the parameter list end.
content = re.sub(
    r"db: Session = Depends\(get_db\)\n\):",
    "db: Session = Depends(get_db),\n    current_user: User = Depends(get_current_user)\n):",
    content
)

# 4. Update log_prediction_to_db calls to pass current_user
content = re.sub(
    r"log_prediction_to_db\(db, request, (.*?)\)",
    r"log_prediction_to_db(db, request, \1, current_user)",
    content
)

# 5. Fix endpoints that don't have db: Session but need current_user and DB logging.
# Wait, let's look at api_predict_diabetes
api_pattern = r"(async def api_predict_\w+\(request: Request, data: [^\)]+\)):"
api_repl = r"\1, current_user: User = Depends(get_current_user), db: Session = Depends(get_db):"
content = re.sub(api_pattern, api_repl, content)

# But api_predict_* don't call log_prediction_to_db. I need to add it.
# It's better to just write the replacement for api_predict_* manually.

with open("backend/app/main.py", "w") as f:
    f.write(content)
print("Patch applied")
