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
from PromptQuizQuestion import QuizPrompts
from GetMedicineInfo import fetch_medicine_info


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

                           
# Define the initialize_openai_client function
def initialize_openai_client() -> instructor.Instructor:
    # Load environment variables from the .env file
    load_dotenv()

    # Get the OpenAI API key from the environment
    openai_api_key = os.getenv("OPENAI_API_KEY")

    # Debug information
    print("Checking OpenAI API key configuration...")
    if openai_api_key:
        print("API key found in environment variables")
    else:
        print("API key not found in environment variables")
        # Try to load from .env file directly
        try:
            with open('.env', 'r') as env_file:
                print("Contents of .env file:")
                print(env_file.read())
        except FileNotFoundError:
            print(".env file not found in current directory")
        except Exception as e:
            print(f"Error reading .env file: {e}")

    if not openai_api_key:
        raise ValueError("OpenAI API key not found. Please set it in the .env file.")

    # Initialize the OpenAI client
    try:
        client = OpenAI(api_key=openai_api_key)
        return instructor.from_openai(client)
    except Exception as e:
        raise RuntimeError(f"Failed to initialize OpenAI client: {e}")


# Function to fetch medicine information from www.apotheek.nl
def fetch_medicine_info(medicine_name: str, atc_cluster: str) -> str:
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


# Functie om relevante informatie te extraheren met een LLM
def extract_relevant_info(client: openai, medicine_info: str, random_category: str) -> str:
    # Use the extraction prompt from QuizPrompts
    prompt = QuizPrompts.get_extraction_prompt(medicine_info, random_category)
    
    # Maak een chat completion request
    response = client.beta.chat.completions.parse(
        model=MODEL,
        response_format=Extraction,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3  # Pas de temperatuur naar beneden aan voor minder creatieve, meer feitelijke antwoorden
    )
    
    # Controleer of de respons een 'choices'-attribuut bevat
    if not hasattr(response, "choices"):
        raise RuntimeError("De respons bevat geen 'choices'-attribuut. Controleer de API-aanroep.")
    
    # Retourneer de inhoud van de eerste keuze
    return response.choices[0].message.parsed

# Function to generate a quiz question
def generate_quiz_question(query: str, relevant_info: str, random_category: str) -> Response:
    try:
        # Create a chat completion request
        response = client.beta.chat.completions.parse(
            model=MODEL, 
            response_format=Response,
            temperature=0.1,  # Adjust the temperature for creativity
            messages=[
                {"role": "system", "content": QuizPrompts.STYLE},
                {"role": "system", "content": f"{QuizPrompts.ROLE}\nGebruik uitsluitend de volgende informatie: {relevant_info}."},
                {"role": "system", "content": QuizPrompts.INSTRUCTIONS},
                {"role": "user", "content": query}
            ],  
        )                  
        return response.choices[0].message.parsed

    except Exception as e:
        raise RuntimeError(f"Failed to generate quiz question: {e}")
    

# Main-functie
if __name__ == "__main__":
    medicine_name = "metoprolol"  # Vervang dit door de naam van het medicijn dat je wilt gebruiken
    atc_cluster = "betablokkers"  # Vervang dit door de ATC-clusterNAAM die je wilt gebruiken 
    
    DEBUG_MODE = True  # Set to True to see debug information
    
    # Initialize the client
    try:
        print("\nInitializing OpenAI client...")
        CLIENT = initialize_openai_client()
        print("OpenAI client initialized successfully")
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}")
        exit(1)
    
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
        relevant_info = extract_relevant_info(CLIENT, medicine_info, random_category)
        print("Relevante informatie:")
        print(relevant_info)
    except Exception as e:
        print(f"Error extracting relevant information: {e}")
        exit(1)

    #Genereer een quizvraag
    print("\nQuizvraag genereren...")
    query = f"De vraag moet gaan over {medicine_name} en betrekking hebben op de categorie: {random_category}."    
    print (f"\n\nQuery: {query}\n")
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
    
    