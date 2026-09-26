"""
FastAPI service for the corrected-calcium calculator and auxiliary audit components.
"""
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from corrected_calcium import CorrectedCalciumEngine
from .base import AuditLogger, SecurityException
from .models import SystemTaskPayload
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="Corrected Calcium Calculator API",
    description="Local API for corrected-calcium calculations and auxiliary audit components.",
    version="1.0.0",
)


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)


class CalculateRequest(BaseModel):
    measured_total_calcium_mg_dl: float
    albumin_g_dl: float = 4.0
    total_protein_g_dl: Optional[float] = None
    phosphate_mg_dl: Optional[float] = None


@app.get("/health")
def health():
    return {
        "status": "HEALTHY",
        "service": "corrected-calcium-calculator",
        "version": app.version,
    }


@app.get("/metrics")
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "system_status": "NOMINAL",
    }


@app.post("/api/calculate")
def api_calculate(payload: CalculateRequest):
    try:
        result = CorrectedCalciumEngine.calculate(
            measured_total_calcium_mg_dl=payload.measured_total_calcium_mg_dl,
            albumin_g_dl=payload.albumin_g_dl,
            total_protein_g_dl=payload.total_protein_g_dl,
            phosphate_mg_dl=payload.phosphate_mg_dl,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result.to_dict()


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    try:
        dossier = supervisor.process_task(payload)
    except SecurityException as exc:
        raise HTTPException(status_code=400, detail="Payload blocked by identifier screening.") from exc
    return dossier.to_dict()


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        answer = supervisor.query_supervisory_chat(req.query)
    except SecurityException as exc:
        raise HTTPException(status_code=400, detail="Query blocked by identifier screening.") from exc
    return {"response": answer}


@app.get("/api/audit/logs")
def api_audit_logs():
    return {
        "audit_trail": AuditLogger.get_trail(),
        "verified": AuditLogger.verify_integrity(),
    }
