from datetime import datetime
import uuid
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict, Field

class ModelVersionBase(BaseModel):
    model_name: str
    model_version: str
    disease: str
    framework: str
    algorithm: str
    training_dataset: Optional[str] = None
    dataset_version: Optional[str] = None
    feature_schema_version: Optional[str] = None
    hyperparameters: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None
    model_path: Optional[str] = None
    mlflow_run_id: Optional[str] = None
    mlflow_model_uri: Optional[str] = None
    checksum: Optional[str] = None

class ModelVersionCreate(ModelVersionBase):
    pass

class ModelVersionUpdate(BaseModel):
    status: Optional[str] = None
    retired_at: Optional[datetime] = None
    deployed_at: Optional[datetime] = None

class ModelVersionResponse(ModelVersionBase):
    id: uuid.UUID
    status: str
    training_date: Optional[datetime] = None
    deployed_at: Optional[datetime] = None
    retired_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ModelComparisonResponse(BaseModel):
    model_name: str
    versions: List[ModelVersionResponse]
    metrics_diff: Dict[str, Any]
