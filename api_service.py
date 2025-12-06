# api_service.py
from typing import Dict, Any, Optional, Callable
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import traceback
import uvicorn
import logging

# Import calculators - ensure these names exist in the respective modules
from aluminium_calculators import compute_combined_lca as compute_combined_lca_aluminium
from copper_calculators import compute_combined_lca_copper

# Configure a simple logger (uvicorn logs are also produced)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("metal-lca-engine")

app = FastAPI(title="Metal LCA Engine", version="0.2.0")


# -----------------------
# Pydantic request models
# -----------------------

class MiningInputs(BaseModel):
    ore_input_kg: Optional[float] = None
    ore_grade_percent: Optional[float] = None
    process_recovery: Optional[float] = None
    electricity_kWh: Optional[float] = None
    fuel_diesel_L: Optional[float] = None
    fuel_heavyOil_L: Optional[float] = None
    fuel_naturalGas_MJ: Optional[float] = None
    freshwater_m3: Optional[float] = None
    process_water_m3: Optional[float] = None
    water_returned_m3: Optional[float] = None
    auxiliary_materials_kg: Optional[float] = None
    co_product_outputs_total_kg: Optional[float] = None


class ExtractionInputs(BaseModel):
    ore_input_kg: Optional[float] = None
    fraction_alumina: Optional[float] = None
    fraction_metal: Optional[float] = None
    reduction_efficiency: Optional[float] = None
    electricity_kWh: Optional[float] = None
    fuel_coal_kg: Optional[float] = None
    fuel_naturalGas_MJ: Optional[float] = None
    anode_carbon_kg: Optional[float] = None
    anode_effect_minutes: Optional[float] = None
    CF4_factor: Optional[float] = None
    C2F6_factor: Optional[float] = None
    impurity_fraction: Optional[float] = None
    anode_residue_kg: Optional[float] = None


class ManufacturingInputs(BaseModel):
    metal_input_kg: Optional[float] = None
    process_yield: Optional[float] = None
    electricity_kWh: Optional[float] = None
    fuel_naturalGas_MJ: Optional[float] = None
    lubricants_kg: Optional[float] = None
    auxiliary_materials_kg: Optional[float] = None
    freshwater_m3: Optional[float] = None
    process_water_m3: Optional[float] = None
    cooling_water_returned: Optional[float] = None
    scrap_kg: Optional[float] = None


class StageInputs(BaseModel):
    mining: Optional[MiningInputs] = None
    extraction: Optional[ExtractionInputs] = None
    manufacturing: Optional[ManufacturingInputs] = None


class GenericRequest(BaseModel):
    projectId: str
    scenarioId: str
    metal: str
    route: Optional[str] = None
    stage: Optional[str] = None
    functionalUnit_kg: Optional[float] = 1.0
    recycling_rate: Optional[float] = 0.0
    inputs: Optional[StageInputs] = None


# -----------------------
# Helper: dispatch table
# -----------------------
# Map canonical metal string -> (callable, description)
CALCULATOR_MAP: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    "aluminium": compute_combined_lca_aluminium,
    "aluminum": compute_combined_lca_aluminium,  # alternate spelling
    "copper": compute_combined_lca_copper,
    # add more metals here: "iron": compute_combined_lca_iron, ...
}


def _dispatch_to_calculator(metal: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Call the appropriate calculator based on metal string (case-insensitive)."""
    if not isinstance(metal, str) or not metal:
        raise ValueError("metal must be a non-empty string")
    key = metal.strip().lower()
    func = CALCULATOR_MAP.get(key)
    if func is None:
        raise KeyError(f"Unsupported metal '{metal}'")
    # call calculator - calculators should accept raw dict payload
    return func(payload)


# -----------------------
# Endpoints (existing / compatibility)
# -----------------------

@app.get("/")
async def root():
    return {"message": "Metal LCA Engine running", "version": app.version}


@app.post("/metal/run")
async def run_metal(request: Request) -> JSONResponse:
    """
    Generic endpoint that dispatches to the correct metal calculator based on payload['metal'].
    Accepts the same combined payload format used previously.
    """
    try:
        payload: Dict[str, Any] = await request.json()
    except Exception as e:
        logger.exception("Invalid JSON payload")
        raise HTTPException(status_code=400, detail=f"Invalid JSON body: {e}")

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400, detail="Payload must be a JSON object")

    metal = (payload.get("metal") or "").strip()
    if not metal:
        raise HTTPException(
            status_code=400, detail="Missing 'metal' in payload")

    try:
        logger.info("Dispatching LCA for metal=%s", metal)
        result = _dispatch_to_calculator(metal, payload)
        return JSONResponse(status_code=200, content=result)
    except KeyError as ke:
        raise HTTPException(status_code=400, detail=str(ke))
    except Exception as e:
        logger.exception("Error running LCA for metal=%s", metal)
        raise HTTPException(
            status_code=500, detail=f"Server error running {metal} LCA: {e}")


@app.post("/aluminium/run")
async def run_aluminium(request: Request) -> JSONResponse:
    """Backwards-compatible aluminium endpoint - calls aluminium calculator directly."""
    try:
        payload: Dict[str, Any] = await request.json()
    except Exception as e:
        logger.exception("Invalid JSON payload for aluminium")
        raise HTTPException(status_code=400, detail=f"Invalid JSON body: {e}")

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400, detail="Payload must be a JSON object")

    try:
        logger.info("Running aluminium LCA (compat endpoint)")
        result = compute_combined_lca_aluminium(payload)
        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        logger.exception("Server error running aluminium LCA")
        raise HTTPException(
            status_code=500, detail=f"Server error running aluminium LCA: {e}")


@app.post("/copper/run")
async def run_copper(request: Request) -> JSONResponse:
    """Backwards-compatible copper endpoint - calls copper calculator directly."""
    try:
        payload: Dict[str, Any] = await request.json()
    except Exception as e:
        logger.exception("Invalid JSON payload for copper")
        raise HTTPException(status_code=400, detail=f"Invalid JSON body: {e}")

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400, detail="Payload must be a JSON object")

    try:
        logger.info("Running copper LCA (compat endpoint)")
        result = compute_combined_lca_copper(payload)
        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        logger.exception("Server error running copper LCA")
        raise HTTPException(
            status_code=500, detail=f"Server error running copper LCA: {e}")


# -----------------------
# Run server for local debug
# -----------------------
if __name__ == "__main__":
    # For local dev you can run `python api_service.py` to start
    uvicorn.run("api_service:app", host="0.0.0.0", port=8000, reload=True)
