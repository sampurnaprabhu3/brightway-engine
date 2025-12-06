# steel_calculators.py
from typing import Dict, Any
from aluminium_constants import (  # reuse constants already in repo
    KWH_TO_MJ, L_DIESEL_MJ, KG_COAL_MJ,
    GRID_CO2_KG_PER_KWH, DIESEL_CO2_KG_PER_L,
    COAL_CO2_KG_PER_KG, NG_CO2_KG_PER_MJ
)

# Default energy content (if not in aluminium_constants)
EF_ENERGY_COAL_MJ_PER_KG = KG_COAL_MJ if 'KG_COAL_MJ' in globals() else 29.3
EF_ENERGY_DIESEL_MJ_PER_L = L_DIESEL_MJ if 'L_DIESEL_MJ' in globals() else 38.6

# Default emission factors (India / typical)
EF_ELECTRICITY_CO2_INDIA = 0.82  # kg CO2 / kWh
EF_DIESEL_CO2 = DIESEL_CO2_KG_PER_L if 'DIESEL_CO2_KG_PER_L' in globals() else 2.68
EF_COAL_CO2 = COAL_CO2_KG_PER_KG if 'COAL_CO2_KG_PER_KG' in globals() else 2.42
EF_GAS_CO2 = NG_CO2_KG_PER_MJ if 'NG_CO2_KG_PER_MJ' in globals() else 0.056

# Other generic factors
EF_NOX_PER_GJ = 0.15  # kg NOx / GJ -> convert to per MJ by /1000
EF_CH4_PER_GJ = 0.001  # kg CH4 / GJ
EF_N2O_PER_GJ = 0.0001  # kg N2O / GJ
DUST_FACTOR_PER_ORE_KG = 0.0001  # kg PM per kg ore
PM2_5_FRACTION = 0.75


def _sum_energy_mj_from_inputs(inputs: Dict[str, Any]) -> float:
    total = 0.0
    if not inputs:
        return 0.0
    if "electricity_kWh" in inputs:
        total += float(inputs.get("electricity_kWh", 0.0)) * KWH_TO_MJ
    if "fuel_diesel_L" in inputs:
        total += float(inputs.get("fuel_diesel_L", 0.0)) * \
            EF_ENERGY_DIESEL_MJ_PER_L
    if "fuel_coal_kg" in inputs:
        total += float(inputs.get("fuel_coal_kg", 0.0)) * \
            EF_ENERGY_COAL_MJ_PER_KG
    if "fuel_naturalGas_MJ" in inputs:
        total += float(inputs.get("fuel_naturalGas_MJ", 0.0))
    return total


def compute_steel_mining(inputs: Dict[str, Any]) -> Dict[str, Any]:
    # mining inputs: ore_input_kg, ore_grade_percent, process_recovery, electricity_kWh, fuel_diesel_L, fuel_coal_kg, freshwater_m3, process_water_m3, land_area_m2, auxiliary_materials_kg
    ore_input_kg = float(inputs.get("ore_input_kg", 0.0))
    ore_grade_percent = float(inputs.get("ore_grade_percent", 0.0))
    eta = float(inputs.get("process_recovery", 0.95))  # default yield
    aux_kg = float(inputs.get("auxiliary_materials_kg", 0.0))

    MWF = ore_grade_percent / 100.0
    yield_metal_t = (ore_input_kg * MWF * eta) / 1000.0

    total_material_input_kg = ore_input_kg + aux_kg
    energy_mj = _sum_energy_mj_from_inputs(inputs)

    freshwater_m3 = float(inputs.get("freshwater_m3", 0.0))
    process_water_m3 = float(inputs.get("process_water_m3", 0.0))
    water_consumed_m3 = freshwater_m3 + process_water_m3

    land_occupied_m2 = float(inputs.get("land_area_m2", 0.0))

    waste_solid_kg = ore_input_kg * (1 - MWF) * (1 - eta)

    # emissions
    emissions_co2 = 0.0
    emissions_co2 += float(inputs.get("electricity_kWh",
                           0.0)) * EF_ELECTRICITY_CO2_INDIA
    emissions_co2 += float(inputs.get("fuel_diesel_L", 0.0)) * EF_DIESEL_CO2
    emissions_co2 += float(inputs.get("fuel_coal_kg", 0.0)) * EF_COAL_CO2
    emissions_ch4 = _sum_energy_mj_from_inputs(
        inputs) * (EF_CH4_PER_GJ / 1000.0)
    emissions_n2o = _sum_energy_mj_from_inputs(
        inputs) * (EF_N2O_PER_GJ / 1000.0)
    emissions_nox = _sum_energy_mj_from_inputs(
        inputs) * (EF_NOX_PER_GJ / 1000.0)
    particulates = ore_input_kg * DUST_FACTOR_PER_ORE_KG + \
        float(inputs.get("fuel_diesel_L", 0.0)) * 0.0005

    gwp = emissions_co2 + emissions_ch4 * 25.0 + emissions_n2o * 298.0

    return {
        "yield_metal_t": yield_metal_t,
        "total_material_input_kg": total_material_input_kg,
        "energy_MJ": energy_mj,
        "water_m3": water_consumed_m3,
        "land_occupied_m2": land_occupied_m2,
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


def compute_steel_extraction(inputs: Dict[str, Any], route: str = "primary") -> Dict[str, Any]:
    # extraction / smelting inputs vary; default factors used
    ore_input_kg = float(inputs.get("ore_input_kg", 0.0))
    eta = float(inputs.get("reduction_efficiency",
                inputs.get("process_recovery", 0.95)))
    aux_kg = float(inputs.get("auxiliary_materials_kg", 0.0))

    # yield: extraction usually refers to metal produced from concentrate
    yield_metal_t = (ore_input_kg * eta) / 1000.0

    total_material_input_kg = ore_input_kg + aux_kg
    energy_mj = _sum_energy_mj_from_inputs(inputs)

    # choose slag factor by route (BF-BOF larger slag; EAF smaller)
    if route and "eaf" in route:
        slag_factor = float(inputs.get("slag_factor", 0.12))
    else:
        slag_factor = float(inputs.get("slag_factor", 0.25))

    waste_solid_kg = ore_input_kg * slag_factor
    hazardous_kg = waste_solid_kg * 0.05

    # emissions
    emissions_co2 = 0.0
    emissions_co2 += float(inputs.get("electricity_kWh",
                           0.0)) * EF_ELECTRICITY_CO2_INDIA
    emissions_co2 += float(inputs.get("fuel_coal_kg", 0.0)) * EF_COAL_CO2
    emissions_co2 += float(inputs.get("fuel_naturalGas_MJ", 0.0)) * EF_GAS_CO2
    # process CO2 (reduction + carbonate decomposition) - approximate
    process_co2_direct = float(inputs.get("process_CO2_direct", ore_input_kg * 0.5 / 1000.0)) * \
        1000.0 if inputs.get("process_CO2_direct") else ore_input_kg * 0.5
    emissions_co2 += process_co2_direct

    total_fuel_mj = _sum_energy_mj_from_inputs(inputs)
    emissions_ch4 = total_fuel_mj * (EF_CH4_PER_GJ / 1000.0)
    emissions_n2o = total_fuel_mj * (EF_N2O_PER_GJ / 1000.0)
    emissions_nox = total_fuel_mj * (EF_NOX_PER_GJ / 1000.0)
    particulates = float(inputs.get("fuel_coal_kg", 0.0)) * \
        0.002 + ore_input_kg * DUST_FACTOR_PER_ORE_KG

    gwp = emissions_co2 + emissions_ch4 * 25.0 + emissions_n2o * 298.0

    return {
        "yield_metal_t": yield_metal_t,
        "total_material_input_kg": total_material_input_kg,
        "energy_MJ": energy_mj,
        "waste_solid_kg": waste_solid_kg,
        "waste_hazardous_kg": hazardous_kg,
        "emissions": {
            "co2_kg": emissions_co2,
            "ch4_kg": emissions_ch4,
            "n2o_kg": emissions_n2o,
            "nox_kg": emissions_nox,
            "particulates_kg": particulates
        },
        "gwp_kgCO2e": gwp
    }


def compute_steel_manufacturing(inputs: Dict[str, Any]) -> Dict[str, Any]:
    metal_input_kg = float(inputs.get(
        "metal_input_kg", inputs.get("ore_input_kg", 0.0)))
    eta = float(inputs.get("process_yield", 0.98))
    yield_metal_t = (metal_input_kg * eta) / 1000.0
    total_material_input_kg = metal_input_kg + \
        float(inputs.get("auxiliary_materials_kg", 0.0))
    energy_mj = _sum_energy_mj_from_inputs(inputs)
    freshwater_m3 = float(inputs.get("freshwater_m3", 0.0))
    process_water_m3 = float(inputs.get("process_water_m3", 0.0))
    water_consumed_m3 = freshwater_m3 + process_water_m3
    waste_solid_kg = float(inputs.get("scrap_kg", 0.0)
                           ) if "scrap_kg" in inputs else 0.0

    emissions_co2 = 0.0
    emissions_co2 += float(inputs.get("electricity_kWh",
                           0.0)) * EF_ELECTRICITY_CO2_INDIA
    emissions_co2 += float(inputs.get("fuel_naturalGas_MJ", 0.0)) * EF_GAS_CO2

    total_fuel_mj = _sum_energy_mj_from_inputs(inputs)
    emissions_nox = total_fuel_mj * (EF_NOX_PER_GJ / 1000.0)
    particulates = float(inputs.get("auxiliary_materials_kg", 0.0)) * 0.001

    gwp = emissions_co2

    return {
        "yield_metal_t": yield_metal_t,
        "total_material_input_kg": total_material_input_kg,
        "energy_MJ": energy_mj,
        "water_m3": water_consumed_m3,
        "waste_solid_kg": waste_solid_kg,
        "emissions": {
            "co2_kg": emissions_co2,
            "nox_kg": emissions_nox,
            "particulates_kg": particulates
        },
        "gwp_kgCO2e": gwp
    }


def compute_combined_lca_steel(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    payload: same top-level keys as other calculators: projectId, scenarioId, route, functionalUnit_kg, recycling_rate, inputs: { mining, extraction, manufacturing }
    route string used to detect BF-BOF vs EAF (contains 'eaf' if secondary)
    """
    inputs = payload.get("inputs", {}) or {}
    mining_inputs = inputs.get("mining", {}) or {}
    extraction_inputs = inputs.get("extraction", {}) or {}
    manufacturing_inputs = inputs.get("manufacturing", {}) or {}

    route = (payload.get("route") or "").lower()

    mining_res = compute_steel_mining(mining_inputs) if mining_inputs else {}
    extraction_res = compute_steel_extraction(
        extraction_inputs, route=route) if extraction_inputs else {}
    manufacturing_res = compute_steel_manufacturing(
        manufacturing_inputs) if manufacturing_inputs else {}

    # totals
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

    # simple LCIA results
    global_warming = total_gwp
    acidification = ((extraction_res.get("emissions", {}).get(
        "co2_kg", 0.0) if extraction_res else 0.0) * 0.0) + 0.0
    eutroph = (extraction_res.get("emissions", {}).get(
        "nox_kg", 0.0) if extraction_res else 0.0) * 0.1
    water_depletion = total_water
    resource_depletion = float(mining_inputs.get("ore_input_kg", 0.0))

    lcia = {
        "global_warming_kg_co2e": global_warming,
        "acidification_kg_so2e": acidification,
        "eutrophication_kg_po4e": eutroph,
        "water_depletion_m3": water_depletion,
        "resource_depletion_kg_resource_eq": resource_depletion,
        "particulate_matter_kg_pm2_5_eq": (mining_res.get("emissions", {}).get("particulates_kg", 0.0) if mining_res else 0.0) * PM2_5_FRACTION
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
