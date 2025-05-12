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

# Load environment variables from the .env file
load_dotenv()

# Get the OpenAI API key from the environment
openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    raise ValueError("OpenAI API key not found. Please set it in the .env file.")

client = instructor.from_openai(OpenAI())

# Define your desired output structure using Pydantic
class Reply(BaseModel):
    content: str = Field(description="Your reply that we send to the student.")


# Function to fetch medicine information from www.apotheek.nl
def fetch_medicine_info(medicine_name: str) -> str:
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
def generate_quiz_question(query: str) -> Reply:
    """ 
    Generate a quiz question using the instructor client and information from apotheek.nl.

    Args:
        query (str): The user's query for generating a quiz question.

    Returns:
        Reply: The generated reply containing the quiz question.
    """
    try:
        # Fetch medicine information from apotheek.nl
        medicine_info = fetch_medicine_info(query)

        # Create a chat completion request
        reply = client.chat.completions.create(
            model="gpt-4o-mini",  # Ensure the model name is correct
            response_model=Reply,
            max_retries=2,  # Allow x retries in case of failure
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Je bent een vriendelijke farmacie docent en bedenkt een zeer uitdagende en praktijkgerichte quizvraag voor apothekersassistenten met meer dan 10 jaar werkervaring op bachelorniveau."
                        "Schrijf voordat je de vraag stelt en introductietekst van 1 tot 3 zinnen over het onderwerp van de vraag, waarin je relevante achtergrondinformatie geeft, maar pas op dat je het antwoord op de vraag niet prijsgeeft. Je hoeft niet aan te geven waarom de vraag relevant is. Schrijf alleen inhoudelijke informatie om kennis op te frissen of te verdiepen. Regelmatig introduceer je een patient of een situatie die in de praktijk voordoet" 
                        "Voor elke vraag geef je 4 plausibele antwoordmogelijkheden. Zorg dat deze inhoudelijk en qua stijl op het juiste antwoord lijken." 
                        "Controleer in de medicine_info of de antwoorden ook echt kloppen. Bij twijfel verzin je een ander antwoord. Controleer ook of de introductietekst klopt bij de vraag."
                        "Je geeft ook een uitleg bij het juiste antwoord, in 3 tot 10 zinnen. Daarbij leg je moeilijke termen uit. "
                        "Je schrijft in het Nederlands."
                        "Gebruik niet het woord apothekersassitent of een soortgelijke term. Schrijf geen zinnen zoals: 'Het is essentieel voor apothekersassistenten ...', 'Het is belangrijk voor apothelersassistenten.. ' etc. Dit is niet nodig en komt belerend over. Je schrijft juist aan apothekersassistenten."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Gebruik de volgende informatie over het medicijn {query} van apotheek.nl:\n\n"
                        f"{medicine_info}\n\n"
                        "Bedenk een quizvraag op basis van deze informatie."
                    ),
                },
            ],
        )
        return reply
    except Exception as e:
        raise RuntimeError(f"Failed to generate quiz question: {e}")

if __name__ == "__main__":
    # Test de fetch_medicine_info-functie afzonderlijk
    medicine_name = "metoprolol"

    # Variabele om te bepalen of de tekst moet worden afgedrukt
    print_medicine_info = False  # Zet op False om de tekst niet af te drukken

    try:
        medicine_info = fetch_medicine_info(medicine_name)
        if print_medicine_info:  # Gebruik de variabele hier
            print("Opgehaalde medicatie-informatie:\n")
            print(medicine_info)
    except Exception as e:
        print(f"Error fetching medicine information: {e}")
    
    # Test de generate_quiz_question-functie
    query = medicine_name
    try:
        reply = generate_quiz_question(query)
        print("\n\nGegenereerde quizvraag:\n")
        print(reply.content)
    except Exception as e:
        print(f"Error: {e}")
