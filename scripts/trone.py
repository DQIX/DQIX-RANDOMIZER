"""Zenus assis sur son trone (ZER-116, etape 2).

- Un fichier A PART, `data/chara_sub/s300.chr` (decision du joueur,
  30/10 : la statue s060 de la cinematique de fin ev15520 reste intacte),
  a la racine de chara_sub (voir ajouter_fichier). Contenu : s060.bcfg, le
  nsbmd repeint (zenus_mon.nsbmd_repeint), et `stand` = `walk` = la pose
  assise (data/zenus/trone_assis.nsbca, faite de la boucle `cut10suwal` de
  la cinematique, 13 images, jambes refaites a l'horizontale).
  Le chargeur reconnait les membres par leur extension (arm9 0x020EFB2B :
  ".nsbmd .nsbca ... .bcfg %s.%s"), pas par le nom du modele.
- Le PNJ 8 de X03 (genre 2, modele "z/zenus"), carte 4303 (temple, niveau 1),
  devant le heros du savestate zenus_trone : heros en (0.000, 1.143, -6.670)
  angle pi (face au trone), bloque a z = -7.44 contre le trone.

Usage : python scripts/trone.py <rom entree> <rom sortie> [x y z angle]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zenus_mon as Z
import ndspy.fnt
import ndspy.rom

import nitro_script as N
import treasure

CODE = "X03"
NPC = "data/scenario/X03.npc"
CARTE = 4303
PNJ = 8
FICHIER = "s300.chr"                    # les modeles du jeu s'arretent a s265
MODELE = FICHIER[:-4]
# genoux a l'origine. A x1,25 les cuisses reculent dans le dossier et le bassin descend dans l'assise
# (joueur, 05/11 : « il passe un peu a travers le siege ») : un peu plus haut et plus en avant.
POS = (0.0, 1.30, -8.2)
ANGLE = 0.0
# un peu plus grand que la statue d'origine (joueur, 31/10)
ECHELLE = float(os.environ.get("ECHELLE_TRONE", "1.25"))
# Zenus n'est la qu'entre le don (0x1FD pose) et la victoire (0x1FE pose)
DRAPEAUX = ((0x1FD, 1), (0x1FE, 0))


def _f(x):
    return struct.unpack("<I", struct.pack("<f", x))[0]


def renommer_bca(d, ancien, neuf):
    """Le nom de l'unique animation d'un NSBCA (dictionnaire G3D, noms sur 16
    octets ; avec une seule entree l'arbre ne depend pas du nom)."""
    d = bytearray(d)
    a = ancien.encode().ljust(16, b"\0")
    i = d.find(a)
    assert i > 0 and d.find(a, i + 1) < 0, ancien
    d[i:i + 16] = neuf.encode().ljust(16, b"\0")
    return bytes(d)


def chr_zenus(rom):
    """Le modele du trone, fait de la statue s060 de `rom`."""
    s060 = Z.s060(rom)
    # Le PNJ joue `stand` au repos (gros plan A/B du 30/10 ; une premiere
    # lecture « il joue walk » venait de captures trop petites). La pose
    # remplace aussi `walk`, par prudence.
    stand = Z.donnee("trone_assis.nsbca")    # deja nommee « stand »
    walk = renommer_bca(stand, "stand", "walk")
    # La taille passe par le noeud racine (zenus_mon.nsbca_echelle, 05/11), comme en combat.
    stand, walk = Z.nsbca_echelle(stand, ECHELLE), Z.nsbca_echelle(walk, ECHELLE)
    membres = {"s060.bcfg": s060["s060.bcfg"],
               "s060.nsbmd": Z.nsbmd_repeint(rom),
               "stand.nsbca": stand,
               "walk.nsbca": walk}
    return Z.narc_ecrit(membres)


def ajouter_effet(rom, data, fichier):
    """data/effect/<fichier>, meme methode qu'ajouter_fichier."""
    sub = rom.filenames["data"]["effect"]
    if fichier in sub.files:
        raise SystemExit("effect/%s existe deja" % fichier)
    fid = sub.firstID + len(sub.files)
    for f in _dossiers(rom.filenames):
        if f is not sub and f.firstID >= fid:
            f.firstID += 1
    sub.files.append(fichier)
    rom.files.insert(fid, data)
    assert rom.filenames.idOf("data/effect/" + fichier) == fid
    return fid


def _dossiers(f):
    yield f
    for _n, s in f.folders:
        yield from _dossiers(s)


def _chemins(rom):
    """({chemin: numero}, [numeros sans nom]) ; les overlays n'ont pas de nom."""
    out = {}

    def p(f, pre):
        for k, n in enumerate(f.files):
            out[pre + n] = f.firstID + k
        for n, s in f.folders:
            p(s, pre + n + "/")
    p(rom.filenames, "")
    nommes = set(out.values())
    return out, [i for i in range(len(rom.files)) if i not in nommes]


def ajouter_fichier(rom, data, fichier=FICHIER):
    """data/chara_sub/<FICHIER>, a la fin du dossier. UN SOUS-DOSSIER NE
    MARCHE PAS (30/10 : "z/zenus" invisible, le meme contenu sous "s060"
    affiche) : le fichier va donc a la racine de chara_sub, et tout ce qui
    suit est decale d'un numero (le jeu ouvre ses fichiers par chemin ; le
    blob aussi, patch_amorce). Les premiers numeros des dossiers suivants
    sont renumerotes a la main : ndspy ne le fait pas."""
    sub = rom.filenames["data"]["chara_sub"]
    if fichier in sub.files:
        raise SystemExit("chara_sub/%s existe deja" % fichier)
    fid = sub.firstID + len(sub.files)
    for f in _dossiers(rom.filenames):
        if f is not sub and f.firstID >= fid:
            f.firstID += 1
    sub.files.append(fichier)
    rom.files.insert(fid, data)
    assert rom.filenames.idOf("data/chara_sub/" + fichier) == fid
    return fid


def placer(rom, pos, angle, pnj=PNJ, modele=MODELE):
    global PNJ, MODELE
    PNJ, MODELE, ancien = pnj, modele, (PNJ, MODELE)
    try:
        _placer(rom, pos, angle)
    finally:
        PNJ, MODELE = ancien


def _placer(rom, pos, angle):
    d = bytes(rom.getFileByName(NPC))
    m = treasure.membres_narc(d)
    a, b = m[CODE + "npc.bin"]
    _h, liste = N.lire(d[a:b])
    if any(ps[0][1] == PNJ for op, ps in liste if op == 0x03):
        raise SystemExit("X03npc : le PNJ %d existe deja" % PNJ)
    liste.append((0x03, [(N.ENTIER, PNJ), (N.ENTIER, 2), (N.CHAINE, 0xFFFFFFFF),
                         (N.CHAINE, MODELE), (N.ENTIER, 2)]))
    a, b = m[CODE + "place.bin"]
    _h, place = N.lire(d[a:b])
    x, y, z = pos
    coords = [(N.FLOTTANT, _f(x)), (N.FLOTTANT, _f(y)), (N.FLOTTANT, _f(z)),
              (N.FLOTTANT, _f(angle))]
    if DRAPEAUX:
        # 0x11 (handler 0x0206D4F0, research §113) : le PNJ n'est cree que si
        # chaque drapeau de scenario (type 1) a la valeur dite ; nombre IMPAIR
        # de parametres = paires, moment (2 = toujours), carte, id, x, y, z, angle
        conds = []
        for drapeau, val in DRAPEAUX:
            conds += [(N.ENTIER, 1 << 16 | drapeau), (N.ENTIER, val)]
        place.append((0x11, conds + [(N.ENTIER, 2), (N.ENTIER, CARTE),
                                     (N.ENTIER, PNJ)] + coords))
    else:
        place.append((0x03, [(N.ENTIER, CARTE), (N.ENTIER, PNJ)] + coords))
    # PAS de 0x08 (31/10) : ce n'est pas une echelle, c'est une RONDE (le
    # PNJ fait l'aller-retour entre deux points a +-r dans la direction de
    # l'angle, handler 0x0206C704 : +0x1F = 8). Le joueur l'a vu bouger.
    if os.environ.get("RONDE"):
        place.append((0x08, [(N.ENTIER, PNJ), (N.FLOTTANT, _f(angle)),
                             (N.FLOTTANT, _f(1.0))]))
    rom.setFileByName(NPC, treasure.reconstruire_narc(
        d, {CODE + "npc.bin": N.ecrire(liste), CODE + "place.bin": N.ecrire(place)}))


def construire(entree, sortie, pos=POS, angle=ANGLE):
    rom = ndspy.rom.NintendoDSRom.fromFile(entree)
    ajouter_fichier(rom, chr_zenus(rom))
    placer(rom, pos, angle)
    rom.saveToFile(sortie)
    n, cible = os.path.getsize(sortie), os.path.getsize(entree)
    if n > cible:
        raise SystemExit("ROM plus grande que l'entree")
    with open(sortie, "ab") as fo:
        fo.write(b"\xff" * (cible - n))


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) >= 6:
        construire(a[0], a[1], tuple(map(float, a[2:5])), float(a[5]))
    else:
        construire(a[0], a[1])
