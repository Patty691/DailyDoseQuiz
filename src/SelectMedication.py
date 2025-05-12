import random
import json
import os
import pandas as pd  
""""
from QuizGenerator import generate_quiz_question  # Import de functie uit het andere bestand
"""

# to do:
# select medicatie: random choice ipv unique 
# Step 3: Generate Quiz Questions: schrijf eerst in een afzonderlijk bestand een functie die quizvragen genereert. Neem sample input hiervoor. 

## voeg de merknaam toe aan de output als dit nodig is voor apotheek.nl

# als bestand klaar is:
## code opschonen en relevante info in readme.md 
## unit test en integratie test maken
""" 
Aantal clusters en gnm baseren op uiteindelijk gebruik:
#   Methode van vragen genereren heeft ook invloed op de uiteindelijke database (beinvloedt de weging)
#   Hoe ziet de app eruit. tip: bij 3 vragen per dag 3 over zelfde cluster.
#   Hoeveel vragen wil ik in 1 keer generen (hoeveel dubbelingen en direct na generen ook reviseren?)
#   Optie: op atc7 niveau wel dubbelingen toestaan door random.choices ipv unique
#   Alleen aanpassingen aan de vaste parameters doorvoeren op evaluatiemomenten
"""

WEIGHT_PERCENTAGE = 0.99  # Weight for percentage_verstrekkingen
WEIGHT_GROWTH = 0.01      # Weight for groei_percentage
WEIGHT_NEW_IN_LIST = 2    # Weight multiplier for "nieuw in de lijst"
NUM_CLUSTERS = 10         # Number of ATC5 clusters to select
NUM_MEDICINES = 3         # Number of medicines to select per ATC5 cluster

def load_data(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"Error: File not found at {filename}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Failed to decode JSON file at {filename}: {e}")
        return None

def weighted_selection_unique(choices, k):
    """
    Select `k` unique items from `choices` based on weighted probabilities.
    If all unique items are exhausted, allow repetition.

    Args:
        choices (list): A list of items (with duplicates for weighting).
        k (int): The number of items to select.

    Returns:
        list: A list of selected items.
    """
    selected = []
    unique_choices = list(set(choices))  # Get unique items from the choices

    for _ in range(k):
        if not unique_choices:  # If all unique items are exhausted, refill the list
            unique_choices = list(set(choices))
        
        # Select a random item from the unique choices
        selected_item = random.choice(unique_choices)
        selected.append(selected_item)
        
        # Remove the selected item from the unique choices to avoid duplicates
        unique_choices.remove(selected_item)

    return selected

def weighted_selection_cluster(atc_clusters, num_clusters=NUM_CLUSTERS):
    choices = []
    weights_log = {}  # Dictionary to store weights for logging

    # Step 1: Calculate weights for all items except items without valid ATC7-code or "nieuw in de lijst"
    for atc5_code, cluster_data in atc_clusters.items():
        try:
            # Exclude medication which doesn't have an ATC7-code (only 5 characters of ATC5-code assigned to medicine)
            valid_atc7 = all(
                len(med.get("atc7", "")) == 7 
                for med in cluster_data.get("geneesmiddelen", [])
            )
            if not valid_atc7:
                # Skip this cluster if any medication has an invalid ATC7 code
                continue
            # Check if growth is a digit and not "nieuw in de lijst"
            growth = cluster_data["statistiek"]["totaal_groeipercentage"]
            if not (isinstance(growth, str) and growth.lower() == "nieuw in de lijst"):
                # Calculate weight for existing items
                weight = round(
                    cluster_data["statistiek"]["totaal_percentage_verstrekkingen"] * WEIGHT_PERCENTAGE +
                    cluster_data["statistiek"]["totaal_groeipercentage"] * WEIGHT_GROWTH,
                    3
                )
                weights_log[atc5_code] = weight
        except (KeyError, TypeError, ValueError):
            continue

    # Step 2: Assign weight for "nieuw in de lijst" as 2x the maximum weight in the list   
    max_weight = max(weights_log.values(), default=0)  # Find the highest weight in the list
    
    for atc5_code, cluster_data in atc_clusters.items():
        try:
            growth = cluster_data["statistiek"]["totaal_groeipercentage"]
            if isinstance(growth, str) and growth.lower() == "nieuw in de lijst":
                weight = round(max_weight * WEIGHT_NEW_IN_LIST, 3) 
                weights_log[atc5_code] = weight
        except (KeyError, TypeError, ValueError):
            continue

    # Step 3: Build the choices list based on weights
    for atc5_code, weight in weights_log.items():
        choices.extend([atc5_code] * int(weight))

    # Randomly select unique ATC5 codes based on the weighted choices
    selected_atc5 = random.choices(choices, k=num_clusters) if choices else []    
    return selected_atc5, weights_log

def weighted_selection_medication(medicines, num_medicines=NUM_MEDICINES):
    choices = []
    weights_log = {}  # Dictionary to store weights for logging

    # Step 1: Calculate weights for all medicines
    for med in medicines:
        try:
            percentage_verstrekkingen = med["percentage_verstrekkingen"]
            groei_percentage = med["groei_percentage"]
            # Calculate weight
            weight = round(
                percentage_verstrekkingen * WEIGHT_PERCENTAGE +
                groei_percentage * WEIGHT_GROWTH,
                3
            )
            weights_log[med["atc7"]] = weight
        except (KeyError, TypeError, ValueError):
            continue

    # Step 2: Assign weight for "nieuw in de lijst" if applicable
    max_weight = max(weights_log.values(), default=0)  # Find the highest weight in the list
    for med in medicines:
        try:
            groei_percentage = med["groei_percentage"]
            if isinstance(groei_percentage, str) and groei_percentage.lower() == "nieuw in de lijst":
                weight = round(max_weight * WEIGHT_NEW_IN_LIST, 3)  
                weights_log[med["atc7"]] = weight
        except (KeyError, TypeError, ValueError):
            continue

    # Step 3: Build the choices list based on weights
    for atc7, weight in weights_log.items():
        choices.extend([atc7] * int(weight))  # Convert weight to int for list extension

    # Randomly select unique medicines based on the weighted choices
    selected_medicines = weighted_selection_unique(choices, k=num_medicines) if choices else []
    return selected_medicines, weights_log


if __name__ == "__main__":

    # Path to the JSON file (update this path if needed)
    filename = "/Users/pattynooijen/Documents/VisualStudioCode/daily_dose_quiz/data/MedicationClustersDatabase.json"

    # Load the data
    atc_clusters = load_data(filename)

    if atc_clusters:  
        # Step 1: Weighted selection at ATC5 level
        selected_atc5, weights_log = weighted_selection_cluster(atc_clusters)

        # Print the selected ATC5 codes and their weights
        if selected_atc5:
            for atc5_code in selected_atc5:
                weight = weights_log.get(atc5_code, "N/A")  # Get the weight for the selected ATC5 code
        else:
            print("No ATC5 codes could be selected.")

        # Step 2: Weighted selection at ATC7 level
        print("\nGeselecteerde geneesmiddelen:")

        for atc5_code in selected_atc5:
            cluster_name = atc_clusters[atc5_code]["naam"]  # Get the cluster name
            medicines = atc_clusters[atc5_code]["geneesmiddelen"]  # Get the medicines in the cluster
            selected_medicines, weights_log_meds = weighted_selection_medication(medicines)

            for atc7_code in selected_medicines:
                # Find the selected medicine details
                selected_medicine = next((med for med in medicines if med["atc7"] == atc7_code), None)
                if selected_medicine:
                    # Print the details of the selected medicine
                    print(f"\nCluster: {cluster_name} ({atc5_code})")
                    print(f"Geneesmiddel: {selected_medicine['geneesmiddel']} ({selected_medicine['atc7']})")

    else:
        print("Failed to load ATC cluster data.")
    print("\n\n\n")

""" 
Verdeling van verantwoordelijkheden:
In dit bestand (SelectMedication.py):

Beheer de selectie van ATC5-clusters en ATC7-medicatie.
Roep de functie aan die quizvragen genereert.



Zorg voor het opslaan van de gegenereerde quizvragen.
In een afzonderlijk bestand (QuizGenerator.py):

Implementeer de logica voor het genereren van quizvragen.
Dit kan bijvoorbeeld een eenvoudige tekstgeneratie zijn of een integratie met een AI-model zoals GPT.


# Step 3: Generate Quiz Questions
def generate_quiz_questions(selected_medicines, atc_clusters):
    
    #Generate quiz questions for the selected medicines.

    #Args:
    #    selected_medicines (list): List of selected ATC7 codes.
    #    atc_clusters (dict): The ATC cluster data.

    #Returns:
    #    list: A list of generated quiz questions.
   
    quiz_questions = []

    for atc7_code in selected_medicines:
        # Zoek de details van het geneesmiddel op
        for atc5_code, cluster_data in atc_clusters.items():
            medicines = cluster_data.get("geneesmiddelen", [])
            selected_medicine = next((med for med in medicines if med["atc7"] == atc7_code), None)
            if selected_medicine:
                # Genereer een quizvraag met behulp van de externe functie
                question = generate_quiz_question(
                    atc7_code=selected_medicine["atc7"],
                    geneesmiddel=selected_medicine["geneesmiddel"],
                    merknaam=selected_medicine.get("merknaam", ""),
                    cluster=cluster_data["naam"]
                )
                quiz_questions.append(question)

    return quiz_questions




        if __name__ == "__main__":
        # Path to the JSON file (update this path if needed)
        filename = "/Users/pattynooijen/Documents/VisualStudioCode/daily_dose_quiz/data/MedicationClustersDatabase.json"
    
        # Load the data
        atc_clusters = load_data(filename)
    
        if atc_clusters:  
            # Step 1: Weighted selection at ATC5 level
            selected_atc5, weights_log = weighted_selection_cluster(atc_clusters)
    
            # Step 2: Weighted selection at ATC7 level
            selected_medicines = []
            for atc5_code in selected_atc5:
                medicines = atc_clusters[atc5_code]["geneesmiddelen"]
                selected, _ = weighted_selection_medication(medicines)
                selected_medicines.extend(selected)
    
            # Step 3: Generate quiz questions
            quiz_questions = generate_quiz_questions(selected_medicines, atc_clusters)
    
            # Step 4: Save quiz questions
            for question in quiz_questions:
                save_quiz_question(question)
    
            print("\nGenerated Quiz Questions:")
            for question in quiz_questions:
                print(question)
        else:
            print("Failed to load ATC cluster data.")





# Step 4: Store Quiz Questions
def save_quiz_question(question, filename="quiz_questions.json"):
  
    try:
        with open(filename, "r", encoding="utf-8") as f:
            questions = json.load(f)
    except FileNotFoundError:
        questions = []
    
    questions.append({"question": question})
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=4)
""" 