# VeriQual/tools/common/files.py

import os
from typing import Tuple, Optional

ValidationResult = Tuple[bool, Optional[str]]

def check_file_exists(filepath: str) -> ValidationResult:
    """
    Vérifie si un fichier existe à l'emplacement spécifié,
    en distinguant les liens symboliques brisés.
    """
    if not os.path.exists(filepath):
        if os.path.islink(filepath):
            return False, (f"Le lien symbolique '{filepath}' est brisé "
                           f"(la cible est introuvable).")
        else:
            return False, (f"Le fichier ou répertoire '{filepath}' est "
                           f"introuvable.")

    if not os.path.isfile(filepath):
        return False, (f"Le chemin '{filepath}' existe mais n'est pas "
                       f"un fichier.")

    return True, None

def check_file_not_empty(filepath: str) -> ValidationResult:
    """Vérifie si un fichier n'est pas vide (taille > 0)."""
    try:
        if os.path.getsize(filepath) == 0:
            return False, f"Le fichier '{filepath}' est vide."
    except OSError as e:
        return False, (f"Impossible de lire la taille du fichier "
                       f"'{filepath}': {e}")
    return True, None

def check_file_extension(filepath: str, expected_extension: str) -> ValidationResult:
    """Vérifie si l'extension du fichier correspond à celle attendue."""
    if not expected_extension.startswith('.'):
        expected_extension = '.' + expected_extension

    _, actual_extension = os.path.splitext(filepath)

    if actual_extension.lower() != expected_extension.lower():
        return False, (f"Extension de fichier invalide. Attendu: "
                       f"'{expected_extension}', Obtenu: '{actual_extension}'.")
    return True, None

def check_file_readable(filepath: str) -> ValidationResult:
    """
    Vérifie si le processus actuel a les permissions de lecture sur le fichier.
    Assumed: file exists and is a file (checked by check_file_exists beforehand).
    """
    try:
        if not os.access(filepath, os.R_OK):
            return False, (f"Permissions de lecture manquantes pour "
                           f"le fichier '{filepath}'.")
        return True, None
    except FileNotFoundError:
        return False, (f"Erreur: Le fichier '{filepath}' est introuvable "
                       f"ou son chemin est invalide lors de la vérification "
                       f"des permissions. (Possible race condition ou oubli "
                       f"de 'check_file_exists').")
    except Exception as e:
        return False, (f"Erreur inattendue lors de la vérification des "
                       f"permissions de '{filepath}': {e}")