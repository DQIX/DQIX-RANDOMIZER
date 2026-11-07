"""Le modele de l'Eclair de Zenus (ZER-116) : une epee du jeu dont la LAME est
remplacee par un eclair en zigzag, toute la palette passee a l'or et au
jaune-blanc.

  * la liste d'affichage est decodee (gx.py) ; chaque primitive dont les
    coordonnees de texture tombent toutes dans la partie « lame » de la
    texture (s < S_LAME) est retiree ; le reste (garde, poignee) est reecrit
    en VTX_16 absolus (l'ordre des groupes ne compte plus) ;
  * l'eclair : une bande de quads le long de Z (l'axe de la lame), le centre
    en zigzag, double face, texture de la lame etiree dessus ;
  * la liste est en fin de modele et de MDL0 : tailles du modele (+0, +0x10),
    du MDL0, decalage de TEX0 et taille du fichier corriges ; boite englobante
    et comptes recalcules.

Usage : python scripts/eclair.py <base.nsbmd> <s_lame> <sortie.nsbmd>
"""
import struct
import sys

import gx
import nitro3d as N

# centre de l'eclair (x, z) en unites de la liste, de la garde a la pointe
ZIGZAG = [(0.00, 1.25), (0.55, 2.45), (-0.20, 2.70), (0.50, 4.05),
          (-0.30, 4.35), (0.30, 5.45)]
POINTE = (-0.05, 6.55)
DEMI_LARGEUR = 0.30
OR_SOMBRE = (0.60, 0.38, 0.04)
JAUNE_BLANC = (1.00, 0.99, 0.80)


def _fx(v):
    return int(round(v * 4096))


def vtx16(x, y, z):
    return (0x23, [(_fx(x) & 0xFFFF) | ((_fx(y) & 0xFFFF) << 16), _fx(z) & 0xFFFF])


def texcoord(s, t):
    return (0x22, [(int(round(s * 16)) & 0xFFFF) | ((int(round(t * 16)) & 0xFFFF) << 16)])


PAR_PRIM = {0: 3, 1: 4}


def groupes(cmds):
    """[(type, [(texcoord (s, t), position (x, y, z) fx)])]"""
    pos = dict(gx.sommets(cmds))
    out, g, tc = [], None, (0, 0)
    for i, (c, p) in enumerate(cmds):
        if c == 0x40:
            g = (p[0], [])
        elif c == 0x22:
            tc = (gx.s(p[0], 16) / 16, gx.s(p[0] >> 16, 16) / 16)
        elif i in pos and g is not None:
            g[1].append((tc, pos[i]))
        elif c == 0x41:
            out.append(g)
            g = None
    return out


def construire(base, s_lame):
    d = bytearray(base)
    (sh, dl, n), = gx.formes(bytes(d))
    cmds = gx.decoder(bytes(d[dl:dl + n]))
    gardes = []                                     # [(type, sommets)]
    for typ, vs in groupes(cmds):
        if typ in PAR_PRIM:
            k = PAR_PRIM[typ]
            prims = [vs[j:j + k] for j in range(0, len(vs), k)]
            prims = [p for p in prims if any(tc[0] >= s_lame for tc, _p in p)]
            if prims:
                gardes.append((typ, [v for p in prims for v in p]))
        elif any(tc[0] >= s_lame for tc, _p in vs):
            gardes.append((typ, vs))
    # coordonnees de texture de la lame (le metal), pour l'eclair
    lame = [tc for _t, vs in groupes(cmds) for tc, _p in vs if tc[0] < s_lame]
    s0, s1 = min(t[0] for t in lame), max(t[0] for t in lame)
    t0, t1 = min(t[1] for t in lame), max(t[1] for t in lame)
    neuf = []
    for typ, vs in gardes:
        neuf.append((0x40, [typ]))
        for (s, t), (x, y, z) in vs:
            neuf.append(texcoord(s, t))
            neuf.append(vtx16(x / 4096, y / 4096, z / 4096))
        neuf.append((0x41, []))
    # l'eclair : quads entre deux points du zigzag, puis la pointe (triangle)
    pts = ZIGZAG
    zmin, zmax = pts[0][1], POINTE[1]

    def tex(x, z, cote):
        return (s0 if cote < 0 else s1), t1 - (z - zmin) / (zmax - zmin) * (t1 - t0)

    quads, tris = [], []
    for (xa, za), (xb, zb) in zip(pts, pts[1:]):
        w = DEMI_LARGEUR
        quads.append([(xa - w, za, -1), (xa + w, za, 1), (xb + w, zb, 1), (xb - w, zb, -1)])
    xa, za = pts[-1]
    tris.append([(xa - DEMI_LARGEUR, za, -1), (xa + DEMI_LARGEUR, za, 1), (POINTE[0], POINTE[1], 0)])
    for typ, prims in ((1, quads), (0, tris)):
        neuf.append((0x40, [typ]))
        for p in prims:
            for face in (p, p[::-1]):              # double face
                for x, z, cote in face:
                    neuf.append(texcoord(*tex(x, z, cote)))
                    neuf.append(vtx16(x, 0.0, z))
        neuf.append((0x41, []))
    liste = gx.encoder(neuf)
    liste += b"\0" * (-len(liste) % 8)
    delta = len(liste) - n
    if dl + n != len(d) - (len(d) - N.blocs(bytes(d), b"BMD0")[b"TEX0"]):
        raise AssertionError("la liste n'est pas en fin de MDL0")
    blocs = N.blocs(bytes(d), b"BMD0")
    m0 = blocs[b"MDL0"]
    (_nom, e), = N.dico(bytes(d), m0 + 8)[:1]
    mod = m0 + N.u32(e, 0)
    taille_mod = N.u32(d, mod)
    out = d[:dl] + liste + d[dl + n:]
    struct.pack_into("<I", out, sh + 12, len(liste))
    for o in (mod, mod + 0x10):
        if N.u32(d, o) == taille_mod:
            struct.pack_into("<I", out, o, taille_mod + delta)
    struct.pack_into("<I", out, m0 + 4, N.u32(d, m0 + 4) + delta)
    struct.pack_into("<I", out, 8, len(out))
    nb = struct.unpack_from("<H", d, 0x0E)[0]
    for k in range(nb):
        o = struct.unpack_from("<I", d, 0x10 + 4 * k)[0]
        if o > dl:
            struct.pack_into("<I", out, 0x10 + 4 * k, o + delta)
    # boite englobante (unites de la liste, fx16) et comptes
    tous = [(x / 4096, y / 4096, z / 4096) for _t, vs in gardes for _tc, (x, y, z) in vs]
    tous += [(x, 0.0, z) for p in quads + tris for x, z, _c in p]
    lo = [min(v[k] for v in tous) for k in range(3)]
    hi = [max(v[k] for v in tous) for k in range(3)]
    struct.pack_into("<6h", out, mod + 0x2C, *[_fx(v) for v in lo + [hi[k] - lo[k] for k in range(3)]])
    ntri = sum(len(vs) // 3 for t, vs in gardes if t == 0) + 2 * len(tris) + \
        sum(len(vs) - 2 for t, vs in gardes if t == 2)
    nquad = sum(len(vs) // 4 for t, vs in gardes if t == 1) + 2 * len(quads) + \
        sum((len(vs) - 2) // 2 for t, vs in gardes if t == 3)
    nsom = sum(len(vs) for _t, vs in gardes) + 8 * len(quads) + 6 * len(tris)
    struct.pack_into("<HHHH", out, mod + 0x24, nsom, ntri + nquad, ntri, nquad)
    return bytes(recolorer(out))


def dorer(c):
    """Une couleur BGR555 -> de l'or sombre au jaune-blanc, selon sa luminance."""
    r, g, b = (c & 31) / 31, ((c >> 5) & 31) / 31, ((c >> 10) & 31) / 31
    lum = min(1.0, (0.3 * r + 0.59 * g + 0.11 * b) * 1.35 + 0.15)
    nr, ng, nb = (OR_SOMBRE[i] + (JAUNE_BLANC[i] - OR_SOMBRE[i]) * lum for i in range(3))
    return round(nr * 31) | (round(ng * 31) << 5) | (round(nb * 31) << 10) | (c & 0x8000)


def recolorer(d):
    """Toutes les couleurs des palettes : luminance -> de l'or sombre au
    jaune-blanc (eclaircie, un eclair brille)."""
    d = bytearray(d)
    t0 = N.blocs(bytes(d), b"BMD0")[b"TEX0"]
    _texs, pals, ctx = N.textures(bytes(d), t0)
    for _nom, off in pals.items():
        p = ctx["pal_data"] + off
        for k in range(16):
            c = struct.unpack_from("<H", d, p + 2 * k)[0]
            r, g, b = (c & 31) / 31, ((c >> 5) & 31) / 31, ((c >> 10) & 31) / 31
            lum = min(1.0, (0.3 * r + 0.59 * g + 0.11 * b) * 1.35 + 0.15)
            nr, ng, nb = (OR_SOMBRE[i] + (JAUNE_BLANC[i] - OR_SOMBRE[i]) * lum for i in range(3))
            v = round(nr * 31) | (round(ng * 31) << 5) | (round(nb * 31) << 10) | (c & 0x8000)
            struct.pack_into("<H", d, p + 2 * k, v)
    return d


if __name__ == "__main__":
    base = open(sys.argv[1], "rb").read()
    out = construire(base, float(sys.argv[2]))
    open(sys.argv[3], "wb").write(out)
    print(sys.argv[3], len(base), "->", len(out))
