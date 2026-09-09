#!/usr/bin/env python3
"""Parse et affiche l'en-tete d'une ROM Nintendo DS.

Reference du format : GBATEK (section "DS Cartridge Header").
Usage: python scripts/nds_header.py <rom.nds>
"""
import struct
import sys
import zlib
import hashlib


def u8(b, o):
    return b[o]


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def main(path):
    with open(path, "rb") as f:
        h = f.read(0x4000)

    print("=" * 72)
    print("EN-TETE ROM NDS :", path)
    print("=" * 72)

    title = h[0x00:0x0C].split(b"\x00")[0].decode("ascii", "replace")
    gamecode = h[0x0C:0x10].decode("ascii", "replace")
    makercode = h[0x10:0x12].decode("ascii", "replace")

    print(f"  Titre interne      : {title!r}")
    print(f"  Game code          : {gamecode}")
    print(f"  Maker code         : {makercode}  (01 = Nintendo, 5D/EB = Square Enix)")
    print(f"  Unit code          : 0x{u8(h, 0x12):02X}  (00=NDS, 02=NDS+DSi, 03=DSi only)")
    print(f"  Device capacity    : 0x{u8(h, 0x14):02X}  -> {(128 << u8(h, 0x14)) // 1024} Mo")
    print(f"  Version ROM        : 0x{u8(h, 0x1E):02X}")

    print("-" * 72)
    print("  BINAIRES EXECUTABLES")
    fields = [
        ("ARM9 offset ROM", 0x20), ("ARM9 entry point", 0x24),
        ("ARM9 adresse RAM", 0x28), ("ARM9 taille", 0x2C),
        ("ARM7 offset ROM", 0x30), ("ARM7 entry point", 0x34),
        ("ARM7 adresse RAM", 0x38), ("ARM7 taille", 0x3C),
    ]
    for name, off in fields:
        v = u32(h, off)
        print(f"  {name:20s} : 0x{v:08X}  ({v:,})")

    print("-" * 72)
    print("  SYSTEME DE FICHIERS (NitroFS)")
    for name, off in [
        ("FNT offset", 0x40), ("FNT taille", 0x44),
        ("FAT offset", 0x48), ("FAT taille", 0x4C),
    ]:
        v = u32(h, off)
        print(f"  {name:20s} : 0x{v:08X}  ({v:,})")
    nb_files = u32(h, 0x4C) // 8
    print(f"  => Nombre de fichiers dans la FAT : {nb_files:,}")

    print("-" * 72)
    print("  OVERLAYS  (code charge dynamiquement - souvent la ou sont les donnees)")
    for name, off in [
        ("ARM9 ovl offset", 0x50), ("ARM9 ovl taille", 0x54),
        ("ARM7 ovl offset", 0x58), ("ARM7 ovl taille", 0x5C),
    ]:
        v = u32(h, off)
        print(f"  {name:20s} : 0x{v:08X}  ({v:,})")
    print(f"  => Nombre d'overlays ARM9 : {u32(h, 0x54) // 32}")
    print(f"  => Nombre d'overlays ARM7 : {u32(h, 0x5C) // 32}")

    print("-" * 72)
    print("  DIVERS")
    print(f"  Icone/titre offset : 0x{u32(h, 0x68):08X}")
    print(f"  Taille ROM utilisee: 0x{u32(h, 0x80):08X}  ({u32(h, 0x80):,} octets)")
    print(f"  Taille en-tete     : 0x{u32(h, 0x84):08X}")
    print(f"  CRC16 en-tete      : 0x{u16(h, 0x15E):04X}")

    print("-" * 72)
    print("  EMPREINTES DU FICHIER COMPLET (identification de la release)")
    crc = 0
    md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    total = 0
    with open(path, "rb") as f:
        while chunk := f.read(1 << 22):
            crc = zlib.crc32(chunk, crc)
            md5.update(chunk)
            sha1.update(chunk)
            total += len(chunk)
    print(f"  Taille fichier     : {total:,} octets ({total / (1 << 20):.0f} Mo)")
    print(f"  CRC32              : {crc:08X}")
    print(f"  MD5                : {md5.hexdigest()}")
    print(f"  SHA1               : {sha1.hexdigest()}")
    print("=" * 72)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "rom.nds")
