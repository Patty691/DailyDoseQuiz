import math
import json

# Step 1: Retrieve Data (from an API or a downloaded file)
# TODO: Implement data retrieval from an API or a local file
# Example: Load data from a JSON file (if already downloaded)
# with open("medication_data.json", "r") as f:
#     medication_data = json.load(f)

# Simulated dataset (GIP Top 500 & fastest-growing medicines with ATC codes)
medication_data = {
    "Metformin": {"usage": 500000, "growth": 0.05, "atc": "A10BA", "atc7": "A10BA02"},
    "Paracetamol": {"usage": 1000000, "growth": 0.02, "atc": "N02BE", "atc7": "N02BE01"},
    "Rivaroxaban": {"usage": 200000, "growth": 0.10, "atc": "B01AF", "atc7": "B01AF01"},
    "Dapagliflozin": {"usage": 150000, "growth": 0.30, "atc": "A10BK", "atc7": "A10BK01"},
    "Upadacitinib": {"usage": 25000, "growth": 0.50, "atc": "L04AA", "atc7": "L04AA02"},
}

# atc cluster names (extend this list as needed)
atc_names = {
    "A10BA": "Biguanides (e.g., Metformin)",
    "N02BE": "Anilides (e.g., Paracetamol)",
    "B01AF": "Direct Oral Anticoagulants (DOACs)",
    "A10BK": "SGLT2 Inhibitors",
    "L04AA": "JAK Inhibitors"
}

# ATC7 medication names (if a reference list is available)
atc7_names = {
    "A10BA02": "Metformin",
    "N02BE01": "Paracetamol",
    "B01AF01": "Rivaroxaban",
    "A10BK01": "Dapagliflozin",
    "L04AA02": "Upadacitinib"
}

# Function to calculate weight based on logarithmic scale and growth factor
def calculate_weight(usage, growth=0):
    return math.log(usage + 1) * (1 + growth)

# Step 2: Group by atc and calculate total usage
atc_clusters = {}
for med, details in medication_data.items():
    atc = details["atc"]
    atc7 = details["atc7"]
    usage = details["usage"]
    growth = details["growth"]

    if atc not in atc_clusters:
        atc_clusters[atc] = {
            "name": atc_names.get(atc, "Unknown group"),
            "total_usage": 0,
            "medicines": {}
        }

    atc_clusters[atc]["total_usage"] += usage
    atc_clusters[atc]["medicines"][atc7] = {
        "name": atc7_names.get(atc7, "Unknown medication"),
        "usage": usage,
        "growth": growth
    }

# Step 3: Calculate weighted probabilities per atc group
for atc, details in atc_clusters.items():
    details["weight"] = calculate_weight(details["total_usage"])

    # Step 4: Calculate weighted probabilities per ATC7 within each atc group
    total_usage_atc = sum(med["usage"] for med in details["medicines"].values())

    for atc7, med_details in details["medicines"].items():
        med_usage = med_details["usage"]
        med_growth = med_details["growth"]

        atc7_weight = calculate_weight(med_usage, med_growth) / calculate_weight(total_usage_atc)

        details["medicines"][atc7]["weight"] = atc7_weight

# Step 5: Export to JSON
output_data = {
    atc: {
        "name": details["name"],
        "weight": details["weight"],
        "medicines": details["medicines"]
    }
    for atc, details in atc_clusters.items()
}

with open("atc_weighted_medicines.json", "w") as f:
    json.dump(output_data, f, indent=4)

# Debug: Print JSON output
print(json.dumps(output_data, indent=4))


"""
example json output

{
    "A10BA": {
        "name": "Biguanides (e.g., Metformin)",
        "weight": 10.82,
        "medicines": {
            "A10BA02": {
                "name": "Metformin",
                "usage": 500000,
                "growth": 0.05,
                "weight": 1.0
            }
        }
    },
    "N02BE": {
        "name": "Anilides (e.g., Paracetamol)",
        "weight": 13.81,
        "medicines": {
            "N02BE01": {
                "name": "Paracetamol",
                "usage": 1000000,
                "growth": 0.02,
                "weight": 1.0
            }
        }
    }
}"""