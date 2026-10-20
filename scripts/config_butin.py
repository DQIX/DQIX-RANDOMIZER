"""La categorie `butin` de « Creer sa ROM » (ZER-93) : le butin tire a chaque
combat (patch_butin, ZER-39), pour `config_rom`.

LES CASES. Deux tables :
  reglages  `tire` : la greffe de l'overlay 23 est posee (le butin d'un
            monstre est tire a chaque combat, et non plus fixe par espece) ;
            `rares` : un objet 4-5 etoiles tire n'est garde qu'une fois sur
            patch_butin.DIVISEUR (sinon, chances egales) ;
  objets    une ligne par objet du jeu, `actif` : il fait partie de la liste
            dans laquelle le butin pioche.

Decision du joueur (19/10/2026) : UNE liste pour tout le jeu, que l'on
coche a la main. Les chances de butin ne bougent pas : seul l'objet change.

LE VERROU (levable) : aucun objet de quete ou hors tirage dans la liste
(objets.objets_importants, objets.HORS_TIRAGE). LA LIMITE DU FORMAT : la
greffe et sa table tiennent en 544 octets derriere le BSS de l'overlay 23 ;
une liste tres eparpillee peut ne pas tenir, `appliquer` le dit.

UN REGLAGE QUI NE SE RELIT PAS TOUJOURS : sans objet 4-5 etoiles dans la
liste, `rares` ne change aucun octet ; relu dans la ROM, il vaut alors vrai.

L'overlay 23 qui revient a son etat vanilla reprend ses OCTETS vanilla (la
recompression ne les rend pas) ; changer une greffe deja posee repart des
octets vanilla, comme le randomizer : meme liste, meme ROM.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import objets
import patch_butin as PB

REGLAGES = ("tire", "rares")


def _place(t, table, k, l):
    if table == "reglages":
        return t("reglage_butin_" + l["reglage"])
    return l.get("nom") or str(l["objet"])


# Un objet de quete porte `quete` dans sa ligne : l'onglet le verrouille
# (la forme ne connait pas la ROM).
FORME = dict(tables=(("reglages", len(REGLAGES)), ("objets", None)),
             champs=(("actif", "booleen"),), verrous=set(), place=_place,
             verrou_ligne=lambda table, l: bool(l.get("quete")),
             cocher="objets", aide="aide_butin")


def interdits(rom):
    return objets.objets_importants(rom) | objets.HORS_TIRAGE


def _section(rom, langue, tire, rares, pool):
    nm = objets.noms(rom, langue, accents=True)
    pool, quete = set(pool), interdits(rom)
    lignes = []
    for i in sorted(objets.catalogue(rom, langue)):
        l = {"objet": i, "nom": nm.get(i, ""), "actif": i in pool}
        if i in quete:
            l["quete"] = True
        lignes.append(l)
    return {"reglages": [{"reglage": "tire", "actif": tire},
                         {"reglage": "rares", "actif": rares}],
            "objets": lignes}


def exporter(rom, langue="en"):
    """La ROM telle qu'elle est. Sans greffe, la liste est celle que
    `--butin-combat` tirerait (objets.pool) et le mode, son defaut."""
    lu = PB.lire(rom)
    if lu is None:
        return _section(rom, langue, False, True, objets.pool(rom))
    mode, pool = lu
    return _section(rom, langue, True, mode == "rares", pool)


def tirer_section(rom, graine, langue="en", libre=False):
    PB.patcher(rom, mode="libre" if libre else "rares", bavard=False)
    return exporter(rom, langue)


def _overlay_vanilla(rom, vanilla):
    """Rend a `rom` l'overlay 23 de `vanilla` : ses octets et son entree
    dans la table des overlays."""
    import ndspy.code
    ovl = rom.loadArm9Overlays()
    v = vanilla.loadArm9Overlays()[PB.OVL]
    rom.files[v.fileID] = bytes(vanilla.files[v.fileID])
    ovl[PB.OVL] = v
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovl)


def appliquer(rom, section, verrous=True, vanilla=None):
    """Pose, change ou retire la greffe du butin. Rend le nombre de cases
    changees."""
    from config_rom import ConfigInvalide
    cat = objets.catalogue(rom)
    nm = objets.noms(rom, "en")
    refuses = interdits(rom) if verrous else set()
    regl = section.get("reglages")
    if (not isinstance(regl, list) or len(regl) != len(REGLAGES)
            or [l.get("reglage") for l in regl if isinstance(l, dict)]
            != list(REGLAGES)):
        raise ConfigInvalide("butin.reglages : %s attendus"
                             % ", ".join(REGLAGES))
    tire, rares = (bool(l.get("actif")) for l in regl)
    lignes = section.get("objets")
    if not isinstance(lignes, list):
        raise ConfigInvalide("butin.objets : une liste attendue")
    pool = set()
    for i, l in enumerate(lignes):
        ou = "butin.objets[%d]" % i
        try:
            o, actif = int(l["objet"]), bool(l["actif"])
        except (KeyError, TypeError, ValueError):
            raise ConfigInvalide(ou + " : 'objet' entier et 'actif' attendus")
        if o not in cat:
            raise ConfigInvalide(ou + " : objet %d inconnu du jeu" % o)
        if actif and o in refuses:
            raise ConfigInvalide(ou + " : %s est un objet de quete ou de "
                                 "debug, il casserait la partie"
                                 % nm.get(o, o))
        if actif:
            pool.add(o)
    if tire and not pool:
        raise ConfigInvalide("butin.objets : aucun objet coche, le butin "
                             "n'aurait rien a tirer")
    mode = "rares" if rares else "libre"
    avant = exporter(rom)
    lu = PB.lire(rom)
    voulu = (mode, sorted(pool)) if tire else None
    if lu == voulu or (lu is None and not tire):
        return 0
    # le nombre de cases qui changent, a l'echelle de la section
    neuf = _section(rom, "en", tire, rares, pool if tire else objets.pool(rom))
    n = sum(a != b for t in ("reglages", "objets")
            for a, b in zip(avant[t], neuf[t]))
    if lu is not None:
        if vanilla is None:
            raise ConfigInvalide("butin : changer une greffe deja posee "
                                 "demande la ROM d'origine")
        _overlay_vanilla(rom, vanilla)
    if tire:
        try:
            PB.patcher(rom, mode=mode, bavard=False, pool=pool)
        except SystemExit as e:
            raise ConfigInvalide("butin.objets : %d objets ne tiennent pas "
                                 "dans la place du jeu (%s) ; cocher des "
                                 "objets voisins ou en retirer" % (len(pool), e))
    return max(n, 1)
