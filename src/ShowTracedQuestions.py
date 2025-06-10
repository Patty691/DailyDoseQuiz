import sqlite3
import json

DB_PATH = "quiz_questions_tracing.db"

def get_all_quiz_questions():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, medicine, category, question, correct_answer, wrong_answers, timestamp FROM quiz_questions')
    rows = c.fetchall()
    conn.close()
    return rows

if __name__ == "__main__":
    questions = get_all_quiz_questions()
    for row in questions:
        print(f"[{row[6]}] {row[1]} ({row[2]})")
        print(f"Vraag: {row[3]}")
        print(f"Juiste antwoord: {row[4]}")
        print(f"Foute antwoorden: {json.loads(row[5])}") 