from typing import Dict, Any
import os
from dotenv import load_dotenv

# Laad environment variables
load_dotenv()

# OpenAI configuratie
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY niet gevonden in environment variables")

# Model configuratie
MODEL_CONFIG = {
    "model": "gpt-4-turbo-preview",  # Default model
    "temperature": 0.7,
    "max_tokens": 1000
}

# Database configuratie
DATABASE_CONFIG = {
    "medication_db": "data/MedicationClustersDatabase.json",
    "quiz_db": "data/quiz.db"
}

# Chain configuratie
CHAIN_CONFIG = {
    "medicine_selection": {
        "num_clusters": 1,
        "num_medicines": 1
    },
    "question_generation": {
        "num_questions": 3,
        "difficulty": "medium",
        "question_types": ["multiple_choice", "open"]
    }
}

def get_config(section: str) -> Dict[str, Any]:
    """
    Haal configuratie op voor een specifieke sectie.
    
    Args:
        section: Naam van de configuratie sectie
        
    Returns:
        Dict met configuratie waardes
    """
    config_map = {
        "model": MODEL_CONFIG,
        "database": DATABASE_CONFIG,
        "chain": CHAIN_CONFIG
    }
    
    if section not in config_map:
        raise ValueError(f"Ongeldige configuratie sectie: {section}")
        
    return config_map[section] 