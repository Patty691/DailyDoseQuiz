import pandas as pd
import json
import requests
from bs4 import BeautifulSoup

"""
#Create CSV file manually

Input data from GIP database downloaded as CSV:
https://www.gipdatabank.nl/databank?infotype=g&label=00-totaal&tabel_d_00-totaal=B_01-basis&tabel_g_00-totaal=R_46_top500_atclaatst&tabel_h_00-totaal=B_01-basis&geg=vs&spec=&item= 
(geneesmiddelen, top 500, uitgiftes, geen specificatie) 

When updating to new version:
1. make sure the headers are all in 1 row (manually adjust if needed)
2. check if the headers have the same names as before, corresponding with the code in this program. If not, adjust the headers or code accordingly.
    - adjust the years in the code, or find out how this would be done if you don't want to adjust the code.
3. back up the previous database, before overwriting it    
    
"""

def adjust_csv():
    # Read the CSV file
    df = pd.read_csv("/Users/pattynooijen/Documents/VisualStudioCode/daliy_dose_quiz/data/gip_top_500_verstrekkingen_2023.csv")

    # Adjust the CSV file

    # Step 1: Add an "atc" column (first 5 characters of the ATC-code)
    df.insert(1, "ATC5", df["ATC-code"].str[:5])

    # Step 2: Split the ATC-code column 
    split_atc = df["ATC-code"].str.split(" ", n=1, expand=True)

    df["ATC7"] = split_atc[0]  # ATC-code (bijv. A02BC02)
    df["geneesmiddel"] = split_atc[1].str.extract(r'([^\(\)]+)')[0].str.strip()  # Extract drug name
    df["merknaam"] = df["ATC-code"].str.extract(r'(\(.*\))')[0]  # Extract brand name

    # Reorder columns so that ATC7, geneesmiddel, and merknaam appear right after atc
    column_order = ["Rang 2023", "ATC5", "ATC7", "geneesmiddel", "merknaam"] + [col for col in df.columns if col not in ["Rang 2023", "ATC5", "ATC7", "geneesmiddel", "merknaam"]]
    df = df[column_order]

    # Remove the original "ATC-code" column (optional, if no longer needed)
    df.drop(columns=["ATC-code"], inplace=True, errors="ignore")

    #placeholder: want to save the file?
    return df 

 
def get_atc_cluster_name(atc5_code):
    # Web scraping URL format
    url = f"https://www.gipdatabank.nl/databank?infotype=g&label=00-totaal&tabel=B_01-basis&geg=gebr&item={atc5_code}"

    # Perform the web scraping
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
            cluster_name = "Unknown"

        # Extract only the part before the "|" character
        if "|" in cluster_name:
            cluster_name = cluster_name.split("|")[0].strip()

        return cluster_name

    except Exception as e:
        print(f"Error retrieving cluster name for ATC5 code {atc5_code}: {e}")
        return "Unknown"
    
def name_atc_clusters(df):
    atc_cluster_names = {}

    for atc5_code in df["ATC5"].unique():
        cluster_name = get_atc_cluster_name(atc5_code)
        atc_cluster_names[atc5_code] = cluster_name

    return atc_cluster_names

def classify_medication(df, atc_clusters, atc_cluster_names):
    # Loop through the dataframe and fill the atc_clusters
    for index, row in df.iterrows():
        atc5_code = row["ATC5"]
        atc7_code = row["ATC7"]
        geneesmiddel = row["geneesmiddel"]
        merknaam = row["merknaam"]
        verstrekkingen_huidig = int(row["2023"].replace('.', ''))
        verstrekkingen_vorig = int(row["2022"].replace('.', ''))
        
       # Add the atc code to the dictionary if it doesn't already exist
        if atc5_code not in atc_clusters:
            atc_clusters[atc5_code] = {
                "naam": atc_cluster_names.get(atc5_code, "Unknown"),  # Use the cluster name
                "geneesmiddelen": [],
                "statistiek": []
            }
        
        # Add the medication information to the cluster
        atc_clusters[atc5_code]["geneesmiddelen"].append({
            "atc7": atc7_code,
            "geneesmiddel": geneesmiddel,
            "merknaam": merknaam,
            "verstrekkingen_huidig": verstrekkingen_huidig,
            "verstrekkingen_vorig": verstrekkingen_vorig,       
        })

    # After populating the dictionary, calculate total statistics for the atc cluster (db = database)
    totaal_verstrekkingen_db = sum(
    med["verstrekkingen_huidig"] for cluster in atc_clusters.values() for med in cluster["geneesmiddelen"]
    ) 
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

        totaal_percentage = (totaal_verstrekkingen_huidig / totaal_verstrekkingen_db) * 100
        totaal_percentage = round(totaal_percentage, 1)

        # add statistics to atc cluster
        atc_clusters[atc5_code]["statistiek"] = {
            "aantal_geneesmiddelen": aantal_geneesmiddelen,
            "totaal_verstrekkingen_huidig": totaal_verstrekkingen_huidig,
            "totaal_verstrekkingen_vorig": totaal_verstrekkingen_vorig,
            "totaal_percentage_verstrekkingen": totaal_percentage,
            "totaal_groeipercentage": totaal_groei_percentage,
            
    }
        
   # Add statistics to each atc7 medication
        for med in atc_clusters[atc5_code]["geneesmiddelen"]:
            percentage_verstrekkingen = round((med["verstrekkingen_huidig"] / totaal_verstrekkingen_huidig) * 100, 1) if totaal_verstrekkingen_huidig > 0 else 0

            if med["verstrekkingen_vorig"] != 0:
                groei_percentage = ((med["verstrekkingen_huidig"] - med["verstrekkingen_vorig"]) / med["verstrekkingen_vorig"]) * 100
            else:
                groei_percentage = "nieuw in de lijst"

            med["percentage_verstrekkingen"] = percentage_verstrekkingen
            med["groei_percentage"] = round(groei_percentage, 1) if isinstance(groei_percentage, float) else groei_percentage

    return atc_clusters
 
 
def test_functions():
    # Test the functions
    df = adjust_csv()  # Laad en verwerk de CSV
    atc_cluster_names = name_atc_clusters(df)  # Geef de DataFrame door aan name_atc_clusters
    atc_clusters = classify_medication(df, {}, atc_cluster_names)  # Geef een lege dictionary door voor atc_clusters

    # Print het eerste cluster
    first_cluster_key = next(iter(atc_clusters))
    first_cluster_value = atc_clusters[first_cluster_key]
    print(f"First cluster key: {first_cluster_key}")
    print(f"First cluster value: {json.dumps(first_cluster_value, ensure_ascii=False, indent=2)}")



# Example usage Uncomment the following line to run tests
# df = adjust_csv()
# print(df.head())

# Uncomment the following line to run the complete function test
# test_functions()


if __name__ == "__main__":
    # Load and adjust CSV
    df = adjust_csv() 

    # Generate clusternamens (webscraping)
    atc_cluster_names = name_atc_clusters(df)  

    # Classify medication and add statistics
    atc_clusters = classify_medication(df, {}, atc_cluster_names)  

    # Safe to database
    output_file = "/Users/pattynooijen/Documents/VisualStudioCode/daliy_dose_quiz/data/MedicationClustersDatabase.json"
    try:
        with open(output_file, "w", encoding="utf-8") as json_file:
            json.dump(atc_clusters, json_file, ensure_ascii=False, indent=2)
        print(f"Data succesvol opgeslagen in: {output_file}")
    except Exception as e:
        print(f"Fout bij het opslaan van JSON-bestand: {e}")

#main()

"""
Example json output:

First cluster key: A02BC
First cluster value: {
  "naam": "Protonpompremmers",
  "geneesmiddelen": [
    {
      "atc7": "A02BC02",
      "geneesmiddel": "Pantoprazol",
      "merknaam": "(Pantozol ®)",
      "verstrekkingen_huidig": 8094200,
      "verstrekkingen_vorig": 8046500,
      "percentage_verstrekkingen": 55.1,
      "groei_percentage": 0.6
    },
    {
      "atc7": "A02BC01",
      "geneesmiddel": "Omeprazol",
      "merknaam": "(Losec mups ®)",
      "verstrekkingen_huidig": 5280000,
      "verstrekkingen_vorig": 5583800,
      "percentage_verstrekkingen": 35.9,
      "groei_percentage": -5.4
    },
    {
      "atc7": "A02BC05",
      "geneesmiddel": "Esomeprazol",
      "merknaam": "(Nexium ®)",
      "verstrekkingen_huidig": 1111100,
      "verstrekkingen_vorig": 1131700,
      "percentage_verstrekkingen": 7.6,
      "groei_percentage": -1.8
    },
    {
      "atc7": "A02BC04",
      "geneesmiddel": "Rabeprazol",
      "merknaam": "(Pariet ®)",
      "verstrekkingen_huidig": 144990,
      "verstrekkingen_vorig": 147770,
      "percentage_verstrekkingen": 1.0,
      "groei_percentage": -1.9
    },
    {
      "atc7": "A02BC03",
      "geneesmiddel": "Lansoprazol",
      "merknaam": "(Prezal ®)",
      "verstrekkingen_huidig": 58485,
      "verstrekkingen_vorig": 60689,
      "percentage_verstrekkingen": 0.4,
      "groei_percentage": -3.6
    }
  ],
  "statistiek": {
    "aantal_geneesmiddelen": 5,
    "totaal_verstrekkingen_huidig": 14688775,
    "totaal_verstrekkingen_vorig": 14970459,
    "totaal_percentage_verstrekkingen": 7.4,
    "totaal_groeipercentage": -1.9
  }
}

"""


# create json file from this (as a main function)
#completely evaluate the code: uniformity and understanding each line, to educate yourself


## create an excel on atc level to see the data (seperate program?)
## create unit tests and datatests
### create some kind of export to further test if data is correct (other clusters)
