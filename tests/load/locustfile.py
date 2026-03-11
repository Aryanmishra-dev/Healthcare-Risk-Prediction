"""
Locust load test for Healthcare Risk Prediction API.

Run:
    locust -f tests/load/locustfile.py --host http://localhost:8000

Web UI at http://localhost:8089 by default.
Headless:
    locust -f tests/load/locustfile.py --host http://localhost:8000 \
           --users 50 --spawn-rate 5 --run-time 60s --headless
"""

import random

from locust import HttpUser, between, task


class HealthPredictUser(HttpUser):
    """Simulates a user interacting with the Healthcare Risk Prediction API."""

    wait_time = between(0.5, 2.0)

    # ── Page loads ────────────────────────────────────────────────────────
    @task(3)
    def homepage(self):
        self.client.get("/")

    @task(1)
    def api_root(self):
        self.client.get("/api")

    @task(1)
    def v1_root(self):
        self.client.get("/api/v1/")

    @task(1)
    def health_check(self):
        self.client.get("/healthz")

    @task(1)
    def model_registry(self):
        self.client.get("/api/v1/models")

    # ── Diabetes predictions ──────────────────────────────────────────────
    @task(5)
    def predict_diabetes_json(self):
        self.client.post("/api/v1/predict/diabetes", json={
            "age": random.randint(1, 13),
            "bmi": round(random.uniform(15, 45), 1),
            "bp": random.randint(0, 1),
            "cholesterol": random.randint(0, 1),
            "smoker": random.randint(0, 1),
            "activity": random.randint(0, 1),
            "health": random.randint(1, 5),
            "mental": random.randint(0, 30),
        })

    # ── Heart disease predictions ─────────────────────────────────────────
    @task(5)
    def predict_heart_json(self):
        self.client.post("/api/v1/predict/heart", json={
            "age": random.randint(1, 13),
            "sex": random.randint(0, 1),
            "bmi": round(random.uniform(15, 45), 1),
            "high_bp": random.randint(0, 1),
            "high_chol": random.randint(0, 1),
            "smoker": random.randint(0, 1),
            "phys_activity": random.randint(0, 1),
            "fruits": random.randint(0, 1),
            "veggies": random.randint(0, 1),
            "heavy_drinker": random.randint(0, 1),
            "gen_health": random.randint(1, 5),
            "ment_health": random.randint(0, 30),
            "phys_health": random.randint(0, 30),
            "diabetes": random.randint(0, 1),
        })

    # ── Lung cancer predictions ───────────────────────────────────────────
    @task(5)
    def predict_lung_json(self):
        self.client.post("/api/v1/predict/lung", json={
            "age": random.randint(18, 90),
            "gender": random.randint(0, 1),
            "smoking": random.randint(0, 1),
            "yellow_fingers": random.randint(0, 1),
            "chronic_disease": random.randint(0, 1),
            "fatigue": random.randint(0, 1),
            "wheezing": random.randint(0, 1),
            "shortness_of_breath": random.randint(0, 1),
        })

    # ── Metrics endpoint ──────────────────────────────────────────────────
    @task(1)
    def prometheus_metrics(self):
        self.client.get("/metrics")
