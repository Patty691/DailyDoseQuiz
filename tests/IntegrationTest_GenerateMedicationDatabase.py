import sys
import os

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

import json
from src.GenerateMedicationDatabase import (
    adjust_csv,
    name_atc_clusters,
    generate_medication_database,
)

def test_integration():
    """
    Integration test for the full workflow of GenerateMedicationDatabase.py.
    """
    try:
        print("Test: Processing the CSV...")
        df = adjust_csv()
        print("CSV successfully processed.")
        print(df.head())  # Display the first few rows for verification

        print("\nTest: Fetching cluster names...")
        atc_cluster_names = name_atc_clusters(df)
        print("Cluster names successfully fetched.")
        print(f"Sample cluster names: {list(atc_cluster_names.items())[:5]}")  # Display the first 5 cluster names

        print("\nTest: Generating the medication database...")
        atc_clusters = generate_medication_database(df, atc_cluster_names)
        print("Medication database successfully generated.")
        print(f"Number of clusters: {len(atc_clusters)}")

        print("\nTest: Saving the JSON file...")
        output_file = "/Users/pattynooijen/Documents/VisualStudioCode/daily_dose_quiz/data/test_data/TestMedicationClustersDatabase.json"
        with open(output_file, "w", encoding="utf-8") as json_file:
            json.dump(atc_clusters, json_file, ensure_ascii=False, indent=2)
        print(f"Test JSON file successfully saved at: {output_file}")

        print("\nIntegration test completed successfully!")

    except Exception as e:
        print(f"Error during integration test: {e}")

if __name__ == "__main__":
    test_integration()