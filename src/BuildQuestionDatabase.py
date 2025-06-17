import os
import sqlite3
import json
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional
import uuid

from SelectMedication import select_medication
from GetMedicineInfo import get_medicine_info
from GenerateQuestion import generate_quiz_question


# LangChain tracing activeren
# Opslag naar DB inbouwen


os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "VUL_HIER_JE_LSMITH_API_KEY_IN")


# Configuratie
NUM_CLUSTERS = 1
NUM_MEDICINES = 1
DB_PATH = "/Users/pattynooijen/Documents/VisualStudioCode/daily_dose_quiz/data/QuizQuestions.db"
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "Schema.sql")

# Basis componenten
class StatisticsManager:
    """Beheert statistieken voor het quiz generatie proces."""
    def __init__(self):
        self.stats = {
            "start_time": datetime.now(),
            "clusters_processed": 0,
            "total_medications": 0,
            "successful_medications": 0,
            "failed_medications": [],
            "questions_generated": 0,
            "categories_used": set(),
            "errors": []
        }

    def increment_clusters_processed(self):
        self.stats["clusters_processed"] += 1

    def increment_total_medications(self):
        self.stats["total_medications"] += 1

    def increment_successful_medications(self):
        self.stats["successful_medications"] += 1

    def increment_questions_generated(self):
        self.stats["questions_generated"] += 1

    def add_failed_medication(self, name: str, cluster: str, reason: str):
        self.stats["failed_medications"].append({
            "name": name,
            "cluster": cluster,
            "reason": reason
        })

    def add_error(self, error: str):
        self.stats["errors"].append(error)

    def add_category(self, category: str):
        self.stats["categories_used"].add(category)

class DatabaseManager:
    """Beheert database operaties voor quiz vragen en logging."""
    def __init__(self, db_path: str = DB_PATH, schema_path: str = SCHEMA_PATH):
        self.db_path = db_path
        self.schema_path = schema_path
        self._init_db()

    def _init_db(self):
        if not os.path.exists(self.schema_path):
            raise FileNotFoundError(f"schema.sql niet gevonden op: {self.schema_path}")
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        with open(self.schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
            c.executescript(schema_sql)
        conn.commit()
        conn.close()

    def save_selected_medications(self, selected_medications: Dict[str, Any]) -> None:
        """
        Sla geselecteerde medicatie op in de database.
        
        Args:
            selected_medications: Dict met geselecteerde medicatie informatie
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            for cluster in selected_medications["selected_clusters"]:
                for medicine in cluster["geneesmiddelen"]:
                    c.execute('''
                        INSERT INTO selected_medications (
                            uuid, atc5_code, cluster_name, cluster_weight,
                            atc7_code, medicine_name, brand_name, medicine_weight
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        str(uuid.uuid4()),  # Genereer een nieuwe UUID
                        cluster["atc5_code"],
                        cluster["naam"],
                        cluster["gewicht"],
                        medicine["atc7"],
                        medicine["naam"],
                        medicine.get("merknaam", None),
                        medicine["gewicht"]
                    ))
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Fout bij opslaan geselecteerde medicatie: {str(e)}")
            
        finally:
            conn.close()

    def save_information_and_quiz_question(self, **kwargs):
        quiz_question_uuid = str(uuid.uuid4())
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Save information
        c.execute('''
            INSERT INTO information (
                quiz_question_uuid, atc7_code, kenniscategorie, bron_url, timestamp_opgeslagen,
                geëxtraheerde_informatie, llm_raw_output, timestamp_gegenereerd
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            quiz_question_uuid,
            kwargs.get('atc7_code'),
            kwargs.get('kenniscategorie'),
            kwargs.get('bron_url'),
            kwargs.get('timestamp_opgeslagen'),
            kwargs.get('geëxtraheerde_informatie'),
            kwargs.get('llm_info_raw_output'),
            kwargs.get('timestamp_gegenereerd')
        ))
        information_id = c.lastrowid

        # Save quiz question
        antwoordopties = kwargs.get('antwoordopties', [])
        while len(antwoordopties) < 4:
            antwoordopties.append("")

        c.execute('''
            INSERT INTO generated_quiz_questions (
                quiz_question_uuid, information_id, introductie, vraag,
                antwoordoptie_1, antwoordoptie_2, antwoordoptie_3, antwoordoptie_4,
                juiste_antwoord, uitleg, llm_raw_output, timestamp_gegenereerd
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            quiz_question_uuid,
            information_id,
            kwargs.get('introductie'),
            kwargs.get('vraag'),
            antwoordopties[0],
            antwoordopties[1],
            antwoordopties[2],
            antwoordopties[3],
            kwargs.get('juiste_antwoord'),
            kwargs.get('uitleg'),
            kwargs.get('llm_quiz_raw_output'),
            kwargs.get('timestamp_gegenereerd')
        ))
        conn.commit()
        conn.close()

    def log_process(self, event_type: str, medicine: str, category: str, message: str):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            INSERT INTO process_logs (event_type, medicine, category, message, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (event_type, medicine, category, message, datetime.now().isoformat()))
        conn.commit()
        conn.close()

# Quiz generatie componenten
class MedicationSelector:
    """Selecteert medicatie uit de database."""
    def __init__(self, num_clusters: int = NUM_CLUSTERS, num_medicines: int = NUM_MEDICINES):
        self.num_clusters = num_clusters
        self.num_medicines = num_medicines

    def select_medications(self, atc_cluster: Optional[str] = None) -> Dict[str, Any]:
        try:
            result = select_medication(
                atc_cluster=atc_cluster,
                num_clusters=self.num_clusters,
                num_medicines=self.num_medicines
            )
            
            if "error" in result:
                raise ValueError(result["error"])
                
            return result
            
        except Exception as e:
            raise RuntimeError(f"Fout bij selecteren medicatie: {str(e)}")

class QuestionGenerator:
    """Genereert quiz vragen voor medicatie."""
    def __init__(self, debug_mode: bool = True):
        self.debug_mode = debug_mode
        self.stats_manager = StatisticsManager()

    def _validate_question_data(self, data: Any) -> Optional[Dict[str, Any]]:
        """Valideer en converteer de LLM output naar het juiste formaat."""
        try:
            # Als het al een dictionary is, gebruik die
            if isinstance(data, dict):
                return data
                
            # Als het een string is, probeer het te parsen als JSON
            if isinstance(data, str):
                try:
                    return json.loads(data)
                except json.JSONDecodeError:
                    if self.debug_mode:
                        print(f"Kon string niet parsen als JSON: {data[:100]}...")
                    return None
                    
            # Als het een object is met final_resolution attribuut
            if hasattr(data, 'final_resolution'):
                q = data.final_resolution
                return {
                    "introductie": getattr(q, "introductie", ""),
                    "vraag": getattr(q, "vraag", ""),
                    "antwoordopties": getattr(q, "antwoordopties", []),
                    "antwoord": getattr(q, "antwoord", ""),
                    "uitleg": getattr(q, "uitleg", ""),
                    "categorie": getattr(q, "categorie", "")
                }
                
            # Als het een object is met directe attributen
            if hasattr(data, 'introductie'):
                return {
                    "introductie": getattr(data, "introductie", ""),
                    "vraag": getattr(data, "vraag", ""),
                    "antwoordopties": getattr(data, "antwoordopties", []),
                    "antwoord": getattr(data, "antwoord", ""),
                    "uitleg": getattr(data, "uitleg", ""),
                    "categorie": getattr(data, "categorie", "")
                }
                
            if self.debug_mode:
                print(f"Onbekend data type: {type(data)}")
            return None
            
        except Exception as e:
            if self.debug_mode:
                print(f"Fout bij valideren vraag data: {str(e)}")
            return None

    def generate_question(self, medicine_name: str, medicine_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Genereer een quiz vraag voor een medicijn."""
        try:
            # Genereer de vraag
            question = generate_quiz_question(
                medicine_name=medicine_name,
                medicine_info=medicine_info,
                debug_mode=self.debug_mode  # Geef debug_mode door aan generate_quiz_question
            )
            
            if not question:
                if self.debug_mode:
                    print("Geen vraag gegenereerd")
                return None

            # Valideer en converteer de output
            question_data = self._validate_question_data(question)
            
            if not question_data:
                if self.debug_mode:
                    print("Vraag data kon niet gevalideerd worden")
                self.stats_manager.add_error(f"Ongeldige vraag data voor {medicine_name}")
                return None

            # Controleer of alle verplichte velden aanwezig zijn
            required_fields = ["introductie", "vraag", "antwoordopties", "antwoord", "uitleg"]
            missing_fields = [field for field in required_fields if not question_data.get(field)]
            
            if missing_fields:
                if self.debug_mode:
                    print(f"Ontbrekende velden: {missing_fields}")
                self.stats_manager.add_error(f"Ontbrekende velden in vraag voor {medicine_name}: {missing_fields}")
                return None

            # Update statistieken
            self.stats_manager.add_category(question_data.get("categorie", "onbekend"))
            self.stats_manager.increment_questions_generated()
            
            return question_data
            
        except Exception as e:
            error_msg = f"Fout bij genereren vraag voor {medicine_name}: {str(e)}"
            if self.debug_mode:
                print(error_msg)
            self.stats_manager.add_error(error_msg)
            return None

# Hoofdpipeline
class QuizGenerationPipeline:
    """Coördineert het hele proces van quiz generatie."""
    def __init__(self, debug_mode: bool = True):
        load_dotenv()
        self.debug_mode = debug_mode
        self.db_manager = DatabaseManager()
        self.question_generator = QuestionGenerator(debug_mode)
        self.medication_selector = MedicationSelector()

    def generate_quiz(self, atc_cluster: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            # Select medications
            selected_meds = self.medication_selector.select_medications(atc_cluster)
            
            # Save selected medications to database
            self.db_manager.save_selected_medications(selected_meds)

            # Get medicine information
            medicine_info = self._get_medicine_information(selected_meds)

            # Generate questions
            questions = self._generate_questions(medicine_info)
            return questions
        except Exception as e:
            self.db_manager.log_process("error", '', '', f"Fout tijdens quiz generatie: {str(e)}")
            return []

    def _get_medicine_information(self, medication: Dict[str, Any]) -> Dict[str, Any]:
        all_info = {}
        for cluster in medication["selected_clusters"]:
            self.question_generator.stats_manager.increment_clusters_processed()
            cluster_info = {
                "cluster_name": cluster["naam"],
                "medications": {}
            }
            
            for med in cluster["geneesmiddelen"]:
                self.question_generator.stats_manager.increment_total_medications()
                med_name = med["naam"].lower()
                brand_name = med.get("merknaam", None)
                
                try:
                    # Haal eerst de UUID op uit de database
                    conn = sqlite3.connect(self.db_manager.db_path)
                    c = conn.cursor()
                    c.execute('''
                        SELECT uuid FROM selected_medications 
                        WHERE medicine_name = ? AND atc7_code = ?
                    ''', (med["naam"], med["atc7"]))
                    result = c.fetchone()
                    
                    if not result:
                        raise RuntimeError(f"Geen UUID gevonden voor {med_name}")
                    med_uuid = result[0]
                    
                    info = get_medicine_info(med_name, cluster["naam"], brand_name, debug_mode=self.debug_mode)
                    
                    # Converteer string naar dictionary indien nodig
                    if isinstance(info, str):
                        try:
                            # Probeer eerst als JSON te parsen
                            info = json.loads(info)
                        except json.JSONDecodeError:
                            # Als dat niet lukt, maak een basis dictionary
                            info = {
                                "url": "",
                                "date": datetime.now().isoformat(),
                                "kenniscategorie": "",
                                "relevant_information": info,
                                "llm_raw_output": info
                            }
                    
                    if not info or "Geen informatie beschikbaar" in str(info):
                        self.db_manager.log_process("warning", med_name, '', "Geen informatie gevonden, medicijn overgeslagen")
                        self.question_generator.stats_manager.add_failed_medication(
                            med_name, 
                            cluster["naam"], 
                            "Geen informatie beschikbaar"
                        )
                        continue

                    # Sla de informatie op in de medicine_information tabel
                    c.execute('''
                        INSERT INTO medicine_information (
                            quiz_question_uuid, bron_url, timestamp_opgeslagen,
                            kenniscategorie, relevante_informatie, llm_raw_output,
                            timestamp_gegenereerd
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        med_uuid,  # Gebruik de opgehaalde UUID
                        info.get("url", ""),  # Gebruik 'url' uit dict
                        info.get("date", ""),  # Gebruik datum uit dict
                        info.get("kenniscategorie", ""),
                        info.get("relevant_information", ""),
                        json.dumps(info),
                        datetime.now().isoformat()
                    ))
                    conn.commit()
                    conn.close()
                        
                    cluster_info["medications"][med_name] = {
                        "info": info,
                        "atc7": med["atc7"],
                        "brand": med.get("merknaam", "")
                    }
                    self.question_generator.stats_manager.increment_successful_medications()
                    
                except Exception as med_error:
                    self.db_manager.log_process("error", med_name, '', f"Fout bij ophalen info: {str(med_error)}")
                    self.question_generator.stats_manager.add_failed_medication(
                        med_name, 
                        cluster["naam"], 
                        str(med_error)
                    )
                    continue
                    
            if cluster_info["medications"]:
                all_info[cluster["atc5_code"]] = cluster_info
                
        if not all_info:
            self.db_manager.log_process("error", '', '', "Geen informatie gevonden voor alle geselecteerde medicijnen")
            raise RuntimeError("Geen informatie gevonden voor alle geselecteerde medicijnen")
            
        return all_info

    def _generate_questions(self, medicine_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        questions = []
        for atc5, cluster_info in medicine_info.items():
            for med_name, med_info in cluster_info["medications"].items():
                try:
                    question_data = self.question_generator.generate_question(med_name, med_info["info"])
                    if not question_data:
                        continue
                    
                    # Save to database
                    self.db_manager.save_information_and_quiz_question(
                        atc7_code=med_info["atc7"],
                        kenniscategorie=question_data["categorie"],
                        bron_url=med_info["info"].get("url", ""),
                        timestamp_opgeslagen=datetime.now().isoformat(),
                        geëxtraheerde_informatie=med_info["info"].get("relevant_information", ""),
                        llm_info_raw_output=json.dumps(med_info),
                        introductie=question_data["introductie"],
                        vraag=question_data["vraag"],
                        antwoordopties=question_data["antwoordopties"],
                        juiste_antwoord=question_data["antwoord"],
                        uitleg=question_data["uitleg"],
                        llm_quiz_raw_output=json.dumps(question_data)
                    )

                    questions.append({
                        "question": question_data,
                        "metadata": {
                            "medicine_name": med_name,
                            "atc7": med_info["atc7"],
                            "atc5": atc5,
                            "cluster_name": cluster_info["cluster_name"]
                        }
                    })
                except Exception as e:
                    self.db_manager.log_process("error", med_name, '', f"Fout bij genereren vraag: {str(e)}")
                    self.question_generator.stats_manager.add_failed_medication(
                        med_name, 
                        cluster_info["cluster_name"], 
                        str(e)
                    )
        return questions

def main():
    try:
        # Debug mode instellen voor het hele proces
        debug_mode = True  # Zet op False om debug output uit te schakelen
        pipeline = QuizGenerationPipeline(debug_mode=debug_mode)
        pipeline.generate_quiz()
    except Exception as e:
        db_manager = DatabaseManager()
        db_manager.log_process("fatal_error", '', '', str(e))

if __name__ == "__main__":
    main()