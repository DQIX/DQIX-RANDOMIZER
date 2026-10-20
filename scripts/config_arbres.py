"""La categorie `arbres` de « Creer sa ROM » (ZER-91) : ce que donne chaque
palier des 26 arbres de competences, pour `config_rom`.

LES CASES. Les 286 places (arbre, cout) de `skilltable.bin`
(patch_aptitudes). Une case recoit une CHARGE, designee par l'identifiant
de palier du vanilla qui la porte (champ 0 : 183 = Attaque +30 avec la
hache) ; la charge voyage entiere, libelle, icone et message compris, comme
dans le tirage (`patch_aptitudes.ecrire_permutation`, octet pour octet).

AUCUNE REGLE : une charge peut revenir sur deux places, quitter son arbre,
une technique de livre aller sur un palier ordinaire. Le VERROU (levable,
ZER-51) : les 26 places a 0 point, celles des livres de competence, gardent
leur charge.

L'ecriture part toujours des trois fichiers vanilla (skilltable, sklname,
str_gskl) : `appliquer` demande la ROM d'origine. Avec
--aptitudes-arme-origine, l'arbre d'origine est remarque apres
(`patch_lien_arme.marquer`).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import patch_aptitudes as PA

FICHIERS = (PA.CHEMIN, PA.CHEMIN_NOMS, PA.CHEMIN_MESSAGES)


def _place(t, table, k, l):
    return t("place_palier", l.get("arbre_nom") or l["arbre"], l["cout"])


def _verrou(table, ligne_vanilla):
    return ligne_vanilla.get("cout") == 0


FORME = dict(tables=(("paliers", 286),), champs=(("palier", "palier"),),
             verrous=set(), verrou_ligne=_verrou, place=_place)


def interdits(rom):
    return set()


def _ordre(rom):
    """Les lignes de skilltable, par arbre puis cout (0 point a la fin)."""
    return sorted(PA.lignes(rom), key=lambda x: (
        x[1][PA.CHAMP_ARBRE], 1000 if x[1][PA.CHAMP_COUT] == 0
        else x[1][PA.CHAMP_COUT], x[0]))


def affiche(texte):
    """Un texte du jeu tel qu'il s'affiche, accents compris (la fenetre)."""
    import objets
    for balise, clair in (("<Cap>", ""), ("<%>", "%"), ("<u_arrow>", "↑")):
        texte = texte.replace(balise, clair)
    return objets.avec_accents(texte)


def noms_arbres(rom, langue="en"):
    return {a: affiche(n.decode("utf-8", "replace"))
            for a, n in PA._noms_arbres(rom, langue).items()}


def choisissables(rom, langue="en"):
    """[(identifiant de palier, libelle)] des charges du vanilla `rom`, dans
    l'ordre des arbres. Le libelle dit l'arbre d'origine : un bonus << avec >>
    y lit son arme."""
    aff = PA._libelles_affiches(rom, langue, affiche)
    arbres = noms_arbres(rom, langue)
    out = []
    for _i, f in _ordre(rom):
        a, c = f[PA.CHAMP_ARBRE], f[PA.CHAMP_COUT]
        out.append((f[PA.CHAMP_ID], "%s · %s %d" % (
            aff.get((a, c)) or "—", arbres.get(a, a), c)))
    return out


def exporter(rom, langue="en"):
    aff = PA._libelles_affiches(rom, langue, affiche)
    arbres = noms_arbres(rom, langue)
    return {"paliers": [{"arbre": f[PA.CHAMP_ARBRE],
                         "arbre_nom": arbres.get(f[PA.CHAMP_ARBRE], ""),
                         "cout": f[PA.CHAMP_COUT], "palier": f[PA.CHAMP_ID],
                         "nom": aff.get((f[PA.CHAMP_ARBRE], f[PA.CHAMP_COUT]),
                                        "")}
                        for _i, f in _ordre(rom)]}


def tirer_section(rom, graine, langue="en", chaos=False):
    import random
    PA.patcher(rom, random.Random(graine), chaos=chaos, langue=langue)
    return exporter(rom, langue)


def appliquer(rom, section, verrous=True, vanilla=None):
    from config_rom import ConfigInvalide
    ordre = _ordre(rom)
    lignes = section.get("paliers")
    if not isinstance(lignes, list) or len(lignes) != len(ordre):
        raise ConfigInvalide("arbres.paliers : %d cases attendues" % len(ordre))
    voulu = {}
    for k, (l, (i, f)) in enumerate(zip(lignes, ordre)):
        ou = "arbres.paliers[%d]" % k
        try:
            p, a, c = int(l["palier"]), int(l["arbre"]), int(l["cout"])
        except (KeyError, TypeError, ValueError):
            raise ConfigInvalide(ou + " : 'arbre', 'cout' et 'palier' entiers "
                                 "attendus")
        if (a, c) != (f[PA.CHAMP_ARBRE], f[PA.CHAMP_COUT]):
            raise ConfigInvalide(ou + " : arbre %d cout %d attendus"
                                 % (f[PA.CHAMP_ARBRE], f[PA.CHAMP_COUT]))
        if verrous and c == 0 and p != f[PA.CHAMP_ID]:
            raise ConfigInvalide(ou + " : la technique du livre de competence "
                                 "reste a sa place")
        voulu[i] = p
    if all(voulu[i] == f[PA.CHAMP_ID] for i, f in ordre):
        return 0
    if vanilla is None:
        raise ConfigInvalide("arbres : la ROM d'origine est necessaire")
    ligne_de = {f[PA.CHAMP_ID]: i for i, f in PA.lignes(vanilla)}
    for i in sorted(voulu):
        if voulu[i] not in ligne_de:
            raise ConfigInvalide("arbres : palier %d inconnu du jeu" % voulu[i])
    import patch_lien_arme
    lien = patch_lien_arme.pose(rom)
    for chemin in FICHIERS:
        rom.files[rom.filenames.idOf(chemin)] = bytes(
            vanilla.files[vanilla.filenames.idOf(chemin)])
    perm = {i: ligne_de[p] for i, p in voulu.items()}
    if any(a != d for a, d in perm.items()):
        PA.ecrire_permutation(rom, perm)
    if lien:
        patch_lien_arme.marquer(rom, vanilla)
    return sum(voulu[i] != f[PA.CHAMP_ID] for i, f in ordre)
