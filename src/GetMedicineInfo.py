import json
import os
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from typing import Optional

"""
This code fetches medication information from a website and caches it for future use.

Set the CACHE_EXPIRATION_DAYS variable to determine when the cached information is still recent enough. 

"""

CACHE_FILE = "./data/MedicineInformation.json"  
CACHE_EXPIRATION_DAYS = 180

#Hoofdfunctie
def get_medicine_info(medicine_name: str, atc_cluster: str) -> str:
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
            new_url = ask_for_alternative_url(medicine_name, atc_cluster)
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

#Helperfuncties     
def process_response(response: requests.Response, medicine_name: str, url: str, atc_cluster: str) -> Optional[str]:
    if response.status_code == 200 and "Belangrijk om te weten" in response.text:
        medicine_info = parse_medicine_page(response.text)
        save_to_cache(medicine_name, url, medicine_info, atc_cluster)
        return medicine_info
    else:
        print("\n\nEr is een fout opgetreden: De tekst op de pagina begint niet met 'Belangrijk om te weten' of de URL werkt niet.")
        return None  

def ask_for_alternative_url(medicine_name: str, atc_cluster: str) -> Optional[str]:
    while True:
        user_choice = input("De juiste informatie is niet gevonden.\nWil je handmatig een andere URL opzoeken? (ja/nee): ").strip().lower()
        if user_choice == "nee":
            print(f"\nJe hebt ervoor gekozen om geen URL op te zoeken. Het medicijn '{medicine_name}' wordt overgeslagen.")
            return False
        elif user_choice == "ja":
            return input(f"\nGa naar www.apotheek.nl en zoek de pagina met informatie over '{medicine_name}'.\n\n"
                            f"Let op dat:\n"
                            f"1. De informatie betrekking heeft op ATC-cluster '{atc_cluster}'.\n"
                            f"2. De informatie begint met een sectie 'Belangrijk om te weten'.\n\n"
                            f"Plak de volledige URL hier en druk op enter: ").strip()
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
    soup = BeautifulSoup(html, "html.parser")
    list_items = soup.find_all("li", class_="listItemContent_container__25F5W")

    if not list_items:
        raise ValueError(f"De pagina over {medicine_name} bevat niet de juiste informatiestructuur.")

    medicine_info = []
    for item in list_items:
        title = item.find("h2")
        if title:
            medicine_info.append(title.get_text(strip=True))
        content = item.find("div", class_="listItemContent_content__w3Hqp")
        if content:
            medicine_info.append(content.get_text(separator=" ", strip=True))

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

    medicines = ["metoprolol"]  # Voeg hier meer medicijnen toe
    atc_cluster = "betablokkers" # ATC-cluster voor alle medicijnen, later uit JSON-bestand halen?

    for medicine_name in medicines:
        print(f"\nVerwerken van medicijn '{medicine_name}'")
        try:
            medicine_info = get_medicine_info(medicine_name, atc_cluster)
            if not medicine_info or "No relevant information found" in medicine_info:
                print(f"Geen informatie gevonden voor {medicine_name}. Kan geen quizvraag genereren.")
            else:
                print("________________________________________________________________________")
        except Exception as e:
            print(f"Error tijdens verwerken van '{medicine_name}': {e}")
        