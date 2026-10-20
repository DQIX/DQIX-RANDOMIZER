"""La categorie `stats` de « Creer sa ROM » (ZER-58) : les statistiques des
monstres (patch_stats), pour `config_rom`.

LES CASES. Quatre tables, une ligne par fiche de `mon_moddata` (438, boss
compris) :
  valeurs      `mode` (fixe : les cinq valeurs de la ligne ; tire : une
               valeur tiree dans la plage de la table `plages`, a la
               construction ; combat : retiree dans la plage A CHAQUE COMBAT,
               ZER-96), puis PV, PM, attaque, defense, agilite ;
  plages       min et max de chaque stat, pour les modes tire et combat
               (pre-remplis avec la plage bornee : x0,5 a x2 de la valeur
               d'origine ; en mode combat, celles que la ROM porte) ;
  elements     les 7 resistances aux elements (e1..e7, l'ordre du fichier) ;
  alterations  les 14 resistances aux alterations d'etat (a1..a14).
Chaque case est ecrite dans mon_moddata (lu par le combat) ET dans
mon_btldata, identiques (patch_stats.ecrire). Les resistances sont des
valeurs (le bouton « Tirer » les tire, a un cran ou en chaos).

Decision du joueur (20/10/2026) : monstre par monstre, tous ou certains ;
les plages se reglent quand un monstre est tire, et ce qui ne sert pas est
grise (les valeurs d'un monstre tire, les plages d'un monstre fixe).

LE TIRAGE DU MODE TIRE se fait a la construction, avec la graine de la
construction (`graine`) : meme config et meme graine, meme ROM. Le fichier
relu d'une ROM ne porte que des valeurs (mode fixe) : elles redonnent la
meme ROM.

LE VERROU (levable) : les deux especes du combat du prologue, Aquila et
Corvus des cinematiques et le mannequin du tutoriel gardent leurs valeurs
(le randomizer ne les tire jamais, patch_stats.VERROUILLES). LES LIMITES DU
FORMAT : une stat tient sur 16 bits (0..65535), une resistance sur 8 bits
(0..255) ; un min ne depasse pas son max.
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import patch_stats as PS

TABLES = ("valeurs", "plages", "elements", "alterations")
MODES = ("fixe", "tire", "combat")
ELEMENTS = tuple("e%d" % (k + 1) for k in range(PS.NB_ELEM))
ALTERATIONS = tuple("a%d" % (k + 1) for k in range(PS.NB_ALT))
BORNES = tuple(c for s in PS.STATS for c in (s + "_min", s + "_max"))
CHAMPS = {"valeurs": PS.STATS, "plages": BORNES, "elements": ELEMENTS,
          "alterations": ALTERATIONS}


def _place(t, table, k, l):
    return l.get("monstre_nom") or "#%d" % l["monstre"]


def _tire(section, k):
    """Le monstre prend ses stats dans ses plages (tire ou combat)."""
    try:
        return section["valeurs"][k]["mode"] != "fixe"
    except (KeyError, IndexError, TypeError):
        return False


def _ligne_grise(section, table, k):
    """Les plages d'un monstre fixe ne servent pas."""
    return table == "plages" and not _tire(section, k)


def _case_grise(section, table, k, champ):
    """Les valeurs d'un monstre tire ne servent pas."""
    return table == "valeurs" and champ in PS.STATS and _tire(section, k)


_bornes = {s: (0, 0xFFFF) for s in PS.STATS + BORNES}
_bornes["pv"] = _bornes["pv_min"] = _bornes["pv_max"] = (1, 0xFFFF)
_bornes.update((c, (0, 255)) for c in ELEMENTS + ALTERATIONS)

FORME = dict(tables=tuple((t, None) for t in TABLES),
             champs=(("mode", "mode_stats"),)
             + tuple((c, "nombre") for t in TABLES for c in CHAMPS[t]),
             verrous=set(), place=_place, bornes=_bornes, aide="aide_stats",
             verrou_ligne=lambda table, l: bool(l.get("verrou")),
             ligne_grise=_ligne_grise, case_grise=_case_grise,
             grise="creer_grise_stats")


def interdits(rom):
    return set()


def _vanilla():
    import ndspy.rom
    from rom_vanilla import chemin_vanilla
    return PS.lire(ndspy.rom.NintendoDSRom.fromFile(chemin_vanilla()))


def exporter(rom, langue="en"):
    import config_actions
    noms = config_actions._noms_monstres(langue)
    garde = PS.verrouilles(rom)
    van = _vanilla()
    combat = PS.lire_plages(rom)
    sec = {t: [] for t in TABLES}
    for i, f in enumerate(PS.lire(rom)):
        base = {"monstre": i, "monstre_nom": noms.get(i, "")}
        if i in garde:
            base["verrou"] = True
        sec["valeurs"].append(dict(base, mode="combat" if combat[i] else "fixe",
                                   **{s: f[s] for s in PS.STATS}))
        pl = {}
        for s in PS.STATS:
            pl[s + "_min"], pl[s + "_max"] = (combat[i][s] if combat[i] else
                                              PS.plage_bornee(s, van[i][s]))
        sec["plages"].append(dict(base, **pl))
        sec["elements"].append(dict(base, **dict(zip(ELEMENTS,
                                                     f["elements"]))))
        sec["alterations"].append(dict(base, **dict(zip(ALTERATIONS,
                                                        f["alterations"]))))
    return sec


def tirer_section(rom, graine, langue="en", chaos=False, combat=False):
    """Comme --stats / --stats-chaos / --stats-combat."""
    PS.patcher(rom, graine, chaos=chaos)
    if combat:
        PS.patcher_combat(rom, chaos=chaos)
    return exporter(rom, langue)


def generateur(graine):
    """Le generateur du mode tire (a part de celui de --stats)."""
    return random.Random("stats:config:%d" % graine)


def appliquer(rom, section, verrous=True, vanilla=None, graine=0):
    """Ecrit les cases des tables presentes, tire les monstres en mode tire.
    Rend le nombre de fiches changees."""
    from config_rom import ConfigInvalide
    fiches = PS.lire(rom)
    avant = [dict(f, elements=list(f["elements"]),
                  alterations=list(f["alterations"])) for f in fiches]
    combat_avant = PS.lire_plages(rom)
    combat = list(combat_avant)
    garde = PS.verrouilles(rom) if verrous else frozenset()
    lus = {}
    for table in TABLES:
        if table not in section:
            continue
        lignes = section[table]
        if not isinstance(lignes, list) or len(lignes) != len(fiches):
            raise ConfigInvalide("stats.%s : %d lignes attendues (une par "
                                 "fiche)" % (table, len(fiches)))
        haut = 255 if table in ("elements", "alterations") else 0xFFFF
        lus[table] = []
        for j, l in enumerate(lignes):
            ou = "stats.%s[%d]" % (table, j)
            try:
                i = int(l["monstre"])
                vals = [int(l[c]) for c in CHAMPS[table]]
            except (KeyError, TypeError, ValueError):
                raise ConfigInvalide(ou + " : 'monstre' et %s entiers attendus"
                                     % ", ".join(CHAMPS[table]))
            if i != j:
                raise ConfigInvalide(ou + " : fiche %d, attendu %d" % (i, j))
            if any(not 0 <= v <= haut for v in vals):
                raise ConfigInvalide(ou + " : valeur hors de 0..%d" % haut)
            if table == "valeurs" and l.get("mode", "fixe") not in MODES:
                raise ConfigInvalide(ou + " : mode %r, attendu %s"
                                     % (l.get("mode"), ", ".join(MODES)))
            if table == "plages" and any(a > b for a, b in
                                         zip(vals[::2], vals[1::2])):
                raise ConfigInvalide(ou + " : un min depasse son max")
            lus[table].append((l.get("mode", "fixe"), vals))
    rng = generateur(graine)
    for i, f in enumerate(fiches):
        neuf = dict(f)
        if "valeurs" in lus:
            mode, vals = lus["valeurs"][i]
            if mode != "fixe" and "plages" not in lus:
                raise ConfigInvalide("stats.valeurs[%d] : mode %s sans table "
                                     "'plages'" % (i, mode))
            pl = ({s: (lus["plages"][i][1][2 * k], lus["plages"][i][1][2 * k + 1])
                   for k, s in enumerate(PS.STATS)} if mode != "fixe" else None)
            if mode == "tire":
                neuf.update(PS.tirer_dans(rng, pl))
            else:
                neuf.update(zip(PS.STATS, vals))
            if mode == "combat" and pl["pv"][0] < 1:
                raise ConfigInvalide("stats.plages[%d] : PV min au moins 1" % i)
            if pl is not None and mode == "combat" and i in garde:
                raise ConfigInvalide("stats[%d] : combat du prologue, "
                                     "cinematique ou mannequin, pas de tirage "
                                     "a chaque combat tant que les verrous "
                                     "tiennent" % i)
            combat[i] = pl if mode == "combat" else None
        for table in ("elements", "alterations"):
            if table in lus:
                neuf[table] = lus[table][i][1]
        if neuf != f and i in garde:
            raise ConfigInvalide("stats[%d] : combat du prologue, cinematique "
                                 "ou mannequin, ses stats restent celles du "
                                 "jeu tant que les verrous tiennent" % i)
        fiches[i] = neuf
    if fiches == avant and combat == combat_avant:
        return 0
    n = PS.ecrire(rom, fiches)
    if combat != combat_avant:
        PS.ecrire_plages(rom, combat)
        n += sum(a != b for a, b in zip(combat, combat_avant))
        if any(combat):
            PS.poser_combat(rom)
        else:
            PS.retirer_combat(rom)
    return max(n, 1)
