# copper_calculators.py
from typing import Dict, Any

# ---- Default constants (you can override per-request in payload) ----
KWH_TO_MJ = 3.6
L_DIESEL_MJ = 38.6
L_HEAVYOIL_MJ = 40.9
# use 26 MJ/kg or 29.3 in copper spec if needed - we keep 26 as safe default
KG_COAL_MJ = 26.0

# Emission factors (defaults)
GRID_CO2_KG_PER_KWH_GLOBAL = 0.48
GRID_CO2_KG_PER_KWH_INDIA = 0.82
DIESEL_CO2_KG_PER_L = 2.68
HEAVYOIL_CO2_KG_PER_L = 3.11
NG_CO2_KG_PER_MJ = 0.0561
COAL_CO2_KG_PER_KG = 2.42

# Other small EFs / factors
NOX_PER_GJ = 0.15  # kg NOx / GJ (0.15 kg/GJ)
NOX_PER_MJ = NOX_PER_GJ / 1000.0  # kg NOx / MJ
PM_COAL_KG_PER_KG = 0.001
PM_PER_DIESEL_L = 0.0005
WATER_SCARCITY_FACTOR = 1.0

# Helper: sum energy fields (returns MJ)


def _sum_energy_mj_from_inputs(inputs: Dict[str, Any]) -> float:
    total = 0.0
    if not inputs:
        return 0.0
    if "electricity_kWh" in inputs and inputs.get("electricity_kWh") is not None:
        total += float(inputs.get("electricity_kWh", 0.0)) * KWH_TO_MJ
    if "fuel_diesel_L" in inputs and inputs.get("fuel_diesel_L") is not None:
        total += float(inputs.get("fuel_diesel_L", 0.0)) * L_DIESEL_MJ
    if "fuel_heavyOil_L" in inputs and inputs.get("fuel_heavyOil_L") is not None:
        total += float(inputs.get("fuel_heavyOil_L", 0.0)) * L_HEAVYOIL_MJ
    if "fuel_coal_kg" in inputs and inputs.get("fuel_coal_kg") is not None:
        # copper spec used 29.3 MJ/kg for coal; choose constant if provided in inputs use that
        coal_mj = float(inputs.get("fuel_coal_kg", 0.0)) * KG_COAL_MJ
        total += coal_mj
    if "fuel_naturalGas_MJ" in inputs and inputs.get("fuel_naturalGas_MJ") is not None:
        total += float(inputs.get("fuel_naturalGas_MJ", 0.0))
    return total

# -----------------------
# Copper: Mining stage
# -----------------------


def compute_copper_mining(inputs: Dict[str, Any]) -> Dict[str, Any]:
    # inputs expected: ore_input_kg, ore_grade_percent, process_recovery, electricity_kWh,
    # fuel_diesel_L, fuel_naturalGas_MJ, freshwater_m3, process_water_m3, land_area_m2,
    # auxiliary_materials_kg, transport_*_tkm
    ore_input_kg = float(inputs.get("ore_input_kg", 0.0) or 0.0)
    ore_grade_percent = float(inputs.get("ore_grade_percent", 0.0) or 0.0)
    # stage efficiency / yield (if provided else assume 0.9)
    eta_stage = float(inputs.get("process_recovery", 0.9) or 0.9)

    # yield metal in tonnes
    mwf = ore_grade_percent / 100.0  # mass fraction of metal in ore
    yield_metal_t = (ore_input_kg * mwf * eta_stage) / 1000.0

    total_material_input_kg = ore_input_kg + \
        float(inputs.get("auxiliary_materials_kg", 0.0) or 0.0)

    energy_mj = _sum_energy_mj_from_inputs(inputs)

    # water
    freshwater_m3 = float(inputs.get("freshwater_m3", 0.0) or 0.0)
    process_water_m3 = float(inputs.get("process_water_m3", 0.0) or 0.0)
    water_consumed_m3 = freshwater_m3 + process_water_m3 - \
        float(inputs.get("water_returned_m3", 0.0) or 0.0)

    # land occupied
    land_occupied_m2 = float(inputs.get("land_area_m2", 0.0) or 0.0)

    # waste (tailings + overburden approximation)
    waste_solid_kg = max(0.0, ore_input_kg * (1.0 - mwf) * (1.0 - eta_stage))

    # Emissions: electricity + diesel + natural gas
    grid_factor = float(inputs.get(
        "grid_co2_factor", GRID_CO2_KG_PER_KWH_GLOBAL) or GRID_CO2_KG_PER_KWH_GLOBAL)
    emissions_co2 = 0.0
    if "electricity_kWh" in inputs and inputs.get("electricity_kWh") is not None:
        emissions_co2 += float(inputs.get("electricity_kWh")) * grid_factor
    emissions_co2 += float(inputs.get("fuel_diesel_L", 0.0)
                           or 0.0) * DIESEL_CO2_KG_PER_L
    emissions_co2 += float(inputs.get("fuel_heavyOil_L", 0.0)
                           or 0.0) * HEAVYOIL_CO2_KG_PER_L
    emissions_co2 += float(inputs.get("fuel_naturalGas_MJ",
                           0.0) or 0.0) * NG_CO2_KG_PER_MJ
    emissions_co2 += float(inputs.get("fuel_coal_kg", 0.0)
                           or 0.0) * COAL_CO2_KG_PER_KG

    # SO2 from sulfur in ore (if S_content provided)
    s_content = float(inputs.get("S_content", 0.0) or 0.0)  # fraction
    acid_recovery_factor = float(inputs.get(
        "acid_recovery_factor", 0.85) or 0.85)
    # kg S -> convert to SO2 kg via factor 2 (approx) per spec
    emissions_so2 = (s_content * ore_input_kg * 2.0) * \
        (1.0 - acid_recovery_factor)

    # NOx approx from fuel energy
    total_fuel_mj = _sum_energy_mj_from_inputs(inputs)
    emissions_nox = total_fuel_mj * NOX_PER_MJ

    # particulates
    particulate = float(inputs.get("fuel_diesel_L", 0.0) or 0.0) * PM_PER_DIESEL_L + \
        float(inputs.get("fuel_coal_kg", 0.0) or 0.0) * PM_COAL_KG_PER_KG

    # water emissions
    emissions_water_metal_ions = ore_input_kg * \
        float(inputs.get("metal_leaching_factor", 0.0003) or 0.0003)
    emissions_water_ss = waste_solid_kg * \
        float(inputs.get("runoff_fraction", 0.02) or 0.02)

    # Simple GWP: CO2 + 25*CH4 + 298*N2O if those are known - here we only have CO2 from fuels
    # But we will add tiny combustion CH4/N2O estimates:
    emissions_ch4 = total_fuel_mj * 0.001 / 1000.0   # per spec small factor
    emissions_n2o = total_fuel_mj * 0.0001 / 1000.0
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
            "so2_kg": emissions_so2,
            "nox_kg": emissions_nox,
            "particulates_kg": particulate,
            "ch4_kg": emissions_ch4,
            "n2o_kg": emissions_n2o
        },
        "gwp_kgCO2e": gwp,
        "emissions_water": {
            "metal_ions_kg": emissions_water_metal_ions,
            "suspended_solids_kg": emissions_water_ss
        }
    }

# -----------------------
# Copper: Extraction (smelting + refining)
# -----------------------


def compute_copper_extraction(inputs: Dict[str, Any]) -> Dict[str, Any]:
    # inputs expected: ore_input_kg (concentrate), fraction_alumina/fraction_cu etc.,
    ore_input_kg = float(inputs.get("ore_input_kg", 0.0) or 0.0)
    # fraction of metal in concentrate
    fraction_metal = float(inputs.get("fraction_metal", 0.0) or 0.0)
    reduction_efficiency = float(inputs.get(
        "reduction_efficiency", 0.95) or 0.95)

    # yield metal tonnes
    yield_metal_t = (ore_input_kg * fraction_metal *
                     reduction_efficiency) / 1000.0

    total_material_input_kg = ore_input_kg + \
        float(inputs.get("auxiliary_materials_kg", 0.0) or 0.0)

    energy_mj = _sum_energy_mj_from_inputs(inputs)

    # waste
    impurity_fraction = float(inputs.get("impurity_fraction", 0.0) or 0.0)
    anode_residue_kg = float(inputs.get("anode_residue_kg", 0.0) or 0.0)
    waste_solid_kg = (ore_input_kg * impurity_fraction) + anode_residue_kg

    # emissions from energy + process
    grid_factor = float(inputs.get(
        "grid_co2_factor", GRID_CO2_KG_PER_KWH_GLOBAL) or GRID_CO2_KG_PER_KWH_GLOBAL)
    emissions_co2 = 0.0
    if "electricity_kWh" in inputs and inputs.get("electricity_kWh") is not None:
        emissions_co2 += float(inputs.get("electricity_kWh")) * grid_factor
    emissions_co2 += float(inputs.get("fuel_coal_kg", 0.0)
                           or 0.0) * COAL_CO2_KG_PER_KG
    emissions_co2 += float(inputs.get("fuel_naturalGas_MJ",
                           0.0) or 0.0) * NG_CO2_KG_PER_MJ
    # process CO2 from smelting chemical reactions (approx)
    process_co2 = float(inputs.get("CO2_proc_smelting", 400.0)
                        or 400.0)  # per tonne Cu typical
    # scale by metal produced (if yield_metal > 0)
    emissions_co2 += process_co2 * (yield_metal_t or 0.0)

    # PFCs: if present
    cf4_kg = float(inputs.get("anode_effect_minutes", 0.0) or 0.0) * \
        float(inputs.get("CF4_factor", 0.0) or 0.0)
    c2f6_kg = float(inputs.get("anode_effect_minutes", 0.0)
                    or 0.0) * float(inputs.get("C2F6_factor", 0.0) or 0.0)
    pfc_co2e = cf4_kg * float(inputs.get("CF4_GWP", 7390.0) or 7390.0) + \
        c2f6_kg * float(inputs.get("C2F6_GWP", 12200.0) or 12200.0)

    # SO2 from sulfur in feed (if S_content provided)
    s_content = float(inputs.get("S_content", 0.0) or 0.0)
    acid_recovery_factor = float(inputs.get(
        "acid_recovery_factor", 0.85) or 0.85)
    emissions_so2 = (s_content * ore_input_kg * 2.0) * \
        (1.0 - acid_recovery_factor)

    # other small emissions
    total_fuel_mj = _sum_energy_mj_from_inputs(inputs)
    emissions_nox = total_fuel_mj * NOX_PER_MJ
    particulates_kg = float(inputs.get(
        "fuel_coal_kg", 0.0) or 0.0) * PM_COAL_KG_PER_KG

    gwp = emissions_co2 + pfc_co2e

    # water emissions
    emissions_water_metal_ions = ore_input_kg * \
        float(inputs.get("metal_leaching_factor", 0.0003) or 0.0003)
    emissions_water_chemicals = float(
        inputs.get("process_water_m3", 0.0) or 0.0) * 0.5

    return {
        "yield_metal_t": yield_metal_t,
        "total_material_input_kg": total_material_input_kg,
        "energy_MJ": energy_mj,
        "waste_solid_kg": waste_solid_kg,
        "waste_hazardous_kg": waste_solid_kg * 0.05,
        "emissions": {
            "co2_kg": emissions_co2,
            "cf4_kg": cf4_kg,
            "c2f6_kg": c2f6_kg,
            "pfc_co2e_kgCO2e": pfc_co2e,
            "so2_kg": emissions_so2,
            "nox_kg": emissions_nox,
            "particulates_kg": particulates_kg
        },
        "gwp_kgCO2e": gwp,
        "emissions_water": {
            "metal_ions_kg": emissions_water_metal_ions,
            "chemicals_kg": emissions_water_chemicals
        }
    }

# -----------------------
# Copper: Manufacturing (semifab, casting, rolling, extrusion)
# -----------------------


def compute_copper_manufacturing(inputs: Dict[str, Any]) -> Dict[str, Any]:
    metal_input_kg = float(inputs.get(
        "metal_input_kg", inputs.get("metal_input", 0.0)) or 0.0)
    process_yield = float(inputs.get("process_yield", 1.0) or 1.0)
    yield_metal_t = (metal_input_kg * process_yield) / 1000.0

    total_material_input_kg = metal_input_kg + \
        float(inputs.get("auxiliary_materials_kg", 0.0) or 0.0)
    energy_mj = _sum_energy_mj_from_inputs(inputs)

    freshwater_m3 = float(inputs.get("freshwater_m3", 0.0) or 0.0)
    process_water_m3 = float(inputs.get("process_water_m3", 0.0) or 0.0)
    water_consumed_m3 = freshwater_m3 + process_water_m3 - \
        float(inputs.get("cooling_water_returned", 0.0) or 0.0)

    emissions_co2 = 0.0
    grid_factor = float(inputs.get(
        "grid_co2_factor", GRID_CO2_KG_PER_KWH_GLOBAL) or GRID_CO2_KG_PER_KWH_GLOBAL)
    if "electricity_kWh" in inputs and inputs.get("electricity_kWh") is not None:
        emissions_co2 += float(inputs.get("electricity_kWh")) * grid_factor
    emissions_co2 += float(inputs.get("fuel_naturalGas_MJ",
                           0.0) or 0.0) * NG_CO2_KG_PER_MJ

    nox_kg = float(inputs.get("fuel_naturalGas_MJ", 0.0) or 0.0) * NOX_PER_MJ
    particulates_kg = float(inputs.get(
        "auxiliary_materials_kg", 0.0) or 0.0) * 0.001

    gwp = emissions_co2

    return {
        "yield_metal_t": yield_metal_t,
        "total_material_input_kg": total_material_input_kg,
        "energy_MJ": energy_mj,
        "water_m3": water_consumed_m3,
        "waste_solid_kg": float(inputs.get("scrap_kg", 0.0) or 0.0),
        "emissions": {
            "co2_kg": emissions_co2,
            "nox_kg": nox_kg,
            "particulates_kg": particulates_kg
        },
        "gwp_kgCO2e": gwp
    }

# -----------------------
# Combined wrapper for copper
# -----------------------


def compute_combined_lca_copper(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    payload contains:
      - projectId, scenarioId, route, functionalUnit_kg, recycling_rate
      - inputs: { mining: {...}, extraction: {...}, manufacturing: {...} }
    Returns breakdown & totals.
    """
    inputs = payload.get("inputs", {}) or {}
    mining_inputs = inputs.get("mining", {}) or {}
    extraction_inputs = inputs.get("extraction", {}) or {}
    manufacturing_inputs = inputs.get("manufacturing", {}) or {}

    mining_res = compute_copper_mining(mining_inputs) if mining_inputs else {}
    extraction_res = compute_copper_extraction(
        extraction_inputs) if extraction_inputs else {}
    manufacturing_res = compute_copper_manufacturing(
        manufacturing_inputs) if manufacturing_inputs else {}

    total_gwp = 0.0
    total_energy = 0.0
    total_water = 0.0

    for res in (mining_res, extraction_res, manufacturing_res):
        if not res:
            continue
        total_gwp += float(res.get("gwp_kgCO2e", 0.0) or 0.0)
        total_energy += float(res.get("energy_MJ", 0.0) or 0.0)
        total_water += float(res.get("water_m3", 0.0) or 0.0)

    recycling_rate = float(payload.get("recycling_rate", 0.0) or 0.0)
    primary_route_gwp = float(payload.get(
        "primary_route_gwp_kgCO2e", total_gwp) or total_gwp)
    avoided = recycling_rate * primary_route_gwp

    # minimal LCIA placeholders (backend may compute full LCIA later)
    lcia = {
        "global_warming_kg_co2e": total_gwp,
        "acidification_kg_so2e": (mining_res.get("emissions", {}).get("so2_kg", 0.0) + extraction_res.get("emissions", {}).get("so2_kg", 0.0)) * 1.2,
        "eutrophication_kg_po4e": (mining_res.get("emissions", {}).get("nox_kg", 0.0) + extraction_res.get("emissions", {}).get("nox_kg", 0.0)) * 0.1,
        "water_depletion_m3": total_water,
        "resource_depletion_kg_resource_eq": float(mining_inputs.get("ore_input_kg", 0.0)),
        "human_toxicity_ctu": 0.0,
        "ecotoxicity_ctu": 0.0
    }

    return {
        "metadata": {
            "projectId": payload.get("projectId"),
            "scenarioId": payload.get("scenarioId"),
            "route": payload.get("route")
        },
        "functionalUnit_kg": float(payload.get("functionalUnit_kg", 1.0) or 1.0),
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
