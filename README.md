# Daily Dose Quiz Generator

Een LangChain-gebaseerd systeem voor het genereren van medicatie quiz vragen.

## Setup

1. Installeer de dependencies:
```bash
pip install -r requirements.txt
```

2. Maak een `.env` bestand met je OpenAI API key:
```bash
OPENAI_API_KEY=your_api_key_here
```

3. Zorg dat de medicatie database aanwezig is in `data/MedicationClustersDatabase.json`

## Structuur

Het systeem gebruikt een chain-gebaseerde architectuur met de volgende componenten:

- `MedicineSelectionChain`: Selecteert medicatie op basis van gewichten
- `QuizGenerationChain`: Hoofdchain die alle componenten samenbrengt

De configuratie staat in `src/chains/config.py`.

## Gebruik

Basis gebruik:

```python
from src.chains.base_chain import QuizGenerationChain

# Maak een nieuwe chain
chain = QuizGenerationChain()

# Genereer quiz vragen
result = chain.invoke(
    num_clusters=1,    # Aantal medicatie clusters
    num_medicines=2    # Aantal geneesmiddelen per cluster
)

print(result)
```

## Configuratie

Je kunt de configuratie aanpassen in `src/chains/config.py`:

- Model instellingen (temperatuur, max tokens, etc.)
- Database locaties
- Chain parameters (aantal vragen, moeilijkheidsgraad, etc.) 