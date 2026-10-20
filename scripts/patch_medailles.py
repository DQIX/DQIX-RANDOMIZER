#!/usr/bin/env python3
"""Les recompenses du Capitaine Zac Amedai (mini medailles), ZER-55, 1.7.

OU ELLES SONT -- MESURE (research §103). Deux tables EN DUR dans l'overlay 4
(le menu du Capitaine), enregistrements de 4 octets : u16 nombre de
medailles, u16 objet (identifiant `itemdt`, comme objets.py).

    PALIERS   0x02170010, 10 entrees puis (0, 0). Le Capitaine donne l'objet
              d'un palier quand le TOTAL de medailles qu'on lui a remises
              l'atteint ; la boucle qui cherche le palier suivant est bornee
              a 10 en dur (`cmp r3, #0xa` en 0x021679B0).
                 4 clef de voleur (IMPORTANT)   8 foulard d'Hermes
                13 costume de lapin            18 mariniere
                25 collants transparents       32 epee miracle
                40 armure sacree               50 brassard de meteore
                62 heaume rouille              80 manteau du Dragon
    BOUTIQUE  0x0216FFF8, 6 entrees (ouverte apres le dernier palier) :
                 3 bague de priere    5 elixir elfique   8 cendres sacrees
                10 reinitialithe     15 orichalque      20 bottines lutines

Les textes (`data/bin/menu/str_mdl.gp2`) sont des gabarits : nombre et nom
d'objet viennent de ces tables, rien a reecrire.

DECISIONS DU JOUEUR (14-15/10/2026) :
  - paliers ET boutique randomises ;
  - les mini medailles restent RARES dans le loot (aucun loot fixe : « la
    difficulte sera d'en trouver ») -- en echange, SEUILS ET COUTS DIVISES
    PAR 4 (arrondi au plus proche, demi vers le haut, minimum 1). Regle
    d'equilibrage, donc en deux options : `--medailles-seuils-vanilla` garde
    les nombres du jeu ;
  - la regle des 4-5 etoiles (ZER-49) ne s'applique PAS chez le Capitaine.

TIRAGE. Mode equilibre : chaque objet est remplace par un objet a une etoile
pres de l'objet vanilla (`rarete.rouge`). Mode chaos : n'importe quel objet
du pool. Toujours : la clef de voleur reste a son palier (objet important) ;
pool = `objets.pool` moins la mini medaille ; 16 objets tous differents
(15 tires, la clef reste).
Generateur a part, derive de la graine : rien d'autre ne bouge.
"""
import os
import random
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import objets
import rarete

OVL = 4
PALIERS = 0x02170010
NB_PALIERS = 10
BOUTIQUE = 0x0216FFF8
NB_BOUTIQUE = 6
MINI_MEDAILLE = 22039
CLEF_VOLEUR = 22042

# Le vanilla, pour reconnaitre l'overlay avant d'y ecrire.
VANILLA_PALIERS = ((4, 22042), (8, 12415), (13, 13606), (18, 13040),
                   (25, 16222), (32, 20017), (40, 13189), (50, 18014),
                   (62, 12187), (80, 13310))
VANILLA_BOUTIQUE = ((3, 18023), (5, 22017), (8, 22080), (10, 22107),
                    (15, 22076), (20, 17170))
DIVISEUR = 4


def diviser(n):
    """n / 4 arrondi au plus proche (demi vers le haut), au moins 1."""
    return max(1, (n * 2 + DIVISEUR) // (2 * DIVISEUR))


def _table(d, base, adr, nb):
    return [struct.unpack_from("<HH", d, adr - base + 4 * i) for i in range(nb)]


def lire(rom):
    """Rend (paliers, boutique) : listes de (nombre de medailles, objet)."""
    o = rom.loadArm9Overlays()[OVL]
    d = o.data
    return (_table(d, o.ramAddress, PALIERS, NB_PALIERS),
            _table(d, o.ramAddress, BOUTIQUE, NB_BOUTIQUE))


def patcher(rom, seed, chaos=False, seuils_vanilla=False, langue="en",
            journal=None):
    """Tire les objets, divise les nombres. Rend un dictionnaire de comptes."""
    import ndspy.code

    def note(ligne=""):
        if journal is not None:
            journal.write(ligne + "\n")

    ovl = rom.loadArm9Overlays()
    o = ovl[OVL]
    d = bytearray(o.data)
    base = o.ramAddress
    paliers = _table(d, base, PALIERS, NB_PALIERS)
    boutique = _table(d, base, BOUTIQUE, NB_BOUTIQUE)
    if (tuple(map(tuple, paliers)) != VANILLA_PALIERS
            or tuple(map(tuple, boutique)) != VANILLA_BOUTIQUE
            or struct.unpack_from("<I", d, PALIERS - base + 4 * NB_PALIERS)[0]):
        raise SystemExit("overlay 4 : tables du Capitaine inattendues "
                         "(deja patche ?)")

    rng = random.Random("medailles:%d" % seed)
    etoiles = objets.raretes(rom)
    pool = [i for i in objets.pool(rom) if i != MINI_MEDAILLE]
    pris = {CLEF_VOLEUR}

    def tirer(vanilla):
        if vanilla == CLEF_VOLEUR:
            return CLEF_VOLEUR
        bande = rarete.TOUTES if chaos else rarete.rouge(etoiles.get(vanilla, 0))
        cand = [i for i in pool if i not in pris and etoiles.get(i, 0) in bande]
        choix = rng.choice(cand)
        pris.add(choix)
        return choix

    neufs_p = [((n if seuils_vanilla else diviser(n)), tirer(i))
               for n, i in paliers]
    neufs_b = [((n if seuils_vanilla else diviser(n)), tirer(i))
               for n, i in boutique]
    _ecrire_tables(rom, neufs_p, neufs_b)

    nm = objets.noms(rom, langue)
    note("=== CAPITAINE ZAC AMEDAI (mini medailles) ===")
    note("mode : %s ; nombres de medailles : %s"
         % ("chaos" if chaos else "equilibre (+/-1 etoile)",
            "vanilla" if seuils_vanilla else "divises par 4"))
    for titre, avant, apres in (("paliers", paliers, neufs_p),
                                ("boutique", boutique, neufs_b)):
        note("  %s" % titre)
        for (n0, i0), (n1, i1) in zip(avant, apres):
            note("    %3d -> %3d  %-28s -> %s"
                 % (n0, n1, nm.get(i0, i0), nm.get(i1, i1)))
    return dict(paliers=len(neufs_p), boutique=len(neufs_b))


def _ecrire_tables(rom, paliers, boutique):
    """Ecrit les deux tables telles quelles. Rend le nombre de cases
    changees ; ne recompresse pas l'overlay si rien ne change (la
    recompression ne rend pas les octets d'origine)."""
    import ndspy.code
    ovl = rom.loadArm9Overlays()
    o = ovl[OVL]
    d = bytearray(o.data)
    base = o.ramAddress
    avant = _table(d, base, PALIERS, NB_PALIERS) + _table(d, base, BOUTIQUE, NB_BOUTIQUE)
    for adr, table in ((PALIERS, paliers), (BOUTIQUE, boutique)):
        for k, (n, i) in enumerate(table):
            struct.pack_into("<HH", d, adr - base + 4 * k, n, i)
    changes = sum(a != tuple(b) for a, b in zip(avant, list(paliers) + list(boutique)))
    if changes:
        o.data = bytes(d)
        rom.files[o.fileID] = o.save(compress=True)
        rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovl)
    return changes


# --- affectation explicite (config_rom, ZER-85) -----------------------------

# LA FORME DE LA SECTION, pour l'onglet « Creer sa ROM » (ZER-87) : ses
# tables, le nombre de cases de chacune, le type de chaque champ, et les cases
# que le joueur ne peut pas changer (ce qui empeche de finir le jeu).
FORME = dict(tables=(("paliers", NB_PALIERS), ("boutique", NB_BOUTIQUE)),
             champs=(("medailles", "nombre"), ("objet", "objet")),
             verrous={("paliers", 0, "objet")})


def interdits(rom):
    """Les objets qu'aucune case ne peut recevoir (la clef reste a sa place)."""
    return (objets.objets_importants(rom) | objets.HORS_TIRAGE) - {CLEF_VOLEUR}


def tirer_section(rom, graine, langue="en", chaos=False, seuils_vanilla=False):
    """Tire la categorie seule sur `rom` (vanilla) et rend sa section."""
    patcher(rom, graine, chaos=chaos, seuils_vanilla=seuils_vanilla)
    return exporter(rom, langue)


def exporter(rom, langue="en"):
    """La section `capitaine` du fichier de configuration, lue dans la ROM."""
    nm = objets.noms(rom, langue, accents=True)
    paliers, boutique = lire(rom)
    return {t: [{"medailles": n, "objet": i, "nom": nm.get(i, "")}
                for n, i in table]
            for t, table in (("paliers", paliers), ("boutique", boutique))}


def appliquer(rom, section, verrous=True, vanilla=None):
    """Ecrit la section `capitaine`. Leve config_rom.ConfigInvalide si une
    case ne tient pas dans le format du jeu ; avec `verrous` (le defaut), aussi
    si elle empeche de finir le jeu. Aucune regle d'equilibrage (joueur,
    19/10/2026). Rend le nombre de cases changees."""
    from config_rom import ConfigInvalide
    cat = objets.catalogue(rom)
    refuses = interdits(rom) if verrous else set()
    nm = objets.noms(rom, "en")
    tables = {}
    for t, nb in (("paliers", NB_PALIERS), ("boutique", NB_BOUTIQUE)):
        lignes = section.get(t)
        if not isinstance(lignes, list) or len(lignes) != nb:
            raise ConfigInvalide("capitaine.%s : %d cases attendues" % (t, nb))
        out = []
        for k, l in enumerate(lignes):
            ou = "capitaine.%s[%d]" % (t, k)
            try:
                n, i = int(l["medailles"]), int(l["objet"])
            except (KeyError, TypeError, ValueError):
                raise ConfigInvalide(ou + " : 'medailles' et 'objet' entiers attendus")
            # 0 n'est pas un nombre : c'est la fin de table (0, 0) du jeu
            if not 1 <= n <= 0xFFFF:
                raise ConfigInvalide(ou + " : %d medailles, hors de 1..65535" % n)
            if i not in cat:
                raise ConfigInvalide(ou + " : objet %d inconnu du jeu" % i)
            if i in refuses:
                raise ConfigInvalide(ou + " : %s est un objet de quete ou de "
                                     "debug, il casserait la partie" % nm.get(i, i))
            out.append((n, i))
        tables[t] = out
    p = tables["paliers"]
    if not verrous:
        return _ecrire_tables(rom, p, tables["boutique"])
    # Structure, pas equilibre : le jeu cherche le palier suivant dans
    # l'ordre, et la clef de voleur ouvre des portes de l'histoire.
    if any(b[0] <= a[0] for a, b in zip(p, p[1:])):
        raise ConfigInvalide("capitaine.paliers : les nombres de medailles "
                             "doivent croitre strictement (%s)"
                             % ", ".join(str(n) for n, _ in p))
    if p[0][1] != CLEF_VOLEUR or any(i == CLEF_VOLEUR for _, i in p[1:] + tables["boutique"]):
        raise ConfigInvalide("capitaine.paliers[0] : la clef de voleur reste "
                             "au premier palier, et seulement la")
    return _ecrire_tables(rom, p, tables["boutique"])


def verifier(rom, chaos=False, seuils_vanilla=False):
    """Leve si les tables ne suivent pas les regles. Rend (paliers, boutique)."""
    paliers, boutique = lire(rom)
    etoiles = objets.raretes(rom)
    pool = set(objets.pool(rom)) - {MINI_MEDAILLE}
    attendu_p = [n if seuils_vanilla else diviser(n) for n, _ in VANILLA_PALIERS]
    attendu_b = [n if seuils_vanilla else diviser(n) for n, _ in VANILLA_BOUTIQUE]
    if [n for n, _ in paliers] != attendu_p:
        raise ValueError("paliers : nombres %s, attendus %s"
                         % ([n for n, _ in paliers], attendu_p))
    if [n for n, _ in boutique] != attendu_b:
        raise ValueError("boutique : nombres %s, attendus %s"
                         % ([n for n, _ in boutique], attendu_b))
    if any(b <= a for a, b in zip(attendu_p, attendu_p[1:])):
        raise ValueError("paliers : nombres non strictement croissants")
    if paliers[0][1] != CLEF_VOLEUR:
        raise ValueError("la clef de voleur n'est plus au premier palier")
    objs = [i for _, i in paliers + boutique]
    if len(set(objs)) != len(objs):
        raise ValueError("un objet du Capitaine est en double")
    vanilla = [i for _, i in VANILLA_PALIERS + VANILLA_BOUTIQUE]
    for i, v in zip(objs, vanilla):
        if v == CLEF_VOLEUR:
            continue
        if i not in pool:
            raise ValueError("objet %d hors du pool (ou mini medaille)" % i)
        if not chaos and etoiles.get(i, 0) not in rarete.rouge(etoiles.get(v, 0)):
            raise ValueError("objet %d : %d etoiles pour un vanilla a %d"
                             % (i, etoiles.get(i, 0), etoiles.get(v, 0)))
    return paliers, boutique


if __name__ == "__main__":
    import ndspy.rom
    from rom_vanilla import chemin_vanilla
    rom = ndspy.rom.NintendoDSRom.fromFile(
        sys.argv[1] if len(sys.argv) > 1 else chemin_vanilla())
    nm = objets.noms(rom, "fr")
    p, b = lire(rom)
    print("paliers  :", ", ".join("%d %s" % (n, nm.get(i, i)) for n, i in p))
    print("boutique :", ", ".join("%d %s" % (n, nm.get(i, i)) for n, i in b))
