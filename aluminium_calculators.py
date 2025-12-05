# aluminium_calculators.py
"""
Stage calculators for Aluminium LCA.
Currently: mining stage (follows formulas you provided).
Returns stage results as dicts suitable for JSON response.
"""

from typing import Dict
from decimal import Decimal

from aluminium_constants import (
    KWH_TO_MJ,
    DIESEL_MJ_PER_L,
    HFO_MJ_PER_L,
    COAL_MJ_PER_KG,
    CO2_PER_L_DIESEL,
    CO2_PER_L_HFO,
    CO2_PER_MJ_NATGAS,
    CO2_PER_KG_COAL,
    CH4_PER_L_DIESEL,
    N2O_PER_L_DIESEL,
    NOX_FACTOR_DIESEL,
    PM_FACTOR_DIESEL,
    VOC_FACTOR_AUX,
    LEACHING_FACTOR,
    RUNOFF_FRACTION,
    FLUORIDE_CONC_DEFAULT,
    SO2_SULFUR_CONVERSION,
)


def safe_get(d: dict, key: str, default=0.0):
    v = d.get(key, default)
    try:
        return float(v)
    except Exception:
        return default


def calculate_mining(inputs: Dict) -> Dict:
    """
    inputs: dict with expected keys (any missing key uses a default):
      - ore_input_kg
      - ore_grade_percent
      - process_recovery (0..1)
      - auxiliary_materials_kg
      - electricity_kWh
      - fuel_diesel_L
      - fuel_heavyOil_L
      - fuel_naturalGas_MJ
      - freshwater_m3, process_water_m3, water_returned_m3
      - land_area_m2
      - co_product_outputs_total_kg
      - hazardous_fraction
      - sulfur_content (for coal/if applicable)
      - coal_kg
      - impurity_factor
    Returns dict with stage outputs and emissions.
    """
    # --- inputs (with defaults)
    ore_input_kg = safe_get(inputs, "ore_input_kg", 1000.0)
    ore_grade_percent = safe_get(inputs, "ore_grade_percent", 1.5)
    process_recovery = safe_get(inputs, "process_recovery", 0.9)
    auxiliary_materials_kg = safe_get(inputs, "auxiliary_materials_kg", 0.0)

    electricity_kWh = safe_get(inputs, "electricity_kWh", 0.0)
    fuel_diesel_L = safe_get(inputs, "fuel_diesel_L", 0.0)
    fuel_heavyOil_L = safe_get(inputs, "fuel_heavyOil_L", 0.0)
    fuel_naturalGas_MJ = safe_get(inputs, "fuel_naturalGas_MJ", 0.0)
    coal_kg = safe_get(inputs, "coal_kg", 0.0)
    sulfur_content = safe_get(inputs, "sulfur_content", 0.01)  # fraction

    freshwater_m3 = safe_get(inputs, "freshwater_m3", 0.0)
    process_water_m3 = safe_get(inputs, "process_water_m3", 0.0)
    water_returned_m3 = safe_get(inputs, "water_returned_m3", 0.0)
    land_area_m2 = safe_get(inputs, "land_area_m2", 0.0)
    co_product_outputs_total_kg = safe_get(
        inputs, "co_product_outputs_total_kg", 0.0)
    hazardous_fraction = safe_get(inputs, "hazardous_fraction", 0.0)
    impurity_factor = safe_get(inputs, "impurity_factor", 0.0)
    product_mass_kg = safe_get(inputs, "product_mass_kg", 1.0)

    # --- computed quantities (formula mapping)
    yield_metal_t = ore_input_kg * \
        (ore_grade_percent / 100.0) * process_recovery / 1000.0
    # yield_metal_t is in tonnes (since ore_input_kg /1000)
    total_material_input_kg = ore_input_kg + auxiliary_materials_kg

    # Energy total (MJ)
    energy_total_MJ = (
        electricity_kWh * KWH_TO_MJ
        + fuel_diesel_L * DIESEL_MJ_PER_L
        + fuel_heavyOil_L * HFO_MJ_PER_L
        + fuel_naturalGas_MJ
        + coal_kg * COAL_MJ_PER_KG
    )

    water_consumed_m3 = freshwater_m3 + process_water_m3 - water_returned_m3

    land_occupied_m2 = land_area_m2

    waste_solid_kg = ore_input_kg - \
        (yield_metal_t * 1000.0) - co_product_outputs_total_kg
    if waste_solid_kg < 0:
        waste_solid_kg = 0.0
    waste_hazardous_kg = waste_solid_kg * hazardous_fraction

    # Emissions - CO2
    emissions_co2_kg = (
        electricity_kWh * (inputs.get("grid_factor", 0.0))
        + fuel_diesel_L * CO2_PER_L_DIESEL
        + fuel_heavyOil_L * CO2_PER_L_HFO
        + fuel_naturalGas_MJ * CO2_PER_MJ_NATGAS
        + coal_kg * CO2_PER_KG_COAL
    )

    emissions_ch4_kg = fuel_diesel_L * CH4_PER_L_DIESEL
    emissions_n2o_kg = fuel_diesel_L * N2O_PER_L_DIESEL
    emissions_so2_kg = coal_kg * sulfur_content * SO2_SULFUR_CONVERSION
    emissions_nox_kg = fuel_diesel_L * NOX_FACTOR_DIESEL
    emissions_particulates_kg = fuel_diesel_L * PM_FACTOR_DIESEL
    heavy_metals_kg = ore_input_kg * impurity_factor
    voc_kg = auxiliary_materials_kg * VOC_FACTOR_AUX

    # Water emissions
    emissions_water_metal_ions_kg = ore_input_kg * LEACHING_FACTOR
    emissions_water_suspended_solids_kg = waste_solid_kg * RUNOFF_FRACTION
    emissions_water_fluoride_kg = process_water_m3 * FLUORIDE_CONC_DEFAULT
    emissions_water_chemicals_kg = auxiliary_materials_kg * \
        0.01  # default small loss fraction

    # Pack results
    stage_result = {
        "stage": "mining",
        "yield_metal_t": yield_metal_t,
        "total_material_input_kg": total_material_input_kg,
        "energy_total_MJ": energy_total_MJ,
        "water_consumed_m3": water_consumed_m3,
        "land_occupied_m2": land_occupied_m2,
        "waste_solid_kg": waste_solid_kg,
        "waste_hazardous_kg": waste_hazardous_kg,
        "emissions_air": {
            "co2_kg": emissions_co2_kg,
            "ch4_kg": emissions_ch4_kg,
            "n2o_kg": emissions_n2o_kg,
            "so2_kg": emissions_so2_kg,
            "nox_kg": emissions_nox_kg,
            "particulates_kg": emissions_particulates_kg,
            "heavy_metals_kg": heavy_metals_kg,
            "voc_kg": voc_kg,
        },
        "emissions_water": {
            "metal_ions_kg": emissions_water_metal_ions_kg,
            "suspended_solids_kg": emissions_water_suspended_solids_kg,
            "fluoride_kg": emissions_water_fluoride_kg,
            "chemicals_kg": emissions_water_chemicals_kg,
        },
        "product_mass_kg": product_mass_kg,
    }
    return stage_result
