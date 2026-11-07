"""Lire ET ecrire un script Nitro generique (le format de `treasure.lire_script`).

    en-tete, 16 octets   i32 nb d'instructions, u32 debut des donnees,
                         i32 longueur des donnees, u32 nb de chaines
    instruction          u16 opcode, u8 nb de parametres, 2 bits de type par
                         parametre (0 chaine, 1 entier, 2 flottant), bourrage
                         0xFF jusqu'au mot, puis 4 octets par parametre
    fin                  bourrage 0xFF jusqu'a 16, sans terminateur
    donnees              les chaines, terminees par 0 ; une chaine est un
                         decalage dans cette section

`lire()` rend [(op, [(type, valeur)])], une chaine rendue en `bytes` ;
`ecrire()` refait les octets. Aller-retour verifie au bit pres sur des
fichiers du jeu (`verifier_aller_retour`) : c'est la preuve du format.
"""
import struct

import treasure

CHAINE, ENTIER, FLOTTANT = 0, 1, 2


def lire(d):
    h, ins = treasure.lire_script(d)
    od = h["off_donnees"]
    out = []
    for i in ins:
        ps = []
        for t, v in zip(i.types, i.valeurs):
            if t == CHAINE and v != 0xFFFFFFFF:
                e = d.index(b"\0", od + v)
                ps.append((t, bytes(d[od + v:e])))
            else:
                ps.append((t, v))
        out.append((i.op, ps))
    return h, out


def _pad(b, n=16):
    return b + b"\xff" * (-len(b) % n)


def ecrire(instructions, fin_donnees=b""):
    """`instructions` : [(op, [(type, valeur)])] ; une chaine en `bytes`
    (ou `str`, encodee latin1), ou 0xFFFFFFFF pour « pas de chaine ».
    Les chaines egales ne sont ecrites qu'une fois, dans l'ordre d'apparition."""
    donnees = bytearray()
    places = {}
    code = bytearray()
    for op, ps in instructions:
        n = len(ps)
        types = bytearray((2 * n + 7) // 8)
        valeurs = []
        for k, (t, v) in enumerate(ps):
            types[k // 4] |= t << (2 * (k % 4))
            if t == CHAINE and v != 0xFFFFFFFF:
                if isinstance(v, str):
                    v = v.encode("latin1")
                if v not in places:
                    places[v] = len(donnees)
                    donnees += v + b"\0"
                v = places[v]
            valeurs.append(v & 0xFFFFFFFF)
        ligne = struct.pack("<HB", op, n) + bytes(types)
        ligne += b"\xff" * (-len(ligne) % 4)
        ligne += b"".join(struct.pack("<I", v) for v in valeurs)
        code += ligne
    # PAS DE TERMINATEUR : le bourrage 0xFF jusqu'a 16 en tient lieu quand il
    # y a la place (mesure : un code de 48 octets est suivi des donnees).
    code = _pad(bytes(code))
    donnees = bytes(donnees) + fin_donnees
    tete = struct.pack("<iIiI", len(instructions), 16 + len(code), len(donnees),
                       len(places))
    return _pad(tete + code + donnees)


def verifier_aller_retour(d):
    """Rend True si `ecrire(lire(d))` redonne exactement `d`."""
    h, ins = lire(d)
    od = h["off_donnees"]
    # ce qui suit la derniere chaine connue (souvent rien)
    return ecrire(ins) == bytes(d)
