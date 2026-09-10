#!/usr/bin/env python3
"""Agrandit les groupes de rencontre : plus d'especes par zone.

POURQUOI. Le jeu ne peut faire apparaitre que les especes dont il a precharge le
modele au chargement de la carte (docs/RESEARCH.md §20), et cette liste est le
GROUPE actif de la zone. Randomiser les identifiants ne change donc que
l'identite des 3 a 4 especes d'un groupe, pas leur nombre. Le seul levier reel
est d'ajouter des entrees aux groupes.

STRUCTURE, etablie par analyse (docs/RESEARCH.md §21) :

    tag 0x69 (5 champs)   en-tete de ZONE, champ 0 = identifiant de carte
      tag 0x68 (1 champ)  debut d'un GROUPE
      tag 0x66 (1 champ)  parametres du groupe
      tag 0x67 (2 champs) une ENTREE : identifiant sur 12 bits, poids sur 3 bits
      tag 0x67 ...
      tag 0x68            groupe suivant
    tag 0x69              zone suivante


LE PLAFOND EST 6 POUR LE TERRAIN, ET IL EST IMPOSE PAR LE CODE. La fonction
0x02073ED4 construit deux tableaux de candidats sur la pile, a `sp+0` et
`sp+0x18`, soit 24 octets chacun = 6 entrees de 4 octets. Et la mesure du fichier
donne exactement le meme maximum : aucun groupe d'encfld.bin ne depasse 6 entrees
en vanilla. Aller au-dela deborderait la pile.

On se limite donc strictement a ce que le jeu fait deja quelque part : apres
traitement, tous les groupes ont exactement 6 entrees, jamais plus.

LE POOL D'ESPECES. On ne tire que parmi les especes que le jeu utilise DEJA comme
symbole de terrain (260), moins celles qui apparaissent dans un combat scripte
(5 de recouvrement) : 255 especes. Deux garanties : aucun boss, et chaque espece
a deja fait la preuve qu'elle peut etre placee comme symbole. Les 77 especes qui
n'apparaissent que dans des groupes de combat sont ecartees, faute de savoir si
elles disposent d'un modele de terrain.

Usage: python scripts/agrandir_zones.py <rom.nds> <sortie.nds> <graine>
"""
import os
import random
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ndspy.rom
from montable import TableMonstres
from prmtable import PrmTable

# (fichier, tag de l'entree, nb de champs de l'entree, plafond par groupe)
# On n'agrandit QUE encfld.bin, et voici pourquoi.
#
# Pour encfld.bin le plafond de 6 est etabli deux fois : par le code (deux
# tableaux de 6 entrees sur la pile dans 0x02073ED4) et par les donnees (aucun
# groupe vanilla ne depasse 6).
#
# Pour encbtl.bin, un premier comptage annoncait un maximum de 12, mais il etait
# FAUX : il additionnait les enregistrements d'en-tete de groupe et les entrees.
# En agrandissant sur cette base, des groupes montaient a 16 entrees, au-dela de
# tout ce que le jeu fait. Faute de plafond etabli, on n'y touche pas. C'est de
# toute facon la composition des combats, pas les symboles sur la carte -- donc
# pas ce qui limite la variete visible.
CIBLES = [
    ("data/prm/encfld.bin", 0x67, 2, 6),
]
# La capacite peut etre relevee par scripts/patch_capacite.py, qui agrandit le
# cadre de pile de la fonction de selection. `agrandir()` accepte alors un
# plafond superieur a 6.
TAG_ZONE = 0x69

# LE POIDS EST LA RARETE, et il ne faut surtout pas l'egaliser.
#
# Mesure sur le vanilla : les 4 especes de poids median 1 rapportent 23 100 XP en
# mediane, contre ~400 pour les poids 3 a 5. Toute la famille metallique est a
# 1 ou 2 : `liquid metal slime` (40 200 XP), `platinum king jewel` (43 392 XP),
# `metal king slime` (54 504 XP). Leur rarete fait leur interet.
#
# Une premiere version egalisait tous les poids a 4 pour maximiser la variete
# percue. C'etait une erreur : elle transformait chaque jackpot d'experience en
# monstre banal.
#
# Desormais chaque espece porte SA rarete, calculee comme la mediane de ses poids
# dans le vanilla, et cette rarete est appliquee apres la permutation -- donc en
# fonction de l'espece qui occupe reellement l'emplacement, pas de celle qui s'y
# trouvait a l'origine.
POIDS_DEFAUT = 4
TAG_GROUPE_FLD = 0x68


def construire_rarete():
    """Rend {identifiant: poids}, la rarete naturelle de chaque espece.

    Calculee comme la mediane des poids observes dans le vanilla. Bornee a 1 au
    minimum : un poids de 0 rendrait l'entree inatteignable.
    """
    import statistics
    p = PrmTable(open("work/extracted/data/prm/encfld.bin", "rb").read())
    vus = {}
    for r in p.records:
        if r.tag == 0x67 and len(r.fields) == 2:
            v = r.fields[0]
            vus.setdefault(v & 0xFFF, []).append((v >> 12) & 7)
    return {i: max(1, round(statistics.median(w))) for i, w in vus.items()}


def construire_pool(rom_path):
    """Rend (pool_terrain, pool_boss), deux ensembles DISJOINTS.

    PARTITION, corrigee apres un bug visible en jeu. Une premiere version
    definissait le pool de terrain comme « especes qui rodent, MOINS celles qui
    apparaissent dans un combat scripte ». Les 5 especes de recouvrement se
    retrouvaient alors dans le pool des boss, et la permutation des boss les
    transformait en Dragonlord ou Malroth -- dans des emplacements de TERRAIN.

    Le critere correct est l'inverse : **une espece qui rode en vanilla est une
    espece de terrain**, meme si elle figure aussi dans un combat scripte. Le
    jeu lui-meme la place comme symbole, donc elle en a le modele et le droit.

        pool_terrain = especes utilisees comme symbole de terrain      (260)
        pool_boss    = especes des combats scriptes qui ne rodent JAMAIS (101)

    Les deux sont disjoints, et permuter a l'interieur de chacun garantit qu'un
    emplacement de terrain ne recevra jamais un boss.
    """
    table, _ = TableMonstres.depuis_rom(rom_path)
    ids = {m.id for m in table}

    tf = PrmTable(open("work/extracted/data/prm/encfld.bin", "rb").read())
    terrain = {(r.fields[0] & 0xFFF) for r in tf.records
               if r.tag == 0x67 and len(r.fields) == 2
               and (r.fields[0] & 0xFFF) in ids}

    te = PrmTable(open("work/extracted/data/event/eventbattle.bin", "rb").read())
    scriptes = set()
    for r in te.records:
        if r.tag == 0x64 and len(r.fields) == 9:
            for k in (1, 3, 5):
                if r.fields[k] in ids:
                    scriptes.add(r.fields[k])
    return sorted(terrain), sorted(scriptes - terrain)


def serialiser(entete, records, trailing):
    """Reconstruit le fichier. Un enregistrement = u16 tag + descripteur + champs."""
    corps = bytearray()
    for tag, desc, champs in records:
        corps += struct.pack("<H", tag) + desc
        for c in champs:
            corps += struct.pack("<I", c & 0xFFFFFFFF)
    d = bytearray(entete)
    struct.pack_into("<I", d, 0x00, len(records) + NB_NON_PARSES)
    struct.pack_into("<I", d, 0x04, len(corps) + len(trailing))
    return bytes(d) + bytes(corps) + trailing


NB_NON_PARSES = 0     # renseigne par agrandir()


def agrandir(rom, rng, pool, ids, bavard=True, plafond_force=None,
             rarete=None):
    if rarete is None:
        rarete = construire_rarete()
    global NB_NON_PARSES
    total_ajouts = 0
    for chemin, tag_entree, n_champs, plafond in CIBLES:
        if plafond_force:
            plafond = plafond_force
        fid = rom.filenames.idOf(chemin)
        brut = bytes(rom.files[fid])
        t = PrmTable(brut)
        entete = brut[:t.body]
        # nb annonce dans l'en-tete moins les enregistrements reellement parses :
        # ce sont ceux que le parseur laisse dans `trailing`
        NB_NON_PARSES = t.nb - len(t.records)

        # on reconstitue la liste (tag, desc, champs) puis on complete les groupes
        recs = [(r.tag, r.desc, list(r.fields)) for r in t.records]
        sortie, groupe, modele = [], [], None
        ajouts = 0

        def vider():
            nonlocal ajouts, groupe
            if not groupe:
                return
            entrees = [x for x in groupe if x[0] == tag_entree and len(x[2]) == n_champs]
            manque = plafond - len(entrees)
            if manque > 0 and entrees:
                gabarit = entrees[0]
                # SANS DOUBLON. Un premier jet tirait au hasard sans regarder le
                # groupe : `froicoucass` s'est retrouve deux fois dans la meme
                # zone, ce qui gaspille un emplacement sur les douze.
                deja = {x[2][0] & 0xFFF for x in entrees}
                dispo = [i for i in pool if i not in deja]
                rng.shuffle(dispo)
                for i in range(manque):
                    if not dispo:
                        break
                    champs = list(gabarit[2])
                    champs[0] = dispo.pop()
                    groupe.append((gabarit[0], gabarit[1], champs))
                    ajouts += 1
            # chaque entree recoit la rarete de l'espece qui l'occupe VRAIMENT,
            # apres permutation : un gluant de metal reste rare ou qu'il aille
            for k, x in enumerate(groupe):
                if x[0] == tag_entree and len(x[2]) == n_champs:
                    c = list(x[2])
                    esp = c[0] & 0xFFF
                    c[0] = (rarete.get(esp, POIDS_DEFAUT) << 12) | esp
                    groupe[k] = (x[0], x[1], c)
            sortie.extend(groupe)
            groupe = []

        for rec in recs:
            debut_groupe = (rec[0] == TAG_ZONE
                            or (rec[0] == TAG_GROUPE_FLD and len(rec[2]) == 1))
            if debut_groupe:
                vider()
            groupe.append(rec)
        vider()

        neuf = serialiser(entete, sortie, t.trailing)
        rom.files[fid] = neuf
        total_ajouts += ajouts
        if bavard:
            print(f"  {os.path.basename(chemin):<14s} {len(recs)} -> {len(sortie)} "
                  f"enregistrements (+{ajouts}), {len(brut):,} -> {len(neuf):,} o")
    return total_ajouts


if __name__ == "__main__":
    src, sortie = sys.argv[1], sys.argv[2]
    rng = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 0)
    pool, boss = construire_pool(src)
    print(f"pool : {len(pool)} especes de terrain, {len(boss)} boss exclus")
    rom = ndspy.rom.NintendoDSRom.fromFile(src)
    n = agrandir(rom, rng, pool, {m.id for m in TableMonstres.depuis_rom(src)[0]})
    print(f"{n} entrees ajoutees")
    rom.saveToFile(sortie)
    manque = os.path.getsize(src) - os.path.getsize(sortie)
    if manque > 0:
        with open(sortie, "ab") as f:
            f.write(b"\xff" * manque)
    print(f"ecrit : {sortie} ({os.path.getsize(sortie):,} o)")
