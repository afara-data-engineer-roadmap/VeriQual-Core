flowchart LR

&nbsp;   subgraph Core\["VeriQual-Core"]

&nbsp;       direction TB

&nbsp;       Main\["Moteur Principal"]

&nbsp;       

&nbsp;       subgraph Tools\["Outils Communs"]

&nbsp;           Logs\["tools.common.logs

&nbsp;           • configure\_logging()"]

&nbsp;           Files\["tools.common.files

&nbsp;           • file\_integrity()"]

&nbsp;       end

&nbsp;       

&nbsp;       subgraph Deps\["Dépendances Externes"]

&nbsp;           Pandas\["pandas

&nbsp;           • manipulation de données"]

&nbsp;           Chardet\["chardet

&nbsp;           • détection encodage"]

&nbsp;           Spacy\["spaCy

&nbsp;           • détection PII/DCP"]

&nbsp;           Re\["re

&nbsp;           • expressions régulières"]

&nbsp;           Csv\["csv

&nbsp;           • module standard Python"]

&nbsp;       end

&nbsp;   end

&nbsp;   

&nbsp;   Main --> |Utilise| Logs

&nbsp;   Main --> |Utilise| Files

&nbsp;   Main --> |Importe| Pandas

&nbsp;   Main --> |Importe| Chardet

&nbsp;   Main --> |Importe| Spacy

&nbsp;   Main --> |Importe| Re

&nbsp;   Main --> |Importe| Csv

&nbsp;   

&nbsp;   classDef core fill:#A5D6A7,stroke:#388E3C,color:#000

&nbsp;   classDef tools fill:#81C784,stroke:#388E3C,color:#000

&nbsp;   classDef deps fill:#FFB74D,stroke:#EF6C00,color:#000

&nbsp;   

&nbsp;   class Main core

&nbsp;   class Logs,Files tools

&nbsp;   class Pandas,Chardet,Spacy,Re,Csv deps

