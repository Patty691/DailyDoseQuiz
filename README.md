# Daily Dose Quiz

Dit project genereert quizvragen over medicatie op basis van actuele medicatie-informatie, met behulp van LLMs.
Het doel is om deze quizvragen te gebruiken in een kennisapp voor apothekersassistenten, waarin ze dagelijks een vraag kunnen beantwoorden om hun kennis te toetsen en verbeteren. 

## Structuur

```
daily_dose_quiz/
│
├── src/
│   ├── BuildQuestionDatabase.py
│   ├── EvaluateQuestion.py
│   ├── GenerateMedicationDatabase.py
│   ├── GenerateQuestion.py
│   ├── GetMedicineInfo.py
│   ├── OutputModels.py
│   ├── PromptQuizQuestion.py
│   ├── Schema.sql
│   ├── SelectMedication.py
│   └── ...
├── data/
│   └── QuizQuestions.db
│   └── MedicationClustersDatabase.json
│   └── MedicineInformation.json
│   └── ...
└── README.md
```

## Belangrijkste scripts

### `src/BuildQuestionDatabase.py`
- **Doel:** Bouwt en vult de database met quizvragen en medicatie-informatie.
- **Functionaliteit:**  
  - Selecteert clusters en medicijnen uit 'MedicationDatabase.json'.
  - Haalt informatie op via scraping of API.
  - Genereert quizvragen met een LLM.
  - Slaat alles op in de database.
  - Logt het proces in `process_logs`.

### `src/EvaluateQuestion.py`
- **Doel:** Evalueert de kwaliteit van gegenereerde quizvragen.
- **Functionaliteit:**
  - Controleert de moeilijkheidsgraad
  - Valideert de juistheid van antwoorden
  - Beoordeelt de duidelijkheid van vragen

### `src/GenerateMedicationDatabase.py`
- **Doel:** Genereert de initiële medicatie database.
- **Functionaliteit:**
  - Verzamelt medicatie informatie
  - Creëert clusters van gerelateerde medicijnen
  - Genereert MedicationClustersDatabase.json

### `src/GenerateQuestion.py`
- **Doel:** Genereert een quizvraag voor een medicijn.
- **Functionaliteit:**  
  - Bepaalt een willekeurige kenniscategorie.
  - Extraheert relevante informatie.
  - Genereert een quizvraag met het gekozen model.

### `src/GetMedicineInfo.py`
- **Doel:** Haalt medicatie-informatie op (scraping of API).
- **Functionaliteit:**  
  - Zoekt op naam, cluster en merk.
  - Retourneert gestructureerde info inclusief bron-url en timestamp.

### `src/OutputModels.py`
- **Doel:** Definieert de datamodellen voor LLM-output (Response, Extraction).

### `src/PromptQuizQuestion.py`
- **Doel:** Bevat alle prompts voor extractie en quizgeneratie.

### `src/SelectMedication.py`
- **Doel:** Selecteert clusters en medicijnen op basis van wegingen.

### `tools/PrintDatabase.py`
- **Doel:** Bekijk de inhoud van alle tabellen in de database.


## Configuratie

1. **.env bestand:**  
   OpenAI API key in `.env`:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

2. **Database initialisatie:**  
   De database wordt automatisch aangemaakt via `src/Schema.sql`

## Gebruik

- **Quizvragen genereren en database vullen:**
  ```
  python3 src/BuildQuestionDatabase.py
  ```


## Externe bronnen

- Gebruikersaantallen: https://www.gipdatabank.nl/
- Medicatie-informatie: https://www.apotheek.nl/

## Overig

- **LangChain tracing:** Zet `LANGCHAIN_TRACING_V2=true` in je omgeving voor tracing.
- **Debugging:** Zet `debug_mode=True` in de scripts voor uitgebreide output.

---

**Vragen of problemen?**  
Open een issue of neem contact op met de ontwikkelaar.
