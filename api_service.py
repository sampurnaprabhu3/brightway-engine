# api_service.py  (clean JSON-only version, with stage selection)

from typing import Dict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import brightway2 as bw

# ----------------------------------------------------
# FastAPI app
# ----------------------------------------------------
app = FastAPI(title="Metal LCA Engine", version="0.1.0")


# ----------------------------------------------------
# Pydantic models (request & response)
# ----------------------------------------------------
class AluminiumRequest(BaseModel):
    projectId: str
    scenarioId: str
    metal: str                # e.g. "aluminium"
    route: str                # e.g. "primary_global"
    stage: str                # "mining" | "extraction" | "manufacturing" | "full_chain"
    functionalUnit_kg: float  # mass of metal in kg
    recycling_rate: float     # between 0 and 1
    primary_cost_per_kg: float
    recycled_cost_per_kg: float


class AluminiumResponse(BaseModel):
    # metadata
    engine: str
    projectId: str
    scenarioId: str
    metal: str
    route: str
    stage: str
    functionalUnit_kg: float

    # main result
    gwp_kgCO2e: float

    # per-stage result (only selected stage will be filled)
    stages: Dict[str, float]

    # simple cost outputs
    costs: Dict[str, float]


# ----------------------------------------------------
# Helper: map (route) -> Brightway DB name
# ----------------------------------------------------
def get_db_name_for_route(route: str) -> str:
    """Map user route string to Brightway database name."""
    ROUTE_TO_DB = {
        "primary_global": "aluminium_primary_global",
        # more routes later, e.g.
        # "secondary_global": "aluminium_secondary_global",
    }
    if route not in ROUTE_TO_DB:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown route '{route}'. Supported: {list(ROUTE_TO_DB.keys())}",
        )
    return ROUTE_TO_DB[route]


# ----------------------------------------------------
# Helper: map stage -> activity code, and fetch from DB
# ----------------------------------------------------
def get_stage_activity(db: bw.Database, db_name: str, stage: str):
    """
    User passes stage name; we map that to the correct activity *code*
    and fetch the Activity from the Brightway database.
    """

    STAGE_TO_CODE = {
        "mining": "aluminium_mining",
        "extraction": "aluminium_extraction",
        "manufacturing": "aluminium_manufacturing",
        "full_chain": "aluminium_full_chain",
    }

    if stage not in STAGE_TO_CODE:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown stage '{stage}'. Supported: {list(STAGE_TO_CODE.keys())}",
        )

    code = STAGE_TO_CODE[stage]

    try:
        # ✅ IMPORTANT: for db = bw.Database("aluminium_primary_global")
        # we must pass ONLY the code string, NOT (db_name, code)
        activity = db.get(code)
    except Exception:
        raise HTTPException(
            status_code=404,
            detail=f"Activity with code '{code}' not found in DB '{db_name}'.",
        )

    return activity


# ----------------------------------------------------
# Root (health) endpoint
# ----------------------------------------------------
@app.get("/")
def root():
    return {"message": "Metal LCA engine running", "version": "0.1.0"}


# ----------------------------------------------------
# Main LCA endpoint for aluminium
# ----------------------------------------------------
@app.post("/aluminium/run", response_model=AluminiumResponse)
def run_aluminium(req: AluminiumRequest) -> AluminiumResponse:
    try:
        # 1. Select project
        bw.projects.set_current("metal_lca")

        # 2. Map route -> DB, and open DB
        db_name = get_db_name_for_route(req.route)
        db = bw.Database(db_name)

        # 3. Get the activity for the user-selected stage
        activity = get_stage_activity(db, db_name, req.stage)

        # 4. Choose LCIA method (same as before)
        method = (
            "IPCC 2013 no LT",
            "climate change no LT",
            "global temperature change potential (GTP100) no LT",
        )

        # 5. Functional unit
        fu = {activity: req.functionalUnit_kg}

        # 6. Run LCA
        lca = bw.LCA(fu, method)
        lca.lci()
        lca.lcia()
        gwp = float(lca.score)

        # 7. Simple cost calculation based on recycling rate
        frac_recycled = req.recycling_rate
        frac_primary = 1.0 - frac_recycled

        primary_component = (
            frac_primary * req.functionalUnit_kg * req.primary_cost_per_kg
        )
        recycled_component = (
            frac_recycled * req.functionalUnit_kg * req.recycled_cost_per_kg
        )
        total_cost = primary_component + recycled_component

        costs = {
            "primary_material_fraction": frac_primary,
            "recycled_material_fraction": frac_recycled,
            "primary_cost_component": primary_component,
            "recycled_cost_component": recycled_component,
            "total_cost": total_cost,
        }

        # 8. Stage-wise GWP dict (only selected stage has a value)
        stage_key = f"{req.stage}_GWP_kgCO2e"
        stages = {stage_key: gwp}

        # 9. Build JSON response
        return AluminiumResponse(
            engine="brightway",
            projectId=req.projectId,
            scenarioId=req.scenarioId,
            metal=req.metal,
            route=req.route,
            stage=req.stage,
            functionalUnit_kg=req.functionalUnit_kg,
            gwp_kgCO2e=gwp,
            stages=stages,
            costs=costs,
        )

    except HTTPException:
        # Let FastAPI handle the HTTPException as is
        raise
    except Exception as e:
        # Catch-all for unexpected errors
        raise HTTPException(status_code=500, detail=str(e))
