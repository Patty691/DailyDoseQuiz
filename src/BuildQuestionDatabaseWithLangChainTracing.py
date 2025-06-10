import os
import sqlite3
import json
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional

# LangChain tracing activeren
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "VUL_HIER_JE_LSMITH_API_KEY_IN")

from SelectMedication import select_medication
from GetMedicineInfo import get_medicine_info
from GenerateQuestion import generate_quiz_question

NUM_CLUSTERS = 1
NUM_MEDICINES = 1

DB_PATH = "quiz_questions_tracing.db"
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "../schema.sql")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Lees en voer het schema.sql bestand uit
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()
        c.executescript(schema_sql)
    conn.commit()
    conn.close()

init_db()

class QuizGenerationPipelineWithTracing:
    def __init__(self, debug_mode: bool = True):
        load_dotenv()
        self.debug_mode = debug_mode
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
        self._setup_chains()

    def _setup_chains(self):
        self.medication_chain = select_medication
        self.info_chain = get_medicine_info
        self.full_chain = self._create_chain_sequence

    def log_process(self, event_type, medicine, category, message):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO process_logs (event_type, medicine, category, message, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (event_type, medicine, category, message, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def save_quiz_question(self, medicine, category, question, correct_answer, wrong_answers, llm_raw_output, atc7, brand, atc5, cluster_name):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO quiz_questions (medicine, category, question, correct_answer, wrong_answers, llm_raw_output, atc7, brand, atc5, cluster_name, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            medicine, category, question, correct_answer, json.dumps(wrong_answers), llm_raw_output, atc7, brand, atc5, cluster_name, datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()

    def _create_chain_sequence(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        try:
            medication_result = self.medication_chain(
                atc_cluster=inputs.get("atc_cluster"),
                num_clusters=1,
                num_medicines=1
            )
            if "error" in medication_result:
                raise ValueError(f"Medication selection failed: {medication_result['error']}")
            medicine_info = self.info_chain(medication_result)
            quiz_question = generate_quiz_question(
                medicine_name=medication_result["naam"],
                medicine_info=medicine_info,
                debug_mode=self.debug_mode
            )
            return {
                "selected_medication": medication_result,
                "medicine_info": medicine_info,
                "quiz_question": quiz_question
            }
        except Exception as e:
            self.log_process("error", inputs.get("atc_cluster", ""), "", f"Error in chain sequence: {str(e)}")
            raise

    def generate_questions(self, medicine_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        questions = []
        try:
            for atc5, cluster_info in medicine_info.items():
                for med_name, med_info in cluster_info["medications"].items():
                    try:
                        question = generate_quiz_question(
                            medicine_name=med_name,
                            medicine_info=med_info["info"],
                            debug_mode=self.debug_mode
                        )
                        if not question:
                            self.log_process("warning", med_name, "", "Geen vraag gegenereerd")
                            self.stats["failed_medications"].append({
                                "name": med_name,
                                "cluster": cluster_info["cluster_name"],
                                "reason": "Vraag generatie mislukt"
                            })
                            continue
                        self.stats["questions_generated"] += 1
                        # Structured output extractie
                        try:
                            q = question.final_resolution
                            # Bouw een platte dict met alle relevante velden
                            llm_structured = {
                                "introductie": getattr(q, "introductie", ""),
                                "vraag": getattr(q, "vraag", ""),
                                "antwoordopties": getattr(q, "antwoordopties", []),
                                "antwoord": getattr(q, "antwoord", ""),
                                "uitleg": getattr(q, "uitleg", ""),
                                "categorie": getattr(q, "categorie", "")
                            }
                            self.save_quiz_question(
                                medicine=med_name,
                                category=llm_structured["categorie"],
                                question=llm_structured["vraag"],
                                correct_answer=llm_structured["antwoord"],
                                wrong_answers=llm_structured["antwoordopties"],
                                llm_raw_output=json.dumps(llm_structured),
                                atc7=med_info["atc7"],
                                brand=med_info.get("brand", ""),
                                atc5=atc5,
                                cluster_name=cluster_info["cluster_name"]
                            )
                        except Exception as parse_error:
                            self.log_process("error", med_name, '', f"Fout bij opslaan quizvraag: {str(parse_error)}")
                        question_data = {
                            "question": question,
                            "metadata": {
                                "medicine_name": med_name,
                                "atc7": med_info["atc7"],
                                "brand": med_info.get("brand", ""),
                                "atc5": atc5,
                                "cluster_name": cluster_info["cluster_name"]
                            }
                        }
                        questions.append(question_data)
                    except Exception as e:
                        self.log_process("error", med_name, '', f"Fout bij genereren vraag: {str(e)}")
                        self.stats["failed_medications"].append({
                            "name": med_name,
                            "cluster": cluster_info["cluster_name"],
                            "reason": str(e)
                        })
            return questions
        except Exception as e:
            self.stats["errors"].append(str(e))
            self.log_process("error", '', '', f"Fout bij genereren van vragen: {str(e)}")
            raise RuntimeError(f"Fout bij genereren van vragen: {str(e)}")

    def generate_quiz(self, atc_cluster: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            selected_meds = self.select_medications(atc_cluster)
            medicine_info = self.get_medicine_information(selected_meds)
            questions = self.generate_questions(medicine_info)
            return questions
        except Exception as e:
            self.log_process("error", '', '', f"Fout tijdens quiz generatie: {str(e)}")
            return []

    def select_medications(self, atc_cluster: Optional[str] = None) -> Dict[str, Any]:
        try:
            result = select_medication(
                atc_cluster=atc_cluster,
                num_clusters=NUM_CLUSTERS,
                num_medicines=NUM_MEDICINES
            )
            return result
        except Exception as e:
            self.log_process("error", '', '', f"Fout bij selecteren medicatie: {str(e)}")
            raise RuntimeError(f"Fout bij selecteren medicatie: {str(e)}")

    def get_medicine_information(self, medication: Dict[str, Any]) -> Dict[str, Any]:
        try:
            all_info = {}
            for cluster in medication["selected_clusters"]:
                self.stats["clusters_processed"] += 1
                cluster_info = {
                    "cluster_name": cluster["naam"],
                    "medications": {}
                }
                for med in cluster["geneesmiddelen"]:
                    self.stats["total_medications"] += 1
                    med_name = med["naam"].lower()
                    try:
                        info = get_medicine_info(med_name, cluster["naam"])
                        if not info or "Geen informatie beschikbaar" in info:
                            self.log_process("warning", med_name, '', "Geen informatie gevonden, medicijn overgeslagen")
                            self.stats["failed_medications"].append({
                                "name": med_name,
                                "cluster": cluster["naam"],
                                "reason": "Geen informatie beschikbaar"
                            })
                            continue
                        cluster_info["medications"][med_name] = {
                            "info": info,
                            "atc7": med["atc7"],
                            "brand": med.get("brand", "")
                        }
                        self.stats["successful_medications"] += 1
                    except Exception as med_error:
                        self.log_process("error", med_name, '', f"Fout bij ophalen info: {str(med_error)}")
                        self.stats["failed_medications"].append({
                            "name": med_name,
                            "cluster": cluster["naam"],
                            "reason": str(med_error)
                        })
                        continue
                if cluster_info["medications"]:
                    all_info[cluster["atc5_code"]] = cluster_info
            if not all_info:
                self.log_process("error", '', '', "Geen informatie gevonden voor alle geselecteerde medicijnen")
                raise RuntimeError("Geen informatie gevonden voor alle geselecteerde medicijnen")
            return all_info
        except Exception as e:
            self.stats["errors"].append(str(e))
            self.log_process("error", '', '', f"Fout bij ophalen medicatie informatie: {str(e)}")
            raise RuntimeError(f"Fout bij ophalen medicatie informatie: {str(e)}")

def main():
    try:
        pipeline = QuizGenerationPipelineWithTracing(debug_mode=True)
        pipeline.generate_quiz()
        # Geen print, alles traceerbaar via database en LangChain tracing
    except Exception as e:
        # Log onverwachte fout
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO process_logs (event_type, medicine, category, message, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', ("fatal_error", '', '', str(e), datetime.now().isoformat()))
        conn.commit()
        conn.close()

if __name__ == "__main__":
    main()