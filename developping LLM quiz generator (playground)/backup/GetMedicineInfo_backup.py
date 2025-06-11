import os
import json
import requests
from datetime import datetime, timedelta
from typing import Optional
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse, unquote

# Configuratie
CACHE_FILE = "./data/MedicineInformation.json"  
CACHE_EXPIRATION_DAYS = 180

#Hoofdfunctie
def get_medicine_info(medicine_name: str, atc_cluster: str, brand_name: str = None) -> str:
    cache_checked = False 
    cache_url_attempted = False  
    base_url_attempted = False  

    while True:
        try:
            # Controleer de cache en gebruik de informatie als deze actueel is
            if not cache_checked:
                cached_data = load_from_cache(medicine_name)
                if cached_data:
                    # Controleer de leeftijd van de cache
                    cache_date = datetime.strptime(cached_data["date"], "%Y-%m-%d %H:%M:%S")
                    if datetime.now() - cache_date > timedelta(days=CACHE_EXPIRATION_DAYS):
                        print(f"De opgeslagen informatie over '{medicine_name}' is ouder dan {CACHE_EXPIRATION_DAYS} dagen. Nieuwe informatie wordt opgehaald.")
                        cached_data = None  # Forceer nieuwe informatie
                    else:
                        # Gebruik de cache als deze actueel is
                        url = cached_data["url"].strip()
                        print(f"\nInformatie over '{medicine_name}' uit ATC-cluster '{atc_cluster}' uit de cache geraadpleegd.")
                        print(f"De informatie komt van: {url}")
                        print(f"De informatie is opgeslagen op: {cached_data['date']}")
                        return cached_data["info"]
                cache_checked = True  # Markeer dat de cache is gecontroleerd

            # Probeer de cache URL om informatie opnieuw te halen
            if not cache_url_attempted:
                cached_data = load_from_cache(medicine_name)
                if cached_data:
                    full_url = cached_data["url"].strip()
                    print("De URL uit de cache is geraadpleegd voor het ophalen van nieuwe informatie.")
                    response = requests.get(full_url)
                    result = process_response(response, medicine_name, full_url, atc_cluster)
                    if result:
                        return result
                cache_url_attempted = True
                    continue

            # Probeer de base URL om informatie op te halen
            if not base_url_attempted:
                base_url = f"https://www.apotheek.nl/medicijnen/{medicine_name.lower()}"
                print(f"\nAutomatisch geraadpleegde URL: {base_url}")
                response = requests.get(base_url)
                result = process_response(response, medicine_name, base_url, atc_cluster)
                if result:
                    return result
                base_url_attempted = True
                continue

            # Vraag om een alternatieve URL
            new_url = ask_for_alternative_url(medicine_name, atc_cluster, brand_name)
            if not new_url:
                return "Geen informatie beschikbaar."
            response = requests.get(new_url)
            result = process_response(response, medicine_name, new_url, atc_cluster)
            if result:
                return result

        except Exception as e:
            print(f"\nEr is een fout opgetreden: {e}")
            if not retry_prompt(medicine_name):
                return "Geen informatie beschikbaar."

def process_response(response, medicine_name: str, url: str, atc_cluster: str) -> Optional[str]:
    """Verwerk de response van de website."""
    if response.status_code != 200:
        print(f"Fout bij ophalen informatie: HTTP {response.status_code}")
        return None
        
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Zoek de sectie "Belangrijk om te weten"
    important_section = soup.find('h2', string='Belangrijk om te weten')
    if not important_section:
        print("Sectie 'Belangrijk om te weten' niet gevonden")
        return None
        
    # Verzamel alle informatie tot aan de volgende sectie
    info = []
    current = important_section.find_next()
    while current and current.name != 'h2':
        if current.name == 'p':
            text = current.get_text(strip=True)
            if text:
                info.append(text)
        current = current.find_next()
        
    if not info:
        print("Geen relevante informatie gevonden in de sectie")
        return None
        
    # Sla de informatie op in de cache
    info_text = "\n".join(info)
    save_to_cache(medicine_name, url, info_text, atc_cluster)
    
    return info_text

def ask_for_alternative_url(medicine_name: str, atc_cluster: str, brand_name: str = None) -> Optional[str]:
    while True:
        user_choice = input("\nWil je handmatig een andere URL opzoeken? (ja/nee): ").strip().lower()
        if user_choice == "nee":
            print(f"\nJe hebt ervoor gekozen om geen URL op te zoeken. Het medicijn '{medicine_name}' wordt overgeslagen.")
            return False
        elif user_choice == "ja":
            search_name = f"{medicine_name} ({brand_name})" if brand_name else medicine_name
            url = input(f"\nGa naar www.apotheek.nl en zoek de pagina met informatie over '{search_name}' uit atc-cluster '{atc_cluster}'.\n\n"
                            f"Let op dat de informatie begint met een sectie 'Belangrijk om te weten'.\n\n"
                            f"Plak de volledige URL hier en druk op enter: ").strip()
            if not url:
                print("Geen URL ingevoerd. Probeer opnieuw.")
                continue
            return url
        else:
            print("Ongeldige invoer. Typ 'ja' of 'nee'.")

def retry_prompt(medicine_name: str) -> bool:
    while True:
        retry = input("\nWil je het opnieuw proberen (ja/nee)? ").strip().lower()
        if retry == "nee":
            print(f"\nHet medicijn '{medicine_name}' wordt overgeslagen.")
            return False
        elif retry == "ja":
            print("\nStart opnieuw met het zoeken van informatie...")
            return True
        else:
            print("Ongeldige invoer. Typ 'ja' of 'nee'.")      

def parse_medicine_page(html: str) -> str:
    """Parse de HTML van de medicijnpagina en extraheer de relevante informatie."""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Zoek de sectie "Belangrijk om te weten"
    important_section = soup.find('h2', string='Belangrijk om te weten')
    if not important_section:
        return None
        
    # Verzamel alle informatie tot aan de volgende sectie
    medicine_info = []
    current = important_section.find_next()
    while current and current.name != 'h2':
        if current.name == 'p':
            text = current.get_text(strip=True)
            if text:
                medicine_info.append(text)
        current = current.find_next()
        
    if not medicine_info:
        return None
        
    return "\n\n".join(medicine_info)

def load_from_cache(medicine_name: str) -> Optional[dict]:
    if not os.path.exists(CACHE_FILE):
        return None
        
    with open(CACHE_FILE, "r") as f:
        cache = json.load(f)

    return cache.get(medicine_name)  # Retourneer de cachegegevens (of None als het medicijn niet bestaat)

def save_to_cache(medicine_name: str, url: str, medicine_info: str, atc_cluster: str) -> None:
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)
    else:
        cache = {}
                
    cache[medicine_name] = {
        "url": url,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "info": medicine_info 
    }
        
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=4)
            
    print(f"\n\nInformatie over '{medicine_name}' uit ATC-cluster '{atc_cluster}' is opgezocht en opgeslagen in de cache.")
    print(f"De informatie komt van: {url}")
    print(f"De informatie is opgeslagen op: {cache[medicine_name]['date']}\n\n")

if __name__ == "__main__":
    medicine_name = "metoolol" # Voeg hier meer medicijnen toe
    atc_cluster = "betablokkers" # ATC-cluster voor alle medicijnen, later uit JSON-bestand halen?
    brand_name = "mol"
    
    print(f"\nVerwerken van medicijn '{medicine_name}'")
    try:
        medicine_info = get_medicine_info(medicine_name, atc_cluster, brand_name)
        if not medicine_info or "No relevant information found" in medicine_info:
            print(f"Geen informatie gevonden voor {medicine_name}. Kan geen quizvraag genereren.")
        else:
            print("________________________________________________________________________")
    except Exception as e:
        print(f"Error tijdens verwerken van '{medicine_name}': {e}") 