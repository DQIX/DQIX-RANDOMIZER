#!/usr/bin/env python3
"""Randomize le stock des boutiques, dans `data/bin/menu/shopdata1.bin`.

Format, lieux et prix : `boutiques.py` et `docs/research/11-shops.md` 83.

LA REGLE, emplacement par emplacement : un emplacement qui vend une arme
recoit une arme, un bouclier un bouclier, un accessoire un accessoire, un
objet courant un objet courant. C'est la seule regle, et elle suffit a tenir
les trois demandes du joueur d'un coup :

  - le TYPE de la boutique est respecte (un armurier ne vend pas d'epee) ;
  - le RATIO accessoires / objets courants de chaque epicerie est conserve au
    nombre pres, puisqu'on remplace un accessoire par un accessoire ;
  - les ETALS MIXTES restent mixtes dans les memes proportions (six boutiques
    "general", deux "armes + armures", une melangee).

Les autres invariants :

  - AUCUN OBJET IMPORTANT (les 88 de `objets.objets_importants`). Le vanilla
    n'en vend aucun, on garde l'invariant.
  - AUCUN OBJET A PRIX NUL. 241 des 1090 objets autorises n'ont pas de prix :
    ce sont ceux que le jeu ne met jamais en vente (heaumes de quete, tenues
    uniques, ingredients d'alchimie). Places dans un etal, ils s'achetent
    GRATUITEMENT -- mesure sur la premiere construction : l'arc de cherubin a
    0 po dans l'armurerie d'Ablithia. Le vanilla n'en vend aucun des 330 : la
    regle ne fait donc que suivre le jeu.
  - la MINI MEDAILLE et le SET DU DRACOGUERRIER (`JAMAIS`), quoi qu'il arrive.
  - pas deux fois le meme objet dans une meme boutique -- aucune boutique
    vanilla n'a de doublon interne.
  - le nombre d'articles ne bouge pas : un emplacement vide reste vide. Le
    menu liste par pages de six et les comptes vanilla sont 18, 12, 6 et 1.

LES BOUTIQUES A PART, decisions du joueur (docs/PLAN.md phase 7) :

  id=30   Cote de l'Exil, le CHRONOCRISTAL, seule boutique hors ville connue :
          on n'y touche pas du tout.
  id=33   la boutique SECRETE de Pontaudy,
  id=35   Ablithia armures 2,
  id=37   Ablithia armes 2   -- ces deux-la ne s'ouvrent qu'apres le boss final.
          Les trois sont les boutiques du rare : leur pool est restreint aux
          objets de ETOILES_RARE etoiles et plus, et leur pourcentage de prix
          passe a 500 %. Ce sont les seuls prix qu'on touche, et on les touche
          par le pourcentage de la boutique, jamais par la fiche d'un objet --
          un prix modifie dans la fiche vaudrait pour tout le jeu.

  id=12 (Pontaudy objets) et id=34 gardent leurs 500 % vanilla : la ville de
  voleurs vend cher, c'est un trait du lieu.

TOUT SE REECRIT EN PLACE : 559 mots de 32 bits deja presents, plus deux
pourcentages. Aucune taille de fichier ne change, donc la disposition de la
ROM est preservee et les savestates restent valides (meme propriete que 79.9).
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import boutiques as B
import objets
import treasure as T

# JAMAIS EN BOUTIQUE, decision du joueur du 18 septembre 2026. Ces objets n'ont
# pas de prix en vanilla ; le jour ou on leur en donnera un, ils resteront
# malgre tout hors des etals, parce qu'un etal les rendrait achetables en
# boucle :
#   - la MINI MEDAILLE : on acheterait les recompenses du collectionneur ;
#   - le SET DU DRACOGUERRIER, donne lors d'un evenement.
# Les 26 livres de competence, eux, sont ENTREES en boutique le 18 septembre :
# le joueur les veut achetables, au prix fort (voir `patch_prix.py`).
MINI_MEDAILLE = 22039
SET_DRACOGUERRIER = (12785, 13162, 15286, 16256, 17303)
JAMAIS = {MINI_MEDAILLE} | set(SET_DRACOGUERRIER)

# L'ORDRE DE L'ETAL. Le jeu range ses propres etals ainsi (releve sur la
# boutique de Cherubelle) : les objets courants, puis les armes, puis
# l'equipement du haut vers le bas, les accessoires a la fin.
ORDRE_FAMILLES = ("item", "weapon", "shield", "head", "torso", "arms",
                  "legs", "feet", "accessory")

INTOUCHABLES = {30}
RARES = {33, 35, 37}

# LA RARETE, decidee par le joueur le 18 septembre apres essai : les 4 et 5
# etoiles ne doivent se trouver QUE dans les trois boutiques du rare. Les
# trente-trois autres etals s'arretent a 3 etoiles.
ETOILES_ORDINAIRE_MAX = 3
ETOILES_RARE_MIN = 4

# POURCENTAGE DE CHAQUE BOUTIQUE DU RARE, choisi par le joueur apres essai en
# jeu : 800 % partout. Les 2000 % de l'essai du million donnaient des prix
# demesures a cote du reste du jeu. Un dictionnaire plutot qu'une constante :
# les trois ont deja eu des valeurs differentes, et en reprendre une seule se
# fait ici, sur une ligne.
PCT_RARE = {33: 800, 35: 800, 37: 800}


class Pioche(object):
    """Tirage sans remise, paquet reconstitue quand il est vide.

    Meme raison que dans `patch_loot.py` : avec `rng.choice`, un objet sort
    trois fois pendant qu'un autre ne sort jamais. Ici le paquet est par
    famille, et chaque boutique refuse en plus ses propres doublons.
    """

    def __init__(self, rng, pool):
        self.rng = rng
        self.pool = list(pool)
        self.paquet = []

    def tirer(self, interdits):
        """Rend un objet du pool qui n'est pas dans `interdits`."""
        for _ in range(4 * len(self.pool) + 8):
            if not self.paquet:
                self.paquet = list(self.pool)
                self.rng.shuffle(self.paquet)
            o = self.paquet.pop()
            if o not in interdits:
                return o
        raise AssertionError("pool trop petit : %d objets, %d interdits"
                             % (len(self.pool), len(interdits)))


def vendable(rom, langue="en"):
    """Les objets qu'une boutique peut vendre : autorises ET tarifes.

    `objets.pool()` rend le catalogue moins les 88 objets importants. On en
    retire ceux dont le prix d'achat ou de vente est nul : le jeu ne les met
    jamais en vente, et un etal les donnerait pour rien.
    """
    achat = B.prix_achat(rom)
    vente = B.prix_catalogue(rom)
    return {i for i in objets.pool(rom, langue)
            if i not in JAMAIS
            and achat.get(i, 0) > 0 and vente.get(i, 0) > 0}


def _rang(ident, cat, achat):
    """Cle de tri d'un article : famille, puis TYPE D'ARME, puis prix croissant.

    Le type d'arme se lit dans le NUMERO de l'objet, par tranche de cent :
    19000 dagues, 19100 marteaux, 20000 epees, 20100 eventails, 20200 haches,
    20300 fouets, 20400 baguettes, 20500 lances, 20600 batons, 20700
    boomerangs, 20800 griffes, 20900 arcs. Verifie sur les 268 armes contre la
    classification du save editor de la communaute (`DQIX/editor`,
    `src/game/data.js`) : aucune tranche ne melange deux types.
    """
    fam = B._cat_objet(cat[ident])
    return (ORDRE_FAMILLES.index(fam) if fam in ORDRE_FAMILLES else 99,
            ident // 100, achat.get(ident, 0), ident)


def pools(rom, langue="en"):
    """{famille: [identifiants]} et {famille: [identifiants 3 etoiles et +]}.

    Le pool part de `vendable()` puis se range par famille large (arme,
    bouclier, torse...).
    """
    permis = vendable(rom, langue)
    cat = objets.catalogue(rom)
    etoiles = objets.raretes(rom, langue)
    ordinaire, rare = {}, {}
    for ident, entree in sorted(cat.items()):
        if ident not in permis:
            continue
        fam = B._cat_objet(entree)
        n = etoiles.get(ident, 0)
        if n <= ETOILES_ORDINAIRE_MAX:
            ordinaire.setdefault(fam, []).append(ident)
        if n >= ETOILES_RARE_MIN:
            rare.setdefault(fam, []).append(ident)
    return ordinaire, rare


def _verifier_pools(etals, cat, ordinaire, rare):
    """Chaque boutique doit pouvoir etre remplie sans doublon. On le verifie
    AVANT d'ecrire quoi que ce soit, plutot que d'echouer au milieu."""
    for e in etals:
        if e["id"] in INTOUCHABLES:
            continue
        pool = rare if e["id"] in RARES else ordinaire
        besoin = {}
        for ident in e["objets"]:
            if ident:
                fam = B._cat_objet(cat[ident])
                besoin[fam] = besoin.get(fam, 0) + 1
        for fam, n in sorted(besoin.items()):
            if len(pool.get(fam, ())) < n:
                raise AssertionError(
                    "boutique %d : %d emplacements de famille %s, pool de %d"
                    % (e["id"], n, fam, len(pool.get(fam, ()))))


def patcher(rom, rng, langue="en", journal=None):
    """Reecrit le stock des boutiques. Rend un dictionnaire de comptes."""
    def note(ligne=""):
        if journal is not None:
            journal.write(ligne + "\n")

    d, etals = B.lire(rom)
    cat = objets.catalogue(rom)
    achat = B.prix_achat(rom)
    noms = objets.noms(rom, langue)
    etoiles = objets.raretes(rom, langue)
    ordinaire, rare = pools(rom, langue)
    pioches = {f: Pioche(rng, p) for f, p in ordinaire.items()}
    pioches_rares = {f: Pioche(rng, p) for f, p in rare.items()}

    _verifier_pools(etals, cat, ordinaire, rare)

    buf = bytearray(d)
    comptes = dict(boutiques=0, articles=0, intouchables=0, rares=0, prix=0)

    note("=== BOUTIQUES ===")
    for e in etals:
        if e["id"] in INTOUCHABLES:
            comptes["intouchables"] += 1
            note("boutique id=%-2d INTOUCHEE (%d article(s))"
                 % (e["id"], sum(1 for o in e["objets"] if o)))
            continue

        ce_rare = e["id"] in RARES
        tirage = pioches_rares if ce_rare else pioches
        comptes["boutiques"] += 1
        if ce_rare:
            comptes["rares"] += 1
        note("boutique id=%-2d %-14s %d%%%s"
             % (e["id"], B.CATEGORIE.get(e["categorie"], "?"),
                PCT_RARE[e["id"]] if ce_rare else e["pct"],
                "   [boutique du rare, %d etoiles et +]" % ETOILES_RARE_MIN
                if ce_rare else ""))

        deja, tires = set(), []
        for ident in e["objets"]:
            if not ident:
                continue
            fam = B._cat_objet(cat[ident]) if ident in cat else None
            if fam is None or fam not in tirage:
                raise AssertionError("famille inconnue pour l'objet %d" % ident)
            choisi = tirage[fam].tirer(deja)
            deja.add(choisi)
            tires.append(choisi)

        # ON RANGE L'ETAL : par famille, puis par type d'arme, puis par prix
        # croissant. Demande du joueur -- une liste de dix-huit articles pris au
        # hasard est illisible en jeu, d'autant qu'elle se lit par pages de six.
        tires.sort(key=lambda o: _rang(o, cat, achat))
        remplis = [off for ident, off in zip(e["objets"], e["offsets"]) if ident]
        for slot, (off, choisi) in enumerate(zip(remplis, tires)):
            T.ecrire_u32(buf, off, choisi)
            comptes["articles"] += 1
            note("   %2d %-9s %5d %-26s %s"
                 % (slot, B._cat_objet(cat[choisi]), choisi,
                    objets.nettoyer(noms.get(choisi, "?"))[:26],
                    "*" * etoiles.get(choisi, 0)))

        if ce_rare and e["pct"] != PCT_RARE[e["id"]]:
            T.ecrire_u32(buf, e["off_pct"], PCT_RARE[e["id"]])
            comptes["prix"] += 1
            note("   prix : %d %% -> %d %%" % (e["pct"], PCT_RARE[e["id"]]))

    if len(buf) != len(d):
        raise AssertionError("la taille du fichier a change")
    rom.files[rom.filenames.idOf(B.CHEMIN)] = bytes(buf)
    note()
    return comptes


# LA CLASSE DE PRIX (voir `patch_prix.py`) : la classe 2 n'affiche pas les gros
# montants -- un article a 800 000 y devient "Invendable", mesure en jeu le
# 20 septembre. La classe 5, si. Tant qu'on ne connait pas la borne exacte de la
# classe 2, on prend celle du u16 et on refuse de produire une ROM qui la
# franchirait.
CLASSE_PRIX = (0x04, 13, 7)
PLAFOND_CLASSE_2 = 65535


def classe_prix(rom):
    """{identifiant: classe de prix}, le champ de trois bits de la fiche."""
    off, dec, masque = CLASSE_PRIX
    out = {}
    for c in objets.CATEGORIES:
        d = objets._membre(rom, c, "en")
        n = struct.unpack_from("<H", d, 0)[0] & 0xFFF
        for i in range(n):
            base = objets.TETE + objets.ENREG * i
            ident = struct.unpack_from("<H", d, base + objets.OFF_ID)[0]
            out[ident] = (struct.unpack_from("<I", d, base + off)[0]
                          >> dec) & masque
    return out


def verifier(rom):
    """Controle de coherence sur une ROM deja patchee. Leve si ca cloche."""
    _d, etals = B.lire(rom)
    permis = vendable(rom)
    importants = set(objets.objets_importants(rom))
    cat = objets.catalogue(rom)
    etoiles = objets.raretes(rom)
    achat = B.prix_achat(rom)

    _dv, vanilla = B.lire(_rom_vanilla())
    par_id = {e["id"]: e for e in vanilla}
    classe = classe_prix(rom)
    achat = B.prix_achat(rom)

    for e in etals:
        ref = par_id[e["id"]]
        ids = [o for o in e["objets"] if o]
        if len(ids) != len(set(ids)):
            raise AssertionError("boutique %d : doublon interne" % e["id"])
        if [bool(o) for o in e["objets"]] != [bool(o) for o in ref["objets"]]:
            raise AssertionError("boutique %d : les emplacements tenus ont "
                                 "bouge" % e["id"])
        if e["id"] in INTOUCHABLES:
            if e["objets"] != ref["objets"] or e["pct"] != ref["pct"]:
                raise AssertionError("boutique %d : intouchable, et touchee"
                                     % e["id"])
            continue
        if e["id"] in RARES and e["pct"] != PCT_RARE[e["id"]]:
            raise AssertionError("boutique %d : %d %% au lieu de %d %%"
                                 % (e["id"], e["pct"], PCT_RARE[e["id"]]))
        if e["id"] not in RARES and e["pct"] != ref["pct"]:
            raise AssertionError("boutique %d : le prix a bouge" % e["id"])
        familles_avant = sorted(B._cat_objet(cat[o]) for o in ref["objets"] if o)
        familles_apres = sorted(B._cat_objet(cat[o]) for o in e["objets"] if o)
        if familles_avant != familles_apres:
            raise AssertionError("boutique %d : les familles vendues ont change"
                                 % e["id"])
        for article in e["objets"]:
            if not article:
                continue
            if classe.get(article, 0) == 0:
                raise AssertionError("boutique %d : %d est invendable "
                                     "(classe de prix nulle)"
                                     % (e["id"], article))
            affiche = achat.get(article, 0) * e["pct"] // 100
            if classe.get(article) == 2 and affiche > PLAFOND_CLASSE_2:
                raise AssertionError(
                    "boutique %d : %d a %d po en classe 2, la boutique "
                    "afficherait Invendable" % (e["id"], article, affiche))
        for neuf, avant in zip(e["objets"], ref["objets"]):
            if not avant:
                continue
            if neuf in importants:
                raise AssertionError("boutique %d : objet important %d en vente"
                                     % (e["id"], neuf))
            if neuf not in permis:
                raise AssertionError("boutique %d : objet %d hors pool "
                                     "vendable" % (e["id"], neuf))
            if achat.get(neuf, 0) <= 0:
                raise AssertionError("boutique %d : objet %d a prix nul"
                                     % (e["id"], neuf))
            if e["id"] in RARES and etoiles.get(neuf, 0) < ETOILES_RARE_MIN:
                raise AssertionError("boutique %d du rare : %d n'a que %d "
                                     "etoiles" % (e["id"], neuf,
                                                  etoiles.get(neuf, 0)))
            if e["id"] not in RARES and etoiles.get(neuf, 0) > ETOILES_ORDINAIRE_MAX:
                raise AssertionError("boutique %d du rare : %d n'a que %d "
                                     "etoiles" % (e["id"], neuf,
                                                  etoiles.get(neuf, 0)))
    return True


def _rom_vanilla():
    """La ROM vanilla, pour comparer emplacement par emplacement.

    `rom_vanilla` la cherche dans `banc/roms/` ou via la variable
    d'environnement `DQ9_VANILLA`.
    """
    import ndspy.rom
    import rom_vanilla
    return ndspy.rom.NintendoDSRom.fromFile(rom_vanilla.chemin_vanilla())


if __name__ == "__main__":
    import random
    import ndspy.rom
    if len(sys.argv) < 3:
        sys.exit("usage: patch_boutiques.py <rom.nds> <sortie.nds> [graine]")
    r = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    g = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 1)
    print(patcher(r, g, journal=sys.stdout))
    r.saveToFile(sys.argv[2])
    print("verification :", verifier(ndspy.rom.NintendoDSRom.fromFile(sys.argv[2])))
