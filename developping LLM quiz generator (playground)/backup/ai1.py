from openai import OpenAI
from dotenv import load_dotenv
import os
import instructor
from pydantic import BaseModel, Field
from openai import OpenAI
from enum import Enum

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

# Function to generate a quiz question
def generate_quiz_question(query: str) -> Reply:
    """
    Generate a quiz question using the instructor client.

    Args:
        query (str): The user's query for generating a quiz question.

    Returns:
        Reply: The generated reply containing the quiz question.
    """
    try:
        # Create a chat completion request
        reply = client.chat.completions.create(
            model="gpt-4o-mini",  # Ensure the model name is correct
            response_model=Reply,
            max_retries=2,  # Allow 2 retries in case of failure
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Je bent een docent en bedenkt een uitdagende en praktijkgerichte quizvraag "
                        "voor apothekersassistenten op bachelorniveau. Voor elke vraag geef je 4 antwoordmogelijkheden. "
                        "Je geeft ook een uitleg bij het juiste antwoord, in 5 tot 10 zinnen. Daarbij leg je moeilijke termen uit. "
                        "Je schrijft in het Nederlands."
                    ),
                },
                {"role": "user", "content": query},
            ],
        )
        return reply
    except Exception as e:
        raise RuntimeError(f"Failed to generate quiz question: {e}")

# Example usage
if __name__ == "__main__":
    query = "Bedenk een quizvraag over metoprolol"
    try:
        reply = generate_quiz_question(query)
        print("Generated Quiz Question:")
        print(reply.content)
    except Exception as e:
        print(f"Error: {e}")
