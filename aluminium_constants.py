# aluminium_constants.py
"""
Conversion & emission factors for Aluminium LCA calculations.
Values come from your specification (defaults). Edit if you have region-specific data.
"""

# Energy
KWH_TO_MJ = 3.6
DIESEL_MJ_PER_L = 38.6
HFO_MJ_PER_L = 40.9
COAL_MJ_PER_KG = 26.0

# Emission factors
CO2_PER_L_DIESEL = 2.68         # kg CO2 / L diesel
CO2_PER_L_HFO = 3.11            # kg CO2 / L heavy fuel oil
CO2_PER_MJ_NATGAS = 0.0561      # kg CO2 / MJ natural gas
CO2_PER_KG_COAL = 2.42          # kg CO2 / kg coal

CH4_PER_L_DIESEL = 0.00012
N2O_PER_L_DIESEL = 0.000005

# Default pollutant factors (tunable)
NOX_FACTOR_DIESEL = 0.0015      # kg NOx / L diesel (example)
PM_FACTOR_DIESEL = 0.0005       # kg PM / L diesel (example)

# SO2 conversion (coal sulfur to SO2 mass)
# For SO2: SO2 = S_fraction * coal_mass_kg * (MolarRatio SO2/S ~ 2)
SO2_SULFUR_CONVERSION = 2.0

# Other default factors
VOC_FACTOR_AUX = 0.001          # kg VOC per kg auxiliary material (example)
LEACHING_FACTOR = 0.0001        # metal ions per kg ore (example)
RUNOFF_FRACTION = 0.05          # suspended solids fraction
FLUORIDE_CONC_DEFAULT = 0.0     # default if not applicable
