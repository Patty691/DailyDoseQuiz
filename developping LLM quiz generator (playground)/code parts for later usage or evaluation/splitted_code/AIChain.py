# %%
from dotenv import load_dotenv
import os
import random
import requests
from bs4 import BeautifulSoup
from typing import List
from PromptQuizQuestion import QuizPrompts
from Models import Extraction, Response
from QuizChain import QuizGenerationChain


"""" GAAT NIET GOED, VEEL AANPASSINGEN MET AI GEDAAN. INSTRUCTOR LIJKT NIET TE WERKEN. ZORGEN DAT DIT GEBRUIKT WORDT. """

""" 
Keuze van de modellen: 
gpt-4o-mini ondersteunt het werken in stappen niet, maar werkt verder goed.
gpt-4o-2024-08-06 ondersteunt het werken in stappen, maar werkt nauwelijks beter dan 4.1 mini
gpt-4.1-nano is goedkoper, maar werkt voor deze toepassing niet goed
gpt 4.1 werkt nauwelijks beter en is duurder.
max_retries wordt niet ondersteund in  response= client.beta.chat.completions.parse(
"""

MODEL = "gpt-4o-mini"  
DEBUG_MODE = True  # Set to True to see verification results

KNOWLEDGE_CATEGORIES = {
    "indicaties": 4,
    "werkingsmechanisme": 3,
    "dosering": 2,
    "toediening": 2,
    "interacties": 5,
    "contra-indicaties": 5,
    "bijwerkingen": 5,
    "monitoring": 2,
    "rijvaardigheid": 1,
    "stoppen met gebruik": 1,
    "bijzondere populaties (bijv. ouderen, obesen, kinderen, zwangeren, borstvoeding)": 1,
}

def get_medicine_info(medicine_name: str, atc_cluster: str) -> str:
    try:
        base_url = f"https://www.apotheek.nl/medicijnen/{medicine_name.lower()}"
        response = requests.get(base_url)

        if response.status_code != 200:
            print(f"Kon URL voor {medicine_name} niet vinden.")
            full_url = input(f"Plak de exacte URL voor '{medicine_name}' uit ATC-cluster {atc_cluster}:\n> ")
            response = requests.get(full_url)
    except Exception as e:
        raise RuntimeError(f"Netwerkfout bij ophalen van data: {e}")

    # Hier begint de parsing en herhaal je alleen als de structuur niet klopt
    while True:
        try:
            soup = BeautifulSoup(response.text, "html.parser")
            list_items = soup.find_all("li", class_="listItemContent_container__25F5W")

            if not list_items:
                print(f"De URL bevat niet de juiste structuur voor informatie over {medicine_name} uit ATC-cluster {atc_cluster}:\n>.")
                full_url = input(f"Plak een andere URL waarbij de info begint met 'Belangrijke informatie over':\n> ")
                response = requests.get(full_url)
                continue  # try again with the new URL
            # Structuur klopt, ga door met verwerken
            relevant_text = []
            for item in list_items:
                title = item.find("h2")
                if title:
                    relevant_text.append(title.get_text(strip=False))
                content = item.find("div", class_="listItemContent_content__w3Hqp")
                if content:
                    relevant_text.append(content.get_text(separator=" ", strip=False))

            cleaned_text = "\n\n".join(relevant_text)
            return cleaned_text

        except Exception as e:
            raise RuntimeError(f"Fout bij verwerken van HTML-pagina: {e}")
        
# Function to get a random knowledge category
def get_random_knowledge_category() -> str:
    categories = list(KNOWLEDGE_CATEGORIES.keys())
    weights = list(KNOWLEDGE_CATEGORIES.values())
    random_category = random.choices(categories, weights=weights, k=1)[0]
    return random_category  

# Main-functie
if __name__ == "__main__":
    # Initialize the quiz generation chain
    quiz_chain = QuizGenerationChain(model_name=MODEL, debug_mode=DEBUG_MODE)
    
    medicine_name = "metoprolol"  # Vervang dit door de naam van het medicijn dat je wilt gebruiken
    atc_cluster = "beta-blokkers"  # Vervang dit door de ATC-clusterNAAM die je wilt gebruiken 

    #Haal medicatie-informatie op
    try:
        medicine_info = get_medicine_info(medicine_name, atc_cluster)
        if not medicine_info or "No relevant information found" in medicine_info:
            print("Geen medicatie-informatie gevonden in de functie 'get_medicine_info'. Kan geen quizvraag genereren.")
            exit(1)

    except Exception as e:
        print(f"Error tijdens uitvoeren van de functie 'get_medicine_info': {e}.")
        exit(1)

    # Kies een willekeurige kenniscategorie
    random_category = get_random_knowledge_category()
    print(f"\n\n\nGekozen kenniscategorie: {random_category}\n\n")

    # Generate quiz using LangChain
    try:
        result = quiz_chain.generate_quiz(
            medicine_info=medicine_info,
            category=random_category,
            medicine_name=medicine_name
        )
        
        # Print results
        print("\nGeëxtraheerde informatie:")
        print(result["extracted_info"])
        
        print("\nGegenereerde quizvraag:")
        quiz = result["quiz_question"]
        print(f"\nIntroductie: {quiz.introductie}")
        print(f"\nVraag: {quiz.vraag}")
        print("\nAntwoordopties:")
        for index, option in enumerate(quiz.antwoordopties, start=1):
            print(f"{chr(64 + index)}) {option}")
        print(f"\nAntwoord: {quiz.antwoord}")
        print(f"\nUitleg: {quiz.uitleg}")

    except Exception as e:
        print(f"Error: {e}")

# %%
