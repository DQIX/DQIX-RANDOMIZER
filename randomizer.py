#!/usr/bin/env python3
"""Randomizer de monstres pour Dragon Quest IX (NDS, version Europe YDQP).

CE QU'IL FAIT PAR DEFAUT : il randomise QUELLES ESPECES APPARAISSENT OU, en
laissant leurs statistiques intactes. Un gluant reste un gluant avec ses 8 HP,
mais on le rencontre la ou se trouvait autre chose -- et inversement, ce qui
rend la partie brutale sans rien deregler dans les monstres eux-memes.

Fichiers touches par defaut :
    data/prm/encmons.bin    especes par carte
    data/prm/encfld.bin     rencontres sur le terrain
    data/prm/encbtl.bin     rencontres en combat

COMMENT LES ESPECES SONT REDISTRIBUEES. Par defaut, une PERMUTATION GLOBALE :
chaque espece est remplacee par une autre, toujours la meme partout. N'importe
quel monstre peut donc apparaitre n'importe ou -- un boss de fin dans la zone de
depart, c'est prevu -- mais la variete est preservee (une zone qui avait six
especes en a toujours six differentes) et surtout CHAQUE ESPECE EXISTE ENCORE
QUELQUE PART, ce qui garde le bestiaire completable.

`--tirage-libre` tire au contraire une espece au hasard pour chaque emplacement,
independamment. Plus chaotique, mais certaines especes n'apparaissent nulle part.

EN OPTION :
    --tirage-libre  tirage independant au lieu d'une permutation globale
    --stats         randomise aussi les statistiques (data/prm/mon_btldata.nat)
    --boss          randomise aussi les 98 combats scriptes du scenario

Usage :
  python randomizer.py --seed 1234 "<rom.nds>"                  # rencontres
  python randomizer.py --seed 1234 --boss "<rom.nds>"           # + boss
  python randomizer.py --seed 1234 --stats "<rom.nds>"          # + statistiques
  python randomizer.py --seed 1234 --tirage-libre "<rom.nds>"   # chaos total
  python randomizer.py --seed 1234 --a-blanc "<rom.nds>"        # aucune ecriture

PHILOSOPHIE : DUR PAR DEFAUT. Un randomizer est cense etre brutal. Par defaut
la randomisation est donc COMPLETE, sans egard pour la courbe de difficulte :
un monstre a 8000 HP peut apparaitre au premier combat, c'est le jeu.

Le bornage de progression existe mais il est OPTIONNEL :

  - `--fenetre N` (mode shuffle) limite le deplacement d'un bloc de stats a N
    rangs dans l'ordre du bestiaire. La table est ordonnee suivant la
    progression du jeu (les HP y sont correles a l'index avec un rho de
    Spearman de 0,86), donc borner le deplacement adoucit la courbe.
    `--fenetre 25` donne une partie a peine plus dure que l'originale.
  - `--paliers N` (mode chaos) calcule les plages de tirage par tranche de
    progression au lieu de la table entiere.

Sans ces options, on obtient le comportement voulu : le chaos.
"""
import argparse
import os
import random
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))
from enctables import (FICHIERS_RENCONTRES, FICHIERS_SCRIPTES,
                       TablesRencontres)
from montable import STATS, TableMonstres

# Entrees a ne pas toucher : ce ne sont pas de vrais monstres.
#   800, 801 : toutes stats a 255 -> entrees de test des developpeurs
#   900      : HP 32000 / ATT 9 / DEF 5 -> mannequin d'entrainement du tutoriel
IDS_SPECIAUX = {800, 801, 900}

# LE PREMIER BOSS. `hexacorne`, espece 300, combat scripte d'identifiant 2 --
# le second enregistrement d'`eventbattle.bin`, juste apres le prologue. C'est
# le seul boss du jeu qu'on affronte SANS EQUIPE, d'ou l'option qui le laisse
# en place (`--boss-garder-premier`).
HEXACORNE = 300

# LE COMBAT DU PROLOGUE, jamais touche. L'enregistrement 0 d'`eventbattle`
# (evenement 26) oppose deux gluants et un concombrageur au heros de niveau 1,
# seul, sans equipement et sans equipe. Ces deux especes -- 290 et 292, des
# doublons de tutoriel, pas les gluants ordinaires -- ne servent NULLE PART
# ailleurs en combat scripte. N'importe quoi d'autre a leur place rend la
# partie infaisable des la premiere minute : signale en jeu le 23 septembre.
# Ce n'est pas un reglage d'equilibrage mais une condition pour que le jeu
# soit jouable, donc pas d'option -- on les ecarte toujours.
PROLOGUE = (290, 292)

CHOIX_RES_ELEM = [0, 25, 50, 75, 100, 100, 125, 150, 200]
CHOIX_RES_ETAT = [0, 25, 50, 75, 100, 100]


def bloc(m, avec_resistances=True):
    d = {s: getattr(m, s) for s in STATS}
    if avec_resistances:
        d["_elem"] = m.res_elem
        d["_etat"] = m.res_etat
    return d


def appliquer(m, d):
    for s in STATS:
        setattr(m, s, d[s])
    if "_elem" in d:
        m.res_elem = d["_elem"]
        m.res_etat = d["_etat"]


def permutation_bornee(rng, n, fenetre):
    """Rend une permutation de range(n).

    `fenetre` a 0 (le defaut) : permutation COMPLETE, aucun element n'est
    contraint. C'est le comportement voulu pour un randomizer.

    `fenetre` a N : aucun element ne bouge de plus de N rangs, ce qui adoucit la
    courbe de difficulte. Obtenue par echanges locaux repetes.
    """
    if not fenetre or fenetre >= n:
        perm = list(range(n))
        rng.shuffle(perm)
        return perm
    perm = list(range(n))
    for _ in range(4 * n):
        i = rng.randrange(n)
        j = min(n - 1, max(0, i + rng.randint(-fenetre, fenetre)))
        if abs(perm[i] - j) <= fenetre and abs(perm[j] - i) <= fenetre:
            perm[i], perm[j] = perm[j], perm[i]
    return perm


def tranches(indices, nb):
    if nb <= 1:
        return [list(indices)]
    n = len(indices)
    return [list(indices[i * n // nb:(i + 1) * n // nb]) for i in range(nb)]


def mode_shuffle(rng, table, ordre, avec_res, args):
    blocs = [bloc(table[i], avec_res) for i in ordre]
    perm = permutation_bornee(rng, len(ordre), args.fenetre)
    for pos, i in enumerate(ordre):
        appliquer(table[i], blocs[perm[pos]])


def mode_scale(rng, table, ordre, avec_res, args):
    for i in ordre:
        m = table[i]
        for s in STATS:
            v = getattr(m, s)
            if v:
                setattr(m, s, max(1, round(v * rng.uniform(1 - args.ampleur,
                                                           1 + args.ampleur))))
        if avec_res:
            m.res_elem = [rng.choice(CHOIX_RES_ELEM) for _ in range(7)]
            m.res_etat = [rng.choice(CHOIX_RES_ETAT) for _ in range(14)]


def mode_chaos(rng, table, ordre, avec_res, args):
    for grp in tranches(ordre, args.paliers):
        plages = {s: (min(getattr(table[i], s) for i in grp),
                      max(getattr(table[i], s) for i in grp)) for s in STATS}
        for i in grp:
            m = table[i]
            for s in STATS:
                lo, hi = plages[s]
                setattr(m, s, rng.randint(lo, max(lo, hi)))
            if avec_res:
                m.res_elem = [rng.choice(CHOIX_RES_ELEM) for _ in range(7)]
                m.res_etat = [rng.choice(CHOIX_RES_ETAT) for _ in range(14)]


MODES = {"shuffle": mode_shuffle, "scale": mode_scale, "chaos": mode_chaos}


def trouver_xdelta3():
    """Ou est xdelta3 ?

    Cherche, dans l'ordre : la variable XDELTA3, le PATH, puis `tools/xdelta/`
    relativement au repertoire courant ET a la racine du projet. Le binaire
    Windows officiel est portable : il n'a pas vocation a etre installe, donc le
    chercher uniquement dans le PATH obligeait a bricoler le PATH a chaque fois.
    """
    env = os.environ.get("XDELTA3", "")
    if env and os.path.isfile(env):
        return env
    trouve = shutil.which("xdelta3") or shutil.which("xdelta")
    if trouve:
        return trouve
    racine = os.path.dirname(os.path.abspath(__file__))
    # EN APPLICATION EMBALLEE, le dossier qui compte est celui de l'executable :
    # `__file__` pointe dans le dossier temporaire de PyInstaller, que le joueur
    # ne voit meme pas. On regarde donc aussi a cote de l'exe, et directement
    # dedans -- c'est la que le joueur posera `xdelta3.exe` si on le lui demande.
    voisins = [os.path.dirname(os.path.abspath(sys.executable))] if getattr(
        sys, "frozen", False) else []
    for base in [".", racine] + voisins:
        for nom in ("xdelta3.exe", "xdelta3"):
            for c in (os.path.join(base, "tools", "xdelta", nom),
                      os.path.join(base, nom)):
                if os.path.isfile(c):
                    return c
    return None


def produire_patch(source, cible):
    """Cree un patch xdelta3 de `source` vers `cible`.

    Le patch ne contient que la difference entre les deux ROMs, donc aucune
    donnee du jeu : il peut se partager librement, chacun l'appliquant sur sa
    propre copie. C'est le mode de distribution normal d'un randomizer.

    Application : xdelta3 -d -s <rom_origine> <patch> <rom_randomisee>
    """
    outil = trouver_xdelta3()
    if not outil:
        print("  xdelta3 introuvable. Trois routes, au choix :\n"
              "    - binaire portable depuis https://github.com/jmacd/xdelta/releases\n"
              "      a deballer dans tools/xdelta/ (c'est la que ce script le cherche)\n"
              "    - ou dans le PATH, sous le nom xdelta3 ou xdelta\n"
              "    - ou designe par la variable d'environnement XDELTA3")
        return None
    patch = os.path.splitext(cible)[0] + ".xdelta"
    cmd = [outil, "-e", "-9", "-f", "-s", source, cible, patch]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  echec de xdelta3 : {r.stderr.strip()[:200]}")
        return None
    taille = os.path.getsize(patch)
    print(f"patch : {patch}  ({taille:,} o, soit "
          f"{100 * taille / os.path.getsize(cible):.4f} % de la ROM)")
    print(f"  application : xdelta3 -d -s \"<rom d'origine>\" "
          f"\"{os.path.basename(patch)}\" \"<rom de sortie>.nds\"")
    return patch


def adopter_source(rom, controle=True):
    """La ROM passee en argument devient la ROM de reference de tout le build.

    POURQUOI. Le pool d'especes, les noms de monstres et les tailles de modeles
    ne se lisent pas dans la ROM en cours de patch mais dans la VANILLA, que
    `rom_vanilla.chemin_vanilla()` cherchait dans `banc/roms/`. Sur le PC de
    developpement elle y est ; chez un joueur, non -- il n'a que le fichier
    qu'il vient de deposer. Or ce fichier EST la vanilla : son empreinte le
    prouve. On le declare donc comme tel, et la construction n'a plus besoin de
    rien d'autre que lui.

    Le controle d'empreinte n'est pas une formalite : construire a partir d'une
    ROM deja randomisee reviendrait a randomiser une randomisation, et la
    graine ne suffirait plus a reproduire le resultat.
    """
    from rom_vanilla import MD5_ATTENDU, verifier_vanilla
    _c, md5, conforme = verifier_vanilla(rom)
    if conforme:
        os.environ["DQ9_VANILLA"] = os.path.abspath(rom)
        return md5
    if not controle:
        print(f"  ATTENTION : empreinte {md5}, ce n'est pas la version Europe.")
        print("  --sans-controle-rom accepte : la reference reste "
              "DQ9_VANILLA / banc/roms/.")
        return md5
    raise SystemExit(
        f"Cette ROM n'est pas celle que le randomizer sait traiter.\n"
        f"  empreinte lue : {md5}\n"
        f"  attendue      : {MD5_ATTENDU}  (Europe multi-langue, serial YDQP)\n"
        "  Le randomizer refuse plutot que de produire un jeu casse.")


def main():
    ap = argparse.ArgumentParser(
        description="Randomizer de monstres pour Dragon Quest IX (NDS)",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("rom", help="la ROM d'origine (jamais modifiee en place)")
    ap.add_argument("--seed", type=int, required=True, help="graine, pour la reproductibilite")
    ap.add_argument("--mode", choices=sorted(MODES), default="shuffle")
    ap.add_argument("--fenetre", type=int, default=0,
                    help="mode shuffle : borne le deplacement d'un bloc de stats "
                         "a N rangs du bestiaire, pour adoucir la courbe de "
                         "difficulte. 0 = aucune borne, randomisation complete "
                         "(defaut). Essayer 25 pour une partie a peine plus dure "
                         "que l'originale.")
    ap.add_argument("--paliers", type=int, default=1,
                    help="mode chaos : nombre de tranches de progression sur "
                         "lesquelles calculer les plages de tirage. 1 = toute la "
                         "table, donc chaos complet (defaut).")
    ap.add_argument("--ampleur", type=float, default=0.75,
                    help="mode scale : amplitude de la perturbation (defaut 0.75)")
    ap.add_argument("--resistances", action="store_true",
                    help="randomiser aussi les resistances elementaires et d'etat")
    ap.add_argument("--rencontres", dest="rencontres", action="store_true",
                    default=True,
                    help="randomiser QUELLES especes apparaissent ou "
                         "(encmons.bin, encfld.bin, encbtl.bin). ACTIF PAR DEFAUT.")
    ap.add_argument("--sans-rencontres", dest="rencontres", action="store_false",
                    help="ne pas toucher aux tables de rencontres")
    ap.add_argument("--tirage-libre", dest="tirage_libre", action="store_true",
                    help="tirer une espece au hasard INDEPENDAMMENT pour chaque "
                         "emplacement, au lieu d'une permutation globale. Plus "
                         "chaotique, mais certaines especes n'apparaitront nulle "
                         "part et le bestiaire devient incompletable. La "
                         "permutation globale est le defaut.")
    ap.add_argument("--agrandir-zones", dest="agrandir", action="store_true",
                    default=True,
                    help="reconstruit encfld.bin et encmons.bin ENSEMBLE : "
                         "--especes especes par zone, reparties en groupes de 6 "
                         "entrees au plus, tous rendus toujours eligibles, et la "
                         "meme liste ecrite dans encmons.bin pour que le moteur "
                         "precharge bien leurs modeles. Actif par defaut.")
    ap.add_argument("--sans-agrandissement", dest="agrandir", action="store_false",
                    help="laisser les groupes a leur taille d'origine")
    ap.add_argument("--hasard", action="store_true", default=True,
                    help="PATCHE LE CODE. Actif par defaut. Au lieu de figer les especes d'une "
                         "zone a la construction, les tire au hasard A CHAQUE "
                         "CHARGEMENT DE ZONE parmi les 260 especes de terrain, "
                         "et fait tirer le terrain dans cette liste. Ressortir "
                         "d'une zone et y revenir donne un autre lot. Boss "
                         "exclus. L'ARM9 est alors stocke non compresse, ce qui "
                         "alourdit la ROM sans changer sa taille finale. "
                         "Voir scripts/patch_hasard.py.")
    ap.add_argument("--rotation", action="store_true", default=True,
                    help="PATCHE LE CODE. Actif par defaut. Fait tourner le lot "
                         "de monstres EN COURS DE PARTIE, sans changer de zone : "
                         "toutes les 1 024 images (environ 17 s) la liste est "
                         "retiree et les modeles recharges. Les conteneurs sont "
                         "elargis a 150 especes pour que les especes neuves "
                         "franchissent le portier de l'apparition. Voir "
                         "scripts/patch_conteneurs.py et patch_rotation.py.")
    ap.add_argument("--sans-rotation", dest="rotation", action="store_false",
                    help="lot fixe pour toute la duree d'une zone. C'EST LE "
                         "REGLAGE SUR : la rotation vide la liste de "
                         "prechargement en pleine partie, ce qui gele le jeu au "
                         "hasard (voir docs/research/RESEARCH.md 60).")
    ap.add_argument("--periode", type=int, default=0,
                    help="images entre deux rotations (0 = 1 024, environ 17 s). "
                         "Doit etre un immediat ARM encodable : 512, 1 024, "
                         "2 048 conviennent.")
    ap.add_argument("--sans-montage-force", dest="montage", action="store_false",
                    help="ne pas forcer le rechargement des modeles en pleine "
                         "partie. La liste rafraichie prend alors effet au "
                         "prochain rechargement naturel -- fin de combat ou "
                         "changement de zone. C'est le reglage SUR : le montage "
                         "force plante au hasard (voir patch_rotation.py).")
    ap.add_argument("--tirages", type=int, default=0,
                    help="especes tirees a chaque rotation (0 = 12, le maximum). "
                         "Baisser ce nombre allege le rechargement de modeles "
                         "donc la saccade, mais reduit le choix offert a "
                         "l'apparition : les emplacements restants sont pris par "
                         "les monstres encore vivants.")
    ap.add_argument("--portier", action="store_true",
                    help="P3 : PORTIER UNIVERSEL. N'importe quelle espece du "
                         "bestiaire peut apparaitre a CHAQUE apparition -- le "
                         "combat est alors juste, mais le symbole sur la carte "
                         "porte l'apparence d'une des especes deja chargees. "
                         "Ne touche ni au tas des modeles ni a la VRAM, donc "
                         "aucun risque de gel. Voir scripts/patch_portier.py.")
    ap.add_argument("--place", action="store_true",
                    help="P4 etape 1 : rend au tas des modeles le reliquat que "
                         "le montage confisque (36 a 99 Ko par zone, mesure) et "
                         "le cree en ExpHeap pour que l'eviction modele par "
                         "modele devienne possible. Deux mots. Ne change rien "
                         "seul : prepare le chargement a la demande. Voir "
                         "scripts/patch_place.py.")
    ap.add_argument("--etapes", type=int, default=None,
                    help="BISSECTION de l'amorce : 1 allouer seulement, 2 +lire "
                         "le fichier, 3 +synchroniser les caches, 4 +installer "
                         "(defaut). Le premier etage qui bloque le demarrage "
                         "nomme le coupable.")
    ap.add_argument("--blob", action="store_true",
                    help="P4 COMPLET : le chargeur a la demande dans un bloc que "
                         "l'allocateur du jeu GARANTIT libre, relu depuis un "
                         "fichier ajoute a la ROM. Remplace --portier et "
                         "--chargeur, dont les emplacements dans l'ARM9 se sont "
                         "reveles non fiables (voir docs/research/RESEARCH.md 72). Implique "
                         "--place. Voir scripts/patch_amorce.py.")
    ap.add_argument("--chargeur", action="store_true",
                    help="P4 : CHARGEMENT A LA DEMANDE. Le modele de l'espece "
                         "tiree est charge au moment ou elle apparait, en "
                         "reutilisant le prechargeur du jeu en mode « une seule "
                         "espece ». L'apparence du symbole devient donc juste, "
                         "au lieu d'etre empruntee. Implique --portier et "
                         "--place. Voir scripts/patch_chargeur.py.")
    ap.add_argument("--greffes", default="",
                    help="BISECTION : liste des greffes du prechargeur a poser, "
                         "parmi A,TAB,VRAM,DEPART,ESPECE,BOUCLE (defaut toutes). "
                         "Sert a isoler celle qui casse les cartes sans monstres.")
    ap.add_argument("--sans-declencheur", dest="declencheur",
                    action="store_false", default=True,
                    help="BISECTION : poser les greffes du prechargeur SANS le "
                         "declencheur, pour n'exercer que leur mode normal.")
    ap.add_argument("--expheap", action="store_true",
                    help="convertir le tas des modeles en ExpHeap. DESACTIVE "
                         "PAR DEFAUT : sur un frame heap `Free` rembobine tout "
                         "le tas, et le jeu compte dessus -- la conversion "
                         "cassait les textures des cartes sans monstres "
                         "(batiments, villes). Ne servira qu'avec l'eviction.")
    ap.add_argument("--garde", type=int, default=0,
                    help="octets gardes dans le tas des modeles pour le "
                         "chargement a la demande ; tout le reste est cede au "
                         "tas des requetes asynchrones. Defaut 32768.")
    ap.add_argument("--plafond", type=int, default=0,
                    help="avec --place : nombre d'especes que le prechargeur "
                         "charge (0 = pas de plafond). Sans plafond il en charge "
                         "8 a 11 et remplit le tas, ce qui donne les apparences "
                         "empruntees les plus variees. A 5, il reste 50 a 92 Ko "
                         "libres d'un seul bloc pour le chargement a la demande.")
    ap.add_argument("--sans-hasard", dest="hasard", action="store_false",
                    help="ne pas patcher le code : les especes d'une zone sont "
                         "alors figees a la construction, comme avant v14.")
    ap.add_argument("--taille-max", dest="taille_max", type=int, default=0,
                    help="n'autoriser que les especes dont le modele de terrain "
                         "tient dans N octets une fois decompresse (0 = pas de "
                         "filtre). Les modeles vont de 5 500 a 61 368 o ; le tas "
                         "des modeles d'une carte n'en tient qu'un budget limite, "
                         "donc ecarter les plus gros permet d'en charger plus. "
                         "Mesure par scripts/tailles_modeles.py.")
    ap.add_argument("--especes", type=int, default=8,
                    help="nombre d'especes par zone (defaut 8, maximum "
                         "raisonnable 10). Le jeu precharge au plus 12 modeles "
                         "par carte et en ajoute 1 a 4 en dur, d'ou la marge. "
                         "Le vanilla en declare 4 a 6.")
    ap.add_argument("--remplir-zones", dest="remplir", action="store_true",
                    default=False,
                    help="DANGEREUX, DESACTIVE PAR DEFAUT. Remplit les "
                         "emplacements d'espece qui paraissent libres. Teste en "
                         "jeu : PLUS AUCUN MONSTRE n'apparait. Ces emplacements "
                         "ne sont donc pas libres -- ils portent une autre "
                         "information, et les ecraser casse la zone. Conserve "
                         "pour memoire seulement.")
    ap.add_argument("--boss", action="store_true",
                    help="randomiser aussi les 98 COMBATS SCRIPTES du scenario "
                         "(data/event/eventbattle.bin). Separe de --rencontres "
                         "parce que c'est bien plus risque pour la progression : "
                         "un boss de fin trop faible banalise le jeu, un boss "
                         "precoce trop fort le bloque.")
    ap.add_argument("--boss-garder-premier", action="store_true",
                    help="laisser HEXACORNE tel quel (combat scripte 2, espece "
                         "300). C'est le premier boss du scenario et le seul "
                         "qu'on affronte SEUL, sans equipe : n'importe quel "
                         "autre boss a sa place peut rendre la partie "
                         "infaisable. Sans cette option il est tire comme les "
                         "autres. N'a d'effet qu'avec --boss.")
    ap.add_argument("--stats", dest="stats", action="store_true", default=False,
                    help="randomiser AUSSI les statistiques des monstres. "
                         "Desactive par defaut : le randomizer ne touche qu'aux "
                         "rencontres.")
    ap.add_argument("--objets", dest="objets", action="store_true",
                    default=True,
                    help="randomiser le CONTENU DES CONTENEURS : coffres "
                         "bleus, pots, tonneaux, placards (tables de tirage de "
                         "treasure.nsarc) et coffres rouges (scripts de zone). "
                         "Les objets importants ne sont jamais tires, et le "
                         "coffre de la Magic key garde son contenu. Les "
                         "grottos ne sont pas touches. ACTIF PAR DEFAUT depuis "
                         "la 1.2 ; --sans-objets pour ne randomiser que les "
                         "monstres, comme la 1.1.")
    ap.add_argument("--sans-objets", dest="objets", action="store_false",
                    help="ne pas toucher au contenu des conteneurs")
    ap.add_argument("--boutiques", dest="boutiques", action="store_true",
                    default=True,
                    help="randomiser le STOCK DES BOUTIQUES "
                         "(data/bin/menu/shopdata1.bin, 37 etals). Chaque "
                         "emplacement garde sa famille : un armurier ne vend "
                         "pas d'epee et une epicerie garde son compte "
                         "d'accessoires. Aucun objet important. La boutique du "
                         "chronocristal n'est pas touchee ; la boutique "
                         "secrete de Pontaudy et les deux etals d'Ablithia "
                         "d'apres-jeu ne vendent que du 4 etoiles et plus. "
                         "ACTIF PAR DEFAUT depuis la 1.3 ; --sans-boutiques "
                         "pour laisser les etals du jeu tels quels.")
    ap.add_argument("--sans-boutiques", dest="boutiques", action="store_false",
                    help="laisser les boutiques telles qu'en vanilla")
    ap.add_argument("--sans-prix-objets", dest="prix_objets",
                    action="store_false", default=True,
                    help="avec --boutiques : ne PAS fabriquer de prix pour les "
                         "241 objets qui n'en ont pas. Ils restent alors hors "
                         "des etals (sans prix, ils y seraient gratuits). "
                         "Fabriquer les prix fait grossir les neuf archives "
                         "d'objets, donc la disposition de la ROM change et "
                         "les savestates d'une autre construction ne valent "
                         "plus.")
    ap.add_argument("--sans-drops", dest="drops", action="store_false",
                    default=True,
                    help="avec --objets, laisser les drops des monstres "
                         "(mon_btldata.nat) tels qu'en vanilla")
    ap.add_argument("--boss-terrain", dest="boss_terrain", action="store_true",
                    help="EXPERIMENTAL, HORS DE L'APPLICATION. Le joueur n'en "
                         "veut pas dans le randomizer : ce qu'il veut, ce sont "
                         "les combats de boss du scenario (--boss), pas des "
                         "boss qui se promenent. L'option reste parce qu'elle "
                         "est ecrite et mesuree, mais elle n'est ni dans "
                         "--chaos-total ni dans la fenetre, et elle seule "
                         "active la greffe d'index a deux octets. LES BOSS "
                         "PEUVENT ALORS APPARAITRE SUR LE TERRAIN. Le "
                         "bestiaire s'arrete a 256 et tout ce qui suit est un "
                         "boss ; cette option les ajoute au tirage. MESURE : "
                         "150 identifiants hors bestiaire, 74 ont un modele de "
                         "terrain, 54 portent un identifiant que le tireur ne "
                         "sait pas designer -- il en reste 16, ceux que le jeu "
                         "emploie lui-meme comme symboles d'antre. La table "
                         "des fiches du blob grandit en consequence.")
    ap.add_argument("--objets-chaos", dest="objets_chaos", action="store_true",
                    help="avec --objets : IGNORER LES RANGS. N'importe quel "
                         "objet dans n'importe quel conteneur, l'equipement "
                         "legendaire compris, des le premier tonneau. Par "
                         "defaut les objets rares viennent des endroits rares.")
    ap.add_argument("--boutiques-chaos", dest="boutiques_chaos",
                    action="store_true",
                    help="avec --boutiques : IGNORER LES FAMILLES ET LA "
                         "RARETE. N'importe quel objet vendable dans "
                         "n'importe quel etal ; un armurier peut vendre une "
                         "herbe et une epicerie une armure legendaire. Les "
                         "trois boutiques du rare redeviennent ordinaires. La "
                         "boutique du chronocristal reste intouchee et aucun "
                         "objet important n'est jamais vendu.")
    ap.add_argument("--vocations", dest="vocations", action="store_true",
                    default=False,
                    help="OUVRIR LES DOUZE VOCATIONS des le debut. Six "
                         "s'obtiennent normalement par une quete (gladiateur, "
                         "paladin, armagicien, ranger, sage, luminaire) ; le "
                         "pere Blaise, a l'abbaye des Vocations, les propose "
                         "toutes. Un seul mot change dans l'overlay de "
                         "l'abbaye (scripts/patch_vocations.py). Les quetes "
                         "restent jouables. Prouve en jeu le 25 septembre.")
    ap.add_argument("--vocations-embauche", dest="vocations_embauche",
                    action="store_true", default=False,
                    help="VOCATION TIREE AU HASARD A L'EMBAUCHE : un "
                         "compagnon recrute chez Tulipe (auberge "
                         "d'Ablithia) recoit une vocation parmi les douze, "
                         "quelle que soit celle qu'on a choisie dans le menu. "
                         "Tirage fait par le jeu a la creation, donc "
                         "different a chaque recrue. Le menu de Tulipe ne "
                         "propose plus qu'une entree, << Aleatoire >>. Prouve "
                         "en jeu le 25 septembre.")
    ap.add_argument("--vocations-bloquees", dest="vocations_bloquees",
                    action="store_true", default=False,
                    help="VOCATIONS BLOQUEES : chez le pere Blaise, << Changer "
                         "de vocation >> est refuse par un message (5 langues), "
                         "et la << Voix de la vocation >> aussi. La "
                         "renouvocation reste permise (elle ne change pas de "
                         "vocation). Chacun garde la vocation qu'il a recue. "
                         "Les quetes de deblocage restent jouables ; celles "
                         "qui exigent d'exercer une autre vocation ne le sont "
                         "plus. A combiner avec --vocations-embauche et "
                         "--vocation-depart pour une equipe tiree au sort pour "
                         "toute la partie.")
    ap.add_argument("--vocation-depart", dest="vocation_depart",
                    action="store_true", default=False,
                    help="VOCATION DE DEPART DU HEROS TIREE AVEC LA GRAINE, au "
                         "lieu de troubadour. Le heros reste affiche << Gardien "
                         ">> pendant le prologue, comme dans le jeu d'origine ; "
                         "la vocation tiree apparait apres la chute. Ne vaut "
                         "que pour une NOUVELLE partie. Prouve en jeu le "
                         "25 septembre.")
    ap.add_argument("--butin-combat", dest="butin", action="store_true",
                    default=False,
                    help="LE BUTIN DES MONSTRES TIRE A CHAQUE COMBAT : quand "
                         "un monstre lache un objet, l'objet est tire au "
                         "hasard parmi les 1 088 objets du pool au lieu d'etre "
                         "celui de son espece. Les chances de butin ne "
                         "bougent pas. Version EQUILIBREE : un objet 4 ou 5 "
                         "etoiles n'est garde qu'une fois sur 8 (1,7 %% des "
                         "butins). Greffe dans l'overlay 23 "
                         "(scripts/patch_butin.py). Prouve en jeu le "
                         "25 septembre.")
    ap.add_argument("--butin-combat-libre", dest="butin_libre",
                    action="store_true", default=False,
                    help="avec --butin-combat (qu'il implique) : N'IMPORTE "
                         "QUEL OBJET a chances egales, l'equipement "
                         "legendaire compris (12 %% de 4-5 etoiles).")
    ap.add_argument("--coffres-rouges-libres", dest="rang_rouges",
                    action="store_false", default=True,
                    help="avec --objets : un coffre rouge peut contenir "
                         "N'IMPORTE QUEL objet, de 0 a 5 etoiles -- le "
                         "comportement jusqu'a la 1.5. Par defaut il garde la "
                         "rarete de son objet vanilla a une etoile pres, "
                         "parce qu'un coffre rouge est POSE dans une zone : "
                         "sans cette borne la Morteresse donne une veste "
                         "d'entrainement, constate en jeu.")
    ap.add_argument("--objets-sans-consommables", dest="consommables",
                    action="store_false", default=True,
                    help="avec --objets : NE PAS reserver de part aux "
                         "consommables, c'est-a-dire le comportement de la "
                         "1.3. Le pool compte 944 equipements pour 144 "
                         "consommables, donc neuf lignes sur dix rendent de "
                         "l'equipement -- defaut signale par le joueur apres "
                         "la 1.2 (ZER-28). Par defaut on amene des "
                         "consommables dans les tables et on leur donne les "
                         "plus grosses parts de chaque rang : mesure sur la "
                         "graine 3, de 11 a 32 %% du poids pour les coffres "
                         "bleus et de 7 a 36 %% pour les pots. Les chances "
                         "d'or, d'embuscade et de vide ne bougent pas.")
    ap.add_argument("--boutiques-sans-progression", dest="progression",
                    action="store_false", default=True,
                    help="avec --boutiques : NE PAS borner le prix de ce qu'une "
                         "boutique vend. Par defaut chaque etal ne propose rien "
                         "de plus cher que ce que le vanilla y vend deja -- les "
                         "37 boutiques sont rangees par ordre d'histoire, donc "
                         "cette borne suit la progression et une armurerie de "
                         "debut de partie reste utilisable. Les trois "
                         "boutiques du rare n'y sont pas soumises. Sans borne, "
                         "le tirage est uniforme sur tout le catalogue.")
    ap.add_argument("--sorts", dest="sorts", action="store_true", default=False,
                    help="randomiser LES SORTS APPRIS PAR NIVEAU : les 107 "
                         "triplets (vocation, sort, niveau) de "
                         "data/prm/spelltable.bin. Les niveaux et le nombre de "
                         "sorts par vocation ne bougent pas ; seuls les sorts "
                         "changent, sans doublon dans une meme vocation. Les "
                         "trois vocations sans magie (guerrier, artiste "
                         "martial, gladiateur) n'en recoivent pas. DESACTIVE "
                         "PAR DEFAUT tant que ce n'est pas valide en jeu.")
    ap.add_argument("--sorts-chaos", dest="sorts_chaos", action="store_true",
                    help="avec --sorts : ne pas ranger les sorts tires par "
                         "puissance. Par defaut une vocation apprend encore "
                         "ses sorts faibles tot et ses sorts forts tard, la "
                         "puissance etant mesuree par le niveau median auquel "
                         "le vanilla enseigne chaque sort. Avec cette option, "
                         "Omniheal peut tomber au niveau 1.")
    ap.add_argument("--aptitudes", dest="aptitudes", action="store_true",
                    default=False,
                    help="randomiser LES APTITUDES DES ARBRES DE COMPETENCES "
                         "(data/prm/skilltable.bin, 26 arbres de 11 paliers). "
                         "Par defaut les aptitudes sont melangees A "
                         "L'INTERIEUR de chaque arbre : un arbre d'epees ne "
                         "donne que des techniques d'epee, ce qui compte "
                         "puisqu'une technique d'arme exige cette arme en "
                         "main. Les bonus de caracteristique ne bougent pas. "
                         "DESACTIVE PAR DEFAUT tant que ce n'est pas valide "
                         "en jeu.")
    ap.add_argument("--aptitudes-chaos", dest="aptitudes_chaos",
                    action="store_true",
                    help="avec --aptitudes : melanger les 147 aptitudes et les "
                         "139 bonus entre TOUS les arbres, par bandes de cout. "
                         "Une technique d'epee peut alors s'apprendre dans "
                         "l'arbre des fouets -- il faudra une epee pour s'en "
                         "servir ; un bonus d'arme garde son arme et son "
                         "libelle la nomme.")
    ap.add_argument("--chaos-total", dest="chaos_total", action="store_true",
                    help="raccourci : --boss --sorts --sorts-chaos "
                         "--aptitudes --aptitudes-chaos --objets-chaos "
                         "--boutiques-chaos --coffres-rouges-libres "
                         "--boss-garder-premier --vocations "
                         "--vocations-embauche --vocation-depart "
                         "--butin-combat "
                         "--butin-combat-libre. "
                         "Tout ce qui peut etre tire l'est sans borne. "
                         "N'INCLUT PAS --boss-terrain, qui est experimental.")
    ap.add_argument("--inclure-speciaux", action="store_true",
                    help="toucher aussi les entrees de test et le mannequin d'entrainement")
    ap.add_argument("-o", "--sortie", help="chemin de la ROM produite")
    ap.add_argument("--patch", action="store_true",
                    help="produire aussi un patch xdelta3 de la ROM d'origine "
                         "vers la ROM randomisee. Le patch ne contient QUE la "
                         "difference, donc aucune donnee du jeu : il se partage "
                         "sans rien redistribuer.")
    ap.add_argument("--patch-seul", dest="patch_seul", action="store_true",
                    help="comme --patch, puis supprimer la ROM produite. "
                         "Il ne reste que le patch.")
    ap.add_argument("--langue", default="en", choices=("de", "en", "es", "fr", "it"),
                    help="langue des noms de monstres dans le journal (defaut en)")
    ap.add_argument("--a-blanc", action="store_true",
                    help="calculer et journaliser sans ecrire de ROM")
    ap.add_argument("--sans-controle-rom", dest="controle_rom",
                    action="store_false", default=True,
                    help="ne pas refuser une ROM dont l'empreinte MD5 n'est "
                         "pas celle de la version Europe. Reserve au "
                         "developpement : la ROM de reference reste alors "
                         "celle que DQ9_VANILLA ou banc/roms/ designe.")
    a = ap.parse_args()

    if a.chaos_total:
        # PAS --boss-terrain : voir son aide. Le chaos porte sur ce que le
        # joueur a demande -- le loot, les etals, et les boss du scenario.
        a.boss = True
        # HEXACORNE RESTE EPARGNE, MEME EN CHAOS TOTAL. C'est ce que coche le
        # prereglage "Total chaos" de la fenetre, et les deux chemins doivent
        # produire la meme ROM. Sans ca, la graine 7 mettait Baramos (608) au
        # premier combat du scenario, celui qu'on livre sans equipe.
        a.boss_garder_premier = True
        a.objets_chaos = a.boutiques_chaos = True
        a.consommables = a.progression = a.rang_rouges = False
        a.sorts = a.sorts_chaos = True
        a.aptitudes = a.aptitudes_chaos = True
        a.vocations = a.vocations_embauche = a.vocation_depart = True
        a.butin = a.butin_libre = True
    if a.butin_libre:
        a.butin = True
    adopter_source(a.rom, a.controle_rom)
    rng = random.Random(a.seed)
    print(f"lecture de {a.rom}")
    try:
        table, rom = TableMonstres.depuis_rom(a.rom, a.langue)
    except Exception as e:
        print(f"  (noms de monstres indisponibles : {e})")
        table, rom = TableMonstres.depuis_rom(a.rom)

    def nom(i):
        return getattr(table[i], "nom", None) or f"#{i}"
    avant = {i: bloc(table[i]) for i in range(len(table))}

    ordre = [i for i in range(len(table))
             if a.inclure_speciaux or table[i].id not in IDS_SPECIAUX]
    print(f"{len(table)} monstres, {len(ordre)} eligibles "
          f"({len(table) - len(ordre)} exclu(s))")
    detail = (f"fenetre={a.fenetre or 'aucune'}" if a.mode == "shuffle"
              else f"paliers={a.paliers}" if a.mode == "chaos"
              else f"ampleur={a.ampleur}")
    print(f"mode={a.mode} seed={a.seed} {detail} "
          f"resistances={'oui' if a.resistances else 'non'}")

    if a.stats:
        MODES[a.mode](rng, table, ordre, a.resistances, a)
    else:
        print("  statistiques : INTACTES (ajouter --stats pour les randomiser)")

    # --- rencontres : quelles especes apparaissent ou ---
    rencontres = None
    # LE POOL DES BOSS D'ANTRE, tires a chaque visite par le blob (ZER-37).
    pool_antres = None
    if a.rencontres or a.boss:
        fichiers = ((FICHIERS_RENCONTRES if a.rencontres else ())
                    + (FICHIERS_SCRIPTES if a.boss else ()))
        ids_valides = {table[i].id for i in range(len(table))}

        # DEUX ENSEMBLES PERMUTES SEPAREMENT, et c'est essentiel.
        #
        # Une premiere version permutait sur le bestiaire entier : un emplacement
        # de terrain pouvait donc recevoir un BOSS, et l'utilisateur en a vu
        # apparaitre. L'exclusion des boss ne couvrait que les entrees AJOUTEES
        # par l'agrandissement, pas les entrees existantes reecrites ici.
        #
        # Desormais :
        #   - les especes de terrain sont permutees ENTRE ELLES ;
        #   - les especes des combats scriptes (les boss) sont permutees entre
        #     elles, separement ;
        #   - le reste (especes qui n'apparaissent qu'en groupe de combat) est
        #     laisse intact.
        # Les deux ensembles sont disjoints par construction, donc les deux
        # correspondances fusionnent sans conflit.
        from agrandir_zones import construire_pool
        pool_terrain, pool_boss = construire_pool(a.rom)
        # LES BOSS SORTENT AUSSI DES TABLES DE RENCONTRES, et pas seulement du
        # bitmap. Le bitmap gouverne le TIRAGE a l'apparition ; les tables, elles,
        # decident de ce que la carte precharge et de ce que son conteneur
        # accepte. Dix-sept boss rodaient en vanilla comme symboles d'antre --
        # Equinocte et le general Mac Assin ont ete vus en plaine -- et la
        # permutation les redistribuait sur tout le terrain.
        # LES POOLS SONT EN IDENTIFIANTS, LA LISTE BLANCHE EN INDEX : on passe par
        # la table pour comparer (ZER-16 ; voir montable.ids_par_index).
        from monstres_nommes import MONSTRES as _MONSTRES
        _index = {table[i].id: i for i in range(len(table))}
        _avant = len(pool_terrain)
        _boss = {i for i in pool_terrain if _index.get(i) not in _MONSTRES}
        pool_boss = sorted(set(pool_boss) | _boss)
        pool_terrain = [i for i in pool_terrain if i not in _boss]
        if _boss:
            print(f"  boss retires du pool de terrain : {len(_boss)}")

        def permuter(pool):
            cibles = list(pool)
            rng.shuffle(cibles)
            return dict(zip(pool, cibles))

        # UN BOSS DOIT DEVENIR UN BOSS, et c'est un troisieme ensemble, pas
        # deux. `construire_pool` rend « les especes qui n'apparaissent qu'en
        # combat scripte » : sur 101, seules 89 sont des boss, les 12 autres
        # sont des monstres ordinaires que le jeu n'emploie jamais comme
        # symbole. Permuter les 101 ensemble donnait Zoma -> gluant, Malroth ->
        # cuirassassin, Psaro -> scarlatin : douze combats de scenario
        # devenaient triviaux. Mesure du 21 septembre, sur la graine 7.
        # Le critere reste celui du jeu : le bestiaire s'arrete a 256.
        # HEXACORNE RESTE HEXACORNE, SUR DEMANDE. On le retire du pool AVANT
        # le melange : une espece absente du pool n'est ni source ni cible,
        # donc elle se retrouve inchangee dans les trois tables ou elle figure
        # (encfld, encbtl, eventbattle -- une occurrence chacune, verifie).
        # L'ecarter apres coup ne suffirait pas : un autre boss prendrait sa
        # place.
        pool_vrais_boss = [i for i in pool_boss if _index.get(i) not in _MONSTRES]
        pool_scriptes_ordinaires = [i for i in pool_boss
                                    if _index.get(i) in _MONSTRES]

        # CE QU'ON RETIRE DES TROIS POOLS AVANT DE MELANGER. Une espece
        # absente d'un pool n'en est ni source ni cible : elle se retrouve
        # inchangee partout ou elle figure. L'ecarter apres le melange ne
        # suffirait pas -- une autre prendrait sa place.
        garde = set(PROLOGUE)
        if a.boss_garder_premier:
            garde.add(HEXACORNE)
        pool_terrain = [i for i in pool_terrain if i not in garde]
        pool_vrais_boss = [i for i in pool_vrais_boss if i not in garde]
        pool_scriptes_ordinaires = [i for i in pool_scriptes_ordinaires
                                    if i not in garde]
        print("  laisses en place : combat du prologue (%s)%s"
              % (", ".join(str(i) for i in PROLOGUE),
                 ", hexacorne (%d)" % HEXACORNE if a.boss_garder_premier
                 else ""))

        if a.boss:
            pool_antres = list(pool_vrais_boss)
        corresp = permuter(pool_terrain)
        corresp.update(permuter(pool_vrais_boss))
        corresp.update(permuter(pool_scriptes_ordinaires))
        print(f"  permutations : {len(pool_terrain)} especes de terrain, "
              f"{len(pool_vrais_boss)} boss entre eux, "
              f"{len(pool_scriptes_ordinaires)} especes de combat scripte "
              f"ordinaires entre elles")
        rencontres = TablesRencontres(rom, fichiers)
        total, detail_fichiers = rencontres.compter(ids_valides)
        # on releve l'etat AVANT, pour pouvoir journaliser ce qui a change :
        # c'est la seule trace lisible de ce que le randomizer a fait
        cartes_avant = ({c: list(v) for c, v in rencontres.cartes().items()}
                        if a.rencontres else {})
        if a.tirage_libre:
            choix = [table[i].id for i in ordre]
            n_modif = rencontres.appliquer_tirage_libre(rng, choix, ids_valides)
        else:
            n_modif = rencontres.appliquer(corresp, ids_valides)
        print(f"rencontres : mode "
              f"{'tirage libre' if a.tirage_libre else 'permutation globale'}")
        print(f"rencontres : {total} references d'espece "
              f"({', '.join(f'{k}={v}' for k, v in sorted(detail_fichiers.items()))})")
        print(f"             {n_modif} remplacee(s)")

    # coherence : tout doit tenir dans les types du format
    for i in range(len(table)):
        for s in STATS:
            v = getattr(table[i], s)
            assert 0 <= v <= 0xFFFF, f"monstre {i} {s} hors plage : {v}"
        assert all(0 <= x <= 255 for x in table[i].res_elem + table[i].res_etat)

    # journal
    base = a.sortie or f"work/dq9_rand_{a.mode}_s{a.seed}.nds"
    os.makedirs(os.path.dirname(base) or ".", exist_ok=True)
    journal = os.path.splitext(base)[0] + "_journal.txt"
    modifies = 0
    with open(journal, "w", encoding="utf-8") as jf:
        jf.write(f"Randomizer DQ9 - mode={a.mode} seed={a.seed} {detail} "
                 f"resistances={a.resistances}\n")
        jf.write(f"ROM source : {a.rom}\n")
        jf.write(f"rencontres={a.rencontres} boss={a.boss} stats={a.stats} "
                 f"tirage_libre={a.tirage_libre}\n\n")

        # --- ce que le randomizer a fait aux rencontres ---
        if rencontres is not None:
            par_id = {table[i].id: nom(i) for i in range(len(table))}
            if not a.tirage_libre:
                jf.write("=" * 78 + "\n")
                jf.write("SUBSTITUTION DES ESPECES (permutation globale : une "
                         "espece devient toujours la meme)\n")
                jf.write("=" * 78 + "\n")
                jf.write(f"  {'id':>4}  {'espece d origine':<28s} -> "
                         f"{'id':>4}  espece de remplacement\n")
                jf.write("-" * 78 + "\n")
                for ancien in sorted(corresp):
                    nouveau = corresp[ancien]
                    if nouveau == ancien:
                        continue
                    jf.write(f"  {ancien:4d}  {str(par_id.get(ancien))[:28]:<28s} -> "
                             f"{nouveau:4d}  {par_id.get(nouveau)}\n")
                jf.write("\n")
            if a.rencontres and cartes_avant:
                apres = rencontres.cartes()
                jf.write("=" * 78 + "\n")
                jf.write("ESPECES PAR CARTE, AVANT ET APRES\n")
                jf.write("=" * 78 + "\n")
                for c in sorted(cartes_avant):
                    av = [str(par_id.get(i, i)) for i in cartes_avant[c]]
                    ap2 = [str(par_id.get(i, i)) for i in apres.get(c, [])]
                    jf.write(f"  carte {c}\n")
                    jf.write(f"     avant : {', '.join(av)}\n")
                    jf.write(f"     apres : {', '.join(ap2)}\n")
                jf.write("\n")

        if not a.stats:
            jf.write("statistiques des monstres : INTACTES\n")
        entete = (f"  idx   id  {'monstre':<26s}       "
                  + "".join(f"{s:>9}" for s in STATS))
        jf.write(entete + "\n" + "-" * len(entete) + "\n")
        for i in range(len(table)):
            av, ap_ = avant[i], bloc(table[i])
            if av != ap_:
                modifies += 1
                jf.write(f"{i:5d} {table[i].id:4d}  {nom(i)[:26]:<26s} avant"
                         + "".join(f"{av[s]:9d}" for s in STATS) + "\n")
                jf.write(f"{'':11s} {'':<26s} apres"
                         + "".join(f"{ap_[s]:9d}" for s in STATS) + "\n")
    if a.stats:
        print(f"{modifies} monstre(s) modifie(s) aux statistiques")
    print(f"journal detaille : {journal}")

    # Rapport sur les statistiques : n'a de sens que si on y a touche.
    # C'est une INFORMATION, pas un objectif -- un randomizer est cense etre dur.
    if a.stats:
        print("\nrepartition des HP par tranche de progression (information)")
        print(f"  {'tranche':<12} {'avant (min-med-max)':<28} {'apres (min-med-max)'}")
        for k, grp in enumerate(tranches(ordre, 8)):
            av = sorted(avant[i]["hp"] for i in grp)
            ap_ = sorted(table[i].hp for i in grp)
            print(f"  {k * 100 // 8:3d}-{(k + 1) * 100 // 8:3d} %     "
                  f"{av[0]:6d} {av[len(av) // 2]:6d} {av[-1]:6d}"
                  f"            {ap_[0]:6d} {ap_[len(ap_) // 2]:6d} {ap_[-1]:6d}")
        print("\n  premiers monstres du bestiaire :")
        for i in ordre[:6]:
            print(f"    {nom(i)[:22]:<22s} HP {avant[i]['hp']:5d} -> {table[i].hp:5d}   "
                  f"XP {avant[i]['exp']:6d} -> {table[i].exp:6d}")

    if a.a_blanc:
        print("\n--a-blanc : aucune ROM ecrite")
        return

    print("\nreinjection et reconstruction de la ROM (environ 50 s)...")
    if a.stats:
        table.ecrire_dans_rom(rom)
    if rencontres is not None:
        rencontres.ecrire_dans_rom()
    if a.agrandir and a.rencontres:
        # Reconstruction COHERENTE des deux fichiers. Voir scripts/resync_zones.py
        # et docs/research/RESEARCH.md §24 : le conteneur RAM n'accepte que 6 entrees par
        # groupe, une espece doit figurer dans encmons.bin pour pouvoir
        # apparaitre, et le jeu maintient l'invariant
        # union(especes des groupes) <= liste encmons.
        from resync_zones import reconstruire
        print(f"resynchronisation des zones a {a.especes} especes :")
        reconstruire(rom, rng, a.especes)
    if a.remplir and a.rencontres:
        from remplir_zones import remplir
        ids_v = {table[i].id for i in range(len(table))}
        choix = sorted(i for i in ids_v if i <= 347)
        n_rempl = remplir(rom, rng, ids_v, choix)
        print(f"emplacements libres remplis : {n_rempl}")
    if a.objets:
        # PUREMENT DE LA DONNEE : on reecrit des u32 deja presents dans
        # data/scenario/treasure.nsarc, sans changer une seule taille de
        # fichier. Aucun patch de code, donc aucune interaction avec les
        # greffes de monstres ci-dessous.
        from patch_loot import patcher as patcher_loot
        from patch_loot import verifier as verifier_loot
        print("objets des conteneurs (coffres, pots, tonneaux, placards)%s :"
              % ("  [CHAOS : rangs ignores]" if a.objets_chaos else
                 ("  [part reservee aux consommables]" if a.consommables
                  else "  [sans part de consommables]")))
        with open(journal, "a", encoding="utf-8") as jf:
            c_loot = patcher_loot(rom, rng, langue=a.langue, journal=jf,
                                  drops=a.drops, chaos=a.objets_chaos,
                                  consommables=a.consommables
                                  and not a.objets_chaos,
                                  rang_rouges=a.rang_rouges)
        verifier_loot(rom)
        print(f"  {c_loot['outcomes']} outcomes de table reecrits, "
              f"{c_loot['coffres']} coffres rouges, "
              f"{c_loot['coffres_gardes']} garde(s) pour cause d'objet "
              f"important, {c_loot['drops']} drops de monstres")
    if (a.vocations or a.vocations_embauche or a.vocations_bloquees
            or a.vocation_depart):
        # L'OVERLAY 3 (l'abbaye et le bar de Tulipe), le 9 (la creation d'un
        # compagnon), deux archives de textes (str_dam, bm_lui), et UN
        # immediat de l'overlay 17 pour la vocation de depart du heros (hors
        # de toute greffe de monstres ; diff_roms.py le sait).
        from patch_vocations import patcher as patcher_vocations
        from patch_vocations import verifier as verifier_vocations
        from patch_vocations import tirer_depart
        depart = tirer_depart(a.seed) if a.vocation_depart else None
        print("vocations :")
        patcher_vocations(rom, ouvrir=a.vocations,
                          embauche=a.vocations_embauche,
                          bloquer=a.vocations_bloquees, depart=depart)
        verifier_vocations(rom, ouvrir=a.vocations,
                           embauche=a.vocations_embauche,
                           bloquer=a.vocations_bloquees, depart=depart)
    if a.sorts:
        # PUREMENT DE LA DONNEE : 107 mots reecrits en place dans
        # spelltable.bin, aucune taille de fichier ne bouge.
        from patch_sorts import patcher as patcher_sorts
        from patch_sorts import verifier as verifier_sorts
        print("sorts appris par niveau%s :"
              % ("  [CHAOS : sans ordre de puissance]" if a.sorts_chaos else ""))
        with open(journal, "a", encoding="utf-8") as jf:
            c_sorts = patcher_sorts(rom, rng, journal=jf, chaos=a.sorts_chaos)
        verifier_sorts(rom)
        print(f"  {c_sorts['sorts']} sorts redistribues dans "
              f"{c_sorts['vocations']} vocations")
    if a.aptitudes:
        # PUREMENT DE LA DONNEE : 147 mots reecrits en place dans
        # skilltable.bin, aucune taille de fichier ne bouge.
        from patch_aptitudes import patcher as patcher_aptitudes
        from patch_aptitudes import verifier as verifier_aptitudes
        print("aptitudes des arbres de competences%s :"
              % ("  [CHAOS : melange entre arbres]" if a.aptitudes_chaos
                 else ""))
        with open(journal, "a", encoding="utf-8") as jf:
            c_apt = patcher_aptitudes(rom, rng, journal=jf,
                                      chaos=a.aptitudes_chaos,
                                      langue=a.langue)
        import ndspy.rom as _nr
        from rom_vanilla import chemin_vanilla as _cv
        verifier_aptitudes(rom, _nr.NintendoDSRom.fromFile(_cv()))
        print(f"  {c_apt['aptitudes']} aptitudes et {c_apt['bonus']} bonus "
              f"redistribues dans {c_apt['arbres']} arbres")
    if a.boutiques:
        if a.prix_objets:
            # A FAIRE AVANT LE TIRAGE DES ETALS : le pool des boutiques se
            # deduit des prix, donc tarifer d'abord fait entrer ces objets
            # dans le tirage. Seule etape de tout le randomizer qui change une
            # taille de fichier.
            from patch_prix import patcher as patcher_prix
            from patch_prix import verifier as verifier_prix
            print("prix des objets qui n'en avaient pas :")
            with open(journal, "a", encoding="utf-8") as jf:
                c_prix = patcher_prix(rom, langue=a.langue, journal=jf)
            verifier_prix(rom)
            print(f"  {c_prix['objets']} objets tarifes dans "
                  f"{c_prix['archives']} archives, +{c_prix['octets']:,} octets")
        # MEME NATURE QUE --objets : on reecrit des u32 deja presents dans
        # data/bin/menu/shopdata1.bin, aucune taille de fichier ne bouge,
        # aucun patch de code.
        from patch_boutiques import patcher as patcher_boutiques
        from patch_boutiques import verifier as verifier_boutiques
        print("stock des boutiques%s :"
              % ("  [CHAOS : familles, rarete et prix ignores]"
                 if a.boutiques_chaos else
                 ("  [prix bornes par la progression]" if a.progression
                  else "  [sans borne de prix]")))
        with open(journal, "a", encoding="utf-8") as jf:
            c_bout = patcher_boutiques(rom, rng, langue=a.langue, journal=jf,
                                       chaos=a.boutiques_chaos,
                                       prix_fabriques=a.prix_objets,
                                       progression=a.progression
                                       and not a.boutiques_chaos)
        verifier_boutiques(rom, chaos=a.boutiques_chaos,
                           prix_fabriques=a.prix_objets)
        print(f"  {c_bout['articles']} articles reecrits dans "
              f"{c_bout['boutiques']} boutiques, "
              f"{c_bout['intouchables']} intouchee(s), "
              f"{c_bout['rares']} boutique(s) du rare")
    if a.hasard:
        from patch_hasard import patcher
        print("tirage au chargement de zone (patch de code)%s :"
              % ("  [BOSS SUR LE TERRAIN]" if a.boss_terrain else ""))
        patcher(rom, taille_max=a.taille_max, boss=a.boss_terrain)
        # LA GREFFE C N'EST PLUS POSEE QU'AVEC LA ROTATION, ET C'EST GRAVE.
        #
        # Elle porte le conteneur a 150 especes, or le constructeur du jeu
        # (`0x0206F240`) n'est pas fait pour plus de douze : il indexe par
        # `ldrb r1, [r8, r5]` un tableau d'octets dimensionne pour la liste de
        # prechargement, avec r5 allant jusqu'a 149. Il alloue donc des tailles
        # arbitraires, epuise le tas de carte, et ses duplications de chaines
        # rendent des pointeurs corrompus -- les 18 enregistrements fautifs
        # mesures au 59. Mesure comparative sur la sauvegarde du joueur, six
        # allers-retours ville / terrain :
        #
        #   avec la greffe C : 8 puis 2 puis 7 modeles, GEL au sixieme passage
        #   sans la greffe C : 11 puis 10 modeles, aucun gel
        #
        # Elle ne servait qu'a donner de la matiere a la rotation. Sans rotation
        # elle est pure perte, et l'agrandissement des tas qui l'accompagne
        # consomme 147 Kio du tas parent pour rien.
        if a.rotation:
            # La greffe B a grandi pour porter son repli : elle occupe desormais
            # toute la fonction du tireur, y compris les 64 octets ou logeait le
            # morceau A de la rotation. Les deux ne peuvent plus coexister -- et
            # la rotation est de toute facon condamnee (docs/research/RESEARCH.md 63).
            raise SystemExit(
                "--rotation n'est plus compatible avec la greffe B a repli : "
                "voir docs/research/RESEARCH.md 63 et 64. Utiliser --sans-rotation.")
        if False:
            from patch_conteneurs import patcher as patcher_conteneurs
            print("conteneurs elargis :")
            patcher_conteneurs(rom)
            # L'ORDRE COMPTE : la greffe C passe avant la rotation, qui verifie
            # que son bourrage est encore vierge -- et les deux ecrivent dans le
            # meme ARM9 decompresse.
            from patch_rotation import patcher as patcher_rotation
            print("rotation en cours de partie :")
            patcher_rotation(rom, periode=a.periode, tirages=a.tirages,
                             force=a.montage)
        if a.blob:
            if not a.place:
                raise SystemExit("--blob implique --place.")
            from patch_amorce import patcher as patcher_amorce
            print("chargeur relogeable, dans un bloc alloue (P4) :")
            patcher_amorce(rom, plafond=a.plafond or None,
                           etapes=4 if a.etapes is None else a.etapes,
                           boss=a.boss_terrain, antres=pool_antres)
            if pool_antres:
                print(f"  boss d'antre : un tirage a chaque visite, parmi "
                      f"{len(pool_antres)} boss (ZER-37)")
        if a.chargeur and not (a.portier and a.place):
            raise SystemExit("--chargeur implique --portier et --place.")
        if a.place:
            from patch_place import patcher as patcher_place
            print("place dans le tas des modeles (P4 etape 1) :")
            # AVEC LE CHARGEUR, le plafond du prechargeur n'est plus un talon a
            # part : il devient la valeur initiale du mot BORNE, posee par la
            # greffe A de patch_chargeur. Les deux se disputeraient sinon le
            # meme site 0x021A2ACC.
            # AVEC LE BLOB AUSSI le plafond passe par le mot BORNE : la greffe A
            # du blob l'initialise et la greffe borne le sert. Poser en plus le
            # talon de plafond ecraserait le morceau C de l'ancienne rotation,
            # ou la borne loge deja (« 0x020f1d50 n'est pas libre »).
            patcher_place(rom, plafond=0 if (a.chargeur or a.blob) else a.plafond,
                          # AVEC LE BLOB L'EXPHEAP N'EST PLUS UNE OPTION : le
                          # declencheur rend le modele qu'il remplace, et un
                          # frame heap ne sait pas rendre un bloc. Le talon le
                          # conditionne au seuil de terrain, donc les villes et
                          # l'eglise gardent le frame heap et leurs textures.
                          expheap=a.expheap or a.blob,
                          **({"garde": a.garde} if a.garde else {}))
        if a.portier:
            # L'ORDRE COMPTE : le portier reecrit le tireur pose par
            # patch_hasard (la greffe B tirait dans les modeles charges, il la
            # remplace par un tirage dans le bitmap des 256 especes) et se loge
            # dans le bourrage que patch_hasard a laisse libre.
            from patch_portier import patcher as patcher_portier
            print("portier universel + emprunt de modele (P3) :")
            if a.chargeur and a.declencheur:
                # LE PLAN AVANT L'ECRITURE. Le chargeur vit en ITCM, a une
                # adresse fixe mais dont la valeur depend des tailles
                # assemblees : on calcule donc le plan ici pour que le portier
                # connaisse l'adresse du declencheur, et patch_chargeur le
                # recalculera a l'identique quand il ecrira.
                import ndspy.codeCompression as _cc
                from patch_chargeur import plan as plan_chargeur
                _mots, _pieces, _decl = plan_chargeur(
                    bytearray(_cc.decompress(bytes(rom.arm9))), a.plafond or 5)
                patcher_portier(rom, decl=_decl, mots=_mots)
            else:
                patcher_portier(rom)
        if a.chargeur:
            from patch_chargeur import patcher as patcher_chargeur
            print("chargement a la demande (P4 etape 2) :")
            from patch_chargeur import TOUTES
            g = tuple(x.strip() for x in a.greffes.split(",") if x.strip()) or TOUTES
            patcher_chargeur(rom, plafond=a.plafond or 5, greffes=g)
    elif a.portier:
        raise SystemExit("--portier a besoin du patch de code : retirer "
                         "--sans-hasard.")
    if a.butin:
        # UNE GREFFE DANS L'OVERLAY 23, celui du combat, que personne d'autre
        # ne touche. Independante du loot des conteneurs et des monstres.
        from patch_butin import patcher as patcher_butin
        from patch_butin import verifier as verifier_butin
        print("butin des monstres tire a chaque combat%s :"
              % ("  [LIBRE : tout objet a chances egales]" if a.butin_libre
                 else "  [4-5 etoiles rares]"))
        patcher_butin(rom, mode="libre" if a.butin_libre else "rares")
        verifier_butin(rom)
    rom.saveToFile(base)

    # La reconstruction retire le bourrage de fin de cartouche. On le remet :
    # le bourrage d'origine est integralement des 0xFF, donc la ROM produite
    # retrouve exactement la taille et la disposition de l'originale, ce qui en
    # fait un remplacement direct et rend les patchs minuscules.
    taille_src = os.path.getsize(a.rom)
    taille_out = os.path.getsize(base)
    if taille_out < taille_src:
        with open(base, "ab") as f:
            f.write(b"\xff" * (taille_src - taille_out))
        print(f"bourrage 0xFF restaure : {taille_src - taille_out:,} o")
    print(f"ecrit : {base}  ({os.path.getsize(base):,} o)")

    if a.patch or a.patch_seul:
        produire_patch(a.rom, base)
        if a.patch_seul:
            os.remove(base)
            print(f"ROM supprimee, il ne reste que le patch")


if __name__ == "__main__":
    main()
