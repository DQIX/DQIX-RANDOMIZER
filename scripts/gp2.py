#!/usr/bin/env python3
"""Lecteur du conteneur GPC2 (`.gp2`) de Dragon Quest IX.

Format reconstitue d'apres le source C++ de DQIX/ArchiveTool (`ArchiveTool/gp2.cpp`),
cloné dans tools/community/. Aucune specification ecrite publique n'existe.

EN-TETE (0x14 octets) :
    u32  magic = 0x32435047  ("GPC2" en ASCII)
    u16  packedFileCount     bits 0-11 = nombre de fichiers
                             bits 12-15 = log2 du nombre d'indices de l'arbre
    u16  headerLength        en mots de 4 octets
    u16  fileInfoLength      en mots de 4 octets
    u16  firstFileOffs       en mots de 4 octets
    u16  decompressedFileInfoLength
    u16  decompressedFilenameLength
    u32  totalFileSize       en mots de 4 octets ; le bit 0x10000000 indique
                             que les fichiers internes ne sont pas compresses

INDEX : nb entrees de 12 octets { u32 hash, u32 offset, u32 taille }.
    L'offset est en MOTS DE 4 OCTETS, sur ses 24 bits de poids faible ; les
    4 bits de poids fort servent a l'arbre binaire de recherche par hash.
    Position reelle du fichier = firstFileOffs*4 + (offset & 0xFFFFFF)*4

Verification sur mon_data.gp2 :
    firstFileOffs*4 + totalFileSize*4 == taille du fichier, a l'octet pres.

BLOCS COMPRESSIBLES. Chaque bloc (index, table de noms, et chaque fichier) est
prefixe par un u32 de controle :
    type  = controle & 7        0 = brut, 1 = A, 2 et 3 = B, 4 = C
    taille = controle >> 3      taille decompressee
Les algorithmes A, B et C sont des LZ maison. Seul le type 0 est implemente ici :
c'est deja celui de l'index et de la table de noms, ce qui suffit a lister le
contenu de l'archive.

Usage:
    python scripts/gp2.py <fichier.gp2> [...]
"""
import os
import struct
import sys

MAGIC = 0x32435047


from lz_dq9 import ErreurLZ, decompresse_bloc


class BlocCompresse(NotImplementedError):
    pass


def lire_bloc(d, pos, fin=None):
    """Lit un bloc precede de son u32 de controle. Rend (donnees, type, taille).

    Les types 0 (brut) et 1 (LZSS, voir lz_dq9.py) sont geres. Les types 2, 3 et 4
    restent a porter depuis CompressB.cpp et CompressC.cpp.
    """
    try:
        return decompresse_bloc(d, pos, fin)
    except ErreurLZ as e:
        raise BlocCompresse(str(e))


class GP2:
    def __init__(self, chemin):
        with open(chemin, "rb") as f:
            self.d = f.read()
        self.chemin = chemin
        d = self.d
        (magic, packed, self.header_len, self.fileinfo_len, self.first_file,
         self.dec_fileinfo_len, self.dec_nom_len, self.total) = \
            struct.unpack_from("<IHHHHHHI", d, 0)
        if magic != MAGIC:
            raise ValueError(f"{chemin} : magie 0x{magic:08X}, attendu 0x{MAGIC:08X}")
        self.nb = packed & 0xFFF
        self.bits_arbre = (packed & 0xF000) >> 12
        self.compresse = (self.total & 0x10000000) == 0
        self.taille_attendue = self.first_file * 4 + (self.total & 0x0FFFFFFF) * 4

        # index : tableau de nb x (u32 hash, u32 offset, u32 taille)
        #
        # LE CHAMP TAILLE PORTE DES DRAPEAUX. Comme l'offset, il n'utilise que
        # ses 24 bits de poids faible ; l'octet de poids fort sert a l'arbre de
        # recherche par hash. Sans le masque, `enemy.gp2` annonce des membres de
        # 419 Mo. Verification sur ses 601 entrees triees par offset :
        # `pos[i+1] - pos[i] == (taille[i] & 0xFFFFFF) + 4` exactement, et la
        # derniere entree tombe a 4 octets de la fin du fichier.
        brut, typ, _ = lire_bloc(d, self.header_len * 4, self.fileinfo_len * 4)
        self.entrees = [(h, o, t & 0xFFFFFF) for h, o, t in
                        (struct.unpack_from("<III", brut, i * 12)
                         for i in range(self.nb))]
        self.type_index = typ

        # Table de noms : chaines terminees par zero, dans l'ordre des hash.
        # Elle est en pratique compressee (type 1 = DecompressA, non porte), alors
        # que l'index l'est rarement. On continue sans les noms dans ce cas :
        # l'index seul (hash, offset, taille) reste exploitable.
        self.noms = []
        self.type_noms = None
        try:
            brut, self.type_noms, _ = lire_bloc(d, self.fileinfo_len * 4,
                                                 self.first_file * 4)
            self.noms = [n.decode("shift_jis", "replace")
                         for n in brut.split(b"\x00") if n]
        except BlocCompresse:
            self.type_noms = "compresse, non lisible"

    def resume(self):
        print("=" * 74)
        print(f"{self.chemin}  ({len(self.d):,} o)")
        print(f"  {self.nb} fichier(s) internes, arbre sur {1 << self.bits_arbre} indices")
        print(f"  headerLength={self.header_len * 4} fileInfoLength={self.fileinfo_len * 4} "
              f"firstFileOffs={self.first_file * 4}")
        print(f"  taille annoncee = {self.taille_attendue:,} o  "
              f"-> {'CONCORDE' if self.taille_attendue == len(self.d) else 'ECART'}")
        print(f"  fichiers internes compresses : {'oui' if self.compresse else 'non'}")
        print(f"  index et noms stockes en type {self.type_index} / {self.type_noms} "
              f"(0 = brut)")
        print(f"  {'nom':<28s} {'hash':>10s} {'offset':>10s} {'taille':>10s}  type")
        # les noms suivent l'ordre des entrees triees par offset masque
        for i, (h, offs, taille) in enumerate(
                sorted(self.entrees, key=lambda e: e[1] & 0xFFFFFF)):
            nom = self.noms[i] if i < len(self.noms) else "?"
            pos = self.first_file * 4 + (offs & 0xFFFFFF) * 4
            typ = "?"
            if pos + 4 <= len(self.d):
                typ = str(struct.unpack_from("<I", self.d, pos)[0] & 7)
            print(f"  {nom:<28s} 0x{h:08X} {offs:10d} {taille:10d}  {typ}")


if __name__ == "__main__":
    for chemin in sys.argv[1:]:
        try:
            GP2(chemin).resume()
        except BlocCompresse as e:
            print(f"{chemin} : {e}")
        except Exception as e:
            print(f"{chemin} : ECHEC {type(e).__name__} {e}")


def extraire_type0(chemin, dest="work/extracted/gp2"):
    """Extrait les fichiers internes stockes SANS compression (type 0).

    Les autres exigent le portage de DecompressA/B/C depuis ArchiveTool.
    """
    g = GP2(chemin)
    os.makedirs(dest, exist_ok=True)
    base = os.path.splitext(os.path.basename(chemin))[0]
    sortis = []
    for i, (h, offs, taille) in enumerate(sorted(g.entrees, key=lambda e: e[0])):
        pos = g.first_file * 4 + (offs & 0xFFFFFF) * 4
        if pos + 4 > len(g.d):
            continue
        controle = struct.unpack_from("<I", g.d, pos)[0]
        typ, taille_dec = controle & 7, controle >> 3
        if typ != 0:
            continue
        data = g.d[pos + 4: pos + 4 + taille_dec]
        out = os.path.join(dest, f"{base}_{i}_{h:08X}.bin")
        with open(out, "wb") as f:
            f.write(data)
        sortis.append((out, taille_dec, len(data)))
    return sortis


def extraire(chemin, dest="work/extracted/gp2"):
    """Extrait tous les fichiers internes d'une archive GPC2.

    Rend la liste (nom, donnees, type). Les entrees dont l'algorithme n'est pas
    porte sont signalees avec des donnees a None.
    """
    g = GP2(chemin)
    os.makedirs(dest, exist_ok=True)
    # PIEGE : ArchiveTool trie les entrees par OFFSET masque (fileEntrySorter),
    # puis apparie les noms dans l'ordre de la table de noms. Trier par hash
    # donne un appariement nom/contenu faux.
    entrees = sorted(g.entrees, key=lambda e: e[1] & 0xFFFFFF)
    resultats = []
    for i, (h, offs, taille) in enumerate(entrees):
        nom = g.noms[i] if i < len(g.noms) else f"{h:08X}.bin"
        pos = g.first_file * 4 + (offs & 0xFFFFFF) * 4
        try:
            data, typ, attendu = lire_bloc(g.d, pos, pos + taille + 4)
            if len(data) != attendu:
                nom_out = None
                resultats.append((nom, None, f"type {typ}, {len(data)}/{attendu} o"))
                continue
            with open(os.path.join(dest, nom), "wb") as f:
                f.write(data)
            resultats.append((nom, data, typ))
        except BlocCompresse as e:
            resultats.append((nom, None, str(e)))
    return resultats
