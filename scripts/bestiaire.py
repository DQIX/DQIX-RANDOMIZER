"""La fiche du bestiaire montre le butin que la ROM donne (ZER-95).

CE QUE LE JEU FAIT (mesure du 19/10/2026, savestate du joueur sur la fiche
du concombrageur, v17o, sonde `bestiaire_objet.lua`). La fiche « Objets
abandonnes » ne lit PAS `mon_btldata.nat` : elle lit `data/prm/mons_info2.nat`,
qui recopie pour chaque espece l'experience, l'or et les deux objets. Le
randomizer n'avait jamais touche ce fichier : avec un butin change, la fiche
gardait l'objet vanilla (« Herbe curative » alors que l'espece donnait
l'epee cosmique).

LE FORMAT : un en-tete de 8 octets (u16 nombre = 438), puis 438 fiches de
48 octets, DANS L'ORDRE de `mon_btldata.nat` (verifie : les 438 especes et
leurs deux objets concordent sur la vanilla), puis d'autres donnees :

    +0  u32  experience        +6  u16  or
    +4  u16  espece            +8  u16  objet commun    +10 u16  objet rare

LA REGLE, decidee par le joueur (19/10/2026) :
  * butin FIXE par espece (loot de la 1.2, config) : la fiche porte les
    objets de `mon_btldata` (+4 commun, +6 rare) ;
  * butin TIRE A CHAQUE COMBAT (greffe de l'overlay 23, patch_butin) :
    l'espece n'a plus d'objet, la fiche reste celle du jeu de base.
Sur la vanilla, la regle rend le fichier a lui-meme : aucun octet ne change.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CHEMIN = "data/prm/mons_info2.nat"
CHEMIN_BTL = "data/prm/mon_btldata.nat"
ENTETE, PAS = 8, 48
BTL_ENTETE, BTL_PAS = 4, 0x84


def _fiches(info):
    n = struct.unpack_from("<H", info, 0)[0]
    if ENTETE + n * PAS > len(info):
        raise ValueError("mons_info2.nat : %d fiches annoncees, fichier de %d o"
                         % (n, len(info)))
    return n


def objets_btl(rom):
    """[(espece, commun, rare)] de mon_btldata, dans l'ordre du fichier."""
    b = bytes(rom.files[rom.filenames.idOf(CHEMIN_BTL)])
    n = (len(b) - BTL_ENTETE) // BTL_PAS
    out = []
    for i in range(n):
        o = BTL_ENTETE + i * BTL_PAS
        esp = struct.unpack_from("<H", b, o)[0] & 0x7FFF
        c, r = struct.unpack_from("<HH", b, o + 4)
        out.append((esp, c, r))
    return out


def attendu(rom, vanilla):
    """Les octets de mons_info2 que la regle donne a `rom`. `vanilla` : les
    octets vanilla du fichier."""
    import patch_butin
    info = bytearray(vanilla)
    if patch_butin.lire(rom) is not None:
        return bytes(info)
    n = _fiches(info)
    btl = objets_btl(rom)
    if len(btl) != n:
        raise ValueError("mons_info2 : %d fiches, mon_btldata %d" % (n, len(btl)))
    for i, (_esp, c, r) in enumerate(btl):
        struct.pack_into("<HH", info, ENTETE + i * PAS + 8, c, r)
    return bytes(info)


def accorder(rom, vanilla):
    """Ecrit la fiche du bestiaire de `rom` selon la regle. `vanilla` : la
    ROM d'origine (ndspy) ou les octets vanilla de mons_info2 ; sans elle,
    on part du fichier de `rom`. Rend le nombre de fiches changees."""
    fid = rom.filenames.idOf(CHEMIN)
    actuel = bytes(rom.files[fid])
    if vanilla is None:
        van = actuel
    elif isinstance(vanilla, (bytes, bytearray)):
        van = bytes(vanilla)
    else:
        van = bytes(vanilla.files[vanilla.filenames.idOf(CHEMIN)])
    neuf = attendu(rom, van)
    if neuf == actuel:
        return 0
    rom.files[fid] = neuf
    n = _fiches(neuf)
    return sum(neuf[ENTETE + i * PAS:ENTETE + (i + 1) * PAS]
               != actuel[ENTETE + i * PAS:ENTETE + (i + 1) * PAS]
               for i in range(n))


def verifier(rom, vanilla):
    """Leve si la fiche du bestiaire de `rom` ne suit pas la regle."""
    van = bytes(vanilla.files[vanilla.filenames.idOf(CHEMIN)])
    if bytes(rom.files[rom.filenames.idOf(CHEMIN)]) != attendu(rom, van):
        raise AssertionError("mons_info2 : la fiche du bestiaire ne montre "
                             "pas le butin de la ROM")


def verifier_vanilla(vanilla):
    """Leve si l'ordre et les objets de mons_info2 ne sont pas ceux de
    mon_btldata sur la vanilla (la base de la regle)."""
    info = bytes(vanilla.files[vanilla.filenames.idOf(CHEMIN)])
    n = _fiches(info)
    btl = objets_btl(vanilla)
    for i, (esp, c, r) in enumerate(btl[:n]):
        e2, _or, c2, r2 = struct.unpack_from("<HHHH", info, ENTETE + i * PAS + 4)
        if (e2, c2, r2) != (esp, c, r):
            raise AssertionError("mons_info2 fiche %d : %s, mon_btldata %s"
                                 % (i, (e2, c2, r2), (esp, c, r)))
    if attendu(vanilla, info) != info:
        raise AssertionError("mons_info2 : la regle change la vanilla")


if __name__ == "__main__":
    import ndspy.rom
    from rom_vanilla import chemin_vanilla
    v = ndspy.rom.NintendoDSRom.fromFile(chemin_vanilla())
    verifier_vanilla(v)
    print("bestiaire : %d fiches, ordre et objets de mon_btldata, vanilla "
          "inchangee" % _fiches(bytes(v.files[v.filenames.idOf(CHEMIN)])))
    if len(sys.argv) > 1:
        r = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
        verifier(r, v)
        print("%s : la fiche suit le butin" % sys.argv[1])
