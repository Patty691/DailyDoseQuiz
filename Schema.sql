-- Database schema voor quizgenerator
-- Locatie: /Users/pattynooijen/Documents/VisualStudioCode/daily_dose_quiz/schema.sql

-- Stap 1: Information (startpunt, hier wordt de UUID gegenereerd)
CREATE TABLE information (
   id INTEGER PRIMARY KEY,
   quiz_question_uuid TEXT UNIQUE,
   atc7_code TEXT,
   kenniscategorie TEXT,
   bron_url TEXT,
   timestamp_opgeslagen TEXT,
   geëxtraheerde_informatie TEXT,
   llm_raw_output TEXT,
   timestamp_gegenereerd TEXT
);

-- Stap 2: Gegenereerde quizvraag
CREATE TABLE generated_quiz_questions (
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
CREATE TABLE evaluations (
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
CREATE TABLE approved_questions (
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
CREATE TABLE question_usage (
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