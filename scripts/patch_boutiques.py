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

    def tirer(self, interdits, accepte=None):
        """Rend un objet du pool hors `interdits`, et que `accepte` valide."""
        for _ in range(8 * len(self.pool) + 16):
            if not self.paquet:
                self.paquet = list(self.pool)
                self.rng.shuffle(self.paquet)
            o = self.paquet.pop()
            if o not in interdits and (accepte is None or accepte(o)):
                return o
        raise AssertionError("pool trop petit : %d objets, %d interdits"
                             % (len(self.pool), len(interdits)))


# LE PLAFOND DE PRIX D'UNE BOUTIQUE VIENT DU JEU, PAS DE MON GOUT.
# Le vanilla range ses 37 etals par ordre d'histoire dans `shopdata1.bin`, et
# ce qu'ils vendent de plus cher monte avec la progression : 240 po au premier
# village, 840, 540, 1 750... jusqu'a 31 500 en fin de partie. On prend cette
# courbe telle quelle : une boutique ne vendra jamais plus cher que ce que le
# vanilla y vend deja. C'est la reponse a la demande du joueur -- une armurerie
# de debut de partie doit rester utilisable (ZER-31).
#
# LE PLANCHER sert l'autre bout : sans lui, une boutique de fin de partie se
# remplit d'herbes medicinales. On vise donc une fourchette, et on ne la
# desserre que si le pool n'a pas de quoi la remplir.
MARGE_PLAFOND = 1.0      # 1.0 = exactement le maximum du vanilla
PLANCHER_RATIO = 8       # plancher = plafond / 8


def plafonds_vanilla(rom, langue="en"):
    """{id de boutique: prix affiche le plus cher que le vanilla y vend}.

    Le prix affiche tient compte du pourcentage de l'etal : Pontaudy vend a
    500 %, son plafond est donc cinq fois le prix de base de son article le
    plus cher.
    """
    _d, etals = B.lire(rom)
    achat = B.prix_achat(rom)
    out = {}
    for e in etals:
        prix = [achat.get(o, 0) * e["pct"] // 100 for o in e["objets"] if o]
        if prix:
            out[e["id"]] = int(max(prix) * MARGE_PLAFOND)
    return out


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


class _Partout(dict):
    """Un pool unique, rendu quelle que soit la famille demandee.

    EN MODE CHAOS une armurerie peut vendre une epee, une epicerie une armure.
    Le reste du code interroge le pool par famille (`pool[fam]`, `pool.get(fam)`,
    `fam in pool`) : ce dictionnaire repond la meme liste a tout le monde, ce
    qui evite de disperser des `if chaos` dans le tirage et la verification.
    """

    def __init__(self, contenu):
        dict.__init__(self)
        self.contenu = list(contenu)

    def __getitem__(self, _famille):
        return self.contenu

    def get(self, _famille, _defaut=None):
        return self.contenu

    def __contains__(self, _famille):
        return True

    def items(self):
        return [(None, self.contenu)]


class _MemePioche(object):
    """Meme idee que `_Partout`, mais ce qu'il rend est LA pioche partagee."""

    def __init__(self, pioche):
        self.pioche = pioche

    def __getitem__(self, _famille):
        return self.pioche

    def get(self, _famille, _defaut=None):
        return self.pioche

    def __contains__(self, _famille):
        return True


def pools(rom, langue="en", chaos=False):
    """{famille: [identifiants]} et {famille: [identifiants 3 etoiles et +]}.

    Le pool part de `vendable()` puis se range par famille large (arme,
    bouclier, torse...).

    `chaos` : une seule reserve pour tout le monde, rarete comprise. La
    discipline du vanilla -- un armurier ne vend pas d'epee, les 3 etoiles et
    plus sont reservees aux trois boutiques du rare -- tombe.
    """
    permis = vendable(rom, langue)
    if chaos:
        tout = _Partout(sorted(permis))
        return tout, tout
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


def _verifier_pools(etals, cat, ordinaire, rare, classe, achat,
                    rares_actives=True, chaos=False):
    """Chaque boutique doit pouvoir etre remplie sans doublon, avec ce que son
    pourcentage lui permet d'afficher. On le verifie AVANT d'ecrire quoi que ce
    soit, plutot que d'echouer au milieu."""
    for e in etals:
        if e["id"] in INTOUCHABLES:
            continue
        ce_rare = e["id"] in RARES and rares_actives
        pool = rare if ce_rare else ordinaire
        pct = PCT_RARE[e["id"]] if ce_rare else e["pct"]
        besoin = {}
        for ident in e["objets"]:
            if ident:
                # EN CHAOS ON COMPTE L'ETAL ENTIER SUR UNE SEULE FAMILLE : les
                # dix-huit emplacements puisent dans la meme reserve, donc
                # c'est bien dix-huit objets affichables qu'il faut y trouver.
                fam = None if chaos else B._cat_objet(cat[ident])
                besoin[fam] = besoin.get(fam, 0) + 1
        for fam, n in sorted(besoin.items()):
            dispo = [o for o in pool.get(fam, ())
                     if classe.get(o, 0) != 2
                     or achat.get(o, 0) * pct // 100 <= PLAFOND_CLASSE_2]
            if len(dispo) < n:
                raise AssertionError(
                    "boutique %d a %d %% : %d emplacements de famille %s, mais "
                    "seulement %d objets affichables"
                    % (e["id"], pct, n, fam, len(dispo)))


def patcher(rom, rng, langue="en", journal=None, chaos=False,
            prix_fabriques=True, progression=True):
    """Reecrit le stock des boutiques. Rend un dictionnaire de comptes.

    `progression` : borner le prix de ce qu'une boutique vend par ce que le
    vanilla y vend de plus cher (voir `plafonds_vanilla`). Sans cette borne, le
    tirage est uniforme sur tout le catalogue et une armurerie de debut de
    partie propose a 40 000 po ce que le joueur n'aura pas avant vingt heures
    -- defaut signale deux fois par le joueur (ZER-31). Les trois boutiques du
    rare y echappent : elles sont censees etre hors de portee.

    `prix_fabriques` : dire si `patch_prix` est passe avant. Sinon les 241
    objets sans prix restent hors du pool, et les trois boutiques du rare n'ont
    plus de quoi remplir leurs emplacements -- une seule piece de tete
    affichable pour trois places, mesure (ZER-33). Elles redeviennent alors des
    boutiques ordinaires : mieux vaut un etal banal qu'un refus de construire.

    `chaos` : n'importe quel objet vendable dans n'importe quel etal, sans
    egard pour la famille ni pour la rarete. Les trois boutiques du rare
    redeviennent des boutiques ordinaires et gardent leur pourcentage du
    vanilla -- les monter a 500 % n'aurait plus de sens, puisqu'elles ne
    vendent plus forcement du rare. Deux invariants tiennent quand meme :
    aucun objet important n'est jamais vendu, et la boutique du chronocristal
    reste intouchee.
    """
    def note(ligne=""):
        if journal is not None:
            journal.write(ligne + "\n")

    d, etals = B.lire(rom)
    cat = objets.catalogue(rom)
    achat = B.prix_achat(rom)
    noms = objets.noms(rom, langue)
    etoiles = objets.raretes(rom, langue)
    ordinaire, rare = pools(rom, langue, chaos)
    pioches = {f: Pioche(rng, p) for f, p in ordinaire.items()}
    pioches_rares = {f: Pioche(rng, p) for f, p in rare.items()}
    if chaos:
        # UNE SEULE PIOCHE POUR LES 559 EMPLACEMENTS. `_Partout` rend le meme
        # pool a toutes les familles ; sans cette mise en commun, chaque
        # famille aurait son paquet et un objet sortirait dans plusieurs etals
        # bien avant que le catalogue soit epuise.
        pioches = pioches_rares = _MemePioche(Pioche(rng, ordinaire[None]))

    classe = classe_prix(rom)
    plafonds = plafonds_vanilla(rom, langue) if progression else {}
    rares_actives = not chaos and prix_fabriques
    if not rares_actives and not chaos:
        note("(pas de prix fabriques : les trois boutiques du rare sont "
             "traitees comme des boutiques ordinaires)")
    _verifier_pools(etals, cat, ordinaire, rare, classe, achat,
                    rares_actives=rares_actives)

    buf = bytearray(d)
    comptes = dict(boutiques=0, articles=0, intouchables=0, rares=0, prix=0)

    note("=== BOUTIQUES ===")
    for e in etals:
        if e["id"] in INTOUCHABLES:
            comptes["intouchables"] += 1
            note("boutique id=%-2d INTOUCHEE (%d article(s))"
                 % (e["id"], sum(1 for o in e["objets"] if o)))
            continue

        ce_rare = e["id"] in RARES and rares_actives
        tirage = pioches_rares if ce_rare else pioches
        comptes["boutiques"] += 1
        if ce_rare:
            comptes["rares"] += 1
        note("boutique id=%-2d %-14s %d%%%s"
             % (e["id"], B.CATEGORIE.get(e["categorie"], "?"),
                PCT_RARE[e["id"]] if ce_rare else e["pct"],
                "   [boutique du rare, %d etoiles et +]" % ETOILES_RARE_MIN
                if ce_rare else ""))

        # CE QUE CETTE BOUTIQUE PEUT AFFICHER. La classe de prix 2 ne rend pas
        # les gros montants, et le pourcentage de la boutique multiplie le prix
        # avant affichage : un article a 60 000 passe a 100 %, mais donnerait
        # "Invendable" dans un etal a 500 %. On ecarte donc au TIRAGE ce que
        # l'etal ne saurait pas ecrire, plutot que de le decouvrir a la
        # verification.
        pct = PCT_RARE[e["id"]] if ce_rare else e["pct"]

        def affichable(ident, pct=pct):
            if classe.get(ident, 0) != 2:
                return True
            return achat.get(ident, 0) * pct // 100 <= PLAFOND_CLASSE_2

        # LA FOURCHETTE DE PRIX DE CET ETAL. Rien pour les boutiques du rare.
        plafond = None if ce_rare else plafonds.get(e["id"])

        def dans_la_fourchette(ident, avec_plancher, plafond=plafond, pct=pct):
            if plafond is None:
                return True
            p = achat.get(ident, 0) * pct // 100
            if p > plafond:
                return False
            return not avec_plancher or p >= plafond // PLANCHER_RATIO

        deja, tires = set(), []
        for ident in e["objets"]:
            if not ident:
                continue
            fam = B._cat_objet(cat[ident]) if ident in cat else None
            if not chaos and (fam is None or fam not in tirage):
                raise AssertionError("famille inconnue pour l'objet %d" % ident)
            # TROIS ESSAIS, DU PLUS EXIGEANT AU PLUS LACHE : la fourchette
            # complete, puis sans le plancher, puis sans borne du tout. Le
            # dernier recours n'arrive que si le pool d'une famille n'a rien
            # d'assez bon marche -- mieux vaut un article trop cher qu'un
            # refus de construire.
            choisi = None
            for etape in (0, 1, 2):
                def accepte(o, etape=etape):
                    if not affichable(o):
                        return False
                    if etape == 2:
                        return True
                    return dans_la_fourchette(o, etape == 0)
                try:
                    choisi = tirage[fam].tirer(deja, accepte)
                    break
                except AssertionError:
                    comptes["relaches"] = comptes.get("relaches", 0) + 1
            if choisi is None:
                raise AssertionError("boutique %d : aucun article possible"
                                     % e["id"])
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


def verifier(rom, chaos=False, prix_fabriques=True):
    """Controle de coherence sur une ROM deja patchee. Leve si ca cloche.

    `prix_fabriques` : voir `patcher`. Sans prix fabriques les trois boutiques
    du rare sont des boutiques ordinaires, et les controles qui les concernent
    ne s'appliquent pas.

    `chaos` : trois controles tombent, parce que le mode les contredit par
    construction -- la famille vendue par un etal, le seuil d'etoiles des
    boutiques du rare et leur pourcentage a 500 %. TOUT LE RESTE TIENT, et
    c'est le plus important : pas de doublon, pas d'emplacement deplace, pas
    d'objet important en vente, pas de prix nul, et rien que la boutique ne
    saurait afficher (le fameux "Invendable").
    """
    _d, etals = B.lire(rom)
    permis = vendable(rom)
    importants = set(objets.objets_importants(rom))
    cat = objets.catalogue(rom)
    etoiles = objets.raretes(rom)
    achat = B.prix_achat(rom)

    _dv, vanilla = B.lire(_rom_vanilla())
    par_id = {e["id"]: e for e in vanilla}
    rares_actives = not chaos and prix_fabriques
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
        ce_rare = e["id"] in RARES and rares_actives
        if ce_rare and e["pct"] != PCT_RARE[e["id"]]:
            raise AssertionError("boutique %d : %d %% au lieu de %d %%"
                                 % (e["id"], e["pct"], PCT_RARE[e["id"]]))
        if not ce_rare and e["pct"] != ref["pct"]:
            raise AssertionError("boutique %d : le prix a bouge" % e["id"])
        if not chaos:
            familles_avant = sorted(B._cat_objet(cat[o])
                                    for o in ref["objets"] if o)
            familles_apres = sorted(B._cat_objet(cat[o])
                                    for o in e["objets"] if o)
            if familles_avant != familles_apres:
                raise AssertionError("boutique %d : les familles vendues ont "
                                     "change" % e["id"])
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
            if chaos or not prix_fabriques:
                continue
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
