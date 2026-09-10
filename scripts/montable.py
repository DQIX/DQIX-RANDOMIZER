#!/usr/bin/env python3
"""Lecture et ecriture de la table des monstres de DQ9 (data/prm/mon_btldata.nat).

Format (voir docs/RESEARCH.md pour les preuves) :
    u32 nb = 438, puis 438 enregistrements de 132 octets.

Usage:
    python scripts/montable.py <rom.nds> dump [n]        # affiche n monstres
    python scripts/montable.py <rom.nds> stats           # min/max/moyenne par stat
    python scripts/montable.py <rom.nds> extremes        # les plus faibles / plus forts
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CHEMIN = "data/prm/mon_btldata.nat"
STRIDE = 132
ENTETE = 4

# champs u16 identifies, en offset dans l'enregistrement
CHAMPS = {
    "id_brut":  0x00,   # 0x8000 | id
    "modele":   0x02,
    "nom_str":  0x04,
    "desc_str": 0x06,
    "exp":      0x08,
    "or":       0x0C,
    "hp":       0x5C,
    "mp":       0x5E,
    "attaque":  0x60,
    "defense":  0x62,
    "agilite":  0x64,
}
STATS = ("hp", "mp", "attaque", "defense", "agilite", "exp", "or")

# blocs de resistances, en octets
RES_ELEM = (0x6C, 7)     # 7 multiplicateurs de degats elementaires (%)
RES_ETAT = (0x74, 14)    # 14 resistances aux alterations d'etat (%)


class Monstre:
    """Vue sur un enregistrement de 132 octets. Les ecritures vont dans le tampon."""

    def __init__(self, table, index):
        self.t = table
        self.index = index
        self.base = ENTETE + index * STRIDE

    def __getattr__(self, nom):
        if nom in CHAMPS:
            return struct.unpack_from("<H", self.t.data, self.base + CHAMPS[nom])[0]
        raise AttributeError(nom)

    def __setattr__(self, nom, valeur):
        if nom in CHAMPS:
            struct.pack_into("<H", self.t.data, self.base + CHAMPS[nom],
                             max(0, min(0xFFFF, int(valeur))))
        else:
            object.__setattr__(self, nom, valeur)

    @property
    def id(self):
        return self.id_brut & 0x7FFF

    @property
    def res_elem(self):
        o, n = RES_ELEM
        return list(self.t.data[self.base + o:self.base + o + n])

    @res_elem.setter
    def res_elem(self, vals):
        o, n = RES_ELEM
        assert len(vals) == n
        self.t.data[self.base + o:self.base + o + n] = bytes(
            max(0, min(255, int(v))) for v in vals)

    @property
    def res_etat(self):
        o, n = RES_ETAT
        return list(self.t.data[self.base + o:self.base + o + n])

    @res_etat.setter
    def res_etat(self, vals):
        o, n = RES_ETAT
        assert len(vals) == n
        self.t.data[self.base + o:self.base + o + n] = bytes(
            max(0, min(255, int(v))) for v in vals)

    def stats(self):
        return {s: getattr(self, s) for s in STATS}

    def octets(self):
        return bytes(self.t.data[self.base:self.base + STRIDE])

    def __repr__(self):
        nom = getattr(self, "nom", None) or ""
        return (f"#{self.index:3d} id={self.id:3d} {nom[:24]:<24s} "
                f"HP{self.hp:6d} MP{self.mp:4d}  "
                f"ATT{self.attaque:4d} DEF{self.defense:4d} AGI{self.agilite:4d}  "
                f"XP{self.exp:6d} or{getattr(self, 'or'):5d}")


class TableMonstres:
    def __init__(self, donnees):
        self.data = bytearray(donnees)
        self.nb = struct.unpack_from("<I", self.data, 0)[0]
        attendu = ENTETE + self.nb * STRIDE
        if attendu != len(self.data):
            raise ValueError(
                f"taille inattendue : {len(self.data)} au lieu de {attendu} "
                f"(nb={self.nb}, stride={STRIDE})")
        self.monstres = [Monstre(self, i) for i in range(self.nb)]

    @classmethod
    def depuis_rom(cls, chemin_rom, langue=None):
        """Charge la table. Si `langue` est donnee, attache aussi les noms lus
        dans data/prm/mon_data.gp2 (voir monnames.py)."""
        import ndspy.rom
        rom = ndspy.rom.NintendoDSRom.fromFile(chemin_rom)
        table = cls(rom.files[rom.filenames.idOf(CHEMIN)])
        if langue:
            table.attacher_noms(chemin_rom, langue)
        return table, rom

    def attacher_noms(self, chemin_rom, langue="en"):
        from monnames import charger
        noms = charger(chemin_rom, langue)
        for i, m in enumerate(self.monstres):
            if i < len(noms):
                object.__setattr__(m, "nom", noms[i]["nom"])
                object.__setattr__(m, "modele", noms[i]["modele"])

    def ecrire_dans_rom(self, rom):
        rom.files[rom.filenames.idOf(CHEMIN)] = bytes(self.data)

    def __iter__(self):
        return iter(self.monstres)

    def __len__(self):
        return self.nb

    def __getitem__(self, i):
        return self.monstres[i]


def _main():
    chemin, cmd = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "dump")
    langue = os.environ.get("DQ9_LANGUE", "en")
    try:
        table, _rom = TableMonstres.depuis_rom(chemin, langue)
    except Exception as e:
        print(f"(noms indisponibles : {e})")
        table, _rom = TableMonstres.depuis_rom(chemin)
    print(f"{len(table)} monstres, {STRIDE} octets par enregistrement\n")

    if cmd == "dump":
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 20
        for m in list(table)[:n]:
            print(m)

    elif cmd == "stats":
        print(f"{'stat':>9} {'min':>7} {'max':>7} {'moyenne':>9} {'median':>7}")
        print("-" * 44)
        for s in STATS:
            v = sorted(getattr(m, s) for m in table)
            print(f"{s:>9} {v[0]:7d} {v[-1]:7d} {sum(v) / len(v):9.1f} "
                  f"{v[len(v) // 2]:7d}")
        print("\nresistances elementaires : valeurs rencontrees")
        vues = sorted({x for m in table for x in m.res_elem})
        print("   ", vues)
        print("resistances aux alterations d'etat : valeurs rencontrees")
        vues = sorted({x for m in table for x in m.res_etat})
        print("   ", vues)

    elif cmd == "extremes":
        par_hp = sorted(table, key=lambda m: m.hp)
        print("--- les 8 plus faibles en HP ---")
        for m in par_hp[:8]:
            print(m)
        print("--- les 8 plus resistants en HP ---")
        for m in par_hp[-8:]:
            print(m)
        print("--- les 8 qui donnent le plus d'experience ---")
        for m in sorted(table, key=lambda m: m.exp)[-8:]:
            print(m)

    else:
        print(__doc__)


if __name__ == "__main__":
    _main()
