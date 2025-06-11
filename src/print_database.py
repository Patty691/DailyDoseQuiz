import sqlite3
import os
from datetime import datetime

# Database pad
DB_PATH = "/Users/pattynooijen/Documents/VisualStudioCode/daily_dose_quiz/data/QuizQuestions.db"

def print_database_contents():
    """Print alle inhoud van de database in een leesbaar formaat."""
    if not os.path.exists(DB_PATH):
        print(f"Database niet gevonden op: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Print information table
    print("\n=== INFORMATION TABLE ===")
    c.execute("SELECT * FROM information")
    rows = c.fetchall()
    if rows:
        # Get column names
        columns = [description[0] for description in c.description]
        print("\nColumns:", ", ".join(columns))
        for row in rows:
            print("\n--- Information Entry ---")
            for col, val in zip(columns, row):
                if col in ['llm_raw_output', 'geëxtraheerde_informatie']:
                    print(f"{col}: [Lange tekst, niet getoond]")
                else:
                    print(f"{col}: {val}")
    else:
        print("Geen informatie gevonden in information table")

    # Print generated_quiz_questions table
    print("\n=== GENERATED QUIZ QUESTIONS TABLE ===")
    c.execute("SELECT * FROM generated_quiz_questions")
    rows = c.fetchall()
    if rows:
        columns = [description[0] for description in c.description]
        print("\nColumns:", ", ".join(columns))
        for row in rows:
            print("\n--- Quiz Question ---")
            for col, val in zip(columns, row):
                if col == 'llm_raw_output':
                    print(f"{col}: [Lange tekst, niet getoond]")
                else:
                    print(f"{col}: {val}")
    else:
        print("Geen vragen gevonden in generated_quiz_questions table")

    # Print evaluations table
    print("\n=== EVALUATIONS TABLE ===")
    c.execute("SELECT * FROM evaluations")
    rows = c.fetchall()
    if rows:
        columns = [description[0] for description in c.description]
        print("\nColumns:", ", ".join(columns))
        for row in rows:
            print("\n--- Evaluation ---")
            for col, val in zip(columns, row):
                print(f"{col}: {val}")
    else:
        print("Geen evaluaties gevonden in evaluations table")

    # Print approved_questions table
    print("\n=== APPROVED QUESTIONS TABLE ===")
    c.execute("SELECT * FROM approved_questions")
    rows = c.fetchall()
    if rows:
        columns = [description[0] for description in c.description]
        print("\nColumns:", ", ".join(columns))
        for row in rows:
            print("\n--- Approved Question ---")
            for col, val in zip(columns, row):
                print(f"{col}: {val}")
    else:
        print("Geen goedgekeurde vragen gevonden in approved_questions table")

    # Print question_usage table
    print("\n=== QUESTION USAGE TABLE ===")
    c.execute("SELECT * FROM question_usage")
    rows = c.fetchall()
    if rows:
        columns = [description[0] for description in c.description]
        print("\nColumns:", ", ".join(columns))
        for row in rows:
            print("\n--- Question Usage ---")
            for col, val in zip(columns, row):
                print(f"{col}: {val}")
    else:
        print("Geen gebruik gevonden in question_usage table")

    # Print process_logs table
    print("\n=== PROCESS LOGS TABLE ===")
    c.execute("SELECT * FROM process_logs")
    rows = c.fetchall()
    if rows:
        columns = [description[0] for description in c.description]
        print("\nColumns:", ", ".join(columns))
        for row in rows:
            print("\n--- Process Log ---")
            for col, val in zip(columns, row):
                print(f"{col}: {val}")
    else:
        print("Geen logs gevonden in process_logs table")

    conn.close()

if __name__ == "__main__":
    print_database_contents() 