import re

with open("app/main.py", "r") as f:
    code = f.read()

old_lung_explain = """@v1.post("/explain/lung")
def v1_explain_lung(request: Request, data: LungCancerPredictionRequest, db: Session = Depends(get_db)):"""

new_lung_explain = """@v1.post("/explain/lung")
async def v1_explain_lung(request: Request, data: LungCancerPredictionRequest, db: Session = Depends(get_db)):"""
code = code.replace(old_lung_explain, new_lung_explain)

with open("app/main.py", "w") as f:
    f.write(code)

