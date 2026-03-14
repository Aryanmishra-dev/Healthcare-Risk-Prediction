import re

with open("app/main.py", "r") as f:
    code = f.read()

# 1. Update v1 and api predict endpoints to use Request and await
code = code.replace(
    'def api_predict_diabetes(data: PredictionRequest):',
    'async def api_predict_diabetes(request: Request, data: PredictionRequest):'
).replace(
    'result = predict(',
    'result = await predict(request=request,'
).replace(
    'def api_predict_heart(data: HeartDiseasePredictionRequest):',
    'async def api_predict_heart(request: Request, data: HeartDiseasePredictionRequest):'
).replace(
    'result = predict_heart_disease(',
    'result = await predict_heart_disease(request=request,'
).replace(
    'def api_predict_lung(data: LungCancerPredictionRequest):',
    'async def api_predict_lung(request: Request, data: LungCancerPredictionRequest):'
).replace(
    'result = predict_lung_cancer(',
    'result = await predict_lung_cancer(request=request,'
)

code = code.replace(
    'def v1_predict_diabetes(request: Request, data: PredictionRequest, db: Session = Depends(get_db)):',
    'async def v1_predict_diabetes(request: Request, data: PredictionRequest, db: Session = Depends(get_db)):\n'
).replace(
    'def v1_predict_heart(request: Request, data: HeartDiseasePredictionRequest, db: Session = Depends(get_db)):',
    'async def v1_predict_heart(request: Request, data: HeartDiseasePredictionRequest, db: Session = Depends(get_db)):\n'
).replace(
    'def v1_predict_lung(request: Request, data: LungCancerPredictionRequest, db: Session = Depends(get_db)):',
    'async def v1_predict_lung(request: Request, data: LungCancerPredictionRequest, db: Session = Depends(get_db)):\n'
)

# 2. Add dependencies to JSON API endpoints for Rate Limiter
code = code.replace('@app.post("/api/predict", response_model=PredictionResponse)', '@app.post("/api/predict", response_model=PredictionResponse, dependencies=[Depends(RateLimiter(times=RATE_LIMIT, seconds=60))])')
code = code.replace('@app.post("/api/predict-heart", response_model=PredictionResponse)', '@app.post("/api/predict-heart", response_model=PredictionResponse, dependencies=[Depends(RateLimiter(times=RATE_LIMIT, seconds=60))])')
code = code.replace('@app.post("/api/predict-lung", response_model=PredictionResponse)', '@app.post("/api/predict-lung", response_model=PredictionResponse, dependencies=[Depends(RateLimiter(times=RATE_LIMIT, seconds=60))])')

with open("app/main.py", "w") as f:
    f.write(code)

