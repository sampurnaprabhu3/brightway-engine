# tin_calculators.py
from typing import Dict, Any
from aluminium_constants import (
    KWH_TO_MJ, L_DIESEL_MJ, KG_COAL_MJ,
    GRID_CO2_KG_PER_KWH, DIESEL_CO2_KG_PER_L,
    COAL_CO2_KG_PER_KG, NG_CO2_KG_PER_MJ,
    DIESEL_CH4_KG_PER_L, DIESEL_N2O_KG_PER_L,
    PM_PER_DIESEL_L, NOX_PER_GAS_MJ, PM_PER_COAL_KG,
)

# --- helper ---


def _sum_energy_mj_from_inputs(inputs: Dict[str, Any]) -> float:
    total = 0.0
    if "electricity_kWh" in inputs:
        total += float(inputs.get("electricity_kWh", 0.0)) * KWH_TO_MJ
    if "fuel_diesel_L" in inputs:
        total += float(inputs.get("fuel_diesel_L", 0.0)) * L_DIESEL_MJ
    if "fuel_coal_kg" in inputs:
        total += float(inputs.get("fuel_coal_kg", 0.0)) * KG_COAL_MJ
    if "fuel_naturalGas_MJ" in inputs:
        total += float(inputs.get("fuel_naturalGas_MJ", 0.0))
    return total

# --- mining stage for tin (cassiterite -> concentrate) ---


def compute_mining_tin(inputs: Dict[str, Any]) -> Dict[str, Any]:
    ore_input_kg = float(inputs.get("ore_input_kg", 0.0))
    ore_grade_percent = float(inputs.get("ore_grade_percent", 0.0))
    eta = float(inputs.get("process_recovery", 0.85))  # mining recovery
    aux_kg = float(inputs.get("auxiliary_materials_kg", 0.0))

    MWF = ore_grade_percent / 100.0
    yield_metal_t = (ore_input_kg * MWF * eta) / 1000.0
    total_material_input_kg = ore_input_kg + aux_kg
    energy_mj = _sum_energy_mj_from_inputs(inputs)

    freshwater_m3 = float(inputs.get("freshwater_m3", 0.0))
    process_water_m3 = float(inputs.get("process_water_m3", 0.0))
    water_returned_m3 = float(inputs.get("water_returned_m3", 0.0))
    water_consumed_m3 = freshwater_m3 + process_water_m3 - water_returned_m3

    # waste
    waste_solid_kg = max(0.0, ore_input_kg * (1.0 - MWF) * (1.0 - eta))

    # emissions - simple fuel & electricity driven
    emissions_co2 = 0.0
    if "electricity_kWh" in inputs:
        emissions_co2 += float(inputs.get("electricity_kWh",
                               0.0)) * GRID_CO2_KG_PER_KWH
    emissions_co2 += float(inputs.get("fuel_diesel_L",
                           0.0)) * DIESEL_CO2_KG_PER_L
    # small natural gas in mining sometimes:
    emissions_co2 += float(inputs.get("fuel_naturalGas_MJ",
                           0.0)) * NG_CO2_KG_PER_MJ

    emissions_ch4 = float(inputs.get("fuel_diesel_L", 0.0)
                          ) * DIESEL_CH4_KG_PER_L
    emissions_n2o = float(inputs.get("fuel_diesel_L", 0.0)
                          ) * DIESEL_N2O_KG_PER_L
    emissions_nox = float(inputs.get("fuel_diesel_L", 0.0)) * \
        PM_PER_DIESEL_L  # placeholder reuse
    particulates = float(inputs.get("fuel_diesel_L", 0.0)) * PM_PER_DIESEL_L

    gwp = emissions_co2 + emissions_ch4 * 28.0 + emissions_n2o * 265.0

    return {
        "yield_metal_t": yield_metal_t,
        "total_material_input_kg": total_material_input_kg,
        "energy_MJ": energy_mj,
        "water_m3": water_consumed_m3,
        "waste_solid_kg": waste_solid_kg,
        "emissions": {
            "co2_kg": emissions_co2,
            "ch4_kg": emissions_ch4,
            "n2o_kg": emissions_n2o,
            "nox_kg": emissions_nox,
            "particulates_kg": particulates
        },
        "gwp_kgCO2e": gwp
    }

# --- extraction stage for tin (concentrate -> smelt/refine) ---


def compute_extraction_tin(inputs: Dict[str, Any]) -> Dict[str, Any]:
    ore_input_kg = float(inputs.get("ore_input_kg", 0.0))
    eta = float(inputs.get("reduction_efficiency",
                inputs.get("process_recovery", 0.95)))
    yield_metal_t = (ore_input_kg * eta) / 1000.0
    total_material_input_kg = ore_input_kg + \
        float(inputs.get("auxiliary_materials_kg", 0.0))

    energy_mj = _sum_energy_mj_from_inputs(inputs)

    # waste & hazardous
    slag_factor = float(inputs.get("slag_factor", 0.25))
    waste_solid_kg = ore_input_kg * slag_factor
    hazardous_fraction = float(inputs.get("hazardous_fraction", 0.05))
    waste_hazardous_kg = waste_solid_kg * hazardous_fraction

    # emissions
    emissions_co2 = 0.0
    if "electricity_kWh" in inputs:
        emissions_co2 += float(inputs.get("electricity_kWh",
                               0.0)) * GRID_CO2_KG_PER_KWH
    emissions_co2 += float(inputs.get("fuel_coal_kg", 0.0)
                           ) * COAL_CO2_KG_PER_KG
    emissions_co2 += float(inputs.get("fuel_naturalGas_MJ",
                           0.0)) * NG_CO2_KG_PER_MJ
    # process CO2 approx (carbon-based reduction)
    process_co2 = float(inputs.get(
        "process_CO2_per_kg_ore", 0.3)) * ore_input_kg
    emissions_co2 += process_co2

    # particulates / nox
    nox_kg = float(inputs.get("fuel_naturalGas_MJ", 0.0)) * NOX_PER_GAS_MJ
    particulates_kg = float(inputs.get("fuel_coal_kg", 0.0)) * PM_PER_COAL_KG + \
        float(inputs.get("fuel_diesel_L", 0.0)) * PM_PER_DIESEL_L

    # water metal ions (simple leaching loss)
    metal_ions_kg = float(inputs.get("ore_input_kg", 0.0)) * \
        float(inputs.get("leaching_factor_metal", 0.0001))

    gwp = emissions_co2  # CH4/N2O small; omit for simplicity or add from fuels if desired

    return {
        "yield_metal_t": yield_metal_t,
        "total_material_input_kg": total_material_input_kg,
        "energy_MJ": energy_mj,
        "waste_solid_kg": waste_solid_kg,
        "waste_hazardous_kg": waste_hazardous_kg,
        "emissions": {
            "co2_kg": emissions_co2,
            "so2_kg": float(inputs.get("so2_kg_override", 0.0)),
            "nox_kg": nox_kg,
            "particulates_kg": particulates_kg
        },
        "emissions_water": {
            "metal_ions_kg": metal_ions_kg
        },
        "gwp_kgCO2e": gwp
    }

# --- manufacturing stage for tin (refined -> semifab) ---


def compute_manufacturing_tin(inputs: Dict[str, Any]) -> Dict[str, Any]:
    metal_input_kg = float(inputs.get(
        "metal_input_kg", inputs.get("ore_input_kg", 0.0)))
    process_yield = float(inputs.get("process_yield", 0.98))
    yield_metal_t = (metal_input_kg * process_yield) / 1000.0
    total_material_input_kg = metal_input_kg + \
        float(inputs.get("auxiliary_materials_kg", 0.0))
    energy_mj = _sum_energy_mj_from_inputs(inputs)

    water_m3 = float(inputs.get("freshwater_m3", 0.0)) + \
        float(inputs.get("process_water_m3", 0.0))
    waste_solid_kg = metal_input_kg * float(inputs.get("loss_fraction", 0.005))

    emissions_co2 = 0.0
    if "electricity_kWh" in inputs:
        emissions_co2 += float(inputs.get("electricity_kWh",
                               0.0)) * GRID_CO2_KG_PER_KWH
    emissions_co2 += float(inputs.get("fuel_naturalGas_MJ",
                           0.0)) * NG_CO2_KG_PER_MJ

    nox_kg = float(inputs.get("fuel_naturalGas_MJ", 0.0)) * NOX_PER_GAS_MJ
    particulates_kg = float(inputs.get("auxiliary_materials_kg", 0.0)) * 0.001

    gwp = emissions_co2

    return {
        "yield_metal_t": yield_metal_t,
        "total_material_input_kg": total_material_input_kg,
        "energy_MJ": energy_mj,
        "water_m3": water_m3,
        "waste_solid_kg": waste_solid_kg,
        "emissions": {
            "co2_kg": emissions_co2,
            "nox_kg": nox_kg,
            "particulates_kg": particulates_kg
        },
        "gwp_kgCO2e": gwp
    }

# --- combined LCA entrypoint ---


def compute_combined_lca_tin(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accepts payload with same structure as the other compute_combined_lca functions:
    payload: { projectId, scenarioId, route, functionalUnit_kg, recycling_rate, inputs: { mining: {...}, extraction: {...}, manufacturing: {...} } }
    """
    inputs = payload.get("inputs", {}) or {}
    mining_inputs = inputs.get("mining", {}) or {}
    extraction_inputs = inputs.get("extraction", {}) or {}
    manufacturing_inputs = inputs.get("manufacturing", {}) or {}

    mining_res = compute_mining_tin(mining_inputs) if mining_inputs else {}
    extraction_res = compute_extraction_tin(
        extraction_inputs) if extraction_inputs else {}
    manufacturing_res = compute_manufacturing_tin(
        manufacturing_inputs) if manufacturing_inputs else {}

    total_gwp = 0.0
    total_energy = 0.0
    total_water = 0.0

    for r in (mining_res, extraction_res, manufacturing_res):
        if not r:
            continue
        total_gwp += float(r.get("gwp_kgCO2e", 0.0) or 0.0)
        total_energy += float(r.get("energy_MJ", 0.0) or 0.0)
        total_water += float(r.get("water_m3", 0.0) or 0.0)

    recycling_rate = float(payload.get("recycling_rate", 0.0))
    primary_route_gwp = float(payload.get(
        "primary_route_gwp_kgCO2e", total_gwp))
    avoided = recycling_rate * primary_route_gwp

    # a minimal LCIA summary (you can extend with acidification etc)
    lcia = {
        "global_warming_kg_co2e": total_gwp,
        "acidification_kg_so2e": float(payload.get("acidification_override", 0.0)),
        "water_depletion_m3": total_water,
        "resource_depletion_kg_resource_eq": float(payload.get("resource_depletion_override", 0.0)),
    }

    return {
        "metadata": {
            "projectId": payload.get("projectId"),
            "scenarioId": payload.get("scenarioId"),
            "route": payload.get("route")
        },
        "functionalUnit_kg": float(payload.get("functionalUnit_kg", 1000.0)),
        "breakdown": {
            "mining": mining_res,
            "extraction": extraction_res,
            "manufacturing": manufacturing_res
        },
        "totals": {
            "gwp_kgCO2e": total_gwp,
            "energy_MJ": total_energy,
            "water_m3": total_water
        },
        "circularity": {
            "recycling_rate": recycling_rate,
            "avoided_primary_co2e_kg": avoided
        },
        "lcia_results": lcia
    }
