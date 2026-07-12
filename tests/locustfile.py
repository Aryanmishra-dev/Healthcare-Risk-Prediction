import random
from locust import HttpUser, task, between

class HealthPredictUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # Setup session/auth if needed (mocked here or use public endpoints)
        self.client.headers.update({"Content-Type": "application/json"})

    @task(3)
    def check_health(self):
        self.client.get("/healthz")

    @task(5)
    def predict_diabetes(self):
        payload = {
            "Pregnancies": random.randint(0, 10),
            "Glucose": random.randint(70, 200),
            "BloodPressure": random.randint(60, 120),
            "SkinThickness": random.randint(10, 50),
            "Insulin": random.randint(15, 300),
            "BMI": round(random.uniform(18.0, 40.0), 1),
            "DiabetesPedigreeFunction": round(random.uniform(0.1, 1.5), 3),
            "Age": random.randint(21, 80)
        }
        self.client.post("/api/v1/predict/diabetes", json=payload)

    @task(2)
    def predict_heart(self):
        payload = {
            "Age": random.randint(30, 80),
            "Sex": random.choice(["M", "F"]),
            "ChestPainType": random.choice(["ATA", "NAP", "ASY", "TA"]),
            "RestingBP": random.randint(90, 180),
            "Cholesterol": random.randint(100, 300),
            "FastingBS": random.choice([0, 1]),
            "RestingECG": random.choice(["Normal", "ST", "LVH"]),
            "MaxHR": random.randint(80, 200),
            "ExerciseAngina": random.choice(["Y", "N"]),
            "Oldpeak": round(random.uniform(0.0, 5.0), 1),
            "ST_Slope": random.choice(["Up", "Flat", "Down"])
        }
        self.client.post("/api/v1/predict/heart", json=payload)
