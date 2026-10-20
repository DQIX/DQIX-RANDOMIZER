"""La categorie `actions` de « Creer sa ROM » (ZER-93) : les sorts et les
techniques des monstres (patch_actions, ZER-56/57), pour `config_rom`.

LES CASES. Deux tables :
  emplacements  une ligne par (espece, emplacement 1..6) des 438 fiches de
                `mon_moddata` : `action`, l'action fixe de l'emplacement
                (ecrite dans mon_moddata +0x32 ET mon_btldata +0x18,
                identiques dans le jeu d'origine), et `source` : `fixe`,
                `sort` (un sort tire a chaque combat) ou `technique` (une
                technique tiree a chaque combat) -- les masques de
                mon_btldata +0x82 / +0x83 ;
  pool          une ligne par sort (53, ids 0x09-0x3E) et par technique
                (256, celles qui ont une mise en scene), `actif` : elle
                fait partie du pool commun dans lequel les emplacements
                tires piochent. Sorts et techniques vivent dans la MEME
                table de 1 024 bits de l'overlay 0.

Decision du joueur (19/10/2026) : par espece les 6 actions, par
emplacement fixe / tire, un pool de tirage commun.

LE VERROU (levable) : les boss et les deux especes du combat du prologue
gardent leurs actions et ne tirent rien (le randomizer ne les a jamais
touches). LES LIMITES DU FORMAT : une action fixe doit avoir une fiche
d'action dans le jeu ; un emplacement tire avec un pool vide de son genre
ferait tourner le tirage sans fin (refus). Une technique fixe qui n'a pas
de mise en scene pour le modele marche sans animation (garde-fous §4).

LA GREFFE suit les cases : posee des qu'un emplacement est tire, retiree
sinon ; changer le pool la repose. La repartition des vraies animations en
variantes ne depend que du pool : meme config, meme ROM.
"""
import collections
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import patch_actions as PA

SOURCES = ("fixe", "sort", "technique")
TABLES = ("emplacements", "pool")
PROLOGUE = (290, 292)


def _place(t, table, k, l):
    if table == "emplacements":
        return t("place_action", l.get("monstre_nom") or "#%d" % l["monstre"],
                 l["emplacement"])
    return "%s · %s" % (l.get("nom") or "#%d" % l["pool"],
                        t("champ_sort" if l["genre"] == "sort"
                          else "genre_technique"))


FORME = dict(tables=(("emplacements", None), ("pool", None)),
             champs=(("action", "action"), ("source", "source"),
                     ("actif", "booleen")),
             verrous=set(), place=_place,
             verrou_ligne=lambda table, l: bool(l.get("boss")),
             cocher="pool")

_cache = {}


def _mod_vanilla():
    if "mod" not in _cache:
        import source_rom
        _cache["mod"] = bytes(source_rom.lire(PA.MOD))
    return _cache["mod"]


def _cas(rom):
    """{cas generique: [techniques]} du pool complet, calcule sur les actions
    du jeu d'origine (celles d'une ROM tiree en portent d'autres)."""
    if "cas" not in _cache:
        _cache["cas"] = PA.techniques(rom, _mod_vanilla())
    return _cache["cas"]


def _techniques(rom):
    return sorted(a for l in _cas(rom).values() for a in l)


def _fiches(rom):
    if "fiches" not in _cache:
        _cache["fiches"] = frozenset(PA.actions_rom(rom))
    return _cache["fiches"]


def _verrouillees():
    """Index des fiches que le verrou garde : hors bestiaire (les boss) et
    prologue -- celles que patch_actions.eligibles ecarte."""
    mod = _mod_vanilla()
    n = struct.unpack_from("<I", mod, 0)[0]
    return frozenset(set(range(n)) - set(PA.eligibles(mod)))


def interdits(rom):
    return set()


def _noms_actions(rom, langue):
    cle = ("actions", langue)
    if cle not in _cache:
        import objets
        import sorts
        brut = sorts._noms_fiches(rom, langue)
        _cache[cle] = {a: objets.avec_accents(n).strip()
                       for a, n in brut.items()}
    return _cache[cle]


def _noms_monstres(langue):
    cle = ("monstres", langue)
    if cle not in _cache:
        import monnames
        from rom_vanilla import chemin_vanilla
        lignes = monnames.charger(chemin_vanilla(), langue)
        _cache[cle] = {r: (l.get("nom") or "") for r, l in enumerate(lignes)
                       if isinstance(l, dict)}
    return _cache[cle]


def choisissables(rom, langue="en"):
    """[(identifiant, texte)] des actions qu'une case peut recevoir : toute
    action qui a une fiche dans le jeu, sous son nom ; deux actions du meme
    nom (ou sans nom) portent leur identifiant."""
    nm = _noms_actions(rom, langue)
    ids = sorted(_fiches(rom))
    compte = collections.Counter(nm.get(a, "") for a in ids)
    out = [(a, nm.get(a) if nm.get(a) and compte[nm[a]] == 1
            else "%s #%d" % (nm.get(a) or "?", a)) for a in ids]
    return sorted(out, key=lambda x: (x[1].lower(), x[0]))


# --- export ------------------------------------------------------------------

def _section(rom, langue, actions, masques, sorts_actifs, techs_actifs):
    nm = _noms_actions(rom, langue)
    mn = _noms_monstres(langue)
    garde = _verrouillees()
    lignes = []
    for i, acts in enumerate(actions):
        ms, mt = masques[i]
        for k, a in enumerate(acts):
            l = {"monstre": i, "monstre_nom": mn.get(i, ""),
                 "emplacement": k + 1, "action": a,
                 "action_nom": nm.get(a, ""),
                 "source": ("technique" if mt >> k & 1 else
                            "sort" if ms >> k & 1 else "fixe")}
            if i in garde:
                l["boss"] = True
            lignes.append(l)
    sa, ta = set(sorts_actifs), set(techs_actifs)
    pool = ([{"pool": a, "nom": nm.get(a, ""), "genre": "sort",
              "actif": a in sa} for a in PA.sorts()]
            + [{"pool": a, "nom": nm.get(a, ""), "genre": "technique",
                "actif": a in ta} for a in _techniques(rom)])
    return {"emplacements": lignes, "pool": pool}


def _pools_lus(rom, lu):
    """Les pools que la ROM porte ; sans greffe (ou sans technique dans la
    table, la ROM des seuls sorts), le pool complet : il n'y sert a rien."""
    sa = lu["sorts"] if lu["code"] else PA.sorts()
    ta = (lu["techniques"] if lu["code"] and lu["techniques"]
          else _techniques(rom))
    return sa, ta


def exporter(rom, langue="en"):
    lu = PA.lire(rom)
    sa, ta = _pools_lus(rom, lu)
    return _section(rom, langue, lu["actions"], lu["masques"], sa, ta)


def tirer_section(rom, graine, langue="en", sorts=None, techniques=None):
    """Comme --sorts-monstres[-ajout] / --techniques-monstres[-ajout] :
    `sorts`, `techniques` = None, `remplacer` ou `ajouter`."""
    if sorts or techniques:
        PA.patcher(rom, sorts=sorts, techniques_mode=techniques, seed=graine,
                   bavard=False, animations=bool(techniques))
    return exporter(rom, langue)


# --- application -------------------------------------------------------------

def _etat(actions, masques, sa, ta):
    """Ce qui agit en jeu : un pool ne compte que si un emplacement de son
    genre est tire."""
    s = any(m[0] for m in masques)
    t = any(m[1] for m in masques)
    return (actions, masques, sorted(sa) if s else None,
            sorted(ta) if t else None)


def _lire_section(rom, section, verrous):
    from config_rom import ConfigInvalide
    lu = PA.lire(rom)
    n = len(lu["actions"])
    fiches = _fiches(rom)
    garde = _verrouillees() if verrous else frozenset()
    lignes = section.get("emplacements")
    if not isinstance(lignes, list) or len(lignes) != 6 * n:
        raise ConfigInvalide("actions.emplacements : %d lignes attendues "
                             "(6 par espece)" % (6 * n))
    actions = [list(a) for a in lu["actions"]]
    masques = [[0, 0] for _ in range(n)]
    for j, l in enumerate(lignes):
        ou = "actions.emplacements[%d]" % j
        try:
            i, k = int(l["monstre"]), int(l["emplacement"]) - 1
            a, src = int(l["action"]), l["source"]
        except (KeyError, TypeError, ValueError):
            raise ConfigInvalide(ou + " : 'monstre', 'emplacement', 'action' "
                                 "entiers et 'source' attendus")
        if (i, k) != (j // 6, j % 6):
            raise ConfigInvalide(ou + " : espece %d emplacement %d, attendu "
                                 "%d / %d" % (i, k + 1, j // 6, j % 6 + 1))
        if src not in SOURCES:
            raise ConfigInvalide(ou + " : source %r, attendu %s"
                                 % (src, ", ".join(SOURCES)))
        if a not in fiches:
            raise ConfigInvalide(ou + " : l'action %d n'a pas de fiche dans "
                                 "le jeu" % a)
        ms, mt = lu["masques"][i]
        avant = ("technique" if mt >> k & 1 else "sort" if ms >> k & 1
                 else "fixe")
        if i in garde and (a != lu["actions"][i][k] or src != avant):
            raise ConfigInvalide(ou + " : boss ou combat du prologue, ses "
                                 "actions restent celles du jeu tant que les "
                                 "verrous tiennent")
        actions[i][k] = a
        if src == "sort":
            masques[i][0] |= 1 << k
        elif src == "technique":
            masques[i][1] |= 1 << k
    pool = section.get("pool")
    connus = {a: "sort" for a in PA.sorts()}
    connus.update((a, "technique") for a in _techniques(rom))
    if not isinstance(pool, list):
        raise ConfigInvalide("actions.pool : une liste attendue")
    sa, ta = set(), set()
    for j, l in enumerate(pool):
        try:
            a, actif = int(l["pool"]), bool(l["actif"])
        except (KeyError, TypeError, ValueError):
            raise ConfigInvalide("actions.pool[%d] : 'pool' entier et "
                                 "'actif' attendus" % j)
        if a not in connus:
            raise ConfigInvalide("actions.pool[%d] : %d n'est ni un sort ni "
                                 "une technique mise en scene" % (j, a))
        if actif:
            (sa if connus[a] == "sort" else ta).add(a)
    masques = [tuple(m) for m in masques]
    if any(m[0] for m in masques) and not sa:
        raise ConfigInvalide("actions.pool : un emplacement tire un sort et "
                             "aucun sort n'est coche (le tirage ne finirait "
                             "pas)")
    if any(m[1] for m in masques) and not ta:
        raise ConfigInvalide("actions.pool : un emplacement tire une "
                             "technique et aucune technique n'est cochee (le "
                             "tirage ne finirait pas)")
    return lu, actions, masques, sa, ta


def appliquer(rom, section, verrous=True, vanilla=None):
    """Ecrit les actions et les masques, pose / repose / retire la greffe.
    Rend le nombre de cases changees."""
    from config_rom import ConfigInvalide
    lu, actions, masques, sa, ta = _lire_section(rom, section, verrous)
    sa0, ta0 = _pools_lus(rom, lu)
    avant = _etat(lu["actions"], lu["masques"], sa0, ta0)
    voulu = _etat(actions, masques, sa, ta)
    if avant == voulu:
        return 0
    s_avant = exporter(rom)
    code_change = avant[1:] != voulu[1:] and (lu["code"] or any(
        m[0] or m[1] for m in masques))
    if code_change and lu["code"]:
        try:
            PA.retirer(rom, vanilla)
        except SystemExit as e:
            raise ConfigInvalide("actions : la greffe posee ne se retire pas "
                                 "(%s)" % e)
    fm, fb = PA._fid(rom, PA.MOD), PA._fid(rom, PA.BTL)
    mod, btl = bytearray(rom.files[fm]), bytearray(rom.files[fb])
    for i, acts in enumerate(actions):
        om = PA.ENTETE + i * PA.MOD_TAILLE
        ob = PA.ENTETE + i * PA.BTL_TAILLE
        if acts != lu["actions"][i]:
            struct.pack_into("<6H", mod, om + PA.MOD_ACTIONS, *acts)
            struct.pack_into("<6H", btl, ob + PA.BTL_ACTIONS, *acts)
        btl[ob + PA.BTL_MASQUE], btl[ob + PA.BTL_MASQUE_T] = masques[i]
    rom.files[fm], rom.files[fb] = bytes(mod), bytes(btl)
    if code_change and any(m[0] or m[1] for m in masques):
        # sans emplacement de technique, le pool des techniques va dans la
        # table sans mise en scene : il ne sert pas, mais se relit
        cas = {c: [a for a in l if a in ta] for c, l in _cas(rom).items()}
        cas = {c: l for c, l in cas.items() if l}
        avec = any(m[1] for m in masques)
        try:
            PA.poser_code(rom, sorted(sa), cas if avec else {},
                          animations=True, bavard=False,
                          techs_table=() if avec else sorted(ta))
        except SystemExit as e:
            raise ConfigInvalide("actions : %s" % e)
    s_apres = exporter(rom)
    n = sum(a != b for t in TABLES
            for a, b in zip(s_avant[t], s_apres[t]))
    return max(n, 1)
