import brightway2 as bw

PROJECT_NAME = "metal_lca"

bw.projects.set_current(PROJECT_NAME)

if "biosphere3" not in bw.databases:
    print("Running bw2setup() to install biosphere3 + LCIA methods...")
    bw.bw2setup()
else:
    print("Project already initialised with biosphere3.")
