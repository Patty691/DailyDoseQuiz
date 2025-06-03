import pandas as pd
import json
import requests
from bs4 import BeautifulSoup
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from typing import Dict, Any, List
import os

"""
This code generates a JSON file with medication clusters and their statistics.

WARNING: Before updating the CSV file (input), read the user manual in the README.md file.

For detailed instructions and context, also refer to the README.md file in the project root.
"""

# Constants for weight calculation
GEWICHT_PERCENTAGE = 0.99  # Weight for percentage_verstrekkingen
GEWICHT_GROEI = 0.01      # Weight for groei_percentage
GEWICHT_NIEUW = 2    # Weight multiplier for "nieuw in de lijst"

def adjust_csv():
    df = pd.read_csv("/Users/pattynooijen/Documents/VisualStudioCode/daily_dose_quiz/data/gip_top_500_verstrekkingen_2023.csv")

    # Add an "atc" column (first 5 characters of the ATC-code)
    df["ATC5"] =df["ATC-code"].str[:5] 

    # Split the ATC-code column 
    split_atc = df["ATC-code"].str.split(" ", n=1, expand=True) #df = dataframe

    df["ATC7"] = split_atc[0]  
    df["geneesmiddel"] = split_atc[1].str.extract(r'([^\(\)]+)')[0].str.strip()  
    df["merknaam"] = df["ATC-code"].str.extract(r'(\(.*\))')[0] 

    return df 

 
def get_atc_cluster_name(atc5_code: str) -> str:
    url = f"https://www.gipdatabank.nl/databank?infotype=g&label=00-totaal&tabel=B_01-basis&geg=gebr&item={atc5_code}"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Check if request was successful
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the relevant text on the page
        text = soup.get_text()

        # Extract the cluster name after the colon
        if ":" in text:
            cluster_name = text.split(":")[1].strip()
        else:
            cluster_name = "onbekend"

        # Extract only the part before the "|" character
        if "|" in cluster_name:
            cluster_name = cluster_name.split("|")[0].strip()

        return cluster_name

    except Exception as e:
        print(f"Error retrieving cluster name for ATC5 code {atc5_code}: {e}")
        return "onbekend"

def name_atc_clusters(df):
    atc_cluster_names = {}

    for atc5_code in df["ATC5"].unique():
        cluster_name = get_atc_cluster_name(atc5_code)
        atc_cluster_names[atc5_code] = cluster_name

    return atc_cluster_names

def create_clusters(df, atc_clusters, atc_cluster_names):  
    for index, row in df.iterrows():
        atc5_code = row["ATC5"]
        atc7_code = row["ATC7"]
        geneesmiddel = row["geneesmiddel"]
        merknaam = row["merknaam"]
        verstrekkingen_huidig = int(row["2023"].replace('.', ''))
        verstrekkingen_vorig = int(row["2022"].replace('.', ''))

        # Add cluster if not yet present
        if atc5_code not in atc_clusters:
            atc_clusters[atc5_code] = {
                "naam": atc_cluster_names.get(atc5_code, "onbekend"),
                "geneesmiddelen": [],
                "statistiek": {}
            }

        # Add medication to cluster
        atc_clusters[atc5_code]["geneesmiddelen"].append({
            "atc7": atc7_code,
            "geneesmiddel": geneesmiddel,
            "merknaam": merknaam,
            "verstrekkingen_huidig": verstrekkingen_huidig,
            "verstrekkingen_vorig": verstrekkingen_vorig,
        })

    return atc_clusters

def cluster_statistics(atc_clusters):
    totaal_verstrekkingen_dict = sum(
        med["verstrekkingen_huidig"] for cluster in atc_clusters.values() for med in cluster["geneesmiddelen"]
    ) #dict = dictionary

    for atc5_code in atc_clusters:
        totaal_verstrekkingen_huidig = sum(
            med["verstrekkingen_huidig"] for med in atc_clusters[atc5_code]["geneesmiddelen"]
        )
        totaal_verstrekkingen_vorig = sum(
            med["verstrekkingen_vorig"] for med in atc_clusters[atc5_code]["geneesmiddelen"]
        )
        aantal_geneesmiddelen = len(atc_clusters[atc5_code]["geneesmiddelen"])

        if totaal_verstrekkingen_vorig == 0:
            totaal_groei_percentage = "nieuw in de lijst"
        else:
            totaal_groei_percentage = ((totaal_verstrekkingen_huidig - totaal_verstrekkingen_vorig) / totaal_verstrekkingen_vorig) * 100
            totaal_groei_percentage = round(totaal_groei_percentage, 1)

        totaal_percentage = (totaal_verstrekkingen_huidig / totaal_verstrekkingen_dict) * 100
        totaal_percentage = round(totaal_percentage, 1)

        atc_clusters[atc5_code]["statistiek"] = {
            "aantal_geneesmiddelen": aantal_geneesmiddelen,
            "totaal_verstrekkingen_huidig": totaal_verstrekkingen_huidig,
            "totaal_verstrekkingen_vorig": totaal_verstrekkingen_vorig,
            "totaal_percentage_verstrekkingen": totaal_percentage,
            "totaal_groeipercentage": totaal_groei_percentage,
        }
    return atc_clusters

# Calculate statistics per atc7 
def medication_statistics(atc_clusters):
    for atc5_code in atc_clusters:
        totaal_verstrekkingen_huidig = sum(
            med["verstrekkingen_huidig"] for med in atc_clusters[atc5_code]["geneesmiddelen"]
        )

        for med in atc_clusters[atc5_code]["geneesmiddelen"]:
            percentage_verstrekkingen = round((med["verstrekkingen_huidig"] / totaal_verstrekkingen_huidig) * 100, 1) if totaal_verstrekkingen_huidig > 0 else 0

            if med["verstrekkingen_vorig"] != 0:
                groei_percentage = ((med["verstrekkingen_huidig"] - med["verstrekkingen_vorig"]) / med["verstrekkingen_vorig"]) * 100
            else:
                groei_percentage = "nieuw in de lijst"

            med["percentage_verstrekkingen"] = percentage_verstrekkingen
            med["groei_percentage"] = round(groei_percentage, 1) if isinstance(groei_percentage, float) else groei_percentage

    return atc_clusters

def calculate_weights(atc_clusters):
    """Calculate weights for both ATC5 clusters and individual medications."""
    total_verstrekkingen = sum(
        cluster["statistiek"]["totaal_verstrekkingen_huidig"] 
        for cluster in atc_clusters.values()
    )

    # Calculate weights for each ATC5 cluster
    for atc5_code, cluster in atc_clusters.items():
        # Calculate cluster weight based on total verstrekkingen and growth
        cluster_percentage = (cluster["statistiek"]["totaal_verstrekkingen_huidig"] / total_verstrekkingen) * 100
        cluster_growth = cluster["statistiek"]["totaal_groeipercentage"]
        
        if isinstance(cluster_growth, str) and cluster_growth.lower() == "nieuw in de lijst":
            # For new clusters, use a higher weight
            cluster["statistiek"]["gewicht"] = round(cluster_percentage * GEWICHT_NIEUW, 3)
        else:
            # For existing clusters, use the weighted formula
            cluster["statistiek"]["gewicht"] = round(
                cluster_percentage * GEWICHT_PERCENTAGE +
                cluster_growth * GEWICHT_GROEI,
                3
            )

        # Calculate weights for individual medications within the cluster
        for med in cluster["geneesmiddelen"]:
            if isinstance(med["groei_percentage"], str) and med["groei_percentage"].lower() == "nieuw in de lijst":
                # For new medications, use a higher weight
                med["gewicht"] = round(med["percentage_verstrekkingen"] * GEWICHT_NIEUW, 3)
            else:
                # For existing medications, use the weighted formula
                med["gewicht"] = round(
                    med["percentage_verstrekkingen"] * GEWICHT_PERCENTAGE +
                    med["groei_percentage"] * GEWICHT_GROEI,
                    3
                )

    return atc_clusters

def generate_medication_database(df, atc_cluster_names):
    atc_clusters = {}
    atc_clusters = create_clusters(df, atc_clusters, atc_cluster_names)
    atc_clusters = cluster_statistics(atc_clusters)
    atc_clusters = medication_statistics(atc_clusters)
    atc_clusters = calculate_weights(atc_clusters)
    return atc_clusters

if __name__ == "__main__":
    print("Bezig met samenstellen MedicationClustersDatabase") 
    df = adjust_csv()
    atc_cluster_names = name_atc_clusters(df)
    atc_clusters = generate_medication_database(df, atc_cluster_names)

    output_file = "/Users/pattynooijen/Documents/VisualStudioCode/daily_dose_quiz/data/MedicationClustersDatabase.json"
    try:
        with open(output_file, "w", encoding="utf-8") as json_file:
            json.dump(atc_clusters, json_file, ensure_ascii=False, indent=2)
        print(f"Data succesvol opgeslagen in: {output_file}")
    except Exception as e:
        print(f"Fout bij het opslaan van JSON-bestand: {e}")


""" 
Example json output:

{
  "A02BC": {
    "naam": "Protonpompremmers",
    "geneesmiddelen": [
      {
        "atc7": "A02BC02",
        "geneesmiddel": "Pantoprazol",
        "merknaam": "(Pantozol ®)",
        "verstrekkingen_huidig": 8094200,
        "verstrekkingen_vorig": 8046500,
        "percentage_verstrekkingen": 55.1,
        "groei_percentage": 0.6,
        "gewicht": 54.6
      },
      {
        "atc7": "A02BC01",
        "geneesmiddel": "Omeprazol",
        "merknaam": "(Losec mups ®)",
        "verstrekkingen_huidig": 5280000,
        "verstrekkingen_vorig": 5583800,
        "percentage_verstrekkingen": 35.9,
        "groei_percentage": -5.4,
        "gewicht": 35.3
      },
      {
        "atc7": "A02BC05",
        "geneesmiddel": "Esomeprazol",
        "merknaam": "(Nexium ®)",
        "verstrekkingen_huidig": 1111100,
        "verstrekkingen_vorig": 1131700,
        "percentage_verstrekkingen": 7.6,
        "groei_percentage": -1.8,
        "gewicht": 7.5
      },
      {
        "atc7": "A02BC04",
        "geneesmiddel": "Rabeprazol",
        "merknaam": "(Pariet ®)",
        "verstrekkingen_huidig": 144990,
        "verstrekkingen_vorig": 147770,
        "percentage_verstrekkingen": 1.0,
        "groei_percentage": -1.9,
        "gewicht": 1.0
      },
      {
        "atc7": "A02BC03",
        "geneesmiddel": "Lansoprazol",
        "merknaam": "(Prezal ®)",
        "verstrekkingen_huidig": 58485,
        "verstrekkingen_vorig": 60689,
        "percentage_verstrekkingen": 0.4,
        "groei_percentage": -3.6,
        "gewicht": 0.4
      }
    ],
    "statistiek": {
      "aantal_geneesmiddelen": 5,
      "totaal_verstrekkingen_huidig": 14688775,
      "totaal_verstrekkingen_vorig": 14970459,
      "totaal_percentage_verstrekkingen": 7.4,
      "totaal_groeipercentage": -1.9,
      "gewicht": 7.3
    }
  }
}
"""





# %%
