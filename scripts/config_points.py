"""La categorie `points` de « Creer sa ROM » (ZER-97) : les objets des
points brillants (patch_points), pour `config_rom`.

LES CASES. Quatre tables :
  reglages   une ligne : `ramassage` (oui : a chaque entree sur une carte,
             16 objets tires dans SON pool, puis un tire a chaque
             ramassage ; non : l'objet fixe de chaque groupe) ;
  cartes     une ligne par (carte, objet courant) -- les 40 cartes a points
             et les zones speciales 98/99 --, `actif` : l'objet fait partie
             du pool de la carte (joueur, 20/10/2026 : « pool par carte ») ;
  terrain    une ligne par groupe de points (87), `objet` (mode fixe) ;
  speciales  une ligne par case des zones speciales 98/99 (8 groupes de
             partie x 16 cases), `objet` (mode fixe).
Ce qui ne sert pas dans le mode choisi est grise.

UN POOL DE CARTE tient 16 a 127 objets (patch_points.POOL_MIN/POOL_MAX) :
moins de 16 objets coches se repetent, plus de 127 en donnent 127 tires
avec un generateur fixe (meme config, meme ROM). Une carte sans objet coche
est refusee.

AUCUNE REGLE : un equipement peut aller dans un point fixe (le randomizer ne
le fait jamais, et ce n'est pas essaye en jeu). Le VERROU (levable) : aucun
objet important ni hors tirage, comme les autres categories d'objets.
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import objets
import patch_points as PP

TABLES = ("reglages", "cartes", "terrain", "speciales")
SPECIALES = "98/99"


def _place(t, table, k, l):
    if table == "reglages":
        return t("reglage_ramassage")
    if table == "cartes":
        return "%s · %s" % (l.get("lieu") or l["carte"], l.get("nom") or l["objet"])
    if table == "terrain":
        return "%s · zone %d" % (l.get("lieu") or l["carte"], l["zone"])
    return "98/99 · %d · %d" % (l["groupe"], l["case"])


def _ramassage(section):
    try:
        return bool(section["reglages"][0]["ramassage"])
    except (KeyError, IndexError, TypeError):
        return False


def _ligne_grise(section, table, k):
    """Au ramassage, les objets fixes ne servent pas ; en fixe, les pools."""
    if table == "reglages":
        return False
    return (table == "cartes") != _ramassage(section)


FORME = dict(tables=(("reglages", 1), ("cartes", None), ("terrain", None),
                     ("speciales", None)),
             champs=(("ramassage", "booleen"), ("actif", "booleen"),
                     ("objet", "objet")),
             verrous=set(), place=_place, ligne_grise=_ligne_grise,
             cocher="cartes", grise="creer_grise_points")


def interdits(rom):
    return objets.objets_importants(rom) | objets.HORS_TIRAGE


def _speciales_vanilla():
    """Les 128 cases d'izmitm du jeu d'origine (en mode ramassage, le fichier
    ne porte plus que le pool)."""
    import ndspy.rom
    from rom_vanilla import chemin_vanilla
    return PP.lire(ndspy.rom.NintendoDSRom.fromFile(chemin_vanilla()))[1]


def _cartes(groupes):
    out = []
    for l in groupes:
        if l["carte"] not in out:
            out.append(l["carte"])
    return out


def exporter(rom, langue="en"):
    import zones
    nm = objets.noms(rom, langue, accents=True)
    lieux = zones.noms_zones(rom, langue)
    g, t = PP.lire(rom)
    lu = PP.lire_ramassage(rom)
    pools = dict(lu["pools"], **{SPECIALES: lu["special"]}) if lu["actif"] \
        else None
    if lu["actif"]:
        t = _speciales_vanilla()

    def lieu(c):
        return (objets.avec_accents(lieux.get(c, "")) or c) if c != SPECIALES \
            else "Zones 98/99"
    cartes = []
    for c in _cartes(g) + [SPECIALES]:
        actifs = set(pools.get(c, ())) if pools is not None else None
        for i in PP.pool(rom):
            cartes.append({"carte": c, "lieu": lieu(c), "objet": i,
                           "nom": nm.get(i, ""),
                           "actif": actifs is None or i in actifs})
    return {"reglages": [{"reglage": "ramassage",
                          "ramassage": lu["actif"]}],
            "cartes": cartes,
            "terrain": [{"carte": l["carte"], "lieu": lieu(l["carte"]),
                         "zone": l["zone"], "objet": l["objet"],
                         "objet_nom": nm.get(l["objet"], "")} for l in g],
            "speciales": [{"groupe": l["groupe"], "case": l["rang"],
                           "objet": l["objet"],
                           "objet_nom": nm.get(l["objet"], "")} for l in t]}


def tirer_section(rom, graine, langue="en", par_rang=False, ramassage=True):
    """Comme --points-brillants[-par-rang] (et -fixes)."""
    PP.patcher(rom, graine, par_rang=par_rang, ramassage=ramassage)
    return exporter(rom, langue)


def appliquer(rom, section, verrous=True, vanilla=None):
    """Ecrit le mode et les cases. Rend le nombre de cases changees."""
    from config_rom import ConfigInvalide
    cat = objets.catalogue(rom)
    nm = objets.noms(rom, "en")
    refuses = interdits(rom) if verrous else set()
    avant = exporter(rom)
    regl = section.get("reglages", avant["reglages"])
    try:
        ramassage = bool(regl[0]["ramassage"])
    except (KeyError, TypeError, IndexError):
        raise ConfigInvalide("points.reglages : [{'reglage': 'ramassage', "
                             "'ramassage': oui/non}] attendu")
    voulu = {"reglages": [{"reglage": "ramassage", "ramassage": ramassage}]}
    for table, cles in (("cartes", ("carte", "objet")), ("terrain", ("zone",)),
                        ("speciales", ("case",))):
        lignes = section.get(table, avant[table])
        if not isinstance(lignes, list) or len(lignes) != len(avant[table]):
            raise ConfigInvalide("points.%s : %d cases attendues"
                                 % (table, len(avant[table])))
        out = []
        for i, (l, r) in enumerate(zip(lignes, avant[table])):
            ou = "points.%s[%d]" % (table, i)
            try:
                ident = tuple(l[c] for c in cles)
                val = bool(l["actif"]) if table == "cartes" else int(l["objet"])
            except (KeyError, TypeError, ValueError):
                raise ConfigInvalide(ou + " : %s et '%s' attendus"
                                     % (", ".join(cles), "actif"
                                        if table == "cartes" else "objet"))
            if ident != tuple(r[c] for c in cles):
                raise ConfigInvalide(ou + " : %s attendu"
                                     % ", ".join(str(r[c]) for c in cles))
            if table != "cartes":
                if val not in cat:
                    raise ConfigInvalide(ou + " : objet %d inconnu du jeu"
                                         % val)
                if val in refuses:
                    raise ConfigInvalide(ou + " : %s est un objet de quete "
                                         "ou de debug, il casserait la "
                                         "partie" % nm.get(val, val))
            out.append(dict(r, **{"actif" if table == "cartes" else "objet":
                                  val}))
        voulu[table] = out

    def pools(s):
        p = {}
        for l in s["cartes"]:
            p.setdefault(l["carte"], [])
            if l["actif"]:
                p[l["carte"]].append(l["objet"])
        return p
    p_voulu = pools(voulu)
    if ramassage:
        vides = [c for c, l in p_voulu.items() if not l]
        if vides:
            raise ConfigInvalide("points.cartes : aucun objet coche pour %s "
                                 "(tirage au ramassage)" % ", ".join(vides))

    def etat(s):
        r = s["reglages"][0]["ramassage"]
        return (r, [l["objet"] for l in s["terrain"]],
                None if r else [l["objet"] for l in s["speciales"]],
                {c: sorted(v) for c, v in pools(s).items()} if r else None)
    if etat(voulu) == etat(avant):
        return 0
    objets_groupes = [l["objet"] for l in voulu["terrain"]]
    if ramassage:
        rng = random.Random("points:config")
        tires = {c: PP._remplir(rng, sorted(l)) for c, l in p_voulu.items()}
        special = tires.pop(SPECIALES)
        PP.poser_ramassage(rom, tires, special, objets_groupes)
    else:
        if avant["reglages"][0]["ramassage"]:
            PP.retirer_ramassage(rom)
        g, t = PP.lire(rom)
        for l, o in zip(g, objets_groupes):
            l["objet"] = o
        for l, v in zip(t, voulu["speciales"]):
            l["objet"] = v["objet"]
        PP.ecrire(rom, g, t)
    apres = exporter(rom)
    n = sum(a != b for tb in TABLES for a, b in zip(avant[tb], apres[tb]))
    return max(n, 1)
