"""Le monde vide (ZER-116) : une fois Zenus vaincu, plus aucun PNJ ni monstre.

Decision du joueur (31/10/2026) : « on ne garde absolument personne ». Le
drapeau de victoire (`zenus_royaume.FAIT`, pose par le declencheur de genre 15)
coupe deux chemins, sans toucher a aucune donnee :

  PNJ. Tous les PNJ d'une carte sont crees par `0x0206DA90` (ARM9), appelee
  par l'overlay 17 en `0x021A2D94`, qui lit `<code>place.bin` (research
  §111.8). Son 5e argument, sur la pile, est la carte courante : une `0x03`
  ne cree son PNJ que si sa carte est celle-la. Le relais y ecrit 0xFFFF :
  la fonction tourne normalement (la liste est remise a zero), mais aucune
  entree ne correspond -- aucun PNJ.

  MONSTRES. Le tic d'apparition (ARM9 `0x02073C48`) et le repli de l'overlay
  17 (`0x021A24B0`, Sifflet et pontes sans espece) demandent d'abord la table
  du groupe a `0x02073ED4` ; s'ils recoivent 0, il n'y a pas d'apparition
  (`beq` qui suit, relu dans les deux). Le relais rend 0. Les deux `bl`
  touches ne sont reecrits par aucun mode (le blob reecrit `0x02073CA0` et
  `0x021A24CC`, le tireur, plus loin).

Le drapeau se lit a une adresse FIXE : l'objet de partie est en BSS de l'ARM9
(`0x02108844`, champ de bits en +0x8C, research §110.5) ; octet `drapeau >> 3`,
bit `drapeau & 7` (lecteur `0x0206DFC0`).

LA PLACE. 2 x 28 octets dans l'ARM9 (appeles depuis l'ARM9 et l'overlay 17),
pris dans des zones DEJA validees en jeu par le projet et restees vierges dans
le mode de cette ROM (les options se les partagent : `patch_hasard`,
`patch_stats` au combat, `patch_amorce`). Ce module passe EN DERNIER. Exclues :
`0x020F1CB8` (le blob y ecrit un compteur a l'execution) et `0x020F1D2C`
(`patch_place`).

Usage (essai) : python scripts/patch_monde_vide.py <entree.nds> <sortie.nds> [drapeau]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE_ARM9 = 0x02000000
COMPRESSED_END = 0xBBC - 0x1C + 0x14
FLAGS = 0x02108844 + 0x8C              # champ de bits des drapeaux de jeu

TABLE_GROUPE = 0x02073ED4              # rend la table du groupe, ou 0
PLACE = 0x0206DA90                     # cree les PNJ de la carte courante
SITES = (
    # (overlay ou None = ARM9, adresse du `bl`, cible d'origine, relais)
    (None, 0x02073C48, TABLE_GROUPE, "monstres"),     # le tic de terrain
    (17, 0x021A24B0, TABLE_GROUPE, "monstres"),       # le repli de l'overlay
    (17, 0x021A2D94, PLACE, "pnj"),                   # les PNJ de la carte
)
# L'Orion Express (S14, cartes 6401-6405) garde ses PNJ : c'est en parlant a
# l'Express (PNJ 2, modele s011, carte 6401) qu'on repart du royaume. Premier
# essai du joueur (31/10) : sans lui, plus de « ! », bloque au royaume.
EXPRESS = (6400, 6)                    # cartes [6400, 6406[
# Mais SEULS les PNJ sans modele y restent (joueur, 05/11 : « on a juste besoin du ! sur le tableau de
# bord »). Le tableau de bord est le PNJ 106, zone sans modele (S14Q0, 106_fr : « ne semble pas capable
# de dechiffrer les commandes ») ; l'hypothese du 31/10, « le ! est Stella », n'avait pas ete jouee.
# Fin de S14place.bin, sur le drapeau de victoire : 0x11 dont la carte n'est pas la carte courante RETIRE
# le PNJ (0x0206D66C). Stella 2, Aster 203, b012c 210.
S14 = "data/scenario/S14.npc"
S14_PLACE = "S14place.bin"
S14_RETIRES = (2, 203, 210)
CARTE_AUCUNE = 0xFFFF
TAILLE_RELAIS = {"monstres": 28, "pnj": 44}
# Zones validees en jeu (canari, puis greffes posees et jouees) ; on ne prend
# qu'une zone ENTIEREMENT vierge dans la ROM traitee.
CANDIDATS = (
    (0x02073FEC + 68, 64),     # queue du tireur, code mort quand patch_hasard l'a reecrit
    (0x020F1E40, 72),          # ROT_B (patch_stats au combat)
    (0x020E7C78, 40),          # GREFFE_C2 (patch_stats au combat)
    (0x020E8888, 40),          # GREFFE_C3 (patch_stats au combat)
    # EN FIN DE LISTE (06/11) : sans le hasard et AVEC les stats a chaque combat, les quatre
    # du dessus sont prises ou vivantes, et la ROM ne se construisait plus. Deux zones
    # validees en jeu par d'autres greffes, libres quand leur option n'est pas cochee :
    # ZONE_LIBRE de patch_hasard (canari 0 ecriture, son code y tourne depuis la 1.0) et
    # ROT_C (canari 57, talons de patch_place). En fin de liste : les ROM d'avant gardent
    # leurs relais au meme endroit, au bit pres.
    (0x020E7268, 280),         # ZONE_LIBRE (patch_hasard)
    (0x020F1D2C, 52),          # ROT_C (patch_place)
)


def relais_poses(rom):
    """{nom: adresse} des relais que les SITES appellent dans `rom` (vide sans monde vide)."""
    arm9 = _arm9_clair(rom)
    o17 = rom.loadArm9Overlays()[17]
    out = {}
    for ov, site, cible, nom in SITES:
        d, base = (arm9, BASE_ARM9) if ov is None else (o17.data, o17.ramAddress)
        mot = struct.unpack_from("<I", d, site - base)[0]
        if mot >> 24 == 0xEB:
            dest = site + 8 + (((mot & 0xFFFFFF) ^ 0x800000) - 0x800000) * 4
            if dest != cible:
                out[nom] = dest
    return out


def _octet_masque(drapeau):
    return FLAGS + (drapeau >> 3), 1 << (drapeau & 7)


def relais(nom, adr, drapeau):
    """Le relais `nom`, assemble a `adr` : instructions + 1 litteral."""
    from patch_hasard import assembler
    octet, masque = _octet_masque(drapeau)
    if nom == "monstres":
        fin = ["movne r0, #0", "bxne lr", "b #%d" % TABLE_GROUPE]
    else:
        # hors de l'Express, r12 = 0xFFFFFFFF : la carte devient 0xFFFF,
        # qu'aucune n'a
        fin = ["beq #%d" % PLACE, "ldrh r12, [sp]", "sub r12, r12, #%d" % EXPRESS[0],
               "cmp r12, #%d" % EXPRESS[1], "mvnhs r12, #0", "strhs r12, [sp]",
               "b #%d" % PLACE]
    code = assembler(["ldr r12, [pc, #{L0}]", "ldrb r12, [r12]",
                      "tst r12, #%d" % masque] + fin, adr, litteraux=(octet,))
    if len(code) != TAILLE_RELAIS[nom]:
        raise SystemExit("relais %s : %d o" % (nom, len(code)))
    return code


def _arm9_clair(rom):
    import ndspy.codeCompression as cc
    brut = bytes(rom.arm9)
    if struct.unpack_from("<I", brut, COMPRESSED_END)[0]:
        brut = cc.decompress(brut)
    arm9 = bytearray(brut)
    struct.pack_into("<I", arm9, COMPRESSED_END, 0)
    return arm9


def _places(arm9):
    """Un emplacement par relais dans les zones vierges, le plus grand d'abord."""
    libres = [[deb, n] for deb, n in CANDIDATS
              if not any(arm9[deb - BASE_ARM9:deb - BASE_ARM9 + n])]
    places = {}
    for nom in sorted(TAILLE_RELAIS, key=TAILLE_RELAIS.get, reverse=True):
        zone = next((z for z in libres if z[1] >= TAILLE_RELAIS[nom]), None)
        if zone is None:
            raise SystemExit("monde vide : pas de place (zones prises : %s)" % ", ".join(
                "%#x" % d for d, n in CANDIDATS
                if any(arm9[d - BASE_ARM9:d - BASE_ARM9 + n])))
        places[nom] = zone[0]
        zone[0] += TAILLE_RELAIS[nom]
        zone[1] -= TAILLE_RELAIS[nom]
    return places


def _retraits(drapeau):
    import nitro_script as N
    return [(0x11, [(N.ENTIER, 1 << 16 | drapeau), (N.ENTIER, 1), (N.ENTIER, 2), (N.ENTIER, CARTE_AUCUNE),
                    (N.ENTIER, pnj)] + [(N.FLOTTANT, 0)] * 4) for pnj in S14_RETIRES]


def retirer_express(rom, drapeau):
    """Stella, Aster et b012c quittent l'Express une fois Zenus vaincu ; le tableau de bord reste."""
    import nitro_script as N
    import treasure
    d = bytes(rom.getFileByName(S14))
    a, b = treasure.membres_narc(d)[S14_PLACE]
    _h, place = N.lire(d[a:b])
    rom.setFileByName(S14, treasure.reconstruire_narc(d, {S14_PLACE: N.ecrire(place + _retraits(drapeau))}))


def patcher(rom, drapeau=None, bavard=True):
    import ndspy.code
    from patch_hasard import bl
    if drapeau is None:
        from zenus_royaume import FAIT as drapeau
    arm9 = _arm9_clair(rom)
    ovl = rom.loadArm9Overlays()
    o17 = bytearray(ovl[17].data)
    places = _places(arm9)
    for nom, adr in places.items():
        arm9[adr - BASE_ARM9:adr - BASE_ARM9 + TAILLE_RELAIS[nom]] = relais(nom, adr, drapeau)
    for ov, site, cible, nom in SITES:
        d, base = (arm9, BASE_ARM9) if ov is None else (o17, ovl[17].ramAddress)
        o = site - base
        if bytes(d[o:o + 4]) != bl(site, cible):
            raise SystemExit("monde vide : %#x n'appelle plus %#x" % (site, cible))
        d[o:o + 4] = bl(site, places[nom])
    rom.arm9 = bytes(arm9)
    ovl[17].data = bytes(o17)
    rom.files[ovl[17].fileID] = ovl[17].save(compress=True)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovl)
    retirer_express(rom, drapeau)
    if bavard:
        print("  monde vide : drapeau %#x, relais a %s" % (drapeau, ", ".join(
            "%s %#x" % kv for kv in places.items())))
    return places


def verifier(rom, drapeau=None):
    """Les trois sites appellent un relais, et le relais est celui attendu."""
    from patch_hasard import bl
    if drapeau is None:
        from zenus_royaume import FAIT as drapeau
    arm9 = _arm9_clair(rom)
    o17 = rom.loadArm9Overlays()[17]
    for ov, site, cible, nom in SITES:
        d, base = (arm9, BASE_ARM9) if ov is None else (o17.data, o17.ramAddress)
        mot = struct.unpack_from("<I", d, site - base)[0]
        if mot >> 24 != 0xEB:
            raise AssertionError("monde vide : %#x n'est plus un bl" % site)
        dest = site + 8 + (((mot & 0xFFFFFF) ^ 0x800000) - 0x800000) * 4
        if bytes(arm9[dest - BASE_ARM9:dest - BASE_ARM9 + TAILLE_RELAIS[nom]]) \
                != relais(nom, dest, drapeau):
            raise AssertionError("monde vide : relais %s a %#x" % (nom, dest))
    import nitro_script as N
    import treasure
    d = bytes(rom.getFileByName(S14))
    a, b = treasure.membres_narc(d)[S14_PLACE]
    _h, place = N.lire(d[a:b])
    if place[-len(S14_RETIRES):] != _retraits(drapeau):
        raise AssertionError("monde vide : retraits de l'Express")
    return True


if __name__ == "__main__":
    import ndspy.rom
    entree, sortie = sys.argv[1:3]
    rom = ndspy.rom.NintendoDSRom.fromFile(entree)
    dr = int(sys.argv[3], 0) if len(sys.argv) > 3 else None
    patcher(rom, dr)
    verifier(rom, dr)
    rom.saveToFile(sortie)
    n, cible = os.path.getsize(sortie), os.path.getsize(entree)
    with open(sortie, "ab") as fo:
        fo.write(b"\xff" * (cible - n))
