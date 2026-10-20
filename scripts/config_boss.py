"""La categorie `boss` de « Creer sa ROM » (ZER-88) : chaque combat scripte,
case par case, pour `config_rom`.

LES CASES. Une par emplacement de monstre d'`eventbattle.bin`, sauf le
prologue (enregistrement 0, jamais touche, randomizer.PROLOGUE) :

    histoire  32  les boss du scenario et des quetes (Aquila et Corvus des
                  cinematiques compris, verrouilles : leurs combats sont mis
                  en scene, randomizer.CINEMATIQUES)
    grottes   12  les boss des antres (evenements 34-45)
    legendes  45  les boss legendaires, trois niveaux (evenements 46-84) ;
                  les trois combats de Mortamor portent trois boss chacun
    autres    20  les monstres ORDINAIRES des combats scriptes, que `--boss`
                  permute aussi : sans eux, le fichier n'ecrirait pas tout

Une case vaut une espece (un boss ou un monstre du bestiaire : --boss-mixte
en met) et un tirage : `fixe`, ou `visite` -- le blob tire alors un boss neuf
a chaque visite (greffe 0x020740B8, patch_blob). L'espece d'une case
`visite` reste ecrite : c'est celle du combat la ou le blob n'est pas monte.
TOUTE CASE PEUT VALOIR `visite`, histoire et monstres ordinaires compris
(joueur, 19/10/2026 : « laisse choisir le joueur, tu mets trop de
barriere »). Le blob tire alors dans le pool des boss.

UN COMBAT, DEUX CASES : l'evenement 1 a deux enregistrements (Sylvane,
rang 3, et un combat ordinaire, rang 97). Le blob tire par evenement et
emplacement : si l'une des deux cases vaut `visite`, les deux le sont
(l'onglet les change ensemble).

PAS DE SYMBOLE A SUIVRE. Mesure du 19/10/2026 sur la vanilla : aucune des 89
especes de boss ne figure dans encfld, encbtl ou encmons ; chacune figure une
fois, dans eventbattle. Ecrire eventbattle suffit.

LES TIRAGES A CHAQUE VISITE vivent dans le blob (`dq9rand.bin`), qui est
assemble AVANT que `--config` s'applique. `preparer_blob` donne donc au
randomizer, avant l'assemblage, le pool et la table que la config demande ;
`appliquer` ne fait ensuite que verifier que le blob de la ROM tire bien
les cases `visite`, et elles seules.
"""
import os
import random
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import categories_boss as CB

CHEMIN = "data/event/eventbattle.bin"
TABLES = ("histoire", "grottes", "legendes", "autres")
TIRAGES = ("fixe", "visite")
PROLOGUE_ENREG = 0
CINEMATIQUES = (800, 801)
ENREG_CINEMATIQUES = (12, 26)         # evenements 131 et 135
VIDE = 0xFFFFFFFF
# LES EMPLACEMENTS DE BOSS, par rang d'enregistrement (le randomizer ne
# reordonne jamais le fichier) : l'emplacement 0, sauf ou c'est dit.
# Recontroles sur la vanilla par verifier_cases().
ENREG_BOSS = (list(range(1, 15)) + [18, 19] + list(range(23, 39))
              + list(range(43, 94)))
EMPL_BOSS = {19: (1,), 63: (0, 1, 2), 76: (0, 1, 2), 89: (0, 1, 2)}
# Les niveaux 2 et 3 des legendes (ZER-76), pour les etiquettes.
LEGENDES_NIV2 = frozenset((600, 602, 606, 610, 615, 622, 628, 633, 778, 639,
                           776, 770, 645, 650, 655))
LEGENDES_NIV3 = frozenset((601, 604, 608, 612, 618, 624, 630, 635, 779, 641,
                           777, 773, 647, 652, 658))
# LES ANTRES (ZER-37) : ce que tire la greffe de `--boss` seul.
ANTRES = frozenset((e, 0) for e in CB.EVT_GROTTES)


# --- lecture -----------------------------------------------------------------

def _table(rom):
    from prmtable import PrmTable
    return PrmTable(rom.files[rom.filenames.idOf(CHEMIN)])


def _famille(evt):
    return ("grottes" if evt in CB.EVT_GROTTES else
            "legendes" if evt in CB.EVT_LEGENDES else "histoire")


def _ids(rom):
    """Les identifiants d'espece, par rang d'enregistrement (mon_btldata)."""
    from montable import CHEMIN as BTL, TableMonstres
    return [m.id for m in TableMonstres(rom.files[rom.filenames.idOf(BTL)])]


def _valides(rom):
    return set(_ids(rom)) - {0}


def cases(records, ids=None):
    """[(table, rang, emplacement 0..2, evenement)] dans l'ordre du fichier,
    table par table. `ids` : les especes valides, pour la table `autres`
    (un emplacement vide vaut 0xFFFFFFFF)."""
    boss = {(r, k) for r in ENREG_BOSS for k in EMPL_BOSS.get(r, (0,))}
    out = {t: [] for t in TABLES}
    for r, rec in enumerate(records):
        if r == PROLOGUE_ENREG or rec.tag != 0x64 or len(rec.fields) != 9:
            continue
        for k in range(3):
            v = rec.fields[1 + 2 * k]
            if (r, k) in boss:
                out[_famille(rec.fields[0])].append((r, k, rec.fields[0]))
            elif ids is not None and v != VIDE and v in ids:
                out["autres"].append((r, k, rec.fields[0]))
    return [(t, r, k, e) for t in TABLES for r, k, e in out[t]]


NB = dict(histoire=32, grottes=12, legendes=45, autres=20)
# LA FORME DE LA SECTION, pour l'onglet (comme patch_medailles.FORME). Les
# deux cases des cinematiques : leurs rangs dans la table `histoire`.
_HIST = [r for r in ENREG_BOSS if r < 43]
FORME = dict(tables=tuple((t, NB[t]) for t in TABLES),
             champs=(("espece", "espece"), ("tirage", "tirage")),
             verrous={("histoire", _HIST.index(r), c)
                      for r in ENREG_CINEMATIQUES for c in ("espece", "tirage")})


def noms(rom, langue="en"):
    """{identifiant: nom} des especes, tels que le jeu les affiche."""
    import monnames
    from objets import _membre_archive
    d = _membre_archive(rom, "data/prm/mon_data.gp2", "mon_data_%s.nat" % langue)
    return {i: e["nom"] for i, e in zip(_ids(rom), monnames.lire_table(d))
            if e["nom"]}


def genre(espece):
    """'histoire', 'grottes', 'legendes1/2/3' ou 'monstre'."""
    c = CB.categorie(espece)
    if c == "legendes":
        return "legendes%d" % (3 if espece in LEGENDES_NIV3 else
                               2 if espece in LEGENDES_NIV2 else 1)
    return c or "monstre"


def especes_choisissables(rom, langue="en", verrous=True):
    """[(identifiant, nom, genre)] de ce qu'une case peut recevoir : les boss,
    puis le bestiaire, par nom. Avec les verrous, ni Aquila ni Corvus des
    cinematiques (9999 PV : un combat ingagnable, 11/10/2026)."""
    from monstres_nommes import MONSTRES
    ids = _ids(rom)
    nm = noms(rom, langue)
    boss = set(CB.HISTOIRE | CB.GROTTES | CB.LEGENDES)
    if verrous:
        boss -= set(CINEMATIQUES)
    bestiaire = {ids[i] for i in MONSTRES if i < len(ids)}
    out = [(i, nm.get(i, "#%d" % i), genre(i)) for i in boss | bestiaire]
    rang = {"histoire": 0, "grottes": 1, "legendes1": 2, "legendes2": 2,
            "legendes3": 2, "monstre": 3}
    return sorted(out, key=lambda x: (rang[x[2]], x[1].lower(), x[0]))


# --- le blob -----------------------------------------------------------------

def _blob(rom):
    """Les octets de `dq9rand.bin`, ou None (pas de --blob)."""
    from patch_amorce import NOM_BLOB

    def chercher(dossier, chemin=""):
        for k, nom in enumerate(dossier.files):
            if nom == NOM_BLOB:
                return dossier.firstID + k
        for nom, sd in dossier.folders:
            f = chercher(sd)
            if f is not None:
                return f
        return None
    fid = chercher(rom.filenames)
    return None if fid is None else bytes(rom.files[fid])


def visites(rom):
    """L'ensemble des (evenement, emplacement) que le blob de `rom` tire a
    chaque visite. Vide sans blob, ou si sa greffe d'antre n'est pas posee.

    DISPOSITION (patch_blob.construire) : apres l'en-tete, les mots, les
    modeles et les tableaux ; puis `antres` (un compte et ses especes),
    `cache_antres` (douze u16), et `boss_t`, la table de tirage_boss, si les
    options de la 1.6 l'ont posee -- le pool d'antres est alors vide."""
    import patch_blob
    import tirage_boss as TB
    b = _blob(rom)
    if b is None:
        return set()
    o = patch_blob.BASE + 4 * (patch_blob.MOTS_N + 2 * patch_blob.MODELES_N)
    n = struct.unpack_from("<I", b, o)[0]
    if n:
        return set(ANTRES)
    if not _greffe_posee(b):
        return set()
    t = b[o + 4 + 2 * patch_blob.ANTRE_N:]
    nf, _m, _r, nevt = t[0], t[1], t[2], t[3]
    if not 1 <= nf <= 3 or nevt != TB.NEVT:
        raise ValueError("dq9rand.bin : table des boss illisible")
    masques = TB.relire(t)[2]
    return {(e, k) for e in range(len(masques)) for k in range(3)
            if masques[e] & (1 << k)}


# Le mot que la greffe d'antre remplace (0x020740B8, ARM9) : `strh r0,
# [r1, #2]`, lu dans la vanilla. La table des sites du blob le garde pour le
# desinstalleur.
ORIGINE_ANTRE = 0xE1C100B2


def _greffe_posee(b):
    """Vrai si la table des sites du blob porte la greffe d'antre : le site,
    sa cible, puis le mot d'origine."""
    import patch_blob
    site = struct.pack("<I", patch_blob.SITE_ANTRE)
    p = b.find(site)
    while p >= 0:
        if p % 4 == 0 and b[p + 8:p + 12] == struct.pack("<I", ORIGINE_ANTRE):
            return True
        p = b.find(site, p + 1)
    return False


def _visites_section(section):
    return {(l["evenement"], l["emplacement"] - 1)
            for t in TABLES for l in section.get(t, ())
            if l.get("tirage") == "visite"}


def pool_defaut(garder_premier=False, legacy_tous=False):
    """Le pool de `--boss` seul (randomizer.py : cibles_boss), trie."""
    garde = set(CINEMATIQUES) | ({300} if garder_premier else set())
    exclus = set() if legacy_tous else CB.LEGENDES_HAUTES
    return sorted((CB.HISTOIRE | CB.GROTTES | CB.LEGENDES) - garde - exclus)


def preparer_blob(section, antres, tirage, blob, defaut):
    """Ce que le blob doit tirer pour la section `boss` d'une config.

    `antres`, `tirage` : ce que les options ont prepare (pool de ZER-37, ou
    table de tirage_boss) ; `defaut` : le pool si aucun des deux. Rend le
    couple (antres, tirage) a passer a patch_amorce. Les memes cases `visite`
    que les options : rien ne change, la ROM est celle des options."""
    import tirage_boss as TB
    from config_rom import ConfigInvalide
    voulu = _visites_section(section)
    if voulu and not blob:
        raise ConfigInvalide("boss : << tire a chaque visite >> demande le "
                             "blob (monstres en mode aleatoire)")
    if tirage:
        fams, monstres, masques, retenir = TB.relire(tirage)
        actuel = {(e, k) for e in range(len(masques)) for k in range(3)
                  if masques[e] & (1 << k)}
    else:
        actuel = set(ANTRES) if antres else set()
    if voulu == actuel:
        return antres, tirage
    if not voulu:
        return None, None
    if not tirage and voulu == ANTRES:
        return list(antres or defaut), None
    if not tirage:
        fams, monstres, retenir = [sorted(antres or defaut)], [], True
    masques = bytearray(TB.NEVT)
    for e, k in voulu:
        masques[e] |= 1 << k
    return None, TB.table(fams, monstres, masques, retenir)


# --- l'affectation (config_rom) ----------------------------------------------

def interdits(rom):
    return set(CINEMATIQUES)


def tirer_section(rom, graine, langue="en", garder_premier=True, egales=False,
                  histoire=False, mixte=False, chaque_combat=False,
                  legacy_tous=False, seuils=None, blob=True):
    """Tire la categorie seule (rom vanilla, non modifiee) avec les options
    de l'onglet Boss, par tirage_boss.plan. Les monstres ordinaires des
    combats scriptes restent ceux de la vanilla."""
    import tirage_boss as TB
    records = _table(rom).records
    garde = set(CINEMATIQUES) | ({300} if garder_premier else set())
    pool = sorted((CB.HISTOIRE | CB.GROTTES | CB.LEGENDES) - garde)
    monstres = []
    if mixte:
        from patch_hasard import especes_tirables
        monstres = [i for i in especes_tirables() if i not in garde]
    corresp, table = TB.plan(
        random.Random(graine), pool, monstres, records, histoire=histoire,
        egales=egales and not histoire, mixte=mixte,
        chaque_combat=chaque_combat and blob,
        exclus=frozenset() if legacy_tous or histoire else CB.LEGENDES_HAUTES,
        seuils=None if histoire else seuils)
    vis = set()
    if table and blob:
        m = TB.relire(table)[2]
        vis = {(e, k) for e in range(len(m)) for k in range(3)
               if m[e] & (1 << k)}
    sec = exporter(rom, langue)
    nm = noms(rom, langue)
    for t in TABLES[:3]:
        for l in sec[t]:
            e = corresp.get(l["espece"], l["espece"])
            l.update(espece=e, nom=nm.get(e, ""),
                     tirage="visite" if (l["evenement"], l["emplacement"] - 1)
                     in vis else "fixe")
    return sec


def exporter(rom, langue="en"):
    """La section `boss` du fichier de configuration, lue dans la ROM."""
    records = _table(rom).records
    nm = noms(rom, langue)
    vis = visites(rom)
    out = {t: [] for t in TABLES}
    for t, r, k, evt in cases(records, _valides(rom)):
        e = records[r].fields[1 + 2 * k]
        out[t].append({"evenement": evt, "emplacement": k + 1, "espece": e,
                       "nom": nm.get(e, ""),
                       "tirage": "visite" if (evt, k) in vis else "fixe"})
    return out


def appliquer(rom, section, verrous=True, vanilla=None):
    """Ecrit la section `boss` dans eventbattle. Leve ConfigInvalide si une
    case n'est pas une espece du jeu ; avec `verrous`, aussi si elle touche
    aux combats des cinematiques ou y emmene leurs boss. Rend le nombre de
    cases changees."""
    from config_rom import ConfigInvalide
    t = _table(rom)
    records = t.records
    ids = _valides(rom)
    attendu = {}
    for tb, r, k, evt in cases(records, ids):
        attendu.setdefault(tb, []).append((r, k, evt))
    vis_rom = visites(rom)
    ecrire, n = {}, 0
    for tb in TABLES:
        lignes = section.get(tb)
        if not isinstance(lignes, list) or len(lignes) != len(attendu[tb]):
            raise ConfigInvalide("boss.%s : %d cases attendues"
                                 % (tb, len(attendu[tb])))
        for i, (l, (r, k, evt)) in enumerate(zip(lignes, attendu[tb])):
            ou = "boss.%s[%d]" % (tb, i)
            try:
                e, ev, em = int(l["espece"]), int(l["evenement"]), int(l["emplacement"])
                tir = l.get("tirage", "fixe")
            except (KeyError, TypeError, ValueError):
                raise ConfigInvalide(ou + " : 'espece', 'evenement' et "
                                     "'emplacement' entiers attendus")
            if (ev, em) != (evt, k + 1):
                raise ConfigInvalide(ou + " : evenement %d emplacement %d "
                                     "attendus" % (evt, k + 1))
            if e not in ids:
                raise ConfigInvalide(ou + " : espece %d inconnue du jeu" % e)
            if tir not in TIRAGES:
                raise ConfigInvalide(ou + " : tirage %r, attendu fixe ou "
                                     "visite" % (tir,))
            avant = records[r].fields[1 + 2 * k]
            if verrous and (avant in CINEMATIQUES or e in CINEMATIQUES) \
                    and (e != avant or tir != "fixe"):
                raise ConfigInvalide(ou + " : Aquila et Corvus des "
                                     "cinematiques restent a leur place, et "
                                     "seulement la")
            if e != avant:
                ecrire[(r, k)] = e
            if e != avant or ((evt, k) in vis_rom) != (tir == "visite"):
                n += 1
    # LE BLOB A ETE PREPARE PAR preparer_blob : on verifie qu'il tire bien
    # ces cases-la. Sans blob (ROM vanilla de l'onglet), rien a verifier.
    if _blob(rom) is not None and _visites_section(section) != vis_rom:
        raise ConfigInvalide("boss : le blob de la ROM ne tire pas les cases "
                             "<< visite >> du fichier")
    for (r, k), e in ecrire.items():
        t.set_field(r, 1 + 2 * k, e)
    # LA MUSIQUE SUIT LE BOSS POSE (ZER-94), comme a la construction : elle
    # ne s'exporte pas, elle se deduit des especes.
    import musique_boss
    if musique_boss.accorder(t) or ecrire:
        rom.files[rom.filenames.idOf(CHEMIN)] = bytes(t.data)
    return n


def verifier_cases(rom):
    """Leve si les cases ne sont pas celles de la vanilla `rom` : 89 boss
    ranges dans leur famille, 20 monstres ordinaires."""
    records = _table(rom).records
    c = cases(records, _valides(rom))
    for tb in TABLES:
        nb = sum(1 for x in c if x[0] == tb)
        if nb != NB[tb]:
            raise AssertionError("config_boss : %d cases %s, %d attendues"
                                 % (nb, tb, NB[tb]))
    for tb, r, k, _e in c:
        v = records[r].fields[1 + 2 * k]
        g = CB.categorie(v)
        if (tb == "autres") != (g is None) or (g and g != tb):
            raise AssertionError("config_boss : espece %d en %s" % (v, tb))
        if g == "legendes" and genre(v) != "legendes%d" % (
                1 if r < 68 else 2 if r < 81 else 3):
            raise AssertionError("config_boss : niveau de %d" % v)
    import ndspy.codeCompression as cc
    import patch_blob
    arm9 = cc.decompress(bytes(rom.arm9))
    mot = struct.unpack_from("<I", arm9, patch_blob.SITE_ANTRE - 0x02000000)[0]
    if mot != ORIGINE_ANTRE:
        raise AssertionError("config_boss : %08x en 0x020740B8, %08x attendu"
                             % (mot, ORIGINE_ANTRE))
