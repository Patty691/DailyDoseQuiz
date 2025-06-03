import random
import json
import os
import pandas as pd  
from typing import Dict, Any, List, Tuple

# als bestand klaar is:
## code opschonen en relevante info in readme.md 
## unit test en integratie test maken
#   Hoe ziet de app eruit. tip: bij 3 vragen per dag 3 over zelfde cluster.

NUM_CLUSTERS = 2      # Aantal ATC5 clusters om te selecteren
NUM_MEDICINES = 1     # Aantal geneesmiddelen om te selecteren per cluster

def load_data(filename: str) -> dict[str, any]:
    """Laad de medicatie database met vooraf berekende gewichten."""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"Error: Bestand niet gevonden: {filename}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: JSON bestand kan niet worden gelezen: {e}")
        return None

def weighted_selection_unique(choices: list[str], gewichten: list[float], k: int) -> list[str]:
    """
    Selecteer `k` unieke items uit `choices` op basis van hun gewichten.
    Deze functie wordt alleen gebruikt voor cluster selectie (ATC5 niveau).
    
    Args:
        choices: Lijst van items om uit te kiezen
        gewichten: Lijst van gewichten uit de database voor elk item
        k: Aantal te selecteren items
        
    Returns:
        Lijst van uniek geselecteerde items
    """
    if not choices or not gewichten or k < 1:
        return []
        
    selected = []
    available_indices = list(range(len(choices)))
    
    for _ in range(min(k, len(choices))):
        if not available_indices:
            break
            
        # Haal gewichten op voor beschikbare keuzes
        current_gewichten = [gewichten[i] for i in available_indices]
        total_gewicht = sum(current_gewichten)
        
        if total_gewicht <= 0:
            break
            
        # Normaliseer gewichten voor selectie
        normalized_gewichten = [w/total_gewicht for w in current_gewichten]
        
        # Selecteer een index
        chosen_idx = random.choices(available_indices, normalized_gewichten, k=1)[0]
        selected.append(choices[chosen_idx])
        available_indices.remove(chosen_idx)
    
    return selected

def weighted_selection_cluster(atc_clusters: dict[str, any], num_clusters: int = 1) -> tuple[list[str], dict[str, float]]:
    """
    Selecteer ATC5 clusters op basis van hun gewichten uit de database.
    Clusters worden uniek geselecteerd (geen duplicaten).
    
    Args:
        atc_clusters: De medicatie clusters data uit de database
        num_clusters: Aantal te selecteren clusters
        
    Returns:
        tuple: (geselecteerde ATC5 codes, gebruikte gewichten)
    """
    # Verzamel geldige clusters en hun gewichten uit de database
    valid_clusters = []
    gewichten = []
    
    for atc5_code, cluster in atc_clusters.items():
        # Sla clusters over zonder geldige ATC7 codes
        if not all(len(med.get("atc7", "")) == 7 for med in cluster.get("geneesmiddelen", [])):
            continue
            
        valid_clusters.append(atc5_code)
        # Gebruik het gewicht dat al in de database staat
        gewichten.append(cluster["statistiek"]["gewicht"])
    
    # Selecteer unieke clusters
    selected_atc5 = weighted_selection_unique(valid_clusters, gewichten, num_clusters)
    
    # Log voor debugging
    gewichten_log = {cluster: gewicht for cluster, gewicht in zip(valid_clusters, gewichten)}
    
    return selected_atc5, gewichten_log

def weighted_selection_medication(medicines: list[dict[str, any]], num_medicines: int = 1) -> tuple[list[str], dict[str, float]]:
    """
    Selecteer geneesmiddelen uit een cluster op basis van hun gewichten uit de database.
    Staat duplicaten toe (hetzelfde medicijn kan meerdere keren geselecteerd worden).
    
    Args:
        medicines: Lijst van geneesmiddelen in het cluster
        num_medicines: Aantal te selecteren geneesmiddelen
        
    Returns:
        tuple: (geselecteerde ATC7 codes, gebruikte gewichten)
    """
    # Verzamel medicijnen en hun gewichten uit de database
    med_codes = []
    gewichten = []
    
    for med in medicines:
        med_codes.append(med["atc7"])
        # Gebruik het gewicht dat al in de database staat
        gewichten.append(med["gewicht"])
    
    # Normaliseer gewichten voor selectie
    total_gewicht = sum(gewichten)
    if total_gewicht <= 0:
        return [], {}
        
    normalized_gewichten = [w/total_gewicht for w in gewichten]
    
    # Selecteer medicijnen (staat duplicaten toe)
    selected_medicines = random.choices(
        population=med_codes,
        weights=normalized_gewichten,
        k=num_medicines
    )
    
    # Log voor debugging
    gewichten_log = {med: gewicht for med, gewicht in zip(med_codes, gewichten)}
    
    return selected_medicines, gewichten_log

def select_medication(atc_cluster: str = None, num_clusters: int = 1, num_medicines: int = 1) -> dict[str, any]:
    """
    Hoofdfunctie voor het selecteren van medicatie op basis van gewichten uit de database.
    
    Args:
        atc_cluster: Optioneel, specifiek ATC cluster om uit te selecteren
        num_clusters: Aantal te selecteren clusters
        num_medicines: Aantal te selecteren geneesmiddelen per cluster
        
    Returns:
        dict: Geselecteerde medicatie met hun details
    """
    # Laad medicatie data met vooraf berekende gewichten
    filename = "data/MedicationClustersDatabase.json"
    atc_clusters = load_data(filename)
    
    if not atc_clusters:
        return {"error": "Kan medicatie database niet laden"}
    
    result = {
        "selected_clusters": [],
        "selected_geneesmiddelen": []
    }
    
    try:
        # Als specifiek cluster is opgegeven, gebruik alleen dat cluster
        if atc_cluster:
            if atc_cluster not in atc_clusters:
                return {"error": f"ATC cluster {atc_cluster} niet gevonden"}
            selected_atc5 = [atc_cluster]
        else:
            # Selecteer clusters op basis van gewichten uit database
            selected_atc5, _ = weighted_selection_cluster(atc_clusters, num_clusters)
        
        # Voor elk geselecteerd cluster, selecteer medicijnen
        for atc5_code in selected_atc5:
            cluster = atc_clusters[atc5_code]
            cluster_info = {
                "atc5_code": atc5_code,
                "naam": cluster["naam"],
                "gewicht": cluster["statistiek"]["gewicht"],
                "geneesmiddelen": []
            }
            
            # Selecteer medicijnen uit het cluster
            selected_meds, _ = weighted_selection_medication(
                cluster["geneesmiddelen"], 
                num_medicines
            )
            
            # Voeg geneesmiddel details toe
            for atc7 in selected_meds:
                med_info = next(
                    med for med in cluster["geneesmiddelen"] 
                    if med["atc7"] == atc7
                )
                cluster_info["geneesmiddelen"].append({
                    "atc7": med_info["atc7"],
                    "naam": med_info["geneesmiddel"],
                    "merknaam": med_info.get("merknaam", ""),
                    "gewicht": med_info["gewicht"]
                })
            
            result["selected_clusters"].append(cluster_info)
            
        return result
        
    except Exception as e:
        return {"error": f"Fout bij selecteren medicatie: {str(e)}"}

if __name__ == "__main__":
    # Test de selectie met de gedefinieerde constanten
    result = select_medication(num_clusters=NUM_CLUSTERS, num_medicines=NUM_MEDICINES)
    
    # Print resultaten in leesbaar formaat
    print("\nGeselecteerde medicatie clusters en geneesmiddelen:")
    print("=" * 70)
    
    for cluster in result["selected_clusters"]:
        # Print cluster informatie
        print(f"\nCluster: {cluster['naam']} ({cluster['atc5_code']})")
        print(f"Cluster gewicht: {cluster['gewicht']:.1f}")
        
        # Print geneesmiddelen in dit cluster
        for med in cluster["geneesmiddelen"]:
            print(f"\n  Geneesmiddel: {med['naam']} ({med['atc7']})")
            print(f"  Gewicht: {med['gewicht']:.1f}")
            if med['merknaam']:
                print(f"  Merknaam: {med['merknaam']}")
        
        print("-" * 70)

