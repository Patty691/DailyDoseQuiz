#integrationtest
def test_script():
    print("Test: Verwerken van de CSV...")
    df = adjust_csv()
    print("CSV succesvol verwerkt.")
    print(df.head())  

    print("\nTest: Ophalen van clusternamen...")
    atc_cluster_names = name_atc_clusters(df)
    print("Clusternamen succesvol opgehaald.")
    print(f"Voorbeeld clusternamen: {list(atc_cluster_names.items())[:5]}")  

    print("\nTest: Genereren van clusters...")
    atc_clusters = create_clusters(df, {}, atc_cluster_names)
    print("Clusters succesvol gegenereerd.")
    print(f"Aantal clusters: {len(atc_clusters)}")

    print("\nTest: Berekenen van clusterstatistieken...")
    atc_clusters = cluster_statistics(atc_clusters)
    print("Clusterstatistieken succesvol berekend.")
    first_cluster_key = next(iter(atc_clusters))
    print(f"Voorbeeld clusterstatistieken voor {first_cluster_key}: {atc_clusters[first_cluster_key]['statistiek']}")

    print("\nTest: Berekenen van medicijnstatistieken...")
    atc_clusters = medication_statistics(atc_clusters)
    print("Medicijnstatistieken succesvol berekend.")
    print(f"Voorbeeld medicijnstatistieken voor {first_cluster_key}: {atc_clusters[first_cluster_key]['geneesmiddelen'][0]}")

    print("\nTest: Opslaan van JSON-bestand...")
    output_file = "/Users/pattynooijen/Documents/VisualStudioCode/daily_dose_quiz/data/test_data/TestMedicationClustersDatabase.json"
    try:
        with open(output_file, "w", encoding="utf-8") as json_file:
            json.dump(atc_clusters, json_file, ensure_ascii=False, indent=2)
        print(f"Test JSON-bestand succesvol opgeslagen in: {output_file}")
    except Exception as e:
        print(f"Fout bij het opslaan van JSON-bestand: {e}")