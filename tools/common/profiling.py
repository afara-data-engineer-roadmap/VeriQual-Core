# VeriQual/tools/common/profiling.py

import pandas as pd
from typing import List, Dict, Any, Optional, Tuple 
import re 


def profile_dataframe_columns(df: pd.DataFrame, header_map: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """
    Calcule un ensemble de métriques objectives et statistiques pour chaque colonne d'un DataFrame (F-03).

    Cette fonction étend le profilage de base pour inclure des métriques spécifiques
    aux types de données (numériques, textuelles, dates), et assure la traçabilité
    des noms de colonnes originaux via le header_map. Elle ne réalise PAS le typage sémantique.

    Args:
        df (pd.DataFrame): Le DataFrame à profiler.
        header_map (Optional[Dict[str, str]]): Un dictionnaire de mappage {original_name: normalized_name}
                                                pour récupérer les noms de colonnes originaux.
                                                Si None, le nom original est le nom actuel de la colonne.

    Returns:
        List[Dict[str, Any]]: Une liste de dictionnaires, chaque dictionnaire représentant le profil d'une colonne.
                              Chaque profil contient:
                                - column_name (nom normalisé actuel)
                                - original_name (nom avant normalisation, si applicable)
                                - pandas_dtype (type de données interne de Pandas)
                                - metrics (dictionnaire des métriques calculées)
    """
    profile = []
    total_rows = len(df)

    # Créer un mappage inverse pour trouver le nom original à partir du nom normalisé
    reverse_header_map = {v: k for k, v in header_map.items()} if header_map else {}

    for col_name in df.columns:
        col_data = df[col_name]

        # Métriques de base (applicables à tous les types de colonnes)
        missing_ratio = col_data.isna().sum() / total_rows if total_rows > 0 else 0.0
        unique_count = col_data.nunique(dropna=False) 
        unique_ratio = unique_count / total_rows if total_rows > 0 else 0.0

        type_specific_metrics = {}
        pandas_dtype = str(col_data.dtype)

        # Métriques pour colonnes numériques
        if pd.api.types.is_numeric_dtype(col_data):
            numeric_stats = col_data.describe().to_dict()
            type_specific_metrics = {
                "min": round(numeric_stats.get('min', float('nan')), 4),
                "max": round(numeric_stats.get('max', float('nan')), 4),
                "mean": round(numeric_stats.get('mean', float('nan')), 4),
                "std": round(numeric_stats.get('std', float('nan')), 4),
                "median": round(col_data.median(), 4) if not col_data.empty and col_data.count() > 0 else float('nan'),
                "q1": round(col_data.quantile(0.25), 4) if not col_data.empty and col_data.count() > 0 else float('nan'),
                "q3": round(col_data.quantile(0.75), 4) if not col_data.empty and col_data.count() > 0 else float('nan'),
            }
        # Métriques pour colonnes catégorielles/texte (objets ou strings)
        elif pd.api.types.is_object_dtype(col_data) or pd.api.types.is_string_dtype(col_data):
            top_frequencies = col_data.value_counts(normalize=True).head(5).to_dict()
            type_specific_metrics["top_frequencies"] = {str(k): round(v, 4) for k, v in top_frequencies.items()}
            type_specific_metrics["most_frequent_value"] = str(col_data.mode()[0]) if not col_data.mode().empty else None
            
        # Métriques pour colonnes de date/heure
        elif pd.api.types.is_datetime64_any_dtype(col_data):
            try:
                col_data_dt = pd.to_datetime(col_data, errors='coerce')
                if not col_data_dt.dropna().empty:
                    type_specific_metrics = {
                        "min_date": str(col_data_dt.min()),
                        "max_date": str(col_data_dt.max()),
                    }
                else:
                    type_specific_metrics = {
                        "min_date": None,
                        "max_date": None,
                    }
            except Exception:
                pass 


        profile.append({
            "column_name": col_name,
            "original_name": reverse_header_map.get(col_name, col_name), # Récupère le nom original
            "pandas_dtype": pandas_dtype, # Ajout du dtype Pandas
            "metrics": {
                "missing_values_ratio": round(missing_ratio, 4),
                "unique_values_ratio": round(unique_ratio, 4),
                "total_unique_values": int(unique_count), 
                **type_specific_metrics # Ajouter les métriques spécifiques au type
            }
        })
    return profile


def infer_semantic_types(profiled_columns: List[Dict[str, Any]], df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Interprète les métriques de profilage et le contenu du DataFrame pour déduire le type
    de données métier le plus probable pour chaque colonne (F-04).

    Args:
        profiled_columns (List[Dict[str, Any]]): Liste des profils de colonnes générés par profile_dataframe_columns.
        df (pd.DataFrame): Le DataFrame original (ou normalisé) pour un accès direct aux données.

    Returns:
        List[Dict[str, Any]]: La liste des profils de colonnes complétée avec le champ "data_type_detected".
    """
    # Liste des formats de date courants à essayer
    COMMON_DATE_FORMATS = [
        '%Y-%m-%d',        # 2023-01-15
        '%d/%m/%Y',        # 15/01/2023
        '%m/%d/%Y',        # 01/15/2023
        '%Y/%m/%d',        # 2023/01/15
        '%Y-%m-%d %H:%M:%S', # 2023-01-15 14:30:00
        '%d/%m/%Y %H:%M:%S', # 15/01/2023 14:30:00
        '%m/%d/%Y %H:%M:%S', # 01/15/2023 14:30:00
    ]

    for col_profile in profiled_columns:
        col_name = col_profile["column_name"]
        col_data = df[col_name] 

        data_type = "Inconnu" # Valeur par défaut pour les types non gérés

        if pd.api.types.is_integer_dtype(col_data):
            data_type = "Entier"
        elif pd.api.types.is_float_dtype(col_data):
            data_type = "Flottant"
        elif pd.api.types.is_datetime64_any_dtype(col_data):
            data_type = "Date"
        elif pd.api.types.is_object_dtype(col_data) or pd.api.types.is_string_dtype(col_data):
            # Tenter de déduire le type Date avec des formats spécifiques pour éviter les warnings
            is_date_candidate = False
            for fmt in COMMON_DATE_FORMATS:
                try:
                    col_as_date = pd.to_datetime(col_data, format=fmt, errors="coerce")
                    # Heuristique: si plus de 50% des valeurs sont des dates valides, inférer comme Date
                    if col_as_date.count() / len(col_data) > 0.5 and not col_as_date.dropna().empty:
                        data_type = "Date"
                        is_date_candidate = True
                        break # Un format a fonctionné, on sort de la boucle des formats
                except Exception: # Capture les erreurs inattendues lors de la conversion avec format spécifique
                    continue # Essayer le format suivant
            
            if not is_date_candidate:
                # Si aucun format spécifique n'a fonctionné, ou si le ratio est trop bas,
                # on tente une dernière fois sans format spécifique (où le warning pourrait apparaître si non géré)
                # ou on considère directement que c'est du texte.
                # Pour éviter le warning ici, on peut décider que si les formats courants n'ont pas marché,
                # c'est du texte, ou on peut le laisser tenter et gérer le warning globalement si nécessaire.
                # Pour V1, on va dire que si les formats courants ne marchent pas, c'est Texte.
                data_type = "Texte"
        else:
            # Pour les autres dtypes (ex: boolean, category), par défaut à Texte pour V1
            data_type = "Texte" 
        
        # Ajouter le type sémantique détecté au profil de la colonne
        col_profile["data_type_detected"] = data_type
        
    return profiled_columns


def detect_sensitive_data(df: pd.DataFrame, column_profiles: List[Dict[str, Any]]) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Scanne le contenu du DataFrame pour identifier la présence potentielle de Données Personnelles (PII/DCP) (F-05).

    Args:
        df (pd.DataFrame): Le DataFrame à analyser.
        column_profiles (List[Dict[str, Any]]): Liste des profils de colonnes (avec data_type_detected).

    Returns:
        Tuple[bool, List[Dict[str, Any]]]:
            - True si des données sensibles sont détectées, False sinon.
            - Liste de dictionnaires des colonnes détectées et des types de PII.
    """
    EMAIL_REGEX = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
    PHONE_REGEX = r"\b(?:\+33|0)[1-9](?:[\s.-]?\d{2}){4}\b"
    # Ajout de la regex pour NIR (Numéro d'Inscription au Répertoire) - Exemple simplifié
    # Un NIR français a 13 chiffres + 2 clés, ou 15 chiffres.
    # Regex simplifiée: commence par 1 ou 2, puis 12 chiffres (pour couvrir les 13+2 et 15)
    # Pour une validation stricte, il faudrait une regex plus complexe et une validation de la clé.
    NIR_REGEX = r"^[12]\d{12}$" 


    detected_columns = []

    for col in column_profiles:
        # On ne scanne que les colonnes qui ont été détectées comme du texte
        if col.get("data_type_detected") != "Texte":
            continue 

        col_name = col["column_name"]
        # Convertir la colonne en string pour appliquer les regex, gérer les NaN
        col_data_str = df[col_name].astype(str).fillna('') 

        pii_types = []
        if col_data_str.str.contains(EMAIL_REGEX, regex=True, na=False).any():
            pii_types.append("EMAIL")
        if col_data_str.str.contains(PHONE_REGEX, regex=True, na=False).any():
            pii_types.append("PHONE")
        if col_data_str.str.contains(NIR_REGEX, regex=True, na=False).any(): 
            pii_types.append("NIR")

        if pii_types:
            detected_columns.append({
                "column_name": col_name,
                "pii_types": pii_types
            })

    contains_sensitive_data = len(detected_columns) > 0
    return contains_sensitive_data, detected_columns
