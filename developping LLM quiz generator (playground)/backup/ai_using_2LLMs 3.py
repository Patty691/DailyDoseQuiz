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
## grootste knelpunt: de introductie verraad het antwoord


## betrouwbaarheid van de quizvraag geeft nog onvoldoende informatie
## evaluatiefunctie is nog niet goed
## fetch info: optie om over te slaan als je niet de juiste URL kunt invoeren (of geen URL wilt geven)

## later: moeilijkheidsgraad toevoegen in output?

""" 
Keuze van de modellen: 
gpt-4o-mini ondersteunt het werken in stappen niet, maar werkt verder goed.
gpt-4o-2024-08-06 ondersteunt het werken in stappen, maar werkt nauwelijks beter dan 4.1 mini
gpt-4.1-nano is goedkoper, maar werkt voor deze toepassing niet goed
gpt 4.1 werkt nauwelijks beter en is duurder.
max_retries wordt niet ondersteund in  response= client.beta.chat.completions.parse(
"""

MODEL = "gpt-4o-mini"  
CLIENT = initialize_openai_client()

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

    class FinalResolution(BaseModel):
        introductie: str = Field(description="The introduction text for the quiz question.")
        vraag: str = Field(description="The quiz question.")
        antwoordopties: List[str] = Field(description="The answer options for the quiz question, without any prefixes.")
        antwoord: str = Field(description="The correct answer to the quiz question.")
        uitleg: str = Field(description="The explanation for the correct answer.")
    final_resolution: FinalResolution

class Config:
        json_schema_extra = {
        "required": ["steps", "final_resolution"]
        }

class Evaluation(BaseModel):
    is_consistent: bool = Field(description="Whether the response is consistent with the source information")
    feedback: str = Field(description="Detailed feedback about the quiz question, correctness, the style and difficulty")
    improvement_suggestions: List[str] = Field(description="List of suggested improvements")
    score: float = Field(description="Overall quality score (0-1)", ge=0, le=1)      
                           
# Define the initialize_openai_client function
def initialize_openai_client() -> instructor.Instructor:
    # Load environment variables from the .env file
    load_dotenv()

    # Get the OpenAI API key from the environment
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if not openai_api_key:
        raise ValueError("OpenAI API key not found. Please set it in the .env file.")

    return instructor.from_openai(OpenAI())


# Function to fetch medicine information from www.apotheek.nl
def fetch_medicine_info(medicine_name: str, atc_cluster: str) -> str:
    try:
        # Probeer standaard URL
        base_url = f"https://www.apotheek.nl/medicijnen/{medicine_name.lower()}"
        response = requests.get(base_url)

        # Als de standaard URL niet werkt, vraag handmatig om een juiste URL
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
def extract_relevant_info(client: openai, medicine_info: str, random_category: str) -> str:
    prompt = f"""
    Hier is informatie over een medicijn:  {medicine_info}
    Geef de informatie die specifiek betrekking heeft op de categorie '{random_category}'.
    """
    # Maak een chat completion request
    response = client.beta.chat.completions.parse(
        model=MODEL,
        response_format=Extraction,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1  # Pas de temperatuur naar beneden aan voor minder creatieve, meer feitelijke antwoorden
    )
    
    # Controleer of de respons een 'choices'-attribuut bevat
    if not hasattr(response, "choices"):
        raise RuntimeError("De respons bevat geen 'choices'-attribuut. Controleer de API-aanroep.")
    
    # Retourneer de inhoud van de eerste keuze
    return response.choices[0].message.parsed

# Function to generate a quiz question
def generate_quiz_question(query: str, relevant_info: str, random_category: str) -> Response:
    style = """
    - je schrijft in het Nederlands, de je-vorm en zonder namen te noemen
    - richt je impliciet tot de apothekersassistent (noem het woord apothekersassistent niet).
    - gebruik toegankelijke, maar vakinhoudelijke taal.
    - benoem niet wat of waarom iets belangrijk is.
    - geen formulering zoals 'stel dat'.
    """ 

    role = f"""
    Je bent een zeer goede docent en wint prjzen voor het stellen van goede quizvragen en bijbehorende antwoordopties, introductie en uitleg. Maak een moeilijke, praktijkgerichte quizvraag voor zeer ervaren apothekersassistenten (bachelorniveau).
    Gebruik uitsluitend de volgende informatie: {relevant_info}. 
    """

    instructions = """ 
    Antwoordopties:
    - Antwoordopties zijn uitdagend en lijken sterk op elkaar, zodat het niet eenvoudig is het juiste antwoord te herkennen.
    - Foute antwoordopties zijn inhoudelijk geloofwaardig, sluiten aan bij de context, en bevatten subtiele fouten of veelvoorkomende misvattingen.
    - Foute antwoordopties zijn qua formulering en onderwerp vergelijkbaar met het juiste antwoord, zodat ze niet direct opvallen als fout.
    - Vermijd antwoordopties die duidelijk onjuist zijn of het juiste antwoord te makkelijk maken.
    - Het juiste antwoord is correct volgens de broninformatie en de foute antwoorden zijn zeker fout.
    
    Fout voorbeeld: 
    Vraag: Bij welke van de volgende aandoeningen is metoprolol een geschikte behandeling?
    Antwoordopties: A) Hartfalen B) Astma C) Diabetes D) Angina pectoris
    Antwoord: Angina pectoris
    Fout omdat: 
    1. angina pectoris al in de introductie staat en het antwoord dus makkelijk te raden is.
    2. hartfalen ook een indicatie is voor metoprolol.
    
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
        return response.choices[0].message.parsed

    except Exception as e:
        raise RuntimeError(f"Failed to generate quiz question: {e}")
    
def evaluation(client: OpenAI, response: Response, relevant_info: str) -> Evaluation:
    try:
        evaluation_prompt = f"""
        Evalueer deze quizvraag op basis van de originele informatie en retourneer je evaluatie in het volgende JSON-formaat:
        {{
            "is_consistent": true of false,
            "feedback": "string met gedetailleerde feedback",
            "improvement_suggestions": ["suggestie 1", "suggestie 2"],
            "score": een getal tussen 0 en 1
        }}

        ORIGINELE INFORMATIE:
        {relevant_info}

        GEGENEREERDE QUIZ:
        Introductie: {response.final_resolution.introductie}
        Vraag: {response.final_resolution.vraag}
        Antwoordopties: {response.final_resolution.antwoordopties}
        Antwoord: {response.final_resolution.antwoord}
        Uitleg: {response.final_resolution.uitleg}
    
        Controleer en beoordeel de volgende aspecten:
        1. Inhoudelijke correctheid en consistentie met de broninfo
        2. Niveau (bachelor-niveau apothekersassistent)
        3. Praktijkgerichtheid
        4. Kwaliteit van de antwoordopties
        5. Kwaliteit van de introductie en uitleg
        6. Of de vraag en antwoord logisch zijn voor deze casus en of ze aansluiten bij de praktijk
        """

        result = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "Je bent een expert in het evalueren van quizvragen. Geef je evaluatie altijd in correct JSON-formaat."},
                {"role": "user", "content": evaluation_prompt}
            ],
            response_model=Evaluation,
            temperature=0.2
        )
        return result

    except Exception as e:
        raise RuntimeError(f"Error during response evaluation: {str(e)}")

# Main-functie
if __name__ == "__main__":
    medicine_name = "asa"  # Vervang dit door de naam van het medicijn dat je wilt gebruiken
    atc_cluster = "antistolling"  # Vervang dit door de ATC-clusterNAAM die je wilt gebruiken 
    
    client = CLIENT    
    DEBUG_MODE = False  # Zet op False om debug-informatie niet af te drukken
    EVALUATION_MODE = False #zet op True om de evaluatie uit te voeren

    try:
        medicine_info = fetch_medicine_info(medicine_name, atc_cluster)
        if not medicine_info or "No relevant information found" in medicine_info:
            print("Geen relevante medicatie-informatie gevonden. Kan geen quizvraag genereren.")
            exit(1)
       # Print debug-informatie alleen als DEBUG_MODE True is
        if DEBUG_MODE:
            print("DEBUG: Opgehaalde medicatie-informatie:")
            print(medicine_info)
    except Exception as e:
        print(f"Error fetching medicine information: {e}")
        exit(1)

    # Kies een willekeurige kenniscategorie
    random_category = get_random_knowledge_category()
    print(f"\n\n\nGekozen kenniscategorie: {random_category}\n\n")

    # Haal relevante informatie op
    try:
        relevant_info = extract_relevant_info(client, medicine_info, random_category)
        print("DEBUG: Relevante informatie:")
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
    
    #check the quality of the response
    if EVALUATION_MODE:
        print("\n\nEvaluatie van de quizvraag...")
        try:
            evaluation = evaluation(client, response, relevant_info)
            
            print("\nEvaluatie resultaten:")
            print(f"Consistentie: {'Ja' if evaluation.is_consistent else 'Nee'}")
            print(f"Score: {evaluation.score:.2f}")
            print("\nFeedback:")
            print(evaluation.feedback)
            print("\nVerbeterpunten:")
            for suggestion in evaluation.improvement_suggestions:
                print(f"- {suggestion}")
                
        except Exception as e:
            print(f"Error tijdens evaluatie: {e}")

# %%
