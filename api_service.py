# api_service.py
"""
API service for Metal LCA engine (FastAPI).
- POST /aluminium/run accepts AluminiumRequest and returns AluminiumResponse JSON
- Uses aluminium_calculators.calculate_mining for mining-stage calculations
- Attempts to connect to Brightway (optional); failure to connect is tolerated.
"""

from typing import Dict, Optional, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
import os

# Try to import Brightway (optional). If Brightway not configured, we continue.
try:
    import brightway2 as bw  # noqa: F401
    BRIGHTWAY_AVAILABLE = True
except Exception:
    BRIGHTWAY_AVAILABLE = False

# Import the mining calculator (expects aluminium_calculators.py near this file)
try:
    from aluminium_calculators import calculate_mining
except Exception as e:
    # If missing, raise a clear error later when called.
    calculate_mining = None
    logging.warning(
        "aluminium_calculators.calculate_mining not available: %s", e)

app = FastAPI(title="Metal LCA Engine", version="0.1.0")

# ---------------------------
# Pydantic models
# ---------------------------


class AluminiumRequest(BaseModel):
    projectId: str
    scenarioId: str
    metal: str                      # e.g. "aluminium"
    route: str                      # e.g. "primary_global"
    stage: str                      # "mining" | "extraction" | "manufacturing" | "full_chain"
    functionalUnit_kg: float = 1.0  # mass in kg
    recycling_rate: float = 0.0     # between 0 and 1
    primary_cost_per_kg: float = 0.0
    recycled_cost_per_kg: float = 0.0
    # optional stage-specific numeric inputs
    inputs: Optional[Dict[str, Any]] = None


class AluminiumResponse(BaseModel):
    metadata: Dict[str, Any]
    functionalUnit_kg: float
    gwp_kgCO2e: float
    stages: Dict[str, Any]
    costs: Dict[str, Any]


# ---------------------------
# Helper functions
# ---------------------------

def try_connect_brightway():
    """
    Optional: attempt a Brightway connection (safe — doesn't fail the API).
    Caller should check BRIGHTWAY_AVAILABLE before using bw features.
    """
    if not BRIGHTWAY_AVAILABLE:
        return {"available": False, "message": "brightway2 not installed/configured"}
    try:
        # If the user has BRIGHTWAY2_DIR env var set, Brightway will use it.
        dbs = bw.databases
        # return a brief listing
        return {"available": True, "databases": list(dbs)}
    except Exception as exc:
        return {"available": False, "message": str(exc)}


def build_basic_response(projectId: str, scenarioId: str, req: AluminiumRequest):
    """
    Basic response template with metadata fields.
    """
    meta = {
        "engine": "brightway" if BRIGHTWAY_AVAILABLE else "local",
        "projectId": projectId,
        "scenarioId": scenarioId,
        "metal": req.metal,
        "route": req.route,
        "stage": req.stage,
        "functionalUnit_kg": req.functionalUnit_kg,
    }
    if BRIGHTWAY_AVAILABLE:
        bw_info = try_connect_brightway()
        meta["brightway"] = bw_info
    return meta


# ---------------------------
# FastAPI endpoints
# ---------------------------

@app.get("/", tags=["health"])
def root():
    """Simple root health-check endpoint."""
    return {"message": "Metal LCA engine running", "version": app.version}


@app.post("/aluminium/run", response_model=AluminiumResponse, tags=["aluminium"])
def run_aluminium(req: AluminiumRequest):
    """
    Run Aluminium LCA scenario.
    - expects optional `inputs` dict inside request containing numeric inputs for the stage.
    - currently supports 'mining' stage; 'full_chain' runs mining for quick testing (extendable).
    """
    # Validate: ensure our mining calculator exists
    if calculate_mining is None:
        raise HTTPException(
            status_code=500, detail="Mining calculator module not found on server.")

    # Prepare response metadata
    metadata = build_basic_response(req.projectId, req.scenarioId, req)

    # Extract the stage-specific inputs (optional)
    request_inputs = req.inputs or {}

    # Stage handling
    try:
        if req.stage == "mining":
            # Run mining calculator
            mining_result = calculate_mining(request_inputs)
            gwp_kgCO2e = mining_result.get(
                "emissions_air", {}).get("co2_kg", 0.0)

            costs = compute_costs_basic(req)  # basic cost placeholder

            resp = {
                "metadata": metadata,
                "functionalUnit_kg": req.functionalUnit_kg,
                "gwp_kgCO2e": gwp_kgCO2e,
                "stages": {"mining": mining_result},
                "costs": costs,
            }
            return resp

        elif req.stage == "full_chain":
            # For now run mining only (fast smoke-test). We'll extend extraction + manufacturing next.
            mining_result = calculate_mining(request_inputs)
            gwp_kgCO2e = mining_result.get(
                "emissions_air", {}).get("co2_kg", 0.0)

            costs = compute_costs_basic(req)

            resp = {
                "metadata": metadata,
                "functionalUnit_kg": req.functionalUnit_kg,
                "gwp_kgCO2e": gwp_kgCO2e,
                "stages": {"mining": mining_result},
                "costs": costs,
            }
            return resp

        elif req.stage in ("extraction", "manufacturing"):
            # Placeholder — we haven't implemented these calculators yet
            raise HTTPException(
                status_code=501, detail=f"Stage '{req.stage}' not yet implemented on server.")

        else:
            raise HTTPException(
                status_code=400, detail=f"Unknown stage '{req.stage}'")

    except HTTPException:
        # re-raise FastAPI HTTPExceptions
        raise
    except Exception as exc:
        logging.exception("Error while running stage")
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------
# Simple cost function (placeholder)
# ---------------------------

def compute_costs_basic(req: AluminiumRequest) -> Dict[str, float]:
    """
    Compute a simple cost breakdown using the provided cost per kg values and recycling_rate.
    - primary_cost_per_kg and recycled_cost_per_kg must be provided in request, else 0.
    - returns dict with primary/recycled/total cost components (per functional unit).
    """
    try:
        primary_cost = float(req.primary_cost_per_kg or 0.0)
        recycled_cost = float(req.recycled_cost_per_kg or 0.0)
        r = float(req.recycling_rate or 0.0)
        # blended cost per kg: (1 - r) * primary + r * recycled
        blended_per_kg = (1.0 - r) * primary_cost + r * recycled_cost
        total_cost = blended_per_kg * float(req.functionalUnit_kg or 1.0)
        return {
            "primary_material_fraction": 1.0 - r,
            "recycled_material_fraction": r,
            "primary_cost_component": (1.0 - r) * primary_cost * req.functionalUnit_kg,
            "recycled_cost_component": r * recycled_cost * req.functionalUnit_kg,
            "total_cost": total_cost,
            "blended_cost_per_kg": blended_per_kg,
        }
    except Exception as e:
        logging.exception("Error computing costs")
        return {"error": str(e)}


# ---------------------------
# Run app (optional guard for direct run)
# ---------------------------
if __name__ == "__main__":
    import uvicorn
    # When run directly: uvicorn api_service:app --reload
    uvicorn.run("api_service:app", host="127.0.0.1", port=8000, reload=True)
