Documentation: Weighted Medication Usage for Quiz Question Generation

A. Generating a Weighted Medication Usage List as a Source for Quiz Questions

1. Load Data

Load the top 500 medications and their growth rates during the previous year from the GIP database. Yearly updated in may.

2023:
https://www.gipdatabank.nl/databank?infotype=g&label=00-totaal&tabel_d_00-totaal=B_01-basis&tabel_g_00-totaal=R_46_top500_atclaatst&tabel_h_00-totaal=B_01-basis&geg=vs&spec=&item=

(geneesmiddelen, top 500, uitgiftes, geen specificatie)

2. Classification of Medications

Medications are classified at the atc level.

All ATC7 data is nested within its corresponding atc category.

3. atc Cluster Naming

The atc code is supplemented with the corresponding atc cluster name.

The name is retrieved from a predefined dictionary.

4. Weighting of Top 500 and Growth Medications at atc Level

Percentages of usage. 

Growth Medications: Medications with a high growth rate (% from second last to last year).


5. Weighting at ATC7 Level Within a Cluster

Percentages of usage within the cluster.

6. Output Storage

The structured output is stored in a JSON file. 




B. Selection of a Medication for Quiz Question Generation

1. Weighted Random Selection at atc Level

80% of selections come from the usage percentage. 

20% of selections come from Growth Medications.

Intelligent Tracking & Variation Mechanism:

Cooldown Mechanism: Reduces repetition of previously selected medications.

User Performance-Based Selection: Difficult topics appear more frequently if a user struggles with them.

2. Weighted Random Selection at ATC7 Level

A medication is selected randomly based on its calculated weight within its atc cluster.

3. Automated Question Generation

Questions are generated using an AI prompt.

Categories are pre-defined to ensure relevance.

Information is sourced exclusively from Apotheek.nl.

The output follows a structured format.

4. Output Storage

The structured quiz questions are stored in a JSON file for evaluation further use.

