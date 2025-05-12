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

# to do
## later: moeilijkheidsgraad toevoegen in output?

""" 
Belangrijke informatie: 
gpt-4o-mini ondersteunt het werken in stappen niet (goed)
gpt-4o-2024-08-06 ondersteunt het werken in stappen
max_retries wordt niet ondersteund in  response= client.beta.chat.completions.parse(
"""

MODEL = "gpt-4o-mini"  # Specify the model you want to use

# Definieer de kenniscategorieën met bijbehorende gewichten
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

# Define your desired output structure using Pydantic
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

    confidence: float = Field(description="Confidence that the final resolution is consistent with the provided input information (value between 0 and 1).")

    class Config:
        json_schema_extra = {
        "required": ["steps", "final_resolution", "confidence"]
        }
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
def get_medicine_info(medicine_name: str) -> str:
    try:
        # Format the search URL dynamically based on the medicine name
        base_url = f"https://www.apotheek.nl/medicijnen/{medicine_name.lower()}"
        response = requests.get(base_url)

        # Check if the request was successful
        if response.status_code != 200:
            raise RuntimeError(f"Failed to fetch data from apotheek.nl (status code: {response.status_code})")

        # Parse the HTML content
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract all <li> elements with the specified class
        list_items = soup.find_all("li", class_="listItemContent_container__25F5W")
        if not list_items:
            return f"Found no URL for {medicine_name} on apotheek.nl, manually look for the right URL."

        # Extract and clean the text from each <li> element
        relevant_text = []
        for item in list_items:
            # Extract the title (e.g., "Hoge bloeddruk")
            title = item.find("h2")
            if title:
                relevant_text.append(title.get_text(strip=False))  # Add the title with a newline

            # Extract the content (e.g., "Verschijnselen", "Mensen met een hoge bloeddruk...")
            content = item.find("div", class_="listItemContent_content__w3Hqp")
            if content:
                relevant_text.append(content.get_text(separator=" ", strip=False))  # Add the content with spaces

        # Join the extracted text with a newline between sections
        cleaned_text = "\n\n".join(relevant_text)

        return cleaned_text

    except Exception as e:
        raise RuntimeError(f"Error fetching medicine info: {e}")

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
        temperature=0.2  # Pas de temperatuur aan voor minder creatieve, meer feitelijke antwoorden
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
    - geen overbodige nadruk op belang.
    - geen formulering zoals 'stel dat'.
    """ 

    role = f"""
    Je bent een farmacie docent en bedenkt praktijkgerichte quizvragen over medicijnen. Gebruik uitsluitend de volgende informatie uit: {relevant_info}. 

    - De vragen zijn uitdagend voor zeer ervaren apothekersassistenten (bachelorniveau).
    - De vragen zijn gericht op het toepassen van kennis in de praktijk.
    - De antwoordopties maken het moeilijk om het juiste antwoord te raden (lijken in stijl en inhoud op het juiste antwoord).
    - Zorg dat je zeker weet dat de foute antwoorden ook echt fout zijn.

    De introductie en uitleg:
    - zijn relevant voor de vraag
    - elk 3 tot 10 zinnen   
    - zijn vakinhoudelijk en geven achtergrondinformatie over het medicijn, zoals farmacologische werking, klinische implicaties en mogelijke uitzonderingen.
    - introduceer een fictieve patiënt (leeftijd, evt. geslacht, aandoening) en een relevante situatie.
    - let op dat de introductie het antwoord op de vraag niet verraad.
    """
                     
    try:
        # Create a chat completion request
        response = client.beta.chat.completions.parse(
            model=MODEL, 
            response_format=Response,
            temperature=0.2,  # Adjust the temperature for creativity
            messages=[
                {"role": "system", "content": style},
                {"role": "system", "content": role},
                {"role": "user", "content": query}
            ],  
        )                  
        return response.choices[0].message.parsed

    except Exception as e:
        raise RuntimeError(f"Failed to generate quiz question: {e}")
    

class Evaluation(BaseModel):
    is_consistent: bool = Field(description="Whether the response is consistent with the source information")
    feedback: str = Field(description="Detailed feedback about the quiz question, correctness, the style and difficulty")
    improvement_suggestions: List[str] = Field(description="List of suggested improvements")
    score: float = Field(description="Overall quality score (0-1)", ge=0, le=1)

def evaluation(client: OpenAI, response: Response, relevant_info: str) -> Evaluation:
    """
    Evaluate the generated quiz question for consistency and quality.
    """
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
        Correct antwoord: {response.final_resolution.antwoord}
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
    medicine_name = "metoprolol"
    client = initialize_openai_client()
    DEBUG_MODE = False  # Zet op False om debug-informatie niet af te drukken
    # Haal medicatie-informatie op
    EVALUATION_MODE = True

    try:
        medicine_info = get_medicine_info(medicine_name)
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
        print(f"\nUitleg: {response.final_resolution.uitleg}")
        print(f"\nBetrouwbaarheid: {response.confidence}")

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
