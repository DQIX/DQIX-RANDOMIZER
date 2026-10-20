"""La musique d'un combat scripte suit son boss (ZER-94).

Demande du joueur (19/10/2026) : si Corvus tombe au premier combat, on doit
entendre la musique de Corvus. Defaut, sans option.

LE CHAMP 7 D'`eventbattle.bin` est la musique du combat (research §84) :
23 un combat ordinaire, 24 les boss d'histoire et d'antre, 26 Corvus, 27-38
un theme par boss legendaire (ses trois niveaux le partagent ; Mortamor, ses
pinces et Nokturnus ont tous le 35). La musique est donc PAR COMBAT, pas par
espece : un boss deplace par `--boss` emportait la musique de sa place
d'arrivee.

LA REGLE, la meme a la construction et dans le blob : la musique d'un combat
est celle du PREMIER emplacement (0, 1, 2) dont l'espece est un boss --
la musique de son combat vanilla. Sans boss (prologue, monstres ordinaires,
--boss-mixte qui pose un monstre), le combat garde la sienne. Sur la
vanilla, la regle rend chaque combat a lui-meme : aucun octet ne change.

    construction   accorder() / appliquer(), apres que les especes sont
                   ecrites (randomizer, puis config_boss.appliquer) ;
    chaque visite  la greffe `greffe_musique` du blob (patch_blob), sur
                   `strh r0, [r1, #0xe]` en 0x020740F0, avec table_blob().
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CHEMIN = "data/event/eventbattle.bin"
CHAMP = 7
VIDE = 0xFFFFFFFF
PROLOGUE_ENREG = 0

# LA MUSIQUE DE CHAQUE BOSS, celle de son combat vanilla. Les 89 especes de
# categories_boss, recontrolees sur la ROM par verifier_table().
_PAR_MUSIQUE = {
    23: (800,),
    24: (216, 219, 225, 227, 234, 300, 301, 302, 303, 304, 305, 306, 307,
         308, 309, 310, 311, 312, 313, 314, 315, 316, 317, 318, 319, 322,
         326, 332, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345,
         346, 347, 801),
    26: (320,),
    27: (500, 600, 601), 28: (501, 602, 604), 29: (502, 606, 608),
    30: (503, 610, 612), 31: (504, 615, 618), 32: (505, 622, 624),
    33: (506, 628, 630), 34: (507, 633, 635),
    35: (508, 509, 510, 514, 639, 641, 770, 773, 776, 777, 778, 779),
    36: (511, 645, 647), 37: (512, 650, 652), 38: (513, 655, 658),
}
MUSIQUES = {e: m for m, es in _PAR_MUSIQUE.items() for e in es}

# LA TABLE DU BLOB : un u16 par boss, l'espece sur 10 bits, la musique
# moins 23 sur les 6 du haut ; un zero termine (aucune entree ne vaut 0).
MUSIQUE_BASE = 23


def musique(especes, actuelle):
    """La musique d'un combat dont les trois emplacements portent `especes`."""
    for e in especes:
        if e in MUSIQUES:
            return MUSIQUES[e]
    return actuelle


def _enreg_musical(r, rec):
    return (r != PROLOGUE_ENREG and rec.tag == 0x64 and len(rec.fields) == 9
            and rec.fields[CHAMP] != VIDE)


def accorder(table):
    """Accorde le champ 7 de chaque combat de `table` (PrmTable) a son boss.
    Rend le nombre de combats changes."""
    n = 0
    for r, rec in enumerate(table.records):
        if not _enreg_musical(r, rec):
            continue
        f = rec.fields
        m = musique((f[1], f[3], f[5]), f[CHAMP])
        if m != f[CHAMP]:
            table.set_field(r, CHAMP, m)
            n += 1
    return n


def appliquer(rom):
    """accorder() sur l'eventbattle de `rom` (ndspy), reecrit seulement s'il
    change. Rend le nombre de combats changes."""
    from prmtable import PrmTable
    fid = rom.filenames.idOf(CHEMIN)
    t = PrmTable(rom.files[fid])
    n = accorder(t)
    if n:
        rom.files[fid] = bytes(t.data)
    return n


def table_blob():
    """Les octets de la table de la greffe (u16, zero final)."""
    out = bytearray()
    for e, m in sorted(MUSIQUES.items()):
        assert 0 < e < 1 << 10 and 0 <= m - MUSIQUE_BASE < 1 << 6, (e, m)
        out += struct.pack("<H", e | (m - MUSIQUE_BASE) << 10)
    return bytes(out + b"\x00\x00")


def verifier(rom):
    """Leve si un combat de `rom` ne porte pas la musique de son boss."""
    from prmtable import PrmTable
    for r, rec in enumerate(PrmTable(rom.files[rom.filenames.idOf(CHEMIN)]).records):
        if not _enreg_musical(r, rec):
            continue
        f = rec.fields
        if musique((f[1], f[3], f[5]), f[CHAMP]) != f[CHAMP]:
            raise AssertionError("musique : combat %d (evenement %d), %d au "
                                 "lieu de %d" % (r, f[0], f[CHAMP],
                                                 musique((f[1], f[3], f[5]), 0)))


def verifier_table(rom):
    """Leve si MUSIQUES n'est pas celle de la vanilla `rom` : chaque boss de
    categories_boss, la musique de son combat, et la regle rend la vanilla
    a elle-meme."""
    import categories_boss as CB
    from prmtable import PrmTable
    boss = CB.HISTOIRE | CB.GROTTES | CB.LEGENDES
    if set(MUSIQUES) != boss:
        raise AssertionError("musique : %d boss dans la table, %d attendus"
                             % (len(MUSIQUES), len(boss)))
    t = PrmTable(rom.files[rom.filenames.idOf(CHEMIN)])
    for r, rec in enumerate(t.records):
        if r == PROLOGUE_ENREG or rec.tag != 0x64 or len(rec.fields) != 9:
            continue
        for k in range(3):
            e = rec.fields[1 + 2 * k]
            if e in boss and MUSIQUES[e] != rec.fields[CHAMP]:
                raise AssertionError("musique : %d joue %d en vanilla, %d dans "
                                     "la table" % (e, rec.fields[CHAMP],
                                                   MUSIQUES[e]))
    if accorder(t):
        raise AssertionError("musique : la regle change la vanilla")


if __name__ == "__main__":
    import ndspy.rom
    from rom_vanilla import chemin_vanilla
    v = ndspy.rom.NintendoDSRom.fromFile(chemin_vanilla())
    verifier_table(v)
    verifier(v)
    print("musique_boss : %d boss, table du blob %d o, vanilla inchangee"
          % (len(MUSIQUES), len(table_blob())))
    if len(sys.argv) > 1:
        verifier(ndspy.rom.NintendoDSRom.fromFile(sys.argv[1]))
        print("%s : chaque combat porte la musique de son boss" % sys.argv[1])
