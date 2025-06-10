from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from .config import get_config

class QuizQuestion(BaseModel):
    """Model voor een quiz vraag."""
    question_type: str = Field(description="Type vraag (multiple_choice of open)")
    question_text: str = Field(description="De vraag tekst")
    correct_answer: str = Field(description="Het juiste antwoord")
    explanation: str = Field(description="Uitleg waarom dit het juiste antwoord is")
    difficulty: str = Field(description="Moeilijkheidsgraad (easy, medium, hard)")
    options: List[str] = Field(
        default=[],
        description="Antwoord opties voor multiple choice vragen"
    )
    topic: str = Field(description="Het onderwerp van de vraag")
    subtopic: str = Field(description="Het specifieke aspect van het onderwerp")

class QuizQuestionBatch(BaseModel):
    """Model voor een set quiz vragen."""
    questions: List[QuizQuestion] = Field(description="Lijst van gegenereerde vragen")

class QuestionGenerationChain:
    """Chain voor het genereren van quiz vragen."""
    
    def __init__(self):
        """Initialiseer de question generation chain."""
        model_config = get_config("model")
        chain_config = get_config("chain")["question_generation"]
        
        # Configureer de prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """Je bent een expert in farmacologie en medische educatie. 
Genereer quiz vragen over de gegeven medicatie die geschikt zijn voor geneeskunde studenten.

Richtlijnen voor het maken van vragen:
1. Maak vragen die begrip testen, niet alleen feitenkennis
2. Gebruik klinisch relevante scenario's waar mogelijk
3. Bij multiple choice vragen:
   - Maak 4 plausibele opties
   - Vermijd 'alle bovenstaande' of 'geen van bovenstaande'
   - Zorg dat afleiders geloofwaardig zijn
4. Varieer in moeilijkheidsgraad en onderwerpen
5. Focus op:
   - Werkingsmechanisme
   - Indicaties en contra-indicaties
   - Belangrijke bijwerkingen
   - Interacties
   - Praktische aspecten van voorschrijven

Output moet in het Nederlands zijn."""),
            ("human", """Genereer {num_questions} {question_type} vragen over de volgende medicatie:

Cluster: {cluster_name}
Geneesmiddelen:
{medicines_info}

Moeilijkheidsgraad: {difficulty}""")
        ])
        
        # Configureer de LLM
        self.llm = ChatOpenAI(
            model=model_config["model"],
            temperature=model_config["temperature"]
        )
        
        # Configureer de output parser
        self.parser = JsonOutputParser(pydantic_object=QuizQuestionBatch)
        
        # Bouw de chain
        self.chain = self.prompt | self.llm | self.parser
        
    def _format_medicines_info(self, medicines: List[Dict[str, Any]]) -> str:
        """Format medicatie informatie voor de prompt."""
        info = []
        for med in medicines:
            med_info = f"- {med['naam']}"
            if med.get('merknaam'):
                med_info += f" ({med['merknaam']})"
            info.append(med_info)
        return "\n".join(info)
        
    def invoke(
        self,
        cluster_name: str,
        medicines: List[Dict[str, Any]],
        num_questions: int = None,
        question_type: str = None,
        difficulty: str = None
    ) -> Dict[str, Any]:
        """
        Genereer quiz vragen voor de gegeven medicatie.
        
        Args:
            cluster_name: Naam van het medicatie cluster
            medicines: Lijst van geselecteerde geneesmiddelen
            num_questions: Aantal te genereren vragen
            question_type: Type vragen (multiple_choice of open)
            difficulty: Moeilijkheidsgraad
            
        Returns:
            Dict met gegenereerde vragen
        """
        config = get_config("chain")["question_generation"]
        
        # Gebruik default waardes uit config als geen specifieke waardes gegeven
        num_questions = num_questions or config["num_questions"]
        question_type = question_type or config["question_types"][0]
        difficulty = difficulty or config["difficulty"]
        
        # Bereid input voor
        chain_input = {
            "cluster_name": cluster_name,
            "medicines_info": self._format_medicines_info(medicines),
            "num_questions": num_questions,
            "question_type": question_type,
            "difficulty": difficulty
        }
        
        try:
            # Genereer vragen
            result = self.chain.invoke(chain_input)
            
            return {
                "questions": [question.dict() for question in result.questions]
            }
            
        except Exception as e:
            raise RuntimeError(f"Fout bij genereren vragen: {str(e)}")

if __name__ == "__main__":
    # Test data
    test_cluster = "Beta-blokkers"
    test_medicines = [
        {
            "naam": "Metoprolol",
            "merknaam": "Selokeen",
            "atc7": "C07AB02",
            "gewicht": 1.0
        }
    ]
    
    # Test de chain
    chain = QuestionGenerationChain()
    result = chain.invoke(
        cluster_name=test_cluster,
        medicines=test_medicines,
        num_questions=2,
        question_type="multiple_choice",
        difficulty="medium"
    )
    
    # Print resultaten
    print("\nGegenereerde vragen:")
    print("=" * 70)
    
    for i, question in enumerate(result["questions"], 1):
        print(f"\nVraag {i}:")
        print(f"Type: {question['question_type']}")
        print(f"Moeilijkheid: {question['difficulty']}")
        print(f"\n{question['question_text']}")
        
        if question["options"]:
            print("\nOpties:")
            for option in question["options"]:
                print(f"- {option}")
                
        print(f"\nJuiste antwoord: {question['correct_answer']}")
        print(f"Uitleg: {question['explanation']}")
        print(f"\nOnderwerp: {question['topic']}")
        print(f"Specifiek aspect: {question['subtopic']}")
        print("-" * 70) 