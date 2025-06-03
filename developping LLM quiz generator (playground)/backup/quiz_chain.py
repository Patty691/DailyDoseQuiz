from langchain.chains import SequentialChain, LLMChain
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.callbacks import get_openai_callback
from langchain.callbacks.base import BaseCallbackHandler
from typing import Dict, Any, List
from Models import Extraction, Response
from PromptQuizQuestion import QuizPrompts

class QuizGenerationChain:
    def __init__(self, model_name: str = "gpt-4o-mini", debug_mode: bool = True):
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=0.2
        )
        self.debug_mode = debug_mode
        self._setup_chains()

    def _setup_chains(self):
        # Extraction Chain
        extraction_prompt = PromptTemplate(
            input_variables=["medicine_info", "category"],
            template=QuizPrompts.get_extraction_prompt("{medicine_info}", "{category}")
        )
        self.extraction_chain = LLMChain(
            llm=self.llm,
            prompt=extraction_prompt,
            output_key="extracted_info"
        )

        # Quiz Generation Chain
        quiz_prompt = PromptTemplate(
            input_variables=["medicine_name", "category", "extracted_info"],
            template=f"""{{{{system}}}} {QuizPrompts.STYLE}
            {{{{system}}}} {QuizPrompts.ROLE}
            {{{{system}}}} {QuizPrompts.INSTRUCTIONS}
            De vraag moet gaan over {{medicine_name}} en betrekking hebben op de categorie: {{category}}.
            Gebruik deze informatie: {{extracted_info}}
            """
        )
        self.quiz_chain = LLMChain(
            llm=self.llm,
            prompt=quiz_prompt,
            output_key="quiz_question"
        )

        # Combine chains
        self.full_chain = SequentialChain(
            chains=[self.extraction_chain, self.quiz_chain],
            input_variables=["medicine_info", "category", "medicine_name"],
            output_variables=["extracted_info", "quiz_question"],
            verbose=self.debug_mode
        )

    def generate_quiz(self, medicine_info: str, category: str, medicine_name: str) -> Dict[str, Any]:
        """
        Generate a quiz question using the chain.
        
        Args:
            medicine_info (str): The medical information text
            category (str): The knowledge category
            medicine_name (str): The name of the medicine
        
        Returns:
            Dict[str, Any]: Contains 'extracted_info' and 'quiz_question'
        """
        with get_openai_callback() as cb:
            result = self.full_chain({
                "medicine_info": medicine_info,
                "category": category,
                "medicine_name": medicine_name
            })
            
            if self.debug_mode:
                print(f"\nToken usage: {cb}")
            
            return result

class DebugCallback(BaseCallbackHandler):
    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs):
        print(f"\nStarting chain: {serialized.get('name', 'Unknown')}")
        print(f"Inputs: {inputs}")

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs):
        print(f"\nChain output: {outputs}")

    def on_chain_error(self, error: Exception, **kwargs):
        print(f"\nChain error: {error}")

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs):
        print(f"\nStarting LLM with prompt: {prompts[0][:200]}...") 