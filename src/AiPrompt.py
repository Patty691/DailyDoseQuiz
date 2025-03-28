
import json

#question format
# add tools in format: show source!?!

VALID_CLINICAL_AREAS = [
    "Cardiovascular", "Respiratory", "Gastrointestinal", "Neurology", 
    "Psychiatry", "Diabetes", "Endocrinology", "Urology", "Gynecology", 
    "Dermatology", "Rheumatology", "Oncology", "Hematology", 
    "Infectious Diseases", "Ophthalmology", "Ear Nose and Throat", 
    "Pain Management", "Emergency Situations", "Musculoskeletal", 
    "Metabolic", "Vitamin Deficiencies and Supplements", 
    "Central Nervous System", "Sleep Disorders", "Addiction Care", 
    "Palliative Care", "Autoimmune Diseases"
]

VALID_KNOWLEDGE_CATEGORIES = [
    "Indications", "Mechanism of Action", "Pharmacokinetics", 
    "Pharmacodynamics", "Dosing", "Administration", "Interactions", 
    "Contraindications", "Side Effects", "Monitoring", 
    "Storage and Stability", "Discontinuation"
]

#nog toevoegen aan json/andere documenten 
VALID_PATIENT_CATEGORIES = [
    "Pediatric", "Adults (without specific conditions)", "Elderly", 
    "Pregnancy and Lactation", "Renal Impairment", "Hepatic Impairment", 
    "Immunocompromised Patients", "Obese Patients"
]

VALID_DIFFICULTY = ["Easy", "Medium", "Hard"]

def new_quiz_question(id, question, options, answer, clinical_area, knowledge_category, difficulty, target_audience):
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

# get AI to generate a question, format = json data, question is numbered, make sure explanation is long enough, use only allowed tools
def_generate_questions(new_quiz_question)
number_of_questions = 10

#how many?



# assign ID to each question and export question to json
with open('/Users/pattynooijen/Documents/VisualStudioCode/daliy_dose_quiz/data/questions.json', 'r') as file:
    questions = json.load(file)
    #find highest ID nr and add new ID per question

    with open('/Users/pattynooijen/Documents/VisualStudioCode/daliy_dose_quiz/data/questions.json', 'w') as file:
        json.dump(questions, file, indent=4)

 


