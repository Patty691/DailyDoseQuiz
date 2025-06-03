
from langchain.llms import OpenAI
from pydantic import BaseModel, ValidationError, validator
import json

# create LLM chain with langchain, pydantic and instructor for the question, answers etc.  
# start with a basic function, which we can further develop, use # to explain where and how to develop.

# Object of the function:
# The function should generate a quiz question based on the input data.

# The input data includes:
    # atc 7 code
    # name of the medicine
    # brand name of the medicine?

# The function should be a RAG system.
    # The function should use the apotheek.nl website as source.
    # The function should use the ATC code or name of the medication to find the relevant information on the apotheek.nl website.
    # The function should use the information from the apotheek.nl website to generate the quiz question.
    # The answer options, correct answer and explanation should be based on apotheek.nl website, if not sufficient information is available, the function should use the information from reliable medical sources and state from which source the information is coming.


# The role and the context for the ai:
    # The AI should act as a medical quiz question generator.
    # The AI should generate a quiz question for pharmacy assistants at bachelor level.
    # The question should be practical and relevant to the daily practice of pharmacy assistants.
    # The AI should provide 4 answer options for the quiz question.
    # The AI should ensure that the question is clear and unambiguous.
    # The AI should also provide the correct answer and an explanation for the correct answer, including background information.
    # The AI should ensure that the question is relevant to the clinical area and knowledge category.
    # The AI should also ensure that the question is appropriate for the target patient category.
    # The AI should ensure that the question is appropriate for the specified difficulty level.
    # The AI should provide the thought process and reasoning behind the question generation.

# The structured output should be in the following format:
    # - question: The quiz question itself
    # - options: A list of answer options
    # - answer: The correct answer
    # - explanation: Explanation for the correct answer
    # - clinical_area: The clinical area related to the question
    # - knowledge_category: The category of knowledge being tested
    # - difficulty: The difficulty level of the question


        # - add id: Unique identifier for the question
"""
Stap 4: Uitbreiding
LangChain-keten:
Voeg een keten toe om meerdere stappen te combineren, zoals ophalen van informatie van apotheek.nl en genereren van vragen.
Validatie met Pydantic:
Gebruik Pydantic om de structuur van de gegenereerde vragen te valideren.
Logging en foutafhandeling:
Voeg logging toe om fouten en waarschuwingen te registreren.
Integratie met externe bronnen:
Gebruik een scraper of API om informatie van apotheek.nl op te halen.""" 


VALID_CLINICAL_AREAS = [
    "Cardiovascular", "Respiratory", "Gastrointestinal", "Neurology", 
    "Psychiatry", "Diabetes", "Endocrinology", "Urology", "Gynecology", 
    "Dermatology", "Rheumatology", "Oncology", "Hematology", 
    "Infectious Diseases", "Ophthalmology", "Ear Nose and Throat", 
    "Pain Management", "Emergency Situations", "Musculoskeletal", 
    "Metabolic", "Vitamin Deficiencies and Supplements", 
    "Central Nervous System", "Sleep Disorders", "Addiction Care", 
    "Palliative Care", "Autoimmune Diseases", 
]

VALID_KNOWLEDGE_CATEGORIES = [
    "Indications", "Mechanism of Action", "Pharmacokinetics", 
    "Pharmacodynamics", "Dosing", "Administration", "Interactions", 
    "Contraindications", "Side Effects", "Monitoring", "Discontinuation"
]

VALID_PATIENT_CATEGORIES = [
    "Pediatric", "Adults (without specific conditions)", "Elderly", 
    "Pregnancy and Lactation", "Renal Impairment", "Hepatic Impairment", 
    "Immunocompromised Patients", "Obese Patients"
]

VALID_DIFFICULTY = ["Easy", "Medium", "Hard"]

""" 
def new_quiz_question(id, question, options, answer, clinical_area, knowledge_category, difficulty):
    if clinical_area not in VALID_CLINICAL_AREAS:
        raise ValueError(f"Invalid clinical area: {clinical_area}. Choose from {VALID_CLINICAL_AREAS}")
    
    if knowledge_category not in VALID_KNOWLEDGE_CATEGORIES:
        raise ValueError(f"Invalid knowledge category: {knowledge_category}. Choose from {VALID_KNOWLEDGE_CATEGORIES}")
    
    if difficulty not in VALID_DIFFICULTY:
        raise ValueError(f"Invalid difficulty: {difficulty}. Choose from {VALID_DIFFICULTY}")
    
    return     {
        "id": "id_value",
        "question": "question_value",
        "options": [
            "option1",
            "option2",
            "option3",
            "option4"
        ],
        "answer": "answer_value",
        "explanation": "This is the explanation for why the correct answer is correct.",
        "clinical_area": "clinical_area",
        "knowledge_category": "knowledge_category",
        "difficulty": "difficulty_value",
        "source": "information_source",
        "approved": false,
        "statistics": {
            "date_shown": null,
            "total_responses": 0,
            "correctly_answered": 0,
            "total_answered": {
                "option1": 0,
                "option2": 0,
                "option3": 0,
                "option4": 0
            }
        }
    },


# assign ID to each question and export question to json
with open('/Users/pattynooijen/Documents/VisualStudioCode/daliy_dose_quiz/data/questions.json', 'r') as file:
    questions = json.load(file)
    #find highest ID nr and add new ID per question

    with open('/Users/pattynooijen/Documents/VisualStudioCode/daliy_dose_quiz/data/questions.json', 'w') as file:
        json.dump(questions, file, indent=4)
""" 


# Pydantic model for validating the quiz question structure
class QuizQuestion(BaseModel):
    id: int
    question: str
    options: list[str]
    answer: str
    explanation: str
    clinical_area: str
    knowledge_category: str
    difficulty: str
    source: str
    approved: bool = False
    statistics: dict = {
        "date_shown": None,
        "total_responses": 0,
        "correctly_answered": 0,
        "total_answered": {
            "option1": 0,
            "option2": 0,
            "option3": 0,
            "option4": 0
        }
    }

    # Validators for specific fields
    @validator("clinical_area")
    def validate_clinical_area(cls, value):
        if value not in VALID_CLINICAL_AREAS:
            raise ValueError(f"Invalid clinical area: {value}. Choose from {VALID_CLINICAL_AREAS}")
        return value

    @validator("knowledge_category")
    def validate_knowledge_category(cls, value):
        if value not in VALID_KNOWLEDGE_CATEGORIES:
            raise ValueError(f"Invalid knowledge category: {value}. Choose from {VALID_KNOWLEDGE_CATEGORIES}")
        return value

    @validator("difficulty")
    def validate_difficulty(cls, value):
        if value not in VALID_DIFFICULTY:
            raise ValueError(f"Invalid difficulty: {value}. Choose from {VALID_DIFFICULTY}")
        return value


# Function to generate a quiz question using LangChain
def generate_quiz_question(atc7_code, medicine_name, brand_name=None):
    """
    Generate a quiz question using LangChain and validate it with Pydantic.

    Args:
        atc7_code (str): The ATC7 code of the medicine.
        medicine_name (str): The name of the medicine.
        brand_name (str, optional): The brand name of the medicine.

    Returns:
        dict: A validated quiz question.
    """
    # Initialize the LLM (e.g., OpenAI GPT)
    llm = OpenAI(model="text-davinci-003", temperature=0.7)

    # Prompt for the LLM
    prompt = f"""
    Generate a quiz question on a bachelor level for pharmacy assistants based on the following data:
    - ATC7 code: {atc7_code}
    - Medicine name: {medicine_name}
    - Brand name: {brand_name or "N/A"}

    The datasource is www.apotheek.nl. (build in a function)

    The question should include:
    - A clear and practical question
    - Four answer options, without any prefixes 
    - The correct answer
    - An explanation for the correct answer, including explanation of difficult terminology
    - Clinical area, knowledge category, and difficulty level
    - Source of the information
    """

    # Generate the response
    response = llm(prompt)

    # Parse the response into a dictionary
    try:
        question_data = json.loads(response)
    except json.JSONDecodeError:
        raise ValueError("The LLM response is not valid JSON.")

    # Validate the response with Pydantic
    try:
        validated_question = QuizQuestion(**question_data)
    except ValidationError as e:
        raise ValueError(f"Validation error: {e}")

    return validated_question.dict()

def save_quiz_question(question_data, json_file_path):
    """
    Save the quiz question to a JSON file.

    Args:
        question_data (dict): The quiz question data.
        json_file_path (str): Path to the JSON file.

    Returns:
        None
    """
    try:
        with open(json_file_path, "r", encoding="utf-8") as file:
            questions = json.load(file)
    except FileNotFoundError:
        questions = []

    # Assign a unique ID to the question
    new_id = max((q["id"] for q in questions), default=0) + 1
    question_data["id"] = new_id

    # Append the new question and save
    questions.append(question_data)
    with open(json_file_path, "w", encoding="utf-8") as file:
        json.dump(questions, file, indent=4)

if __name__ == "__main__":
    # Example input
    atc7_code = "A02BC02"
    medicine_name = "Pantoprazol"
    brand_name = "Pantozol"

    # Generate a quiz question
    try:
        question = generate_quiz_question(atc7_code, medicine_name, brand_name)
        print("Generated Question:", question)

        # Save the question to a JSON file
        json_file_path = "/Users/pattynooijen/Documents/VisualStudioCode/daily_dose_quiz/data/questions.json"
        save_quiz_question(question, json_file_path)
        print("Quiz question saved successfully!")
    except Exception as e:
        print(f"Error: {e}")