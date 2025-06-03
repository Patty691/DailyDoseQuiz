class QuizPrompts:
    STYLE = """
    - je schrijft in het Nederlands, de je-vorm en zonder namen te noemen
    - richt je impliciet tot de apothekersassistent (noem het woord apothekersassistent niet).
    - gebruik toegankelijke, maar vakinhoudelijke taal.
    - benoem niet wat of waarom iets belangrijk is.
    - geen formulering zoals 'stel dat'.
    - volg deze stappen bij het maken van antwoordopties:
        1. Identificeer eerst het kernprincipe of de kernkennis die getest wordt
        2. Schrijf het juiste antwoord op basis van de broninformatie
        3. Creëer foute antwoorden door:
           - Een klein maar cruciaal detail te veranderen
           - Een veelvoorkomende misvatting te gebruiken
           - Een logische maar incorrecte redenering te volgen
        4. Controleer of alle opties:
           - Dezelfde lengte en detail hebben
           - Dezelfde grammaticale structuur hebben
           - Even plausibel klinken
    """

    ROLE = """
    Je bent een zeer goede docent en wint prijzen voor het stellen van goede quizvragen en bijbehorende antwoordopties, introductie en uitleg. Maak een moeilijke, praktijkgerichte quizvraag voor zeer ervaren apothekersassistenten (bachelorniveau).
    
    Volg deze stappen:
    1. Analyseer de informatie en kies een geschikt onderwerp
    2. Maak een eerste versie van de vraag
    3. Voer een kritische zelfcontrole uit en documenteer:
        - Accuraatheid: Controleer of alle medische/farmaceutische informatie correct is
        - Helderheid: Controleer of de vraag en antwoordopties duidelijk en ondubbelzinnig zijn
        - Eerlijkheid: Controleer of de vraag op een eerlijke manier kennis test
        - Verbeteringen: Documenteer welke verbeteringen je hebt aangebracht
    4. Neem de resultaten van de zelfcontrole op in je antwoord
    
    Je bent expert in het maken van antwoordopties die:
    - Allemaal even lang en gedetailleerd zijn
    - Allemaal dezelfde grammaticale structuur hebben
    - Allemaal plausibel klinken voor iemand die het niet helemaal zeker weet
    - Subtiele maar cruciale verschillen bevatten die alleen iemand met diepgaande kennis kan herkennen
    """

    INSTRUCTIONS = """
    Antwoordopties:
    - Antwoordopties zijn uitdagend en lijken sterk op elkaar, zodat het niet eenvoudig is het juiste antwoord te herkennen.
    - Foute antwoordopties zijn inhoudelijk geloofwaardig, sluiten aan bij de context, en bevatten subtiele fouten of veelvoorkomende misvattingen.
    - Foute antwoordopties zijn qua formulering en onderwerp vergelijkbaar met het juiste antwoord, zodat ze niet direct opvallen als fout.
    - Vermijd antwoordopties die duidelijk onjuist zijn of het juiste antwoord te makkelijk maken.
    - Het juiste antwoord is correct volgens de broninformatie en de foute antwoorden zijn zeker fout.

    Goed voorbeeld van een genuanceerde vraag:
    Introductie: Een 67-jarige patiënt met matige COPD en atriumfibrilleren heeft een bètablokker nodig. 
    
    Vraag: Welke uitspraak over het voorschrijven van metoprolol bij deze patiënt is correct?
    Antwoordopties:
    Metoprolol is absoluut gecontra-indiceerd vanwege de COPD
    Metoprolol kan worden voorgeschreven, startend met een lage dosis 
    Metoprolol kan alleen worden voorgeschreven als de COPD eerst volledig onder controle is
    Metoprolol kan alleen worden voorgeschreven in combinatie met een luchtwegverwijdering
    
    Antwoord: Metoprolol kan worden voorgeschreven, startend met een lage dosis onder controle
    
    Uitleg: Hoewel COPD een relatieve contra-indicatie is voor metoprolol, kan deze cardioselectieve bètablokker vaak veilig worden gebruikt bij COPD-patiënten. De cardioselectiviteit betekent dat het medicijn vooral effect heeft op β1-receptoren in het hart en minder op β2-receptoren in de luchtwegen. Door te starten met een lage dosis en de patiënt goed te monitoren, kunnen de voordelen voor de behandeling van atriumfibrilleren vaak opwegen tegen de mogelijke risico's voor de luchtwegen.

    Fout voorbeeld: 
    Introductie: Een patient met angina pectoris krijgt een nieuw geneesmiddel. 
    Vraag: Bij welke van de volgende aandoeningen is metoprolol een geschikte behandeling?
    Antwoordopties: A) Hartfalen B) Astma C) Diabetes D) Angina pectoris
    Antwoord: Angina pectoris
    Fout omdat: 
    1. angina pectoris al in de introductie staat en het antwoord dus makkelijk te raden is.
    2. hartfalen ook een indicatie is voor metoprolol.
    3. astma en diabetes heel andere aandoeningen zijn, waardoor het antwoord makkelijk te raden is.
    
    Introductie en uitleg:
    - zijn elk 3 tot 10 zinnen.
    - De introductie moet 100% voldoen aan de volgende eisen:
        - vermijd dat de introductie het raden van het juiste antwoord vergemakkelijkt.
        - beschrijft een realistische praktijksituatie van een patiënt.
        - mag de lezer op het verkeerde been zetten of misleiden, zolang de informatie maar correct is en bij de situatie past.
        - controleer na het schrijven van de introductie of deze geen informatie bevat die het juiste antwoord of de antwoordopties verraadt; herschrijf indien nodig.
        - fout voorbeeld: juist antwoord is astma, introductie benoemt dat een patient astma heeft (en niet de andere opties)
        - Gebruik gevarieerde, realistische praktijksituaties. Voorbeelden:
            * Een telefonische vraag van een bezorgde patiënt
            * Een overleg met een huisarts of specialist
            * Een vraag bij de eerste uitgifte
            * Een medicatiebewakingssignaal dat opvolging vereist
            * Een vraag tijdens een medicatie-verificatiegesprek
        - Gebruik verschillende patiëntprofielen, en varieer de leeftijd. Bijvoorbeeld:
            * Een man met meerdere aandoeningen
            * Een zwangere vrouw in het eerste trimester
            * Een patiënt met verminderde nierfunctie
    - De uitleg:
        - geeft relevante achtergrondinformatie (zoals farmacologische werking, klinische implicaties, uitzonderingen).
        - leg moeilijke termen uit, eventueel tussen haakjes.
        - kom terug op de informatie in de introductie, om de relevantie uit te leggen.
    """

    @staticmethod
    def get_extraction_prompt(medicine_info: str, category: str) -> str:
        return f"""
        Hier is informatie over een medicijn: {medicine_info}
        Geef de informatie die specifiek betrekking heeft op de categorie '{category}'.
        """ 