"""Une technique garde l'arme de son arbre d'ORIGINE (ZER-65, option).

LE CONSTAT (retour d'un joueur, 26/09/2026). Avec `--aptitudes-chaos`, une
technique deplacee dans l'arbre d'une autre arme (Tension, de la hache,
arrivee dans l'arbre de la baguette) ne s'utilise qu'avec l'arme de l'arbre
d'ARRIVEE, mais s'anime avec celle d'origine. Le joueur veut les deux
comportements : l'actuel, et « la technique reste liee a son arme ».

POURQUOI (research §99). Au chargement, `skilltable.bin` est relu en une
table de fiches de 12 octets (gestionnaire `0x0209A114`, ARM9) :

    +0  bits 0-10 champ 0 (palier)     bits 11-15 champ 4 (nature)
    +2  u16       champ 3 (l'action, cle de `0x0209A624`)
    +4  bits 0-4  champ 1 (L'ARBRE)    bits 5-11 champ 2 (cout)
        bits 12-19 champ 5 (valeur)    bits 20-24 champ 8 (categorie)
        bits 25-31 remis a zero        (`bic r2, r1, #0xfe000000`)
    +8  u16 champ 6    +10 u16 champ 7

Le filtre des techniques du combat (overlay 0, `0x0217C3D0`) cherche la fiche
de chaque technique apprise PAR SON ACTION et compare ses bits 0-4 -- l'arbre
ou elle est rangee -- a la categorie de l'arme (et du bouclier) en main ; un
arbre au-dela de 14 (les vocations) passe toujours. `0x0209A624` n'a que cet
appelant.

L'OPTION. On range l'arbre d'ORIGINE de chaque aptitude dans les bits 5-9 de
son champ 8 (valeurs vanilla 1 a 20 : les bits 0-4 suffisent) ; le
constructeur le recopie en bits 25-29 au lieu de les effacer (cinq
instructions changees, aucune ajoutee), et le filtre lit ces bits-la au lieu
de l'arbre (quatre decalages changes). L'autre gestionnaire de
`skilltable.bin` (`0x0209A228`) tronque le champ 8 a cinq bits : il ne voit
rien. Aucune lecture non masquee des bits 20 et plus n'existe dans le code
(balayage de l'ARM9 et des 35 overlays).

A appeler APRES patch_aptitudes : l'arbre d'origine d'une charge se lit dans
la ROM vanilla par son identifiant de palier (champ 0), qui voyage avec elle.
"""
import struct

import ndspy.code
import ndspy.codeCompression as cc

from patch_hasard import assembler, COMPRESSED_END
from prmtable import PrmTable

CHEMIN = "data/prm/skilltable.bin"
BASE_ARM9 = 0x02000000
OVL_COMBAT = 0
CHAMP_PALIER, CHAMP_ARBRE, CHAMP_ACTION, CHAMP_CATEGORIE = 0, 1, 3, 8

# Le constructeur : le champ 8 sur dix bits (categorie + arbre d'origine)
# en +4 bits 20-29, et les bits 25-29 gardes.
ARM9_SITES = [
    (0x0209A1F0, "lsl r0, r0, #0x1b",        "lsl r0, r0, #0x16"),
    (0x0209A1F4, "bic r1, r1, #0x1f00000",   "bic r1, r1, #0xff000000"),
    (0x0209A1F8, "orr r1, r1, r0, lsr #7",   "bic r1, r1, #0xf00000"),
    (0x0209A1FC, "str r1, [sp, #4]",         "orr r1, r1, r0, lsr #2"),
    (0x0209A204, "bic r2, r1, #0xfe000000",  "mov r2, r1"),
]
# Le filtre : l'exigence lue en bits 25-29 au lieu de l'arbre (bits 0-4).
OVL0_SITES = [
    (0x0217C424, "lsl r1, r1, #0x1b", "lsl r1, r1, #2"),
    (0x0217C444, "lsl r1, r1, #0x1b", "lsl r1, r1, #2"),
    (0x0217C46C, "lsl r2, r2, #0x1b", "lsl r2, r2, #2"),
    (0x0217C488, "lsl r2, r2, #0x1b", "lsl r2, r2, #2"),
]


def _desas(octets, adr):
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
    i = next(md.disasm(bytes(octets[:4]), adr))
    return "%s %s" % (i.mnemonic, i.op_str)


def _poser(d, base, sites):
    for adr, avant, apres in sites:
        o = adr - base
        lu = _desas(d[o:o + 4], adr)
        if lu != avant:
            raise SystemExit("lien arme : a %#010x attendu %r, lu %r"
                             % (adr, avant, lu))
        d[o:o + 4] = assembler([apres], adr)


def arbres_d_origine(rom_vanilla):
    """{palier: arbre} lus dans la ROM vanilla."""
    t = PrmTable(bytes(rom_vanilla.getFileByName(CHEMIN)))
    return {r.fields[CHAMP_PALIER]: r.fields[CHAMP_ARBRE]
            for r in t.records if len(r.fields) == 9}


def patcher(rom, rom_vanilla, bavard=True):
    """Marque l'arbre d'origine des aptitudes et pose les deux leviers.
    Rend le nombre d'aptitudes marquees."""
    n, deplacees = marquer(rom, rom_vanilla)

    arm9 = bytearray(cc.decompress(bytes(rom.arm9)))
    _poser(arm9, BASE_ARM9, ARM9_SITES)
    struct.pack_into("<I", arm9, COMPRESSED_END, 0)
    rom.arm9 = bytes(arm9)

    ovl = rom.loadArm9Overlays()
    o = ovl[OVL_COMBAT]
    d = bytearray(o.data)
    _poser(d, o.ramAddress, OVL0_SITES)
    o.data = bytes(d)
    rom.files[o.fileID] = o.save(compress=True)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovl)
    if bavard:
        print("  lien technique-arme : %d aptitudes gardent l'arme de leur "
              "arbre d'origine (%d hors de leur arbre)" % (n, deplacees))
    return n


def pose(rom):
    """Vrai si les leviers de code sont poses (le constructeur lit dix bits)."""
    arm9 = cc.decompress(bytes(rom.arm9))
    adr, _avant, apres = ARM9_SITES[0]
    return _desas(arm9[adr - BASE_ARM9:adr - BASE_ARM9 + 4], adr) == apres


def marquer(rom, rom_vanilla):
    """La partie donnees : l'arbre d'origine de chaque aptitude dans les bits
    5-9 de son champ 8, d'apres son palier. Rend (marquees, hors de leur
    arbre). A refaire apres toute reecriture des arbres (config_arbres)."""
    origine = arbres_d_origine(rom_vanilla)
    fid = rom.filenames.idOf(CHEMIN)
    t = PrmTable(bytes(rom.files[fid]))
    n = deplacees = 0
    for i, r in enumerate(t.records):
        if len(r.fields) != 9 or not r.fields[CHAMP_ACTION]:
            continue
        cat = r.fields[CHAMP_CATEGORIE]
        if cat >> 5:
            raise SystemExit("lien arme : champ 8 = %d, plus de cinq bits" % cat)
        arbre = origine[r.fields[CHAMP_PALIER]]
        t.set_field(i, CHAMP_CATEGORIE, cat | (arbre << 5))
        n += 1
        deplacees += arbre != r.fields[CHAMP_ARBRE]
    rom.files[fid] = bytes(t.data)
    return n, deplacees


def verifier(rom, rom_vanilla):
    """Leve si les leviers manquent ou si une aptitude ne porte pas l'arbre
    d'origine de son palier. Rend le nombre d'aptitudes marquees."""
    origine = arbres_d_origine(rom_vanilla)
    t = PrmTable(bytes(rom.getFileByName(CHEMIN)))
    n = 0
    for r in t.records:
        if len(r.fields) != 9 or not r.fields[CHAMP_ACTION]:
            continue
        if r.fields[CHAMP_CATEGORIE] >> 5 != origine[r.fields[CHAMP_PALIER]]:
            raise AssertionError("lien arme : palier %d marque %d, origine %d"
                                 % (r.fields[CHAMP_PALIER],
                                    r.fields[CHAMP_CATEGORIE] >> 5,
                                    origine[r.fields[CHAMP_PALIER]]))
        n += 1
    arm9 = cc.decompress(bytes(rom.arm9))
    for adr, _avant, apres in ARM9_SITES:
        if _desas(arm9[adr - BASE_ARM9:adr - BASE_ARM9 + 4], adr) != apres:
            raise AssertionError("lien arme : ARM9 %#010x non pose" % adr)
    o = rom.loadArm9Overlays()[OVL_COMBAT]
    for adr, _avant, apres in OVL0_SITES:
        a = adr - o.ramAddress
        if _desas(o.data[a:a + 4], adr) != apres:
            raise AssertionError("lien arme : overlay 0 %#010x non pose" % adr)
    return n
