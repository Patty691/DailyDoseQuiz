# %%
from dotenv import load_dotenv
import os
import instructor
import random
import openai
from openai import OpenAI
from enum import Enum
from typing import List
from PromptQuizQuestion import QuizPrompts
from GetMedicineInfo import get_medicine_info 
from OutputModels import Response, Extraction


# get_medicine_info is verwijderd uit dit bestand. check of het afzonderlijke bestand goed gebruikt wordt.
#zorg ervoor dat als de informatie niet wordt opgehaald, of de relevante informatie niet beschikbaar is, de quizvraag niet wordt gegenereerd.
#langchain inbouwen
#Models in een afzonderlijk bestand
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

# Function to handle the complete question generation process
def generate_quiz_question(medicine_name: str, medicine_info: str, debug_mode: bool = False) -> Response:
    """
    Handles the complete process of generating a quiz question:
    1. Gets a random category
    2. Extracts relevant information
    3. Generates the quiz question
    
    Args:
        medicine_name: Name of the medicine
        medicine_info: Complete medicine information
        debug_mode: Whether to print debug information
        
    Returns:
        Response: The generated question with all its components
    """
    try:
        # Initialize client
        client = initialize_openai_client()
        
        # Get random category
        random_category = get_random_knowledge_category()
        if debug_mode:
            print(f"\nGekozen kenniscategorie: {random_category}")
            
        # Extract relevant information
        relevant_info = extract_relevant_info(client, medicine_info, random_category)
        if debug_mode:
            print("\nRelevante informatie:")
            print(relevant_info)
            
        # Generate query
        query = f"De vraag moet gaan over {medicine_name} en betrekking hebben op de categorie: {random_category}"
        if debug_mode:
            print(f"\nQuery: {query}")
            
        # Generate question using the same client
        response = client.beta.chat.completions.parse(
            model=MODEL, 
            response_format=Response,
            temperature=0.6,  # Adjust the temperature for creativity
            messages=[
                {"role": "system", "content": QuizPrompts.STYLE},
                {"role": "system", "content": f"{QuizPrompts.ROLE}\nGebruik uitsluitend de volgende informatie: {relevant_info}."},
                {"role": "system", "content": QuizPrompts.INSTRUCTIONS},
                {"role": "user", "content": query}
            ],  
        )                  
        return response.choices[0].message.parsed
            
    except Exception as e:
        raise RuntimeError(f"Failed to generate complete quiz question: {e}")


# Define the initialize_openai_client function
def initialize_openai_client() -> instructor.Instructor:
    # Load environment variables from the .env file
    load_dotenv()

    # Get the OpenAI API key from the environment
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if not openai_api_key:
        raise ValueError("OpenAI API key not found. Please set it in the .env file.")

    return instructor.from_openai(OpenAI())


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

# Main-functie
if __name__ == "__main__":
    medicine_name = "aska"  # Vervang dit door de naam van het medicijn dat je wilt gebruiken
    atc_cluster = "geen"  # Vervang dit door de ATC-clusterNAAM die je wilt gebruiken 
    
    DEBUG_MODE = True  # Zet op False om debug-informatie niet af te drukken
        
    try:
        medicine_info = get_medicine_info(medicine_name, atc_cluster)
        if not medicine_info or "No relevant information found" in medicine_info:
            print("Geen relevante medicatie-informatie gevonden. Kan geen quizvraag genereren.")
            exit(1)
            
        response = generate_quiz_question(medicine_name, medicine_info, DEBUG_MODE)
        
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
    
    