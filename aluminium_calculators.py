# aluminium_calculators.py
from typing import Dict, Any
from aluminium_constants import (
    KWH_TO_MJ, L_DIESEL_MJ, L_HEAVYOIL_MJ, KG_COAL_MJ,
    GRID_CO2_KG_PER_KWH, DIESEL_CO2_KG_PER_L, HEAVYOIL_CO2_KG_PER_L,
    NG_CO2_KG_PER_MJ, COAL_CO2_KG_PER_KG, ANODE_CARBON_CO2_KG_PER_KG,
    DIESEL_CH4_KG_PER_L, DIESEL_N2O_KG_PER_L,
    PM_PER_DIESEL_L, NOX_PER_GAS_MJ, PM_PER_COAL_KG,
    WATER_SCARCITY_FACTOR
)


def _sum_energy_mj_from_inputs(inputs: Dict[str, Any]) -> float:
    """Sum energy from common fields if present (returns MJ)."""
    total = 0.0
    if "electricity_kWh" in inputs:
        total += float(inputs.get("electricity_kWh", 0.0)) * KWH_TO_MJ
    if "fuel_diesel_L" in inputs:
        total += float(inputs.get("fuel_diesel_L", 0.0)) * L_DIESEL_MJ
    if "fuel_heavyOil_L" in inputs:
        total += float(inputs.get("fuel_heavyOil_L", 0.0)) * L_HEAVYOIL_MJ
    if "fuel_coal_kg" in inputs:
        total += float(inputs.get("fuel_coal_kg", 0.0)) * KG_COAL_MJ
    if "fuel_naturalGas_MJ" in inputs:
        total += float(inputs.get("fuel_naturalGas_MJ", 0.0))
    return total


def compute_mining(inputs: Dict[str, Any]) -> Dict[str, Any]:
    # inputs expected: ore_input_kg, ore_grade_percent, process_recovery, electricity_kWh, fuel_diesel_L, freshwater_m3, process_water_m3, water_returned_m3 (optional)
    ore_input_kg = float(inputs.get("ore_input_kg", 0.0))
    ore_grade_percent = float(inputs.get("ore_grade_percent", 0.0))
    process_recovery = float(inputs.get("process_recovery", 1.0))
    aux_materials_kg = float(inputs.get("auxiliary_materials_kg", 0.0))
    # yield metal in tonnes
    yield_metal_t = (ore_input_kg * (ore_grade_percent / 100.0)
                     * process_recovery) / 1000.0

    total_material_input_kg = ore_input_kg + aux_materials_kg
    energy_mj = _sum_energy_mj_from_inputs(inputs)

    # water
    freshwater_m3 = float(inputs.get("freshwater_m3", 0.0))
    process_water_m3 = float(inputs.get("process_water_m3", 0.0))
    water_returned_m3 = float(inputs.get("water_returned_m3", 0.0))
    water_consumed_m3 = freshwater_m3 + process_water_m3 - water_returned_m3

    # waste
    co_product_outputs_total_kg = float(
        inputs.get("co_product_outputs_total_kg", 0.0))
    waste_solid_kg = max(0.0, ore_input_kg - yield_metal_t *
                         1000.0 - co_product_outputs_total_kg)

    # emissions (air) simplified
    emissions_co2 = 0.0
    if "electricity_kWh" in inputs:
        emissions_co2 += float(inputs.get("electricity_kWh",
                               0.0)) * GRID_CO2_KG_PER_KWH
    emissions_co2 += float(inputs.get("fuel_diesel_L",
                           0.0)) * DIESEL_CO2_KG_PER_L
    emissions_co2 += float(inputs.get("fuel_heavyOil_L",
                           0.0)) * HEAVYOIL_CO2_KG_PER_L
    emissions_co2 += float(inputs.get("fuel_naturalGas_MJ",
                           0.0)) * NG_CO2_KG_PER_MJ

    emissions_ch4 = float(inputs.get("fuel_diesel_L", 0.0)
                          ) * DIESEL_CH4_KG_PER_L
    emissions_n2o = float(inputs.get("fuel_diesel_L", 0.0)
                          ) * DIESEL_N2O_KG_PER_L
    emissions_nox = float(inputs.get("fuel_diesel_L", 0.0)
                          ) * PM_PER_DIESEL_L  # placeholder
    particulate = float(inputs.get("fuel_diesel_L", 0.0)) * PM_PER_DIESEL_L

    # basic LCIA metric: GWP in kg CO2e (CO2 + CH4*28 + N2O*265)
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
            "particulates_kg": particulate
        },
        "gwp_kgCO2e": gwp
    }


def compute_extraction(inputs: Dict[str, Any]) -> Dict[str, Any]:
    # inputs: ore_input_kg, fraction_alumina, reduction_efficiency, electricity_kWh, fuel_coal_kg, anode_carbon_kg, fuel_naturalGas_MJ, etc.
    ore_input_kg = float(inputs.get("ore_input_kg", 0.0))
    fraction_alumina = float(inputs.get("fraction_alumina", 0.0))
    reduction_efficiency = float(inputs.get("reduction_efficiency", 1.0))

    yield_metal_t = (ore_input_kg * fraction_alumina *
                     reduction_efficiency) / 1000.0
    total_material_input_kg = ore_input_kg + \
        float(inputs.get("anode_materials", 0.0))
    energy_mj = _sum_energy_mj_from_inputs(inputs)

    # waste
    impurity_fraction = float(inputs.get("impurity_fraction", 0.0))
    anode_residue_kg = float(inputs.get("anode_residue_kg", 0.0))
    waste_solid_kg = (ore_input_kg * impurity_fraction) + anode_residue_kg

    # emissions
    emissions_co2 = 0.0
    if "electricity_kWh" in inputs:
        emissions_co2 += float(inputs.get("electricity_kWh",
                               0.0)) * GRID_CO2_KG_PER_KWH
    emissions_co2 += float(inputs.get("fuel_coal_kg", 0.0)
                           ) * COAL_CO2_KG_PER_KG
    emissions_co2 += float(inputs.get("fuel_naturalGas_MJ",
                           0.0)) * NG_CO2_KG_PER_MJ
    emissions_co2 += float(inputs.get("anode_carbon_kg", 0.0)
                           ) * ANODE_CARBON_CO2_KG_PER_KG

    # PFCs simple estimate
    cf4_kg = float(inputs.get("anode_effect_minutes", 0.0)) * \
        float(inputs.get("CF4_factor", 0.0))
    c2f6_kg = float(inputs.get("anode_effect_minutes", 0.0)) * \
        float(inputs.get("C2F6_factor", 0.0))
    pfc_co2e = cf4_kg * 7390.0 + c2f6_kg * 12200.0

    # other small emissions
    nox_kg = float(inputs.get("fuel_naturalGas_MJ", 0.0)) * NOX_PER_GAS_MJ
    particulates_kg = float(inputs.get("fuel_coal_kg", 0.0)) * PM_PER_COAL_KG

    gwp = emissions_co2 + pfc_co2e

    return {
        "yield_metal_t": yield_metal_t,
        "total_material_input_kg": total_material_input_kg,
        "energy_MJ": energy_mj,
        "waste_solid_kg": waste_solid_kg,
        "emissions": {
            "co2_kg": emissions_co2,
            "cf4_kg": cf4_kg,
            "c2f6_kg": c2f6_kg,
            "pfc_co2e_kgCO2e": pfc_co2e,
            "nox_kg": nox_kg,
            "particulates_kg": particulates_kg
        },
        "gwp_kgCO2e": gwp
    }


def compute_manufacturing(inputs: Dict[str, Any]) -> Dict[str, Any]:
    # inputs: metal_input_kg, process_yield, electricity_kWh, fuel_naturalGas_MJ, lubricants_kg, etc.
    metal_input_kg = float(inputs.get(
        "metal_input_kg", inputs.get("metal_input", 0.0)))
    process_yield = float(inputs.get("process_yield", 1.0))
    yield_metal_t = (metal_input_kg * process_yield) / 1000.0
    total_material_input_kg = metal_input_kg + \
        float(inputs.get("lubricants_kg", 0.0))
    energy_mj = _sum_energy_mj_from_inputs(inputs)

    # water consumed
    freshwater_m3 = float(inputs.get("freshwater_m3", 0.0))
    process_water_m3 = float(inputs.get("process_water_m3", 0.0))
    water_returned_m3 = float(inputs.get("cooling_water_returned", 0.0))
    water_consumed_m3 = freshwater_m3 + process_water_m3 - water_returned_m3

    # emissions
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
        "water_m3": water_consumed_m3,
        "waste_solid_kg": float(inputs.get("scrap_kg", 0.0)),
        "emissions": {
            "co2_kg": emissions_co2,
            "nox_kg": nox_kg,
            "particulates_kg": particulates_kg
        },
        "gwp_kgCO2e": gwp
    }


def compute_combined_lca(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    payload contains:
      - projectId, scenarioId, route, functionalUnit_kg, recycling_rate
      - inputs: { mining: {...}, extraction: {...}, manufacturing: {...} }
    Returns breakdown & totals.
    """
    inputs = payload.get("inputs", {})
    mining_inputs = inputs.get("mining", {})
    extraction_inputs = inputs.get("extraction", {})
    manufacturing_inputs = inputs.get("manufacturing", {})

    mining_res = compute_mining(mining_inputs) if mining_inputs else {}
    extraction_res = compute_extraction(
        extraction_inputs) if extraction_inputs else {}
    manufacturing_res = compute_manufacturing(
        manufacturing_inputs) if manufacturing_inputs else {}

    # totals (sum numeric fields)
    total_gwp = 0.0
    total_energy = 0.0
    total_water = 0.0

    for res in (mining_res, extraction_res, manufacturing_res):
        if not res:
            continue
        total_gwp += float(res.get("gwp_kgCO2e", 0.0) or 0.0)
        total_energy += float(res.get("energy_MJ", 0.0) or 0.0)
        total_water += float(res.get("water_m3", 0.0) or 0.0)

    # circularity: avoided primary burden (very simplified)
    recycling_rate = float(payload.get("recycling_rate", 0.0))
    # If user provided primary route GWP we could compute avoided; for now use manufacturing_gwp * recycling_rate
    primary_route_gwp = float(payload.get(
        "primary_route_gwp_kgCO2e", total_gwp))
    avoided = recycling_rate * primary_route_gwp

    return {
        "metadata": {
            "projectId": payload.get("projectId"),
            "scenarioId": payload.get("scenarioId"),
            "route": payload.get("route")
        },
        "functionalUnit_kg": float(payload.get("functionalUnit_kg", 1.0)),
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
        }
    }
