"""Lit les declencheurs d'une carte, `data/scenario/trigger<code>.bin`.

C'est un script Nitro generique (`treasure.lire_script`). Chaque instruction
0x01 est un declencheur :

    carte, de_a, de_b, a_a, a_b, genre, noeud, noeud, ...

- `carte` : identifiant de carte (le declencheur n'existe que sur elle) ;
- fenetre d'histoire : de_a*1000+de_b <= progression <= a_a*1000+a_b ;
- `genre` : 0 = evalue avant de parler (pose la condition de dialogue du PNJ),
  1 = evalue apres le dialogue (accepter, finir, donner...), autres a decoder ;
- puis des noeuds. Chaque parametre u32 se lit en deux demi-mots, POIDS FORT
  D'ABORD : 0x00370015 donne 0x37, 0x15. Le premier demi-mot d'un noeud est
  son opcode ; un opcode < 0x64 (ou >= 0x1F4) est un TEST (tous doivent etre
  vrais), sinon une ACTION. Un noeud occupe ARITE[op] parametres u32.

ARITE a ete mesuree en faisant tourner le vrai lecteur du jeu (0x0205EC80)
sous unicorn, un opcode a la fois (research §111). Absent = 1 parametre.
L'opcode 0x45 n'a pas pu etre mesure (lecture hors carte memoire) : un fichier
qui l'emploie est signale.

Usage : python scripts/declencheurs.py <code carte> [--brut]
        python scripts/declencheurs.py --tout     (verifie tous les fichiers)
"""
import sys

import treasure

ARITE = {
    0x1D: 3, 0x20: 2, 0x21: 2, 0x2C: 2, 0x2E: 2, 0x2F: 2, 0x30: 2, 0x31: 2, 0x32: 5,
    0x34: 2, 0x35: 3, 0x36: 3, 0x37: 2, 0x38: 3, 0x39: 3, 0x3A: 3, 0x3B: 3, 0x3C: 3,
    0x3D: 3, 0x3E: 2, 0x3F: 2, 0x40: 3, 0x41: 3, 0x42: 2, 0x46: 2, 0x49: 2, 0x4A: 2,
    0x4B: 2, 0x4C: 2, 0x4E: 3, 0x4F: 2, 0x52: 5, 0x53: 2, 0x55: 2, 0x5A: 2, 0x5B: 2,
    0x6C: 3, 0x6D: 3, 0x74: 2, 0x75: 2, 0x76: 2, 0x7A: 4, 0x7B: 2, 0x82: 2, 0x83: 2,
    0x84: 4, 0x85: 2, 0x86: 2, 0x87: 2, 0x88: 3, 0x8A: 2, 0x8B: 2, 0x8C: 2, 0x8F: 8,
    0x90: 2, 0x94: 4, 0x95: 2, 0x96: 2, 0x98: 3, 0x99: 3, 0x9A: 3, 0x9B: 2, 0x9C: 2,
    0x9D: 2, 0x9E: 2, 0x9F: 2, 0xA7: 2, 0xA8: 2, 0xA9: 2, 0xAB: 2, 0xAC: 2, 0xAE: 2,
    0xB0: 2, 0xB1: 2, 0xB2: 4, 0xB3: 2, 0xB4: 2, 0xBC: 3, 0xBE: 3, 0xC3: 2, 0xC4: 2,
    0xC8: 2, 0xC9: 2, 0xCF: 3, 0xD5: 3, 0xD6: 4, 0xD7: 3, 0xE2: 2, 0xE6: 2, 0xE8: 2,
    0x1F4: 2,
}
INCONNUS = {0x45}

# Etat de quete tel que l'ecrivent les donnees (dialogues 0x02 et tests
# 0x35-0x3D) -> valeur brute (4 bits par quete en 0x02108844+0x2CC).
ETAT_QUETE = {3: "proposable (brut 1)", 0: "en cours (brut 2)", 2: "finie (brut 3)",
              1: "bit 0x4", -1: "fermee (brut 0)", 5: "fermee (brut 0)"}


def _etat(v):
    v = v - 0x10000 if v >= 0x8000 else v
    return "%d=%s" % (v, ETAT_QUETE.get(v, "?"))


# Ce qui est compris (research §111). Les autres s'affichent en brut.
NOMS = {
    0x00: lambda a: "drapeau %#x pose" % a[0],
    0x01: lambda a: "drapeau %#x efface" % a[0],
    0x64: lambda a: "POSER drapeau %#x" % a[0],
    0x65: lambda a: "EFFACER drapeau %#x" % a[0],
    0x06: lambda a: "PNJ == %d" % a[0],
    0x0B: lambda a: "condition de la ligne dite == %d" % a[0],
    0x10: lambda a: "reponse au choix == %d" % a[0],
    0x12: lambda a: "a l'objet 0x%04X" % a[0],
    0x13: lambda a: "n'a pas l'objet 0x%04X" % a[0],
    0x14: lambda a: "quete %d en cours" % a[0],
    0x30: lambda a: "a au moins %d fois l'objet 0x%04X" % (a[2], a[0]),
    0x16: lambda a: "quete %d finie" % a[0],
    0x35: lambda a: "PNJ %d, quete %d %s, ligne %d, choix %d" % (a[0], a[1], _etat(a[2]), a[3], a[4]),
    0x36: lambda a: "PNJ %d, quete %d %s, a l'objet 0x%04X" % (a[0], a[1], _etat(a[2]), a[3]),
    0x37: lambda a: "PNJ %d, quete %d %s" % (a[0], a[1], _etat(a[2])),
    0x57: lambda a: "journal de quetes %s" % ("plein (8)" if a[0] else "pas plein"),
    0x72: lambda a: "DONNER objet 0x%04X x1" % a[0],
    0x73: lambda a: "RETIRER objet 0x%04X x1" % a[0],
    0x74: lambda a: "DONNER objet 0x%04X x%d" % (a[0], a[1]),
    0x75: lambda a: "RETIRER objet 0x%04X x%d" % (a[0], a[1]),
    0x76: lambda a: "condition de dialogue du PNJ %d := %d" % (a[0], a[1]),
    0x7D: lambda a: "ACCEPTER quete %d" % a[0],
    0x7F: lambda a: "FINIR quete %d" % a[0],
}


def demi_mots(params):
    for p in params:
        yield (p >> 16) & 0xFFFF
        yield p & 0xFFFF


def noeuds(params):
    """Decoupe les parametres apres l'en-tete en noeuds (op, [args])."""
    i = 0
    out = []
    while i < len(params):
        op = (params[i] >> 16) & 0xFFFF
        if op in INCONNUS:
            raise ValueError("opcode 0x%X d'arite inconnue" % op)
        n = ARITE.get(op, 1)
        if i + n > len(params):
            raise ValueError("noeud 0x%X tronque" % op)
        hw = list(demi_mots(params[i:i + n]))
        out.append((op, hw[1:]))
        i += n
    return out


def texte_noeud(op, args):
    f = NOMS.get(op)
    if f:
        try:
            return f(args)
        except IndexError:
            pass
    return "op %02X(%s)" % (op, ", ".join("0x%X" % a for a in args))


def lire(rom, code):
    d = bytes(rom.getFileByName("data/scenario/trigger%s.bin" % code))
    _, ins = treasure.lire_script(d)
    res = []
    for i in ins:
        if i.op != 0x01:
            continue
        v = list(i.valeurs)
        carte, da, db, aa, ab, genre = v[:6]
        res.append({"debut": i.debut, "carte": carte, "de": (da, db), "a": (aa, ab),
                    "genre": genre, "noeuds": noeuds(v[6:])})
    return res


def _codes(rom):
    def walk(f, p=""):
        for n in f.files:
            yield p + n
        for n, s in f.folders:
            yield from walk(s, p + n + "/")
    for n in walk(rom.filenames):
        if n.startswith("data/scenario/trigger") and n.endswith(".bin"):
            yield n[len("data/scenario/trigger"):-4]


def main():
    import ndspy.rom
    import rom_vanilla
    rom = ndspy.rom.NintendoDSRom.fromFile(rom_vanilla.chemin_vanilla())
    if sys.argv[1] == "--tout":
        ok = ko = 0
        for code in _codes(rom):
            try:
                n = len(lire(rom, code))
                ok += 1
            except ValueError as e:
                ko += 1
                print("%s : %s" % (code, e))
        print("%d fichiers lus en entier, %d en echec" % (ok, ko))
        return
    for t in lire(rom, sys.argv[1]):
        print("%04X carte %d  histoire %d.%d-%d.%d  genre %d" % (
            t["debut"], t["carte"], t["de"][0], t["de"][1], t["a"][0], t["a"][1], t["genre"]))
        for op, args in t["noeuds"]:
            if "--brut" in sys.argv:
                print("     %s %02X %s" % ("si " if op < 0x64 or op >= 0x1F4 else "=> ", op, args))
            else:
                print("     %s %s" % ("si " if op < 0x64 or op >= 0x1F4 else "=> ", texte_noeud(op, args)))


if __name__ == "__main__":
    main()
