"""FastAPI inference service for NetGuard-AI."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from netguard.config import get_settings
from netguard.predict import clear_model_cache, load_model_bundle, predict_batch


class FlowFeatures(BaseModel):
    """One network connection / flow in NSL-KDD feature form."""

    duration: float = 0
    protocol_type: str = Field(..., examples=["tcp"])
    service: str = Field(..., examples=["http"])
    flag: str = Field(..., examples=["SF"])
    src_bytes: float = 0
    dst_bytes: float = 0
    land: int = 0
    wrong_fragment: int = 0
    urgent: int = 0
    hot: int = 0
    num_failed_logins: int = 0
    logged_in: int = 0
    num_compromised: int = 0
    root_shell: int = 0
    su_attempted: int = 0
    num_root: int = 0
    num_file_creations: int = 0
    num_shells: int = 0
    num_access_files: int = 0
    num_outbound_cmds: int = 0
    is_host_login: int = 0
    is_guest_login: int = 0
    count: float = 0
    srv_count: float = 0
    serror_rate: float = 0
    srv_serror_rate: float = 0
    rerror_rate: float = 0
    srv_rerror_rate: float = 0
    same_srv_rate: float = 0
    diff_srv_rate: float = 0
    srv_diff_host_rate: float = 0
    dst_host_count: float = 0
    dst_host_srv_count: float = 0
    dst_host_same_srv_rate: float = 0
    dst_host_diff_srv_rate: float = 0
    dst_host_same_src_port_rate: float = 0
    dst_host_srv_diff_host_rate: float = 0
    dst_host_serror_rate: float = 0
    dst_host_srv_serror_rate: float = 0
    dst_host_rerror_rate: float = 0
    dst_host_srv_rerror_rate: float = 0

    model_config = {"extra": "ignore"}


class PredictRequest(BaseModel):
    """Single flow or a batch of flows."""

    flows: list[FlowFeatures] = Field(..., min_length=1, max_length=512)


class PredictionItem(BaseModel):
    attack_category: str
    is_attack: bool
    anomaly_flag: bool
    anomaly_score: float
    confidence: float | None = None
    class_probabilities: dict[str, float] | None = None


class PredictResponse(BaseModel):
    count: int
    predictions: list[PredictionItem]


class HealthResponse(BaseModel):
    status: str
    project: str
    version: str
    models_loaded: bool
    supervised_model: str
    anomaly_model: str


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Warm the model cache at startup so the first request is fast."""
    try:
        load_model_bundle()
    except FileNotFoundError:
        # Allow the app to start; endpoints will return 503 until artifacts exist.
        pass
    yield
    clear_model_cache()


settings = get_settings()
app = FastAPI(
    title=settings.project.name,
    description=settings.project.description,
    version=settings.project.version,
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness + whether model artifacts loaded successfully."""
    models_loaded = False
    try:
        load_model_bundle()
        models_loaded = True
    except FileNotFoundError:
        models_loaded = False

    return HealthResponse(
        status="ok" if models_loaded else "degraded",
        project=settings.project.name,
        version=settings.project.version,
        models_loaded=models_loaded,
        supervised_model=settings.api.model_name,
        anomaly_model=settings.api.anomaly_model_name,
    )


@app.get("/metrics")
def metrics() -> dict[str, Any]:
    """Return evaluation metrics saved during training."""
    try:
        bundle = load_model_bundle()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if not bundle.metrics:
        raise HTTPException(
            status_code=404,
            detail="metrics.json not found. Re-run scripts/train.py.",
        )
    return bundle.metrics


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest) -> PredictResponse:
    """Classify flow feature vectors with supervised + anomaly models."""
    try:
        bundle = load_model_bundle()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    records = [flow.model_dump() for flow in request.flows]
    raw = predict_batch(records, bundle=bundle)
    predictions = [PredictionItem.model_validate(item) for item in raw]
    return PredictResponse(count=len(predictions), predictions=predictions)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "NetGuard-AI inference API",
        "docs": "/docs",
        "health": "/health",
        "predict": "/predict",
        "metrics": "/metrics",
    }
