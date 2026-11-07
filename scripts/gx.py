"""Listes d'affichage GX d'un NSBMD : decodage, sommets absolus, reecriture.

Une forme (shape) du MDL0 : u16 tag, u16 taille, u32 drapeaux, u32 decalage de
la liste (depuis la forme), u32 taille de la liste. La liste : des mots de 4
commandes empaquetees, suivis de leurs parametres (32 bits chacun).
"""
import os
import struct
import sys

import nitro3d as N

NPARAMS = {0x00: 0, 0x10: 1, 0x11: 0, 0x12: 1, 0x13: 1, 0x14: 1, 0x15: 0, 0x16: 16,
           0x17: 12, 0x18: 16, 0x19: 12, 0x1A: 9, 0x1B: 3, 0x1C: 3, 0x20: 1, 0x21: 1,
           0x22: 1, 0x23: 2, 0x24: 1, 0x25: 1, 0x26: 1, 0x27: 1, 0x28: 1, 0x29: 1,
           0x2A: 1, 0x2B: 1, 0x30: 1, 0x31: 1, 0x32: 1, 0x33: 1, 0x34: 32, 0x40: 1,
           0x41: 0, 0x50: 1, 0x60: 1, 0x70: 3, 0x71: 2, 0x72: 1}


def formes(d):
    """[(position de la forme, position de la liste, taille)] du premier modele."""
    m0 = N.blocs(d, b"BMD0")[b"MDL0"]
    (_nom, e), = N.dico(d, m0 + 8)[:1]
    mod = m0 + N.u32(e, 0)
    sd = mod + N.u32(d, mod + 0x0C)
    out = []
    for _n, e in N.dico(d, sd):
        sh = sd + N.u32(e, 0)
        out.append((sh, sh + N.u32(d, sh + 8), N.u32(d, sh + 12)))
    return out


def decoder(dl):
    """[(commande, [parametres])]"""
    cmds, p = [], 0
    while p + 4 <= len(dl):
        mot = dl[p:p + 4]
        p += 4
        for c in mot:
            if c == 0 and not cmds:
                pass
            n = NPARAMS[c]
            cmds.append((c, list(struct.unpack_from("<%dI" % n, dl, p))))
            p += 4 * n
    # les NOP de bourrage en fin de mot restent : sans effet
    return cmds


def s(v, bits):
    v &= (1 << bits) - 1
    return v - (1 << bits) if v >> (bits - 1) else v


def sommets(cmds):
    """Positions absolues (unites fx 1/4096) apres chaque commande de sommet :
    [(index de commande, (x, y, z))]."""
    x = y = z = 0
    out = []
    for i, (c, ps) in enumerate(cmds):
        if c == 0x23:
            x, y = s(ps[0], 16), s(ps[0] >> 16, 16)
            z = s(ps[1], 16)
        elif c == 0x24:
            x, y, z = (s(ps[0] >> k, 10) << 6 for k in (0, 10, 20))
        elif c == 0x25:
            x, y = s(ps[0], 16), s(ps[0] >> 16, 16)
        elif c == 0x26:
            x, z = s(ps[0], 16), s(ps[0] >> 16, 16)
        elif c == 0x27:
            y, z = s(ps[0], 16), s(ps[0] >> 16, 16)
        elif c == 0x28:
            x += s(ps[0], 10)
            y += s(ps[0] >> 10, 10)
            z += s(ps[0] >> 20, 10)
        else:
            continue
        out.append((i, (x, y, z)))
    return out


def encoder(cmds):
    """Empaquette 4 commandes par mot (NOP pour completer)."""
    out = bytearray()
    for k in range(0, len(cmds), 4):
        grp = cmds[k:k + 4]
        grp += [(0, [])] * (4 - len(grp))
        out += bytes(c for c, _p in grp)
        for _c, ps in grp:
            out += struct.pack("<%dI" % len(ps), *[v & 0xFFFFFFFF for v in ps])
    return bytes(out)


if __name__ == "__main__":
    import collections
    for f in sys.argv[1:]:
        d = open(f, "rb").read()
        for sh, dl, n in formes(d):
            cmds = decoder(d[dl:dl + n])
            c = collections.Counter("%02X" % k for k, _p in cmds)
            v = sommets(cmds)
            zs = [p[2] / 4096 for _i, p in v]
            print(os.path.basename(f), "liste", n, "o", dict(c), "z %.2f..%.2f" % (min(zs), max(zs)))
