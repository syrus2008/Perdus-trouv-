from rapidfuzz import fuzz
import os
import logging

# Configuration du logging (si non déjà fait dans main)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# Seuil configurable via variable d'environnement
DEFAULT_MATCH_THRESHOLD = int(os.getenv("MATCH_THRESHOLD", 60))

def find_matches_for_trouve(objets_perdus, description, threshold=DEFAULT_MATCH_THRESHOLD):
    results = []
    for obj in objets_perdus:
        desc_perdu = obj.get("description", "")
        score = fuzz.token_sort_ratio(description.lower(), desc_perdu.lower())
        if score > threshold:
            logging.info(f"Matching trouvé (score={score}) : '{description}' <-> '{desc_perdu}'")
            results.append(obj)
        else:
            logging.debug(f"Pas de match (score={score}) : '{description}' <-> '{desc_perdu}'")
    if not results:
        logging.info(f"Aucune correspondance trouvée pour : '{description}'")
    return results

def find_matches_for_perdu(objets_trouves, description, threshold=DEFAULT_MATCH_THRESHOLD):
    results = []
    for obj in objets_trouves:
        desc_trouve = obj.get("description", "")
        score = fuzz.token_sort_ratio(description.lower(), desc_trouve.lower())
        if score > threshold:
            logging.info(f"Matching trouvé (score={score}) : '{description}' <-> '{desc_trouve}'")
            results.append(obj)
        else:
            logging.debug(f"Pas de match (score={score}) : '{description}' <-> '{desc_trouve}'")
    if not results:
        logging.info(f"Aucune correspondance trouvée pour : '{description}'")
    return results
