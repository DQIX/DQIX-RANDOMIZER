"""La categorie `monstres` de « Creer sa ROM » (ZER-93) : les monstres du
terrain, pour `config_rom`.

LES TROIS MODES (decision du joueur, 19/10/2026) :
  aleatoire  n'importe quelle espece a chaque apparition : le blob, comme
             `--apparitions aleatoire`. Les tables ne s'appliquent pas.
  zone       chaque espece vanilla d'une CARTE devient l'espece de sa case
             (table `zones`), comme `--apparitions zone`, sans blob.
  globale    chaque espece vanilla devient l'espece de sa case PARTOUT
             (table `globale`), comme `--apparitions globale`, sans blob.
             La table identite = les monstres du jeu d'origine.
Pas de liste tiree en jeu par zone : B et C s'ecrivent a la construction.

LE MODE DECIDE DU BLOB, qui est assemble bien avant que `--config`
s'applique : `mode_config` le donne au randomizer, qui regle
`--apparitions` d'apres lui (comme config_boss.preparer_blob). `appliquer`
ne pose ni ne retire le blob ; il refuse un mode zone ou globale sur une
ROM qui le porte.

LES CASES. Une ligne `reglages` (le mode) ; `globale`, une ligne par espece
des trois tables de rencontres (encmons, encfld, encbtl) ; `zones`, une
ligne par (carte, espece vanilla de la carte), sur toutes les references de
la carte (symboles, combats, prechargement), comme `rencontres_zone`. Les
trois aires d'encbtl qu'aucune carte ne porte suivent `globale` dans les
deux modes.

CE QU'UNE CASE PEUT RECEVOIR : toute espece qui a un modele de terrain et
que le jeu sait faire roder (le bestiaire, et les especes deja presentes
dans les tables : symboles d'antre). Aucune autre limite (joueur, 19/10).
Deux especes d'une carte qui deviennent la meme : sa liste prechargee ne la
porte qu'une fois (l'emplacement en double devient vide, comme le vanilla).
"""
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enctables import CHEMINS, FICHIERS_RENCONTRES, TablesRencontres

MODES = ("aleatoire", "zone", "globale")
TABLES = ("reglages", "globale", "zones")


def _place(t, table, k, l):
    if table == "reglages":
        return t("champ_mode")
    if table == "globale":
        return t("monstres_partout")
    return l.get("carte_nom") or str(l["carte"])


def _vue(section):
    """Ce que l'onglet montre selon le mode (joueur, 20/10/2026) : par zone,
    la table des zones ; partout, la table globale ; aleatoire, tout grise
    (les tables ne s'appliquent pas)."""
    try:
        mode = section["reglages"][0]["mode"]
    except (KeyError, IndexError, TypeError):
        mode = "aleatoire"
    if mode == "zone":
        return ["reglages", "zones"], set()
    if mode == "globale":
        return ["reglages", "globale"], set()
    return ["reglages", "globale", "zones"], {"globale", "zones"}


FORME = dict(tables=(("reglages", 1), ("globale", None), ("zones", None)),
             champs=(("mode", "apparition"), ("espece", "monstre")),
             verrous=set(), place=_place, vue=_vue)


# --- lecture -----------------------------------------------------------------

class _Fichiers(object):
    """Ce que TablesRencontres lit d'une ROM, pour la vanilla en cache."""

    def __init__(self, contenus):
        self.files = [contenus[n] for n in FICHIERS_RENCONTRES]
        idx = {CHEMINS[n]: i for i, n in enumerate(FICHIERS_RENCONTRES)}
        self.filenames = type("N", (), {"idOf": staticmethod(idx.get)})()


def _tables_vanilla(vanilla=None):
    if vanilla is not None:
        return TablesRencontres(vanilla, FICHIERS_RENCONTRES)
    import source_rom
    return TablesRencontres(_Fichiers(
        {n: source_rom.lire(CHEMINS[n]) for n in FICHIERS_RENCONTRES}),
        FICHIERS_RENCONTRES)


_cache = {}


def _ids():
    if "ids" not in _cache:
        from montable import ids_par_index
        from rom_vanilla import chemin_vanilla
        _cache["ids"] = ids_par_index(chemin_vanilla())
    return _cache["ids"]


def _structure(tv):
    """[(fichier, enreg, champ, decalage, masque, espece vanilla, carte)] :
    chaque reference d'espece des trois tables vanilla, avec sa carte (None
    pour les aires orphelines d'encbtl)."""
    import rencontres_zone as RZ
    RZ._cache.clear()
    _par, aire_carte = RZ.especes_par_carte(tv, set(_ids()))
    out = [(n, ir, ic, d, m, v, RZ._carte(tv, n, ir, aire_carte))
           for n, ir, ic, d, m, v in tv.references(set(_ids()))]
    RZ._cache.clear()
    return out


def _blob(rom):
    import config_boss
    return config_boss._blob(rom) is not None


def _noms(rom, langue):
    """{identifiant: nom} des especes, {carte: nom} des cartes."""
    import monnames
    from rom_vanilla import chemin_vanilla
    cle = ("noms", langue)
    if cle not in _cache:
        lignes = monnames.charger(chemin_vanilla(), langue)
        ids = _ids()
        esp = {ids[r]: (l.get("nom") or "") for r, l in enumerate(lignes)
               if r < len(ids) and isinstance(l, dict)}
        _cache[cle] = (esp, _noms_cartes(rom, langue))
    return _cache[cle]


def _noms_cartes(rom, langue):
    import objets
    import zones
    d = objets._membre_archive(rom, "data/map/mapname.gp2",
                               "mapname_%s.bin" % langue)
    instrs, s = zones._chaines(d)
    out = {}
    for i in instrs:
        if i.op == 0x67 and len(i.valeurs) > 1 and i.types[1] == 0:
            out[i.valeurs[0]] = objets.nettoyer(s(i.valeurs[1]) or "")
    return out


def choisissables(rom, langue="en"):
    """[(identifiant, texte)] des especes qu'une case peut recevoir, triees
    par nom ; deux especes du meme nom (le gluant en a cinq versions)
    portent leur identifiant."""
    esp, _c = _noms(rom, langue)
    vals = sorted(_valides())
    compte = collections.Counter(esp.get(i, "") for i in vals)
    out = [(i, esp.get(i) or str(i) if compte[esp.get(i, "")] == 1
            else "%s #%d" % (esp.get(i) or "?", i)) for i in vals]
    return sorted(out, key=lambda x: (x[1].lower(), x[0]))


def _valides():
    """Les especes qu'une case peut recevoir : un modele de terrain, et le
    bestiaire ou deja dans les tables vanilla."""
    if "valides" not in _cache:
        from monstres_nommes import MONSTRES
        from patch_hasard import tailles_par_identifiant
        ids = _ids()
        tailles = tailles_par_identifiant()
        bestiaire = {ids[r] for r in MONSTRES if r < len(ids)}
        tables = {s[5] for s in _structure(_tables_vanilla())}
        _cache["valides"] = frozenset(
            i for i in bestiaire | tables if i in tailles)
    return _cache["valides"]


def interdits(rom):
    return set()


# --- export ------------------------------------------------------------------

def _images(rom, tv):
    """{(carte, espece vanilla): set(especes)} lu position par position dans
    `rom`, ou None si ses tables n'ont pas la forme vanilla (blob agrandi)."""
    tn = TablesRencontres(rom, FICHIERS_RENCONTRES)
    for n in FICHIERS_RENCONTRES:
        a, b = tv.tables[n].records, tn.tables[n].records
        if len(a) != len(b) or any(
                (x.tag, len(x.fields)) != (y.tag, len(y.fields))
                for x, y in zip(a, b)):
            return None
    out = collections.defaultdict(set)
    for n, ir, ic, d, m, v, carte in _structure(tv):
        w = (tn.tables[n].records[ir].fields[ic] >> d) & m
        if w:                     # un doublon de liste prechargee, vide
            out[(carte, v)].add(w)
    return out


def _section(rom, langue, mode, images):
    """La section, `images` = {(carte, espece vanilla): espece}."""
    esp, cartes = _noms(rom, langue)
    especes = sorted({v for _c, v in _paires()})
    glob = {}
    for v in especes:
        orph = images.get((None, v))
        if orph is not None:
            glob[v] = orph
            continue
        vues = {images.get((c, v), v) for c, v2 in _paires()
                if v2 == v and c is not None}
        glob[v] = vues.pop() if len(vues) == 1 else v
    lignes_g = [{"espece_vanilla": v, "espece": glob[v],
                 "nom": esp.get(glob[v], "")} for v in especes]
    lignes_z = []
    for c, v in sorted((p for p in _paires() if p[0] is not None)):
        w = images.get((c, v), v)
        lignes_z.append({"carte": c, "carte_nom": "%s (%d)" % (
            cartes.get(c, "") or "?", c), "espece_vanilla": v,
            "espece": w, "nom": esp.get(w, "")})
    return {"reglages": [{"reglage": "mode", "mode": mode}],
            "globale": lignes_g, "zones": lignes_z}


def _paires():
    if "paires" not in _cache:
        _cache["paires"] = sorted({(s[6], s[5])
                                   for s in _structure(_tables_vanilla())},
                                  key=lambda p: (p[0] is None, p[0] or 0, p[1]))
    return _cache["paires"]


def exporter(rom, langue="en"):
    """La ROM telle qu'elle est. Avec le blob : mode aleatoire, tables du jeu
    d'origine (elles ne s'appliquent pas). Sans : globale si chaque espece a
    la meme image partout, zone sinon."""
    tv = _tables_vanilla()
    images = None if _blob(rom) else _images(rom, tv)
    if images is None:
        return _section(rom, langue, "aleatoire", {})
    une = {k: min(s) for k, s in images.items()}
    par_espece = collections.defaultdict(set)
    for (c, v), w in une.items():
        par_espece[v].add(w)
    mode = ("globale" if all(len(s) == 1 for s in par_espece.values())
            else "zone")
    return _section(rom, langue, mode, une)


def mode_config(section):
    """Le mode d'une section, pour le randomizer avant l'assemblage du blob
    (leve ConfigInvalide)."""
    from config_rom import ConfigInvalide
    regl = section.get("reglages")
    try:
        mode = regl[0]["mode"]
    except (TypeError, IndexError, KeyError):
        raise ConfigInvalide("monstres.reglages : [{'reglage': 'mode', "
                             "'mode': ...}] attendu")
    if mode not in MODES:
        raise ConfigInvalide("monstres.reglages : mode %r, attendu %s"
                             % (mode, ", ".join(MODES)))
    return mode


def apparitions(section):
    """La valeur de `--apparitions` qu'une section demande au randomizer.
    Une table globale identite est le jeu d'origine : `vanilla`, qui ne
    tire rien (le meme chemin que l'option, donc la meme ROM)."""
    mode = mode_config(section)
    try:
        identite = all(int(l["espece"]) == int(l["espece_vanilla"])
                       for l in section.get("globale") or ())
    except (KeyError, TypeError, ValueError):
        identite = False            # appliquer dira quelle case
    return "vanilla" if mode == "globale" and identite else mode


# --- application -------------------------------------------------------------

def _lire_table(section, table, cle, valides):
    """{cle: espece} d'une table de la section (leve ConfigInvalide)."""
    from config_rom import ConfigInvalide
    lignes = section.get(table)
    if not isinstance(lignes, list):
        raise ConfigInvalide("monstres.%s : une liste attendue" % table)
    connues = ({v for _c, v in _paires()} if table == "globale"
               else {p for p in _paires() if p[0] is not None})
    out = {}
    for i, l in enumerate(lignes):
        ou = "monstres.%s[%d]" % (table, i)
        try:
            k = cle(l)
            w = int(l["espece"])
        except (KeyError, TypeError, ValueError):
            raise ConfigInvalide(ou + " : 'espece_vanilla', 'espece'%s "
                                 "entiers attendus"
                                 % (", 'carte'" if table == "zones" else ""))
        if k not in connues:
            raise ConfigInvalide(ou + " : %s n'est pas dans les tables du jeu"
                                 % (k,))
        if w not in valides:
            raise ConfigInvalide(ou + " : l'espece %d n'a pas de modele de "
                                 "terrain" % w)
        out[k] = w
    return out


def _sans_doublons(tables, tv):
    """Une espece qu'un CHANGEMENT met deux fois dans une liste prechargee
    n'y reste qu'une fois : l'emplacement change en double devient 0 (vide).
    Un emplacement inchange reste tel quel, et un doublon herite aussi : la
    vanilla a elle-meme un doublon (carte 20039, espece 100), que les deux
    emplacements suivent ensemble."""
    em, ev = tables.tables["encmons.bin"], tv.tables["encmons.bin"]
    for ir, r in enumerate(em.records):
        if r.tag != 0x66 or not r.fields:
            continue
        rv = ev.records[ir]
        places = [(ic, dec) for ic in range(1, len(r.fields))
                  for dec in (0, 16)]
        val = {p: (r.fields[p[0]] >> p[1]) & 0xFFFF for p in places}
        van = {p: (rv.fields[p[0]] >> p[1]) & 0xFFFF for p in places}
        # espece -> especes vanilla des emplacements qui la portent : un
        # doublon HERITE (deux emplacements de la meme espece vanilla) reste
        vus = collections.defaultdict(set)
        for p in places:
            if val[p] == van[p]:
                vus[val[p]].add(van[p])
        for p in places:
            x = val[p]
            if x == van[p] or x in (0, 0xFFFF):
                continue
            if x in vus and van[p] not in vus[x]:
                ic, dec = p
                em.set_field(ir, ic, em.records[ir].fields[ic]
                             & ~(0xFFFF << dec))
            else:
                vus[x].add(van[p])


def ecrire_tables(rom, mode, glob, zones, vanilla=None):
    """Recrit les trois tables de `rom` depuis celles du vanilla."""
    tv = _tables_vanilla(vanilla)
    tn = TablesRencontres(rom, FICHIERS_RENCONTRES)
    for n in FICHIERS_RENCONTRES:
        tn.tables[n] = type(tv.tables[n])(bytes(tv.tables[n].data))
    for n, ir, ic, d, m, v, carte in _structure(tv):
        w = (zones.get((carte, v), glob.get(v, v)) if mode == "zone"
             and carte is not None else glob.get(v, v))
        if w != v:
            t = tn.tables[n]
            x = t.records[ir].fields[ic]
            t.set_field(ir, ic, (x & ~(m << d)) | ((w & m) << d))
    _sans_doublons(tn, tv)
    for n in FICHIERS_RENCONTRES:
        fid = rom.filenames.idOf(CHEMINS[n])
        neuf = bytes(tn.tables[n].data)
        if bytes(rom.files[fid]) != neuf:
            rom.files[fid] = neuf


def appliquer(rom, section, verrous=True, vanilla=None):
    """Ecrit les tables d'apres le mode. Rend le nombre de cases changees."""
    from config_rom import ConfigInvalide
    mode = mode_config(section)
    valides = _valides()
    glob = _lire_table(section, "globale",
                       lambda l: int(l["espece_vanilla"]), valides)
    zones = _lire_table(section, "zones",
                        lambda l: (int(l["carte"]), int(l["espece_vanilla"])),
                        valides)
    avant = exporter(rom)
    if mode == "aleatoire":
        # le blob tire a chaque apparition ; sans lui (la ROM vanilla de
        # l'onglet), les tables restent celles de la ROM
        return 0
    if _blob(rom):
        raise ConfigInvalide("monstres : le mode %s ne pose pas le blob, et "
                             "cette ROM le porte (le randomizer regle "
                             "--apparitions d'apres la config)" % mode)
    ecrire_tables(rom, mode, glob, zones, vanilla)
    apres = exporter(rom)
    return sum(a != b for t in TABLES for a, b in zip(avant[t], apres[t]))


# --- tirage ------------------------------------------------------------------

def tirer_section(rom, graine, langue="en", mode="aleatoire"):
    """Tire la categorie sur `rom` (la vanilla), comme `--apparitions`."""
    import random
    from montable import TableMonstres
    from patch_hasard import tailles_par_identifiant
    import rencontres_zone as RZ
    if mode not in ("zone", "globale"):
        s = exporter(rom, langue)
        s["reglages"][0]["mode"] = "aleatoire" if mode == "aleatoire" else "globale"
        return s
    rng = random.Random(graine)
    pool = sorted(i for i in _valides() if i in _pool_terrain())
    tables = TablesRencontres(rom, FICHIERS_RENCONTRES)
    ids = set(_ids())
    tailles = tailles_par_identifiant()
    cibles = list(pool)
    rng.shuffle(cibles)
    corresp = dict(zip(pool, cibles))
    if mode == "zone":
        RZ.appliquer(tables, rng, pool, ids, tailles, corresp)
    else:
        par, _ac = RZ.especes_par_carte(tables, ids)
        p, _b, _pire = RZ.permutation_globale(rng, pool, tailles, par)
        tables.appliquer(p, ids)
    tables.ecrire_dans_rom()
    s = exporter(rom, langue)
    s["reglages"][0]["mode"] = mode
    return s


def _pool_terrain():
    """Le pool de `--apparitions` : especes de terrain du bestiaire, sans
    prologue ni cinematiques (randomizer.py)."""
    if "pool" not in _cache:
        from agrandir_zones import construire_pool
        from monstres_nommes import MONSTRES
        from rom_vanilla import chemin_vanilla
        ids = _ids()
        index = {i: r for r, i in enumerate(ids)}
        pool, _b = construire_pool(chemin_vanilla())
        _cache["pool"] = frozenset(
            i for i in pool if index.get(i) in MONSTRES
            and i not in (290, 292, 800, 801))
    return _cache["pool"]
