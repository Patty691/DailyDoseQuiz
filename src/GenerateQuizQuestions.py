import #fill out

#to do:
#add step to retrieve database information (created in GenerateWeighted...)
#update main accordingly
#example of json

# Step 1: Weighted Selection at atc Level
def weighted_selection_atc(weighted_data):
    """Select an atc category based on weighted probabilities."""
    choices = []
    for atc, data in weighted_data.items():
        choices.extend([atc] * int(data["weight_top500"] * 0.8 + data["weight_growth"] * 0.2))
    return random.choice(choices) if choices else None

# Step 2: Weighted Selection at ATC7 Level
def weighted_selection_atc7(medications):
    """Select an ATC7 medication within the atc cluster based on weight."""
    weighted_choices = [(med["atc7"], med["weight"]) for med in medications]
    total_weight = sum(weight for _, weight in weighted_choices)
    
    if total_weight == 0:
        return None
    
    rand_val = random.uniform(0, total_weight)
    cumulative = 0
    for atc7, weight in weighted_choices:
        cumulative += weight
        if rand_val <= cumulative:
            return atc7
    return None

# Step 3: Generate Quiz Question
def generate_quiz_question(atc7_code):
    """Generate a quiz question using AI prompt based on trusted datasource."""
    # Placeholder for AI integration (e.g., API call to GPT)
    return f"What is the correct usage of medication {atc7_code}?"

# Step 4: Store Quiz Questions
def save_quiz_question(question, filename="quiz_questions.json"):
    """Append the generated question to a JSON file."""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            questions = json.load(f)
    except FileNotFoundError:
        questions = []
    
    questions.append({"question": question})
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=4)

# Main execution
def main():
    selected_atc = weighted_selection_atc(weighted_data)
    if selected_atc and weighted_data[selected_atc]["medications"]:
        selected_atc7 = weighted_selection_atc7(weighted_data[selected_atc]["medications"])
        if selected_atc7:
            question = generate_quiz_question(selected_atc7)
            save_quiz_question(question)
            print(f"Generated question: {question}")

if __name__ == "__main__":
    main()
