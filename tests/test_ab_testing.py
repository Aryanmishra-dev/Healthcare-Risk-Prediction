import pytest
from app.ab_testing import ab_router, ABRouter

def dummy_champion(**kwargs):
    return {"risk_percentage": 10.0, "risk_level": "Low"}

def dummy_challenger(**kwargs):
    return {"risk_percentage": 20.0, "risk_level": "Moderate"}

@pytest.fixture
def clean_router():
    """Return a fresh ABRouter instance for each test."""
    return ABRouter()

def test_register_experiment(clean_router):
    clean_router.register("test_model", dummy_champion, dummy_challenger, traffic_pct=20)
    assert "test_model" in clean_router.active_experiments

def test_register_experiment_invalid_pct(clean_router):
    with pytest.raises(ValueError, match="traffic_pct must be between 0 and 100"):
        clean_router.register("test_model", dummy_champion, dummy_challenger, traffic_pct=150)

def test_route_uses_deterministic_hashing(clean_router):
    clean_router.register("test_model", dummy_champion, dummy_challenger, traffic_pct=50)
    
    # Send the same request_id twice -> should give identical variants
    req1_id = "user123"
    result1, variant1 = clean_router.route("test_model", request_id=req1_id)
    result2, variant2 = clean_router.route("test_model", request_id=req1_id)
    
    assert variant1 == variant2
    assert result1["risk_percentage"] == result2["risk_percentage"]

def test_route_unregistered_model(clean_router):
    with pytest.raises(KeyError, match="No A/B experiment registered"):
        clean_router.route("unknown_model")

def test_get_summary(clean_router):
    clean_router.register("test_model", dummy_champion, dummy_challenger, traffic_pct=50)
    
    # Mocking different request_ids to hopefully hit both champion and challenger
    # We will just route 10 times with different ids
    for i in range(10):
        clean_router.route("test_model", request_id=f"user_{i}")
        
    summary = clean_router.get_summary("test_model")
    assert summary["experiment"] == "test_model"
    assert summary["traffic_pct"] == 50
    assert summary["total_requests"] == 10
    
    assert "count" in summary["champion"]
    assert "count" in summary["challenger"]

def test_get_summary_unregistered(clean_router):
    summary = clean_router.get_summary("unknown_model")
    assert "error" in summary
