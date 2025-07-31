flowchart TD
    subgraph Interface["Interface Utilisateur"]
        User[Utilisateur] --> WebApp[VeriQual-WebApp]
    end
    
    subgraph Core["Moteur Central"]
        WebApp --> |Déclenche Audit| Core[VeriQual-Core]
        CSV[Fichier CSV Brut] --> |Analyse| Core
        Core --> |Produit| JSON[Dossier d'Audit JSON]
    end
    
    subgraph Modules["Modules Dépendants"]
        JSON --> |Consommé par| WebApp
        JSON --> |Consommé par| Transform[VeriQual-Transform]
        JSON --> |Consommé par| Report[VeriQual-Report]
        User --> |Définit Règles| WebApp
        WebApp --> |Plan de Transformation| Transform
        CSV --> |Transformé| Transform
        Transform --> |Produit| CleanCSV[Fichier CSV Nettoyé]
    end
    
    classDef interface fill:#90CAF9,stroke:#1976D2,color:#000
    classDef core fill:#A5D6A7,stroke:#388E3C,color:#000
    classDef module fill:#FFE082,stroke:#FFA000,color:#000
    
    class User,WebApp interface
    class Core,JSON,Csv core
    class Transform,Report,CleanCSV module