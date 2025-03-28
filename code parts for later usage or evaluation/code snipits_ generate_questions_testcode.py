from langchain.tools import Tool
from langchain.utilities import SerpAPIWrapper
from langchain.chat_models import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from langchain.prompts import PromptTemplate
import os

# Zet je API keys hier
os.environ["OPENAI_API_KEY"] = "jouw-openai-api-key"
os.environ["SERPAPI_API_KEY"] = "jouw-serpapi-api-key"

# Definieer de bronnen
trusted_sources = [
    "site:nhg.org",
    "site:knmp.nl",
    "site:apotheek.nl"
]

# Zoekfunctie met SerpAPI
def search_medical_info(query):
    search = SerpAPIWrapper()
    full_query = f"{query} {' OR '.join(trusted_sources)}"
    return search.run(full_query)

# AI-model instellen (GPT-4 via OpenAI API)
llm = ChatOpenAI(model_name="gpt-4", temperature=0.7)

# Prompt voor quizvraaggeneratie
prompt = PromptTemplate(
    input_variables=["info"],
    template="Op basis van de volgende medische informatie, genereer een multiple-choice quizvraag met vier antwoordopties en geef aan welke correct is:\n\n{info}\n\nVraag:"
)

# LangChain Tool maken voor zoekopdracht
search_tool = Tool(
    name="Medical Search",
    func=search_medical_info,
    description="Zoekt medische informatie binnen NHG, KNMP en Apotheek.nl"
)

# Agent initialiseren
agent = initialize_agent(
    tools=[search_tool],
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# Zoek een onderwerp en genereer een quizvraag
def generate_quiz_question(topic):
    search_results = search_medical_info(topic)
    question = llm.predict(prompt.format(info=search_results))
    return question

# Test met een onderwerp
topic = "Antistollingsmedicatie bij ouderen"
quiz_question = generate_quiz_question(topic)
print(quiz_question)



#adjust weight according to user performance; Reinforce Difficult Categories
user_performance = {"Diabetes": 0.8, "Cardiovascular": 0.6, "Respiratory": 0.4}  # Scores (lower = harder)

def adjust_weights_by_performance(categories):
    """Increase frequency of difficult categories"""
    adjusted_weights = {c: (1 - user_performance.get(c, 0.5)) for c in categories}
    return random.choices(list(adjusted_weights.keys()), weights=adjusted_weights.values(), k=1)[0]

print(adjust_weights_by_performance(categories))


#select topic for quizquestion
import random

def select_category():
    categories = list(CATEGORY_WEIGHTS.keys())
    weights = list(CATEGORY_WEIGHTS.values())
    return random.choices(categories, weights=weights, k=1)[0]

# Example: Generate 10 quiz questions with balanced categories
quiz_categories = [select_category() for _ in range(10)]
print(quiz_categories)

#Wwebscraping through AI
import requests

# Example function to query a (hypothetical) API with prescribing data
def get_trending_categories():
    url = "https://api.example.com/pharmacy-trends"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()  # Returns real-time category data
    return ["Diabetes", "Cardiovascular", "Respiratory"]  # Default fallback

trending_categories = get_trending_categories()
print(trending_categories)