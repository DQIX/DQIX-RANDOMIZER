#!/usr/bin/env python3
"""Tables de rencontres de Dragon Quest IX : lecture et reecriture des
identifiants de monstre.

QUATRE FICHIERS, tous au format de table taggee (voir docs/RESEARCH.md §3) :

    data/prm/encmons.bin       209 enreg.   especes par carte
    data/prm/encfld.bin       1827 enreg.   rencontres sur le terrain
    data/prm/encbtl.bin       2874 enreg.   rencontres en combat
    data/event/eventbattle.bin  98 enreg.   COMBATS SCRIPTES (boss, prologue)

Le dernier a ete trouve en cherchant les chaines de chemin de fichier dans le
code : `data/event/eventbattle.bin` est reference par l'ARM9 decompresse et par
l'overlay 17. Il explique pourquoi randomiser les trois premiers ne change rien
au combat du prologue : celui-ci est scripte, et son enregistrement est
[26] = 1x slime, 1x cruelcumber, 1x slime.

L'overlay ARM9 numero 17 reference les trois premiers, plus
fld_mondata.bin.

OU SONT LES IDENTIFIANTS — mesure, pas supposition. Pour chaque combinaison
(fichier, tag, nombre de champs, position du champ), on a compte la proportion de
valeurs non nulles qui sont des identifiants de monstre valides, selon plusieurs
decoupages. Resultat :

    encbtl  tag 0x66 champ0   1058 valeurs   12 bits bas : 100,0 %
    encbtl  tag 0x67 champ0   1526 valeurs   12 bits bas : 100,0 %
    encfld  tag 0x67 champ0   1043 valeurs   12 bits bas : 100,0 %
    encmons tag 0x66 champs>=2               u16 de poids fort : 100 % / 99,2 %

Soit 3 627 valeurs dont les 12 bits de poids faible sont TOUTES des identifiants
valides. Sur 65 536 valeurs possibles dont seules 438 sont valides, c'est
impossible par hasard.

Les bits de poids fort portent autre chose (un poids ou une probabilite : dans
encfld tag 0x67, `valeur >> 12` ne prend que les valeurs 0 a 7). On les preserve
tels quels.

REGLE DE PRUDENCE. Le decoupage du u16 de poids faible d'encmons n'est pas
elucide : il contient un identifiant valide dans la plupart des enregistrements
mais seulement 14 % du temps sur un champ. On ne reecrit donc QUE les
emplacements qui contiennent deja un identifiant valide. Un champ dont on ignore
le sens reste intact, par construction.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prmtable import PrmTable

# chemin NitroFS de chaque fichier gere
CHEMINS = {
    "encmons.bin":     "data/prm/encmons.bin",
    "encfld.bin":      "data/prm/encfld.bin",
    "encbtl.bin":      "data/prm/encbtl.bin",
    "eventbattle.bin": "data/event/eventbattle.bin",
}
FICHIERS = tuple(CHEMINS)
# les rencontres libres d'un cote, les combats scriptes de l'autre : toucher aux
# boss du scenario est bien plus risque pour la progression, donc on separe
FICHIERS_RENCONTRES = ("encmons.bin", "encfld.bin", "encbtl.bin")
FICHIERS_SCRIPTES = ("eventbattle.bin",)

# Emplacements ou un identifiant de monstre a ete mesure.
#   (tag, nb_champs, position) -> liste de (decalage_en_bits, masque)
# Un identifiant occupe `masque` bits a partir du bit `decalage`.
EMPLACEMENTS = {
    "encbtl.bin": {
        (0x66, 2, 0): [(0, 0xFFF)],
        (0x67, 1, 0): [(0, 0xFFF)],
    },
    "encfld.bin": {
        (0x67, 2, 0): [(0, 0xFFF)],
    },
    # data/event/eventbattle.bin : les 98 combats SCRIPTES du jeu.
    # 9 champs u32 : [id_evenement, id1, nb1, id2, nb2, id3, nb3, ?, id_message]
    # Les champs 1, 3 et 5 portent un identifiant de monstre a 100 %.
    # Les emplacements vides valent 0xFFFFFFFF, donc ils sont ignores
    # automatiquement par la regle de prudence (ce n'est pas un id valide).
    "eventbattle.bin": {
        (0x64, 9, 1): [(0, 0xFFFFFFFF)],
        (0x64, 9, 3): [(0, 0xFFFFFFFF)],
        (0x64, 9, 5): [(0, 0xFFFFFFFF)],
    },
    "encmons.bin": {
        # champs de donnees : deux moities u16, chacune pouvant porter un id
        (0x66, 3, 2): [(0, 0xFFFF), (16, 0xFFFF)],
        (0x66, 4, 2): [(0, 0xFFFF), (16, 0xFFFF)],
        (0x66, 4, 3): [(0, 0xFFFF), (16, 0xFFFF)],
        (0x66, 5, 1): [(0, 0xFFFF), (16, 0xFFFF)],
        (0x66, 5, 2): [(0, 0xFFFF), (16, 0xFFFF)],
        (0x66, 5, 3): [(0, 0xFFFF), (16, 0xFFFF)],
        (0x66, 5, 4): [(0, 0xFFFF), (16, 0xFFFF)],
    },
}


class TablesRencontres:
    def __init__(self, rom, fichiers=FICHIERS):
        self.rom = rom
        self.tables = {}
        for nom in fichiers:
            fid = rom.filenames.idOf(CHEMINS[nom])
            self.tables[nom] = PrmTable(rom.files[fid])

    def references(self, ids_valides):
        """Enumere les references d'identifiant : (fichier, i_enreg, i_champ,
        decalage, masque, id_actuel). Ne rend que celles qui contiennent
        effectivement un identifiant valide."""
        for nom, t in self.tables.items():
            regles = EMPLACEMENTS.get(nom, {})
            for ir, r in enumerate(t.records):
                cle = (r.tag, len(r.fields), None)
                for ic, v in enumerate(r.fields):
                    for dec, masque in regles.get((r.tag, len(r.fields), ic), []):
                        val = (v >> dec) & masque
                        if val in ids_valides:
                            yield nom, ir, ic, dec, masque, val

    def compter(self, ids_valides):
        n = 0
        par_fichier = {}
        for nom, *_ in self.references(ids_valides):
            n += 1
            par_fichier[nom] = par_fichier.get(nom, 0) + 1
        return n, par_fichier

    def appliquer(self, correspondance, ids_valides):
        """Remplace chaque identifiant par `correspondance[id]`. Ne touche que
        les emplacements deja porteurs d'un identifiant valide."""
        modifs = 0
        for nom, ir, ic, dec, masque, ancien in list(
                self.references(ids_valides)):
            nouveau = correspondance.get(ancien, ancien)
            if nouveau == ancien:
                continue
            t = self.tables[nom]
            v = t.records[ir].fields[ic]
            v = (v & ~(masque << dec)) | ((nouveau & masque) << dec)
            t.set_field(ir, ic, v)
            modifs += 1
        return modifs

    def appliquer_tirage_libre(self, rng, choix, ids_valides):
        """Tire une espece au hasard, INDEPENDAMMENT pour chaque reference.

        Difference avec `appliquer` : il n'y a plus de correspondance globale.
        Une meme espece d'origine peut devenir differentes choses selon
        l'endroit, et certaines especes n'apparaitront nulle part.

        Consequence a connaitre : le symbole visible sur le terrain et la
        composition du combat sont stockes dans des fichiers differents
        (`encfld.bin` et `encbtl.bin`). Un tirage independant peut donc faire
        apparaitre un monstre a l'ecran et en engager un autre au combat. Avec
        une permutation globale ce risque n'existe pas.
        """
        modifs = 0
        for nom, ir, ic, dec, masque, ancien in list(
                self.references(ids_valides)):
            nouveau = rng.choice(choix)
            if nouveau == ancien:
                continue
            t = self.tables[nom]
            v = t.records[ir].fields[ic]
            v = (v & ~(masque << dec)) | ((nouveau & masque) << dec)
            t.set_field(ir, ic, v)
            modifs += 1
        return modifs

    def ecrire_dans_rom(self):
        for nom, t in self.tables.items():
            fid = self.rom.filenames.idOf(CHEMINS[nom])
            self.rom.files[fid] = bytes(t.data)

    def cartes(self):
        """Rend { id_carte : [ids de monstre] } d'apres encmons.bin."""
        out = {}
        t = self.tables["encmons.bin"]
        for r in t.records:
            if r.tag != 0x66 or not r.fields:
                continue
            carte = r.fields[0]
            liste = []
            for v in r.fields[1:]:
                for dec in (0, 16):
                    x = (v >> dec) & 0xFFFF
                    if x:
                        liste.append(x)
            out[carte] = liste
        return out


if __name__ == "__main__":
    import ndspy.rom
    from montable import TableMonstres
    from monnames import charger

    rom_path = sys.argv[1]
    rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)
    table, _ = TableMonstres.depuis_rom(rom_path)
    ids = {m.id for m in table}
    noms = charger(rom_path, sys.argv[2] if len(sys.argv) > 2 else "en")
    par_id = {m.id: noms[i]["nom"] for i, m in enumerate(table)}

    tr = TablesRencontres(rom)
    n, detail = tr.compter(ids)
    print(f"{n} references d'identifiant de monstre trouvees")
    for k, v in sorted(detail.items()):
        print(f"   {k:<14s} {v:5d}")
    print("\nquelques cartes et leurs especes :")
    for carte, liste in list(tr.cartes().items())[:8]:
        libelles = [par_id.get(i, f"?{i}") for i in liste]
        print(f"   carte {carte:6d} : {', '.join(libelles)}")
