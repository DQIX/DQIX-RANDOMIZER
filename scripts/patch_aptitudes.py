#!/usr/bin/env python3
"""Randomise les aptitudes des arbres de competences.

CE QU'EST `data/prm/skilltable.bin`, mesure le 21 septembre 2026 :
**26 arbres de 11 paliers**, soit 286 enregistrements de 9 champs.

    champ 0  IDENTIFIANT DU PALIER (0 a 285), celui des drapeaux de maitrise
             de la sauvegarde (183 = Attack +30 with Axe). Ce n'est PAS un
             index de ligne : l'arbre des haches commence par 178, 177, 180.
             C'est de lui que le jeu tire le TYPE d'un bonus (voir plus bas).
    champ 1  ARBRE (1 a 26) : les 14 armes et boucliers, puis les 12 arbres
             propres aux vocations
    champ 2  cout en points de competence (0 a 100)
    champ 3  IDENTIFIANT D'ACTION quand le palier donne une aptitude, 0 sinon.
             Meme espace de noms que les sorts, ET MEME DECALAGE DE UN : le
             nom se lit dans `actname.nat` a l'identifiant + 1. Sans lui,
             l'arbre des epees annonce Divine Intervention a la place de
             Dragon Slash.
    champ 4  nature du palier : 1 = une aptitude (148 paliers, dont un seul
             sans identifiant d'action : il en reste 147 a deplacer),
             2 = Attaque +N,
             3 = taux de coup critique, 4 = maitrise omni-vocationnelle,
             9/10/15/16 = une caracteristique naturelle +N, etc.
    champ 5  la valeur du bonus (10, 20, 30, 50, 100...)
    champs 6 a 8  drapeaux d'affichage, laisses tels quels

Exemple, l'arbre 1 (epees) : Dragon Slash a 3 PC, Attaque +10 a 7, Metal Slash
a 13, taux de critique a 22, Miracle Slash a 35... jusqu'a Gigaslash a 88 et la
maitrise a 100.

DEUX TABLES, ET IL FAUT BOUGER LES DEUX. `skilltable.bin` dit CE QUE le
palier donne ; `sklname.gp2` porte le LIBELLE affiche, une entree par palier,
dans les cinq langues. Deplacer la premiere seule donne exactement ce que le
joueur a constate le 22 septembre : les aptitudes recues en combat sont bien
changees, mais les menus (sorts et aptitudes, repartition des points) affichent
encore les noms du vanilla. Pire que visible : trompeur. On deplace donc le
libelle avec l'aptitude.

CE QU'ON DEPLACE : LA CHARGE DES 286 PALIERS, aptitudes ET bonus, depuis le
23 septembre (la premiere version ne bougeait que les 148 aptitudes). La
place -- arbre, cout -- ne bouge jamais ; les six paliers sans libelle sont
epingles.

LE TYPE D'UN BONUS VOYAGE AVEC SON IDENTIFIANT, mesure en jeu le 24 septembre
(ZER-46). Le jeu lit la VALEUR dans le champ 5, mais le TYPE -- attaque avec
quelle arme, PV, taux critique -- vient du champ 0. Jusqu'a ce jour le champ 0
restait a la place : << Attaque + 30 avec >> pose sur une place de PV donnait
+30 PV et zero attaque, et c'etait vrai dans les deux modes. On deplace donc le
champ 0 avec le reste de la charge. Un bonus << avec >> garde alors SON arme,
ou qu'il aille.

LES 54 BONUS << AVEC >> ET LEUR ICONE. Leur libelle finit par << avec >> et le
jeu dessine derriere l'icone de l'arme DE L'ARBRE, pas celle du bonus. Un bonus
de hache pose dans l'arbre des epees montrerait une epee. En chaos, quand un
tel bonus quitte son arbre, on lui ecrit donc un libelle neuf qui nomme son
arme en toutes lettres (<< Attaque + 30 avec la hache >>), et on eteint son
drapeau d'icone.

DEUX MODES :

  equilibre (defaut)  On melange les paliers A L'INTERIEUR de chaque arbre.
                      Un arbre d'epees ne donne donc que des techniques
                      d'epee -- ce qui compte, parce qu'une technique d'arme
                      ne s'utilise qu'avec cette arme en main. Ce qui change,
                      c'est l'ordre et le cout.
  chaos               On melange les paliers entre TOUS les arbres. Une
                      technique d'epee peut alors tomber dans l'arbre des
                      fouets : elle s'apprend, mais il faudra une epee pour
                      s'en servir. Le rang de puissance est conserve (le
                      palier a 88 PC recoit une aptitude d'une bande de cout
                      comparable), sans quoi la progression n'a plus de sens.
"""
import collections
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sorts
from prmtable import PrmTable

CHEMIN = "data/prm/skilltable.bin"
CHEMIN_NOMS = "data/prm/sklname.gp2"      # un membre par langue, un nom par palier
BANDES = 4                # bandes de puissance du mode chaos
NATURE_APTITUDE = 1
CHAMP_ARBRE, CHAMP_COUT, CHAMP_ACTION, CHAMP_NATURE = 1, 2, 3, 4

# CE QU'UN PALIER DONNE, ET RIEN D'AUTRE. Une ligne de `skilltable.bin` porte
# neuf champs ; trois disent OU le palier se trouve et six disent CE QU'IL
# DONNE. On ne deplace que les seconds :
#
#     1  arbre                     #     2  cout en points            |  la PLACE : ne bouge jamais
#     7  numero de ligne, unique  /
#
#     0  identifiant du palier     #        -- le TYPE du bonus       |
#     3  identifiant d'action       |
#     4  nature : 1 = aptitude,     |
#        2 = attaque, 3 = taux de   |  LA CHARGE : c'est elle qu'on permute
#        critique, 4 = maitrise,    |
#        11 = PV max, 12 = PM...    |
#     5  valeur du bonus (10, 20,   |
#        30, 60...)                 |
#     6  action secondaire, non     |
#        nulle pour dix paliers     |
#     8  categorie d'affichage     /
#
# LES BONUS SONT DES PALIERS COMME LES AUTRES. Jusqu'au 23 septembre seules
# les 147 lignes de nature 1 bougeaient, et les 139 bonus -- << Attaque + 10
# avec >>, << PV max. naturels + 60 >>, << Taux parade + 2 % >> -- restaient
# a leur place : le joueur les voyait identiques d'une graine a l'autre et l'a
# dit. En deplacant la CHARGE ENTIERE, un palier qui donnait une aptitude peut
# donner un bonus et reciproquement, et les 286 lignes se melangent vraiment.
#
# LE CHAMP 0 EST DE LA CHARGE, PAS DE LA PLACE. Le jeu tire le type d'un bonus
# de l'identifiant et sa valeur du champ 5. Laisse a la place du 23 au 24
# septembre, il faisait donner a chaque bonus deplace l'effet de la place
# d'arrivee avec sa propre valeur. Mesure en jeu (ZER-46), meme sauvegarde :
# un seul echange hache 76 PC <-> Cran 4 PC depuis la vanilla donne, charge
# seule, PV 409 -> 429 et attaque 551 -> 531 ; charge et champ 0 ensemble,
# 409 et 551, exactement la vanilla. Il va EN DERNIER pour que les positions
# 0 (action) et 1 (nature) de la charge ne bougent pas.
CHAMPS_CHARGE = (3, 4, 5, 6, 8, 0)
CHAMP_ID = 0
POS_ID = CHAMPS_CHARGE.index(CHAMP_ID)
TAG_NOM = 0x66            # dans sklname : une ligne par palier
CHAMP_NOM = 1             # offset du nom dans le pool de chaines
CHAMP_NOM_ARBRE, CHAMP_NOM_COUT = 3, 4      # la cle de jointure
CHAMP_NOM_APTITUDE, CHAMP_NOM_ARME = 2, 5   # deux drapeaux, et ils SUIVENT
# MESURE DU 24 SEPTEMBRE, sur les 286 lignes du vanilla :
#   champ 2 = 1 pour les 147 paliers qui donnent une APTITUDE, 0 sinon ;
#   champ 5 = 1 pour les 54 paliers dont le libelle attend une ARME --
#     << Attaque + 10 avec >>, le jeu collant derriere l'icone de l'arme de
#     l'arbre. C'est CE DRAPEAU qui les designe, pas l'espace finale : en
#     espagnol, neuf de ces libelles n'en ont pas.
# Ils decrivent donc la CHARGE, pas la place, et doivent voyager avec elle.
# Ne pas les deplacer donnait un palier de bonus portant le drapeau
# d'aptitude, et surtout un << Attaque + 30 avec >> sans icone derriere --
# constate en jeu le 24 septembre.
CHAMPS_NOM = (CHAMP_NOM, CHAMP_NOM_APTITUDE, CHAMP_NOM_ARME)


def _lire(rom):
    fid = rom.filenames.idOf(CHEMIN)
    if fid is None:
        raise ValueError("absent de la ROM : " + CHEMIN)
    return fid, PrmTable(bytes(rom.files[fid]))


def paliers(rom):
    """Rend [(index, arbre, cout, action, nature)] pour les 286 paliers."""
    _fid, t = _lire(rom)
    return [(i, r.fields[CHAMP_ARBRE], r.fields[CHAMP_COUT],
             r.fields[CHAMP_ACTION], r.fields[CHAMP_NATURE])
            for i, r in enumerate(t.records) if len(r.fields) == 9]


def lignes(rom):
    """Rend [(index de ligne, les neuf champs)] pour les 286 paliers."""
    _fid, t = _lire(rom)
    return [(i, list(r.fields)) for i, r in enumerate(t.records)
            if len(r.fields) == 9]


def patcher(rom, rng, journal=None, chaos=False, langue="en"):
    """Deplace la charge des 286 paliers. Rend un dictionnaire de comptes.

    `langue` ne sert qu'au JOURNAL : il y ajoute le libelle tel que le menu
    du jeu l'affichera. Sans lui, le journal parle anglais et le joueur lit
    du francais a l'ecran, ce qui rend la verification penible pour rien.
    """
    def note(ligne=""):
        if journal is not None:
            journal.write(ligne + chr(10))

    fid, t = _lire(rom)
    taille_avant = len(t.data)
    noms = sorts.noms_actions(rom)
    affiches = _libelles_affiches(rom, langue)
    tous = lignes(rom)
    place = {i: (f[CHAMP_ARBRE], f[CHAMP_COUT]) for i, f in tous}
    charge = {i: [f[k] for k in CHAMPS_CHARGE] for i, f in tous}

    # LE RANG DE PUISSANCE VIENT DU JEU : le cout en points de competence que
    # le vanilla demandait pour ce palier. Le palier a 0 point (la recompense
    # de maitrise) compte comme le plus cher, pas comme le moins.
    def rang(cout):
        return 1000 if cout == 0 else cout

    # LES PALIERS SANS LIBELLE NE SONT PAS DES PALIERS. Six lignes du vanilla
    # n'ont aucun nom affiche -- arbres 13, 15, 18, 19, 21 et 26, toutes au
    # cout 0, une place vide que le jeu ne montre pas. Les melanger amenait
    # ce vide sur un palier visible : le joueur a vu, le 24 septembre, une
    # ligne blanche a 16 points dans l'arbre Cran. On les epingle.
    fixes = {i for i, _f in tous if not affiches.get(place[i])}

    comptes = dict(arbres=0, paliers=0, aptitudes=0, bonus=0)
    note("=== APTITUDES ET BONUS DES ARBRES DE COMPETENCES ===")
    note("mode : %s" % ("chaos (melange entre tous les arbres)" if chaos
                        else "equilibre (melange a l'interieur de chaque arbre)"))

    mobiles = [i for i, _f in tous if i not in fixes]
    if chaos:
        # PAR BANDES DE PUISSANCE, ET SURTOUT PAS PAR RANG EXACT. Trier le sac
        # et les places par le meme cout redonne l'affectation d'origine : le
        # premier jet de ce mode ne changeait RIEN, mesure faite. On decoupe
        # donc les paliers en quatre bandes de cout et on ne melange qu'a
        # l'interieur d'une bande : un palier de debut d'arbre reste un palier
        # de debut d'arbre, mais ce n'est plus la meme chose qu'on y gagne.
        places = sorted(mobiles, key=lambda i: (rang(place[i][1]), i))
        n = len(places)
        perm = {i: i for i in fixes}
        for k in range(BANDES):
            debut, fin_b = n * k // BANDES, n * (k + 1) // BANDES
            tranche = places[debut:fin_b]
            sac = list(tranche)
            rng.shuffle(sac)
            for arrivee, depart in zip(tranche, sac):
                perm[arrivee] = depart
        # PLUS DE REPARATION POUR LES BONUS << AVEC >>. Du 23 au 24 septembre
        # on les ramenait dans les treize arbres d'arme, faute de quoi leur
        # libelle finissait dans le vide. Depuis que l'identifiant voyage, un
        # tel bonus garde son arme partout, et `_nommer_armes` lui ecrit un
        # libelle qui la nomme : il peut aller dans n'importe quel arbre,
        # comme le joueur le demandait (ZER-46).
    else:
        perm = {i: i for i in fixes}
        par_arbre = collections.defaultdict(list)
        for i in mobiles:
            par_arbre[place[i][0]].append(i)
        for arbre in sorted(par_arbre):
            l = sorted(par_arbre[arbre])
            sac = list(l)
            rng.shuffle(sac)
            for arrivee, depart in zip(l, sac):
                perm[arrivee] = depart

    par_arbre = collections.defaultdict(list)
    for i, _f in tous:
        par_arbre[place[i][0]].append(i)
    for arbre in sorted(par_arbre):
        comptes["arbres"] += 1
        note("")
        note("arbre %d" % arbre)
        for arrivee in sorted(par_arbre[arbre],
                              key=lambda i: (rang(place[i][1]), i)):
            depart = perm[arrivee]
            for k, v in zip(CHAMPS_CHARGE, charge[depart]):
                t.set_field(arrivee, k, v)
            comptes["paliers"] += 1
            if charge[depart][1] == NATURE_APTITUDE and charge[depart][0]:
                comptes["aptitudes"] += 1
            else:
                comptes["bonus"] += 1
            note("   %3d PC  %-28s -> %-28s %s"
                 % (place[arrivee][1], _quoi(noms, affiches, place, charge,
                                             arrivee),
                    _quoi(noms, affiches, place, charge, depart),
                    "[%s]" % affiches.get(place[depart], "")))

    if len(t.data) != taille_avant:
        raise AssertionError("skilltable.bin a change de taille")
    rom.files[fid] = bytes(t.data)

    comptes["libelles"] = _deplacer_libelles(rom, place, perm, note)
    comptes["armes_nommees"] = _nommer_armes(rom, place, perm, note)
    comptes["messages_armes"] = _messages_armes(rom, place, perm, note)
    note("")
    return comptes


def _quoi(noms, affiches, place, charge, i):
    """Ce qu'un palier donne, en une ligne lisible pour le journal.

    Une aptitude porte un nom d'action ; un bonus n'en a pas, et c'est son
    libelle affiche qui le decrit (<< Attaque + 10 avec >>). On prend donc
    l'un ou l'autre selon la nature, sans jamais inventer.
    """
    action, nature = charge[i][0], charge[i][1]
    if nature == NATURE_APTITUDE and action:
        return noms.get(action + 1, "?%d" % action)
    return affiches.get(place[i], "bonus nature %d" % nature)


# LE JEU ECRIT SES ACCENTS EN BALISES, pas en UTF-8 : `<'e>` pour e accent
# aigu, `<1>` pour l'apostrophe typographique. On les rend lisibles POUR LE
# JOURNAL seulement -- rien de tout cela n'est reecrit dans la ROM.
ACCENTS = {"<'e>": "e", "<`e>": "e", "<^e>": "e", "<^a>": "a", "<^i>": "i",
           "<:i>": "i", "<'E>": "E", "<oe>": "oe", "<1>": "'", "<%>": "%",
           "<u_arrow>": "^", "<Cap>": ""}


def _lisible(nom):
    for balise, clair in ACCENTS.items():
        nom = nom.replace(balise, clair)
    return nom


def _libelles_affiches(rom, langue):
    """Rend {(arbre, cout): libelle}, tel que le menu du jeu l'affichera.

    La table est lue AVANT le deplacement, donc chaque couple (arbre, cout)
    y porte encore le nom de son aptitude vanilla. C'est exactement ce qu'il
    faut : pour savoir ce que le menu affichera a un palier, on cherche le
    libelle du palier D'OU VIENT l'aptitude qu'on y met.
    """
    import objets as _objets
    try:
        membre = _objets._membre_archive(rom, CHEMIN_NOMS,
                                         "sklname_%s.bin" % langue)
    except Exception:
        return {}
    pool = membre.find(b"2010/")
    if pool < 0:
        return {}
    out = {}
    for r in PrmTable(membre).records:
        if r.tag == TAG_NOM and len(r.fields) == 6:
            o = pool + r.fields[CHAMP_NOM]
            fin = membre.find(bytes(1), o)
            if o < fin:
                out[(r.fields[CHAMP_NOM_ARBRE], r.fields[CHAMP_NOM_COUT])] = (
                    _lisible(membre[o:fin].decode("utf-8", "replace")))
    return out


def _deplacer_libelles(rom, place_par_palier, perm, note):
    """Fait suivre le libelle de chaque palier deplace, dans les 5 langues.

    LA CLE DE JOINTURE N'EST PAS L'INDEX DE LIGNE. Une ligne de `sklname`
    porte (index, offset du nom, drapeau, ARBRE, COUT, drapeau) : c'est le
    couple (arbre, cout) qui designe le palier, et il est unique -- 286 cles
    distinctes des deux cotes. Les deux tables ne sont PAS dans le meme ordre
    (la ligne 11 de sklname decrit l'arbre 2 au cout 7, la ligne 11 de
    skilltable l'arbre 2 au cout 3). Joindre par l'index donne 18 noms justes
    sur 147 ; joindre par (arbre, cout) en donne 134, le reste n'etant que des
    apostrophes encodees `<1>` et trois actions absentes d'`actname`.
    """
    import gp2
    import gp2_ecrire
    import objets as _objets

    # LA PERMUTATION EST DEJA DITE EN PALIERS : {arrivee: depart}. Il ne reste
    # qu'a la traduire en couples (arbre, cout), la cle de `sklname`.
    source = {}
    for arrivee, depart in perm.items():
        a, d = place_par_palier.get(arrivee), place_par_palier.get(depart)
        if a and d and a != d:
            source[a] = d
    if not source:
        return 0

    fid = rom.filenames.idOf(CHEMIN_NOMS)
    d = bytes(rom.files[fid])
    gp2_ecrire.verifier_aller_retour(d)
    arc = gp2.GP2(CHEMIN_NOMS, donnees=d)
    clairs = {}
    for nom in arc.noms:
        membre = _objets._membre_archive(rom, CHEMIN_NOMS, nom)
        tn = PrmTable(membre)
        lignes = [(i, r.fields) for i, r in enumerate(tn.records)
                  if r.tag == TAG_NOM and len(r.fields) == 6]
        if len(lignes) != 286:
            raise AssertionError("%s : %d libelles, 286 attendus"
                                 % (nom, len(lignes)))
        place = {(f[CHAMP_NOM_ARBRE], f[CHAMP_NOM_COUT]): i for i, f in lignes}
        # TROIS CHAMPS BOUGENT, ET PAS UN DE PLUS. L'offset du nom, le
        # drapeau << c'est une aptitude >> et le drapeau << colle l'arme de
        # l'arbre derriere >>. Les champs 3 et 4 restent : ce sont l'arbre et
        # le cout, c'est-a-dire la cle de jointure et la place, qui ne
        # bougent jamais.
        avant = {(f[CHAMP_NOM_ARBRE], f[CHAMP_NOM_COUT]):
                 [f[k] for k in CHAMPS_NOM] for _, f in lignes}
        pose = 0
        for arrivee, depart in source.items():
            ir = place.get(arrivee)
            if ir is None or depart not in avant:
                continue
            for k, v in zip(CHAMPS_NOM, avant[depart]):
                tn.set_field(ir, k, v)
            pose += 1
        if pose != len(source):
            raise AssertionError("%s : %d libelles poses sur %d"
                                 % (nom, pose, len(source)))
        clairs[nom] = bytes(tn.data)
    neuf = gp2_ecrire.reecrire(d, clairs)
    rom.files[fid] = neuf
    note("%d libelle(s) deplaces avec leur aptitude, %d -> %d octets"
         % (len(source), len(d), len(neuf)))
    return len(source)


# LE NOM DE L'ARME, LANGUE PAR LANGUE. Le jeu n'a aucune balise de texte pour
# dessiner une icone d'arme (140 balises relevees dans tous les textes, aucune
# ne le fait) : un bonus << avec >> sorti de son arbre nomme donc son arme en
# toutes lettres. On la tire du NOM LONG de l'arbre, `data/bin/str_sklc.gp2`
# (<< Competence a la hache >>, << Axe Skill >>, << Axt-Talent >>, << Abilita
# con l'ascia >>, << Destreza con hacha >>), deja encode comme le jeu l'attend,
# accents en balises compris. Chaque langue a sa regle ; l'arbre 14, le combat
# a mains nues, ne se laisse pas reduire a un nom et a le sien, ecrit a la main.
CHEMIN_ARBRES = "data/bin/str_sklc.gp2"
ARBRE_POINGS = 14
POINGS = {"de": b"F<:a>usten", "en": b"Fisticuffs", "es": b"los pu<~n>os",
          "fr": b"les poings", "it": b"i pugni"}
# (prefixe du nom long, ce qu'il devient) -- le premier qui correspond gagne.
REGLES = {
    "en": ((b"", b""),),
    "de": ((b"", b""),),
    "es": ((b"Destreza con ", b""),),
    "it": ((b"Abilit<`a> con ", b""),),
    "fr": ((b"Comp<'e>tence <`a> la ", b"la "),
           (b"Comp<'e>tence <`a> l<1>", b"l<1>"),
           (b"Comp<'e>tence aux ", b"les "),
           (b"Comp<'e>tence au ", b"le ")),
}
SUFFIXES = {"en": b" Skill", "de": b"-Talent"}
# LA LIGNE DU MENU A UNE LARGEUR. Mesure en jeu le 24 septembre, firmware en
# espagnol : << Aumentar valor de impacto critico con abanico >> (45 signes)
# touche le bord ; en italien, 44 signes passent avec de la marge, et les
# autres langues restent en dessous. Seul le critique espagnol deborderait
# (<< ... con espada corta >>, 50 signes) : quand on le renomme, on prend un
# debut plus court, 39 signes au pire.
TIGES_COURTES = {"es": {b"Aumentar valor de impacto cr<'i>tico con":
                        b"M<'a>s impactos cr<'i>ticos con"}}


def _noms_arbres(rom, langue):
    """Rend {arbre (1 a 26): nom long encode}, depuis `str_sklc`."""
    import objets as _objets
    m = _objets._membre_archive(rom, CHEMIN_ARBRES, "str_sklc_%s.bin" % langue)
    pool = struct.unpack_from("<I", m, 4)[0]
    out = {}
    for r in PrmTable(m).records:
        if r.tag == 0x67 and len(r.fields) == 2 and r.fields[1] != 0xFFFFFFFF:
            o = pool + r.fields[1]
            out[r.fields[0]] = bytes(m[o:m.find(b"\0", o)])
    return out


def _arme(rom, langue, arbre):
    """Rend le nom de l'arme de l'arbre, pret a suivre << avec >>."""
    if arbre == ARBRE_POINGS:
        return POINGS[langue]
    nom = _noms_arbres(rom, langue)[arbre]
    for prefixe, devient in REGLES[langue]:
        if nom.startswith(prefixe):
            nom = devient + nom[len(prefixe):]
            break
    else:
        raise AssertionError("%s : nom d'arbre imprevu %r" % (langue, nom))
    fin = SUFFIXES.get(langue, b"")
    if fin:
        if not nom.endswith(fin):
            raise AssertionError("%s : nom d'arbre imprevu %r" % (langue, nom))
        nom = nom[:-len(fin)]
    return nom


def _nommer_armes(rom, place_par_palier, perm, note):
    """Donne un libelle qui nomme son arme a chaque bonus << avec >> sorti de
    son arbre. Rend le nombre de paliers renommes.

    A appeler APRES `_deplacer_libelles` : les libelles et le drapeau d'icone
    ont deja suivi la charge, et l'arbre d'ORIGINE d'une charge est celui de
    sa place de depart (la ROM d'entree est la vanilla).

    ON AJOUTE A LA FIN DU POOL, ON NE REECRIT PAS. Un membre de `sklname`
    commence par quatre mots -- nombre d'enregistrements, debut du pool,
    taille du pool, nombre de chaines -- et le pool finit par un bourrage
    0xFF jusqu'au multiple de 16. On pose les chaines neuves apres la
    derniere, on corrige la taille et le compte, et seuls les paliers renommes
    changent d'offset. Meme methode que les noms << Talent >> de
    `patch_arbres.py`, que le jeu a affiches sans broncher le 23 septembre.
    """
    import gp2
    import gp2_ecrire
    import objets as _objets

    # arrivee -> arbre d'origine, pour les seules charges qui changent d'arbre
    source = {}
    for arrivee, depart in perm.items():
        a, d = place_par_palier.get(arrivee), place_par_palier.get(depart)
        if a and d and a[0] != d[0]:
            source[a] = d[0]
    if not source:
        return 0

    fid = rom.filenames.idOf(CHEMIN_NOMS)
    d = bytes(rom.files[fid])
    arc = gp2.GP2(CHEMIN_NOMS, donnees=d)
    clairs, renommes = {}, set()
    for nom in arc.noms:
        langue = nom[len("sklname_"):-len(".bin")]
        m = bytearray(_objets._membre_archive(rom, CHEMIN_NOMS, nom))
        _nb, pool, taille, nchaines = struct.unpack_from("<4I", m, 0)
        tn = PrmTable(bytes(m))
        neuves = bytearray()
        offsets = {}
        changes = []
        for ir, r in enumerate(tn.records):
            f = r.fields
            if r.tag != TAG_NOM or len(f) != 6 or not f[CHAMP_NOM_ARME]:
                continue
            origine = source.get((f[CHAMP_NOM_ARBRE], f[CHAMP_NOM_COUT]))
            if origine is None:
                continue
            o = pool + f[CHAMP_NOM]
            tige = bytes(m[o:m.find(b"\0", o)]).rstrip(b" ")
            tige = TIGES_COURTES.get(langue, {}).get(tige, tige)
            texte = tige + b" " + _arme(rom, langue, origine)
            if texte not in offsets:
                offsets[texte] = taille + len(neuves)
                neuves += texte + b"\0"
            changes.append((ir, offsets[texte]))
            renommes.add((f[CHAMP_NOM_ARBRE], f[CHAMP_NOM_COUT]))
            if langue == "fr":
                note("   arbre %2d, %3d PC : << %s >>"
                     % (f[CHAMP_NOM_ARBRE], f[CHAMP_NOM_COUT],
                        _lisible(texte.decode("utf-8", "replace"))))
        for ir, off in changes:
            tn.set_field(ir, CHAMP_NOM, off)
            tn.set_field(ir, CHAMP_NOM_ARME, 0)
        corps = bytearray(tn.data[:pool + taille]) + neuves
        struct.pack_into("<4I", corps, 0, _nb, pool, taille + len(neuves),
                         nchaines + len(offsets))
        corps += b"\xff" * (-len(corps) % 16)
        clairs[nom] = bytes(corps)
    rom.files[fid] = gp2_ecrire.reecrire(d, clairs)
    note("%d bonus << avec >> renommes d'apres leur arme" % len(renommes))
    return len(renommes)


# LE MESSAGE D'APPRENTISSAGE, << Melchior voit son attaque augmenter de 20
# lorsqu'il est equipe d'une hache ! >>. Mesure le 24 septembre (ZER-46) :
#
#   * le champ 8 d'un palier EST le numero de ce message dans
#     `data/prm/str_gskl.gp2` (1 = apprend une aptitude, 2 = attaque ou PM
#     avec une arme, 3 = critique, 4 = caracteristique, 5 = maitrise,
#     14 = esquive...), et ne sert pas a l'effet : il a voyage avec la charge
#     dans les essais en jeu sans rien changer aux stats ;
#   * dans les messages 2, 3, 5 et 14, << <str_2> >> est le texte 100 + ARBRE
#     DU PALIER : 101 << une epee >> ... 114 << une paire de poings >>. Pour
#     un bonus sorti de son arbre, le jeu nomme donc l'arme de l'arbre
#     d'arrivee -- ou rien dans un arbre de vocation (constate : << lorsqu'il
#     est equipe d' ! >>) ;
#   * AU-DELA DE 31, LE NUMERO NE MARCHE PLUS. Une copie du message 2 posee
#     au numero 25 s'affiche ; une copie posee au 34 donne le message 2
#     d'origine (34 = 32 + 2) -- le jeu semble n'en lire que cinq bits, le
#     code n'a pas ete desassemble. Il n'y a donc que huit numeros libres,
#     24 a 31 : trop peu pour une copie par arme (jusqu'a 36 par partie).
#
# ON DONNE AUX BONUS DEPLACES UN MESSAGE SANS NOM D'ARME, puisque leur
# libelle la nomme deja (<< Attaque + 30 avec la hache >>) :
#   2  -> 4, le message des caracteristiques, qui existe : << voit son
#         attaque augmenter de 30 ! >> (<str_2> y est la caracteristique) ;
#   3, 14 -> une copie coupee avant le nom de l'arme : << a plus de chances
#         d'infliger des coups critiques ! >> ;
#   5  -> une copie ou l'arme devient << cette arme >>.
# Trois numeros, 24 a 26. Les enregistrements du vanilla ne sont pas tous
# dans l'ordre (le 113 est range apres le 216) ; on pose quand meme les
# copies a leur place dans l'ordre, apres le 22, par prudence.
CHEMIN_MESSAGES = "data/prm/str_gskl.gp2"
CHAMP_MESSAGE = 8
GENERIQUE = {2: 4, 3: 24, 14: 25, 5: 26}
# Le connecteur qui introduit l'arme dans les messages 3 et 14 : on coupe
# de lui jusqu'a la fin, et on remet la ponctuation finale.
CONNECTEURS = {"fr": b" lorsqu<1>", "en": b" when ", "de": b"<,> wenn",
               "it": b" se ", "es": b" si se "}
# Dans le message 5, ce qui remplace l'arme.
CETTE_ARME = {"fr": (b"d<1><str_2>", b"de cette arme"),
              "en": (b"<str_2>", b"this weapon"),
              "de": (b"<str_2>", b"dieser Waffe"),
              "it": (b"<str_2>", b"quest<1>arma"),
              "es": (b"<str_2>", b"esta arma")}


def _message_generique(langue, cat, texte):
    """Rend le message `cat` sans nom d'arme, dans la langue donnee."""
    if cat == 5:
        avant, apres = CETTE_ARME[langue]
        if texte.count(avant) != 1:
            raise AssertionError("%s, message 5 imprevu : %r" % (langue, texte))
        return texte.replace(avant, apres)
    con = CONNECTEURS[langue]
    if texte.count(con) != 1 or texte.count(b"<str_2>") != 1:
        raise AssertionError("%s, message %d imprevu : %r" % (langue, cat, texte))
    # On ne garde que la ponctuation finale : en allemand le verbe suit
    # l'arme (<< wenn er mit <str_2> ausgeruestet ist! >>) et partirait avec.
    fin = b"<!>" if texte.endswith(b"<!>") else texte[-1:]
    return texte[:texte.index(con)] + fin


def _enregistrements(m):
    """Rend [(position, tag, champs)] d'un membre de table de textes.

    Lecture a la main plutot que `PrmTable` : celui-ci s'arrete avant le
    dernier enregistrement de `str_gskl` (le 113, range hors de l'ordre).
    Un enregistrement = tag u16, nombre de champs u8, un octet de type, puis
    les champs en u32.
    """
    nb = struct.unpack_from("<I", m, 0)[0]
    out, p = [], 0x10
    for _ in range(nb):
        tag, nch = struct.unpack_from("<HB", m, p)
        out.append((p, tag, list(struct.unpack_from("<%dI" % nch, m, p + 4))))
        p += 4 + 4 * nch
    return out


def _messages_armes(rom, place_par_palier, perm, note):
    """Donne un message d'apprentissage sans nom d'arme a chaque bonus d'arme
    sorti de son arbre. Rend le nombre de paliers touches."""
    import gp2
    import gp2_ecrire
    import objets as _objets

    fid_t, t = _lire(rom)
    ligne = {(f[CHAMP_ARBRE], f[CHAMP_COUT]): i for i, f in lignes(rom)}
    touches = 0
    for arrivee, depart in sorted(perm.items()):
        a, d = place_par_palier.get(arrivee), place_par_palier.get(depart)
        if not (a and d) or a[0] == d[0]:
            continue
        i = ligne[a]
        cat = t.records[i].fields[CHAMP_MESSAGE]
        if cat in GENERIQUE:
            t.set_field(i, CHAMP_MESSAGE, GENERIQUE[cat])
            touches += 1
    if not touches:
        return 0
    rom.files[fid_t] = bytes(t.data)

    copies = sorted((n, cat) for cat, n in GENERIQUE.items() if n >= 24)
    fid = rom.filenames.idOf(CHEMIN_MESSAGES)
    donnees = bytes(rom.files[fid])
    arc = gp2.GP2(CHEMIN_MESSAGES, donnees=donnees)
    clairs = {}
    for nom in arc.noms:
        langue = nom[len("str_gskl_"):-len(".bin")]
        m = _objets._membre_archive(rom, CHEMIN_MESSAGES, nom)
        nb, pool, taille, nchaines = struct.unpack_from("<4I", m, 0)
        recs = _enregistrements(m)
        textes = {}
        for _p, tag, f in recs:
            if tag == 0x67 and f[1] != 0xFFFFFFFF:
                o = pool + f[1]
                textes[f[0]] = bytes(m[o:m.find(b"\0", o)])
        if any(n in textes for n, _c in copies):
            raise AssertionError("%s : numero de message deja pris" % nom)
        neufs_recs, neuves = bytearray(), bytearray()
        for n, cat in copies:
            neufs_recs += struct.pack("<HBBII", 0x67, 2, 1, n,
                                      taille + len(neuves))
            neuves += _message_generique(langue, cat, textes[cat]) + b"\0"
        # apres le message 22, pour garder l'ordre des numeros
        apres = next(p + 4 + 4 * len(f) for p, tag, f in recs
                     if tag == 0x67 and f[0] == 22)
        fin_recs = recs[-1][0] + 4 + 4 * len(recs[-1][2])
        tete = (bytearray(m[:apres]) + neufs_recs
                + bytearray(m[apres:fin_recs]))
        k = len(copies)
        for p, tag, f in recs:
            if tag == 0x66 and p < apres:           # le compte des messages
                struct.pack_into("<I", tete, p + 4, f[0] + k)
        tete += b"\xff" * (-len(tete) % 16)
        struct.pack_into("<4I", tete, 0, nb + k, len(tete), taille + len(neuves),
                         nchaines + k)
        corps = tete + m[pool:pool + taille] + neuves
        corps += b"\xff" * (-len(corps) % 16)
        clairs[nom] = bytes(corps)
    rom.files[fid] = gp2_ecrire.reecrire(donnees, clairs)
    note("%d message(s) d'apprentissage sans nom d'arme, pour les bonus "
         "sortis de leur arbre" % touches)
    return touches


def verifier(rom, vanilla=None):
    """Controle de coherence. Leve si ca cloche.

    LA CHARGE DE CHAQUE PALIER DOIT ETRE PRESENTE, ET UNE SEULE FOIS. En
    perdre une la rendrait inapprenable dans toute la partie ; en dupliquer
    une en volerait une autre. On compare donc le SAC ENTIER des 286 charges
    a celui du vanilla, bonus compris -- et pas seulement les 147 aptitudes,
    qui etaient les seules a bouger avant le 23 septembre.
    """
    tous = lignes(rom)
    if len(tous) != 286:
        raise AssertionError("%d paliers, 286 attendus" % len(tous))
    # LE NUMERO DE MESSAGE SE JUGE A PART : un bonus sorti de son arbre en
    # recoit un autre (`GENERIQUE`). Dans le sac, on lui rend celui du vanilla
    # pour son identifiant ; le controle du message vient plus bas.
    van = ({f[CHAMP_ID]: f for _i, f in lignes(vanilla)}
           if vanilla is not None else {})

    def charge(f):
        return tuple(van[f[CHAMP_ID]][k]
                     if k == CHAMP_MESSAGE and f[CHAMP_ID] in van else f[k]
                     for k in CHAMPS_CHARGE)
    sac = collections.Counter(charge(f) for _i, f in tous)
    aptitudes = [f for _i, f in tous
                 if f[CHAMP_NATURE] == NATURE_APTITUDE and f[CHAMP_ACTION]]
    if vanilla is None and len(aptitudes) != 147:
        raise AssertionError("%d aptitudes, 147 attendues" % len(aptitudes))
    ids = [f[CHAMP_ACTION] for f in aptitudes]
    if len(set(ids)) != len(ids):
        doublons = [a for a, n in collections.Counter(ids).items() if n > 1]
        raise AssertionError("aptitude(s) en double : %s" % doublons[:5])
    if vanilla is not None:
        attendu = collections.Counter(charge(f) for _i, f in lignes(vanilla))
        if sac != attendu:
            perdues = sorted((attendu - sac).elements())[:5]
            ajoutees = sorted((sac - attendu).elements())[:5]
            raise AssertionError("le sac des charges a change : %d perdue(s) "
                                 "%s, %d ajoutee(s) %s"
                                 % (sum((attendu - sac).values()), perdues,
                                    sum((sac - attendu).values()), ajoutees))
    # UN IDENTIFIANT PAR PALIER. C'est lui qui porte le type du bonus : deux
    # paliers au meme identifiant donneraient deux fois le meme bonus.
    idents = collections.Counter(f[CHAMP_ID] for _i, f in tous)
    if len(idents) != len(tous):
        raise AssertionError("identifiant(s) de palier en double : %s"
                             % [k for k, n in idents.items() if n > 1][:5])
    if vanilla is not None:
        # UNE ICONE D'ARME N'EST JUSTE QUE DANS L'ARBRE DE L'ARME. Le jeu la
        # dessine d'apres l'arbre du palier ; un bonus << avec >> qui garde
        # son drapeau d'icone doit donc etre reste dans l'arbre de son
        # identifiant, sinon il annonce une arme et en sert une autre.
        arbre_de = {f[CHAMP_ID]: f[CHAMP_ARBRE] for _i, f in lignes(vanilla)}
        ident_a = {(f[CHAMP_ARBRE], f[CHAMP_COUT]): f[CHAMP_ID]
                   for _i, f in tous}
        faux = [cle for cle, arme in _drapeaux_arme(rom).items()
                if arme and arbre_de.get(ident_a.get(cle)) != cle[0]]
        if faux:
            raise AssertionError("%d bonus << avec >> affichent l'icone d'un "
                                 "autre arbre : %s" % (len(faux), faux[:5]))
        # MEME REGLE POUR LE MESSAGE D'APPRENTISSAGE : un message qui nomme
        # l'arme de l'arbre n'est juste que dans l'arbre de l'identifiant ;
        # ailleurs, le bonus doit porter le message sans arme.
        faux = []
        for _i, f in tous:
            v8 = van[f[CHAMP_ID]][CHAMP_MESSAGE]
            chez_lui = f[CHAMP_ARBRE] == arbre_de[f[CHAMP_ID]]
            attendu = v8 if chez_lui or v8 not in GENERIQUE else GENERIQUE[v8]
            if f[CHAMP_MESSAGE] != attendu:
                faux.append((f[CHAMP_ARBRE], f[CHAMP_COUT], f[CHAMP_MESSAGE]))
        if faux:
            raise AssertionError("%d message(s) d'apprentissage nomment une "
                                 "autre arme : %s" % (len(faux), faux[:5]))
    return True


def _drapeaux_arme(rom, langue="en"):
    """Rend {(arbre, cout): drapeau d'icone d'arme} lu dans `sklname`."""
    import objets as _objets
    membre = _objets._membre_archive(rom, CHEMIN_NOMS, "sklname_%s.bin" % langue)
    return {(r.fields[CHAMP_NOM_ARBRE], r.fields[CHAMP_NOM_COUT]):
            r.fields[CHAMP_NOM_ARME]
            for r in PrmTable(membre).records
            if r.tag == TAG_NOM and len(r.fields) == 6}


if __name__ == "__main__":
    import random

    import ndspy.rom
    from rom_vanilla import chemin_vanilla
    if len(sys.argv) < 3:
        sys.exit("usage: patch_aptitudes.py <rom.nds> <sortie.nds> [graine] [chaos]")
    r = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    v = ndspy.rom.NintendoDSRom.fromFile(chemin_vanilla())
    g = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 1)
    print(patcher(r, g, journal=sys.stdout,
                  chaos=len(sys.argv) > 4 and sys.argv[4] == "chaos"))
    verifier(r, v)
    r.saveToFile(sys.argv[2])
