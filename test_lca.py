import brightway2 as bw

bw.projects.set_current("metal_lca")

db = bw.Database("aluminium_simple")

method = (
    "IPCC 2013 no LT",
    "climate change no LT",
    "global temperature change potential (GTP100) no LT"
)

print("\n===== Checking activities =====")
for act in db:
    print("-", act['name'], "→", act.key)

# ---- test mining ----
mining = db.get("aluminium_mining")
lca = bw.LCA({mining: 1}, method)
lca.lci()
lca.lcia()
print("\nMining CO2:", lca.score)

# ---- test extraction ----
extract = db.get("aluminium_extraction")
lca = bw.LCA({extract: 1}, method)
lca.lci()
lca.lcia()
print("Extraction CO2:", lca.score)

# ---- test manufacturing ----
manu = db.get("aluminium_manufacturing")
lca = bw.LCA({manu: 1}, method)
lca.lci()
lca.lcia()
print("Manufacturing CO2:", lca.score)

# ---- test full chain ----
full = db.get("aluminium_full_chain")
lca = bw.LCA({full: 1}, method)
lca.lci()
lca.lcia()
print("\nFull Chain CO2:", lca.score)
