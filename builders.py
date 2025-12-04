import brightway2 as bw
import pandas as pd

# ---------- Brightway project ----------
PROJECT_NAME = "metal_lca"
bw.projects.set_current(PROJECT_NAME)


def build_single_metal_db(df_subset: pd.DataFrame, metal: str, route: str):
    """
    Build one Brightway database for a given (metal, route).

    df_subset must contain at least:
        metal, route, stage, CO2_per_kg
    """
    db_name = f"{metal}_{route}"

    # delete DB if it already exists (we are rebuilding from fresh data)
    if db_name in bw.databases:
        del bw.databases[db_name]

    db = bw.Database(db_name)

    # get CO2 biosphere flow
    bio = bw.Database("biosphere3")
    co2_flow = bio.search("carbon dioxide, fossil")[0]

    data = {}

    # ---- stage activities ----
    for _, row in df_subset.iterrows():
        stage = str(row["stage"])
        code = f"{metal}_{stage}"
        co2 = float(row["CO2_per_kg"])

        data[(db_name, code)] = {
            "name": f"{metal} {stage}",
            "reference product": f"{metal}, {stage}",
            "unit": "kilogram",
            "location": "GLO",
            "exchanges": [
                # production
                {
                    "input": (db_name, code),
                    "amount": 1.0,
                    "unit": "kilogram",
                    "type": "production",
                },
                # CO2 emission
                {
                    "input": co2_flow.key,
                    "amount": co2,
                    "unit": "kilogram",
                    "type": "biosphere",
                },
            ],
        }

    # ---- full-chain activity ----
    full_code = f"{metal}_full_chain"
    full_key = (db_name, full_code)

    exchanges = [
        {
            "input": full_key,
            "amount": 1.0,
            "unit": "kilogram",
            "type": "production",
        }
    ]

    for stage_name in df_subset["stage"].unique():
        exchanges.append(
            {
                "input": (db_name, f"{metal}_{stage_name}"),
                "amount": 1.0,
                "unit": "kilogram",
                "type": "technosphere",
            }
        )

    data[full_key] = {
        "name": f"{metal} full supply chain",
        "reference product": f"{metal}, ingot",
        "unit": "kilogram",
        "location": "GLO",
        "exchanges": exchanges,
    }

    db.write(data)
    print(f"✅ Built Brightway DB: {db_name} with {len(df_subset)} stages")


def build_metal_dbs_from_df(df: pd.DataFrame):
    """
    Build one DB per (metal, route) from a single DataFrame.

    Expected columns in df:
        metal, route, stage, CO2_per_kg
    """
    required = {"metal", "route", "stage", "CO2_per_kg"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in DataFrame: {missing}")

    # group by (metal, route) and build a DB for each
    for (metal, route), subset in df.groupby(["metal", "route"]):
        build_single_metal_db(subset, str(metal), str(route))
