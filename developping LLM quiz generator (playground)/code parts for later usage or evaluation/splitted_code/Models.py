from pydantic import BaseModel, Field
from typing import List

class Extraction(BaseModel):
    relevant_information: str = Field(description="The extracted information.")

class Response(BaseModel):
    class Step(BaseModel):
        description: str = Field(description="Description of the step taken.")
        action: str = Field(description="Action taken to resolve the issue.")
        result: str = Field(description="Result of the action taken.")
    steps: List[Step]

    class SelfVerification(BaseModel):
        check_accuracy: str = Field(description="Verification of medical/pharmaceutical accuracy")
        check_clarity: str = Field(description="Verification that the question and options are clear and unambiguous")
        check_fairness: str = Field(description="Verification that the question tests knowledge fairly")
        improvements: List[str] = Field(description="List of improvements made during verification")

    class FinalResolution(BaseModel):
        introductie: str = Field(description="The introduction text for the quiz question.")
        vraag: str = Field(description="The quiz question.")
        antwoordopties: List[str] = Field(description="The answer options for the quiz question, without any prefixes.")
        antwoord: str = Field(description="The correct answer to the quiz question.")
        uitleg: str = Field(description="The explanation for the correct answer.")
        verificatie: "Response.SelfVerification" = Field(description="Self-verification results")

    final_resolution: FinalResolution

    class Config:
        json_schema_extra = {
            "required": ["steps", "final_resolution"]
        } 