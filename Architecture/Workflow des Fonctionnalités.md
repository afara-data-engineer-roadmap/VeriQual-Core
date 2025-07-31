flowchart TD

&nbsp;   subgraph Entrée\["Entrée"]

&nbsp;       CSV\[Fichier CSV Brut]

&nbsp;   end

&nbsp;   

&nbsp;   subgraph Analyse\["Analyse Structurelle"]

&nbsp;       F01\["Vérification Intégrité

&nbsp;       • Existence

&nbsp;       • Permissions

&nbsp;       • Extension CSV"]

&nbsp;       

&nbsp;       F02\["Détection Format

&nbsp;       • Encodage

&nbsp;       • Séparateur

&nbsp;       • Structure Rectangulaire"]

&nbsp;   end

&nbsp;   

&nbsp;   subgraph Traitement\["Traitement des Données"]

&nbsp;       F03\["Normalisation En-têtes

&nbsp;       • Nettoyage noms colonnes

&nbsp;       • Suppression espaces"]

&nbsp;       

&nbsp;       F04\["Profilage Données

&nbsp;       • Métriques par colonne

&nbsp;       • Analyse valeurs"]

&nbsp;       

&nbsp;       F05\["Typage Sémantique

&nbsp;       • Numérique

&nbsp;       • Date

&nbsp;       • Texte"]

&nbsp;       

&nbsp;       F06\["Détection PII/DCP

&nbsp;       • Emails

&nbsp;       • Téléphones

&nbsp;       • Entités sensibles"]

&nbsp;   end

&nbsp;   

&nbsp;   subgraph Qualité\["Analyse de Qualité"]

&nbsp;       F07\["Détection Doublons

&nbsp;       • Lignes exactes

&nbsp;       • Ratio doublons"]

&nbsp;       

&nbsp;       F08\["Calcul Score

&nbsp;       • Agrégation métriques

&nbsp;       • Pondération profils"]

&nbsp;   end

&nbsp;   

&nbsp;   CSV --> F01

&nbsp;   F01 --> F02

&nbsp;   F02 --> F03

&nbsp;   F03 --> F04

&nbsp;   F04 --> F05

&nbsp;   F05 --> F06

&nbsp;   F06 --> F07

&nbsp;   F07 --> F08

&nbsp;   

&nbsp;   F08 --> JSON\[Dossier d'Audit JSON]

&nbsp;   

&nbsp;   classDef input fill:#90CAF9,stroke:#1976D2,color:#000

&nbsp;   classDef analysis fill:#81C784,stroke:#388E3C,color:#000

&nbsp;   classDef treatment fill:#FFE082,stroke:#FFA000,color:#000

&nbsp;   classDef quality fill:#EF9A9A,stroke:#D32F2F,color:#000

&nbsp;   classDef output fill:#CE93D8,stroke:#7B1FA2,color:#000

&nbsp;   

&nbsp;   class CSV input

&nbsp;   class F01,F02 analysis

&nbsp;   class F03,F04,F05,F06 treatment

&nbsp;   class F07,F08 quality

&nbsp;   class JSON output

