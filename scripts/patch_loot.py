#!/usr/bin/env python3
"""Randomize le contenu des conteneurs : coffres, pots, tonneaux, placards.

CE QUI EST TOUCHE, et rien d'autre :

  1. `randTBox.bin` -- la table de tirage des COFFRES BLEUS, rangs 1 a 5.
     Chaque outcome de type "objet" recoit un objet tire dans le pool autorise.
     Les pourcentages, les rangs, les montants d'or et les deux embuscades
     (rang 4 et rang 5, 10 % chacune) restent tels quels.

  2. `randTTT.bin` -- celle des POTS, TONNEAUX et PLACARDS, rangs 1 a 20.
     Meme traitement. Les sommes de pourcentage y vont de 20 a 50 % par rang :
     le complement est du vide, et on le preserve, sinon chaque pot du jeu
     deviendrait une garantie de butin.

  3. Les COFFRES ROUGES, un par un, dans les 265 scripts de zone. Leur contenu
     n'est pas tire au sort par le jeu : il est ecrit en dur dans le script. On
     le remplace donc une fois pour toutes a la construction de la ROM.

CE QUI N'EST PAS TOUCHE :

  - `randTD.bin`, la table des GROTTOS (rangs 1 a 10). Decision du joueur.
  - les coffres rouges dont le contenu vanilla est un objet IMPORTANT. Il n'y
    en a qu'un dans tout le jeu, la Magic key de C02M07, et la partie est
    infinissable sans elle. La regle est generale, pas une exception codee en
    dur : un coffre qui porte un objet important garde son objet.
  - les conteneurs dont le lootType vanilla est "or" ou "rien".
  - les embuscades : l'identite du monstre qui embusque est un autre chantier
    (ZER-21), la table qui associe le type d'embuscade a une espece n'est pas
    encore localisee.

4. Les DROPS DES MONSTRES : dans `data/prm/mon_btldata.nat`, chaque monstre
     porte un objet commun en +0x04 et un objet rare en +0x06. Chaque
     emplacement non vide recoit un objet du pool ; un emplacement vide le
     reste, et les taux de drop ne bougent pas. Les objets de quete lootes sur
     des monstres (plume d'archimere...) ne sont PAS dans cette table : ce sont
     les scripts de quete `data/scenario/quest_btl_*.stb` qui les donnent,
     quete active. Ils ne sont pas touches. RESEARCH.md 80.

LES COFFRES ROUGES ET LES DROPS sont reecrits en place. LES DEUX TABLES sont
reconstruites avec plus de lignes (voir repartir) : `treasure.nsarc` grossit
de quelques Ko, la disposition de la ROM change, et les savestates prises sur
une construction sans extension ne sont plus valides.
"""
import collections
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import objets
import treasure as T

CHEMIN_ARCHIVE = "data/scenario/treasure.nsarc"
CHEMIN_MONSTRES = "data/prm/mon_btldata.nat"
MON_ENTETE, MON_ENREG = 4, 132
OFF_DROPS = ((0x04, "commun"), (0x06, "rare"))


class Pioche(object):
    """Tirage SANS remise dans le pool, reconstitue quand il est vide.

    Avec `rng.choice`, un objet pouvait sortir trois fois et un autre jamais :
    sur la graine 1, 594 objets du pool sur 1090 etaient obtenables. En piochant
    dans un paquet melange, chaque emplacement recoit un objet different tant
    que le paquet dure, donc la couverture est la plus large possible pour un
    nombre d'emplacements donne.
    """

    def __init__(self, rng, pool):
        self.rng = rng
        self.pool = list(pool)
        self.paquet = []

    def __call__(self):
        if not self.paquet:
            self.paquet = list(self.pool)
            self.rng.shuffle(self.paquet)
        return self.paquet.pop()


# LES DEUX PLAFONDS DU MOTEUR, lus dans le decomp (LootableContainer.cpp) :
#   - Sample() range les outcomes d'un rang dans un tableau de 32 : au-dela,
#     les suivants sont ignores ;
#   - LoadZoneContainers() charge chaque table dans un tampon de pile de 0x400
#     octets gere par un HMRFAllocator, dont l'en-tete prend 48 octets
#     (SignedAllocatorHeader 36 + Block 8 + newestState 4). Il reste 976
#     octets, soit 244 outcomes de 4 octets. Si AllocateOutcomes echoue, la
#     table est vide : pas de plantage, mais plus aucun butin. On garde deux
#     outcomes de marge.
MAX_PAR_RANG = 32
MAX_PAR_TABLE = 242


# RANGS JUMEAUX DES COFFRES BLEUS. randTBox n'a que 5 rangs : a 32 lignes par
# rang, elle plafonne a 160 lignes alors que le tampon du jeu en accepte 242.
# On cree donc des rangs 6, 7, 8, copies conformes des rangs 3, 4, 5 (memes
# pourcentages d'objet, d'or, d'embuscade et de vide), et on y deplace un
# coffre bleu sur deux de ces rangs. Un coffre garde exactement les memes
# chances qu'en vanilla ; il tire seulement dans une autre liste d'objets.
# Ce sont les rangs les plus peuples (19, 19 et 13 coffres) : chaque jumeau en
# recoit 6 a 9, donc aucun n'est une liste que personne n'atteint.
JUMEAUX = {6: 3, 7: 4, 8: 5}


def jumeler(arc, membres, vanilla, note):
    """Ajoute les rangs jumeaux a `vanilla` et reecrit en place le rang des
    coffres bleus deplaces. Rend le nombre de coffres deplaces."""
    coffres = {}
    for zone, (deb, _fin) in sorted(_lot_zones(membres).items()):
        for c in T.conteneurs(bytes(arc), deb):
            if c["conteneur"] == 4:
                coffres.setdefault(c["item"], []).append((zone, c))
    deplaces = 0
    for neuf, source in sorted(JUMEAUX.items()):
        vanilla.extend(dict(o, rang=neuf) for o in list(vanilla)
                       if o["rang"] == source)
        # un meme uniqueID peut figurer dans deux zones (variantes de
        # scenario) : on decide par uniqueID, pour que les deux suivent
        uids = sorted({c["unique"] for _z, c in coffres.get(source, [])})
        partent = set(uids[1::2])
        for zone, c in coffres.get(source, []):
            if c["unique"] in partent:
                T.ecrire_u32(arc, c["off_packed"],
                             T.encoder_packed(c["unique"], neuf))
                deplaces += 1
                note("  coffre bleu %-12s uid %-4d rang %d -> rang %d"
                     % (zone, c["unique"], source, neuf))
    return deplaces


def repartir(vanilla, etendre=True):
    """Rend les lignes d'une table, rang par rang.

    Or et embuscades : recopies tels quels. La part "objet" d'un rang (la somme
    de ses pourcentages d'objet, P) est decoupee en n lignes de pourcentages
    entiers aussi egaux que possible, n <= P (une ligne vaut au moins 1 %) et
    n <= 32 moins les lignes d'or et d'embuscade. Si le total depasse
    MAX_PAR_TABLE, les rangs les plus fournis cedent des lignes un a un.
    Sans `etendre`, chaque rang garde son nombre de lignes vanilla.
    """
    rangs = {}
    for o in vanilla:
        r = rangs.setdefault(o["rang"], dict(autres=[], p=0, n=0))
        if o["loot"] == T.TYPE_OBJET:
            r["p"] += o["pct"]
            r["n"] += 1
        else:
            r["autres"].append(dict(o))
    if etendre:
        for r in rangs.values():
            r["n"] = min(r["p"], MAX_PAR_RANG - len(r["autres"]))
        fixes = sum(len(r["autres"]) for r in rangs.values())
        while fixes + sum(r["n"] for r in rangs.values()) > MAX_PAR_TABLE:
            max(rangs.values(), key=lambda r: r["n"])["n"] -= 1
    lignes = []
    for rang in sorted(rangs):
        r = rangs[rang]
        lignes.extend(r["autres"])
        if r["n"]:
            base, reste = divmod(r["p"], r["n"])
            for k in range(r["n"]):
                lignes.append(dict(rang=rang, loot=T.TYPE_OBJET, id=0,
                                   pct=base + (1 if k < reste else 0)))
    # la part de vide de chaque rang ne doit pas bouger d'un point
    for rang in rangs:
        av = sum(o["pct"] for o in vanilla if o["rang"] == rang)
        ap = sum(o["pct"] for o in lignes if o["rang"] == rang)
        assert av == ap, (rang, av, ap)
    return lignes


def _lot_zones(membres):
    return {k: v for k, v in membres.items() if k not in T.TABLES}


def patcher(rom, rng, langue="en", journal=None,
            tables=True, coffres_rouges=True, drops=True, etendre=True):
    """Reecrit le loot dans la ROM chargee. Rend un dictionnaire de comptes.

    Trois temps : on RECENSE tous les emplacements (lignes de tables, coffres
    rouges, drops) avec les etoiles qu'ils acceptent (rarete.py), on AFFECTE
    un objet a chacun en garantissant que tout le pool sort, puis on ECRIT.

    `journal` : un fichier ouvert en ecriture, ou None.
    """
    import rarete
    from monstres_nommes import MONSTRES
    from monnames import lire_table

    def note(ligne=""):
        if journal is not None:
            journal.write(ligne + "\n")

    permis = objets.pool(rom, langue)
    importants = objets.objets_importants(rom, langue)
    noms = objets.noms(rom, langue)
    etoiles = objets.raretes(rom, langue)

    def nom(i):
        return "%5d %-26s %s" % (i, noms.get(i, "?")[:26], "*" * etoiles.get(i, 0))

    note("=" * 78)
    note("OBJETS DANS LES CONTENEURS")
    note("=" * 78)
    note("pool autorise : %d objets sur %d au catalogue"
         % (len(permis), len(permis) + len(importants)))
    note("exclus : %d objets importants (cles, Fyggs, objets de quete)"
         % len(importants))
    note()

    fid = rom.filenames.idOf(CHEMIN_ARCHIVE)
    if fid is None:
        raise ValueError("absent de la ROM : " + CHEMIN_ARCHIVE)
    arc = bytearray(rom.files[fid])
    taille_avant = len(arc)
    membres = T.membres_narc(bytes(arc))
    comptes = dict(outcomes=0, coffres=0, coffres_gardes=0, or_intact=0,
                   embuscades_intactes=0, drops=0,
                   coffres_bleus_deplaces=0)
    emplacements = []   # (cle, etoiles acceptees)

    # ---- recensement 1 et 2 : les deux tables -------------------------------
    # Les tables sont RECONSTRUITES : pour que les 1090 objets du pool puissent
    # sortir, chaque rang recoit plus de lignes que la vanilla (repartir()).
    # Les pourcentages d'or, d'embuscade et de vide sont conserves au point pres.
    lignes_tables = {}
    if tables:
        for table in (T.TABLE_COFFRES_BLEUS, T.TABLE_POTS):
            deb, _fin = membres[table]
            vanilla = [o for _off, o in T.outcomes(bytes(arc), deb)]
            lignes_tables[table] = (len(vanilla), None)
            if etendre and table == T.TABLE_COFFRES_BLEUS:
                note("-" * 78)
                note("RANGS JUMEAUX DES COFFRES BLEUS")
                note("-" * 78)
                comptes["coffres_bleus_deplaces"] = jumeler(arc, membres,
                                                            vanilla, note)
            lignes = repartir(vanilla, etendre)
            lignes_tables[table] = (lignes_tables[table][0], lignes)
            for k, o in enumerate(lignes):
                if o["loot"] == T.TYPE_OBJET:
                    ens = (rarete.BLEU.get(o["rang"], rarete.TOUTES)
                           if table == T.TABLE_COFFRES_BLEUS
                           else rarete.pot(o["rang"]))
                    emplacements.append((("t", table, k), ens))

    # ---- recensement 3 : les coffres rouges ---------------------------------
    # Deux zones peuvent decrire la MEME piece a deux moments du scenario
    # (C04M04 et C04M05) : une seule place par uniqueID, pour que le coffre ne
    # change pas de contenu avec l'avancement de l'histoire.
    rouges = []
    if coffres_rouges:
        vus = set()
        for zone, (deb, _fin) in sorted(_lot_zones(membres).items()):
            for c in T.conteneurs(bytes(arc), deb):
                if c["conteneur"] != 0:
                    continue
                if c["loot"] == T.TYPE_OR:
                    comptes["or_intact"] += 1
                    continue
                if c["loot"] != T.TYPE_OBJET:
                    continue
                rouges.append((zone, c))
                if c["item"] in importants or c["unique"] in vus:
                    continue
                vus.add(c["unique"])
                emplacements.append((("r", c["unique"]), rarete.TOUTES))

    # ---- recensement 4 : les drops ------------------------------------------
    # UNE ESPECE, UN BUTIN : plusieurs enregistrements portent le meme monstre
    # (le crabat-joie est a la fois 238 et 256) ; une seule place par (nom,
    # emplacement, objet vanilla). La chance de la place vient de la classe de
    # taux, +0x02 pour le commun et +0x03 pour le rare (RESEARCH.md 81).
    fm = rom.filenames.idOf(CHEMIN_MONSTRES)
    mon = bytearray(rom.files[fm])
    nb = struct.unpack_from("<I", mon, 0)[0]
    if MON_ENTETE + nb * MON_ENREG != len(mon):
        raise ValueError("mon_btldata.nat : taille inattendue")
    try:
        noms_mon = [m["nom"] for m in lire_table(objets._membre_archive(
            rom, "data/prm/mon_data.gp2", "mon_data_en.nat"))]
    except Exception:
        noms_mon = []
    drops_a_ecrire = []
    hors_terrain = []
    if drops:
        par_cle = collections.OrderedDict()
        for k in range(nb):
            base = MON_ENTETE + k * MON_ENREG
            for off, genre in OFF_DROPS:
                v = struct.unpack_from("<H", mon, base + off)[0]
                if v == 0:
                    continue
                if v in importants:
                    raise AssertionError("monstre %d : objet important %d en "
                                         "drop, non prevu" % (k, v))
                cle = ("d", noms_mon[k] if k < len(noms_mon) and noms_mon[k]
                       else "#%d" % k, off, v)
                classe = mon[base + (2 if off == 0x04 else 3)]
                drops_a_ecrire.append((k, base, off, genre, v, cle, classe))
                par_cle.setdefault(cle, []).append((k, classe))
        for cle, lot in par_cle.items():
            # la place compte pour la couverture si un monstre de terrain la
            # porte avec une chance non nulle ; sa rarete suit cette chance
            terrain = [classe for k, classe in lot
                       if k in MONSTRES and classe != 7]
            if terrain:
                emplacements.append((cle, rarete.DROP[min(terrain)]))
            else:
                hors_terrain.append(cle)

    # ---- affectation --------------------------------------------------------
    # Le pool entier est couvert sur les places atteignables ; les places hors
    # terrain (boss, entrees inutilisees, chance nulle) recoivent un objet
    # quelconque.
    affecte = rarete.affecter(rng, emplacements, etoiles, permis)
    for cle in hors_terrain:
        affecte[cle] = rng.choice(permis)

    # ---- ecriture : tables ---------------------------------------------------
    neuves = {}
    for table, (n_vanilla, lignes) in lignes_tables.items():
        deb, fin_t = membres[table]
        note("-" * 78)
        note("%s : %d lignes (vanilla %d)" % (table, len(lignes), n_vanilla))
        note("-" * 78)
        note("  %-4s %-10s %5s  %s" % ("rang", "type", "%", "contenu"))
        for k, o in enumerate(lignes):
            if o["loot"] == T.TYPE_OBJET:
                o["id"] = affecte[("t", table, k)]
                comptes["outcomes"] += 1
                etiq = nom(o["id"])
            elif o["loot"] == T.TYPE_OR:
                comptes["or_intact"] += 1
                etiq = "%d or" % o["id"]
            else:
                comptes["embuscades_intactes"] += 1
                etiq = "embuscade type %d, INTACTE (ZER-21)" % o["id"]
            note("  %-4d %-10s %4d %%  %s" %
                 (o["rang"], T.NOM_LOOT[o["loot"]], o["pct"], etiq))
        neuves[table] = T.reconstruire_table(bytes(arc), deb, fin_t, lignes)
        note()

    # ---- ecriture : coffres rouges ------------------------------------------
    if rouges:
        note("-" * 78)
        note("COFFRES ROUGES (contenu fixe, ecrit dans le script de zone)")
        note("-" * 78)
        for zone, c in rouges:
            if c["item"] in importants:
                comptes["coffres_gardes"] += 1
                note("  %-12s %-6d %s    GARDE : objet important" %
                     (zone, c["unique"], nom(c["item"])))
                continue
            neuf = affecte[("r", c["unique"])]
            T.ecrire_u32(arc, c["off_packed"], T.encoder_packed(c["unique"], neuf))
            comptes["coffres"] += 1
            note("  %-12s %-6d %s -> %s" %
                 (zone, c["unique"], nom(c["item"]), nom(neuf)))
        note()

    if len(arc) != taille_avant:
        raise AssertionError("treasure.nsarc a change de taille : %d -> %d"
                             % (taille_avant, len(arc)))
    if neuves:
        arc = bytearray(T.reconstruire_narc(bytes(arc), neuves))
    rom.files[fid] = bytes(arc)

    # ---- ecriture : drops ----------------------------------------------------
    if drops_a_ecrire:
        note("-" * 78)
        note("DROPS DES MONSTRES (mon_btldata.nat, taux inchanges)")
        note("-" * 78)
        chances = {0: "toujours", 1: "1/8", 2: "1/16", 3: "1/32", 4: "1/64",
                   5: "1/128", 6: "1/256", 7: "jamais"}
        for k, base, off, genre, v, cle, classe in drops_a_ecrire:
            neuf = affecte[cle]
            struct.pack_into("<H", mon, base + off, neuf)
            comptes["drops"] += 1
            note("  monstre %3d  %-6s %-8s %s -> %s" %
                 (k, genre, chances.get(classe, "?"), nom(v), nom(neuf)))
        rom.files[fm] = bytes(mon)
        note()

    note("bilan : %d outcomes de table reecrits, %d coffres rouges reecrits, "
         "%d gardes, %d montants d'or intacts, %d embuscades intactes, "
         "%d drops de monstres"
         % (comptes["outcomes"], comptes["coffres"], comptes["coffres_gardes"],
            comptes["or_intact"], comptes["embuscades_intactes"],
            comptes["drops"]))
    note()
    return comptes


def verifier(rom):
    """Controle de coherence sur une ROM deja patchee. Leve si quelque chose
    cloche. Ne remplace pas un essai en jeu, mais attrape les fautes betes."""
    permis = set(objets.pool(rom))
    importants = objets.objets_importants(rom)
    fid = rom.filenames.idOf(CHEMIN_ARCHIVE)
    arc = bytes(rom.files[fid])
    membres = T.membres_narc(arc)

    # aucun objet important ne doit sortir d'une table de tirage, et les deux
    # plafonds du moteur sont respectes
    for nom in (T.TABLE_COFFRES_BLEUS, T.TABLE_POTS):
        deb = membres[nom][0]
        rangs = {}
        for _off, o in T.outcomes(arc, deb):
            rangs.setdefault(o["rang"], []).append(o)
            if o["loot"] == T.TYPE_OBJET and o["id"] in importants:
                raise AssertionError("%s : objet important %d dans un outcome"
                                     % (nom, o["id"]))
            if o["loot"] == T.TYPE_OBJET and o["id"] not in permis:
                raise AssertionError("%s : objet inconnu %d" % (nom, o["id"]))
        if len(T.outcomes(arc, deb)) > MAX_PAR_TABLE:
            raise AssertionError("%s : %d outcomes, le tampon du jeu en tient %d"
                                 % (nom, len(T.outcomes(arc, deb)), MAX_PAR_TABLE))
        for rang, lot in rangs.items():
            # LootDistribution::GetOutcomesByRank plafonne a 32
            if len(lot) > 32:
                raise AssertionError("%s rang %d : %d outcomes, le jeu en lit "
                                     "32 au plus" % (nom, rang, len(lot)))
            total = sum(o["pct"] for o in lot)
            if total > 100:
                raise AssertionError("%s rang %d : somme %d %%"
                                     % (nom, rang, total))
    # randTD (grottos) doit etre intacte : on verifie qu'elle porte toujours
    # ses trois types d'embuscade et ses dix rangs
    deb = membres[T.TABLE_GROTTOS][0]
    lot = [o for _o, o in T.outcomes(arc, deb)]
    if len({o["rang"] for o in lot}) != 10:
        raise AssertionError("randTD.bin : les grottos ont ete touches")

    # la Magic key doit encore etre dans un coffre rouge
    cles = 0
    for nom, (d0, _d1) in _lot_zones(membres).items():
        for c in T.conteneurs(arc, d0):
            if c["conteneur"] == 0 and c["loot"] == T.TYPE_OBJET:
                if c["item"] in importants:
                    cles += 1
                elif c["item"] not in permis:
                    raise AssertionError("%s : coffre rouge, objet inconnu %d"
                                         % (nom, c["item"]))
    if cles < 1:
        raise AssertionError("aucun objet important ne reste dans un coffre "
                             "rouge : la Magic key a disparu")

    # chaque conteneur a tirage doit trouver des lignes a son rang
    rangs_tbox = {o["rang"] for _o, o in T.outcomes(arc, membres[T.TABLE_COFFRES_BLEUS][0])}
    rangs_ttt = {o["rang"] for _o, o in T.outcomes(arc, membres[T.TABLE_POTS][0])}
    for zone, (d0, _d1) in _lot_zones(membres).items():
        for c in T.conteneurs(arc, d0):
            if c["conteneur"] == 4 and c["item"] not in rangs_tbox:
                raise AssertionError("%s uid %d : coffre bleu de rang %d sans "
                                     "liste" % (zone, c["unique"], c["item"]))
            if c["conteneur"] in (1, 2, 3) and c["item"] and c["item"] not in rangs_ttt:
                raise AssertionError("%s uid %d : rang %d sans liste"
                                     % (zone, c["unique"], c["item"]))

    # drops : que des objets du pool, ou zero
    mon = bytes(rom.files[rom.filenames.idOf(CHEMIN_MONSTRES)])
    nb = struct.unpack_from("<I", mon, 0)[0]
    for k in range(nb):
        for off, genre in OFF_DROPS:
            v = struct.unpack_from("<H", mon, MON_ENTETE + k * MON_ENREG + off)[0]
            if v and v not in permis:
                raise AssertionError("monstre %d, drop %s : objet %d hors pool"
                                     % (k, genre, v))
    return True


if __name__ == "__main__":
    import random
    import ndspy.rom
    from rom_vanilla import chemin_vanilla
    chemin = sys.argv[1] if len(sys.argv) > 1 else chemin_vanilla()
    graine = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    rom = ndspy.rom.NintendoDSRom.fromFile(chemin)
    comptes = patcher(rom, random.Random(graine), journal=sys.stdout)
    verifier(rom)
    print("verification : OK")
