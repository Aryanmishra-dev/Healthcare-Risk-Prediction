import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import Request
from backend.app.services.prediction_pipeline import prediction_pipeline

@pytest.mark.anyio
async def test_prediction_pipeline_success():
    req = MagicMock(spec=Request)
    
    async def mock_predict(request, **kwargs):
        return {"risk_percentage": 10.0, "risk_level": "Low"}
        
    def mock_build_features(**kwargs):
        return "features_df"
        
    result = await prediction_pipeline.run_pipeline(
        request=req,
        disease="diabetes",
        input_data={"age": 30},
        predict_func=mock_predict,
        build_features_func=mock_build_features
    )
    
    assert "risk_percentage" in result
    assert "risk_level" in result
    assert "model_version" in result
    assert "processing_time_ms" in result
    assert "shap_values" in result

@pytest.mark.anyio
async def test_prediction_pipeline_heart_disease():
    req = MagicMock(spec=Request)
    
    async def mock_predict(request, **kwargs):
        return {"risk_percentage": 20.0, "risk_level": "Moderate"}
        
    def mock_build_features(**kwargs):
        return "features_df"
        
    result = await prediction_pipeline.run_pipeline(
        request=req,
        disease="heart_disease",
        input_data={"age": 50},
        predict_func=mock_predict,
        build_features_func=mock_build_features
    )
    
    assert result["risk_level"] == "Moderate"

@pytest.mark.anyio
async def test_prediction_pipeline_lung_cancer():
    req = MagicMock(spec=Request)
    
    async def mock_predict(request, **kwargs):
        return {"risk_percentage": 80.0, "risk_level": "High"}
        
    def mock_build_features(**kwargs):
        return "features_df"
        
    result = await prediction_pipeline.run_pipeline(
        request=req,
        disease="lung_cancer",
        input_data={"age": 70},
        predict_func=mock_predict,
        build_features_func=mock_build_features
    )
    
    assert result["risk_level"] == "High"

@pytest.mark.anyio
async def test_prediction_pipeline_exception():
    req = MagicMock(spec=Request)
    
    async def mock_predict(request, **kwargs):
        raise ValueError("Model error")
        
    with pytest.raises(ValueError):
        await prediction_pipeline.run_pipeline(
            request=req,
            disease="diabetes",
            input_data={"age": 30},
            predict_func=mock_predict,
            build_features_func=None
        )

@pytest.mark.anyio
async def test_prediction_pipeline_shap_exception():
    req = MagicMock(spec=Request)
    
    async def mock_predict(request, **kwargs):
        return {"risk_percentage": 10.0, "risk_level": "Low"}
        
    def mock_build_features_error(**kwargs):
        raise RuntimeError("SHAP error")
        
    # Should catch the error and not raise
    result = await prediction_pipeline.run_pipeline(
        request=req,
        disease="diabetes",
        input_data={"age": 30},
        predict_func=mock_predict,
        build_features_func=mock_build_features_error
    )
    
    assert result["shap_values"] is None
