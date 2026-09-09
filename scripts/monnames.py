#!/usr/bin/env python3
"""Noms des monstres de Dragon Quest IX, dans les 5 langues de la version Europe.

OU SONT LES NOMS. Dans `data/prm/mon_data.gp2`, une archive GPC2 contenant
5 fichiers internes `mon_data_<lg>.nat` (de, en, es, fr, it). Le code du jeu
reference ce gabarit avec un marqueur de langue `<LG>`.

FORMAT de `mon_data_<lg>.nat` — CONFIRME :

    +0x00   u16   nb sur les 12 bits de poids faible : `u16 & 0xFFF` = 438,
                  le meme nombre que mon_btldata.nat. Les 4 bits de poids fort
                  sont des drapeaux qui varient selon la langue (0x0, 0x1, 0x3,
                  0xC) -- meme convention que le packedFileCount de l'en-tete
                  GPC2. Lire le u16 brut donne 49590 en allemand et fait tout
                  deborder.
    +0x02   u16   ?
    +0x04         438 enregistrements de 28 octets :
                    +0x00  u32  offset du nom, dans le pool
                    +0x04  u32  offset du code de modele
                    +0x14  u32  offset du nom au pluriel
                    (les 12 autres octets restent a elucider)
            puis un bourrage de zeros
            puis le pool : chaines terminees par zero

    Verification : pour l'anglais, la zone d'enregistrements va de 0x04 a 0x2FEC,
    soit 12 264 octets = 438 x 28 exactement. Et les 438 offsets de nom pointent
    tous sur un debut de chaine reel, dans les 5 langues.

C'est donc une correspondance DIRECTE index -> nom, valable pour les 438
enregistrements, et non une heuristique de regroupement.

    index 0   -> slime               HP 8   DEF 7
    index 2   -> metal slime         HP 4   DEF 256  XP 4096
    index 26  -> liquid metal slime  HP 8   DEF 256  XP 40200

DEUX PIEGES rencontres en route, tous deux silencieux :

  1. Le pool est precede d'un bourrage de zeros. Un balayage arriere qui accepte
     les octets nuls s'arrete 6 octets trop tot, et tous les offsets se retrouvent
     decales. Il faut sauter les zeros de tete.
  2. Dans l'archive GPC2, les noms de fichiers correspondent aux entrees de
     l'index triees par OFFSET masque, et non par hash. Verifie par le contenu :
     dans l'ordre des offsets les langues sortent bien de, en, es, fr, it.

Usage:
    python scripts/monnames.py <rom.nds> [langue] [nb]
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gp2 import GP2, lire_bloc
from nitrofs import NitroFS

ARCHIVE = "/data/prm/mon_data.gp2"
LANGUES = ("de", "en", "es", "fr", "it")
STRIDE = 28
OFF_NOM, OFF_MODELE, OFF_PLURIEL = 0x00, 0x04, 0x14

# Balisage des diacritiques employe par les textes du jeu.
DIACRITIQUES = {
    "<'a>": "á", "<'e>": "é", "<'i>": "í", "<'o>": "ó", "<'u>": "ú",
    "<'E>": "É",
    "<`a>": "à", "<`e>": "è", "<`u>": "ù",
    "<^e>": "ê", "<^i>": "î", "<^u>": "û",
    "<:a>": "ä", "<:i>": "ï", "<:o>": "ö", "<:u>": "ü",
    "<~n>": "ñ", "<ss>": "ß",
    "<1>": "'",   # apostrophe : "bag o<1> laughs" -> "bag o' laughs"
}
# Balises de flexion grammaticale, surtout en allemand et en francais :
# [gs] genitif singulier, [adjf] adjectif feminin, [sgl_inf_1] variante...
# Le moteur les resout a l'affichage ; ici ce sont des parasites.
BALISE_GRAMMAIRE = re.compile(r"\[[^\]]{1,16}\]")


def decode_texte(s):
    for balise, car in DIACRITIQUES.items():
        s = s.replace(balise, car)
    return BALISE_GRAMMAIRE.sub("", s).strip()


def _base_pool(d, nb):
    """Debut du pool de chaines, DEDUIT de la structure et non devine.

    La zone d'enregistrements fait exactement `nb * STRIDE` octets et commence a
    l'offset 4, donc le pool commence a `4 + nb * STRIDE`, plus un eventuel
    bourrage de zeros.

    Un premier essai reperait le pool en remontant depuis la fin du fichier tant
    que les octets etaient imprimables ou nuls. C'etait fragile et silencieux :
    ca marchait en anglais et se decalait de quelques octets en allemand, ce qui
    invalidait tous les offsets. Le calcul ci-dessous n'a pas ce defaut.
    """
    p = 4 + nb * STRIDE
    while p < len(d) and d[p] == 0:
        p += 1
    return p


def _chaines(d, base):
    """Rend un dictionnaire offset_dans_le_pool -> chaine decodee."""
    out, o = {}, 0
    for c in d[base:].split(b"\x00"):
        if c:
            out[o] = c.decode("latin-1")
        o += len(c) + 1
    return out


def lire_table(data):
    """Rend la liste des 438 entrees { nom, pluriel, modele } d'un mon_data_<lg>.nat."""
    nb = struct.unpack_from("<H", data, 0)[0] & 0xFFF
    base = _base_pool(data, nb)
    ch = _chaines(data, base)
    entrees = []
    for i in range(nb):
        p = 4 + i * STRIDE
        o_nom, o_mod = struct.unpack_from("<II", data, p + OFF_NOM)
        o_pl = struct.unpack_from("<I", data, p + OFF_PLURIEL)[0]
        entrees.append({
            "nom": decode_texte(ch[o_nom]) if o_nom in ch else None,
            "pluriel": decode_texte(ch[o_pl]) if o_pl in ch else None,
            "modele": ch.get(o_mod),
        })
    return entrees


def charger(chemin_rom, langue="en"):
    """Rend la liste des 438 entrees, indexee comme mon_btldata.nat."""
    if langue not in LANGUES:
        raise ValueError(f"langue inconnue : {langue} (attendu {LANGUES})")
    fs = NitroFS(chemin_rom)
    fid = next(k for k, v in fs.paths.items() if v == ARCHIVE)
    racine = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "work")
    os.makedirs(racine, exist_ok=True)
    tmp = os.path.join(racine, "_mon_data.gp2")
    with open(tmp, "wb") as f:
        f.write(fs.read(fid))

    g = GP2(tmp)
    # les noms de la table correspondent aux entrees triees par offset masque
    for i, (h, offs, taille) in enumerate(
            sorted(g.entrees, key=lambda e: e[1] & 0xFFFFFF)):
        if i < len(g.noms) and g.noms[i].endswith(f"_{langue}.nat"):
            pos = g.first_file * 4 + (offs & 0xFFFFFF) * 4
            data, _, _ = lire_bloc(g.d, pos, pos + taille + 4)
            return lire_table(data)
    raise RuntimeError(f"aucun fichier interne pour la langue {langue}")


def noms_simples(chemin_rom, langue="en"):
    """Dictionnaire index -> nom, pour l'affichage."""
    return {i: e["nom"] for i, e in enumerate(charger(chemin_rom, langue))
            if e["nom"]}


if __name__ == "__main__":
    rom = sys.argv[1]
    lg = sys.argv[2] if len(sys.argv) > 2 else "en"
    nb = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    t = charger(rom, lg)
    nommes = sum(1 for e in t if e["nom"])
    print(f"{len(t)} entrees en langue {lg!r}, {nommes} avec un nom\n")
    print(f"{'idx':>4}  {'nom':<26s} {'pluriel':<26s} modele")
    print("-" * 76)
    for i, e in enumerate(t[:nb]):
        print(f"{i:4d}  {str(e['nom']):<26s} {str(e['pluriel']):<26s} {e['modele']}")
