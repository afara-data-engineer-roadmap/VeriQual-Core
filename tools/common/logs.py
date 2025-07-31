# -*- coding: utf-8 -*-
import logging
import sys
import os

def configure_logging(
    name: str, 
    level: str = 'INFO', 
    log_to_console: bool = True, 
    log_to_file: bool = False, 
    log_file: str = 'app.log',
    force: bool = False,
    format_string: str = None,
    date_format: str = None
) -> logging.Logger:
    """
    Configure et retourne un logger modulaire, robuste et flexible.

    Args:
        name (str): Le nom du logger (utiliser __name__).
        level (str): Le niveau de log minimum (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_to_console (bool): Si True, envoie les logs à la console.
        log_to_file (bool): Si True, envoie les logs à un fichier.
        log_file (str): Le chemin du fichier de log.
        force (bool): Si True, supprime et reconfigure les handlers existants.
        format_string (str, optional): Chaîne de formatage personnalisée.
        date_format (str, optional): Format de date personnalisé pour le formatter.

    Returns:
        logging.Logger: L'instance du logger configuré.
        
    Raises:
        ValueError: Si le niveau de log fourni est invalide.
    """
    # 1. Validation du niveau de log (Critique 3: "Fail-Fast")
    level_upper = level.upper()
    log_level = getattr(logging, level_upper, None)
    if not isinstance(log_level, int):
        raise ValueError(f"Niveau de log invalide : {level}")

    # 2. Récupération du logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # 3. Gestion de la reconfiguration (Critique 2: "force=True")
    if force and logger.hasHandlers():
        logger.handlers.clear()

    # Si déjà configuré et pas de "force", on ne fait rien
    if logger.hasHandlers():
        return logger

    # 4. Empêcher la propagation au logger racine (Critique 1: "propagate")
    # C'est la manière propre d'isoler le logger.
    logger.propagate = False

    # 5. Création du formatter personnalisé ou par défaut (Critique 4: "flexibilité")
    default_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    default_date_format = '%Y-%m-%d %H:%M:%S'
    
    formatter = logging.Formatter(
        fmt=format_string or default_format,
        datefmt=date_format or default_date_format
    )

    # 6. Handler pour la console
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # 7. Handler pour le fichier
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    file_handler = logging.FileHandler(log_file, mode='a')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
