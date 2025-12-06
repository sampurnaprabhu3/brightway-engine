# api_service.py
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import traceback
import uvicorn
import logging

# calculators (aluminium, copper already present)
from aluminium_calculators import compute_combined_lca as compute_combined_lca_aluminium
from copper_calculators import compute_combined_lca_copper

# steel calculator (new)
# NOTE: keep this import optional-safe in case dev wants to run without steel module
try:
    from steel_calculators import compute_combined_lca_steel
    _STEEL_AVAILABLE = True
except Exception:
    compute_combined_lca_steel = None
    _STEEL_AVAILABLE = False

logger = logging.getLogger("metal-lca-engine")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Metal LCA Engine", version="0.2.0")


# -----------------------
# Pydantic request models
# (keeps fields optional to accept partial/combined stage payloads)
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


class AluminiumRequest(BaseModel):
    projectId: str
    scenarioId: str
    metal: str
    route: Optional[str] = None
    stage: Optional[str] = None
    functionalUnit_kg: Optional[float] = 1.0
    recycling_rate: Optional[float] = 0.0
    primary_cost_per_kg: Optional[float] = None
    recycled_cost_per_kg: Optional[float] = None
    inputs: Optional[StageInputs] = None


class CopperRequest(BaseModel):
    projectId: str
    scenarioId: str
    metal: str
    route: Optional[str] = None
    stage: Optional[str] = None
    functionalUnit_kg: Optional[float] = 1000.0
    recycling_rate: Optional[float] = 0.0
    inputs: Optional[StageInputs] = None


# -----------------------
# Helpers
# -----------------------
def _validate_json_payload(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400, detail="Payload must be a JSON object")
    return payload


# -----------------------
# Endpoints
# -----------------------

@app.get("/")
async def root():
    return {"message": "Metal LCA Engine running", "version": app.version}


@app.post("/aluminium/run")
async def run_aluminium(request: Request) -> JSONResponse:
    try:
        payload: Dict[str, Any] = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON body: {e}")

    _validate_json_payload(payload)
    try:
        logger.info("Dispatching LCA for metal=aluminium")
        result = compute_combined_lca_aluminium(payload)
        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Server error running aluminium LCA: {e}")


@app.post("/copper/run")
async def run_copper(request: Request) -> JSONResponse:
    try:
        payload: Dict[str, Any] = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON body: {e}")

    _validate_json_payload(payload)
    try:
        logger.info("Dispatching LCA for metal=copper")
        result = compute_combined_lca_copper(payload)
        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Server error running copper LCA: {e}")


# NEW: steel endpoint
@app.post("/steel/run")
async def run_steel(request: Request) -> JSONResponse:
    if not _STEEL_AVAILABLE:
        raise HTTPException(
            status_code=500, detail="Steel calculator module not available on server")

    try:
        payload: Dict[str, Any] = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON body: {e}")

    _validate_json_payload(payload)
    try:
        logger.info("Dispatching LCA for metal=steel")
        result = compute_combined_lca_steel(payload)
        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Server error running steel LCA: {e}")


# -----------------------
# Run server for local debug (if you run python api_service.py)
# -----------------------
if __name__ == "__main__":
    # default bind for development
    uvicorn.run("api_service:app", host="0.0.0.0", port=8000, reload=True)
