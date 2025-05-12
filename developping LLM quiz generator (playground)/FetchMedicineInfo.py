import json
import os
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from typing import Optional

CACHE_FILE = "medicine_cache.json" # nog aanpassen naar een andere naam en locatie
USE_CACHE = True  # True:de reeds opgeslagen informatie uit de cache gebruiken. False: informatie opnieuw ophalen (URL uit de cache wordt dan wel gebruikt) 



##volgende checks zijn nog nodig:
#de functie moet ook een lijst met medicijnen kunnen aanroepen (bijv. in de main functie)
#als medicijn wordt overgeslagen en er is een lijst medicijnen, dan moet de functie opnieuw worden aangeroepen met de volgende medicijn in de lijst

##opties:
#get medicine heeft een aan/uit om info uit de cache te gebruiken. Je kunt ook de (main) functie aanpassen naar bijv.: als datum < 3 maanden dan cache gebruiken)


#Hoofdfunctie
def get_medicine_info(medicine_name: str, atc_cluster: str, USE_CACHE: bool) -> str:
    cache_url_attempted = False  
    base_url_attempted = False  

    while True:
        try:
            # Gebruik de informatie uit de cache
            if USE_CACHE:
                cached_data = load_from_cache(medicine_name)
                if cached_data:
                    url = cached_data["url"].strip()
                    print(f"\nInformatie over '{medicine_name}' uit ATC-cluster '{atc_cluster}' uit de cache geraadpleegd.")
                    print(f"De informatie komt van: {url}")
                    print(f"Opgeslagen op: {cached_data['date']}")
                    return cached_data["info"]

            # Probeer de cache URL om informatie opnieuw te halen
            if not cache_url_attempted:
                cached_data = load_from_cache(medicine_name)
                if cached_data:
                    full_url = cached_data["url"].strip()
                    print(f"\nURL uit de cache geraadpleegd voor het ophalen van nieuwe informatie: {full_url}")
                    response = requests.get(full_url)
                    result = process_response(response, medicine_name, full_url)
                    if result:
                        return result
                    cache_url_attempted = True
                    continue

            # Probeer de base URL om informatie op te halen
            if not base_url_attempted:
                base_url = f"https://www.apotheek.nl/medicijnen/{medicine_name.lower()}"
                print(f"\nAutomatisch geraadpleegde URL: {base_url}")
                response = requests.get(base_url)
                result = process_response(response, medicine_name, base_url)
                if result:
                    return result
                base_url_attempted = True
                continue

            # Vraag om een alternatieve URL
            new_url = ask_for_alternative_url(medicine_name, atc_cluster)
            if not new_url:
                return "Geen informatie beschikbaar."
            response = requests.get(new_url)
            result = process_response(response, medicine_name, new_url)
            if result:
                return result

        except Exception as e:
            print(f"\nEr is een fout opgetreden: {e}")
            if not retry_prompt(medicine_name):
                return "Geen informatie beschikbaar."

#Helperfuncties     
def process_response(response: requests.Response, medicine_name: str, url: str) -> Optional[str]:
    if response.status_code == 200 and "Belangrijk om te weten" in response.text:
        medicine_info = parse_medicine_page(response.text)
        save_to_cache(medicine_name, url, medicine_info)
        return medicine_info
    else:
        print("\n\nDEBUG: De tekst op de pagina begint niet met 'Belangrijk om te weten' of de URL werkt niet.")
        return None  

def ask_for_alternative_url(medicine_name: str, atc_cluster: str) -> Optional[str]:
    while True:
        user_choice = input("De juiste informatie is niet gevonden.\nWil je handmatig een andere URL opzoeken? (ja/nee): ").strip().lower()
        if user_choice == "nee":
            print(f"Je hebt ervoor gekozen om geen URL op te zoeken. Het medicijn '{medicine_name}' wordt overgeslagen.")
            return False
        elif user_choice == "ja":
            return input(f"\nGa naar www.apotheek.nl en zoek informatie over {medicine_name}.\n\n"
                            f"Let op dat:\n"
                            f"1. De informatie betrekking heeft op ATC-cluster {atc_cluster}.\n"
                            f"2. De pagina begint met 'Belangrijk om te weten'.\n\n"
                            f"Plak de volledige URL hier en druk op enter: ").strip()
        else:
            print("Ongeldige invoer. Typ 'ja' of 'nee'.")

def retry_prompt(medicine_name: str) -> bool:
    while True:
        retry = input("\nWil je het opnieuw proberen (ja/nee)? ").strip().lower()
        if retry == "nee":
            print(f"Het medicijn '{medicine_name}' wordt overgeslagen.")
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
        raise ValueError(f"De pagina bevat niet de juiste informatie over {medicine_name}.")

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

    return cache.get(medicine_name)

def save_to_cache(medicine_name: str, url: str, medicine_info: str) -> None:
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)
    else:
        cache = {}

    cache[medicine_name] = {
        "url": url,
        "info": medicine_info,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=4)

    print(f"\n\nInformatie over '{medicine_name}' uit ATC-cluster '{atc_cluster}' opgezocht en opgeslagen in cache. \nDatum en tijd: {cache[medicine_name]['date']}\n\n")

if __name__ == "__main__":

    medicines = ["lisil", "apixaban", "enl"]  # Voeg hier meer medicijnen toe
    atc_cluster = "hartmedicatie" # ATC-cluster voor alle medicijnen, later uit JSON-bestand halen

    for medicine_name in medicines:
        print(f"\nVerwerken van medicijn: {medicine_name}")
        try:
            medicine_info = get_medicine_info(medicine_name, atc_cluster, USE_CACHE)
            if not medicine_info or "No relevant information found" in medicine_info:
                print(f"Geen informatie gevonden voor {medicine_name}. Kan geen quizvraag genereren.")
            else:
                print("________________________________________________________________________")
        except Exception as e:
            print(f"Error tijdens verwerken van {medicine_name}: {e}")
        