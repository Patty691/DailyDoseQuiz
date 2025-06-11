import json
import os
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any
import re
from urllib.parse import urlparse, unquote

#merknaam toevoegen bij: Ga naar www.apotheek.nl en zoek de pagina met informatie over '{medicine_name}'.\n\n"
                            
"""
This code fetches medication information from a website and caches it for future use.

Set the CACHE_EXPIRATION_DAYS variable to determine when the cached information is still recent enough. 

"""

CACHE_FILE = "medicine_info_cache.json"
CACHE_EXPIRATION_DAYS = 30
DEBUG_MODE = False

def debug_print(*args, **kwargs):
    """Print alleen als debug mode aan staat of als het script direct wordt uitgevoerd."""
    if DEBUG_MODE or __name__ == "__main__":
        print(*args, **kwargs)

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
                        debug_print(f"De opgeslagen informatie over '{medicine_name}' is ouder dan {CACHE_EXPIRATION_DAYS} dagen. Nieuwe informatie wordt opgehaald.")
                        cached_data = None  # Forceer nieuwe informatie
                    else:
                        # Gebruik de cache als deze actueel is
                        url = cached_data["url"].strip()
                        debug_print(f"\nInformatie over '{medicine_name}' uit ATC-cluster '{atc_cluster}' uit de cache geraadpleegd.")
                        debug_print(f"De informatie komt van: {url}")
                        debug_print(f"De informatie is opgeslagen op: {cached_data['date']}")
                        return cached_data["info"]
                cache_checked = True  # Markeer dat de cache is gecontroleerd

            # Als we hier komen, moeten we nieuwe informatie ophalen
            if not cache_url_attempted:
                # Probeer eerst de URL uit de cache
                cached_data = load_from_cache(medicine_name)
                if cached_data:
                    url = cached_data["url"].strip()
                    debug_print(f"\nProberen informatie op te halen van: {url}")
                    response = requests.get(url)
                    if response.status_code == 200 and "Belangrijk om te weten" in response.text:
                        medicine_info = parse_medicine_page(response.text)
                        save_to_cache(medicine_name, url, medicine_info, atc_cluster)
                        return medicine_info
                cache_url_attempted = True

            # Als de cache-URL niet werkt, probeer de standaard URL
            if not base_url_attempted:
                base_url = f"https://www.apotheek.nl/medicijnen/{medicine_name.lower()}"
                debug_print(f"\nProberen informatie op te halen van: {base_url}")
                response = requests.get(base_url)
                if response.status_code == 200 and "Belangrijk om te weten" in response.text:
                    medicine_info = parse_medicine_page(response.text)
                    save_to_cache(medicine_name, base_url, medicine_info, atc_cluster)
                    return medicine_info
                base_url_attempted = True

            # Als beide URLs niet werken, vraag om een alternatieve URL
            new_url = ask_for_alternative_url(medicine_name, atc_cluster, brand_name)
            if not new_url:
                return "Geen informatie beschikbaar"
            response = requests.get(new_url)
            if response.status_code == 200 and "Belangrijk om te weten" in response.text:
                medicine_info = parse_medicine_page(response.text)
                save_to_cache(medicine_name, new_url, medicine_info, atc_cluster)
                return medicine_info

        except Exception as e:
            debug_print(f"Fout bij ophalen informatie: {str(e)}")
            return "Geen informatie beschikbaar"

#Helperfuncties     
def process_response(response: requests.Response, medicine_name: str, url: str, atc_cluster: str) -> Optional[str]:
    if response.status_code == 200 and "Belangrijk om te weten" in response.text:
        medicine_info = parse_medicine_page(response.text)
        save_to_cache(medicine_name, url, medicine_info, atc_cluster)
        return medicine_info
    else:
        debug_print("\n\nEr is een fout opgetreden: De tekst op de pagina begint niet met 'Belangrijk om te weten' of de URL werkt niet.")
        return None  

def ask_for_alternative_url(medicine_name: str, atc_cluster: str, brand_name: str = None) -> str:
    """Vraag de gebruiker om een alternatieve URL."""
    search_name = f"{medicine_name} ({brand_name})" if brand_name else medicine_name
    while True:
        url = input(f"\nGeef de URL voor informatie over '{search_name}' uit ATC-cluster '{atc_cluster}':\n> ")
        if url:
            return url
        debug_print("Geen URL ingevoerd. Probeer opnieuw.")

def retry_prompt(medicine_name: str) -> bool:
    while True:
        choice = input(f"\nWil je het opnieuw proberen voor {medicine_name}? (ja/nee): ").strip().lower()
        if choice == "ja":
            return True
        elif choice == "nee":
            return False
        else:
            debug_print("Ongeldige invoer. Typ 'ja' of 'nee'.")      

def parse_medicine_page(html: str) -> str:
    """Parse de HTML van de medicijnpagina en extraheer de relevante informatie."""
    soup = BeautifulSoup(html, "html.parser")
    list_items = soup.find_all("li", class_="listItemContent_container__25F5W")

    if not list_items:
        raise ValueError("De pagina bevat niet de juiste informatiestructuur.")

    medicine_info = []
    for item in list_items:
        title = item.find("h2")
        if title:
            medicine_info.append(title.get_text(strip=True))
        content = item.find("div", class_="listItemContent_content__w3Hqp")
        if content:
            medicine_info.append(content.get_text(separator=" ", strip=True))

    return "\n\n".join(medicine_info)

def load_from_cache(medicine_name: str) -> Optional[Dict[str, Any]]:
    """Laad informatie uit de cache."""
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
                return cache.get(medicine_name)
    except Exception as e:
        debug_print(f"Fout bij laden uit cache: {str(e)}")
    return None

def save_to_cache(medicine_name: str, url: str, info: str, atc_cluster: str):
    """Sla de informatie op in de cache."""
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
        else:
            cache = {}

        cache[medicine_name] = {
            "url": url,
            "info": info,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "atc_cluster": atc_cluster
        }

        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        debug_print(f"Fout bij opslaan in cache: {str(e)}")

    debug_print(f"\n\nInformatie over '{medicine_name}' uit ATC-cluster '{atc_cluster}' is opgezocht en opgeslagen in de cache.")
    debug_print(f"De informatie komt van: {url}")
    debug_print(f"De informatie is opgeslagen op: {cache[medicine_name]['date']}\n\n")

if __name__ == "__main__":
    # Zet debug mode aan voor directe uitvoering
    DEBUG_MODE = False
    
    medicine_name = "apurinol"
    atc_cluster = "colestyramine"
    brand_name = "test"
    
    # Debug output
    debug_print(f"\nDebug: Zoeken naar informatie over {medicine_name}")
    debug_print(f"Debug: ATC-cluster: {atc_cluster}")
    debug_print(f"Debug: Merknaam: {brand_name}")
    
    # Haal informatie op
    medicine_info = get_medicine_info(medicine_name, atc_cluster, brand_name)
    
    # Toon resultaat
    debug_print("\nGevonden informatie:")
    debug_print(medicine_info)
    