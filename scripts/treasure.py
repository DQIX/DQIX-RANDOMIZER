#!/usr/bin/env python3
"""Lecture et reecriture de data/scenario/treasure.nsarc (le loot du jeu).

L'archive porte 268 membres :
  - 265 scripts de zone `<zone>.bin` : ils declarent les conteneurs de la zone
    (coffre rouge, pot, tonneau, placard, coffre bleu) avec l'opcode 0x67 ;
  - `randTBox.bin` : la table de tirage des COFFRES BLEUS, rangs 1 a 5 ;
  - `randTTT.bin`  : celle des POTS, TONNEAUX et PLACARDS, rangs 1 a 20 ;
  - `randTD.bin`   : celle des GROTTOS, rangs 1 a 10. HORS PERIMETRE.

Format des membres : le script Nitro generique de la classe `Script` du decomp.

  en-tete, 16 octets   i32 nb d'instructions
                       u32 offset de la section de donnees
                       i32 longueur de la section de donnees
                       u32 nb de chaines
  instruction          u16 opcode
                       u8  nb de parametres
                       2 bits de type par parametre (0 chaine, 1 entier,
                         2 flottant), puis bourrage 0xff jusqu'au mot suivant
                       puis 4 octets par parametre

Opcodes rencontres ici :
  0x64 / 0x65   horodatage de construction, souches vides dans le jeu
  0x66          LootManager_Unknown_66(entier)
  0x67          LootManager_CreateContainer
  0x69          LootDistribution_DeclareOutcome, un u32 empaquete
  0x6a          LootDistribution_AllocateOutcomes(capacite)
  0xffff        fin

Empaquetage de l'outcome (opcode 0x69), u32 :
  bits 0-6    pourcentage
  bits 7-22   itemID, ou montant d'or, ou type d'embuscade
  bits 23-25  lootType : 0 rien, 1 or, 2 objet, 3 embuscade
  bits 26-30  rang

Empaquetage du conteneur (opcode 0x67) :
  param 0   packedID : uniqueID sur les 16 bits de poids fort,
                       itemIDOrRank sur les 16 bits de poids faible
  param 1   flags    : bits 0-1 inconnu, bits 2-3 lootType, bits 4-6 containerType
  suite     la position : 4 valeurs pour les types 0 et 4, 1 pour le type 3,
            3 sinon

Toute reecriture se fait EN PLACE, sur un u32 deja present : aucune taille de
fichier ne change, donc les savestates restent valides.
"""
import struct

TYPE_RIEN, TYPE_OR, TYPE_OBJET, TYPE_EMBUSCADE = 0, 1, 2, 3
NOM_LOOT = {0: "rien", 1: "or", 2: "objet", 3: "embuscade"}
NOM_CONTENEUR = {0: "coffre rouge", 1: "pot", 2: "tonneau",
                 3: "placard", 4: "coffre bleu"}

# Les trois tables de tirage. randTD est celle des grottos : hors perimetre.
TABLE_COFFRES_BLEUS = "randTBox.bin"
TABLE_POTS = "randTTT.bin"
TABLE_GROTTOS = "randTD.bin"
TABLES = (TABLE_COFFRES_BLEUS, TABLE_POTS, TABLE_GROTTOS)


# --------------------------------------------------------------------------
# archive NARC
# --------------------------------------------------------------------------
def membres_narc(d):
    """Rend {nom: (debut, fin)} des membres d'une archive NARC Nitro."""
    if d[:4] != b"NARC":
        raise ValueError("pas une archive NARC")
    n_blocs = struct.unpack_from("<H", d, 14)[0]
    pos = struct.unpack_from("<H", d, 12)[0]
    fat = noms = img = None
    for _ in range(n_blocs):
        magie = d[pos:pos + 4]
        taille = struct.unpack_from("<I", d, pos + 4)[0]
        if magie == b"BTAF":
            nb = struct.unpack_from("<H", d, pos + 8)[0]
            fat = [struct.unpack_from("<II", d, pos + 12 + i * 8)
                   for i in range(nb)]
        elif magie == b"BTNF":
            noms = (pos + 8, d[pos:pos + taille])
        elif magie == b"GMIF":
            img = pos + 8
        pos += taille
    if fat is None or img is None:
        raise ValueError("archive NARC incomplete")
    out = {}
    if noms:
        bloc = noms[1]
        deb = struct.unpack_from("<I", bloc, 8)[0]
        p, i = 8 + deb, 0
        while p < len(bloc) and i < len(fat):
            lg = bloc[p]
            if lg == 0:
                break
            nom = bloc[p + 1:p + 1 + lg].decode("ascii", "replace")
            out[nom] = (img + fat[i][0], img + fat[i][1])
            p += 1 + lg
            i += 1
    if not out:
        out = {str(i): (img + a, img + b) for i, (a, b) in enumerate(fat)}
    return out


# --------------------------------------------------------------------------
# script Nitro
# --------------------------------------------------------------------------
class Instruction(object):
    __slots__ = ("op", "types", "offsets", "valeurs", "debut")

    def __init__(self, op, types, offsets, valeurs, debut):
        self.op = op            # entier
        self.types = types      # 0 chaine, 1 entier, 2 flottant
        self.offsets = offsets  # offset ABSOLU du u32 de chaque parametre
        self.valeurs = valeurs  # les u32 bruts
        self.debut = debut


def lire_script(d, base=0):
    """Decoupe un script en instructions. `base` = offset du script dans `d`."""
    nb, off_donnees, lg_donnees, nb_chaines = struct.unpack_from("<iIiI", d, base)
    instrs = []
    pos = base + 16
    fin = base + off_donnees
    while pos + 4 <= fin:
        op = struct.unpack_from("<H", d, pos)[0]
        if op == 0xFFFF:
            break
        n = d[pos + 2]
        oct_types = (2 * n + 7) // 8
        types = [(d[pos + 3 + i // 4] >> (2 * (i % 4))) & 3 for i in range(n)]
        p = pos + 3 + oct_types
        p = (p + 3) & ~3
        offsets = [p + 4 * i for i in range(n)]
        valeurs = [struct.unpack_from("<I", d, o)[0] for o in offsets]
        instrs.append(Instruction(op, types, offsets, valeurs, pos))
        pos = p + 4 * n
    return (dict(nb=nb, off_donnees=off_donnees, lg_donnees=lg_donnees,
                 nb_chaines=nb_chaines), instrs)


def ecrire_u32(buf, offset, valeur):
    """Reecrit un parametre en place dans un bytearray."""
    struct.pack_into("<I", buf, offset, valeur & 0xFFFFFFFF)


# --------------------------------------------------------------------------
# outcomes (opcode 0x69)
# --------------------------------------------------------------------------
def decoder_outcome(v):
    return dict(pct=v & 0x7F, id=(v >> 7) & 0xFFFF,
                loot=(v >> 23) & 7, rang=(v >> 26) & 0x1F)


def encoder_outcome(pct, ident, loot, rang):
    assert 0 <= pct <= 0x7F and 0 <= ident <= 0xFFFF
    assert 0 <= loot <= 7 and 0 <= rang <= 0x1F
    return pct | (ident << 7) | (loot << 23) | (rang << 26)


def outcomes(d, base=0):
    """Rend [(offset du u32, champs decodes)] pour une table de tirage."""
    instrs = lire_script(d, base)[1]
    return [(i.offsets[0], decoder_outcome(i.valeurs[0]))
            for i in instrs if i.op == 0x69]


# --------------------------------------------------------------------------
# conteneurs (opcode 0x67)
# --------------------------------------------------------------------------
def conteneurs(d, base=0):
    """Rend la liste des conteneurs declares par un script de zone.

    Chaque entree porte l'offset du u32 de packedID, pour pouvoir reecrire
    l'objet en place.
    """
    instrs = lire_script(d, base)[1]
    out = []
    for i in instrs:
        if i.op != 0x67 or len(i.valeurs) < 2:
            continue
        packed, flags = i.valeurs[0], i.valeurs[1]
        out.append(dict(off_packed=i.offsets[0], off_flags=i.offsets[1],
                        unique=packed >> 16, item=packed & 0xFFFF,
                        conteneur=(flags >> 4) & 7, loot=(flags >> 2) & 3,
                        flags=flags, nb_params=len(i.valeurs)))
    return out


def encoder_packed(unique, item):
    return ((unique & 0xFFFF) << 16) | (item & 0xFFFF)


def encoder_flags(flags, loot=None, conteneur=None):
    if loot is not None:
        flags = (flags & ~0x0C) | ((loot & 3) << 2)
    if conteneur is not None:
        flags = (flags & ~0x70) | ((conteneur & 7) << 4)
    return flags


# --------------------------------------------------------------------------
# reconstruction : quand une table de tirage change de taille
# --------------------------------------------------------------------------
def _aligner16(b):
    return b + b"\xff" * (-len(b) % 16)


def reconstruire_table(d, base, fin, nouveaux):
    """Rend un membre `randT*.bin` neuf dont les outcomes sont `nouveaux`.

    `nouveaux` : liste de dict(pct, id, loot, rang). On garde tel quel tout ce
    qui precede l'opcode 0x6a (les horodatages 0x64 / 0x65) et la section de
    donnees (leurs chaines) ; on reecrit la capacite 0x6a et les 0x69.

    Mise en page mesuree sur les trois tables vanilla : le code est bourre de
    0xff jusqu'a un multiple de 16, la section de donnees suit, et le membre
    entier est bourre de 0xff jusqu'a un multiple de 16.
    """
    h, instrs = lire_script(d, base)
    i6a = next(i for i in instrs if i.op == 0x6A)
    avant = bytes(d[base + 16:i6a.debut])
    n_avant = sum(1 for i in instrs if i.debut < i6a.debut)
    code = bytearray(avant)
    code += struct.pack("<HBBI", 0x6A, 1, 1, len(nouveaux))
    for o in nouveaux:
        code += struct.pack("<HBBI", 0x69, 1, 1,
                            encoder_outcome(o["pct"], o["id"], o["loot"], o["rang"]))
    code = _aligner16(bytes(code) + struct.pack("<H", 0xFFFF))
    donnees = bytes(d[base + h["off_donnees"]:fin])
    tete = struct.pack("<iIiI", n_avant + 1 + len(nouveaux), 16 + len(code),
                       h["lg_donnees"], h["nb_chaines"])
    return _aligner16(tete + code + donnees)


def reconstruire_narc(d, remplacements):
    """Rend l'archive NARC `d` ou les membres nommes dans `remplacements`
    ({nom: octets}) sont remplaces. Les membres restent contigus et alignes
    sur 16 octets, comme dans la ROM."""
    membres = membres_narc(d)
    noms = sorted(membres, key=lambda k: membres[k][0])
    p = struct.unpack_from("<H", d, 12)[0]
    blocs = {}
    for _ in range(struct.unpack_from("<H", d, 14)[0]):
        blocs[bytes(d[p:p + 4])] = p
        p += struct.unpack_from("<I", d, p + 4)[0]
    btaf, btnf = blocs[b"BTAF"], blocs[b"BTNF"]
    btnf_bloc = bytes(d[btnf:btnf + struct.unpack_from("<I", d, btnf + 4)[0]])
    img = bytearray()
    fat = []
    for nom in noms:
        a, b = membres[nom]
        contenu = remplacements.get(nom, bytes(d[a:b]))
        contenu = contenu + b"\xff" * (-len(contenu) % 4)
        fat.append((len(img), len(img) + len(contenu)))
        img += contenu
    btaf_bloc = struct.pack("<4sIHH", b"BTAF", 12 + 8 * len(fat), len(fat), 0)
    btaf_bloc += b"".join(struct.pack("<II", a, b) for a, b in fat)
    gmif_bloc = struct.pack("<4sI", b"GMIF", 8 + len(img)) + bytes(img)
    corps = btaf_bloc + btnf_bloc + gmif_bloc
    tete = bytearray(d[:16])
    struct.pack_into("<I", tete, 8, 16 + len(corps))
    # l'ordre des noms de BTNF suit l'ordre des membres : on l'a preserve
    assert [membres_narc(bytes(tete) + corps)[n] for n in noms]
    return bytes(tete) + corps
