#!/usr/bin/env python3
"""Le fichier de configuration d'une ROM : l'affectation EXPLICITE de ce que
le randomizer sait changer, case par case (ZER-81 / ZER-85, 1.7).

POURQUOI. L'onglet « Creer sa ROM » laisse le joueur choisir chaque case a la
main, puis partager son choix dans un fichier. Decision du joueur (19/10/2026) :
le fichier ECRIT TOUT -- chaque case avec son identifiant et son nom lisible --
et ne depend donc ni de la graine ni de la facon dont une version tire. La meme
config donne la meme ROM.

DEUX SENS, une seule verite : la ROM.
  exporter  lit l'affectation dans une ROM deja construite (`--exporter-config`).
            On ne rejoue pas le tirage : on relit ce qu'il a ecrit.
  appliquer ecrit une affectation dans la ROM (`--config`), APRES tous les
            tirages. Le tirage d'une categorie a donc deja consomme son
            generateur : remplacer une categorie ne decale aucune autre.

Preuve (contrôle `config_aller_retour` de la matrice) : une ROM, sa config
exportee, puis la meme commande avec `--config` -> la meme ROM, octet pour
octet ; et une ROM vanilla + `--config` -> les memes cases.

REGLES. Une affectation explicite n'est soumise a AUCUNE regle d'equilibrage,
ZER-49 comprise (joueur, 19/10/2026). `appliquer` ne refuse que ce qui empeche
de finir le jeu ou ce que le format du jeu ne peut pas porter, et dit quelle
case.

FORMAT (JSON, UTF-8) :
    {
      "format": 1,
      "rom": "YDQP",
      "randomizer": "<commande qui a produit la ROM, pour memoire>",
      "langue": "fr",
      "<categorie>": { ... }       une cle par categorie, voir CATEGORIES
    }
Une categorie absente du fichier garde ce que les options ont produit.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

FORMAT = 1
SERIE = "YDQP"
# `figees` : les cases que le joueur a epinglees dans l'onglet, pour les
# retrouver en rouvrant le fichier. N'agit pas sur la ROM.
# `verrous` (vrai par defaut) : refuser ce qui empeche de finir le jeu. Faux,
# seul le format du jeu limite les cases (joueur, 19/10/2026 : les verrous se
# levent, mais sont la par defaut).
ENTETE = ("format", "rom", "randomizer", "langue", "figees", "verrous")


class ConfigInvalide(ValueError):
    """Un fichier qu'on refuse, avec la raison et la case."""


def _categories():
    """{nom: module} des categories que le fichier sait porter, dans l'ordre
    ou elles s'appliquent. Chaque module fournit FORME, interdits(rom),
    exporter(rom, langue) -> section, tirer_section(rom, graine, langue,
    **options) et appliquer(rom, section, verrous, vanilla) -> nombre de
    cases changees ; appliquer leve ConfigInvalide."""
    import config_actions
    import config_alchimie
    import config_arbres
    import config_boss
    import config_boutiques
    import config_butin
    import config_coffres
    import config_grottes
    import config_monstres
    import config_points
    import config_sorts
    import config_stats
    import config_vocations
    import patch_medailles
    return {"capitaine": patch_medailles, "boss": config_boss,
            "boutiques": config_boutiques, "coffres": config_coffres,
            "grottes": config_grottes, "points": config_points,
            "alchimie": config_alchimie,
            "arbres": config_arbres, "sorts": config_sorts,
            "vocations": config_vocations, "monstres": config_monstres,
            "butin": config_butin, "stats": config_stats,
            "actions": config_actions}


CATEGORIES = ("capitaine", "boss", "boutiques", "coffres", "grottes",
              "points", "alchimie", "arbres", "sorts", "vocations", "monstres", "butin",
              "stats", "actions")


def exporter(rom, langue="en", commande=""):
    """Rend la configuration complete lue dans `rom`."""
    cfg = {"format": FORMAT, "rom": SERIE, "randomizer": commande,
           "langue": langue}
    for nom, mod in _categories().items():
        cfg[nom] = mod.exporter(rom, langue)
    return cfg


def _texte(v, retrait=0):
    """JSON lisible : un objet sur plusieurs lignes, mais UNE CASE PAR LIGNE
    (un element de liste tient sur sa ligne)."""
    if isinstance(v, dict) and v:
        pas = " " * (retrait + 1)
        return "{\n" + ",\n".join(
            pas + json.dumps(k, ensure_ascii=False) + ": " + _texte(x, retrait + 1)
            for k, x in v.items()) + "\n" + " " * retrait + "}"
    if isinstance(v, list) and v:
        pas = " " * (retrait + 1)
        return "[\n" + ",\n".join(
            pas + json.dumps(x, ensure_ascii=False) for x in v) + "\n" + " " * retrait + "]"
    return json.dumps(v, ensure_ascii=False)


def ecrire(chemin, cfg):
    os.makedirs(os.path.dirname(os.path.abspath(chemin)), exist_ok=True)
    with open(chemin, "w", encoding="utf-8", newline="\n") as f:
        f.write(_texte(cfg) + "\n")


def lire(chemin):
    """Lit et controle l'en-tete. Leve ConfigInvalide."""
    try:
        with open(chemin, encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, ValueError) as e:
        raise ConfigInvalide("fichier illisible : %s" % e)
    if not isinstance(cfg, dict):
        raise ConfigInvalide("le fichier n'est pas un objet JSON")
    if cfg.get("format") != FORMAT:
        raise ConfigInvalide("format %r, ce randomizer lit le format %d"
                             % (cfg.get("format"), FORMAT))
    if cfg.get("rom") != SERIE:
        raise ConfigInvalide("config pour la ROM %r, pas %s"
                             % (cfg.get("rom"), SERIE))
    inconnues = sorted(set(cfg) - set(ENTETE) - set(CATEGORIES))
    if inconnues:
        raise ConfigInvalide("categories inconnues de cette version : %s"
                             % ", ".join(inconnues))
    return cfg


def forme(categorie):
    """La forme d'une section (tables, champs, cases verrouillees)."""
    return _categories()[categorie].FORME


def tirer(categorie, rom, graine, langue="en", **options):
    """Tire UNE categorie sur `rom`, qui doit etre la vanilla (elle est
    modifiee), avec une graine a part. Rend sa section."""
    section = _categories()[categorie].tirer_section(rom, graine, langue,
                                                     **options)
    import bestiaire
    bestiaire.accorder(rom, None)       # `rom` etait la vanilla (ZER-95)
    return section


def objets_choisissables(rom, langue="en", categorie=None, verrous=True):
    """[(identifiant, nom, type, etoiles)] des objets qu'une case peut
    recevoir, tries par nom. `type` : w s b u h a l d (equipement, comme
    objets.CATEGORIES) ou t (objet courant). Sans verrous : tous."""
    import objets
    nm = objets.noms(rom, langue, accents=True)
    cat = objets.catalogue(rom, langue)
    et = objets.raretes(rom, langue)
    exclus = (set() if not verrous
              else _categories()[categorie].interdits(rom) if categorie
              else objets.objets_importants(rom, langue) | objets.HORS_TIRAGE)
    return sorted(((i, nm.get(i, str(i)), cat[i][0], et.get(i, 0))
                   for i in cat if i not in exclus),
                  key=lambda x: x[1].lower())


def especes_choisissables(rom, langue="en", verrous=True):
    """[(identifiant, nom, genre)] des especes qu'une case de boss peut
    recevoir (config_boss)."""
    import config_boss
    return config_boss.especes_choisissables(rom, langue, verrous)


def interdits(categorie, rom):
    """Ce qu'aucune case de la categorie ne recoit tant que les verrous
    tiennent."""
    return _categories()[categorie].interdits(rom)


def sorts_choisissables(rom, langue="en"):
    import config_sorts
    return config_sorts.choisissables(rom, langue)


def paliers_choisissables(rom, langue="en"):
    import config_arbres
    return config_arbres.choisissables(rom, langue)


def monstres_choisissables(rom, langue="en"):
    """[(identifiant, texte)] des especes qu'une case de monstre du terrain
    peut recevoir (config_monstres)."""
    import config_monstres
    return config_monstres.choisissables(rom, langue)


def actions_choisissables(rom, langue="en"):
    """[(identifiant, texte)] des actions qu'une case d'action de monstre
    peut recevoir (config_actions)."""
    import config_actions
    return config_actions.choisissables(rom, langue)


def vocations(rom, langue="en"):
    import config_vocations
    return config_vocations.noms(rom, langue)


def appliquer(rom, cfg, vanilla=None, graine=0):
    """Ecrit chaque categorie presente. Rend {categorie: cases changees}.

    `vanilla` : la ROM d'origine. Certaines categories (arbres, vocations,
    prix des boutiques) reecrivent depuis ses octets : sans elle, elles
    refusent ce qu'elles ne savent pas defaire. `graine` : celle de la
    construction, pour les cases qui se tirent a la construction (le mode
    tire des stats)."""
    out = {}
    verrous = cfg.get("verrous", True) is not False
    for nom, mod in _categories().items():
        if nom in cfg:
            if not isinstance(cfg[nom], dict):
                raise ConfigInvalide("%s : objet attendu" % nom)
            extra = {"graine": graine} if nom == "stats" else {}
            out[nom] = mod.appliquer(rom, cfg[nom], verrous=verrous,
                                     vanilla=vanilla, **extra)
    # LA FICHE DU BESTIAIRE suit le butin que la config laisse (ZER-95)
    import bestiaire
    bestiaire.accorder(rom, vanilla)
    return out


if __name__ == "__main__":
    # python scripts/config_rom.py <rom.nds> [sortie.json]  : exporter une ROM
    import ndspy.rom
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    cfg = exporter(rom, "fr", "export de %s" % os.path.basename(sys.argv[1]))
    if len(sys.argv) > 2:
        ecrire(sys.argv[2], cfg)
        print("ecrit :", sys.argv[2])
    else:
        print(json.dumps(cfg, ensure_ascii=False, indent=1))
