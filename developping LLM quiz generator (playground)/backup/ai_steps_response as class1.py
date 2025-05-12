# %%
from openai import OpenAI
from dotenv import load_dotenv
import os
import instructor
from pydantic import BaseModel, Field
from openai import OpenAI
from enum import Enum
import requests
from bs4 import BeautifulSoup
from typing import List

##gpt-4o-mini ondersteund het werken in stappen niet
##gpt-4o-2024-08-06 ondersteund het werken in stappen
MODEL = "gpt-4o-mini"

# check de rollen. hoe is de beschrijving. nogal veel tokens lijkt me? zeker met de hele tekst uit apotheek.nl. ook veel dubbelingen in vragen. ook ontevreden over aantal aspecten in de response.
# vraag chat-gpt (co-pilot) advies. vraag waar eerst naar te kijken en verbeter stap voor stap. 
# prompt aanpassen mbv chat gpt.
# tekst eerst opknippen?
# temperatuur aanpassen? 

##   max_retries wordt niet ondersteund in  response= client.beta.chat.completions.parse(

# Load environment variables from the .env file
load_dotenv()

# Get the OpenAI API key from the environment
openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    raise ValueError("OpenAI API key not found. Please set it in the .env file.")

client = instructor.from_openai(OpenAI())

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
            return f"No relevant information found for {medicine_name} on apotheek.nl."

        # Extract and clean the text from each <li> element
        relevant_text = []
        for item in list_items:
            # Extract the title (e.g., "Hoge bloeddruk")
            title = item.find("h2")
            if title:
                relevant_text.append(title.get_text(strip=True))  # Add the title with a newline

            # Extract the content (e.g., "Verschijnselen", "Mensen met een hoge bloeddruk...")
            content = item.find("div", class_="listItemContent_content__w3Hqp")
            if content:
                relevant_text.append(content.get_text(separator=" ", strip=True))  # Add the content with spaces

        # Join the extracted text with a newline between sections
        cleaned_text = "\n\n".join(relevant_text)

        return cleaned_text

    except Exception as e:
        raise RuntimeError(f"Error fetching medicine info: {e}")


# Function to generate a quiz question
def generate_quiz_question(query: str) -> Response:
    """ 
    Generate a quiz question using the instructor client and information from apotheek.nl.

    Args:
        query (str): The user's query for generating a quiz question.

    Returns:
        Response: The generated reply containing the quiz question.
    """
    try:
        # Fetch medicine information from apotheek.nl
        medicine_info = get_medicine_info(query)

        # Create a chat completion request
        response = client.beta.chat.completions.parse(
            model= MODEL, 
            response_format=Response,
            temperature=0.7,  # Adjust the temperature for creativity
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Je bent een farmacie docent en bedenkt uitdagende en praktijkgerichte quizvragen. Zorg ervoor dat elke vraag uniek is en een ander aspect van het medicijn benadrukt, zoals bijwerkingen, interacties, dosering, of gebruiksinstructies. Vermijd herhaling van eerdere vragen."                        "Gebruik niet het woord apothekersassistent of een soortgelijke term. Schrijf geen zinnen zoals: 'Het is essentieel voor apothekersassistenten ...', 'Het is belangrijk voor apothekersassistenten.. ' ' het is belangrijk om te weten'  etc. Dit is niet nodig en komt belerend over. Je schrijft juist aan apothekersassistenten. Je mag wel schrijven hoe ze deze kennis kunnen gebruiken in hun werk. Schrijf dan in de je-vorm. "
                        "Voor elke vraag geef je 4 plausibele antwoordmogelijkheden. Zorg dat deze inhoudelijk en qua stijl op het juiste antwoord lijken en dat het moeilijk, maar wel eenduidig, is het goede antwoord te raden." 
                        "Controleer in de medicine_info of de antwoorden ook echt kloppen. Bij twijfel verzin je een ander antwoord. Controleer ook of de introductietekst klopt bij de vraag."
                        "Je geeft ook een uitleg bij het juiste antwoord, in 1 tot 6 zinnen. Daarbij leg je moeilijke termen uit. "
                        "Schrijf pas nadat je de vraag en antwoordopties hebt gegegeven een introductietekst voor de vraag (1 tot 3 zinnen) over het onderwerp van de vraag, waarin je relevante achtergrondinformatie geeft, maar pas op dat je het antwoord op de vraag niet prijsgeeft. Je hoeft niet aan te geven waarom de vraag relevant is. Schrijf alleen inhoudelijke informatie om kennis op te frissen of te verdiepen. Regelmatig introduceer je een patiënt of een situatie die in de praktijk voorkomt." 
                        "Je schrijft in het Nederlands."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Gebruik de volgende informatie over het medicijn {query} van apotheek.nl:\n\n"
                        f"{medicine_info}\n\n"
                        "Bedenk een quizvraag op basis van deze informatie. Zorg ervoor dat de output het volgende JSON-formaat heeft:\n\n"
                        "{\n"
                        "  \"steps\": [\n"
                        "    {\n"
                        "      \"description\": \"[Beschrijving van de stap]\",\n"
                        "      \"action\": \"[Actie die is uitgevoerd]\",\n"
                        "      \"result\": \"[Resultaat van de actie]\"\n"
                        "    },\n"
                        "    ...\n"
                        "  ],\n"
                        "  \"final_resolution\": {\n"
                        "    \"introductie\": \"[Introductietekst]\",\n"
                        "    \"vraag\": \"[De quizvraag]\",\n"
                        "    \"antwoordopties\": {\n"
                        "      \"[Antwoordoptie A]\",\n"
                        "      \"[Antwoordoptie B]\",\n"
                        "      \"[Antwoordoptie C]\",\n"
                        "      \"[Antwoordoptie D]\"\n"
                        "    },\n"
                        "    \"antwoord\": \"[Het juiste antwoord]\",\n"
                        "    \"uitleg\": \"[Een uitleg van 3 tot 10 zinnen over het juiste antwoord, inclusief uitleg van moeilijke termen.]\"\n"
                        "  },\n"
                        "  \"confidence\": [Een waarde tussen 0 en 1 die aangeeft hoe zeker je bent van de gegenereerde output]\n"
                        "}"
                    ),
                },
            ],
        )
        return response.choices[0].message.parsed

    except Exception as e:
        raise RuntimeError(f"Failed to generate quiz question: {e}")


if __name__ == "__main__":
    # Test de get_medicine_info-functie afzonderlijk
    medicine_name = "metoprolol"

    # Variabele om te bepalen of de tekst moet worden afgedrukt
    print_medicine_info = False  # Zet op False om de tekst niet af te drukken

    try:
        medicine_info = get_medicine_info(medicine_name)
        if print_medicine_info:  # Gebruik de variabele hier
            print("Opgehaalde medicatie-informatie:\n")
            print(medicine_info)
    except Exception as e:
        print(f"Error fetching medicine information: {e}")
    
    # Test de generate_quiz_question-functie
    print("Generating a question")
    query = medicine_name
    try:
        response = generate_quiz_question(query)
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
