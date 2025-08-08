\# Plan de Refactorisation Granulaire – VeriQual-Core



\## 🎯 Objectif

Isoler :

\- Logique métier (`core/`)

\- Entrées/Sorties (`io\_handlers/`)

\- Journalisation (`logger/`)



\## 1. Cartographie initiale (0,5 j)

| Étape | Action | Livrable |

| :--- | :--- | :--- |

| 1.1 | Parcourir `audit\_runner.py` et modules appelés | Tableau Google Sheets avec colonnes : `Fichier`, `Fonction`, `Lignes`, `Type (L/IO/LOG)` |

| 1.2 | Marquer chaque bloc de code avec `# TODO L/IO/LOG` | Version annotée du code |



\## 2. Extraction des I/O (1,5 j)

| Étape | Action | Livrable |

| :--- | :--- | :--- |

| 2.1 | Créer `io\_handlers/file\_ops.py` | Nouveau module |

| 2.2 | Déplacer `check\_file\_\*`, `detect\_\*`, `load\_dataframe\_robustly`, `get\_csv\_files\_in\_directory` | Code déplacé et import mis à jour |

| 2.3 | Dans `AuditRunner`, remplacer appels directs par appels à `io\_handlers` | `audit\_runner.py` nettoyé de la logique I/O |

| 2.4 | Centraliser les chemins et paramètres I/O dans un `config.py` | `config.py` créé et utilisé |



\## 3. Extraction des logs (0,5 j)

| Étape | Action | Livrable |

| :--- | :--- | :--- |

| 3.1 | Créer `logger/logger\_config.py` avec `configure\_logging` | Nouveau module |

| 3.2 | Supprimer toute configuration directe de `logging` dans `AuditRunner` | `audit\_runner.py` propre |

| 3.3 | Uniformiser les niveaux de log (`info`, `warning`, `error`) | Convention de logs documentée |



\## 4. Isolation de la logique métier (1 j)

| Étape | Action | Livrable |

| :--- | :--- | :--- |

| 4.1 | Conserver dans `core/` : `AuditRunner`, `\_normalize\_headers`, `\_detect\_duplicates`, `\_calculate\_quality\_score` | Module `core/audit.py` |

| 4.2 | Déplacer `profile\_dataframe\_columns`, `infer\_semantic\_types`, `detect\_sensitive\_data` vers `core/profiling.py` | Profilage centralisé |

| 4.3 | Supprimer toute ouverture/écriture de fichiers de la logique | Code pur logique métier |



\## 5. Mise à jour des imports et tests (1,5 j)

| Étape | Action | Livrable |

| :--- | :--- | :--- |

| 5.1 | Corriger tous les imports après refactor | Code compilable |

| 5.2 | Mettre à jour `test\_audit\_runner.py` pour tester modules séparés | Tests unitaires séparés |

| 5.3 | Ajouter tests manquants pour F-01 → F-09 | Couverture 100% |



\## 6. Validation finale (0,5 j)

| Étape | Action | Livrable |

| :--- | :--- | :--- |

| 6.1 | Lancer tous les tests automatisés | Rapport `pytest` vert |

| 6.2 | Vérifier fonctionnement CLI et mode batch | Validation manuelle |



---

\*\*⏳ Durée totale estimée : 5,5 jours\*\*

