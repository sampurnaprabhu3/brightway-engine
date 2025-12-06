# lithium_calculators.py
from typing import Dict, Any
import math

# --- Default constants / EF (change later if you have more accurate local values) ---
EF_ELECTRICITY_GLOBAL = 0.48  # kg CO2 / kWh
EF_ELECTRICITY_INDIA = 0.82
EF_DIESEL_CO2_PER_L = 2.68
EF_COAL_CO2_PER_KG = 2.42
EF_GAS_CO2_PER_MJ = 0.056

MJ_PER_KWH = 3.6
MJ_PER_L_DIESEL = 38.6
MJ_PER_KG_COAL = 29.3

EF_NOX_PER_MJ = 0.15 / 1000  # kg NOx / MJ
EF_CH4_PER_MJ = 0.001 / 1000
EF_N2O_PER_MJ = 0.0001 / 1000

# helper util


def _safe_float(x, default=0.0):
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _sum_energy_mj(inputs: Dict[str, Any]) -> float:
    # supports electricity_kWh, fuel_naturalGas_MJ, fuel_coal_kg, fuel_diesel_L
    el = _safe_float(inputs.get("electricity_kWh", 0.0))
    gas = _safe_float(inputs.get("fuel_naturalGas_MJ", 0.0))
    coal = _safe_float(inputs.get("fuel_coal_kg", 0.0))
    diesel = _safe_float(inputs.get("fuel_diesel_L", 0.0))
    return el * MJ_PER_KWH + gas + coal * MJ_PER_KG_COAL + diesel * MJ_PER_L_DIESEL


def _co2_from_energy(inputs: Dict[str, Any], ef_electricity=EF_ELECTRICITY_GLOBAL) -> float:
    el = _safe_float(inputs.get("electricity_kWh", 0.0))
    gas = _safe_float(inputs.get("fuel_naturalGas_MJ", 0.0))
    coal = _safe_float(inputs.get("fuel_coal_kg", 0.0))
    diesel = _safe_float(inputs.get("fuel_diesel_L", 0.0))
    co2 = el * ef_electricity + gas * EF_GAS_CO2_PER_MJ + \
        coal * EF_COAL_CO2_PER_KG + diesel * EF_DIESEL_CO2_PER_L
    return co2


def _combustion_GHGs(inputs: Dict[str, Any]) -> Dict[str, float]:
    total_mj = _sum_energy_mj(inputs)
    ch4 = total_mj * EF_CH4_PER_MJ
    n2o = total_mj * EF_N2O_PER_MJ
    nox = total_mj * EF_NOX_PER_MJ
    return {"CH4": ch4, "N2O": n2o, "NOx": nox, "TotalFuelMJ": total_mj}

# Main single-stage calculator helper


def _calc_stage_common(stage_inputs: Dict[str, Any], defaults: Dict[str, Any]) -> Dict[str, Any]:
    """
    stage_inputs - raw dict from payload for this stage (can be empty)
    defaults - dictionary with stage defaults (eta, slag_factor, hazardous_fraction, etc.)
    """
    # read inputs with safe float conversions
    ore_input_kg = _safe_float(stage_inputs.get("ore_input_kg", 0.0))
    electricity_kWh = _safe_float(stage_inputs.get("electricity_kWh", 0.0))
    fuel_naturalGas_MJ = _safe_float(
        stage_inputs.get("fuel_naturalGas_MJ", 0.0))
    fuel_coal_kg = _safe_float(stage_inputs.get("fuel_coal_kg", 0.0))
    fuel_diesel_L = _safe_float(stage_inputs.get("fuel_diesel_L", 0.0))
    freshwater_m3 = _safe_float(stage_inputs.get("freshwater_m3", 0.0))
    process_water_m3 = _safe_float(stage_inputs.get("process_water_m3", 0.0))
    auxiliary_materials_kg = _safe_float(
        stage_inputs.get("auxiliary_materials_kg", 0.0))
    ore_grade_percent = _safe_float(stage_inputs.get(
        "ore_grade_percent", None) or defaults.get("ore_grade_percent", 0.0))
    eta = defaults.get("eta_stage", 0.9)
    slag_factor = defaults.get("slag_factor", 0.2)
    hazardous_fraction = defaults.get("hazardous_fraction", 0.05)

    # yield_metal_t: if ore_input provided and grade given, else use eta*ore_input
    MWF = ore_grade_percent / 100.0 if ore_grade_percent else None
    if ore_input_kg and MWF is not None:
        yield_metal_t = (ore_input_kg * MWF * eta) / 1000.0
    elif ore_input_kg:
        yield_metal_t = (ore_input_kg * eta) / 1000.0
    else:
        yield_metal_t = defaults.get("yield_override_t", 0.0)

    # material & energy
    total_material_input_kg = ore_input_kg + auxiliary_materials_kg
    energy_MJ = _sum_energy_mj(stage_inputs)
    water_m3 = freshwater_m3 + process_water_m3

    # waste
    if ore_input_kg and MWF is not None:
        waste_solid_kg = ore_input_kg * \
            (1.0 - (MWF if MWF is not None else 0.0)) * (1.0 - eta)
    elif ore_input_kg:
        waste_solid_kg = ore_input_kg * (1.0 - eta)
    else:
        # fallback for brine mining etc - proportional to auxiliaries
        waste_solid_kg = auxiliary_materials_kg * \
            (defaults.get("waste_factor_aux", 0.5))

    waste_hazardous_kg = waste_solid_kg * hazardous_fraction

    # emissions
    co2_from_energy = _co2_from_energy(stage_inputs, ef_electricity=defaults.get(
        "ef_electricity", EF_ELECTRICITY_GLOBAL))
    combustion = _combustion_GHGs(stage_inputs)
    # optional simple process CO2 (user may provide or defaults)
    process_co2_direct = _safe_float(stage_inputs.get(
        "process_CO2_direct", defaults.get("process_CO2_direct", 0.0)))
    emissions_air_co2_kg = co2_from_energy + process_co2_direct

    # SO2 approx: from coal sulfur (if coal present)
    s_content_coal = defaults.get("s_content_coal", 0.02)  # 2% default
    desulfur_eff = defaults.get("desulfurization_efficiency", 0.0)
    so2_from_coal = fuel_coal_kg * s_content_coal * 2.0 * (1.0 - desulfur_eff)
    so2_from_diesel = fuel_diesel_L * defaults.get("ef_so2_diesel", 0.0)
    emissions_air_so2_kg = so2_from_coal + so2_from_diesel

    # particulates: simple sum
    particulates = ore_input_kg * \
        defaults.get("dust_factor", 0.0001) + fuel_coal_kg * \
        defaults.get("ef_pm_coal", 0.002)

    # water emissions (simplified)
    emissions_water_chemicals_kg = process_water_m3 * \
        defaults.get("chem_concentration_kg_per_m3", 0.5)
    emissions_water_metal_ions_kg = ore_input_kg * \
        defaults.get("leaching_factor_metal", 0.0001)

    return {
        "yield_metal_t": yield_metal_t,
        "total_material_input_kg": total_material_input_kg,
        "energy_MJ": energy_MJ,
        "water_m3": water_m3,
        "waste_solid_kg": waste_solid_kg,
        "waste_hazardous_kg": waste_hazardous_kg,
        "emissions": {
            "co2_kg": emissions_air_co2_kg,
            "ch4_kg": combustion["CH4"],
            "n2o_kg": combustion["N2O"],
            "nox_kg": combustion["NOx"],
            "so2_kg": emissions_air_so2_kg,
            "particulates_kg": particulates
        },
        "emissions_water": {
            "chemicals_kg": emissions_water_chemicals_kg,
            "metal_ions_kg": emissions_water_metal_ions_kg
        },
    }

# Top-level combined LCA function


def compute_combined_lca_lithium(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accepts the same combined payload shape as other metals.
    Returns breakdown, totals, circularity, lcia_results.
    """
    metadata = {
        "projectId": payload.get("projectId"),
        "scenarioId": payload.get("scenarioId"),
        "route": payload.get("route")
    }
    FU = _safe_float(payload.get("functionalUnit_kg", 1000.0)
                     )  # default to 1000 kg = 1 t
    inputs = payload.get("inputs", {})

    # default stage parameters for lithium routes (you can fine-tune per route)
    defaults_mining = {
        "eta_stage": 0.90,
        "ef_electricity": EF_ELECTRICITY_GLOBAL,
        "waste_factor_aux": 0.5,
        "leaching_factor_metal": 0.0001,
        "chem_concentration_kg_per_m3": 0.5
    }
    defaults_extraction = {
        "eta_stage": 0.90,
        "ef_electricity": EF_ELECTRICITY_GLOBAL,
        "slag_factor": 0.15,
        "hazardous_fraction": 0.05,
        "leaching_factor_metal": 0.0001
    }
    defaults_manufacturing = {
        "eta_stage": 0.98,
        "ef_electricity": EF_ELECTRICITY_GLOBAL
    }

    # mining stage
    mining_inputs = inputs.get("mining", {}) or {}
    extraction_inputs = inputs.get("extraction", {}) or {}
    manufacturing_inputs = inputs.get("manufacturing", {}) or {}

    mining_res = _calc_stage_common(mining_inputs, defaults_mining)
    extraction_res = _calc_stage_common(extraction_inputs, defaults_extraction)
    manufacturing_res = _calc_stage_common(
        manufacturing_inputs, defaults_manufacturing)

    # totals
    totals_gwp = mining_res["emissions"]["co2_kg"] + \
        extraction_res["emissions"]["co2_kg"] + \
        manufacturing_res["emissions"]["co2_kg"]
    totals_energy = mining_res["energy_MJ"] + \
        extraction_res["energy_MJ"] + manufacturing_res["energy_MJ"]
    totals_water = mining_res["water_m3"] + \
        extraction_res["water_m3"] + manufacturing_res["water_m3"]

    # circularity placeholders (if user supplies recycling_rate etc. you can use it)
    recycling_rate = _safe_float(payload.get("recycling_rate", 0.0))
    avoided_primary_co2e_kg = 0.0  # need benchmark to compute; left zero for now

    # simple LCIA results (GWP using CH4 & N2O)
    total_ch4 = mining_res["emissions"]["ch4_kg"] + \
        extraction_res["emissions"]["ch4_kg"] + \
        manufacturing_res["emissions"]["ch4_kg"]
    total_n2o = mining_res["emissions"]["n2o_kg"] + \
        extraction_res["emissions"]["n2o_kg"] + \
        manufacturing_res["emissions"]["n2o_kg"]
    global_warming = totals_gwp + 25.0 * total_ch4 + 298.0 * total_n2o
    acidification = 1.2 * (mining_res["emissions"].get("so2_kg", 0.0) + extraction_res["emissions"].get("so2_kg", 0.0) + manufacturing_res["emissions"].get("so2_kg", 0.0)) \
        + 0.7 * (mining_res["emissions"].get("nox_kg", 0.0) + extraction_res["emissions"].get(
            "nox_kg", 0.0) + manufacturing_res["emissions"].get("nox_kg", 0.0))
    eutrophication = 0.1 * (mining_res["emissions"].get("nox_kg", 0.0) + extraction_res["emissions"].get(
        "nox_kg", 0.0) + manufacturing_res["emissions"].get("nox_kg", 0.0))
    water_depletion = totals_water  # region CF not applied
    resource_depletion = _safe_float(payload.get("inputs", {}).get(
        "mining", {}).get("ore_input_kg", 0.0)) * 1.0  # placeholder

    response = {
        "metadata": metadata,
        "functionalUnit_kg": FU,
        "breakdown": {
            "mining": mining_res,
            "extraction": extraction_res,
            "manufacturing": manufacturing_res
        },
        "totals": {
            "gwp_kgCO2e": global_warming,
            "energy_MJ": totals_energy,
            "water_m3": water_depletion
        },
        "circularity": {
            "recycling_rate": recycling_rate,
            "avoided_primary_co2e_kg": avoided_primary_co2e_kg
        },
        "lcia_results": {
            "global_warming_kg_co2e": global_warming,
            "acidification_kg_so2e": acidification,
            "eutrophication_kg_po4e": eutrophication,
            "water_depletion_m3": water_depletion,
            "resource_depletion_kg_resource_eq": resource_depletion
        }
    }
    return response
