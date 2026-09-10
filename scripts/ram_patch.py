#!/usr/bin/env python3
"""Traduit les differences entre deux ROMs en une liste de mots a ecrire en RAM.

POURQUOI CE DETOUR. Un savestate restaure TOUTE la RAM, code compris : on ne
peut donc pas tester une modification de ROM en chargeant une sauvegarde faite
avant. Et refaire une sauvegarde coute un aller-retour avec le joueur, puisque
le harnais ne sait pas traverser les menus de demarrage.

La sortie est un fichier Lua que les sondes chargent par `dofile` et rejouent
avec `memory.write_u32_le`. Elle ne convient qu'au CODE : l'agrandissement des
tas du contexte de terrain, lui, est lu une seule fois a la creation du contexte
et ne peut pas se tester ainsi (docs/RESEARCH.md 56).

Usage: python scripts/ram_patch.py <origine.nds> <modifiee.nds> <sortie.lua>
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ndspy.codeCompression as cc
import ndspy.rom

COMPRESSED_END = 0xBBC - 0x1C + 0x14


def clair(brut):
    return cc.decompress(brut) if struct.unpack_from("<I", brut,
                                                     COMPRESSED_END)[0] else brut


def mots_differents(a, b, base):
    n = min(len(a), len(b))
    for i in range(0, n - 3, 4):
        x = struct.unpack_from("<I", a, i)[0]
        y = struct.unpack_from("<I", b, i)[0]
        if x != y:
            yield base + i, y


def main():
    src, mod, sortie = sys.argv[1], sys.argv[2], sys.argv[3]
    r0 = ndspy.rom.NintendoDSRom.fromFile(src)
    r1 = ndspy.rom.NintendoDSRom.fromFile(mod)
    mots = list(mots_differents(clair(bytes(r0.arm9)), clair(bytes(r1.arm9)),
                                0x02000000))
    n_arm9 = len(mots)
    o0, o1 = r0.loadArm9Overlays(), r1.loadArm9Overlays()
    for i in sorted(o0):
        if i not in o1:
            continue
        a, b = o0[i], o1[i]
        # `Overlay.data` est deja decompresse par ndspy quand `compressed`
        # est vrai : c'est `save()` qui recompresse. Rien a faire ici.
        da, db = a.data, b.data
        mots += list(mots_differents(da, db, a.ramAddress))
    with open(sortie, "w", encoding="utf-8") as f:
        f.write("-- produit par scripts/ram_patch.py : %s -> %s\n"
                % (os.path.basename(src), os.path.basename(mod)))
        f.write("return {\n")
        for adr, val in mots:
            f.write("  {0x%08X, 0x%08X},\n" % (adr, val))
        f.write("}\n")
    print(f"{len(mots)} mots ({n_arm9} dans l'ARM9, {len(mots) - n_arm9} dans "
          f"les overlays) -> {sortie}")


if __name__ == "__main__":
    main()
