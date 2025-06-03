# %%
from dotenv import load_dotenv
import os
import instructor
import random
import openai
from pydantic import BaseModel, Field
from openai import OpenAI
from enum import Enum
import requests
from bs4 import BeautifulSoup
from typing import List

# to do:

#zie 2LLMs functioneel.py


""" 
Keuze van de modellen: 
gpt-4o-mini ondersteunt het werken in stappen niet, maar werkt verder goed.
gpt-4o-2024-08-06 ondersteunt het werken in stappen, maar werkt nauwelijks beter dan 4.1 mini
gpt-4.1-nano is goedkoper, maar werkt voor deze toepassing niet goed
gpt 4.1 werkt nauwelijks beter en is duurder.
max_retries wordt niet ondersteund in  response= client.beta.chat.completions.parse(
"""

MODEL = "gpt-4o-mini"  


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

class Extraction(BaseModel):
    relevant_information: str = Field(description="The extracted information.")

class Response(BaseModel):
    class Step(BaseModel):
        description: str = Field(description="Description of the step taken.")
        action: str = Field(description="Action taken to resolve the issue.")
        result: str = Field(description="Result of the action taken.")
    steps: List[Step]

    class SelfVerification(BaseModel):
        check_accuracy: str = Field(description="Verification of medical/pharmaceutical accuracy")
        check_clarity: str = Field(description="Verification that the question and options are clear and unambiguous")
        check_fairness: str = Field(description="Verification that the question tests knowledge fairly")
        improvements: List[str] = Field(description="List of improvements made during verification")

    class FinalResolution(BaseModel):
        introductie: str = Field(description="The introduction text for the quiz question.")
        vraag: str = Field(description="The quiz question.")
        antwoordopties: List[str] = Field(description="The answer options for the quiz question, without any prefixes.")
        antwoord: str = Field(description="The correct answer to the quiz question.")
        uitleg: str = Field(description="The explanation for the correct answer.")
        verificatie: "Response.SelfVerification" = Field(description="Self-verification results")

    final_resolution: FinalResolution

    class Config:
        json_schema_extra = {
            "required": ["steps", "final_resolution"]
        }


def initialize_openai_client() -> instructor.Instructor:
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if not openai_api_key:
        raise ValueError("OpenAI API key not found. Please set it in the .env file.")

    return instructor.from_openai(OpenAI())

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
    return random.choices(categories, weights=weights, k=1)[0]
    """
    Kies willekeurig een kenniscategorie uit de lijst KNOWLEDGE_CATEGORIES.

    Returns:
        str: Een willekeurige kenniscategorie.
    """
    return random.choice(KNOWLEDGE_CATEGORIES)

# Functie om relevante informatie te extraheren met een LLM
def extract_relevant_info(medicine_info: str, category: str) -> str:
    """
    Extract information relevant to a specific category using headers and/or keywords.
    Some information is found under specific headers, other information needs keyword search,
    and some needs both.
    
    Args:
        medicine_info (str): The full medicine information text
        category (str): The category to extract information for
    
    Returns:
        str: The extracted relevant information
    """
    # Map categories to their search criteria
    category_mapping = {
        "indicaties": {
            "headers": ["Wat doet"]
        },
        "werkingsmechanisme": {
            "headers": ["Wat doet"],
            "keywords": ["werkt door", "zorgt ervoor", "werking", "effect op"]
        },
        "dosering": {
            "keywords": ["keer per dag", "tablet", "mg", "dosis", "innemen", "gebruiken"]
        },
        "toediening": {
            "headers": ["Hoe gebruik ik"]
        },
        "interacties": {
            "headers": ["Mag ik", "met andere medicijnen gebruiken"],
            "keywords": ["combinatie met", "samen met", "wisselwerking"]
        },
        "contra-indicaties": {
            "headers": ["met andere medicijnen gebruiken"], #onjuist, aanpassen
            "keywords": []
        },
        "bijwerkingen": {
            "headers": ["Wat zijn mogelijke bijwerkingen"]
        },
        "monitoring": {
            "headers": ["Belangrijk om te weten"],
            "keywords": ["controleren", "meten", "in de gaten houden", "bloeddruk", "hartslag"]
        },
        "rijvaardigheid": {
            "headers": ["Kan ik met dit medicijn autorijden"]
        },
        "stoppen met gebruik": {
            "headers": ["Mag ik zomaar"]
        },
        "bijzondere populaties": {
            "headers": [
                "Mag ik dit medicijn gebruiken als ik zwanger ben",
                "bij ouderen",
                "bij kinderen"
            ],
            "keywords": ["zwanger", "borstvoeding", "ouderen", "kinderen", "verminderde nierfunctie", "leverfunctie"]
        }
    }
    
    # Get mapping for the requested category
    category_info = category_mapping.get(category.lower())
    if not category_info:
        return f"Geen specifieke informatie gevonden voor {category}."
    
    # Split into sections
    sections = medicine_info.split("\n\n")
    relevant_sections = []
    
    for i, section in enumerate(sections):
        section_lower = section.lower()
        is_relevant = False
        
        # Check headers if present
        if "headers" in category_info:
            if any(header.lower() in section_lower for header in category_info["headers"]):
                is_relevant = True
                # Add this section and the next one (which usually contains the content)
                relevant_sections.append(section)
                if i + 1 < len(sections):
                    relevant_sections.append(sections[i + 1])
                
        # Check keywords if present
        if "keywords" in category_info and not is_relevant:
            if any(keyword.lower() in section_lower for keyword in category_info["keywords"]):
                relevant_sections.append(section)
    
    # If no relevant sections found, return a message
    if not relevant_sections:
        return f"Geen specifieke informatie gevonden over {category}."
    
    # Join all relevant sections
    return "\n\n".join(relevant_sections)

# Function to generate a quiz question
def generate_quiz_question(query: str, relevant_info: str, random_category: str) -> Response:
    style = """
    - je schrijft in het Nederlands, de je-vorm en zonder namen te noemen
    - richt je impliciet tot de apothekersassistent (noem het woord apothekersassistent niet).
    - gebruik toegankelijke, maar vakinhoudelijke taal.
    - benoem niet wat of waarom iets belangrijk is.
    - geen formulering zoals 'stel dat'.
    - volg deze stappen bij het maken van antwoordopties:
        1. Identificeer eerst het kernprincipe of de kernkennis die getest wordt
        2. Schrijf het juiste antwoord op basis van de broninformatie
        3. Creëer foute antwoorden door:
           - Een klein maar cruciaal detail te veranderen
           - Een veelvoorkomende misvatting te gebruiken
           - Een logische maar incorrecte redenering te volgen
        4. Controleer of alle opties:
           - Dezelfde lengte en detail hebben
           - Dezelfde grammaticale structuur hebben
           - Even plausibel klinken
    """ 

    role = f"""
    Je bent een zeer goede docent en wint prijzen voor het stellen van goede quizvragen en bijbehorende antwoordopties, introductie en uitleg. Maak een moeilijke, praktijkgerichte quizvraag voor zeer ervaren apothekersassistenten (bachelorniveau).
    
    Volg deze stappen:
    1. Analyseer de informatie en kies een geschikt onderwerp
    2. Maak een eerste versie van de vraag
    3. Voer een kritische zelfcontrole uit en documenteer:
        - Accuraatheid: Controleer of alle medische/farmaceutische informatie correct is
        - Helderheid: Controleer of de vraag en antwoordopties duidelijk en ondubbelzinnig zijn
        - Eerlijkheid: Controleer of de vraag op een eerlijke manier kennis test
        - Verbeteringen: Documenteer welke verbeteringen je hebt aangebracht
    4. Neem de resultaten van de zelfcontrole op in je antwoord
    
    Je bent expert in het maken van antwoordopties die:
    - Allemaal even lang en gedetailleerd zijn
    - Allemaal dezelfde grammaticale structuur hebben
    - Allemaal plausibel klinken voor iemand die het niet helemaal zeker weet
    - Subtiele maar cruciale verschillen bevatten die alleen iemand met diepgaande kennis kan herkennen
    
    Belangrijke regels voor medische accuraatheid:
    - Vermijd oversimplificatie van farmacotherapeutische informatie
    - Maak onderscheid tussen verschillende gradaties (bijv. absoluut vs. relatief, ernstig vs. mild)
    - Benoem relevante nuances zoals:
        * Dosisafhankelijkheid
        * Receptorselectiviteit
        * Tijdsafhankelijkheid
        * Patiëntkenmerken
        * Comedicatie
    - Gebruik genuanceerde formuleringen wanneer er uitzonderingen mogelijk zijn:
        * 'meestal', 'vaak', 'soms', 'kan'
        * 'onder bepaalde voorwaarden'
        * 'afhankelijk van'
    - Vermijd absolute uitspraken tenzij het echt om absolute situaties gaat
    - Als er voorwaarden of beperkingen zijn, specificeer deze dan
    - Plaats informatie in de juiste context (bijv. ernst van de situatie, beschikbaarheid alternatieven)
    
    Gebruik uitsluitend de volgende informatie: {relevant_info}. 
    """

    instructions = """ 
    Antwoordopties:
    - Antwoordopties zijn uitdagend en lijken sterk op elkaar, zodat het niet eenvoudig is het juiste antwoord te herkennen.
    - Foute antwoordopties zijn inhoudelijk geloofwaardig, sluiten aan bij de context, en bevatten subtiele fouten of veelvoorkomende misvattingen.
    - Foute antwoordopties zijn qua formulering en onderwerp vergelijkbaar met het juiste antwoord, zodat ze niet direct opvallen als fout.
    - Vermijd antwoordopties die duidelijk onjuist zijn of het juiste antwoord te makkelijk maken.
    - Het juiste antwoord is correct volgens de broninformatie en de foute antwoorden zijn zeker fout.

    Goed voorbeeld van een genuanceerde vraag:
    Introductie: Een 67-jarige patiënt met matige COPD en atriumfibrilleren heeft een bètablokker nodig. 
    
    Vraag: Welke uitspraak over het voorschrijven van metoprolol bij deze patiënt is correct?
    Antwoordopties:
    Metoprolol is absoluut gecontra-indiceerd vanwege de COPD
    Metoprolol kan worden voorgeschreven, startend met een lage dosis 
    Metoprolol kan alleen worden voorgeschreven als de COPD eerst volledig onder controle is
    Metoprolol kan alleen worden voorgeschreven in combinatie met een luchtwegverwijdering
    
    Antwoord: Metoprolol kan worden voorgeschreven, startend met een lage dosis onder controle
    
    Uitleg: Hoewel COPD een relatieve contra-indicatie is voor metoprolol, kan deze cardioselectieve bètablokker vaak veilig worden gebruikt bij COPD-patiënten. De cardioselectiviteit betekent dat het medicijn vooral effect heeft op β1-receptoren in het hart en minder op β2-receptoren in de luchtwegen. Door te starten met een lage dosis en de patiënt goed te monitoren, kunnen de voordelen voor de behandeling van atriumfibrilleren vaak opwegen tegen de mogelijke risico's voor de luchtwegen.

    Fout voorbeeld: 
    Introductie: Een patient met angina pectoris krijgt een nieuw geneesmiddel. 
    Vraag: Bij welke van de volgende aandoeningen is metoprolol een geschikte behandeling?
    Antwoordopties: A) Hartfalen B) Astma C) Diabetes D) Angina pectoris
    Antwoord: Angina pectoris
    Fout omdat: 
    1. angina pectoris al in de introductie staat en het antwoord dus makkelijk te raden is.
    2. hartfalen ook een indicatie is voor metoprolol.
    3. astma en diabetes heel andere aandoeningen zijn, waardoor het antwoord makkelijk te raden is.
    
    Introductie en uitleg:
    - zijn elk 3 tot 10 zinnen.
    - De introductie moet 100% voldoen aan de volgende eisen:
        - vermijd dat de introductie het raden van het juiste antwoord vergemakkelijkt.
        - beschrijft een realistische praktijksituatie van een patiënt.
        - mag de lezer op het verkeerde been zetten of misleiden, zolang de informatie maar correct is en bij de situatie past.
        - controleer na het schrijven van de introductie of deze geen informatie bevat die het juiste antwoord of de antwoordopties verraadt; herschrijf indien nodig.
        - fout voorbeeld: juist antwoord is astma, introductie benoemt dat een patient astma heeft (en niet de andere opties)
    - De uitleg:
        - geeft relevante achtergrondinformatie (zoals farmacologische werking, klinische implicaties, uitzonderingen).
        - leg moeilijke termen uit, eventueel tussen haakjes.
        - kom terug op de informatie in de introductie, om de relevantie uit te leggen.
    """ 

    try:
        # Create a chat completion request
        response = client.beta.chat.completions.parse(
            model=MODEL, 
            response_format=Response,
            temperature=0.1,  # Adjust the temperature for creativity
            messages=[
                {"role": "system", "content": style},
                {"role": "system", "content": role},
                {"role": "system", "content": instructions},
                {"role": "user", "content": query}
            ],  
        )                  

        # Get the parsed response from the first choice
        parsed_response = response.choices[0].message.parsed

        # Print verification results if in debug mode
        if DEBUG_MODE:
            print("\nZelf-verificatie resultaten:")
            verificatie = parsed_response.final_resolution.verificatie
            print(f"Accuraatheid: {verificatie.check_accuracy}")
            print(f"Helderheid: {verificatie.check_clarity}")
            print(f"Eerlijkheid: {verificatie.check_fairness}")
            if verificatie.improvements:
                print("\nAangebrachte verbeteringen:")
                for improvement in verificatie.improvements:
                    print(f"- {improvement}")
            print()
            
        return parsed_response

    except Exception as e:
        raise RuntimeError(f"Failed to generate quiz question: {e}")
    
# Main-functie
if __name__ == "__main__":
    client = initialize_openai_client()
   
    medicine_name = "metoprolol"  # Vervang dit door de naam van het medicijn dat je wilt gebruiken
    atc_cluster = "beta-blokkers"  # Vervang dit door de ATC-clusterNAAM die je wilt gebruiken 

    DEBUG_MODE = False  # Zet op False om debug-informatie niet af te drukken
    EVALUATION_MODE = False #zet op True om de evaluatie uit te voeren

    #Haal medicatie-informatie op
    try:
        medicine_info = get_medicine_info(medicine_name, atc_cluster)
        if not medicine_info or "No relevant information found" in medicine_info:
            print("Geen medicatie-informatie gevonden in de functie 'get_medicine_info'. Kan geen quizvraag genereren.")
            exit(1)
       # Print debug-informatie alleen als DEBUG_MODE True is
        if DEBUG_MODE:
            print("DEBUG: Opgehaalde medicatie-informatie:")
            print(medicine_info)
    except Exception as e:
        print(f"Error tijdens uitvoeren van de functie 'get_medicine_info': {e}.")
        exit(1)

    # Kies een willekeurige kenniscategorie
    random_category = get_random_knowledge_category()
    print(f"\n\n\nGekozen kenniscategorie: {random_category}\n\n")

    # Extraheer relevante informatie 
    try:
        relevant_info = extract_relevant_info(medicine_info, random_category)
        print("Relevante informatie:")
        print(relevant_info)
    except Exception as e:
        print(f"Error extracting relevant information: {e}")
        exit(1)

    #Genereer een quizvraag
    print("\nQuizvraag genereren...")
    query = f"De vraag moet gaan over {medicine_name} en betrekking hebben op de categorie: {random_category}."    
    print (f"\n\nQuery: {query}")
    try:
        response = generate_quiz_question(query, medicine_info, random_category)
        # Print de stappen
        for step in response.steps:
            print(f"Step: {step.description}")
            print(f"Action: {step.action}")
            print(f"Result: {step.result}\n")

        # Print de final_resolution
        print("\nGegenereerde quizvraag:")
        print(f"\n\nIntroductie: {response.final_resolution.introductie}")
        print(f"\nVraag: {response.final_resolution.vraag}")
        print("\nAntwoordopties:")
        for index, option in enumerate(response.final_resolution.antwoordopties, start=1):
            print(f"{chr(64 + index)}) {option}")  # Converteer index naar A, B, C, D
        print(f"\nAntwoord: {response.final_resolution.antwoord}")
        print(f"\nUitleg: {response.final_resolution.uitleg}\n\n")

    except Exception as e:
        print(f"Error: {e}")

# %%
