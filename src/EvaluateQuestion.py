from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from typing import Dict, Any, Tuple
from OutputModels import Response, Evaluation
import json

#nog niet in gebruik, dit is een voorbeeld van de opzet.
#AI gegenereerd, functies nog beoordelen en aanpassen.


class QuestionEvaluator:
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=0.2
        )
        self._setup_prompts()

    def _setup_prompts()-> None:
        """Setup the evaluation prompts."""
        self.human_evaluation_prompt = """
        Evalueer deze quizvraag en geef feedback:
        
        VRAAG:
        {question}
        
        FEEDBACK:
        {feedback}
        
        Wil je:
        1. Deze vraag accepteren
        2. Deze vraag aanpassen
        3. Een nieuwe vraag genereren
        
        Kies een optie (1/2/3): 
        """

        self.ai_adjustment_prompt = """
        Pas deze quizvraag aan op basis van de gegeven feedback.
        
        ORIGINELE VRAAG:
        Introductie: {introductie}
        Vraag: {vraag}
        Antwoordopties:
        {antwoordopties}
        Antwoord: {antwoord}
        Uitleg: {uitleg}
        
        FEEDBACK:
        {feedback}
        
        Pas de vraag aan en behoud daarbij:
        - De medicatie en kenniscategorie
        - De moeilijkheidsgraad
        - De praktijkgerichtheid
        
        Geef alleen de aangepaste vraag terug in exact hetzelfde format.
        """

    def evaluate_question(self, question: Response, medicine_info: str) -> Tuple[str, str]:
        """
        Present the question to a human evaluator and get their feedback.
        
        Args:
            question (Response): The question to evaluate
            medicine_info (str): The original medicine information used
            
        Returns:
            Tuple[str, str]: The feedback and choice (1, 2, or 3)
        """
        # Show question to human evaluator
        print("\nGegenereerde vraag:")
        print(f"Introductie: {question.final_resolution.introductie}")
        print(f"Vraag: {question.final_resolution.vraag}")
        print("\nAntwoordopties:")
        for i, optie in enumerate(question.final_resolution.antwoordopties, 1):
            print(f"{chr(64+i)}) {optie}")
        print(f"\nAntwoord: {question.final_resolution.antwoord}")
        print(f"Uitleg: {question.final_resolution.uitleg}")
        
        # Get human feedback
        feedback = input("\nGeef je feedback op deze vraag: ")
        choice = input("\nWil je:\n1. Deze vraag accepteren\n2. Deze vraag aanpassen\n3. Een nieuwe vraag genereren\n\nKies een optie (1/2/3): ")
        
        return feedback, choice

    def adjust_question(self, question: Response, feedback: str, medicine_info: str) -> Response:
        """
        Adjust the question based on human feedback using the AI.
        
        Args:
            question (Response): The original question
            feedback (str): Human feedback on the question
            medicine_info (str): The original medicine information
            
        Returns:
            Response: The adjusted question
        """
        # Format the antwoordopties for the prompt
        antwoordopties = "\n".join([f"{chr(65+i)}) {opt}" for i, opt in enumerate(question.final_resolution.antwoordopties)])
        
        # Create the adjustment prompt
        prompt = PromptTemplate(
            input_variables=["introductie", "vraag", "antwoordopties", "antwoord", "uitleg", "feedback"],
            template=self.ai_adjustment_prompt
        )
        
        # Get AI response
        response = self.llm.invoke(prompt.format(
            introductie=question.final_resolution.introductie,
            vraag=question.final_resolution.vraag,
            antwoordopties=antwoordopties,
            antwoord=question.final_resolution.antwoord,
            uitleg=question.final_resolution.uitleg,
            feedback=feedback
        ))
        
        # Parse the response back into a Response object
        # Note: This assumes the AI returns the response in the correct format
        try:
            adjusted = json.loads(response.content)
            return Response(
                steps=question.steps,  # Keep the original steps
                final_resolution={
                    "introductie": adjusted["introductie"],
                    "vraag": adjusted["vraag"],
                    "antwoordopties": adjusted["antwoordopties"],
                    "antwoord": adjusted["antwoord"],
                    "uitleg": adjusted["uitleg"],
                    "verificatie": question.final_resolution.verificatie  # Keep the original verification
                }
            )
        except Exception as e:
            print(f"Error parsing adjusted question: {e}")
            return question  # Return original question if parsing fails

def main():
    # Test the evaluator
    evaluator = QuestionEvaluator()
    
    # Create a dummy question for testing
    test_question = Response(
        steps=[],
        final_resolution={
            "introductie": "Een test introductie",
            "vraag": "Een test vraag",
            "antwoordopties": ["A", "B", "C", "D"],
            "antwoord": "A",
            "uitleg": "Test uitleg",
            "verificatie": None
        }
    )
    
    feedback, choice = evaluator.evaluate_question(test_question, "Test medicine info")
    print(f"\nFeedback: {feedback}")
    print(f"Choice: {choice}")

if __name__ == "__main__":
    main() 