#VeriQual_Core\audit_runner.py
"""
Module : audit_runner.py

Contient la classe principale AuditRunner responsable d'orchestrer
l'audit de fichiers CSV, ainsi que les classes de configuration associées.

Ce module constitue le cœur du moteur VeriQual-Core.
"""

import os
import logging
from typing import Optional, Dict, List, Any

from pydantic import BaseModel, Field, ValidationError

from tools.common.logs import configure_logging
from tools.common.files import (
    check_file_exists,
    check_file_readable,
    check_file_extension,
    check_file_not_empty,
)


class ChecksConfig(BaseModel):
    check_f01_struct: bool = True
    check_f02_header: bool = True
    check_f03_profil: bool = True
    check_f04_typing: bool = True
    check_f05_pii: bool = True
    check_f06_dupes: bool = True
    check_f07_score: bool = True
    check_f08_weight: bool = True

class FilePropertiesConfig(BaseModel):
    filepath: str
    expected_extension: str = ".csv"
    force_encoding: Optional[str] = None
    force_separator: Optional[str] = None

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
    file_config: FilePropertiesConfig
    checks_config: ChecksConfig = Field(default_factory=ChecksConfig)
    
class AuditRunner:
    def __init__(self, config_dict: dict):
        """
        Initialise le moteur d'audit à partir d'une configuration utilisateur brute.
        """
        self.logger = configure_logging(
            name="veriqual.audit",
            level="INFO",
            log_to_console=True,
            log_to_file=False,
            force=True
            )
        self.logger.info("Logger initialisé pour AuditRunner.")
        try:
           self.config = VeriQualConfigV1(**config_dict)
           self.logger.info("Configuration chargée et validée avec succès.")
        except ValidationError as e:
           self.logger.error("Erreur de validation de la configuration :")
           self.logger.error(e.json(indent=2))
           raise ValueError("Configuration invalide fournie au moteur VeriQual-Core.")
        self.filepath = self.config.file_config.filepath
        self.checks = self.config.checks_config
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

    def run_audit(self) -> dict:
        """
        Lance le processus d’audit et retourne un dictionnaire JSON normalisé.
        """
        self.logger.info("Début de l'audit.")
        if self.checks.check_f01_struct:
            self.logger.info(f"Vérification de l'existence du fichier : {self.filepath}")
            exists, error = check_file_exists(self.filepath)
            if not exists:
                self.logger.error(f"Erreur détectée : {error}")
                self.audit_report["structural_errors"].append(error)
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
                self.audit_report["structural_errors"].append(error)
                return self.audit_report
        
