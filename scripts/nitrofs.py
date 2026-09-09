#!/usr/bin/env python3
"""Lecture / extraction du systeme de fichiers NitroFS d'une ROM Nintendo DS.

Implementation en Python pur (aucune dependance) d'apres GBATEK.

Structure de la FNT (File Name Table) :
  - Table des repertoires, entrees de 8 octets :
      u32 offset de la sous-table de noms (relatif au debut de la FNT)
      u16 premier file ID contenu dans ce repertoire
      u16 ID du repertoire parent (pour le repertoire 0 : nombre total de repertoires)
  - Puis les sous-tables de noms, suite d'entrees :
      u8 type/longueur : 0x00 = fin de sous-table
                         0x01..0x7F = fichier, longueur du nom = valeur
                         0x81..0xFF = repertoire, longueur = valeur & 0x7F, suivi d'un u16 dir id
Structure de la FAT (File Allocation Table), entrees de 8 octets :
      u32 offset de debut dans la ROM, u32 offset de fin

Usage:
  python scripts/nitrofs.py <rom.nds> list                 # arbre complet
  python scripts/nitrofs.py <rom.nds> tree                 # repertoires + stats
  python scripts/nitrofs.py <rom.nds> extract <dest>       # tout extraire
  python scripts/nitrofs.py <rom.nds> grep <motif>         # chercher dans les noms
"""
import os
import struct
import sys


class NitroFS:
    def __init__(self, path):
        self.path = path
        with open(path, "rb") as f:
            hdr = f.read(0x4000)
            self.fnt_off = struct.unpack_from("<I", hdr, 0x40)[0]
            self.fnt_size = struct.unpack_from("<I", hdr, 0x44)[0]
            self.fat_off = struct.unpack_from("<I", hdr, 0x48)[0]
            self.fat_size = struct.unpack_from("<I", hdr, 0x4C)[0]
            f.seek(self.fnt_off)
            self.fnt = f.read(self.fnt_size)
            f.seek(self.fat_off)
            self.fat = f.read(self.fat_size)

        self.nb_files = self.fat_size // 8
        self.nb_dirs = struct.unpack_from("<H", self.fnt, 6)[0]
        # files[id] = (offset_debut, offset_fin)
        self.files = [
            struct.unpack_from("<II", self.fat, i * 8) for i in range(self.nb_files)
        ]
        self.paths = {}   # file id -> chemin complet
        self.dirs = {}    # dir id -> chemin complet
        self._walk(0, "")

    def _walk(self, dir_id, prefix):
        """Parcourt recursivement la sous-table de noms du repertoire dir_id."""
        self.dirs[dir_id] = prefix or "/"
        base = (dir_id & 0xFFF) * 8
        sub_off, first_id, _parent = struct.unpack_from("<IHH", self.fnt, base)
        p = sub_off
        fid = first_id
        while p < len(self.fnt):
            t = self.fnt[p]
            p += 1
            if t == 0:
                break
            length = t & 0x7F
            name = self.fnt[p:p + length].decode("shift_jis", "replace")
            p += length
            if t & 0x80:
                sub_dir_id = struct.unpack_from("<H", self.fnt, p)[0]
                p += 2
                self._walk(sub_dir_id, f"{prefix}/{name}")
            else:
                self.paths[fid] = f"{prefix}/{name}"
                fid += 1

    def size(self, fid):
        s, e = self.files[fid]
        return e - s

    def read(self, fid):
        s, e = self.files[fid]
        with open(self.path, "rb") as f:
            f.seek(s)
            return f.read(e - s)


def cmd_list(fs):
    for fid in sorted(fs.paths):
        s, e = fs.files[fid]
        print(f"{fid:5d}  0x{s:08X}  {e - s:10,d}  {fs.paths[fid]}")


def cmd_tree(fs):
    print(f"Repertoires : {fs.nb_dirs}   Fichiers : {fs.nb_files}")
    print("-" * 78)
    # statistiques par repertoire
    stats = {}
    for fid, path in fs.paths.items():
        d = os.path.dirname(path) or "/"
        n, total = stats.get(d, (0, 0))
        stats[d] = (n + 1, total + fs.size(fid))
    for d in sorted(stats):
        n, total = stats[d]
        print(f"{n:6d} fichiers  {total:12,d} o   {d}")
    print("-" * 78)
    # statistiques par extension
    ext_stats = {}
    for fid, path in fs.paths.items():
        ext = os.path.splitext(path)[1].lower() or "(sans extension)"
        n, total = ext_stats.get(ext, (0, 0))
        ext_stats[ext] = (n + 1, total + fs.size(fid))
    print("PAR EXTENSION :")
    for ext, (n, total) in sorted(ext_stats.items(), key=lambda kv: -kv[1][1]):
        print(f"{n:6d} fichiers  {total:12,d} o   {ext}")


def cmd_grep(fs, motif):
    m = motif.lower()
    for fid in sorted(fs.paths):
        if m in fs.paths[fid].lower():
            s, e = fs.files[fid]
            print(f"{fid:5d}  0x{s:08X}  {e - s:10,d}  {fs.paths[fid]}")


def cmd_extract(fs, dest):
    n = 0
    with open(fs.path, "rb") as rom:
        for fid, path in sorted(fs.paths.items()):
            out = os.path.join(dest, path.lstrip("/").replace("/", os.sep))
            os.makedirs(os.path.dirname(out), exist_ok=True)
            s, e = fs.files[fid]
            rom.seek(s)
            with open(out, "wb") as f:
                f.write(rom.read(e - s))
            n += 1
            if n % 500 == 0:
                print(f"  {n} fichiers...", flush=True)
    print(f"OK : {n} fichiers extraits dans {dest}")


if __name__ == "__main__":
    rom = sys.argv[1]
    cmd = sys.argv[2] if len(sys.argv) > 2 else "tree"
    fs = NitroFS(rom)
    if cmd == "list":
        cmd_list(fs)
    elif cmd == "tree":
        cmd_tree(fs)
    elif cmd == "grep":
        cmd_grep(fs, sys.argv[3])
    elif cmd == "extract":
        cmd_extract(fs, sys.argv[3])
    else:
        print(__doc__)
