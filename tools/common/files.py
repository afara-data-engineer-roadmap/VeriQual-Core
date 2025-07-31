# VeriQual/tools/common/files.py

import os
import chardet
import csv # Added for csv.Sniffer
import pandas as pd
from typing import Tuple, Optional,List,Dict,Any

_DEFAULT_CONFIDENCE_THRESHOLD = 0.8
_ENCODINGS_FALLBACK = ['utf-8', 'latin1', 'windows-1252'] 
_SAMPLE_SIZE_BYTES = 131072 # 128 KB
_PANDAS_SEPARATORS_FALLBACK = [',', ';', '\t']


ValidationResult = Tuple[bool, Optional[str]]

def check_file_exists(filepath: str) -> ValidationResult:
    """
    Vérifie si un fichier existe à l'emplacement spécifié,
    en distinguant les liens symboliques brisés.

    Returns:
        Tuple[bool, Optional[str]]: (succès, message d'erreur éventuel)
    """
    if not os.path.exists(filepath):
        if os.path.islink(filepath):
            return False, (
                f"[check_file_exists] Le lien symbolique '{filepath}' est brisé "
                f"(la cible est introuvable)."
            )
        return False, (
            f"[check_file_exists] Le fichier ou répertoire '{filepath}' est introuvable."
        )

    if not os.path.isfile(filepath):
        return False, (
           f"[check_file_exists] Le chemin '{filepath}' existe mais n'est pas un fichier."
        )

    return True, None

def check_file_not_empty(filepath: str) -> ValidationResult:
    """
    Vérifie si un fichier n'est pas vide.
    
    Returns:
        Tuple[bool, Optional[str]]: (succès, message d'erreur éventuel)
    """

    try:
        if os.path.getsize(filepath) == 0:
            return False, f"[check_file_not_empty] Le fichier '{filepath}' est vide."
    except OSError as e:
        return False, (f"[check_file_not_empty] Impossible de lire la taille du fichier"
                       f" '{filepath}': {e}")
    return True, None

def check_file_extension(filepath: str, expected_extension: str) -> ValidationResult:
    """
    Vérifie si l'extension du fichier correspond à celle attendue.
    
    Returns:
        Tuple[bool, Optional[str]]: (succès, message d'erreur éventuel)
    """    
    if not expected_extension.startswith('.'):
        expected_extension = '.' + expected_extension

    _, actual_extension = os.path.splitext(filepath)

    if actual_extension.lower() != expected_extension.lower():
        return False, (f"[check_file_extension] Extension de fichier invalide. Attendu: "
                       f"' {expected_extension}', Obtenu: '{actual_extension}'.")
    return True, None

def check_file_readable(filepath: str) -> ValidationResult:
    """
    Vérifie si le processus actuel a les permissions de lecture sur le fichier.
    Assumed: file exists and is a file (checked by check_file_exists beforehand).
    """
    try:
        if not os.access(filepath, os.R_OK):
            return False, (f"[check_file_readable] Permissions de lecture manquantes "
                           f"pour le fichier '{filepath}'.")
        return True, None
    except FileNotFoundError:
        return False, (f"[check_file_readable] Le fichier '{filepath}' est  "
                       f" introuvable ou le chemin est incorrect lors de la "
                       f"vérification des permissions. ( race condition ou "
                       f"oubli de 'check_file_exists').")
    except Exception as e:
        return False, (f"[check_file_readable] Erreur inattendue lors de la "
                       f"vérification des permissions de '{filepath}': {e}")


def detect_file_encoding(filepath: str) -> Tuple[Optional[str], Optional[float], Optional[str]]:
    """
    Tente de détecter l'encodage d'un fichier à partir d'un échantillon binaire.
    Considère un encodage comme détecté de manière fiable si chardet est confiant
    OU si c'est UTF-8 (encodage robuste).

    Args:
        filepath (str): Chemin vers le fichier à analyser.

    Returns:
        Tuple contenant :
            - encoding détecté (str ou None),
            - confiance (float ou None),
            - message d'erreur (str ou None, uniquement si échec total).
    """
    raw_sample = b''
    try:
        with open(filepath, 'rb') as f:
            raw_sample = f.read(_SAMPLE_SIZE_BYTES)
    except (IOError, OSError) as e:
        return None, None, f"Erreur d'ouverture ou de lecture du fichier : {e}"
    
    if not raw_sample:
        return None, None, "Échantillon vide : impossible de détecter l'encodage."

    chardet_result = chardet.detect(raw_sample)
    chardet_encoding = chardet_result.get("encoding")
    chardet_confidence = chardet_result.get("confidence")

    # 1. Tenter avec chardet si la confiance est suffisante
    if chardet_encoding and chardet_confidence and chardet_confidence >= _DEFAULT_CONFIDENCE_THRESHOLD:
        try:
            # Vérifier que chardet_encoding décode réellement l'échantillon
            raw_sample.decode(chardet_encoding) 
            return chardet_encoding, chardet_confidence, None # Succès fiable via chardet
        except UnicodeDecodeError:
            pass

    # 2. Si pas de détection fiable par chardet, tenter avec UTF-8 (encodage robuste et strict)
    # UTF-8 est un encodage qui lève souvent des erreurs si les octets ne sont pas valides,
    # ce qui est un bon indicateur de "non-sens".
    try:
        raw_sample.decode('utf-8')
        return 'utf-8', 0.0, None # Succès via repli UTF-8 (confiance 0.0 car pas de détection chardet fiable)
    except UnicodeDecodeError:
        pass # UTF-8 échoue, on continue

    # 3. Si aucune des méthodes fiables n'a fonctionné, considérer l'encodage comme indétectable.
    # On ne tente PAS latin1/windows-1252 ici pour la détection *fiable*.
    # Si ces encodages sont les seuls à décoder, c'est que le fichier est probablement du charabia,
    # et cela doit être signalé comme un échec de détection fiable.
    return None, None, "Encodage indétectable après toutes les tentatives fiables."


def check_file_empty_content(
    filepath: str, 
    encoding: str, 
    sample_size: int = _SAMPLE_SIZE_BYTES
) -> ValidationResult:
    """
    Vérifie si un fichier contient un contenu significatif (hors espaces/retours ligne).
    
    Args:
        filepath (str): Chemin du fichier à analyser.
        encoding (str): Encodage à utiliser pour le décodage.
        sample_size (int): Taille de l’échantillon binaire à lire.

    Returns:
        Tuple[bool, Optional[str]]: True si contenu significatif, False sinon, avec message d’erreur.
    """
    raw_sample = b''
    try:
        with open(filepath, 'rb') as f:
            raw_sample = f.read(sample_size)
    except (IOError, OSError) as e:
        return False, f"[check_file_empty_content] Erreur de lecture du fichier '{filepath}' : {e}"
    
    # La vérification du fichier de 0 octet est gérée par check_file_not_empty
    # Cette fonction se concentre sur le contenu *après* décodage.
    # Si raw_sample est vide ici, cela signifie que le fichier est plus petit que sample_size
    # et ne contient rien. C'est un cas limite qui devrait être géré par check_file_not_empty
    # ou considéré comme un fichier vide de contenu significatif.
    # On va le laisser passer pour que le decode() puisse lever une erreur ou le strip() le vide.

    try:
        decoded_sample = raw_sample.decode(encoding)
    except UnicodeDecodeError:
        return False, (
            f"[check_file_empty_content] Impossible de décoder l'échantillon avec l'encodage '{encoding}' "
            f"pour vérifier le contenu (problème d'encodage)."
        )
    
    if not decoded_sample.strip():
        return False, (
        "[check_file_empty_content] Le fichier est vide de contenu significatif (contient seulement des espaces/retours à la ligne)."
    )
    return True, None


def detect_csv_separator(
    filepath: str,
    encoding: str,
    sample_size: int = _SAMPLE_SIZE_BYTES
) -> Tuple[Optional[str], Optional[str]]:
    """
    Tente de détecter automatiquement le séparateur CSV à partir d’un échantillon.

    La fonction lit un échantillon du fichier avec l'encodage spécifié, puis
    utilise `csv.Sniffer` pour deviner le dialecte (séparateur, quoting, etc.).

    Args:
        filepath (str): Chemin absolu vers le fichier CSV à analyser.
        encoding (str): Encodage à utiliser pour lire le fichier.
        sample_size (int, optional): Taille maximale de l’échantillon lu (en octets).
            Défaut : 128 KB.

    Returns:
        Tuple[Optional[str], Optional[str]]: 
            - séparateur détecté (ex: ',', ';', '\t') ou None si échec,
            - message d'erreur ou None si succès.
    """
    try:
        # Utilise 'errors="replace"' pour éviter UnicodeDecodeError si l'encodage n'est pas parfait
        with open(filepath, "r", encoding=encoding, errors="replace") as f:
            sample_data = f.read(sample_size)
    except (IOError, OSError) as e:
        return None, f"[detect_csv_separator] Erreur lors de la lecture de l’échantillon : {e}"

    # Vérification si l'échantillon est vide ou ne contient que des blancs
    if not sample_data.strip():
        return None, "[detect_csv_separator] L'échantillon est vide de contenu significatif, séparateur non détectable."

    sniffer = csv.Sniffer()
    try:
        dialect = sniffer.sniff(sample_data)
        
        # Vérification du séparateur à caractère unique
        if len(dialect.delimiter) != 1:
            return None, (f"[detect_csv_separator] Séparateur détecté ('{dialect.delimiter}') "
                          f"n'est pas un caractère unique.")

        return dialect.delimiter, None
    except csv.Error:
        return None, "[detect_csv_separator] Séparateur indétectable par Sniffer."

def load_dataframe_robustly(
    filepath: str,
    encoding: str,
    detected_separator: Optional[str] = None
) -> Tuple[Optional[pd.DataFrame], Optional[str], Optional[str], Optional[str]]: # Modifié: Ajout de Optional[str] pour error_code
    """
    Tente de charger un fichier CSV dans un DataFrame Pandas de manière robuste.
    Essaie le séparateur détecté, puis une liste de séparateurs de repli.
    Gère les erreurs de parsing et de données vides.

    Args:
        filepath (str): Chemin d'accès au fichier CSV.
        encoding (str): Encodage à utiliser pour la lecture.
        detected_separator (Optional[str]): Séparateur détecté par csv.Sniffer, si disponible.

    Returns:
        Tuple[Optional[pd.DataFrame], Optional[str], Optional[str], Optional[str]]:
        - DataFrame Pandas chargé ou None si échec.
        - Séparateur finalement utilisé pour le chargement.
        - Message d'erreur si le chargement échoue (None si succès).
        - Code d'erreur spécifique (ex: "non_rectangular_structure", "file_empty_after_header") ou None.
    """
    separators_to_try = []
    if detected_separator:
        separators_to_try.append(detected_separator)
    
    for sep in _PANDAS_SEPARATORS_FALLBACK:
        if sep not in separators_to_try:
            separators_to_try.append(sep)

    # Variables pour stocker les dernières erreurs rencontrées, avec leur code
    last_parser_error_msg = None
    last_parser_error_code = None
    last_empty_data_error_msg = None
    last_empty_data_error_code = None
    last_other_error_msg = None
    last_other_error_code = None

    for current_sep in separators_to_try:
        try:
            # Utilisation de on_bad_lines='skip' pour ignorer les lignes mal formées
            # C'est déprécié dans les versions récentes de pandas (remplacé par on_bad_lines='warn' ou callable)
            # Pour la V1, on le garde pour compatibilité si besoin.
            df = pd.read_csv(
                filepath, 
                encoding=encoding, 
                sep=current_sep, 
                on_bad_lines='skip',
            )
            
            # Vérification si le DataFrame est vide après chargement (e.g., seulement en-têtes, pas de lignes de données)
            if df.empty:
                last_empty_data_error_msg = (f"[load_dataframe_robustly] Le fichier est vide de données "
                                            f"après l'en-tête avec le séparateur '{current_sep}'.")
                last_empty_data_error_code = "file_empty_after_header"
                continue # Essayer d'autres séparateurs si ce résultat est un DataFrame vide

            # Succès du chargement avec des données
            return df, current_sep, None, None # Succès, pas d'erreur, pas de code d'erreur

        except pd.errors.ParserError as e:
            # Erreur de parsing (structure non rectangulaire, etc.)
            last_parser_error_msg = (f"[load_dataframe_robustly] Erreur de parsing avec le séparateur "
                                    f"'{current_sep}': {e}")
            last_parser_error_code = "non_rectangular_structure"
            continue # Essayer d'autres séparateurs
        except pd.errors.EmptyDataError as e:
            # Fichier vide ou seulement des en-têtes (pas de lignes de données)
            last_empty_data_error_msg = (f"[load_dataframe_robustly] Le fichier est vide de données "
                                        f"après l'en-tête avec le séparateur '{current_sep}': {e}")
            last_empty_data_error_code = "file_empty_after_header"
            continue # Essayer d'autres séparateurs
        except UnicodeDecodeError as e:
            # Normalement géré par detect_file_encoding, mais sécurité ici
            last_other_error_msg = (f"[load_dataframe_robustly] Erreur de décodage Unicode avec le séparateur "
                                    f"'{current_sep}': {e}")
            last_other_error_code = "unicode_decode_error_in_load" # Nouveau code pour cette erreur spécifique
            continue # Essayer d'autres séparateurs
        except Exception as e:
            # Capture toute autre erreur inattendue lors du chargement
            last_other_error_msg = (f"[load_dataframe_robustly] Erreur inattendue avec le séparateur "
                                    f"'{current_sep}': {e}")
            last_other_error_code = "df_load_failure_unknown" # Code générique pour les erreurs non prévues
            continue # Essayer d'autres séparateurs
            
    # Si la boucle se termine, cela signifie que toutes les tentatives ont échoué.
    # Retourner le message d'erreur le plus spécifique rencontré en dernier.
    if last_parser_error_msg:
        return None, None, last_parser_error_msg, last_parser_error_code
    if last_empty_data_error_msg:
        return None, None, last_empty_data_error_msg, last_empty_data_error_code
    if last_other_error_msg:
        return None, None, last_other_error_msg, last_other_error_code
    
    # Message de repli si aucune erreur spécifique n'a été capturée (ne devrait idéalement pas arriver)
    return None, None, "[load_dataframe_robustly] Impossible de charger le DataFrame avec les séparateurs essayés.", "df_load_failure_unknown"



