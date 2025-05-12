# %%
from dotenv import load_dotenv
import os
import instructor
import random
from pydantic import BaseModel, Field
from openai import OpenAI
from enum import Enum
import requests
from bs4 import BeautifulSoup
from typing import List


# prompt verkorten. misschien niet alle informatie van aopotheek.nl gebruiken? of andere methode om op te halen/de tekst te verkorten. een LLM ervoor zetten: gegevens over {middel} en {categorie} extraheren, dan voeren aan gpt-4o-mini?
# als medicijn info niet opgehaald kan worden: geen vraag genereren
#vectorizing input
# implementeren langchain

# feedbackmechanisme om de output te verbeteren: nieuw prompt: zoek het antwoord op de vraag op apotheek.nl (en geef een uitleg)

# later: moeilijkheidsgraad toevoegen in output?




##gpt-4o-mini ondersteunt het werken in stappen niet (goed)
##gpt-4o-2024-08-06 ondersteunt het werken in stappen
##   max_retries wordt niet ondersteund in  response= client.beta.chat.completions.parse(


MODEL = "gpt-4o-mini"  # Specify the model you want to use

# Definieer de kenniscategorieën met bijbehorende gewichten
KNOWLEDGE_CATEGORIES = {
    "indicaties": 4,
    "werkingsmechanisme": 4,
    "farmacokinetiek": 1,
    "farmacodynamiek": 1,
    "dosering": 1,
    "toediening": 1,
    "interacties": 4,
    "contra-indicaties": 4,
    "bijwerkingen": 4,
    "monitoring": 2,
    "rijvaardigheid": 1,
    "stoppen met gebruik": 1,
    "bijzondere populaties (bijv. ouderen, obesen, kinderen, zwangeren, borstvoeding)": 1,
}

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
        antwoordopties: List[str] = Field(description="The answer options for the quiz question.")
        antwoord: str = Field(description="The correct answer to the quiz question.")
        uitleg: str = Field(description="The explanation for the correct answer.")
    final_resolution: FinalResolution

    confidence: float = Field(description="Confidence in the resolution (0-1)")

    class Config:
        json_schema_extra = {
        "required": ["steps", "final_resolution", "confidence"]
        }
# Define the initialize_openai_client function
def initialize_openai_client() -> instructor.Instructor:
    """
    Initialize the OpenAI client using the API key from the environment.

    Returns:
        instructor.Instructor: The initialized OpenAI client.
    """
    # Load environment variables from the .env file
    load_dotenv()

    # Get the OpenAI API key from the environment
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if not openai_api_key:
        raise ValueError("OpenAI API key not found. Please set it in the .env file.")

    return instructor.from_openai(OpenAI())


# Function to fetch medicine information from www.apotheek.nl
def get_medicine_info(medicine_name: str) -> str:
    """
    Fetch information about a medicine from www.apotheek.nl.

    Args:
        medicine_name (str): The name of the medicine to search for.

    Returns:
        str: A summary of the medicine's information.
    """
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

# Function to generate a quiz question
def generate_quiz_question(query: str, medicine_info: str, random_category: str) -> Response:
    """ 
    Generate a quiz question using the instructor client and information from apotheek.nl.

    Args:
        query (str): The user's query for generating a quiz question.
        medicine_info (str): The medicine information fetched from apotheek.nl.
        random_category (str): The chosen knowledge category.

    Returns:
        Response: The generated reply containing the quiz question.
    """
    try:
        # Create a chat completion request
        response = client.beta.chat.completions.parse(
            model=MODEL, 
            response_format=Response,
            temperature=0.6,  # Adjust the temperature for creativity
            messages=[
                {
                    "role": "system",
                    "content": f"""
Je bent een farmacie docent en bedenkt praktijkgerichte quizvragen over medicijnen. Gebruik uitsluitend de volgende informatie uit: {medicine_info}. 

Aanvullende instructies:
De vragen zijn uitdagend voor zeer ervaren apothekersassistenten (bachelorniveau).
De vragen zijn gericht op het toepassen van kennis in de praktijk.

De introductie en uitleg (elk 3 tot 10 zinnen):   
 - zijn vakinhoudelijk en geven achtergrondinformatie over het medicijn, zoals farmacologische werking, klinische implicaties en mogelijke uitzonderingen.
 - introduceer een fictieve patiënt (leeftijd, geslsacht, aandoening) en een relevante situatie.
 - gebruik toegankelijke, maar vakinhoudelijke taal.
 - let op dat de introductie de vraag niet al te veel verklapt.

Schrijftijl:
- in het Nederlands
- in de je-vorm 
- richt je aan de apothekersassistent (noem dit niet expliciet).
- schrijf duidelijk, inhoudelijk sterk en zonder overbodige nadruk op belang.

Voorbeeld:
De vraag moet gaan over het werkingsmechanisme van metoprolol.
Introductie:
Een 78-jarige patiënt met atriumfibrilleren komt voor herhaalmedicatie. Je ziet dat hij metoprolol gebruikt. 
Een goed begrip van het werkingsmechanisme van metoprolol helpt om bijwerkingen beter te herkennen, zeker bij oudere patiënten met comorbiditeiten.

Vraag:
Wat is het primaire effect van metoprolol?

Antwoordopties:
A) Verhoogt de hartfrequentie 
B) Verlaagt de hartfrequentie 
C) Verhoogt perifere vasodilatatie 
D) Vermindert vasoconstrictie 

Correct antwoord:
B) Verlaagt de hartfrequentie 

Uitleg:
Metoprolol is een cardioselectieve bètablokker. Het blokkeert vooral de β1-adrenerge receptoren in het hart.
Hierdoor daalt de hartfrequentie, neemt de kracht van de hartcontractie af en vermindert de zuurstofbehoefte van de hartspier.
Deze effecten helpen om de bloeddruk te verlagen en hartritmestoornissen te stabiliseren.
Tegelijkertijd kunnen ze ook bijwerkingen veroorzaken, zoals: bradycardie (trage hartslag), hypotensie (lage bloeddruk), duizeligheid en vermoeidheid.
Hoewel metoprolol relatief β1-selectief is, kan het bij hogere doseringen ook β2-receptoren blokkeren.
Dit kan leiden tot benauwdheid, vooral bij patiënten met astma of COPD.
"""
                },
                {
                    "role": "user",
                    "content": f"""
Bedenk een quizvraag. {query}
"""
                }
            ]
        )
        return response.choices[0].message.parsed

    except Exception as e:
        raise RuntimeError(f"Failed to generate quiz question: {e}")
if __name__ == "__main__":
    medicine_name = "metoprolol"
    
    client = initialize_openai_client() 

    # Variabele om te bepalen of de tekst moet worden afgedrukt
    print_medicine_info = False  # Zet op False om de tekst niet af te drukken

    try:
        medicine_info = get_medicine_info(medicine_name)
        if print_medicine_info:  # Gebruik de variabele hier
            print("Opgehaalde medicatie-informatie:\n")
            print(medicine_info)
    except Exception as e:
        print(f"Error fetching medicine information: {e}")

    # Kies een willekeurige kenniscategorie
    random_category = get_random_knowledge_category()
 
    #Genereer een quizvraag
    print("\nStap 3: Quizvraag genereren...")
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


       

# %%
