from typing import Dict, Any, List, Optional
from datetime import datetime
from dotenv import load_dotenv
import os

from SelectMedication import select_medication
from GetMedicineInfo import get_medicine_info
from GenerateQuestion import generate_quiz_question
# Evaluation system temporarily disabled - will be added back later
# from EvaluateQuestion import QuestionEvaluator

"""TODO
controleer of alle functionaliteit gebruikt wordt (zoals gewichten en randomisatie)
beter verdiepen in langchain. wordt nu niet (echt) gebruikt. is het handig om dit in te bouwen, zo ja waarom?
merknaam toevoegen aan output,op meerdere plekken.
 1: nodig om juiste informatie te vinden (bij zelf url plakken)
 2: evaluatie van de vraag (past de vraag bij dit geneesmiddel of was de geneesmiddeltekst bijv. te algemeen (vb. insulines))

 database bouwen
 - al rekening houden met evaluatiefunctie

 evaluatiefunctie bouwen
 -human in the loop


 """

NUM_CLUSTERS = 1      # Aantal ATC5 clusters om te selecteren
NUM_MEDICINES = 1     # Aantal geneesmiddelen om te selecteren per cluster

class QuizGenerationPipeline:
    def __init__(self, debug_mode: bool = True):  # Default debug mode to True
        """
        Initialiseer de quiz generatie pipeline.
        
        Args:
            debug_mode: Of debug informatie moet worden getoond
        """
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
        # Evaluation system temporarily disabled
        # self.evaluator = QuestionEvaluator(model_name=model_name)
        self._setup_chains()

    def _setup_chains(self):
        # Medication Selection Chain
        # This chain selects a medication based on ATC clusters and weights
        self.medication_chain = select_medication

        # Medicine Info Chain
        # This chain fetches and processes medication information
        self.info_chain = get_medicine_info
        
        # For now, we'll handle the chain sequence manually since SequentialChain is deprecated
        self.full_chain = self._create_chain_sequence

    def _create_chain_sequence(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Manual implementation of chain sequence to replace SequentialChain
        
        Args:
            inputs (Dict[str, Any]): Input variables including atc_cluster
            
        Returns:
            Dict[str, Any]: Combined output from all chains
        """
        try:
            # Step 1: Select medication
            medication_result = self.medication_chain(
                atc_cluster=inputs.get("atc_cluster"),
                num_clusters=1,
                num_medicines=1
            )
            
            if "error" in medication_result:
                raise ValueError(f"Medication selection failed: {medication_result['error']}")
            
            # Step 2: Get medicine info
            medicine_info = self.info_chain(medication_result)
            
            # Step 3: Generate quiz question using the complete process
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
            if self.debug_mode:
                print(f"Error in chain sequence: {str(e)}")
            raise

    def generate_questions(self, medicine_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Genereer quizvragen voor alle geselecteerde medicatie.
        
        Args:
            medicine_info: Medicatie informatie uit get_medicine_information
            
        Returns:
            List van gegenereerde vragen met metadata
        """
        questions = []
        
        try:
            for atc5, cluster_info in medicine_info.items():
                for med_name, med_info in cluster_info["medications"].items():
                    if self.debug_mode:
                        print(f"\n{'='*80}")
                        print(f"Genereren vraag over {med_name}")
                        print(f"{'='*80}")
                    
                    try:
                        # Gebruik de complete vraag generatie functie
                        question = generate_quiz_question(
                            medicine_name=med_name,
                            medicine_info=med_info["info"],
                            debug_mode=self.debug_mode
                        )
                        
                        if not question:
                            print(f"Waarschuwing: Geen vraag gegenereerd voor {med_name}")
                            self.stats["failed_medications"].append({
                                "name": med_name,
                                "cluster": cluster_info["cluster_name"],
                                "reason": "Vraag generatie mislukt"
                            })
                            continue
                            
                        self.stats["questions_generated"] += 1
                        
                        # Print de gegenereerde vraag in een duidelijk format
                        if self.debug_mode:
                            print("\nGegenereerde quizvraag:")
                            print(f"{'='*40}")
                            print(f"Introductie:\n{question.final_resolution.introductie}\n")
                            print(f"Vraag:\n{question.final_resolution.vraag}\n")
                            print("Antwoordopties:")
                            for index, option in enumerate(question.final_resolution.antwoordopties, start=1):
                                print(f"{chr(64 + index)}) {option}")
                            print(f"\nJuiste antwoord: {question.final_resolution.antwoord}")
                            print(f"\nUitleg:\n{question.final_resolution.uitleg}")
                            print(f"{'='*40}\n")
                        
                        # Voeg metadata toe
                        question_data = {
                            "question": question,
                            "metadata": {
                                "medicine_name": med_name,
                                "atc7": med_info["atc7"],
                                "brand": med_info["brand"],
                                "atc5": atc5,
                                "cluster_name": cluster_info["cluster_name"]
                            }
                        }
                        
                        questions.append(question_data)
                        
                    except Exception as e:
                        print(f"Fout bij genereren vraag voor {med_name}: {str(e)}")
                        self.stats["failed_medications"].append({
                            "name": med_name,
                            "cluster": cluster_info["cluster_name"],
                            "reason": str(e)
                        })
                    
            return questions
            
        except Exception as e:
            self.stats["errors"].append(str(e))
            raise RuntimeError(f"Fout bij genereren van vragen: {str(e)}")

    def generate_quiz(self, atc_cluster: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Hoofdfunctie die het hele proces van vraag generatie doorloopt.
        Gebruikt de configuratie uit SelectMedication.py.
        
        Args:
            atc_cluster: Optioneel specifiek ATC cluster
            
        Returns:
            List van gegenereerde vragen met metadata
        """
        try:
            # 1. Selecteer medicatie
            selected_meds = self.select_medications(atc_cluster)
            
            # 2. Haal medicatie informatie op
            medicine_info = self.get_medicine_information(selected_meds)
            
            # 3. Genereer vragen
            questions = self.generate_questions(medicine_info)
            
            return questions
            
        except Exception as e:
            if self.debug_mode:
                print(f"\nFout tijdens quiz generatie: {str(e)}")
            return []

    def generate_report(self) -> str:
        """
        Genereer een samenvattend rapport van het vraag generatie proces.
        
        Returns:
            str: Het rapport in leesbare tekst
        """
        end_time = datetime.now()
        duration = end_time - self.stats["start_time"]
        
        report = [
            "\n=== Quiz Generatie Rapport ===",
            f"\nUitvoering gestart op: {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}",
            f"Duur: {duration.total_seconds():.1f} seconden",
            
            "\nVerwerkte gegevens:",
            f"- Clusters verwerkt: {self.stats['clusters_processed']}",
            f"- Totaal medicijnen: {self.stats['total_medications']}",
            f"- Succesvol verwerkt: {self.stats['successful_medications']}",
            f"- Vragen gegenereerd: {self.stats['questions_generated']}",
            
            "\nNiet verwerkte medicijnen:"
        ]
        
        if self.stats["failed_medications"]:
            for med in self.stats["failed_medications"]:
                report.append(f"- {med['name']} (cluster: {med['cluster']})")
                report.append(f"  Reden: {med['reason']}")
        else:
            report.append("- Geen")
            
        if self.stats["errors"]:
            report.extend([
                "\nOpgetreden fouten:",
                "- " + "\n- ".join(self.stats["errors"])
            ])
            
        success_rate = (self.stats["successful_medications"] / self.stats["total_medications"] * 100) if self.stats["total_medications"] > 0 else 0
        
        report.extend([
            f"\nSamenvatting:",
            f"- Succes percentage: {success_rate:.1f}%",
            f"- Gemiddeld aantal vragen per medicijn: {self.stats['questions_generated'] / self.stats['successful_medications']:.1f}" if self.stats['successful_medications'] > 0 else "- Geen vragen gegenereerd",
            "\n=== Einde Rapport ===\n"
        ])
        
        return "\n".join(report)

    def select_medications(self, atc_cluster: Optional[str] = None) -> Dict[str, Any]:
        """
        Selecteer medicatie uit de database.
        Gebruikt de configuratie uit SelectMedication.py.
        
        Args:
            atc_cluster: Optioneel specifiek ATC cluster
            
        Returns:
            Dict met geselecteerde medicatie informatie
        """
        try:
            result = select_medication(
                atc_cluster=atc_cluster,
                num_clusters=NUM_CLUSTERS,
                num_medicines=NUM_MEDICINES
            )
            
            if "error" in result:
                raise ValueError(result["error"])
                
            if self.debug_mode:
                print("\nGeselecteerde medicatie:")
                for cluster in result["selected_clusters"]:
                    print(f"\nCluster: {cluster['naam']} (ATC5: {cluster['atc5_code']}, Gewicht: {cluster['gewicht']:.2f})")
                    for med in cluster["geneesmiddelen"]:
                        print(f"- {med['naam']} (ATC7: {med['atc7']}, Gewicht: {med['gewicht']:.2f})")
                        
            return result
            
        except Exception as e:
            raise RuntimeError(f"Fout bij selecteren medicatie: {str(e)}")

    def get_medicine_information(self, medication: Dict[str, Any]) -> Dict[str, Any]:
        """
        Haal informatie op voor geselecteerde medicatie.
        Slaat medicijnen over waar geen informatie voor gevonden kan worden.
        
        Args:
            medication: Medicatie informatie uit select_medication
            
        Returns:
            Dict met medicatie informatie
        """
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
                            if self.debug_mode:
                                print(f"\nWaarschuwing: Geen informatie gevonden voor {med_name}, dit medicijn wordt overgeslagen")
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
                        if self.debug_mode:
                            print(f"\nFout bij ophalen informatie voor {med_name}: {str(med_error)}")
                        self.stats["failed_medications"].append({
                            "name": med_name,
                            "cluster": cluster["naam"],
                            "reason": str(med_error)
                        })
                        continue
                
                # Alleen clusters toevoegen die medicijnen bevatten
                if cluster_info["medications"]:
                    all_info[cluster["atc5_code"]] = cluster_info
                elif self.debug_mode:
                    print(f"\nWaarschuwing: Geen bruikbare medicijnen gevonden in cluster {cluster['naam']}")
                
            if not all_info:
                raise RuntimeError("Geen informatie gevonden voor alle geselecteerde medicijnen")
                
            return all_info
            
        except Exception as e:
            self.stats["errors"].append(str(e))
            raise RuntimeError(f"Fout bij ophalen medicatie informatie: {str(e)}")

def main():
    """Hoofdfunctie voor het testen van de quiz generatie."""
    try:
        # Initialiseer de pipeline met debug mode aan
        pipeline = QuizGenerationPipeline(debug_mode=True)
        
        # Genereer de quiz (gebruikt configuratie uit SelectMedication.py)
        questions = pipeline.generate_quiz()
        
        # Toon het rapport
        print(pipeline.generate_report())
            
    except Exception as e:
        print(f"\nOnverwachte fout: {str(e)}")

if __name__ == "__main__":
    main() 