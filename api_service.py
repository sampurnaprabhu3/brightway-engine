# api_service.py
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import traceback
import uvicorn
import logging

logger = logging.getLogger("metal-lca-engine")
logging.basicConfig(level=logging.INFO,
                    format="%(levelname)s:%(name)s:%(message)s")

# Try to import calculators. If a module is missing, we set the reference to None and report at runtime.
try:
    from aluminium_calculators import compute_combined_lca as compute_combined_lca_aluminium
except Exception as e:
    compute_combined_lca_aluminium = None
    logger.warning(
        "aluminium_calculators.compute_combined_lca not available: %s", e)

try:
    # your copper calculator function name (you used compute_combined_lca_copper earlier)
    from copper_calculators import compute_combined_lca_copper
except Exception as e:
    compute_combined_lca_copper = None
    logger.warning(
        "copper_calculators.compute_combined_lca_copper not available: %s", e)

try:
    from steel_calculators import compute_combined_lca_steel
except Exception as e:
    compute_combined_lca_steel = None
    logger.warning(
        "steel_calculators.compute_combined_lca_steel not available: %s", e)

try:
    from tin_calculators import compute_combined_lca_tin
except Exception as e:
    compute_combined_lca_tin = None
    logger.warning(
        "tin_calculators.compute_combined_lca_tin not available: %s", e)

try:
    from lithium_calculators import compute_combined_lca_lithium
except Exception as e:
    compute_combined_lca_lithium = None
    logger.warning(
        "lithium_calculators.compute_combined_lca_lithium not available: %s", e)


app = FastAPI(title="Metal LCA Engine", version="0.2.0")


# -----------------------
# Pydantic models (kept simple/optional to accept partial stage payloads)
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


class MetalRequest(BaseModel):
    projectId: str
    scenarioId: str
    metal: str
    route: Optional[str] = None
    stage: Optional[str] = None
    functionalUnit_kg: Optional[float] = 1.0
    recycling_rate: Optional[float] = 0.0
    inputs: Optional[StageInputs] = None


# -----------------------
# Helpers
# -----------------------
async def _read_json_request(request: Request) -> Dict[str, Any]:
    """
    Safely read JSON body from request; returns dict or raises HTTPException upon failure.
    """
    try:
        payload: Dict[str, Any] = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON body: {e}")
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400, detail="Payload must be a JSON object")
    return payload


def _ensure_calc_available(calc_fn, metal_name: str):
    if calc_fn is None:
        raise HTTPException(
            status_code=500, detail=f"Calculator for '{metal_name}' not available on server. Please deploy {metal_name}_calculators.py.")


# -----------------------
# Endpoints
# -----------------------
@app.get("/")
async def root():
    return {"message": "Metal LCA Engine running", "version": app.version}


# aluminium endpoint (unchanged)
@app.post("/aluminium/run")
async def run_aluminium(request: Request) -> JSONResponse:
    payload = await _read_json_request(request)
    _ensure_calc_available(compute_combined_lca_aluminium, "aluminium")
    try:
        result = compute_combined_lca_aluminium(payload)
        logger.info("Run aluminium LCA (route=%s project=%s)",
                    payload.get("route"), payload.get("projectId"))
        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Server error running aluminium LCA: {e}")


# copper endpoint (unchanged)
@app.post("/copper/run")
async def run_copper(request: Request) -> JSONResponse:
    payload = await _read_json_request(request)
    _ensure_calc_available(compute_combined_lca_copper, "copper")
    try:
        result = compute_combined_lca_copper(payload)
        logger.info("Run copper LCA (route=%s project=%s)",
                    payload.get("route"), payload.get("projectId"))
        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Server error running copper LCA: {e}")


# steel endpoint (new)
@app.post("/steel/run")
async def run_steel(request: Request) -> JSONResponse:
    payload = await _read_json_request(request)
    _ensure_calc_available(compute_combined_lca_steel, "steel")
    try:
        result = compute_combined_lca_steel(payload)
        logger.info("Run steel LCA (route=%s project=%s)",
                    payload.get("route"), payload.get("projectId"))
        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Server error running steel LCA: {e}")


# tin endpoint (new)
@app.post("/tin/run")
async def run_tin(request: Request) -> JSONResponse:
    payload = await _read_json_request(request)
    _ensure_calc_available(compute_combined_lca_tin, "tin")
    try:
        result = compute_combined_lca_tin(payload)
        logger.info("Run tin LCA (route=%s project=%s)",
                    payload.get("route"), payload.get("projectId"))
        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Server error running tin LCA: {e}")


# lithium endpoint (new)
@app.post("/lithium/run")
async def run_lithium(request: Request) -> JSONResponse:
    payload = await _read_json_request(request)
    _ensure_calc_available(compute_combined_lca_lithium, "lithium")
    try:
        result = compute_combined_lca_lithium(payload)
        logger.info("Run lithium LCA (route=%s project=%s)",
                    payload.get("route"), payload.get("projectId"))
        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Server error running lithium LCA: {e}")


# Generic dispatch endpoint: frontend can POST to /metal/run with "metal" set
@app.post("/metal/run")
async def run_metal(request: Request) -> JSONResponse:
    payload = await _read_json_request(request)
    metal = (payload.get("metal") or "").strip().lower()
    if not metal:
        raise HTTPException(
            status_code=400, detail="Missing 'metal' field in payload")

    # dispatch map
    dispatch_map = {
        "aluminium": compute_combined_lca_aluminium,
        "aluminum": compute_combined_lca_aluminium,  # US spelling
        "copper": compute_combined_lca_copper,
        "steel": compute_combined_lca_steel,
        "tin": compute_combined_lca_tin,
        "lithium": compute_combined_lca_lithium,
    }

    calc_fn = dispatch_map.get(metal)
    if calc_fn is None:
        # If calc function exists but is None because module import failed, give helpful message
        if metal in dispatch_map:
            raise HTTPException(
                status_code=500, detail=f"Calculator for '{metal}' not available on server. Please ensure module is deployed.")
        raise HTTPException(
            status_code=400, detail=f"Unsupported metal '{metal}'. Supported metals: {list(dispatch_map.keys())}")

    try:
        result = calc_fn(payload)
        logger.info("Dispatching LCA for metal=%s route=%s project=%s",
                    metal, payload.get("route"), payload.get("projectId"))
        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Server error running {metal} LCA: {e}")


# -----------------------
# Optional: stage-specific endpoints (examples)
# Uncomment and implement compute_mining, compute_extraction, compute_manufacturing
# in the respective calculators if you want single-stage endpoints.
# -----------------------
#
# @app.post("/aluminium/mining")
# async def aluminium_mining(request: Request):
#     payload = await _read_json_request(request)
#     try:
#         mining_inputs = payload.get("inputs", {}).get("mining", {})
#         from aluminium_calculators import compute_mining
#         res = compute_mining(mining_inputs)
#         return JSONResponse(status_code=200, content={"stage": "mining", "result": res})
#     except Exception:
#         traceback.print_exc()
#         raise HTTPException(status_code=500, detail="Error running mining stage")
#
# -----------------------
# Run server for local debug (if you run python api_service.py)
# -----------------------
if __name__ == "__main__":
    # default bind for development; when you deploy with uvicorn entrypoint, use that command.
    uvicorn.run("api_service:app", host="0.0.0.0", port=8000, reload=True)
