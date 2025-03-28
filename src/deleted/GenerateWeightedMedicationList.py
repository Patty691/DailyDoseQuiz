




#oude versie. check generate_new. 
# 
# 
# 
# 
# 
# houdt de nodige teksten uit dit bestand ook











import pandas as pd 
import json
import math
import random


#to do:

# Predefined dictionary mapping atc codes to atc cluster names (in separate file)
atc_CLUSTER_NAMES = {
    # "atc5_code": "Cluster Name"
}

#placeholders
#add json example """""" 

"""
Input data from GIP database downloaded as CSV:
https://www.gipdatabank.nl/databank?infotype=g&label=00-totaal&tabel_d_00-totaal=B_01-basis&tabel_g_00-totaal=R_46_top500_atclaatst&tabel_h_00-totaal=B_01-basis&geg=vs&spec=&item= 
(geneesmiddelen, top 500, uitgiftes, geen specificatie) 

When updating to new version:
1. make sure the headers are all in 1 row (manually adjust if needed)
2. check if the headers have the same names as before, corresponding with the code in this program. If not, adjust the headers or code accordingly."""


# Load data from GIP database (downloaded file)

df = pd.read_csv("/Users/pattynooijen/Documents/VisualStudioCode/daliy_dose_quiz/data/gip_top_500_verstrekkingen_2023.csv")
print("Column names:", df.columns)


# Edit the CSV file: add atc code, split ATC 7 code and description

# Add an "atc" column (first 5 characters of the ATC-code)
df.insert(1, "atc", df["ATC-code"].str[:5])

# Split the ATC-code column 
split_atc = df["ATC-code"].str.split(" ", n=1, expand=True)

df["ATC7"] = split_atc[0]  # ATC-code (bijv. A02BC02)
df["Geneesmiddel"] = split_atc[1].str.extract(r'([^\(\)]+)')[0].str.strip()  # Extract drug name
df["Merknaam"] = df["ATC-code"].str.extract(r'(\(.*\))')[0]  # Extract brand name

# Reorder columns so that ATC7, Geneesmiddel, and Merknaam appear right after atc
column_order = ["Rang 2023", "atc", "ATC7", "Geneesmiddel", "Merknaam"] + [col for col in df.columns if col not in ["Rang 2023", "atc", "ATC7", "Geneesmiddel", "Merknaam", "ATC-code"]]
df = df[column_order]

# Remove the original "ATC-code" column (optional, if no longer needed)
df.drop(columns=["ATC-code"], inplace=True, errors="ignore")


# Classification of Medications

def classify_medications(data):
    #Classify medications at the atc level and nest ATC7 data.
    classified_data = {}
    for entry in data:
        atc = entry["left 5 characters of atc7"]
        atc7 = entry["atc7"]
        usage = entry["usage latest year"]
        growth = entry.get("growth", 0)

        if atc not in classified_data:
            classified_data[atc] = {"name": atc_CLUSTER_NAMES.get(atc, "Unknown"), "medications": []}
        
        classified_data[atc]["medications"].append({"atc7": atc7, "usage": usage, "growth": growth})
    return classified_data

# Step 4: Weighting at atc level
def calculate_weights(classified_data):
    #Calculate weights for top 500 and growth medications.
    weighted_data = {}
    for atc, data in classified_data.items():
        total_usage = sum(med["usage"] for med in data["medications"])
        growth_medications = [m for m in data["medications"] if m["growth"] > 0]
        
        weight_top500 = math.log(total_usage) if total_usage > 0 else 0
        weight_growth = sum(math.log(m["usage"]) * m["growth"] for m in growth_medications if m["usage"] > 0)
        
        weighted_data[atc] = {
            "name": data["name"],
            "weight_top500": weight_top500,
            "weight_growth": weight_growth,
            "medications": data["medications"]
        }
    return weighted_data

# Step 5: Weighting at ATC7 level
def weight_atc7(medications):
   # Calculate weight for each ATC7 medication within its cluster.
    for med in medications:
        med["weight"] = math.log(med["usage"]) if med["usage"] > 0 else 0

# Step 6: Store the output in JSON
def save_to_json(data, filename="ATC_weighted_medication_usage.json"):
    #Save structured data to JSON file.
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# Main execution
def main():
    data = load_gip_data()
    classified_data = classify_medications(data)
    weighted_data = calculate_weights(classified_data)
    
    for atc in weighted_data:
        weight_atc7(weighted_data[atc]["medications"])
    
    save_to_json(weighted_data)
    

if __name__ == "__main__":
    main()
"""