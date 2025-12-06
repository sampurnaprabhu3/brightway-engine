# aluminium_constants.py
# Default conversion factors and emission factors. Tweak to match your dataset.

# energy conversions
KWH_TO_MJ = 3.6
L_DIESEL_MJ = 38.6
L_HEAVYOIL_MJ = 40.9
KG_COAL_MJ = 26.0  # MJ per kg coal

# default emission factors (kg)
GRID_CO2_KG_PER_KWH = 0.5        # change to region-specific grid factor
DIESEL_CO2_KG_PER_L = 2.68
HEAVYOIL_CO2_KG_PER_L = 3.11
NG_CO2_KG_PER_MJ = 0.0561
COAL_CO2_KG_PER_KG = 2.42
ANODE_CARBON_CO2_KG_PER_KG = 3.67

# small GHGs and other
DIESEL_CH4_KG_PER_L = 0.00012
DIESEL_N2O_KG_PER_L = 0.000005

# particulate, NOx placeholders
PM_PER_DIESEL_L = 0.0005
NOX_PER_GAS_MJ = 0.0003
PM_PER_COAL_KG = 0.002

# LCIA Characterisation factors (very simplified)
CF_GWP_CO2E = {
    # resource -> kg CO2e per unit
    "co2": 1.0,
    "ch4": 28.0,   # global warming potential 100yr
    "n2o": 265.0
}

# scarcity / water factors
WATER_SCARCITY_FACTOR = 1.0

# placeholders for other LCIA categories (expand later)
