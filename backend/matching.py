from rapidfuzz import fuzz

def find_matches_for_trouve(objets_perdus, description):
    results = []
    for obj in objets_perdus:
        desc_perdu = obj.get("description", "")
        score = fuzz.token_sort_ratio(description.lower(), desc_perdu.lower())
        if score > 60:
            results.append(obj)
    return results

def find_matches_for_perdu(objets_trouves, description):
    results = []
    for obj in objets_trouves:
        desc_trouve = obj.get("description", "")
        score = fuzz.token_sort_ratio(description.lower(), desc_trouve.lower())
        if score > 60:
            results.append(obj)
    return results
