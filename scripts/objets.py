#!/usr/bin/env python3
"""Le catalogue d'objets de Dragon Quest IX, lu DANS LA ROM.

OU SONT LES OBJETS. `data/prm/item_fn_div.nat` liste les neuf archives qui
portent le catalogue, une par categorie :

    itemdt_w.gp2  armes          268
    itemdt_s.gp2  boucliers       45
    itemdt_b.gp2  torse          183
    itemdt_u.gp2  jambes          85
    itemdt_h.gp2  tete           132
    itemdt_a.gp2  bras            78
    itemdt_l.gp2  pieds          101
    itemdt_d.gp2  accessoires     52
    itemdt_t.gp2  objets courants ET objets importants   234
                                  ----
                                  1178

Chaque archive GPC2 contient cinq `.nat`, un par langue, de contenu identique
pour ce qui nous interesse. Total 1178, le compte exact de `itemname.gp2`.

FORMAT d'un `itemdt_<c>_<lg>.nat` -- MESURE, pas suppose :

    +0x00   u16   nombre d'enregistrements sur les 12 bits de poids faible
    +0x10         les enregistrements, 32 octets chacun
                    +0x04  u32  champ de drapeaux ; son quartet de poids faible
                                vaut 8 pour un objet utilisable depuis le menu,
                                9 sinon
                    +0x14  u16  IDENTIFIANT DE L'OBJET
            puis un pool de chaines

    Trouve par balayage : pour chaque (taille d'en-tete, taille
    d'enregistrement, position), on a cherche la colonne de u16 dont les
    valeurs sont toutes distinctes et toutes dans 11000-23000. Une seule
    combinaison sort, la meme pour les neuf fichiers, et les neuf ensembles
    d'identifiants obtenus correspondent exactement, categorie par categorie,
    a ceux du save editor de la communaute (`DQIX/editor`, `src/game/data.js`).

LES OBJETS IMPORTANTS. Le jeu ne porte pas de drapeau "important" universel :
le quartet de poids faible de `+0x04` vaut 9 pour TOUT l'equipement. Mais a
l'INTERIEUR de `itemdt_t`, qui melange les objets courants et les objets
importants, il separe exactement 88 objets (quartet 9) de 146 (quartet 8) -- et
ces 88 sont exactement ceux que le save editor classe ITEM_TYPE_IMPORTANT.
Deux sources independantes, zero desaccord.

La lecture est donc : dans `itemdt_t`, quartet 9 = non utilisable = objet
important. `objets_importants()` verifie ce compte de 88 et la presence des
cles connues, et leve si la ROM ne repond pas comme prevu.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gp2

CATEGORIES = {
    "w": "arme", "s": "bouclier", "b": "torse", "u": "jambes",
    "h": "tete", "a": "bras", "l": "pieds", "d": "accessoire",
    "t": "courant ou important",
}
CHEMIN = "data/prm/itemdt_%s.gp2"
TETE = 0x10
ENREG = 32
OFF_DRAPEAUX = 0x04
OFF_ID = 0x14

# Les objets de progression qu'on DOIT retrouver dans les exclusions. Si l'un
# manque, la lecture est fausse et il faut s'arreter : un randomizer qui place
# la Magic key dans un pot rend la partie infinissable.
TEMOINS = {
    22042: "Thief's key",
    22043: "Magic key",
    22044: "Ultimate key",
    22131: "Little key",
    22162: "Quarantomb key",
    22169: "Fygg",
}
NB_IMPORTANTS = 88
NB_OBJETS = 1178


def _membre(rom, categorie, langue="en"):
    """Rend les octets de `itemdt_<c>_<lg>.nat`, lu dans la ROM."""
    chemin = CHEMIN % categorie
    fid = rom.filenames.idOf(chemin)
    if fid is None:
        raise ValueError("absent de la ROM : " + chemin)
    arc = gp2.GP2(chemin, donnees=bytes(rom.files[fid]))
    entrees = sorted(arc.entrees, key=lambda e: e[1] & 0xFFFFFF)
    vise = "itemdt_%s_%s.nat" % (categorie, langue)
    for i, (h, offs, taille) in enumerate(entrees):
        nom = arc.noms[i] if i < len(arc.noms) else ""
        if nom != vise and len(entrees) > 1:
            continue
        pos = arc.first_file * 4 + (offs & 0xFFFFFF) * 4
        data = gp2.lire_bloc(arc.d, pos, pos + taille + 4)[0]
        return data
    raise ValueError("membre introuvable : " + vise)


def lire_categorie(rom, categorie, langue="en"):
    """Rend [(identifiant, quartet de drapeaux)] d'une categorie."""
    d = _membre(rom, categorie, langue)
    n = struct.unpack_from("<H", d, 0)[0] & 0xFFF
    if TETE + n * ENREG > len(d):
        raise ValueError("itemdt_%s : %d enregistrements ne tiennent pas dans "
                         "%d octets" % (categorie, n, len(d)))
    out = []
    for i in range(n):
        o = TETE + i * ENREG
        out.append((struct.unpack_from("<H", d, o + OFF_ID)[0],
                    d[o + OFF_DRAPEAUX] & 0x0F))
    return out


def raretes(rom, langue="en"):
    """Rend {identifiant: etoiles (0 a 5)}, la « Rarity » de l'ecran d'objet.

    Octet +0x05 de l'enregistrement, bits 1 a 3. Trouve en
    cherchant le champ qui vaut 0 pour l'herbe antidote, 2 pour la hache du
    bourreau et 3 pour le « Gladiator's Guide », les etoiles vues a l'ecran sur
    la v12 (captures du joueur, 17 septembre). Une seule position convient, ses
    valeurs vont de 0 a 5, et les 22 objets a 5 etoiles sont exactement les
    equipements legendaires (epee hypernova, massue etoilee, armure legendaire,
    arc de seraphin...).
    """
    out = {}
    for c in CATEGORIES:
        d = _membre(rom, c, langue)
        n = struct.unpack_from("<H", d, 0)[0] & 0xFFF
        for i in range(n):
            o = TETE + i * ENREG
            out[struct.unpack_from("<H", d, o + OFF_ID)[0]] = (d[o + 5] >> 1) & 7
    return out


def catalogue(rom, langue="en"):
    """Rend {identifiant: (categorie, quartet)} pour les 1178 objets du jeu."""
    out = {}
    for c in CATEGORIES:
        for ident, quartet in lire_categorie(rom, c, langue):
            if ident in out:
                raise ValueError("identifiant d'objet en double : %d" % ident)
            out[ident] = (c, quartet)
    if len(out) != NB_OBJETS:
        raise ValueError("catalogue : %d objets, %d attendus"
                         % (len(out), NB_OBJETS))
    return out


def objets_importants(rom, langue="en"):
    """Rend l'ensemble des identifiants a NE JAMAIS mettre dans un conteneur.

    Leve si le compte ou les temoins ne sont pas au rendez-vous : mieux vaut
    ne rien produire qu'une ROM ou une cle manque.
    """
    imp = {ident for ident, quartet in lire_categorie(rom, "t", langue)
           if quartet == 9}
    if len(imp) != NB_IMPORTANTS:
        raise ValueError("objets importants : %d trouves, %d attendus. La "
                         "lecture du catalogue est fausse, on s'arrete."
                         % (len(imp), NB_IMPORTANTS))
    manquants = sorted(set(TEMOINS) - imp)
    if manquants:
        raise ValueError("objets importants : temoins absents %s"
                         % ", ".join("%d (%s)" % (i, TEMOINS[i])
                                     for i in manquants))
    return imp


def pool(rom, langue="en"):
    """Les identifiants qu'on s'autorise a placer dans un conteneur."""
    cat = catalogue(rom, langue)
    imp = objets_importants(rom, langue)
    return sorted(set(cat) - imp)


# L'ORDRE DES NOMS. `itemname_<lg>.nat` range ses 1178 noms en mettant bout a
# bout les neuf categories dans CET ordre-ci, chacune dans l'ordre de ses
# enregistrements `itemdt`. Mesure : sous cette regle, 1178 noms sur 1178
# concordent avec le save editor de la communaute, aux codes de balisage et a
# trois coquilles de l'editeur pres (« startotoga », « sensible sandles »,
# « xenion claws » : la ROM dit stratotoga, sandals, xenlon). Et deux objets
# vus en jeu depuis les savestates du joueur (15033 « silver bracelets »,
# 20507 « holy lance ») portent bien le nom que la regle leur donne.
ORDRE_NOMS = "hbauldwst"

# Balisage des chaines du jeu : accents et guillemets.
BALISES = {
    "<1>": "'", "<6>": "'", "<9>": "'", "<,>": ",", "<oe>": "oe",
    "<:a>": "a", "<:e>": "e", "<:i>": "i", "<:u>": "u", "<:o>": "o",
    "<^a>": "a", "<^e>": "e", "<^i>": "i", "<^o>": "o", "<^u>": "u",
    "<`a>": "a", "<`e>": "e", "<'e>": "e", "<'E>": "E", "<,c>": "c",
}


def nettoyer(nom):
    """Retire le balisage. Sans accents : les sorties console sont en cp1252."""
    for b, v in BALISES.items():
        nom = nom.replace(b, v)
    return nom


def _membre_archive(rom, chemin, vise):
    fid = rom.filenames.idOf(chemin)
    if fid is None:
        raise ValueError("absent de la ROM : " + chemin)
    arc = gp2.GP2(chemin, donnees=bytes(rom.files[fid]))
    entrees = sorted(arc.entrees, key=lambda e: e[1] & 0xFFFFFF)
    for i, (h, offs, taille) in enumerate(entrees):
        if i < len(arc.noms) and arc.noms[i] == vise:
            pos = arc.first_file * 4 + (offs & 0xFFFFFF) * 4
            return gp2.lire_bloc(arc.d, pos, pos + taille + 4)[0]
    raise ValueError("membre introuvable : " + vise)


def noms(rom, langue="en"):
    """Rend {identifiant: nom} lus dans `itemname.gp2`."""
    d = _membre_archive(rom, "data/prm/itemname.gp2",
                        "itemname_%s.nat" % langue)
    n = struct.unpack_from("<H", d, 0)[0] & 0xFFF
    if n != NB_OBJETS:
        raise ValueError("itemname : %d noms, %d attendus" % (n, NB_OBJETS))
    pool_debut = 4 + n * 16
    while d[pool_debut] == 0:
        pool_debut += 1

    def chaine(k):
        o = pool_debut + struct.unpack_from("<I", d, 4 + k * 16)[0]
        return nettoyer(d[o:d.index(b"\x00", o)].decode("utf-8", "replace"))

    out = {}
    k = 0
    for c in ORDRE_NOMS:
        for ident, _q in lire_categorie(rom, c, langue):
            out[ident] = chaine(k)
            k += 1
    return out


if __name__ == "__main__":
    import ndspy.rom
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from rom_vanilla import chemin_vanilla
    chemin = sys.argv[1] if len(sys.argv) > 1 else chemin_vanilla()
    rom = ndspy.rom.NintendoDSRom.fromFile(chemin)
    cat = catalogue(rom)
    imp = objets_importants(rom)
    print("%d objets au catalogue" % len(cat))
    for c, etiq in CATEGORIES.items():
        n = sum(1 for v in cat.values() if v[0] == c)
        print("  itemdt_%s  %-22s %4d" % (c, etiq, n))
    print()
    print("%d objets importants, exclus du pool :" % len(imp))
    print("  " + " ".join(str(i) for i in sorted(imp)))
    print()
    print("pool autorise : %d objets" % len(pool(rom)))
