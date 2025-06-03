from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_community.callbacks.manager import get_openai_callback
from langchain.callbacks.base import BaseCallbackHandler
from typing import Dict, Any, List
from Models import Extraction, Response
from PromptQuizQuestion import QuizPrompts
import os
from dotenv import load_dotenv
import json

class QuizGenerationChain:
    def __init__(self, model_name: str = "gpt-4o-mini", debug_mode: bool = True):
        # Load environment variables
        load_dotenv()
        
        # Initialize the LLM
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=0.2,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        self.debug_mode = debug_mode
        self._setup_chain()

    def _setup_chain(self):
        # Extraction Prompt
        extraction_prompt = PromptTemplate(
            input_variables=["medicine_info", "category"],
            template=QuizPrompts.get_extraction_prompt("{medicine_info}", "{category}")
        )

        # Quiz Generation Prompt
        quiz_prompt = PromptTemplate(
            input_variables=["medicine_name", "category", "extracted_info"],
            template="""
            {system_style}
            {system_role}
            {system_instructions}
            De vraag moet gaan over {medicine_name} en betrekking hebben op de categorie: {category}.
            Gebruik deze informatie: {extracted_info}

            Je moet een JSON response teruggeven in het volgende format:
            {{
                "introductie": "string",
                "vraag": "string",
                "antwoordopties": ["string", "string", "string", "string"],
                "antwoord": "string",
                "uitleg": "string"
            }}
            """.format(
                system_style=QuizPrompts.STYLE,
                system_role=QuizPrompts.ROLE,
                system_instructions=QuizPrompts.INSTRUCTIONS
            )
        )

        # Create the extraction chain
        extraction_chain = extraction_prompt | self.llm | (
            lambda x: {"extracted_info": x.content}
        )

        # Create the quiz generation chain
        quiz_chain = quiz_prompt | self.llm | (
            lambda x: self._parse_quiz_response(x.content)
        )

        # Create a function to prepare inputs for quiz chain
        def prepare_quiz_inputs(inputs: dict) -> dict:
            return {
                "medicine_name": inputs["medicine_name"],
                "category": inputs["category"],
                "extracted_info": inputs["extracted_info"]
            }

        # Combine the chains using RunnablePassthrough
        self.chain = (
            extraction_chain 
            | RunnablePassthrough.assign(
                quiz_question=lambda x: quiz_chain.invoke(prepare_quiz_inputs(x))
            )
        )

    def _parse_quiz_response(self, quiz_str: str) -> Response:
        """Parse the quiz response string into a Response object."""
        quiz_dict = json.loads(quiz_str)
        return Response(
            introductie=quiz_dict["introductie"],
            vraag=quiz_dict["vraag"],
            antwoordopties=quiz_dict["antwoordopties"],
            antwoord=quiz_dict["antwoord"],
            uitleg=quiz_dict["uitleg"]
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
            result = self.chain.invoke({
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