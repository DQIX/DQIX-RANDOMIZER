#!/usr/bin/env python3
"""Decompresseurs des blocs internes des archives GPC2 de Dragon Quest IX.

Porte depuis le source C++ de DQIX/ArchiveTool (CompressA.cpp / CompressB.cpp /
CompressC.cpp), clone dans tools/community/.

Le u32 de controle qui prefixe chaque bloc donne le type et la taille finale :
    type   = controle & 7        0 = brut, 1 = A, 2 et 3 = B, 4 = C
    taille = controle >> 3

--- TYPE 1 : algorithme A ---

Le source C++ fait 176 lignes avec des `goto`, mais il contient une variable
`compressionType` initialisee a 0 et **jamais reassignee**. Toute la branche
`if (compressionType == 1)` est donc du code mort. Ce qui reste est un LZSS
classique :

    - un octet de controle fournit 8 drapeaux, lus du bit de poids fort au bit
      de poids faible ;
    - drapeau a 0 -> recopier un octet litteral ;
    - drapeau a 1 -> lire deux octets b1 et b2, puis recopier depuis la sortie
          longueur  = (b1 >> 4) + 3          (donc 3 a 18 octets)
          distance  = 1 + (((b1 & 0xF) << 8) | b2)   (donc 1 a 4096)

Recoupement avec le compresseur du meme depot, qui ecrit
`((longueur - 3) << 4) | (distance_moins_un >> 8)` puis `distance_moins_un & 0xFF` :
le decompresseur calcule `0x30 + b1`, et comme `0x30 = 3 << 4` cela reconstitue
`(longueur << 4) | (distance_moins_un >> 8)`. Les deux sens concordent exactement.

--- TYPES 2 et 3 : algorithme B ---   --- TYPE 4 : algorithme C ---
Portes plus bas, d'apres CompressB.cpp et CompressC.cpp.
"""
import struct


class ErreurLZ(Exception):
    pass


def decompresse_a(d, pos, fin, taille):
    """LZSS de DQ9 (type 1). `pos` est le debut des donnees, `fin` la borne."""
    out = bytearray()
    controle = 0
    bits = 0
    while len(out) < taille:
        if bits == 0:
            if pos >= fin:
                break
            controle = d[pos]
            pos += 1
            bits = 8
            continue
        if pos >= fin:
            break
        if (controle & 0x80) == 0:
            out.append(d[pos])
            pos += 1
        else:
            b1 = d[pos]
            pos += 1
            if pos >= fin:
                break
            b2 = d[pos]
            pos += 1
            # 0x30 = 3 << 4 : la longueur est stockee diminuee de 3
            ctl = 0x30 + b1
            distance = 1 + (((ctl & 0xF) << 8) | b2)
            longueur = ctl >> 4
            if distance > len(out):
                raise ErreurLZ(
                    f"distance {distance} au-dela du deja-decompresse "
                    f"({len(out)} o) : flux incoherent")
            for _ in range(longueur):
                if len(out) >= taille:
                    break
                out.append(out[-distance])
        controle = (controle << 1) & 0xFF
        bits -= 1
    return bytes(out)


def decompresse_bloc(d, pos, fin=None):
    """Lit le u32 de controle a `pos` et rend (donnees, type, taille_annoncee)."""
    if fin is None:
        fin = len(d)
    controle = struct.unpack_from("<I", d, pos)[0]
    typ = controle & 7
    taille = controle >> 3
    debut = pos + 4
    if typ == 0:
        return bytes(d[debut:debut + taille]), typ, taille
    if typ == 1:
        return decompresse_a(d, debut, fin, taille), typ, taille
    if typ in (2, 3):
        return decompresse_b(d, debut, fin, taille, 1 << typ), typ, taille
    if typ == 4:
        return decompresse_c(d, debut, fin, taille), typ, taille
    raise ErreurLZ(f"type de compression inconnu : {typ}")


def decompresse_b(d, pos, fin, taille, largeur):
    """Types 2 et 3 : decodeur binaire a table, porte de CompressB.cpp.

    `largeur` vaut 1 << type, donc 4 pour le type 2 et 8 pour le type 3 : c'est
    le nombre de bits produits par symbole.

    Le flux alterne des BLOCS de table et des mots de 32 bits de selection :
      - un octet donne la taille brute du bloc, puis `((taille + 1) << 1) - 1`
        octets de table, indexes a partir de 1 (l'octet de taille occupe l'index 0) ;
      - ensuite des u32 dont les bits sont consommes du poids fort au poids faible ;
        chaque bit fait avancer la position dans la table, et le bit 7 de l'entree
        atteinte signale un symbole complet.

    La ligne `if ((currDecomp - decompressedLength) < (shiftRegister >> 3))` du
    source d'origine fait une soustraction NON SIGNEE qui deborde tant que
    currDecomp < decompressedLength. On la reproduit telle quelle, sur 32 bits :
    c'est peut-etre un bug d'origine, mais le jeu vit avec.
    """
    out = bytearray()
    reg = 0          # nombre de bits accumules
    cumul = 0        # accumulateur 32 bits
    bloc_pos = 1
    while len(out) < taille:
        if pos >= fin:
            break
        taille_brute = d[pos]
        pos += 1
        n = ((taille_brute + 1) << 1) - 1
        bloc = bytearray(n + 1)
        for i in range(1, n + 1):
            if pos >= fin:
                return bytes(out[:taille])
            bloc[i] = d[pos]
            pos += 1
        bloc[0] = taille_brute
        while len(out) < taille:
            if pos + 4 > fin:
                return bytes(out[:taille])
            pack = struct.unpack_from("<I", d, pos)[0]
            pos += 4
            for _ in range(32):
                if bloc_pos >= len(bloc):
                    return bytes(out[:taille])
                offs = bloc[bloc_pos]
                bloc_pos &= ~1
                bloc_pos += ((offs & 0x3F) + 1) << 1
                bit = 1 if (pack & 0x80000000) else 0
                bloc_pos += bit
                offs = (offs << bit) & 0xFF
                pack = (pack << 1) & 0xFFFFFFFF
                if offs & 0x80:
                    if bloc_pos >= len(bloc):
                        return bytes(out[:taille])
                    valeur = bloc[bloc_pos]
                    cumul = (cumul >> largeur) | ((valeur << (32 - largeur)) & 0xFFFFFFFF)
                    bloc_pos = 1
                    reg += largeur
                    # soustraction non signee du source d'origine, sur 32 bits
                    if ((len(out) - taille) & 0xFFFFFFFF) < (reg >> 3):
                        cumul >>= (32 - reg)
                        reg = 32
                    if reg >= 32:
                        out += struct.pack("<I", cumul & 0xFFFFFFFF)
                        reg = 0
                        cumul = 0
                        if len(out) >= taille:
                            return bytes(out[:taille])
    return bytes(out[:taille])


def decompresse_c(d, pos, fin, taille):
    """Type 4 : RLE simple, porte de CompressC.cpp.

      octet de controle, bit 7 a 0 -> recopier (c & 0x7F) + 1 octets litteraux
      octet de controle, bit 7 a 1 -> lire un octet et le repeter (c & 0x7F) + 3 fois
    """
    out = bytearray()
    while len(out) < taille and pos < fin - 1:
        c = d[pos]
        pos += 1
        if (c & 0x80) == 0:
            n = (c & 0x7F) + 1
            out += d[pos:pos + n]
            pos += n
        else:
            n = (c & 0x7F) + 3
            if pos >= fin:
                break
            out += bytes([d[pos]]) * n
            pos += 1
    return bytes(out[:taille])
