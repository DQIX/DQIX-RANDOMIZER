#!/usr/bin/env python3
"""Le « bestiaire des objets » : ou chaque objet peut-il sortir, dans une ROM ?

Sorties EN ANGLAIS (demande du joueur, pour la communaute), dans `<prefixe>` :

  _items.txt / _items.csv      une entree par objet du catalogue (1178)
  _containers.txt / .csv       une ligne par conteneur (847), avec le nom de
                               la zone en jeu et l'offset dans la ROM
  _items.json                  les donnees de la page artifact

Les .txt sont des tableaux a colonnes alignees, lisibles tels quels.
« Obtainable » = sort d'un coffre bleu, d'un pot/tonneau/placard, d'un coffre
rouge ou d'un monstre rencontrable (liste blanche des 256). Grottos, quetes et
boutiques ne sont pas comptes.

Usage :
  python scripts/catalogue_objets.py <rom.nds> <prefixe>
"""
import csv
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ndspy.rom
import objets
import treasure as T
from monnames import charger as noms_monstres
from monstres_nommes import MONSTRES
from zones import noms_zones

CATEGORIE = {"w": "weapon", "s": "shield", "b": "torso", "u": "legs",
             "h": "head", "a": "arms", "l": "feet", "d": "accessory",
             "t": "item"}
CONTENEUR = {0: "red chest", 1: "pot", 2: "barrel", 3: "cupboard",
             4: "blue chest"}
LOOT = {0: "nothing", 1: "gold", 2: "item", 3: "ambush"}
# classe de taux de drop -> chance (table du code de combat, RESEARCH.md 81)
CHANCE = {0: "always", 1: "1/8", 2: "1/16", 3: "1/32", 4: "1/64", 5: "1/128",
          6: "1/256", 7: "never"}


def tableau(entetes, lignes, droite=()):
    """Texte a colonnes alignees."""
    larg = [max(len(str(x)) for x in col) for col in zip(entetes, *lignes)]

    def fmt(l):
        return "  ".join((str(v).rjust(w) if i in droite else str(v).ljust(w))
                         for i, (v, w) in enumerate(zip(l, larg))).rstrip()
    sep = "  ".join("-" * w for w in larg)
    return "\n".join([fmt(entetes), sep] + [fmt(l) for l in lignes]) + "\n"


def ecrire_csv(chemin, entetes, lignes):
    """CSV pour Excel en francais : separateur point-virgule, UTF-8 avec BOM
    (sinon Excel lit les accents de travers), une information par cellule.
    Les flottants sont ecrits avec une virgule decimale."""
    def cellule(v):
        if isinstance(v, float):
            return ("%.2f" % v).replace(".", ",")
        return "" if v is None else v
    with open(chemin, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";", lineterminator="\r\n")
        w.writerow(entetes)
        for l in lignes:
            w.writerow([cellule(v) for v in l])


def main(chemin, prefixe):
    rom = ndspy.rom.NintendoDSRom.fromFile(chemin)
    cat = objets.catalogue(rom)
    imp = objets.objets_importants(rom)
    nen = objets.noms(rom, "en")
    nfr = objets.noms(rom, "fr")
    etoiles = objets.raretes(rom)
    zen = noms_zones(rom, "en")
    mon_en = [objets.nettoyer(m["nom"] or "#%d" % k) for k, m in enumerate(noms_monstres(chemin, "en"))]
    mon_fr = [m["nom"] or "#%d" % k for k, m in enumerate(noms_monstres(chemin, "fr"))]

    src = {i: dict(red=[], blue=[], pots=[], drops=[], field=False) for i in cat}

    fid = rom.filenames.idOf("data/scenario/treasure.nsarc")
    arc = bytes(rom.files[fid])
    membres = T.membres_narc(arc)
    for table, cle in ((T.TABLE_COFFRES_BLEUS, "blue"), (T.TABLE_POTS, "pots")):
        for _off, o in T.outcomes(arc, membres[table][0]):
            if o["loot"] == T.TYPE_OBJET and o["id"] in src:
                src[o["id"]][cle].append(dict(rank=o["rang"], pct=o["pct"]))

    with open(chemin, "rb") as f:
        f.seek(0x48)
        fat_off = struct.unpack("<I", f.read(4))[0]
        f.seek(fat_off + 8 * fid)
        base_rom = struct.unpack("<I", f.read(4))[0]

    conteneurs = []
    conteneurs_csv = []
    for zone, (deb, _fin) in sorted(membres.items()):
        if zone in T.TABLES:
            continue
        code = zone[:-4]
        for ins in T.lire_script(arc, deb)[1]:
            if ins.op != 0x67:
                continue
            packed, flags = ins.valeurs[0], ins.valeurs[1]
            uid, val = packed >> 16, packed & 0xFFFF
            ct, lt = (flags >> 4) & 7, (flags >> 2) & 3
            posf = [None, None, None]
            if ct != 3:
                posf = []
                for t, v in zip(ins.types[2:5], ins.valeurs[2:5]):
                    if t == 2:
                        posf.append(struct.unpack("<f", struct.pack("<I", v))[0])
                    else:
                        posf.append(float(v if v < 0x80000000 else v - 0x100000000))
            pos = ["" if x is None else "%.2f" % x for x in posf]
            genre, obj, orr, rang = "", None, None, None
            if ct == 0 and lt == T.TYPE_OBJET:
                contenu = "%s (%d)" % (nen.get(val, "?"), val)
                genre, obj = "item", val
                if val in src:
                    src[val]["red"].append(dict(zone=zen.get(code, ""), code=code, uid=uid))
            elif ct == 0 and lt == T.TYPE_OR:
                contenu = "%d gold" % val
                genre, orr = "gold", val
            elif ct == 0:
                contenu = "empty"
                genre = "empty"
            else:
                contenu = "rank %d" % val
                genre, rang = "rank", val
            conteneurs.append([code, zen.get(code, ""), uid, CONTENEUR.get(ct, "?"),
                               contenu] + pos
                              + ["0x%05X" % ins.offsets[0],
                                 "0x%08X" % (base_rom + ins.offsets[0])])
            conteneurs_csv.append([code, zen.get(code, ""), uid, CONTENEUR.get(ct, "?"),
                                   genre, obj, nen.get(obj, "") if obj else "",
                                   nfr.get(obj, "") if obj else "", orr, rang]
                                  + posf
                                  + ["0x%05X" % ins.offsets[0],
                                     "0x%08X" % (base_rom + ins.offsets[0])])

    mon = bytes(rom.files[rom.filenames.idOf("data/prm/mon_btldata.nat")])
    for k in range(struct.unpack_from("<I", mon, 0)[0]):
        for off, genre, oc in ((4, "common", 2), (6, "rare", 3)):
            v = struct.unpack_from("<H", mon, 4 + k * 132 + off)[0]
            classe = mon[4 + k * 132 + oc]
            if v in src:
                atteignable = k in MONSTRES and classe != 7
                src[v]["drops"].append(dict(en=mon_en[k], fr=mon_fr[k], kind=genre,
                                            field=atteignable,
                                            chance=CHANCE.get(classe, "?")))
                if atteignable:
                    src[v]["field"] = True

    def obtenable(i):
        s = src[i]
        return bool(s["red"] or s["blue"] or s["pots"] or s["field"])

    # ---------------- items ----------------
    lignes_csv, lignes_txt, donnees = [], [], []
    for i in sorted(cat):
        s = src[i]
        rouges = "; ".join("%s [%s #%d]" % (r["zone"], r["code"], r["uid"]) for r in s["red"])
        bleus = "; ".join("rank %d %d%%" % (r["rank"], r["pct"]) for r in s["blue"])
        pots = "; ".join("rank %d %d%%" % (r["rank"], r["pct"]) for r in s["pots"])
        drops = "; ".join("%s (%s %s%s)" % (d["en"], d["kind"], d["chance"], "" if d["field"] else ", never obtainable")
                          for d in s["drops"])
        ok = obtenable(i)
        lignes_csv.append([i, CATEGORIE[cat[i][0]], nen[i], nfr[i],
                           "yes" if i in imp else "", rouges, bleus, pots, drops,
                           "yes" if ok else ""])
        lignes_txt.append([i, CATEGORIE[cat[i][0]], nen[i], nfr[i], etoiles[i],
                           "yes" if i in imp else "", len(s["red"]), len(s["blue"]),
                           len(s["pots"]), sum(1 for d in s["drops"] if d["field"]),
                           "yes" if ok else "NO"])
        donnees.append(dict(id=i, cat=CATEGORIE[cat[i][0]], en=nen[i], fr=nfr[i],
                            stars=etoiles[i],
                            imp=i in imp, ok=ok, red=s["red"], blue=s["blue"],
                            pots=s["pots"], drops=s["drops"]))

    ecrire_csv(prefixe + "_items.csv",
               ["id", "category", "name_en", "name_fr", "rarity_stars", "important",
                "obtainable", "red_chests", "blue_chest_entries",
                "pot_barrel_cupboard_entries", "field_monster_drops"],
               [l[:5] + [l[5], l[10]] + l[6:10] for l in lignes_txt])
    sources = []
    for d in donnees:
        base = [d["id"], d["en"], d["fr"]]
        for r in d["red"]:
            sources.append(base + ["red chest", r["code"], r["zone"], r["uid"],
                                   None, None, "", "", "", "", ""])
        for r in d["blue"]:
            sources.append(base + ["blue chest", "", "", None, r["rank"], r["pct"],
                                   "", "", "", "", ""])
        for r in d["pots"]:
            sources.append(base + ["pot/barrel/cupboard", "", "", None, r["rank"],
                                   r["pct"], "", "", "", "", ""])
        for m in d["drops"]:
            sources.append(base + ["monster drop", "", "", None, None, None,
                                   m["en"], m["fr"], m["kind"], m["chance"],
                                   "yes" if m["field"] else "no"])
    ecrire_csv(prefixe + "_item_sources.csv",
               ["item_id", "item_en", "item_fr", "source", "zone_code", "zone",
                "chest_uid", "rank", "chance_pct", "monster_en", "monster_fr",
                "drop_kind", "drop_chance", "obtainable_drop"], sources)
    n_ok = sum(1 for i in cat if i not in imp and obtenable(i))
    with open(prefixe + "_items.txt", "w", encoding="utf-8") as f:
        f.write("Dragon Quest IX (EU) - item catalogue - %s\n" % os.path.basename(chemin))
        f.write("%d items, %d important (never randomized), %d of the other %d "
                "obtainable from chests, pots or field monsters\n\n"
                % (len(cat), len(imp), n_ok, len(cat) - len(imp)))
        f.write("Columns: red / blue / pots = number of red chests, blue chest "
                "table entries, pot-barrel-cupboard table entries; drops = field "
                "monsters that drop it.\n\n")
        f.write(tableau(["id", "category", "name (EN)", "name (FR)", "stars",
                         "important", "red", "blue", "pots", "drops", "obtainable"],
                        lignes_txt, droite=(0, 4, 6, 7, 8, 9)))
        f.write("\nDETAIL\n\n")
        for d in donnees:
            if not (d["red"] or d["blue"] or d["pots"] or d["drops"]):
                continue
            f.write("%5d  %s\n" % (d["id"], d["en"]))
            for r in d["red"]:
                f.write("         red chest   %-32s %-8s #%d\n" % (r["zone"], r["code"], r["uid"]))
            for r in d["blue"]:
                f.write("         blue chest  rank %-2d  %3d %%\n" % (r["rank"], r["pct"]))
            for r in d["pots"]:
                f.write("         pot/barrel  rank %-2d  %3d %%\n" % (r["rank"], r["pct"]))
            for m in d["drops"]:
                f.write("         drop        %-26s %-6s %-6s%s\n" % (
                    m["en"], m["kind"], m["chance"],
                    "" if m["field"] else "  (never obtainable)"))
    with open(prefixe + "_items.json", "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, separators=(",", ":"))

    # ---------------- containers ----------------
    ent = ["code", "zone", "uid", "type", "content", "x", "y", "z",
           "offset_in_nsarc", "offset_in_rom"]
    ecrire_csv(prefixe + "_containers.csv",
               ["zone_code", "zone", "uid", "container", "content", "item_id",
                "item_en", "item_fr", "gold", "rank", "x", "y", "z",
                "offset_in_nsarc", "offset_in_rom"], conteneurs_csv)
    with open(prefixe + "_containers.txt", "w", encoding="utf-8") as f:
        f.write("Dragon Quest IX (EU, YDQP) - every container in the game - %s\n"
                % os.path.basename(chemin))
        f.write("Source: data/scenario/treasure.nsarc, opcode 0x67 of each zone "
                "script. Red chests hold a fixed item; pots, barrels, cupboards "
                "and blue chests hold a RANK, rolled against randTTT.bin / "
                "randTBox.bin each time the zone loads.\n")
        f.write("offset_in_rom points at the u32 'packed' field: "
                "(uniqueID << 16) | itemID-or-rank. Position in game units.\n\n")
        f.write(tableau(ent, conteneurs, droite=(2, 5, 6, 7)))

    print("%s : %d items, %d obtainable out of %d non-important, %d containers"
          % (chemin, len(cat), n_ok, len(cat) - len(imp), len(conteneurs)))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
