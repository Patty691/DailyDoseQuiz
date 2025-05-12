import json
import os
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from typing import Optional

#check deze code... is aanpassing van originele code
#code werkt nog niet goed. 
#check of op alle nodige plekken de code je terug in de (juiste) loop brengt
#origineel bestand in backup/FetchMedicineInfo.py
CACHE_FILE = "medicine_cache.json"

def get_medicine_info(medicine_name: str, atc_cluster: str, use_cache: bool = False) -> str:
    """
    Haalt medicatie-informatie op via een URL of uit de cache.
    """
    cached_data = load_from_cache(medicine_name)
    if use_cache and cached_data:
        url = cached_data["url"].strip()
        print(f"URL uit de cache geraadpleegd: {url}")
        response = fetch_url(url)

        if response and response.status_code == 200:
            return cached_data["info"]
        else:
            print("De URL uit de cache werkt niet. Probeer de standaard URL.")

    base_url = f"https://www.apotheek.nl/medicijnen/{medicine_name.lower()}"
    print(f"Nieuwe URL geraadpleegd: {base_url}")
    response = fetch_url(base_url)

    if not response or response.status_code != 200:
        print(f"De standaard URL werkt niet voor '{medicine_name}'.")
        response = handle_alternative_url(medicine_name, atc_cluster)

    if not response or "Belangrijk om te weten" not in response.text:
        return "De gezochte informatie is niet beschikbaar. Probeer een andere URL."

    relevant_text = parse_medicine_page(response.text)
    save_to_cache(medicine_name, response.url, relevant_text)
    return relevant_text

def fetch_url(url: str) -> Optional[requests.Response]:
    """
    Voert een GET-verzoek uit naar de opgegeven URL.
    """
    try:
        return requests.get(url)
    except Exception as e:
        print(f"Fout bij ophalen van de URL: {e}")
        return None

def handle_alternative_url(medicine_name: str, atc_cluster: str) -> Optional[requests.Response]:
    """
    Vraagt de gebruiker om een alternatieve URL als de standaard URL niet werkt.
    """
    while True:
        user_choice = input("Wil je een andere URL opzoeken? (ja/nee): ").strip().lower()
        if user_choice == "nee":
            print(f"Je hebt ervoor gekozen om geen URL op te zoeken. '{medicine_name}' wordt overgeslagen.")
            return None
        elif user_choice == "ja":
            url = input(f"Plak de volledige URL hier voor '{medicine_name}': ").strip()
            response = fetch_url(url)
            if response and response.status_code == 200:
                return response
            else:
                print("De ingevoerde URL werkt niet. Probeer opnieuw.")
        else:
            print("Ongeldige invoer. Typ 'ja' of 'nee'.")

def parse_medicine_page(html: str) -> str:
    """
    Parseert de HTML-pagina en haalt relevante medicatie-informatie op.
    """
    soup = BeautifulSoup(html, "html.parser")
    list_items = soup.find_all("li", class_="listItemContent_container__25F5W")

    if not list_items:
        raise ValueError("De structuur van de pagina is niet zoals verwacht.")

    relevant_text = []
    for item in list_items:
        title = item.find("h2")
        if title:
            relevant_text.append(title.get_text(strip=True))
        content = item.find("div", class_="listItemContent_content__w3Hqp")
        if content:
            relevant_text.append(content.get_text(separator=" ", strip=True))

    return "\n\n".join(relevant_text)

def load_from_cache(medicine_name: str) -> Optional[dict]:
    """
    Laadt medicatie-informatie uit de cache als deze beschikbaar is.
    """
    if not os.path.exists(CACHE_FILE):
        return None

    with open(CACHE_FILE, "r") as f:
        cache = json.load(f)

    return cache.get(medicine_name)

def save_to_cache(medicine_name: str, url: str, info: str) -> None:
    """
    Slaat medicatie-informatie op in de cache.
    """
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)
    else:
        cache = {}

    cache[medicine_name] = {
        "url": url,
        "info": info,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=4)

    print(f"Informatie over '{medicine_name}' opgeslagen in cache.")

if __name__ == "__main__":
    medicine_name = "xeja"
    atc_cluster = "hartmedicatie"
    use_cache = False
    DEBUG_MODE = False

    try:
        medicine_info = get_medicine_info(medicine_name, atc_cluster, use_cache)
        if not medicine_info or "Geen informatie beschikbaar" in medicine_info:
            print("Geen informatie gevonden. Kan geen quizvraag genereren.")
            exit(1)
        if DEBUG_MODE:
            print("DEBUG: Opgehaalde informatie:")
            print(medicine_info)
    except Exception as e:
        print(f"Error tijdens uitvoeren van de functie: {e}.")
        exit(1)