import sys
import os

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

import unittest
import pandas as pd
import json
from unittest.mock import patch
from src.GenerateMedicationDatabase import (
    adjust_csv,
    get_atc_cluster_name,
    name_atc_clusters,
    create_clusters,
    cluster_statistics,
    medication_statistics,
    generate_medication_database,
)

class TestGenerateMedicationDatabase(unittest.TestCase):
    def setUp(self):
        """
        Set up test data for all tests.
        """
        # Sample CSV-like data
        self.sample_data = pd.DataFrame({
            "ATC-code": ["A02BC02 Pantoprazol (Pantozol ®)", "C07AB02 Metoprolol (Selokeen ®)", "A10BA02 Metformine (Glucient ®)"],
            "2023": ["8.094.200", "7.521.500", "5.304.900"],
            "2022": ["8.046.500", "7.539.700", "5.311.500"]
        })

        # Expected adjusted DataFrame
        self.expected_adjusted_data = pd.DataFrame({
            "ATC-code": ["A02BC02 Pantoprazol (Pantozol ®)", "C07AB02 Metoprolol (Selokeen ®)", "A10BA02 Metformine (Glucient ®)"],
            "2023": ["8.094.200", "7.521.500", "5.304.900"],
            "2022": ["8.046.500", "7.539.700", "5.311.500"],
            "ATC5": ["A02BC", "C07AB", "A10BA"],
            "ATC7": ["A02BC02", "C07AB02", "A10BA02"],
            "geneesmiddel": ["Pantoprazol", "Metoprolol", "Metformine"],
            "merknaam": ["(Pantozol ®)", "(Selokeen ®)", "(Glucient ®)"]
        })

        # Sample ATC cluster names
        self.atc_cluster_names = {
            "A02BC": "Protonpompremmers",
            "C07AB": "Selectieve beta-blokkers",
            "A10BA": "Biguaniden"
        }

        # Expected result for clusters
        self.expected_clusters = {
            "A02BC": {
                "naam": "Protonpompremmers",
                "geneesmiddelen": [
                    {
                        "atc7": "A02BC02",
                        "geneesmiddel": "Pantoprazol",
                        "merknaam": "(Pantozol ®)",
                        "verstrekkingen_huidig": 8094200,
                        "verstrekkingen_vorig": 8046500,
                        "percentage_verstrekkingen": 100.0,
                        "groei_percentage": 0.6
                    }
                ],
                "statistiek": {
                    "aantal_geneesmiddelen": 1,
                    "totaal_verstrekkingen_huidig": 8094200,
                    "totaal_verstrekkingen_vorig": 8046500,
                    "totaal_percentage_verstrekkingen": 100.0,
                    "totaal_groeipercentage": 0.6
                }
            }
        }

    def test_adjust_csv(self):
        """
        Test the adjust_csv function.
        """
        with patch("pandas.read_csv", return_value=self.sample_data):
            result = adjust_csv()
            pd.testing.assert_frame_equal(result, self.expected_adjusted_data)

    @patch("src.GenerateMedicationDatabase.requests.get")
    def test_get_atc_cluster_name(self, mock_get):
        """
        Test the get_atc_cluster_name function with mocked web scraping.
        """
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = "A02BC: Protonpompremmers | Extra info"
        result = get_atc_cluster_name("A02BC")
        self.assertEqual(result, "Protonpompremmers")

    @patch("src.GenerateMedicationDatabase.get_atc_cluster_name")
    def test_name_atc_clusters(self, mock_get_atc_cluster_name):
        """
        Test the name_atc_clusters function.
        """
        mock_get_atc_cluster_name.side_effect = lambda atc5: self.atc_cluster_names[atc5]
        result = name_atc_clusters(self.expected_adjusted_data)
        self.assertEqual(result, self.atc_cluster_names)

    def test_create_clusters(self):
        """
        Test the create_clusters function.
        """
        result = create_clusters(self.expected_adjusted_data, {}, self.atc_cluster_names)
        self.assertIn("A02BC", result)
        self.assertEqual(result["A02BC"]["naam"], "Protonpompremmers")
        self.assertEqual(len(result["A02BC"]["geneesmiddelen"]), 1)

    def test_cluster_statistics(self):
        """
        Test the cluster_statistics function.
        """
        clusters = create_clusters(self.expected_adjusted_data, {}, self.atc_cluster_names)
        result = cluster_statistics(clusters)
        self.assertIn("statistiek", result["A02BC"])
        self.assertEqual(result["A02BC"]["statistiek"]["totaal_groeipercentage"], 0.6)

    def test_medication_statistics(self):
        """
        Test the medication_statistics function.
        """
        clusters = create_clusters(self.expected_adjusted_data, {}, self.atc_cluster_names)
        clusters = cluster_statistics(clusters)
        result = medication_statistics(clusters)
        self.assertIn("percentage_verstrekkingen", result["A02BC"]["geneesmiddelen"][0])
        self.assertEqual(result["A02BC"]["geneesmiddelen"][0]["percentage_verstrekkingen"], 100.0)

    def test_generate_medication_database(self):
        """
        Test the generate_medication_database function.
        """
        result = generate_medication_database(self.expected_adjusted_data, self.atc_cluster_names)
        self.assertIn("A02BC", result)
        self.assertEqual(result["A02BC"]["naam"], "Protonpompremmers")

    def test_save_to_json(self):
        """
        Test saving the generated medication database to a JSON file.
        """
        result = generate_medication_database(self.expected_adjusted_data, self.atc_cluster_names)
        output_file = "/Users/pattynooijen/Documents/VisualStudioCode/daily_dose_quiz/data/test_data/UnitTestMedicationClustersDatabase.json"

        # Ensure the directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        # Save to JSON
        with open(output_file, "w", encoding="utf-8") as json_file:
            json.dump(result, json_file, ensure_ascii=False, indent=2)

        # Verify the file was created and contains the correct data
        with open(output_file, "r", encoding="utf-8") as json_file:
            saved_data = json.load(json_file)

        self.assertEqual(saved_data, result)

        # Clean up the test file
        os.remove(output_file)

if __name__ == "__main__":
    unittest.main()