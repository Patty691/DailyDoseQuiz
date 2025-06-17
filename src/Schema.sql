-- Database schema voor quizgenerator
-- Locatie: /Users/pattynooijen/Documents/VisualStudioCode/daily_dose_quiz/schema.sql

-- Stap 1: Geselecteerde medicatie
CREATE TABLE IF NOT EXISTS selected_medications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE,                  -- Unieke identifier voor de selectie
    atc5_code TEXT NOT NULL,           -- ATC5 code van het cluster
    cluster_name TEXT NOT NULL,        -- Naam van het cluster
    cluster_weight REAL,               -- Gewicht van het cluster
    atc7_code TEXT NOT NULL,           -- ATC7 code van het medicijn
    medicine_name TEXT NOT NULL,       -- Naam van het medicijn
    brand_name TEXT,                   -- Merknaam van het medicijn
    medicine_weight REAL,              -- Gewicht van het medicijn
    selection_date DATETIME DEFAULT (datetime('now', 'localtime'))  -- Datum en tijd van selectie in lokaal formaat
); 





-- Stap 2: Geselecteerde informatie
CREATE TABLE IF NOT EXISTS medicine_information (
   id INTEGER PRIMARY KEY,
   quiz_question_uuid TEXT UNIQUE,           -- Koppeling met selected_medications
   bron_url TEXT,                           -- URL van apotheek.nl die is opgeslagen
   timestamp_opgeslagen TEXT,               -- Wanneer de info is opgeslagen
   kenniscategorie TEXT,                    -- Categorie van de vraag (van LLM)
   relevante_informatie TEXT,               -- Alleen de door LLM geëxtraheerde info
   llm_raw_output TEXT,                     -- Ruwe LLM output voor debugging
   timestamp_gegenereerd TEXT,              -- Wanneer de vraag is gegenereerd
   FOREIGN KEY(quiz_question_uuid) REFERENCES selected_medications(uuid)
);

-- Stap 3: Gegenereerde quizvraag
CREATE TABLE IF NOT EXISTS generated_quiz_questions (
   id INTEGER PRIMARY KEY,
   quiz_question_uuid TEXT,
   information_id INTEGER,
   introductie TEXT,
   vraag TEXT,
   antwoordoptie_1 TEXT,
   antwoordoptie_2 TEXT,
   antwoordoptie_3 TEXT,
   antwoordoptie_4 TEXT,
   juiste_antwoord TEXT,
   uitleg TEXT,
   llm_raw_output TEXT,
   timestamp_gegenereerd TEXT,
   FOREIGN KEY(information_id) REFERENCES information(id),
   FOREIGN KEY(quiz_question_uuid) REFERENCES information(quiz_question_uuid)
);

-- Stap 3: Evaluatie
CREATE TABLE IF NOT EXISTS evaluations (
   id INTEGER PRIMARY KEY,
   quiz_question_uuid TEXT,
   quiz_question_id INTEGER,
   status TEXT,
   oordeel TEXT,
   aangepaste_introductie TEXT,
   aangepaste_vraag TEXT,
   aangepaste_antwoordoptie_1 TEXT,
   aangepaste_antwoordoptie_2 TEXT,
   aangepaste_antwoordoptie_3 TEXT,
   aangepaste_antwoordoptie_4 TEXT,
   aangepaste_juiste_antwoord TEXT,
   aangepaste_uitleg TEXT,
   timestamp TEXT,
   FOREIGN KEY(quiz_question_id) REFERENCES generated_quiz_questions(id),
   FOREIGN KEY(quiz_question_uuid) REFERENCES information(quiz_question_uuid)
);

-- Goedgekeurde quizvraag
CREATE TABLE IF NOT EXISTS approved_questions (
   id INTEGER PRIMARY KEY,
   quiz_question_uuid TEXT,
   quiz_question_id INTEGER,
   evaluation_id INTEGER,  
   introductie TEXT,
   vraag TEXT,
   antwoordoptie_1 TEXT,
   antwoordoptie_2 TEXT,
   antwoordoptie_3 TEXT,
   antwoordoptie_4 TEXT,
   juiste_antwoord TEXT,
   uitleg TEXT,
   timestamp_goedgekeurd TEXT,
   FOREIGN KEY(quiz_question_id) REFERENCES generated_quiz_questions(id),
   FOREIGN KEY(evaluation_id) REFERENCES evaluations(id),
   FOREIGN KEY(quiz_question_uuid) REFERENCES information(quiz_question_uuid)
);

-- Gebruik van de vraag
CREATE TABLE IF NOT EXISTS question_usage (
   id INTEGER PRIMARY KEY,
   quiz_question_uuid TEXT,
   approved_question_id INTEGER,
   timestamp_getoond TEXT,
   respons_aantal INTEGER,
   gegeven_antwoorden_1 INTEGER,
   gegeven_antwoorden_2 INTEGER,
   gegeven_antwoorden_3 INTEGER,
   gegeven_antwoorden_4 INTEGER,
   percentage_juist REAL,
   FOREIGN KEY(approved_question_id) REFERENCES approved_questions(id),
   FOREIGN KEY(quiz_question_uuid) REFERENCES information(quiz_question_uuid)
);

CREATE TABLE IF NOT EXISTS quiz_questions (
    id INTEGER PRIMARY KEY,
    medicine TEXT,
    category TEXT,
    question TEXT,
    correct_answer TEXT,
    wrong_answers TEXT,
    llm_raw_output TEXT,
    atc7 TEXT,
    brand TEXT,
    atc5 TEXT,
    cluster_name TEXT,
    timestamp TEXT
);

CREATE TABLE IF NOT EXISTS process_logs (
    id INTEGER PRIMARY KEY,
    event_type TEXT,
    medicine TEXT,
    category TEXT,
    message TEXT,
    timestamp TEXT
);