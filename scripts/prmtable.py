#!/usr/bin/env python3
"""Parseur du format de table de /data/prm (DQ9 NDS).

FORMAT DEDUIT (verifie sur une dizaine de fichiers) :

  En-tete :
    u32  nb_enregistrements
    u32  taille_donnees
    u32  0x1B  (constante ; vaut 0 sur certains fichiers -> variante a en-tete court)
    u32  0x02  (constante ; vaut 0 sur la variante courte)
    puis, sur la variante longue, deux entrees taggees de 8 octets (tags 0x65 et 0x64)
    -> le corps commence a 0x20 (variante longue) ou 0x10 (variante courte)

  Corps : suite d'enregistrements de taille VARIABLE :
    u16  tag          jeu observe : 0x64 a 0x69
                      0x64/0x65 = enregistrements d'en-tete ou de comptage
                      0x66..0x69 = enregistrements de donnees
    u8   nb_champs
    ...  description des types, bourrage 0xFF, le tout aligne pour que
         descripteur + 4*nb_champs soit la taille totale de l'enregistrement
    N x u32  les champs

  Le descripteur est constant pour tous les enregistrements d'un meme type dans un
  fichier donne : on peut donc le traiter comme un prefixe opaque et reecrire les
  champs sans le comprendre entierement (suffisant pour un randomizer).
"""
import collections
import struct
import sys

# Jeu de tags accepte. Il a fallu l'elargir : encbtl.bin et encfld.bin utilisent
# 0x67, 0x68 et 0x69, que la premiere version du parseur rejetait, ce qui donnait
# 0 enregistrement sur ces deux fichiers.
TAGS = frozenset(range(0x60, 0x70))


class Record:
    __slots__ = ("offset", "tag", "desc", "fields", "size")

    def __init__(self, offset, tag, desc, fields, size):
        self.offset = offset
        self.tag = tag
        self.desc = desc
        self.fields = fields
        self.size = size

    def __repr__(self):
        return f"<Rec @0x{self.offset:X} n={len(self.fields)} {self.fields}>"


class PrmTable:
    def __init__(self, path_or_bytes):
        if isinstance(path_or_bytes, (str, bytes)) and not isinstance(path_or_bytes, bytearray):
            if isinstance(path_or_bytes, str):
                with open(path_or_bytes, "rb") as f:
                    self.data = bytearray(f.read())
            else:
                self.data = bytearray(path_or_bytes)
        else:
            self.data = bytearray(path_or_bytes)
        d = self.data
        self.nb, self.data_size = struct.unpack_from("<II", d, 0)
        self.c8, self.cC = struct.unpack_from("<II", d, 8)
        self.body = 0x20 if (0x20 + self.data_size == len(d)) else 0x10
        self.records = []
        self.trailing = b""
        self._parse()

    def _parse(self):
        d = self.data
        p = self.body
        n = len(d)
        while p + 4 <= n:
            tag = struct.unpack_from("<H", d, p)[0]
            if tag not in TAGS:
                break
            ncham = d[p + 2]
            if not (1 <= ncham <= 64):
                break
            # taille du descripteur : 3 octets de tete + les octets de type,
            # le tout aligne de sorte que la taille totale soit multiple de 4
            # -> on determine desc en cherchant la valeur qui fait tomber
            #    l'enregistrement suivant sur un tag valide
            # La taille du descripteur se CALCULE, elle ne se devine pas :
            #   2 octets de tag + 1 octet de nb_champs + 2 bits de type par
            #   champ, le tout aligne sur 4 octets.
            # Le modele reproduit a l'identique les trois formes du fichier
            # d'origine (0315, 0455, 055501ffffff). Une version anterieure
            # essayait les tailles 4, 8, 12... dans l'ordre et retenait la
            # premiere dont la suite ressemblait a un tag valide : sur des
            # enregistrements de 14 champs elle choisissait 4 au lieu de 8 et
            # decrochait au 19e enregistrement.
            n_type = -(-2 * ncham // 8)
            calcule = -(-(2 + 1 + n_type) // 4) * 4
            desc_size = None
            for cand in (calcule, 4, 8, 12, 16, 20):
                total = cand + 4 * ncham
                q = p + total
                if q == n:
                    desc_size = cand
                    break
                if q + 4 <= n:
                    t2 = struct.unpack_from("<H", d, q)[0]
                    if t2 in TAGS and 1 <= d[q + 2] <= 64:
                        desc_size = cand
                        break
            if desc_size is None:
                break
            total = desc_size + 4 * ncham
            fields = list(struct.unpack_from(f"<{ncham}I", d, p + desc_size))
            self.records.append(
                Record(p, tag, bytes(d[p + 2:p + desc_size]), fields, total)
            )
            p += total
        self.trailing = bytes(d[p:])

    def set_field(self, rec_index, field_index, value):
        """Reecrit un champ dans le tampon binaire (pour le patch)."""
        r = self.records[rec_index]
        off = r.offset + (r.size - 4 * len(r.fields)) + 4 * field_index
        struct.pack_into("<I", self.data, off, value & 0xFFFFFFFF)
        r.fields[field_index] = value

    def resume(self, name=""):
        shapes = collections.Counter(
            (r.tag, len(r.fields), r.desc.hex()) for r in self.records
        )
        print(f"--- {name or ''}  ({len(self.data):,} o) ---")
        print(f"    en-tete: nb={self.nb} taille_donnees={self.data_size} "
              f"[8]=0x{self.c8:X} [C]=0x{self.cC:X} corps@0x{self.body:X}")
        print(f"    {len(self.records)} enregistrements parses, "
              f"reste {len(self.trailing)} octets non parses")
        for (tag, ncham, desc), cnt in shapes.most_common(10):
            print(f"      tag=0x{tag:02X} nb_champs={ncham:2d} desc={desc:<14s} x{cnt}")
        return shapes


if __name__ == "__main__":
    for path in sys.argv[1:]:
        t = PrmTable(path)
        t.resume(path)
        for r in t.records[:3]:
            print(f"       {r.fields}")
