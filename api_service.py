# api_service.py
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import JSONResponse

# import the calculator functions that exist in your file
from aluminium_calculators import (
    compute_combined_lca,
    compute_mining,
    compute_extraction,
    compute_manufacturing,
)

app = FastAPI(title="Metal LCA Engine", version="0.2.1")


# -------------------------
# Pydantic input models
# -------------------------
class MiningInputs(BaseModel):
    ore_input_kg: Optional[float] = None
    ore_grade_percent: Optional[float] = None
    process_recovery: Optional[float] = None
    electricity_kWh: Optional[float] = None
    fuel_diesel_L: Optional[float] = None
    # add other mining-specific fields as needed


class ExtractionInputs(BaseModel):
    ore_input_kg: Optional[float] = None
    fraction_alumina: Optional[float] = None
    reduction_efficiency: Optional[float] = None
    electricity_kWh: Optional[float] = None
    fuel_coal_kg: Optional[float] = None
    # add other extraction-specific fields as needed


class ManufacturingInputs(BaseModel):
    metal_input_kg: Optional[float] = None
    process_yield: Optional[float] = None
    electricity_kWh: Optional[float] = None
    fuel_naturalGas_MJ: Optional[float] = None
    # add other manufacturing-specific fields as needed


class StageInputs(BaseModel):
    mining: Optional[MiningInputs] = None
    extraction: Optional[ExtractionInputs] = None
    manufacturing: Optional[ManufacturingInputs] = None
    # any unknown extra keys sent by frontend will be ignored by these models


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


# -------------------------
# Helpers
# -------------------------
def _dict_from_model(m):
    """Safe convert pydantic model or dict to plain dict"""
    if m is None:
        return {}
    if isinstance(m, dict):
        return m
    try:
        return m.dict()
    except Exception:
        return dict(m)


# -------------------------
# Endpoints
# -------------------------
@app.post("/aluminium/run")
async def run_aluminium(req: AluminiumRequest):
    """
    Main endpoint. Accepts:
      - combined payload with `inputs: { mining: {...}, extraction: {...}, manufacturing: {...} }`
      - OR single-stage payload where req.stage is 'mining'|'extraction'|'manufacturing' (and inputs.<stage> is supplied)
    Returns breakdown + totals (JSON).
    """
    payload = req.dict()
    inputs_model = req.inputs
    inputs = _dict_from_model(inputs_model)

    # If front-end sent combined inputs object, prefer compute_combined_lca
    if inputs and (
        ("mining" in inputs and inputs["mining"])
        or ("extraction" in inputs and inputs["extraction"])
        or ("manufacturing" in inputs and inputs["manufacturing"])
    ):
        # Use compute_combined_lca which already does per-stage computations + totals
        try:
            # convert nested pydantic models to normal dicts (if present)
            combined_payload = {
                **payload,
                "inputs": {
                    "mining": _dict_from_model(inputs.get("mining")),
                    "extraction": _dict_from_model(inputs.get("extraction")),
                    "manufacturing": _dict_from_model(inputs.get("manufacturing")),
                },
            }
            result = compute_combined_lca(combined_payload)
            return JSONResponse(status_code=200, content=result)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Server error during combined LCA: {e}")

    # Otherwise, support single-stage operations via req.stage
    stage = (req.stage or "").lower()
    single_inputs = {}
    if inputs:
        # If a single stage payload used, inputs likely contains that key
        if stage:
            single_inputs = inputs.get(stage, {})
        else:
            # try to infer stage if only one present
            present = [k for k, v in inputs.items() if v]
            if len(present) == 1:
                stage = present[0]
                single_inputs = inputs.get(stage, {})
            else:
                raise HTTPException(
                    status_code=400, detail="No combined inputs found and stage not specified or ambiguous.")

    if not stage:
        raise HTTPException(
            status_code=400, detail="stage is required when not sending combined inputs (mining/extraction/manufacturing)")

    # route the single stage to the right calculator
    try:
        if stage == "mining":
            res = compute_mining(single_inputs or {})
            return JSONResponse(status_code=200, content={"stage": "mining", "result": res})
        elif stage == "extraction":
            res = compute_extraction(single_inputs or {})
            return JSONResponse(status_code=200, content={"stage": "extraction", "result": res})
        elif stage == "manufacturing":
            res = compute_manufacturing(single_inputs or {})
            return JSONResponse(status_code=200, content={"stage": "manufacturing", "result": res})
        else:
            raise HTTPException(
                status_code=400, detail=f"Unknown stage '{stage}'. Allowed: mining, extraction, manufacturing")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Server error computing stage '{stage}': {e}")


# quick root check
@app.get("/")
async def root():
    return {"message": "Metal LCA engine running", "version": app.version}
