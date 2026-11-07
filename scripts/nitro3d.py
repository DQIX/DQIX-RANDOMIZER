"""Read the parts of a Nitro 3D file (.nsbmd / .nsbca) that the secret boss
patches need: G3D dictionaries, blocks, texture and palette offsets.

Formats from the public G3D Nitro documentation ("patricia" dictionaries,
TEX0, JNT0), checked on the game's models. No dependency beyond `struct`.
"""
import struct


def u8(d, o): return d[o]
def u16(d, o): return struct.unpack_from("<H", d, o)[0]
def u32(d, o): return struct.unpack_from("<I", d, o)[0]
def fx32(d, o): return struct.unpack_from("<i", d, o)[0] / 4096.0
def fx16(d, o): return struct.unpack_from("<h", d, o)[0] / 4096.0


def dico(d, p):
    """[(name, entry bytes)] of the G3D dictionary at p."""
    n = d[p + 1]
    q = p + u16(d, p + 6)
    taille_entree = u16(d, q)
    q += 4
    entrees = [d[q + k * taille_entree:q + (k + 1) * taille_entree]
               for k in range(n)]
    q += n * taille_entree
    noms = [d[q + 16 * k:q + 16 * k + 16].split(b"\0")[0].decode("latin-1")
            for k in range(n)]
    return list(zip(noms, entrees))


def blocs(d, magie):
    """{block magic: offset} of a Nitro file whose magic is `magie`."""
    if d[:4] != magie:
        raise ValueError("pas un %s" % magie)
    n = u16(d, 0x0E)
    return {d[u32(d, 0x10 + 4 * k):u32(d, 0x10 + 4 * k) + 4]:
            u32(d, 0x10 + 4 * k) for k in range(n)}


def textures(d, t0):
    """TEX0 at t0: ([{nom, largeur, hauteur, format, transparent0, offset}],
    {palette name: offset}, {tex_data, cmp_data, cmp_idx, pal_data, pal_taille})."""
    tex_dico = t0 + u16(d, t0 + 0x0E)
    tex_data = t0 + u32(d, t0 + 0x14)
    cmp_data = t0 + u32(d, t0 + 0x24)
    cmp_idx = t0 + u32(d, t0 + 0x28)
    pal_dico = t0 + u32(d, t0 + 0x34)
    pal_data = t0 + u32(d, t0 + 0x38)
    pal_taille = u16(d, t0 + 0x30) << 3
    texs = []
    for nom, e in dico(d, tex_dico):
        p = u32(e, 0)
        off = (p & 0xFFFF) << 3
        w, h = 8 << ((p >> 20) & 7), 8 << ((p >> 23) & 7)
        fmt, t0r = (p >> 26) & 7, (p >> 29) & 1
        texs.append(dict(nom=nom, largeur=w, hauteur=h, format=fmt,
                         transparent0=bool(t0r), offset=off))
    pals = {}
    for nom, e in dico(d, pal_dico):
        pals[nom] = u16(e, 0) << 3
    ctx = dict(tex_data=tex_data, cmp_data=cmp_data, cmp_idx=cmp_idx,
               pal_data=pal_data, pal_taille=pal_taille)
    return texs, pals, ctx
