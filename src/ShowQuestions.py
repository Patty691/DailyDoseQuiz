import json
import random
from datetime import datetime

# Open en laad het JSON-bestand
with open('/Users/pattynooijen/Documents/VisualStudioCode/daliy_dose_quiz/data/questions.json', 'r') as file:
    questions = json.load(file)

# Selecteer goedgekeurde en nog niet gestelde vragen
valid_questions = [q for q in questions if q["approved"] and q["statistics"]["date_shown"] is None]

if valid_questions:
    random_question = random.choice(valid_questions)
    
    print(random_question['question'])
    print(random_question['options'])
    print(random_question['answer'])
    print(random_question["explanation"])
      
    # Mark the question as asked today and safe to json
    random_question["statistics"]["date_shown"] = datetime.today().date().isoformat()
    with open('/Users/pattynooijen/Documents/VisualStudioCode/daliy_dose_quiz/data/questions.json', 'w') as file:
        json.dump(questions, file, indent=4)
else:
    print("No questions available")


# show question and options to user
# get user input
# compare answer to user input
# provide feedback
# show correct answer and explanation to user 
# collect data on user response
