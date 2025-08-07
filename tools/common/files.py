import os
import chardet
import csv
import pandas as pd
from typing import Optional, Tuple, List
from io import StringIO # Ajout pour lire des échantillons avec pandas

def check_file_exists(filepath: str) -> Tuple[bool, Optional[str]]:
    """Vérifie si un fichier existe."""
    if not os.path.exists(filepath):
        return False, f"Le fichier '{filepath}' est introuvable."
    return True, None

def check_file_readable(filepath: str) -> Tuple[bool, Optional[str]]:
    """Vérifie si un fichier est lisible."""
    if not os.access(filepath, os.R_OK):
        return False, f"Le fichier '{filepath}' n'est pas accessible en lecture (permissions)."
    return True, None

def check_file_extension(filepath: str, expected_extension: str = '.csv') -> Tuple[bool, Optional[str]]:
    """Vérifie si l'extension du fichier correspond à celle attendue."""
    _, ext = os.path.splitext(filepath)
    if ext.lower() != expected_extension.lower():
        return False, f"L'extension du fichier '{ext}' ne correspond pas à l'extension attendue '{expected_extension}'."
    return True, None

def check_file_not_empty(filepath: str) -> Tuple[bool, Optional[str]]:
    """Vérifie si un fichier n'est pas vide (taille > 0 octet)."""
    if os.path.getsize(filepath) == 0:
        return False, f"Le fichier '{filepath}' est vide (0 octet)."
    return True, None

def detect_file_encoding(filepath: str, sample_size: int = 10240) -> Tuple[Optional[str], Optional[float], Optional[str]]:
    """
    Détecte l'encodage d'un fichier en lisant un échantillon.
    Cette version est plus robuste et intègre un mécanisme de repli.
    Elle tente d'abord de lire l'intégralité du fichier avec l'encodage détecté par chardet.
    Si cela échoue, elle passe à une liste d'encodages courants.

    Args:
        filepath (str): Chemin d'accès au fichier.
        sample_size (int): Taille de l'échantillon à lire en octets.

    Returns:
        Tuple[Optional[str], Optional[float], Optional[str]]:
            - encodage détecté (ex: 'utf-8', 'Windows-1252')
            - confiance de la détection (float entre 0 et 1)
            - message d'erreur si l'encodage est indétectable
    """
    # Liste des encodages de repli courants
    common_encodings = ['utf-8', 'latin-1', 'windows-1252']

    try:
        # Tenter la détection initiale avec chardet sur un échantillon
        with open(filepath, 'rb') as f:
            raw_data = f.read(sample_size)
        
        result = chardet.detect(raw_data)
        detected_encoding_chardet = result['encoding']
        confidence = result['confidence']
        
        # Premièrement, tenter de lire le fichier en entier avec l'encodage suggéré par chardet
        if detected_encoding_chardet:
            try:
                with open(filepath, 'r', encoding=detected_encoding_chardet) as f:
                    f.read()
                # Si la lecture réussit, on retourne cet encodage
                return detected_encoding_chardet, confidence, None
            except UnicodeDecodeError:
                # Si la lecture échoue malgré la suggestion de chardet, on continue le repli
                pass

        # Si l'encodage de chardet a échoué, on utilise le mécanisme de repli
        for enc in common_encodings:
            if enc == detected_encoding_chardet:
                continue # Éviter de retester un encodage qui vient d'échouer
            try:
                # Tenter de lire le fichier en entier avec un encodage de la liste
                with open(filepath, 'r', encoding=enc) as f:
                    f.read()
                return enc, 1.0, None # Retourner cet encodage avec une confiance élevée
            except UnicodeDecodeError:
                continue # Continuer au prochain encodage si celui-ci échoue
        
        # Si aucun encodage de repli n'a fonctionné
        return None, None, "Encodage indétectable après toutes les tentatives."
            
    except Exception as e:
        return None, None, f"Erreur lors de la détection de l'encodage : {e}"

def check_file_empty_content(filepath: str, encoding: str) -> Tuple[bool, Optional[str]]:
    """
    Vérifie si le contenu d'un fichier CSV est sémantiquement vide (seulement des espaces, lignes vides).
    """
    try:
        with open(filepath, 'r', encoding=encoding, errors='ignore') as f:
            content = f.read().strip()
            if not content:
                return False, "Le fichier est vide de contenu significatif (seulement des espaces ou lignes vides)."
            # Vérifier si après suppression des lignes vides et espaces, il ne reste rien
            lines = [line.strip() for line in content.splitlines() if line.strip()]
            if not lines:
                return False, "Le fichier ne contient que des lignes vides ou des espaces."
        return True, None
    except Exception as e:
        return False, f"Erreur lors de la vérification du contenu vide : {e}"


def detect_csv_separator(filepath: str, encoding: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Détecte le séparateur de colonnes d'un fichier CSV.
    Si le sniffer détecte un espace et que le fichier semble n'avoir qu'une colonne,
    tente de trouver un meilleur séparateur parmi les plus courants.

    Args:
        filepath (str): Chemin d'accès au fichier.
        encoding (str): Encodage détecté du fichier.

    Returns:
        Tuple[Optional[str], Optional[str]]: Le séparateur détecté et un message d'erreur si applicable.
    """
    try:
        # Lire un échantillon du fichier pour le sniffer et les tentatives de parsing
        with open(filepath, 'r', encoding=encoding, errors='ignore') as file:
            sample = file.read(4096) # Lire les 4 premiers Ko

        # 1. Tentative initiale avec csv.Sniffer
        sniffer = csv.Sniffer()
        
        # Délimiteurs à essayer pour le sniffer. Attention, sniff ne gère pas toujours bien les espaces.
        # On fournit une liste de délimiteurs courants.
        try:
            dialect = sniffer.sniff(sample, delimiters=';, |\t')
            initial_separator = dialect.delimiter
        except csv.Error:
            # Si le sniffer échoue, on part sur une virgule par défaut et on tentera les autres
            initial_separator = ',' 
            
        
        best_separator = initial_separator
        max_columns = 0

        # Tenter de charger un petit DataFrame avec le séparateur initial pour compter les colonnes
        try:
            temp_df_initial = pd.read_csv(StringIO(sample), sep=initial_separator, header=None, nrows=1, encoding=encoding, on_bad_lines='skip')
            max_columns = temp_df_initial.shape[1]
        except Exception:
            # Si le chargement initial échoue, max_columns reste 0
            pass

        # Si le séparateur initial est un espace et qu'il n'y a qu'une seule colonne,
        # ou si le sniffer n'a pas trouvé de séparateur clair (max_columns <= 1)
        # on tente d'autres séparateurs.
        # On inclut l'initial_separator dans la liste pour s'assurer qu'il est toujours considéré.
        common_separators = [';', ',', '\t', '|'] 
        
        # Assurer que le séparateur initial est dans la liste des tentatives, mais sans le dupliquer
        if initial_separator not in common_separators:
            common_separators.insert(0, initial_separator) # Mettre en premier si non présent

        for sep in common_separators:
            try:
                # Tenter de charger avec le nouveau séparateur
                temp_df = pd.read_csv(StringIO(sample), sep=sep, header=None, nrows=1, encoding=encoding, on_bad_lines='skip')
                current_cols = temp_df.shape[1]

                if current_cols > max_columns:
                    max_columns = current_cols
                    best_separator = sep
                elif current_cols == max_columns and sep == ';':
                    # Prioriser le point-virgule si même nombre de colonnes (cas courant en France)
                    best_separator = sep
            except Exception:
                # Ignorer les erreurs de parsing pour ce séparateur, passer au suivant
                pass
        
        # Logique de correction :
        # Si le meilleur résultat est une seule colonne, ce n'est pas une erreur
        # mais une structure de fichier valide (une colonne sans séparateur).
        if max_columns == 1:
            return best_separator, None
        
        # Si le meilleur résultat a plus d'une colonne, mais pas de séparateur trouvé (car max_columns reste 1)
        if max_columns <= 1:
            return best_separator, "Le séparateur optimal n'a pas pu être clairement déterminé."

        return best_separator, None

    except Exception as e:
        return None, f"Erreur inattendue lors de la détection du séparateur : {e}"


def load_dataframe_robustly(filepath: str, encoding: str, separator: str) -> Tuple[Optional[pd.DataFrame], Optional[str], Optional[str], Optional[str]]:
    """
    Charge un DataFrame à partir d'un fichier CSV en utilisant l'encodage et le séparateur fournis.
    Gère les erreurs de parsing et de décodage.

    Args:
        filepath (str): Chemin d'accès au fichier.
        encoding (str): Encodage du fichier.
        separator (str): Séparateur de colonnes à utiliser.

    Returns:
        Tuple[Optional[pd.DataFrame], Optional[str], Optional[str], Optional[str]]:
            - Le DataFrame chargé (ou None en cas d'erreur).
            - Le séparateur réellement utilisé par pandas (sera le 'separator' fourni ici).
            - Message d'erreur (ou None).
            - Code d'erreur (ou None).
    """
    try:
        # Essayer de charger le fichier avec le séparateur et l'encodage détectés
        df = pd.read_csv(filepath, sep=separator, encoding=encoding, on_bad_lines='warn')

        # Vérifier si le fichier est vide après l'en-tête
        if df.empty and pd.read_csv(filepath, sep=separator, encoding=encoding, nrows=0).shape[1] > 0:
            return None, separator, "Le fichier ne contient pas de données après l'en-tête.", "file_empty_after_header"

        return df, separator, None, None

    except pd.errors.ParserError as e:
        return None, separator, f"Erreur de parsing CSV (structure non rectangulaire ou autre) : {e}", "non_rectangular_structure"
    except UnicodeDecodeError as e:
        return None, separator, f"Erreur de décodage Unicode lors du chargement : {e}", "unicode_decode_error_in_load"
    except Exception as e:
        return None, separator, f"Erreur inattendue lors du chargement du DataFrame : {e}", "dataframe_load_error"

def get_csv_files_in_directory(directory_path: str) -> List[str]:
    """
    Liste tous les fichiers CSV (.csv) dans un répertoire donné.

    Args:
        directory_path (str): Le chemin du répertoire à scanner.

    Returns:
        List[str]: Une liste de chemins d'accès complets aux fichiers CSV trouvés.
    """
    csv_files = []
    if not os.path.isdir(directory_path):
        # Vous pouvez ajouter une gestion d'erreur ou un log ici si le chemin n'est pas un répertoire valide
        return csv_files

    for entry in os.listdir(directory_path):
        full_path = os.path.join(directory_path, entry)
        if os.path.isfile(full_path) and full_path.lower().endswith('.csv'):
            csv_files.append(full_path)
    return csv_files
