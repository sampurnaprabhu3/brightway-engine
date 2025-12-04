import brightway2 as bw

PROJECT_NAME = "metal_lca"
DB_NAME = "aluminium_primary_global"

print(f"Using Brightway project: {PROJECT_NAME}")
bw.projects.set_current(PROJECT_NAME)

print("\n📚 Available databases:")
for name in bw.databases:
    print(" -", name)

if DB_NAME not in bw.databases:
    print(f"\n❌ Database '{DB_NAME}' NOT found.")
else:
    db = bw.Database(DB_NAME)
    print(f"\n✅ Activities in '{DB_NAME}':")
    for act in db:
        key = act.key         # ('aluminium_primary_global', 'some_code')
        code = act['code']    # the internal code string
        name = act['name']    # human-readable name
        print("  ", key, "| code:", code, "| name:", name)
