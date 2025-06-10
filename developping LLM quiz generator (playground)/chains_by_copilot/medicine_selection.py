from typing import Dict, Any, List, Optional
import random
import json
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import JsonOutputParser
from langchain.prompts import PromptTemplate

class MedicineSelectionChain:
    """Chain voor het selecteren van geneesmiddelen op basis van gewichten."""
    
    def __init__(self, database_path: str = "data/MedicationClustersDatabase.json"):
        """
        Initialiseer de medicine selection chain.
        
        Args:
            database_path: Pad naar de medicatie database
        """
        self.database_path = database_path
        self.chain = RunnablePassthrough.assign(
            selected_clusters=self._select_clusters,
            selected_medicines=self._select_medicines
        )
    
    def _load_data(self) -> Dict[str, Any]:
        """Laad de medicatie database."""
        try:
            with open(self.database_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Database niet gevonden: {self.database_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Ongeldige JSON in database: {e}")

    def _weighted_selection_unique(
        self, 
        choices: List[str], 
        weights: List[float], 
        k: int
    ) -> List[str]:
        """
        Selecteer unieke items op basis van gewichten.
        
        Args:
            choices: Lijst van items om uit te kiezen
            weights: Lijst van gewichten voor elk item
            k: Aantal te selecteren items
            
        Returns:
            Lijst van geselecteerde items
        """
        if not choices or not weights or k < 1:
            return []
            
        selected = []
        available_indices = list(range(len(choices)))
        
        for _ in range(min(k, len(choices))):
            if not available_indices:
                break
                
            current_weights = [weights[i] for i in available_indices]
            total_weight = sum(current_weights)
            
            if total_weight <= 0:
                break
                
            normalized_weights = [w/total_weight for w in current_weights]
            chosen_idx = random.choices(available_indices, normalized_weights, k=1)[0]
            selected.append(choices[chosen_idx])
            available_indices.remove(chosen_idx)
        
        return selected

    def _select_clusters(
        self, 
        atc_clusters: Dict[str, Any], 
        num_clusters: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Selecteer ATC5 clusters op basis van gewichten.
        
        Args:
            atc_clusters: De medicatie clusters data
            num_clusters: Aantal te selecteren clusters
            
        Returns:
            Lijst van geselecteerde clusters met hun details
        """
        valid_clusters = []
        weights = []
        
        for atc5_code, cluster in atc_clusters.items():
            if not all(len(med.get("atc7", "")) == 7 
                      for med in cluster.get("geneesmiddelen", [])):
                continue
                
            valid_clusters.append(atc5_code)
            weights.append(cluster["statistiek"]["gewicht"])
        
        selected_atc5 = self._weighted_selection_unique(valid_clusters, weights, num_clusters)
        
        return [
            {
                "atc5_code": code,
                "naam": atc_clusters[code]["naam"],
                "gewicht": atc_clusters[code]["statistiek"]["gewicht"],
                "geneesmiddelen": atc_clusters[code]["geneesmiddelen"]
            }
            for code in selected_atc5
        ]

    def _select_medicines(
        self, 
        cluster: Dict[str, Any], 
        num_medicines: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Selecteer geneesmiddelen uit een cluster.
        
        Args:
            cluster: Cluster informatie
            num_medicines: Aantal te selecteren geneesmiddelen
            
        Returns:
            Lijst van geselecteerde geneesmiddelen met hun details
        """
        medicines = cluster["geneesmiddelen"]
        med_codes = [med["atc7"] for med in medicines]
        weights = [med["gewicht"] for med in medicines]
        
        total_weight = sum(weights)
        if total_weight <= 0:
            return []
            
        normalized_weights = [w/total_weight for w in weights]
        
        selected_codes = random.choices(
            population=med_codes,
            weights=normalized_weights,
            k=num_medicines
        )
        
        return [
            next(
                {
                    "atc7": med["atc7"],
                    "naam": med["geneesmiddel"],
                    "merknaam": med.get("merknaam", ""),
                    "gewicht": med["gewicht"]
                }
                for med in medicines if med["atc7"] == code
            )
            for code in selected_codes
        ]

    def invoke(
        self, 
        atc_cluster: Optional[str] = None, 
        num_clusters: int = 1, 
        num_medicines: int = 1
    ) -> Dict[str, Any]:
        """
        Hoofdfunctie voor het selecteren van medicatie.
        
        Args:
            atc_cluster: Optioneel specifiek ATC cluster
            num_clusters: Aantal te selecteren clusters
            num_medicines: Aantal geneesmiddelen per cluster
            
        Returns:
            Dict met geselecteerde medicatie details
        """
        try:
            atc_clusters = self._load_data()
            
            if atc_cluster:
                if atc_cluster not in atc_clusters:
                    raise ValueError(f"ATC cluster {atc_cluster} niet gevonden")
                selected_clusters = [{
                    "atc5_code": atc_cluster,
                    "naam": atc_clusters[atc_cluster]["naam"],
                    "gewicht": atc_clusters[atc_cluster]["statistiek"]["gewicht"],
                    "geneesmiddelen": atc_clusters[atc_cluster]["geneesmiddelen"]
                }]
            else:
                selected_clusters = self._select_clusters(atc_clusters, num_clusters)
            
            result = {
                "selected_clusters": []
            }
            
            for cluster in selected_clusters:
                selected_medicines = self._select_medicines(cluster, num_medicines)
                
                cluster_info = {
                    "atc5_code": cluster["atc5_code"],
                    "naam": cluster["naam"],
                    "gewicht": cluster["gewicht"],
                    "geneesmiddelen": selected_medicines
                }
                
                result["selected_clusters"].append(cluster_info)
            
            return result
            
        except Exception as e:
            raise RuntimeError(f"Fout bij selecteren medicatie: {str(e)}")

if __name__ == "__main__":
    # Test de chain
    chain = MedicineSelectionChain()
    result = chain.invoke(num_clusters=2, num_medicines=1)
    
    # Print resultaten
    print("\nGeselecteerde medicatie clusters en geneesmiddelen:")
    print("=" * 70)
    
    for cluster in result["selected_clusters"]:
        print(f"\nCluster: {cluster['naam']} ({cluster['atc5_code']})")
        print(f"Cluster gewicht: {cluster['gewicht']:.1f}")
        
        for med in cluster["geneesmiddelen"]:
            print(f"\n  Geneesmiddel: {med['naam']} ({med['atc7']})")
            print(f"  Gewicht: {med['gewicht']:.1f}")
            if med['merknaam']:
                print(f"  Merknaam: {med['merknaam']}")
        
        print("-" * 70) 