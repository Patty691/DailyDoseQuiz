from langchain_core.prompts import PromptTemplate
from langchain_core.chains import Chain
from langchain_openai import ChatOpenAI
from langchain_community.callbacks.manager import get_openai_callback
from typing import Dict, Any, List
from dotenv import load_dotenv
import os

from SelectMedication import select_medication
from GetMedicineInfo import get_medicine_info
from GenerateQuestion import generate_quiz_question
# Evaluation system temporarily disabled - will be added back later
# from EvaluateQuestion import QuestionEvaluator

class QuizGenerationPipeline:
    def __init__(self, model_name: str = "gpt-4o-mini", debug_mode: bool = True):
        # Load environment variables
        load_dotenv()
        
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=0.2,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        self.debug_mode = debug_mode
        # Evaluation system temporarily disabled
        # self.evaluator = QuestionEvaluator(model_name=model_name)
        self._setup_chains()

    def _setup_chains(self):
        # Medication Selection Chain
        # This chain selects a medication based on ATC clusters and weights
        self.medication_chain = select_medication

        # Medicine Info Chain
        # This chain fetches and processes medication information
        self.info_chain = get_medicine_info

        # Quiz Generation Chain
        # This chain generates the initial quiz question
        self.quiz_chain = generate_quiz_question
        
        # For now, we'll handle the chain sequence manually since SequentialChain is deprecated
        self.full_chain = self._create_chain_sequence

    def _create_chain_sequence(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Manual implementation of chain sequence to replace SequentialChain
        
        Args:
            inputs (Dict[str, Any]): Input variables including atc_cluster
            
        Returns:
            Dict[str, Any]: Combined output from all chains
        """
        try:
            # Step 1: Select medication
            medication_result = self.medication_chain(
                atc_cluster=inputs.get("atc_cluster"),
                num_clusters=1,
                num_medicines=1
            )
            
            if "error" in medication_result:
                raise ValueError(f"Medication selection failed: {medication_result['error']}")
            
            # Step 2: Get medicine info
            medicine_info = self.info_chain(medication_result)
            
            # Step 3: Generate quiz question
            quiz_question = self.quiz_chain(
                medication=medication_result,
                medicine_info=medicine_info
            )
            
            return {
                "selected_medication": medication_result,
                "medicine_info": medicine_info,
                "quiz_question": quiz_question
            }
            
        except Exception as e:
            if self.debug_mode:
                print(f"Error in chain sequence: {str(e)}")
            raise

    def generate_question(self, atc_cluster: str) -> Dict[str, Any]:
        """
        Generate a quiz question without evaluation.
        
        Args:
            atc_cluster (str): The ATC cluster to select medication from
        
        Returns:
            Dict[str, Any]: The generated question and metadata
        """
        try:
            # Track token usage
            with get_openai_callback() as cb:
                # Generate initial question
                result = self.full_chain({
                    "atc_cluster": atc_cluster
                })
                
                if self.debug_mode:
                    print(f"\nToken usage: {cb}")
                
                return result
                
        except Exception as e:
            if self.debug_mode:
                print(f"Error generating question: {str(e)}")
            return {"error": str(e)}

    def generate_and_evaluate_question(self, atc_cluster: str) -> Dict[str, Any]:
        """
        Generate and evaluate a quiz question (to be implemented later).
        This method is a placeholder for the full pipeline including evaluation.
        
        Args:
            atc_cluster (str): The ATC cluster to select medication from
        
        Returns:
            Dict[str, Any]: The final approved question and metadata
        """
        # For now, just generate without evaluation
        return self.generate_question(atc_cluster)

    def _save_to_database(self, result: Dict[str, Any]) -> None:
        """Save the approved question to the database with metadata."""
        # TODO: Implement database storage
        pass

def main():
    try:
        # Initialize the pipeline
        pipeline = QuizGenerationPipeline(debug_mode=True)
        
        # Example usage
        atc_cluster = "betablokkers"  # Later: get this from user input or configuration
        result = pipeline.generate_question(atc_cluster)  # Using non-evaluation version for now
        
        if "error" in result:
            print(f"\nFout bij genereren van vraag: {result['error']}")
        else:
            print("\nVraag succesvol gegenereerd!")
            print("\nGegenereerde vraag:")
            print(result['quiz_question'])
            
    except Exception as e:
        print(f"\nOnverwachte fout: {str(e)}")

if __name__ == "__main__":
    main() 