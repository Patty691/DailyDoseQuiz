from typing import Dict, Any, Optional, List
from datetime import datetime
from langchain_core.callbacks import CallbackManagerForChainRun
from langchain_core.runnables import RunnablePassthrough
from .medicine_selection import MedicineSelectionChain
from .question_generation import QuestionGenerationChain
from .evaluation import EvaluationChain
from .config import get_config

class QuizGenerationChain:
    """Hoofdchain voor het genereren van quiz vragen."""
    
    def __init__(self):
        """Initialiseer de quiz generation chain met alle componenten."""
        config = get_config("chain")
        
        # Initialiseer componenten
        self.medicine_selection = MedicineSelectionChain()
        self.question_generation = QuestionGenerationChain()
        self.evaluation = EvaluationChain()
        
        # Bouw de hoofdchain
        self.chain = (
            RunnablePassthrough.assign(
                selected_medicine=self._select_medicine,
                generated_questions=self._generate_questions,
                evaluations=self._evaluate_questions
            )
        )
        
    def _select_medicine(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Selecteer medicatie voor de quiz vraag.
        
        Args:
            inputs: Input parameters
            
        Returns:
            Dict met geselecteerde medicatie
        """
        config = get_config("chain")["medicine_selection"]
        
        # Haal optionele parameters uit de inputs
        num_clusters = inputs.get("num_clusters", config["num_clusters"])
        num_medicines = inputs.get("num_medicines", config["num_medicines"])
        atc_cluster = inputs.get("atc_cluster")
        
        return self.medicine_selection.invoke(
            atc_cluster=atc_cluster,
            num_clusters=num_clusters,
            num_medicines=num_medicines
        )
        
    def _generate_questions(
        self,
        selected_medicine: Dict[str, Any],
        inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Genereer vragen voor de geselecteerde medicatie.
        
        Args:
            selected_medicine: Geselecteerde medicatie informatie
            inputs: Input parameters
            
        Returns:
            Dict met gegenereerde vragen
        """
        config = get_config("chain")["question_generation"]
        
        # Haal optionele parameters uit de inputs
        num_questions = inputs.get("num_questions", config["num_questions"])
        question_type = inputs.get("question_type", config["question_types"][0])
        difficulty = inputs.get("difficulty", config["difficulty"])
        
        all_questions = []
        
        # Genereer vragen voor elk cluster
        for cluster in selected_medicine["selected_clusters"]:
            cluster_questions = self.question_generation.invoke(
                cluster_name=cluster["naam"],
                medicines=cluster["geneesmiddelen"],
                num_questions=num_questions,
                question_type=question_type,
                difficulty=difficulty
            )
            all_questions.extend(cluster_questions["questions"])
            
        return {"questions": all_questions}
        
    def _evaluate_questions(
        self,
        generated_questions: Dict[str, Any],
        inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evalueer de gegenereerde vragen.
        
        Args:
            generated_questions: De gegenereerde vragen
            inputs: Input parameters
            
        Returns:
            Dict met evaluatie resultaten
        """
        session_id = f"s_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        evaluations = []
        
        for i, question in enumerate(generated_questions["questions"]):
            question_id = f"{session_id}_q{i+1}"
            evaluation = self.evaluation.invoke(question, question_id)
            evaluations.append(evaluation)
            
        return {
            "session_id": session_id,
            "evaluations": evaluations
        }
        
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
        return self.evaluation.get_pending_reviews(priority, limit)
        
    def submit_human_review(
        self,
        question_id: str,
        reviewer: str,
        approved: bool,
        score: float,
        feedback: List[str],
        suggested_changes: Dict[str, Any]
    ):
        """
        Dien een menselijke review in.
        
        Args:
            question_id: ID van de vraag
            reviewer: Naam van de reviewer
            approved: Of de vraag is goedgekeurd
            score: Review score
            feedback: Feedback punten
            suggested_changes: Voorgestelde wijzigingen
        """
        self.evaluation.store_human_review(
            question_id=question_id,
            reviewer=reviewer,
            approved=approved,
            score=score,
            feedback=feedback,
            suggested_changes=suggested_changes
        )
        
    def invoke(
        self,
        atc_cluster: Optional[str] = None,
        num_clusters: int = 1,
        num_medicines: int = 1,
        num_questions: int = None,
        question_type: str = None,
        difficulty: str = None,
        callbacks: Optional[CallbackManagerForChainRun] = None
    ) -> Dict[str, Any]:
        """
        Genereer quiz vragen.
        
        Args:
            atc_cluster: Optioneel specifiek ATC cluster
            num_clusters: Aantal te selecteren clusters
            num_medicines: Aantal geneesmiddelen per cluster
            num_questions: Aantal vragen per cluster
            question_type: Type vragen (multiple_choice of open)
            difficulty: Moeilijkheidsgraad
            callbacks: Optionele callbacks voor monitoring
            
        Returns:
            Dict met gegenereerde quiz vragen en evaluaties
        """
        inputs = {
            "atc_cluster": atc_cluster,
            "num_clusters": num_clusters,
            "num_medicines": num_medicines,
            "num_questions": num_questions,
            "question_type": question_type,
            "difficulty": difficulty
        }
        
        try:
            return self.chain.invoke(inputs, config={"callbacks": callbacks})
        except Exception as e:
            raise RuntimeError(f"Fout bij genereren quiz: {str(e)}")
            
if __name__ == "__main__":
    # Test de chain
    chain = QuizGenerationChain()
    result = chain.invoke(
        num_clusters=1,
        num_medicines=2,
        num_questions=2,
        question_type="multiple_choice",
        difficulty="medium"
    )
    
    # Print resultaten
    print("\nGegenereerde quiz:")
    print("=" * 70)
    
    # Print geselecteerde medicatie
    for cluster in result["selected_medicine"]["selected_clusters"]:
        print(f"\nCluster: {cluster['naam']} ({cluster['atc5_code']})")
        print(f"Cluster gewicht: {cluster['gewicht']:.1f}")
        
        for med in cluster["geneesmiddelen"]:
            print(f"\n  Geneesmiddel: {med['naam']} ({med['atc7']})")
            print(f"  Gewicht: {med['gewicht']:.1f}")
            if med['merknaam']:
                print(f"  Merknaam: {med['merknaam']}")
    
    # Print gegenereerde vragen en evaluaties
    print("\nGegenereerde vragen en evaluaties:")
    print("=" * 70)
    
    for i, (question, evaluation) in enumerate(zip(
        result["generated_questions"]["questions"],
        result["evaluations"]["evaluations"]
    ), 1):
        print(f"\nVraag {i}:")
        print(f"ID: {evaluation['question_id']}")
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
        
        print("\nEvaluatie:")
        print(f"Score: {evaluation['evaluation']['automated_score']:.2f}")
        print("\nFeedback:")
        for point in evaluation['evaluation']['automated_feedback']:
            print(f"- {point}")
            
        if evaluation['evaluation']['needs_human_review']:
            print(f"\nMenselijke review nodig (Prioriteit: {evaluation['evaluation']['review_priority']})")
            print("Focus punten:")
            for point in evaluation['evaluation']['review_focus']:
                print(f"- {point}")
                
        print("-" * 70) 