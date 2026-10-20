"""La categorie `coffres` de « Creer sa ROM » (ZER-92) : coffres, pots et
objet porte par chaque monstre, pour `config_rom`. Les coffres des grottes
sont a part (`config_grottes`), sur les memes lignes de table.

LES CASES (patch_loot, treasure.py) :
  bleus   les lignes de `randTBox.bin` : rang, pourcentage, et ce qu'elles
          donnent -- un objet, de l'or, une embuscade (qui ne se change
          pas : la table embuscade -> monstre n'est pas localisee, ZER-21).
          Le randomizer en fait plus que la vanilla (`repartir`) : la
          section porte TOUTES les lignes, leur nombre suit la ROM lue.
  pots    les lignes de `randTTT.bin` (pots, tonneaux, placards), idem.
  rouges  les coffres rouges, un par identifiant unique (deux zones peuvent
          decrire la meme piece) : un objet, ou de l'or.
  rangs   le rang de chaque coffre bleu (`rang_coffre`, une colonne a
          part : le rang d'une ligne de table ne se change pas) ; les rangs
          jumeaux 6-8 du
          randomizer y deplacent un coffre sur deux.
  drops   l'objet commun et l'objet rare de chaque fiche de `mon_btldata`
          qui en porte un (les taux ne bougent pas).

LE FORMAT DU JEU limite : 242 lignes par table et 32 par rang (au-dela le
jeu ignore, ou vide la table), 100 % par rang, rang sur 5 bits, valeurs sur
16 bits. AUCUNE REGLE de rarete. Les VERROUS (levables) : aucun objet
important ou hors tirage nulle part, et le coffre rouge qui porte un objet
important (la clef magique) le garde.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import objets
import treasure as T

CHEMIN = "data/scenario/treasure.nsarc"
CHEMIN_MONSTRES = "data/prm/mon_btldata.nat"
MON_ENTETE, MON_ENREG = 4, 132
DROPS = ((0x04, "commun"), (0x06, "rare"))
TYPES = {T.TYPE_RIEN: "rien", T.TYPE_OR: "or", T.TYPE_OBJET: "objet",
         T.TYPE_EMBUSCADE: "embuscade"}
LOOT = {v: k for k, v in TYPES.items()}
MAX_TABLE, MAX_RANG = 242, 32
TABLE_DE = {"bleus": T.TABLE_COFFRES_BLEUS, "pots": T.TABLE_POTS,
            "lignes": T.TABLE_GROTTOS}


def place_ligne(t, table, k, l):
    s = t("place_ligne", l["rang"], l["pct"])
    if l["type"] in ("embuscade", "rien"):
        s += " · " + t("loot_" + l["type"]) + (
            " %d" % l["embuscade"] if "embuscade" in l else "")
    return s


def _place(t, table, k, l):
    if table in ("bleus", "pots"):
        return "%s · %s" % (t("table_" + table), place_ligne(t, table, k, l))
    if table == "drops":
        return "%s · %s" % (l.get("monstre_nom") or "#%d" % l["monstre"],
                            t("drop_" + l["emplacement"]))
    return "%s · %s · %d" % (t("table_" + table), l["zone"], l["uid"])


FORME = dict(tables=tuple((n, None) for n in
                          ("bleus", "pots", "rouges", "rangs", "drops")),
             champs=(("objet", "objet"), ("or", "nombre"),
                     ("rang_coffre", "nombre")),
             bornes={"or": (0, 0xFFFF), "rang_coffre": (1, 31)},
             verrous=set(), place=_place)


def interdits(rom):
    return objets.objets_importants(rom) | objets.HORS_TIRAGE


# --- lecture -----------------------------------------------------------------

def _arc(rom):
    return bytes(rom.files[rom.filenames.idOf(CHEMIN)])


def _zones(membres):
    return sorted((k, v) for k, v in membres.items() if k not in T.TABLES)


def lignes_table(rom, table, nm):
    arc = _arc(rom)
    deb = T.membres_narc(arc)[table][0]
    out = []
    for _off, o in T.outcomes(arc, deb):
        l = {"rang": o["rang"], "pct": o["pct"], "type": TYPES[o["loot"]]}
        if o["loot"] == T.TYPE_OBJET:
            l.update(objet=o["id"], nom=nm.get(o["id"], ""))
        elif o["loot"] == T.TYPE_OR:
            l["or"] = o["id"]
        elif o["loot"] == T.TYPE_EMBUSCADE:
            l["embuscade"] = o["id"]
        else:
            l["valeur"] = o["id"]
        out.append(l)
    return out


def _conteneurs(rom, genre):
    """{uid: [(zone, conteneur)]} des conteneurs de ce genre (0 rouge,
    4 bleu), zones dans l'ordre."""
    arc = _arc(rom)
    out = {}
    for z, (deb, _fin) in _zones(T.membres_narc(arc)):
        for c in T.conteneurs(arc, deb):
            if c["conteneur"] == genre:
                out.setdefault(c["unique"], []).append((z, c))
    return out


def _drops(rom):
    mon = bytes(rom.files[rom.filenames.idOf(CHEMIN_MONSTRES)])
    nb = struct.unpack_from("<I", mon, 0)[0]
    return [(k, off, genre, struct.unpack_from("<H", mon, MON_ENTETE
                                               + k * MON_ENREG + off)[0])
            for k in range(nb) for off, genre in DROPS
            if struct.unpack_from("<H", mon, MON_ENTETE + k * MON_ENREG + off)[0]]


def _noms_monstres(rom, langue):
    from monnames import lire_table
    try:
        return [m["nom"] for m in lire_table(objets._membre_archive(
            rom, "data/prm/mon_data.gp2", "mon_data_%s.nat" % langue))]
    except Exception:
        return []


def exporter(rom, langue="en"):
    nm = objets.noms(rom, langue, accents=True)
    rouges = []
    for uid, lot in sorted(_conteneurs(rom, 0).items(), key=lambda x: (x[1][0][0], x[0])):
        z, c = lot[0]
        l = {"zone": z.rsplit(".", 1)[0], "uid": uid, "type": TYPES[c["loot"]]}
        if c["loot"] == T.TYPE_OBJET:
            l.update(objet=c["item"], nom=nm.get(c["item"], ""))
        elif c["loot"] == T.TYPE_OR:
            l["or"] = c["item"]
        else:
            l["valeur"] = c["item"]
        rouges.append(l)
    rangs = [{"zone": lot[0][0].rsplit(".", 1)[0], "uid": uid,
              "rang_coffre": lot[0][1]["item"]}
             for uid, lot in sorted(_conteneurs(rom, 4).items(),
                                    key=lambda x: (x[1][0][0], x[0]))]
    mn = _noms_monstres(rom, langue)
    drops = [{"monstre": k, "monstre_nom": mn[k] if k < len(mn) else "",
              "emplacement": genre, "objet": o, "nom": nm.get(o, "")}
             for k, _off, genre, o in _drops(rom)]
    return {"bleus": lignes_table(rom, T.TABLE_COFFRES_BLEUS, nm),
            "pots": lignes_table(rom, T.TABLE_POTS, nm),
            "rouges": rouges, "rangs": rangs, "drops": drops}


def tirer_section(rom, graine, langue="en", chaos=True, consommables=False,
                  rang_rouges=True, drops=True, categorie="coffres"):
    """Tire le loot seul (patch_loot tire tout d'un coup : coffres et
    grottes) et rend la section `categorie`."""
    import random
    import patch_loot
    patch_loot.patcher(rom, random.Random(graine), langue=langue, drops=drops,
                       chaos=chaos, consommables=consommables,
                       rang_rouges=rang_rouges)
    if categorie == "grottes":
        import config_grottes
        return config_grottes.exporter(rom, langue)
    return exporter(rom, langue)


# --- ecriture ----------------------------------------------------------------

def _entier(l, cle, ou, bas=0, haut=0xFFFF):
    from config_rom import ConfigInvalide
    try:
        v = int(l[cle])
    except (KeyError, TypeError, ValueError):
        raise ConfigInvalide(ou + " : '%s' entier attendu" % cle)
    if not bas <= v <= haut:
        raise ConfigInvalide(ou + " : %s = %d, hors de %d..%d"
                             % (cle, v, bas, haut))
    return v


def _valeur(l, ou, cat, refuses, nm):
    """L'identifiant d'objet ou le montant d'or d'une case, selon son type."""
    from config_rom import ConfigInvalide
    genre = l.get("type")
    if genre not in LOOT:
        raise ConfigInvalide(ou + " : type %r, attendu objet, or, embuscade "
                             "ou rien" % (genre,))
    if genre == "objet":
        o = _entier(l, "objet", ou)
        if o not in cat:
            raise ConfigInvalide(ou + " : objet %d inconnu du jeu" % o)
        if o in refuses:
            raise ConfigInvalide(ou + " : %s est un objet de quete ou de "
                                 "debug, il casserait la partie" % nm.get(o, o))
        return o
    return _entier(l, {"or": "or", "embuscade": "embuscade"}.get(genre, "valeur"),
                   ou)


def lignes_voulues(rom, nom, lignes, verrous):
    """Les outcomes d'une table de la section, controles. Leve
    ConfigInvalide."""
    from config_rom import ConfigInvalide
    cat = objets.catalogue(rom)
    nm = objets.noms(rom, "en")
    refuses = interdits(rom) if verrous else set()
    if not isinstance(lignes, list) or not lignes:
        raise ConfigInvalide("%s : liste de lignes attendue" % nom)
    if len(lignes) > MAX_TABLE:
        raise ConfigInvalide("%s : %d lignes, le jeu en tient %d"
                             % (nom, len(lignes), MAX_TABLE))
    out, par_rang = [], {}
    for k, l in enumerate(lignes):
        ou = "%s[%d]" % (nom, k)
        if not isinstance(l, dict):
            raise ConfigInvalide(ou + " : objet attendu")
        rang = _entier(l, "rang", ou, 0, 31)
        pct = _entier(l, "pct", ou, 0, 100)
        v = _valeur(l, ou, cat, refuses, nm)
        par_rang.setdefault(rang, []).append(pct)
        out.append(dict(rang=rang, pct=pct, id=v, loot=LOOT[l["type"]]))
    for rang, p in sorted(par_rang.items()):
        if len(p) > MAX_RANG:
            raise ConfigInvalide("%s : rang %d, %d lignes, le jeu en lit %d"
                                 % (nom, rang, len(p), MAX_RANG))
        if sum(p) > 100:
            raise ConfigInvalide("%s : rang %d, %d %% au total"
                                 % (nom, rang, sum(p)))
    return out


def ecrire_tables(rom, voulues):
    """{membre: outcomes} -> treasure.nsarc, si une table change. Rend le
    nombre de lignes changees."""
    arc = _arc(rom)
    membres = T.membres_narc(arc)
    neuves, n = {}, 0
    for table, lignes in voulues.items():
        deb, fin = membres[table]
        avant = [o for _off, o in T.outcomes(arc, deb)]
        if avant == lignes:
            continue
        n += max(len(avant), len(lignes)) - sum(a == b for a, b in zip(avant, lignes))
        neuves[table] = T.reconstruire_table(arc, deb, fin, lignes)
    if neuves:
        rom.files[rom.filenames.idOf(CHEMIN)] = T.reconstruire_narc(arc, neuves)
    return n


def vanilla_si_egale(rom, vanilla):
    """L'archive revenue membre pour membre a la vanilla en reprend les
    octets (la reconstruction ne les rend pas forcement)."""
    if vanilla is None:
        return
    a, v = _arc(rom), _arc(vanilla)
    if a == v:
        return
    ma, mv = T.membres_narc(a), T.membres_narc(v)
    if set(ma) == set(mv) and all(a[ma[k][0]:ma[k][1]].rstrip(b"\xff")
                                  == v[mv[k][0]:mv[k][1]].rstrip(b"\xff")
                                  for k in ma):
        rom.files[rom.filenames.idOf(CHEMIN)] = v


def appliquer(rom, section, verrous=True, vanilla=None):
    from config_rom import ConfigInvalide
    cat = objets.catalogue(rom)
    nm = objets.noms(rom, "en")
    importants = objets.objets_importants(rom)
    refuses = interdits(rom) if verrous else set()
    voulues = {TABLE_DE[t]: lignes_voulues(rom, "coffres." + t, section.get(t),
                                           verrous)
               for t in ("bleus", "pots")}
    # LES CONTENEURS, en place dans les scripts de zone (avant de
    # reconstruire les tables : les positions sont celles de l'archive lue)
    arc = bytearray(_arc(rom))
    n = 0
    for nom, genre, champ in (("rouges", 0, None),
                              ("rangs", 4, "rang_coffre")):
        lot = sorted(_conteneurs(rom, genre).items(),
                     key=lambda x: (x[1][0][0], x[0]))
        lignes = section.get(nom)
        if not isinstance(lignes, list) or len(lignes) != len(lot):
            raise ConfigInvalide("coffres.%s : %d cases attendues"
                                 % (nom, len(lot)))
        for k, (l, (uid, places)) in enumerate(zip(lignes, lot)):
            ou = "coffres.%s[%d]" % (nom, k)
            if _entier(l, "uid", ou) != uid:
                raise ConfigInvalide(ou + " : coffre %d attendu" % uid)
            c0 = places[0][1]
            if champ:
                v = _entier(l, champ, ou, 0, 31)
            else:
                if l.get("type") != TYPES[c0["loot"]]:
                    raise ConfigInvalide(ou + " : type %r, le coffre donne %s"
                                         % (l.get("type"), TYPES[c0["loot"]]))
                # un objet deja en place n'est pas refuse : la clef magique
                # reste dans son coffre
                v = _valeur(l, ou, cat, refuses - {c0["item"]}, nm)
                if (verrous and c0["loot"] == T.TYPE_OBJET
                        and c0["item"] in importants and v != c0["item"]):
                    raise ConfigInvalide(ou + " : ce coffre garde %s, sans "
                                         "lui le jeu ne se finit pas"
                                         % nm.get(c0["item"], c0["item"]))
            for _z, c in places:
                if c["item"] != v:
                    T.ecrire_u32(arc, c["off_packed"], T.encoder_packed(uid, v))
            n += c0["item"] != v
    if bytes(arc) != _arc(rom):
        rom.files[rom.filenames.idOf(CHEMIN)] = bytes(arc)
    n += ecrire_tables(rom, voulues)
    vanilla_si_egale(rom, vanilla)
    # LES DROPS, en place
    fm = rom.filenames.idOf(CHEMIN_MONSTRES)
    mon = bytearray(rom.files[fm])
    lot = _drops(rom)
    lignes = section.get("drops")
    if not isinstance(lignes, list) or len(lignes) != len(lot):
        raise ConfigInvalide("coffres.drops : %d cases attendues" % len(lot))
    for k, (l, (m, off, genre, o)) in enumerate(zip(lignes, lot)):
        ou = "coffres.drops[%d]" % k
        if (_entier(l, "monstre", ou), l.get("emplacement")) != (m, genre):
            raise ConfigInvalide(ou + " : monstre %d, objet %s attendus"
                                 % (m, genre))
        v = _valeur(dict(l, type="objet"), ou, cat, refuses, nm)
        if v != o:
            struct.pack_into("<H", mon, MON_ENTETE + m * MON_ENREG + off, v)
            n += 1
    if bytes(mon) != bytes(rom.files[fm]):
        rom.files[fm] = bytes(mon)
    return n
