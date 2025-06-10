import sqlite3
import json

DB_PATH = "quiz_questions_tracing.db"

def get_all_quiz_questions():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, medicine, category, llm_raw_output, timestamp FROM quiz_questions')
    rows = c.fetchall()
    conn.close()
    return rows

if __name__ == "__main__":
    questions = get_all_quiz_questions()
    for row in questions:
        timestamp, medicine, category, llm_raw_output = row[4], row[1], row[2], row[3]
        try:
            data = json.loads(llm_raw_output)
            # Als data een string is, probeer het opnieuw te laden
            if isinstance(data, str):
                data = json.loads(data)
            # Probeer de nested structuur te pakken (zoals bij response.final_resolution)
            final = data.get("final_resolution", data) if isinstance(data, dict) else {}
            print(f"[{timestamp}] {medicine} ({category})")
            print(f"Introductie: {final.get('introductie', '')}")
            print(f"Vraag: {final.get('vraag', '')}")
            print("Antwoordopties:")
            for idx, option in enumerate(final.get('antwoordopties', []), start=1):
                print(f"{chr(64 + idx)}) {option}")
            print(f"Juiste antwoord: {final.get('antwoord', '')}")
            print(f"Uitleg: {final.get('uitleg', '')}")
            print("-" * 40)
        except Exception as e:
            print(f"[{timestamp}] {medicine} ({category})")
            print(f"Fout bij parsen van vraag {row[0]}: {e}")
            print("-" * 40)