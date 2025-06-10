
# Functie om relevante informatie te extraheren
# vectorisatie
# elke keer opnieuw of opslaan?
# hoeveelheid informatie?

def (medicine_info: str, category: str) -> str:
    """
    Extract information relevant to a specific category using headers and/or keywords.
    Some information is found under specific headers, other information needs keyword search,
    and some needs both.
    
    Args:
        medicine_info (str): The full medicine information text
        category (str): The category to extract information for
    
    Returns:
        str: The extracted relevant information
    """
    # Map categories to their search criteria
    category_mapping = {
        "indicaties": {
            "headers": ["Wat doet"],
            "keywords": ["verschijnselen", "werking","behandeling","effect"]
        },
        "werkingsmechanisme": {
            "headers": ["Wat doet"],
            "keywords": ["werkt door", "zorgt ervoor", "werking", "effect"]
        },
        "dosering": {
            "keywords": ["keer per dag", "tablet", "mg", "dosis", "innemen", "gebruiken"]
        },
        "toediening": {
            "headers": ["Hoe gebruik ik"]
        },
        "interacties": {
            "headers": ["Mag ik", "met andere medicijnen gebruiken"],
            "keywords": ["combinatie met", "samen met", "wisselwerking"]
        },
        "contra-indicaties": {
            "headers": ["met andere medicijnen gebruiken"], #onjuist, aanpassen
            "keywords": []
        },
        "bijwerkingen": {
            "headers": ["Wat zijn mogelijke bijwerkingen"]
        },
        "monitoring": {
            "headers": ["Belangrijk om te weten"],
            "keywords": ["controleren", "meten", "in de gaten houden", "bloeddruk", "hartslag"]
        },
        "rijvaardigheid": {
            "headers": ["Kan ik met dit medicijn autorijden"]
        },
        "stoppen met gebruik": {
            "headers": ["Mag ik zomaar"]
        },
        "bijzondere populaties": {
            "headers": [
                "Mag ik dit medicijn gebruiken als ik zwanger ben",
                "bij ouderen",
                "bij kinderen"
            ],
            "keywords": ["zwanger", "borstvoeding", "ouderen", "kinderen", "verminderde nierfunctie", "leverfunctie", "overgewicht", "obesitas"]
        }
    }
    
    # Get mapping for the requested category
    category_info = category_mapping.get(category.lower())
    if not category_info:
        return f"Geen specifieke informatie gevonden voor {category}."
    
    # Split into sections
    sections = medicine_info.split("\n\n")
    relevant_sections = []
    
    for i, section in enumerate(sections):
        section_lower = section.lower()
        is_relevant = False
        
        # Check headers if present
        if "headers" in category_info:
            if any(header.lower() in section_lower for header in category_info["headers"]):
                is_relevant = True
                # Add this section and the next one (which usually contains the content)
                relevant_sections.append(section)
                if i + 1 < len(sections):
                    relevant_sections.append(sections[i + 1])
                
        # Check keywords if present
        if "keywords" in category_info and not is_relevant:
            if any(keyword.lower() in section_lower for keyword in category_info["keywords"]):
                relevant_sections.append(section)
    
    # If no relevant sections found, return a message
    if not relevant_sections:
        return f"Geen specifieke informatie gevonden over {category}."
    
    # Join all relevant sections
    return "\n\n".join(relevant_sections)