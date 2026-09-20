#!/usr/bin/env python3
"""Donne un prix aux objets qui n'en ont pas, pour qu'ils puissent etre vendus.

POURQUOI. 241 des 1090 objets autorises n'ont aucun prix d'achat : le jeu ne
les met jamais en boutique. Places tels quels dans un etal, ils seraient
GRATUITS. Le randomizer de boutiques les ecarte donc -- sauf si on leur fabrique
un prix, ce que fait ce module.

LE DRAPEAU QUI AUTORISE LA VENTE -- trouve le 18 septembre, et c'est la clef.
Donner un prix ne suffit pas : la boutique affiche "Invendable" tant qu'un
CHAMP DE TROIS BITS, en position 13 a 15 du mot de drapeaux a +0x04, vaut zero.

    (drapeaux >> 13) & 7 == 0   l'article ne peut pas etre mis en vente
    (drapeaux >> 13) & 7 == 2   la valeur des 330 articles vendus en vanilla

Preuve en deux temps. Mesure : les 330 articles que le jeu vend portent TOUS la
valeur 2, et les objets refuses en jeu (equipement d'Elric, livres de
competence, pierres de debug) portent tous 0. Experience : sur la savestate du
joueur, `scripts/lua/essai_drapeau.lua` pose ces bits sur la seule fiche du
heaume d'Elric EN MEMOIRE, ressort de la liste et y rentre pour la faire
rebatir -- l'article passe de "Invendable" a 900 000 po.

On ecrit donc la classe 5 sur les objets qui n'en ont pas, et ON NE TOUCHE PAS
a celle des autres. Le texte de la fiche suit tout seul : plus de "Achat
impossible".

OU SONT LES PRIX QUE LE JEU LIT -- mesure le 18 septembre, et ce n'est PAS la
ou on croyait. Les neuf `itemdt_<c>.gp2` portent bien le catalogue, mais la
boutique lit **`data/prm/itemdt.gp2`**, un fichier de cinq membres (un par
langue) qui reprend les 1178 fiches dans le meme format de 32 octets. Preuve :
patcher les neuf laissait la glugoutte a "Achat impossible", et sa fiche EN
MEMOIRE (sonde `scripts/lua/prix_ram.lua`, savestate du joueur dans une
epicerie) portait toujours achat=0 -- exactement ce qu'`itemdt.gp2` contient.
On ecrit donc dans les DIX archives : la grande, celle que le jeu lit, et les
neuf autres pour que le catalogue reste coherent avec elle.

LES DEUX CHAMPS DE LA FICHE D'OBJET (32 octets, voir `objets.py` et
`docs/research/11-shops.md` 83.6) :

    +0x16  u16  prix de VENTE
    +0x18  i16  prix d'ACHAT : la valeur si elle est positive, sinon un code
                -1 : 2 x vente      -2 : 2 x vente + 1
                -3 : 2 x vente - 1  -4 : 10 x vente

LE PLAFOND, MESURE EN JEU LE 18 SEPTEMBRE. Le prix d'achat de base tient sur un
u16 : AU-DELA DE 65 535, LA BOUTIQUE AFFICHE 0. Releve sur la premiere armurerie
d'Ablithia, savestate du joueur : `Anarc 33 300` s'affiche, `Assommoir`
(200 000 dans la donnee) affiche `0`, comme l'arc de cherubin (300 000) et les
deux 5 etoiles montes a 655 350. Le pourcentage de la boutique, lui, s'applique
APRES et dans un type plus large : la meme construction affiche sans broncher
270 000 dans un etal a 500 %. Donc :

    prix de base <= 65 535, et jusqu'a 327 675 affiches a Pontaudy.

Le million demande est hors d'atteinte SUR LE PRIX DE BASE -- mais pas a
l'affichage : les trois boutiques du rare sont a 2000 %, et le joueur y a bien
vu 1 000 000 s'ecrire.

L'ECHELLE, revue par le joueur apres essai : les majorations par rarete rendaient
les premieres zones injouables. On revient au PRIX DE BASE DU JEU, deux fois le
prix de vente, pour tout le monde, sauf :

    les 26 livres de competence                   100 000 pieces
    les 5 etoiles                                 131 070, le plafond
    les neuf graines                              10 000 pieces -- sinon on
                                                  monte un personnage au
                                                  maximum pour trois fois rien

CE QU'ON NE PEUT PAS VENDRE : un objet dont le prix de vente depasse 32 767, car
deux fois ce prix passerait le plafond et la boutique afficherait 0. Ceux-la
restent hors des etals plutot que de se voir rogner leur valeur de revente.

L'EQUILIBRAGE RESTE A FAIRE : le joueur trouve les armes et armures trop cheres
dans les premieres zones. C'est note dans `docs/PLAN.md` phase 7.

ON N'ECRIT QUE LE CODE -1, JAMAIS UN PRIX EN CLAIR. Les trois seuls objets du
jeu dont le champ porte une valeur positive sont des ARMES (lance de bambou 85,
hallebarde 11 200, baton paratonnerre 15 800) ; aucun objet courant n'en a. Et
les objets courants auxquels on avait ecrit un prix en clair affichaient tous
"Achat impossible" en jeu, quand la laine d'agneau, qui porte -1, s'achetait
normalement. On s'en tient donc au mecanisme prouve : **champ = -1, prix
d'achat = deux fois le prix de vente**. Quand l'objet n'a pas de prix de vente,
c'est LUI qu'on ecrit, a la moitie du prix voulu.

CE QU'ON NE TARIFE PAS : la mini medaille, le set du dracoguerrier (donne lors
d'un evenement) et les objets importants. Ils restent a zero, donc hors
boutique, ce que `patch_boutiques.JAMAIS` garantit par ailleurs.

EFFET DE BORD ASSUME : donner 65 535 de prix de VENTE aux 5 etoiles les rend
revendables d'autant. Le record du jeu de base est deja 45 000 (la robe de
mariee), donc l'economie ne change pas d'ordre de grandeur.

LE FICHIER GROSSIT UN PEU. Les membres reecrits sont recompresses par
`gp2_ecrire.py` : les dix archives ne prennent que quelques milliers d'octets de
plus. Mais LA DISPOSITION DE LA ROM CHANGE quand meme, donc les savestates
prises sur une autre construction ne valent plus. La sauvegarde de partie, elle,
n'est pas concernee.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gp2
import gp2_ecrire
import objets

OFF_DRAPEAUX = 0x04
# LA CLASSE DE PRIX, champ de trois bits en 13-15 du mot de drapeaux.
# Mesure du 20 septembre, apres un faux pas paye en jeu :
#   0  l'article ne peut pas etre mis en vente ("Invendable")
#   2  la classe des 330 articles vendus en vanilla, tous a moins de 65 535
#   5  la classe qui supporte les gros montants -- la robe de Celestelle, 530 000
#      dans un etal a 2000 %, et le heaume sacre pousse a 2 621 400 en RAM
# Ecrire 2 sur un article de classe 5 le rend invendable des que son prix
# depasse ce que la classe 2 accepte : c'est exactement ce qui est arrive a 101
# objets. On ne touche donc JAMAIS une classe non nulle, et on met les zeros a 5.
DECALAGE_VENDABLE, MASQUE_VENDABLE, VENDABLE = 13, 7, 5
OFF_VENTE, OFF_ACHAT = 0x16, 0x18
# LE PLAFOND, corrige le 20 septembre par l'experience.
#
# On a cru longtemps a un u16 sur le prix de base, parce que deux articles a
# 200 000 et 300 000 s'affichaient "0". Faux : ces deux-la passaient par le CODE
# -4 (dix fois la vente), et c'est ce chemin-la qui casse. Le code -1, lui, tient
# bien plus haut -- mesure a la sonde `scripts/lua/essai_prix.lua` : le prix de
# vente du heaume sacre pousse a 65 535 en memoire donne une base de 131 070,
# affichee sans broncher (2 621 400 dans un etal a 2000 %).
#
# Le plafond du prix de base est donc DEUX FOIS le u16 du prix de vente, et il
# n'y a plus d'objet qu'on doive ecarter faute de pouvoir le tarifer.
PLAFOND_ACHAT = 2 * 65535
CODE_DOUBLE = -1                  # le seul code qu'on ecrive : achat = 2 x vente
CHEMIN_TABLE = "data/prm/itemdt.gp2"   # celle que le jeu lit vraiment

MINI_MEDAILLE = 22039
LIVRES = tuple(range(22265, 22291))
SET_DRACOGUERRIER = (12785, 13162, 15286, 16256, 17303)
GRAINES = tuple(range(22045, 22054))
PRIX_GRAINE = 10000
PRIX_LIVRE = 100000       # demande du joueur : cher, mais lisible a 100 %

JAMAIS_TARIFES = {MINI_MEDAILLE} | set(SET_DRACOGUERRIER)
FACTEUR = {}                      # plus de majoration par rarete


def _expression(voulu, vente):
    """Rend (vente finale, champ d'achat, prix obtenu). Champ toujours -1.

    Si l'objet a deja un prix de vente, on n'y touche pas et le prix d'achat
    vaut le double. Sinon on ecrit la moitie du prix voulu comme prix de vente,
    ce qui revient au meme et laisse l'objet revendable, comme tout le reste.
    Rend (None, None, 0) pour un objet qu'on ne peut pas tarifer sous le
    plafond.
    """
    voulu = min(voulu, PLAFOND_ACHAT)
    if vente and 2 * vente > PLAFOND_ACHAT:
        return None, None, 0              # trop cher pour le format
    if vente:
        return vente, CODE_DOUBLE, 2 * vente
    v = max(1, min(voulu // 2, PLAFOND_ACHAT // 2))
    return v, CODE_DOUBLE, 2 * v


def prix_voulus(rom, langue="en"):
    """{identifiant: (vente, achat)} pour les objets a tarifer.

    Ne rend que ceux qu'il faut changer, avec leurs deux valeurs finales.
    """
    import boutiques as B
    permis = set(objets.pool(rom, langue))
    etoiles = objets.raretes(rom, langue)
    vente = B.prix_catalogue(rom)
    achat = B.prix_achat(rom)
    mediane = _medianes(rom, permis, vente, achat, etoiles)

    out = {}
    for i in sorted(permis):
        if i in JAMAIS_TARIFES:
            continue
        if achat.get(i, 0) > 0 and vente.get(i, 0) > 0:
            continue                      # deja tarife, on n'y touche pas
        v = vente.get(i, 0)
        n = etoiles.get(i, 0)
        fam = _famille(rom, i)
        if i in GRAINES:
            # Les graines ont un prix de vente ridicule (15 a 50) : pour les
            # mettre a 10 000 il faut leur en ecrire un, le seul cas ou on
            # touche a une valeur vanilla non nulle.
            out[i] = (PRIX_GRAINE // 2, PRIX_GRAINE)
            continue
        if i in LIVRES:
            voulu = PRIX_LIVRE
        elif n >= 5:
            voulu = PLAFOND_ACHAT
        elif v:
            voulu = 2 * v
        else:
            # Aucun prix de vente : on s'aligne sur la mediane des objets
            # tarifes de meme famille et meme rarete.
            voulu = mediane.get((fam, n)) or mediane.get(fam) or 0
        if not voulu:
            continue
        vente_finale, _champ, obtenu = _expression(voulu, v)
        if not obtenu:
            continue                      # hors plafond : reste hors des etals
        out[i] = (vente_finale, obtenu)
    return out


def _poser_vendable(membre, position):
    """Donne une classe de prix a un article qui n'en a pas.

    Ne fait rien si la classe est deja non nulle : elle vient du jeu et elle
    decide de ce que l'affichage accepte.
    """
    d = struct.unpack_from("<I", membre, position)[0]
    if (d >> DECALAGE_VENDABLE) & MASQUE_VENDABLE:
        return
    struct.pack_into("<I", membre, position,
                     d | (VENDABLE << DECALAGE_VENDABLE))


def _famille(rom, ident):
    import boutiques as B
    return B._cat_objet(objets.catalogue(rom)[ident])


def _medianes(rom, permis, vente, achat, etoiles):
    """Prix d'achat median par (famille, rarete), sur les objets deja tarifes.

    Sert aux 52 objets qui n'ont meme pas de prix de vente : on les aligne sur
    leurs semblables plutot que d'inventer un chiffre.
    """
    import statistics
    import boutiques as B
    cat = objets.catalogue(rom)
    par = {}
    for i in permis:
        if achat.get(i, 0) > 0 and vente.get(i, 0) > 0:
            fam = B._cat_objet(cat[i])
            par.setdefault((fam, etoiles.get(i, 0)), []).append(achat[i])
            par.setdefault(fam, []).append(achat[i])   # repli sans la rarete
    return {k: int(statistics.median(v)) for k, v in par.items()}


def patcher(rom, langue="en", journal=None):
    """Ecrit les prix dans les neuf archives. Rend un dictionnaire de comptes."""
    def note(ligne=""):
        if journal is not None:
            journal.write(ligne + "\n")

    voulus = prix_voulus(rom, langue)
    noms = objets.noms(rom, langue)
    etoiles = objets.raretes(rom, langue)
    cat = objets.catalogue(rom)
    comptes = dict(objets=0, archives=0, octets=0)

    note("=== PRIX DES OBJETS SANS PRIX ===")
    comptes["octets"] += _patcher_table(rom, voulus, note)
    comptes["archives"] += 1
    for c in objets.CATEGORIES:
        vises = {i: p for i, p in voulus.items() if cat[i][0] == c}
        if not vises:
            continue
        chemin = objets.CHEMIN % c
        fid = rom.filenames.idOf(chemin)
        d = bytes(rom.files[fid])
        gp2_ecrire.verifier_aller_retour(d)
        arc = gp2.GP2(chemin, donnees=d)

        clairs = {}
        for nom in arc.noms:
            lg = nom.split("_")[-1].split(".")[0]
            membre = bytearray(objets._membre(rom, c, lg))
            n = struct.unpack_from("<H", membre, 0)[0] & 0xFFF
            for k in range(n):
                b = objets.TETE + objets.ENREG * k
                ident = struct.unpack_from("<H", membre, b + objets.OFF_ID)[0]
                if ident not in vises:
                    continue
                vente, achat = vises[ident]
                champ = CODE_DOUBLE
                _poser_vendable(membre, b + OFF_DRAPEAUX)
                struct.pack_into("<H", membre, b + OFF_VENTE, vente)
                struct.pack_into("<h", membre, b + OFF_ACHAT, champ)
            clairs[nom] = bytes(membre)

        neuf = gp2_ecrire.reecrire(d, clairs)
        rom.files[fid] = neuf
        comptes["archives"] += 1
        comptes["octets"] += len(neuf) - len(d)
        comptes["objets"] += len(vises)
        note("%-22s %3d objets tarifes, %7d -> %7d octets"
             % (chemin.split("/")[-1], len(vises), len(d), len(neuf)))
        for i in sorted(vises):
            vente, achat = vises[i]
            note("   %5d %-28s %-6s vente %6d  achat %7d"
                 % (i, objets.nettoyer(noms.get(i, "?"))[:28],
                    "*" * etoiles.get(i, 0), vente, achat))
    note()
    return comptes


def _patcher_table(rom, voulus, note):
    """Reecrit `data/prm/itemdt.gp2`, LA table que la boutique lit.

    Meme fiche de 32 octets que dans les neuf archives par categorie, mais les
    1178 objets y sont reunis. On repere chaque fiche par son identifiant
    plutot que par un pas suppose, et on verifie que le prix de vente lu
    correspond bien a celui du catalogue avant d'ecrire.
    """
    fid = rom.filenames.idOf(CHEMIN_TABLE)
    d = bytes(rom.files[fid])
    gp2_ecrire.verifier_aller_retour(d)
    arc = gp2.GP2(CHEMIN_TABLE, donnees=d)
    import boutiques as B
    vente0 = B.prix_catalogue(rom)          # les valeurs vanilla : la signature
    clairs = {}
    for nom in arc.noms:
        membre = bytearray(objets._membre_archive(rom, CHEMIN_TABLE, nom))
        for ident, (vente, _achat) in voulus.items():
            # SIGNATURE, pour ne pas ecrire sur deux octets qui vaudraient par
            # hasard l'identifiant : la fiche, c'est l'identifiant SUIVI du prix
            # de vente vanilla et d'un champ d'achat nul. On exige une position
            # et une seule, sinon on s'arrete.
            places = [off for off in range(0, len(membre) - 6, 2)
                      if struct.unpack_from("<HHH", membre, off)
                      == (ident, vente0.get(ident, 0), 0)]
            if len(places) != 1:
                raise AssertionError("objet %d : %d fiches dans %s, une seule "
                                     "attendue" % (ident, len(places), nom))
            off = places[0]
            struct.pack_into("<H", membre, off + 2, vente)
            struct.pack_into("<h", membre, off + 4, CODE_DOUBLE)
            _poser_vendable(membre, off - 0x14 + OFF_DRAPEAUX)
        clairs[nom] = bytes(membre)
    neuf = gp2_ecrire.reecrire(d, clairs)
    rom.files[fid] = neuf
    note("%-22s %3d objets tarifes, %7d -> %7d octets  [la table que le jeu lit]"
         % (CHEMIN_TABLE.split("/")[-1], len(voulus), len(d), len(neuf)))
    return len(neuf) - len(d)


def verifier(rom, langue="en"):
    """Controle apres coup : plus aucun objet tarifable ne reste a zero, et les
    objets deja tarifes en vanilla n'ont pas bouge."""
    import boutiques as B
    from rom_vanilla import chemin_vanilla
    import ndspy.rom
    vanille = ndspy.rom.NintendoDSRom.fromFile(chemin_vanilla())

    achat, vente = B.prix_achat(rom), B.prix_catalogue(rom)
    a0, v0 = B.prix_achat(vanille), B.prix_catalogue(vanille)
    permis = set(objets.pool(rom, langue))
    voulus = prix_voulus(vanille, langue)

    for i in sorted(permis):
        if i in voulus:
            if achat.get(i, 0) != voulus[i][1]:
                raise AssertionError("objet %d : achat %d, attendu %d"
                                     % (i, achat.get(i, 0), voulus[i][1]))
        elif i not in JAMAIS_TARIFES:
            if achat.get(i, 0) != a0.get(i, 0) or vente.get(i, 0) != v0.get(i, 0):
                raise AssertionError("objet %d : prix vanilla modifie" % i)
    for i in JAMAIS_TARIFES:
        if achat.get(i, 0) or vente.get(i, 0) != v0.get(i, 0):
            raise AssertionError("objet %d : ne devait pas etre tarife" % i)
    return True


if __name__ == "__main__":
    import ndspy.rom
    from rom_vanilla import chemin_vanilla
    if len(sys.argv) < 2:
        sys.exit("usage: patch_prix.py <sortie.nds> [rom.nds]")
    src = sys.argv[2] if len(sys.argv) > 2 else chemin_vanilla()
    r = ndspy.rom.NintendoDSRom.fromFile(src)
    print(patcher(r, journal=sys.stdout))
    r.saveToFile(sys.argv[1])
    print("verification :", verifier(ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])))
