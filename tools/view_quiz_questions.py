import sqlite3

DB_PATH = "/Users/pattynooijen/Documents/VisualStudioCode/daily_dose_quiz/data/QuizQuestions.db"

def show_all_tables():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Haal alle tabellen op
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in c.fetchall()]
    if not tables:
        print("Geen tabellen gevonden in de database.")
        conn.close()
        return

    for table in tables:
        print(f"\n{'='*10} Tabel: {table} {'='*10}")
        # Haal kolomnamen op in de juiste volgorde
        c.execute(f"PRAGMA table_info({table})")
        columns = [col[1] for col in c.fetchall()]
        # Haal alle rijen op
        c.execute(f"SELECT * FROM {table}")
        rows = c.fetchall()
        if not rows:
            print("Geen rijen gevonden.\n")
            continue
        for row in rows:
            for col, val in zip(columns, row):
                print(f"{col}: {val}")
            print()  # extra enter tussen rijen
    conn.close()

if __name__ == "__main__":
    show_all_tables()
