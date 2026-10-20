"""La categorie `boutiques` de « Creer sa ROM » (ZER-89) : le stock de chaque
etal, case par case, pour `config_rom`.

LES CASES. `shopdata1.bin` (boutiques.py) : 37 boutiques de 18 emplacements.
  articles      une case par emplacement TENU (559 en vanilla). Un
                emplacement vide reste vide : le menu liste par pages de six
                et l'on n'a pas mesure ce qu'il fait d'un trou rempli.
                Chaque ligne porte aussi le POURCENTAGE de prix de sa
                boutique (100, 500 a Pontaudy, 800 dans les trois boutiques
                du rare apres tirage) : une valeur par boutique, que
                l'onglet change sur toutes ses lignes a la fois (joueur,
                20/10/2026 : plus de lignes a part pour le pourcentage).
  prix_fabriques  hors table : les 241 objets sans prix en ont-ils un
                (patch_prix, et le prix en clair du bouclier d'argent,
                ZER-77) ? Le fichier le dit pour rendre la meme ROM ; il ne
                se change pas dans l'onglet.

AUCUNE REGLE D'EQUILIBRAGE (joueur, 19/10/2026) : ni familles, ni rarete,
ni ZER-49, ni doublons. Les VERROUS (levables) : aucun objet important ou
hors tirage en vente, et les objets de quete de ZER-77 restent dans leur
boutique (la quete d'apres-jeu les demande).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import boutiques as B
import objets
import treasure as T

TABLES = ("articles",)
# Le lieu de chaque boutique (research §83.5, noms francais du releve de la
# communaute -- la ROM ne les porte pas).
LIEUX = {32: "Chérubelle", 0: "Ablithia", 1: "Ablithia", 36: "Ablithia",
         2: "Ablithia", 35: "Ablithia", 37: "Ablithia", 3: "Le Plicata",
         4: "Bacilli", 5: "Bacilli", 6: "Bacilli", 7: "Abbaye des Vocations",
         8: "Port Ehcep", 9: "Port Ehcep", 10: "Rivesall", 11: "Pontaudy",
         12: "Pontaudy", 33: "Pontaudy", 13: "Finefleur", 14: "Finefleur",
         15: "Finefleur", 16: "Finefleur", 17: "Ouadi", 18: "Ouadi",
         19: "Ouadi", 20: "Batsureg", 21: "Batsureg", 22: "Batsureg",
         23: "École Saint-Sévaire", 24: "Dracocardis", 25: "Dracocardis",
         26: "Dracocardis", 27: "Kilimagmaro", 28: "Kilimagmaro",
         29: "Kilimagmaro", 30: "Côte de l'Exil", 34: "?"}


def _lieu(t, boutique, cat):
    return t("place_boutique", boutique, LIEUX.get(boutique, "?"),
             t("etal_%d" % cat))


def _place(t, table, k, l):
    return "%s · %d" % (_lieu(t, l["boutique"], l.get("categorie", 2)),
                        l["case"])


# `liees` : le pourcentage est celui de la BOUTIQUE ; le changer sur une
# ligne le change sur toutes celles de la meme boutique.
FORME = dict(tables=(("articles", None),),
             champs=(("objet", "objet"), ("pourcentage", "nombre")),
             bornes={"pourcentage": (1, 0xFFFF)},
             liees={"pourcentage": "boutique"},
             verrous=set(), place=_place)


def interdits(rom):
    return objets.objets_importants(rom) | objets.HORS_TIRAGE


def prix_fabriques(rom):
    """Vrai si les objets sans prix en ont recu un (patch_prix)."""
    import patch_prix
    return not patch_prix.prix_voulus(rom)


def exporter(rom, langue="en"):
    nm = objets.noms(rom, langue, accents=True)
    _d, etals = B.lire(rom)
    art = []
    for e in etals:
        for k, o in enumerate(e["objets"]):
            if o:
                art.append({"boutique": e["id"], "case": k + 1, "objet": o,
                            "nom": nm.get(o, ""), "pourcentage": e["pct"],
                            "categorie": e["categorie"]})
    return {"articles": art, "prix_fabriques": prix_fabriques(rom)}


def tirer_section(rom, graine, langue="en", chaos=False, progression=True,
                  prix=True):
    """Tire la categorie seule sur `rom` (vanilla), comme randomizer.py."""
    import random
    import patch_boutiques
    import patch_prix
    if prix:
        patch_prix.patcher(rom, langue=langue)
    patch_boutiques.patcher(rom, random.Random(graine), langue=langue,
                            chaos=chaos, prix_fabriques=prix,
                            progression=progression and not chaos)
    return exporter(rom, langue)


def _remettre_prix(rom, vanilla):
    """Rend aux dix archives d'objets leurs octets vanilla."""
    import patch_prix
    for chemin in [patch_prix.CHEMIN_TABLE] + [objets.CHEMIN % c
                                                for c in objets.CATEGORIES]:
        fid = rom.filenames.idOf(chemin)
        rom.files[fid] = bytes(vanilla.files[vanilla.filenames.idOf(chemin)])


def appliquer(rom, section, verrous=True, vanilla=None):
    """Ecrit la section `boutiques`. Rend le nombre de cases changees."""
    from config_rom import ConfigInvalide
    import patch_boutiques as PB
    cat = objets.catalogue(rom)
    nm = objets.noms(rom, "en")
    refuses = interdits(rom) if verrous else set()
    d, etals = B.lire(rom)
    par_id = {e["id"]: e for e in etals}
    tenus = [(e["id"], k) for e in etals for k, o in enumerate(e["objets"]) if o]
    lignes = section.get("articles")
    if not isinstance(lignes, list) or len(lignes) != len(tenus):
        raise ConfigInvalide("boutiques.articles : %d cases attendues"
                             % len(tenus))
    buf = bytearray(d)
    n = 0
    vendus = {}
    pcts = {}
    for i, (l, (b, k)) in enumerate(zip(lignes, tenus)):
        ou = "boutiques.articles[%d]" % i
        try:
            o, lb, lk = int(l["objet"]), int(l["boutique"]), int(l["case"])
        except (KeyError, TypeError, ValueError):
            raise ConfigInvalide(ou + " : 'boutique', 'case' et 'objet' "
                                 "entiers attendus")
        if (lb, lk) != (b, k + 1):
            raise ConfigInvalide(ou + " : boutique %d case %d attendues"
                                 % (b, k + 1))
        if o not in cat:
            raise ConfigInvalide(ou + " : objet %d inconnu du jeu" % o)
        if o in refuses:
            raise ConfigInvalide(ou + " : %s est un objet de quete ou de "
                                 "debug, il casserait la partie" % nm.get(o, o))
        try:
            p = int(l["pourcentage"])
        except (KeyError, TypeError, ValueError):
            raise ConfigInvalide(ou + " : 'pourcentage' entier attendu")
        if not 1 <= p <= 0xFFFF:
            raise ConfigInvalide(ou + " : %d %%, hors de 1..65535" % p)
        if pcts.setdefault(b, p) != p:
            raise ConfigInvalide(ou + " : boutique %d a deux pourcentages "
                                 "(%d et %d), un seul par boutique"
                                 % (b, pcts[b], p))
        vendus.setdefault(b, set()).add(o)
        if par_id[b]["objets"][k] != o:
            T.ecrire_u32(buf, par_id[b]["offsets"][k], o)
            n += 1
    for e in etals:
        p = pcts.get(e["id"], e["pct"])
        if p != e["pct"]:
            T.ecrire_u32(buf, e["off_pct"], p)
            n += 1
    if verrous:
        # LA QUETE D'APRES-JEU (ZER-77) : ses objets restent en vente, dans
        # leur boutique, a n'importe quelle case.
        for b, qs in PB.QUETE.items():
            for q in qs:
                if q not in vendus.get(b, ()):
                    raise ConfigInvalide(
                        "boutiques : %s doit rester en vente dans la boutique "
                        "%d (quete d'apres-jeu), il casserait la partie"
                        % (nm.get(q, q), b))
    actuel = prix_fabriques(rom)
    voulu = section.get("prix_fabriques", actuel)
    if not isinstance(voulu, bool):
        raise ConfigInvalide("boutiques.prix_fabriques : vrai ou faux attendu")
    if voulu != actuel:
        if vanilla is None:
            raise ConfigInvalide("boutiques.prix_fabriques : la ROM d'origine "
                                 "est necessaire pour changer les prix")
        _remettre_prix(rom, vanilla)
        if voulu:
            import patch_prix
            patch_prix.patcher(rom)
            patch_prix.retarifer(rom, PB.prix_quete(rom))
        n += 1
    if bytes(buf) != d:
        rom.files[rom.filenames.idOf(B.CHEMIN)] = bytes(buf)
    return n
