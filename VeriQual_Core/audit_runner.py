#VeriQual_Core\audit_runner.py
"""
Module : audit_runner.py

Contient la classe principale AuditRunner responsable d'orchestrer
l'audit de fichiers CSV, ainsi que les classes de configuration associées.

Ce module constitue le cœur du moteur VeriQual-Core.
"""

import os
import logging
from typing import Optional, Dict, List, Any, Tuple

from pydantic import BaseModel, Field, ValidationError

import pandas as pd

import csv 

from tools.common.logs import configure_logging
from tools.common.files import (
    check_file_exists,
    check_file_readable,
    check_file_extension,
    check_file_not_empty,
    detect_file_encoding,
    check_file_empty_content,
    detect_csv_separator,
    load_dataframe_robustly,
)
from tools.common.profiling import profile_dataframe_columns, infer_semantic_types,detect_sensitive_data # Import ajouté

class VeriQualConfigV1(BaseModel):
    scoring_profile: Dict[str, int] = Field(
        default_factory=lambda: {
            "fiabilite_structurelle": 25,
            "completude": 25,
            "validite": 25,
            "unicite": 15,
            "conformite": 10,
        }
    )

    
class AuditRunner:
    def __init__(self, filepath: str, config_dict: Optional[Dict[str, Any]] = None):

        """
        Initialise le moteur d'audit à partir d'une configuration utilisateur brute.
        """
        self.filepath = filepath
        self.logger = configure_logging(
            name="veriqual.audit",
            level="INFO",
            log_to_console=True,
            log_to_file=True,
            force=True
            )
        self.logger.info("Logger initialisé pour AuditRunner.")
        
        if config_dict is None:
            config_dict = {}

        try:
            self.config = VeriQualConfigV1(**config_dict)
            self.logger.info("Configuration chargée et validée avec succès.")
        except ValidationError as e:
            self.logger.error("Erreur de validation de la configuration :")
            self.logger.error(e.json(indent=2))
            raise ValueError("Configuration invalide fournie au moteur VeriQual-Core.")

        self.profile = self.config.scoring_profile
        self.audit_report = {
            "file_info": {
                "file_name": None,
                "file_size_kb": None,
                "total_rows": None,
                "total_columns": None,
                "detected_encoding": None,
                "encoding_confidence": None,
                "detected_separator": None
            },
            "header_info": {
                "has_normalization_alerts": False,
                "header_map": {}
            },
            "quality_score": {
                "global_score": None,
                "profile_used": "Standard (Défaut)",
                "component_scores": {
                    "fiabilite_structurelle": None,
                    "completude": None,
                    "validite": None,
                    "unicite": None,
                    "conformite": None
                }
            },
            "column_analysis": [],
            "sensitive_data_report": {
                    "contains_sensitive_data": False,
                    "detected_columns": []
                    },
            "duplicate_rows_report": {
               "duplicate_row_count": 0,
               "duplicate_row_ratio": 0.0
            },
            "structural_errors": []
        }

    def _normalize_headers(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str], bool]:
        """
        Nettoie les noms de colonnes d’un DataFrame en supprimant les espaces superflus 
        (via strip) et les caractères insécables (\xa0).

        Args:
            df (pd.DataFrame): Le DataFrame à nettoyer.

        Returns:
            Tuple:
                - df nettoyé (avec les nouveaux noms de colonnes),
                - header_map : {original -> nettoyé},
                - has_alerts : True si au moins un nom a été modifié.
        """
        original_columns = df.columns.tolist()
        normalized_columns = []
        header_map = {}
        has_normalization_alerts = False

        for original_name in original_columns:
            # Nettoyage: strip() et remplacement des espaces insécables
            cleaned_name = original_name.strip().replace('\xa0', ' ')
            
            if cleaned_name != original_name:
                # Le nom a été modifié
                header_map[original_name] = cleaned_name
                has_normalization_alerts = True
            
            normalized_columns.append(cleaned_name)
        
        # Assigner les nouvelles colonnes au DataFrame
        df.columns = normalized_columns
        
        return df, header_map, has_normalization_alerts


    def run_audit(self) -> Dict[str, Any]:
        """
        Lance le processus d’audit et retourne un dictionnaire JSON normalisé.
        """
        self.logger.info("Début de l'audit.")
        
        # Analyse structurelle F-01 (toujours active en V1)
        self.logger.info(f"Vérification de l'existence du fichier : {self.filepath}")
        exists, error = check_file_exists(self.filepath)
        if not exists:
            self.logger.error(f"Erreur détectée : {error}")
            self.audit_report["structural_errors"].append({
                "error_code": "file_not_found",
                "message": error,
                "is_blocking": True
            })
            return self.audit_report
        
        # Extraction des métadonnées de base
        file_name = os.path.basename(self.filepath)
        file_size_bytes = os.path.getsize(self.filepath)
        file_size_kb = round(file_size_bytes / 1024, 2)
        
        self.audit_report["file_info"]["file_name"] = file_name
        self.audit_report["file_info"]["file_size_kb"] = file_size_kb
        
        self.logger.info("Vérification des permissions de lecture sur le fichier.")
        readable, error = check_file_readable(self.filepath)
        if not readable:
            self.logger.error(f"Erreur détectée : {error}")
            self.audit_report["structural_errors"].append({
                "error_code": "file_unreadable",
                "message": error,
                "is_blocking": True
            })
            return self.audit_report
        
        self.logger.info("Vérification que le fichier n'est pas vide (taille > 0 octet).")
        not_empty, error = check_file_not_empty(self.filepath)
        if not not_empty:
            self.logger.error(f"Erreur détectée : {error}")
            self.audit_report["structural_errors"].append({
                "error_code": "file_empty_bytes",
                "message": error,
                "is_blocking": True
            })
            return self.audit_report
        
        detected_encoding, encoding_confidence, encoding_error_msg = detect_file_encoding(self.filepath)
        if encoding_error_msg:
            self.logger.error(f"Erreur détectée : {encoding_error_msg}")
            self.audit_report["structural_errors"].append({
                "error_code": "encoding_undetectable",
                "message": encoding_error_msg,
                "is_blocking": True
            })
            return self.audit_report
        
        self.audit_report["file_info"]["detected_encoding"] = detected_encoding
        self.audit_report["file_info"]["encoding_confidence"] = encoding_confidence
        
        is_content_ok, content_error_msg = check_file_empty_content(self.filepath, detected_encoding)
        if not is_content_ok:
            self.logger.error(f"Erreur détectée : {content_error_msg}")
            self.audit_report["structural_errors"].append({
                "error_code": "file_empty_content",
                "message": content_error_msg,
                "is_blocking": True
            })
            return self.audit_report
        
        # F-01: Détection du séparateur
        detected_separator_sniffer, separator_error_msg = detect_csv_separator(self.filepath, detected_encoding)
        if separator_error_msg:
            self.logger.error(f"Erreur détectée : {separator_error_msg}")
            self.audit_report["structural_errors"].append({
                "error_code": "separator_undetectable",
                "message": separator_error_msg,
                "is_blocking": True
            })
            return self.audit_report
        
        # F-01: Chargement robuste du DataFrame et vérification structure rectangulaire
        df, final_separator, df_load_error_msg, df_load_error_code = load_dataframe_robustly(
            self.filepath,
            detected_encoding,
            detected_separator_sniffer # Utilise le séparateur détecté par Sniffer
        )
        
        if df_load_error_msg:
            self.logger.error(f"Erreur détectée : {df_load_error_msg}")
            self.audit_report["structural_errors"].append({
                "error_code": df_load_error_code, # Utilise le code d'erreur direct de load_dataframe_robustly
                "message": df_load_error_msg,
                "is_blocking": True
            })
            return self.audit_report
        
        # Mise à jour du séparateur dans file_info (si un repli a été utilisé)
        # Note: final_separator est le séparateur qui a réellement fonctionné pour Pandas
        self.audit_report["file_info"]["detected_separator"] = final_separator 
        
        # Mise à jour des dimensions du fichier
        self.audit_report["file_info"]["total_rows"] = df.shape[0]
        self.audit_report["file_info"]["total_columns"] = df.shape[1]

        # F-02: Normalisation des En-têtes
        self.logger.info("Démarrage de la normalisation des en-têtes (F-02).")
        df, header_map, has_alerts = self._normalize_headers(df)
        self.audit_report['header_info']['has_normalization_alerts'] = has_alerts
        self.audit_report['header_info']['header_map'] = header_map
        if has_alerts:
            self.logger.info("Des modifications ont été apportées aux en-têtes.")

        # F-03: Profilage de Données
        self.logger.info("Démarrage du profilage des colonnes (F-03).")
        column_profiles = profile_dataframe_columns(df, header_map) # Appel à la fonction de profiling
        self.audit_report["column_analysis"] = column_profiles

        # F-04: Typage Sémantique
        self.logger.info("Démarrage du typage sémantique (F-04).")
        column_profiles = infer_semantic_types(column_profiles, df) # Appel à la fonction de typage sémantique
        self.audit_report["column_analysis"] = column_profiles # Mise à jour avec les types sémantiques
        # F-05: Détection de PII/DCP
        self.logger.info("Démarrage de la détection PII/DCP (F-06).")
        contains_sensitive, pii_columns = detect_sensitive_data(df, column_profiles)
        self.audit_report["sensitive_data_report"]["contains_sensitive_data"] = contains_sensitive
        self.audit_report["sensitive_data_report"]["detected_columns"] = pii_columns
        # F-06: Détection doublons
        self.logger.info("Démarrage de la détection de lignes dupliquées (F-06).")
        duplicate_count, duplicate_ratio = self._detect_duplicates(df)
        self.audit_report["duplicate_rows_report"]["duplicate_row_count"] = duplicate_count
        self.audit_report["duplicate_rows_report"]["duplicate_row_ratio"] = duplicate_ratio

        return self.audit_report
    
    def _detect_duplicates(self, df: pd.DataFrame) -> Tuple[int, float]:
        """
        Détecte les lignes strictement dupliquées dans un DataFrame.

        Args:
            df (pd.DataFrame): Le DataFrame analysé.

        Returns:
            Tuple[int, float]: Nombre de doublons et ratio des doublons.
        """
        if len(df) == 0:
            return 0, 0.0

        duplicate_count = int(df.duplicated().sum())
        duplicate_ratio = round(float(duplicate_count) / len(df), 4)

        return duplicate_count, duplicate_ratio