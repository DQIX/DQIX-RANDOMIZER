#!/usr/bin/env python3
"""Ajouter une chaine a une table de textes de DQ9, dans ses deux formats.

DEUX FORMATS, mesures le 25 septembre sur les menus de l'abbaye et du bar :

  * TABLE A ENREGISTREMENTS (`bm_*.bin`, `str_gskl_*.bin`) : en-tete de quatre
    u32 (nombre d'enregistrements, debut du pool, taille du pool, nombre de
    chaines), puis des enregistrements `tag u16, nombre de champs u8, type u8,
    champs u32`. Une chaine = tag 0x67, champs (identifiant, deplacement dans
    le pool). Un enregistrement 0x66 place avant les chaines en porte le
    compte. C'est le format que ZER-46 a deja etendu (`patch_aptitudes`).
  * TABLE DE MESSAGES (`str_dam_*.nat`) : un u32 `nombre | taille_du_pool << 12`,
    puis `nombre` couples (identifiant u32, deplacement u32), puis le pool.

Les chaines sont du texte balise du jeu (`<'e>`, `<,>`, `<PAGE>`...), en
octets ASCII.
"""
import struct


def _enregistrements(m):
    nb = struct.unpack_from("<I", m, 0)[0]
    out, p = [], 0x10
    for _ in range(nb):
        tag, nch = struct.unpack_from("<HB", m, p)
        out.append((p, tag, list(struct.unpack_from("<%dI" % nch, m, p + 4))))
        p += 4 + 4 * nch
    return out


def chaines_table(m):
    """{identifiant: texte} d'une table a enregistrements."""
    nb, pool, taille, _n = struct.unpack_from("<4I", m, 0)
    out = {}
    for _p, tag, f in _enregistrements(m):
        if tag == 0x67 and len(f) == 2 and f[1] != 0xFFFFFFFF:
            o = pool + f[1]
            out[f[0]] = bytes(m[o:m.find(b"\0", o)])
    return out


def ajouter_table(m, ident, texte):
    """Rend une copie de la table a enregistrements `m` avec la chaine
    `ident` en plus, placee dans l'ordre des identifiants."""
    nb, pool, taille, nch = struct.unpack_from("<4I", m, 0)
    recs = _enregistrements(m)
    if ident in chaines_table(m):
        raise ValueError("identifiant %#x deja pris" % ident)
    chaines = [(p, f) for p, tag, f in recs if tag == 0x67 and len(f) == 2]
    apres = max((p + 12 for p, f in chaines if f[0] < ident),
                default=chaines[0][0])
    fin_recs = recs[-1][0] + 4 + 4 * len(recs[-1][2])
    tete = (bytearray(m[:apres])
            + struct.pack("<HBBII", 0x67, 2, 1, ident, taille)
            + bytearray(m[apres:fin_recs]))
    for p, tag, f in recs:
        if tag == 0x66 and p < chaines[0][0] and len(f) == 1:
            struct.pack_into("<I", tete, p + 4, f[0] + 1)   # le compte
    tete += b"\xff" * (-len(tete) % 16)
    struct.pack_into("<4I", tete, 0, nb + 1, len(tete),
                     taille + len(texte) + 1, nch + 1)
    corps = tete + m[pool:pool + taille] + texte + b"\0"
    corps += b"\xff" * (-len(corps) % 16)
    return bytes(corps)


def messages(m):
    """{identifiant: texte} d'une table de messages `.nat`."""
    h = struct.unpack_from("<I", m, 0)[0]
    n = h & 0xFFF
    pool = 4 + 8 * n
    out = {}
    for i in range(n):
        ident, off = struct.unpack_from("<II", m, 4 + 8 * i)
        o = pool + off
        out[ident] = bytes(m[o:m.find(b"\0", o)])
    return out


def ajouter_message(m, ident, texte):
    """Rend une copie de la table de messages `m` avec `ident` en plus, a la
    fin (les identifiants du jeu sont contigus et croissants)."""
    h = struct.unpack_from("<I", m, 0)[0]
    n, taille = h & 0xFFF, h >> 12
    pool = 4 + 8 * n
    ids = [struct.unpack_from("<I", m, 4 + 8 * i)[0] for i in range(n)]
    if ident in ids or ident < max(ids):
        raise ValueError("identifiant %#x : deja pris ou hors ordre" % ident)
    if n + 1 > 0xFFF:
        raise ValueError("table pleine")
    out = bytearray(struct.pack("<I", (n + 1) | ((taille + len(texte) + 1) << 12)))
    out += m[4:pool] + struct.pack("<II", ident, taille)
    out += m[pool:pool + taille] + texte + b"\0"
    return bytes(out)
