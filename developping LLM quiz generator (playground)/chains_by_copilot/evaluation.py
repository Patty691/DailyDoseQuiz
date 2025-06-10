from typing import Dict, Any, List, Optional
from datetime import datetime
import sqlite3
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from .config import get_config

class QuestionEvaluation(BaseModel):
    """Model voor vraag evaluatie."""
    question_id: str = Field(description="Unieke identifier voor de vraag")
    automated_score: float = Field(description="Automatische evaluatie score (0-1)")
    automated_feedback: List[str] = Field(description="Lijst van automatische feedback punten")
    needs_human_review: bool = Field(description="Of menselijke review nodig is")
    review_priority: str = Field(description="Review prioriteit (low, medium, high)")
    review_focus: List[str] = Field(description="Aspecten die extra aandacht nodig hebben")

class HumanReview(BaseModel):
    """Model voor menselijke review."""
    question_id: str = Field(description="Unieke identifier voor de vraag")
    reviewer: str = Field(description="Naam van de reviewer")
    approved: bool = Field(description="Of de vraag is goedgekeurd")
    score: float = Field(description="Review score (0-1)")
    feedback: List[str] = Field(description="Feedback punten")
    suggested_changes: Dict[str, Any] = Field(description="Voorgestelde wijzigingen")
    review_date: datetime = Field(description="Datum van de review")

class EvaluationChain:
    """Chain voor het evalueren van quiz vragen met human-in-the-loop."""
    
    def __init__(self, db_path: str = "data/quiz.db"):
        """
        Initialiseer de evaluation chain.
        
        Args:
            db_path: Pad naar de SQLite database
        """
        self.db_path = db_path
        model_config = get_config("model")
        
        # Maak database tabellen aan
        self._init_database()
        
        # Configureer de evaluatie prompt
        self.eval_prompt = ChatPromptTemplate.from_messages([
            ("system", """Je bent een expert in farmacologie en medische educatie.
Evalueer de gegeven quiz vraag op basis van de volgende criteria:

1. Inhoudelijke accuraatheid (30%):
   - Is de informatie correct?
   - Is het juiste antwoord ondubbelzinnig juist?
   - Zijn de afleiders plausibel maar duidelijk onjuist?

2. Educatieve waarde (30%):
   - Test de vraag begrip in plaats van pure feitenkennis?
   - Is het niveau passend voor de doelgroep?
   - Draagt de uitleg bij aan het leerproces?

3. Klinische relevantie (20%):
   - Is de context realistisch?
   - Is de vraag relevant voor de praktijk?
   - Helpt het bij het maken van klinische beslissingen?

4. Technische kwaliteit (20%):
   - Is de vraag duidelijk geformuleerd?
   - Zijn er geen taalfouten?
   - Is de formatting correct?

Geef een score tussen 0 en 1 voor elk criterium en bepaal of menselijke review nodig is.
Als menselijke review nodig is, specificeer welke aspecten extra aandacht nodig hebben."""),
            ("human", """Evalueer de volgende vraag:

Type: {question_type}
Moeilijkheidsgraad: {difficulty}
Onderwerp: {topic}
Specifiek aspect: {subtopic}

Vraag:
{question_text}

{options_text}

Juiste antwoord: {correct_answer}
Uitleg: {explanation}""")
        ])
        
        # Configureer de LLM
        self.llm = ChatOpenAI(
            model=model_config["model"],
            temperature=0.2  # Lager voor meer consistente evaluaties
        )
        
        # Configureer de output parser
        self.parser = JsonOutputParser(pydantic_object=QuestionEvaluation)
        
        # Bouw de chain
        self.chain = self.eval_prompt | self.llm | self.parser
        
    def _init_database(self):
        """Initialiseer de database tabellen."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Maak tabellen aan
        c.execute("""
        CREATE TABLE IF NOT EXISTS question_evaluations (
            question_id TEXT PRIMARY KEY,
            automated_score REAL,
            automated_feedback TEXT,
            needs_human_review INTEGER,
            review_priority TEXT,
            review_focus TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        c.execute("""
        CREATE TABLE IF NOT EXISTS human_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id TEXT,
            reviewer TEXT,
            approved INTEGER,
            score REAL,
            feedback TEXT,
            suggested_changes TEXT,
            review_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (question_id) REFERENCES question_evaluations(question_id)
        )
        """)
        
        conn.commit()
        conn.close()
        
    def _format_options_text(self, options: List[str]) -> str:
        """Format de antwoord opties voor de prompt."""
        if not options:
            return ""
            
        return "Opties:\n" + "\n".join(f"- {opt}" for opt in options)
        
    def _store_evaluation(self, question_id: str, evaluation: QuestionEvaluation):
        """Sla de evaluatie op in de database."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
        INSERT OR REPLACE INTO question_evaluations
        (question_id, automated_score, automated_feedback, needs_human_review,
         review_priority, review_focus)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            question_id,
            evaluation.automated_score,
            str(evaluation.automated_feedback),
            1 if evaluation.needs_human_review else 0,
            evaluation.review_priority,
            str(evaluation.review_focus)
        ))
        
        conn.commit()
        conn.close()
        
    def store_human_review(
        self,
        question_id: str,
        reviewer: str,
        approved: bool,
        score: float,
        feedback: List[str],
        suggested_changes: Dict[str, Any]
    ):
        """
        Sla een menselijke review op.
        
        Args:
            question_id: ID van de vraag
            reviewer: Naam van de reviewer
            approved: Of de vraag is goedgekeurd
            score: Review score
            feedback: Feedback punten
            suggested_changes: Voorgestelde wijzigingen
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
        INSERT INTO human_reviews
        (question_id, reviewer, approved, score, feedback, suggested_changes)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            question_id,
            reviewer,
            1 if approved else 0,
            score,
            str(feedback),
            str(suggested_changes)
        ))
        
        conn.commit()
        conn.close()
        
    def get_pending_reviews(
        self,
        priority: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Haal vragen op die menselijke review nodig hebben.
        
        Args:
            priority: Filter op review prioriteit
            limit: Maximum aantal resultaten
            
        Returns:
            Lijst van vragen die review nodig hebben
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        query = """
        SELECT e.question_id, e.automated_score, e.automated_feedback,
               e.review_priority, e.review_focus, e.created_at
        FROM question_evaluations e
        LEFT JOIN human_reviews r ON e.question_id = r.question_id
        WHERE e.needs_human_review = 1 AND r.id IS NULL
        """
        
        if priority:
            query += f" AND e.review_priority = '{priority}'"
            
        query += f" ORDER BY e.created_at DESC LIMIT {limit}"
        
        results = []
        for row in c.execute(query):
            results.append({
                "question_id": row[0],
                "automated_score": row[1],
                "automated_feedback": eval(row[2]),
                "review_priority": row[3],
                "review_focus": eval(row[4]),
                "created_at": row[5]
            })
            
        conn.close()
        return results
        
    def invoke(
        self,
        question: Dict[str, Any],
        question_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evalueer een quiz vraag.
        
        Args:
            question: De quiz vraag om te evalueren
            question_id: Optionele vraag ID
            
        Returns:
            Dict met evaluatie resultaten
        """
        # Genereer vraag ID als niet gegeven
        if not question_id:
            question_id = f"q_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
        # Bereid input voor
        chain_input = {
            "question_type": question["question_type"],
            "difficulty": question["difficulty"],
            "topic": question["topic"],
            "subtopic": question["subtopic"],
            "question_text": question["question_text"],
            "options_text": self._format_options_text(question["options"]),
            "correct_answer": question["correct_answer"],
            "explanation": question["explanation"]
        }
        
        try:
            # Voer evaluatie uit
            evaluation = self.chain.invoke(chain_input)
            
            # Sla resultaten op
            self._store_evaluation(question_id, evaluation)
            
            return {
                "question_id": question_id,
                "evaluation": evaluation.dict()
            }
            
        except Exception as e:
            raise RuntimeError(f"Fout bij evalueren vraag: {str(e)}")

if __name__ == "__main__":
    # Test data
    test_question = {
        "question_type": "multiple_choice",
        "question_text": "Bij welke patiënt is metoprolol gecontra-indiceerd?",
        "correct_answer": "Een patiënt met een 2e graads AV-blok",
        "explanation": "Metoprolol is gecontra-indiceerd bij 2e en 3e graads AV-blok omdat het de AV-geleiding verder kan vertragen.",
        "difficulty": "medium",
        "options": [
            "Een patiënt met hypertensie",
            "Een patiënt met een 2e graads AV-blok",
            "Een patiënt met angina pectoris",
            "Een patiënt met hartfalen"
        ],
        "topic": "Contra-indicaties",
        "subtopic": "Cardiale contra-indicaties"
    }
    
    # Test de chain
    chain = EvaluationChain()
    result = chain.invoke(test_question)
    
    # Print resultaten
    print("\nEvaluatie resultaten:")
    print("=" * 70)
    print(f"Vraag ID: {result['question_id']}")
    print(f"\nAutomatische score: {result['evaluation']['automated_score']:.2f}")
    print("\nFeedback punten:")
    for point in result['evaluation']['automated_feedback']:
        print(f"- {point}")
    print(f"\nMenselijke review nodig: {result['evaluation']['needs_human_review']}")
    if result['evaluation']['needs_human_review']:
        print(f"Prioriteit: {result['evaluation']['review_priority']}")
        print("\nFocus punten:")
        for point in result['evaluation']['review_focus']:
            print(f"- {point}")
    print("-" * 70) 