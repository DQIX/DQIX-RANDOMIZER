"""La categorie `vocations` de « Creer sa ROM » (ZER-91) : les quatre leviers
de patch_vocations, pour `config_rom`.

LES CASES, une ligne par reglage :
  depart     la vocation de depart du heros (1 a 12 ; 6, troubadour, en
             vanilla), un immediat de l'overlay 17 ;
  ouvertes   les douze vocations chez le pere Blaise des le debut ;
  embauche   une vocation tiree a chaque recrue de Tulipe ;
  bloquees   changer de vocation refuse (la renouvocation reste ouverte).

Les leviers sont du code : les retirer d'une ROM qui les porte demande les
octets d'origine (`vanilla`). Un fichier, overlay ou archive, qui revient a
son etat vanilla reprend les OCTETS vanilla : la recompression ne les rend
pas, et la meme config doit rendre la meme ROM. Aucun verrou.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import patch_vocations as PV

REGLAGES = ("depart", "ouvertes", "embauche", "bloquees")


def _place(t, table, k, l):
    return t("reglage_" + l["reglage"])


FORME = dict(tables=(("reglages", len(REGLAGES)),),
             champs=(("vocation", "vocation"), ("actif", "booleen")),
             verrous=set(), place=_place)


def interdits(rom):
    return set()


def noms(rom, langue="en"):
    """{vocation 1..12: nom affiche}, lus dans les textes du bar de Tulipe
    (chaines 0x12-0x1D de `bm_lui`, que le randomizer ne touche jamais)."""
    import objets
    import textes_dq9
    m = objets._membre_archive(rom, PV.CHEMIN_BAR, "bm_lui_%s.bin" % langue)
    c = textes_dq9.chaines_table(m)
    return {v: objets.avec_accents(c.get(0x11 + v, b"").decode("utf-8",
                                                               "replace"))
            for v in range(1, 13)}


def lire(rom):
    """{reglage: valeur} lu dans la ROM."""
    from patch_hasard import assembler
    ovl = rom.loadArm9Overlays()
    o17, o3, o9 = ovl[PV.OVL_DEPART], ovl[PV.OVL_ABBAYE], ovl[PV.OVL_TULIPE]
    dep = PV._desas(o17.data, o17.ramAddress, PV.SITE_DEPART)
    if not dep.startswith("mov r2, #"):
        raise ValueError("overlay 17 : %r en %#010x" % (dep, PV.SITE_DEPART))
    bloc = assembler(PV._lignes_bloque(), PV.BLOC_REFUS)
    z = PV.BLOC_REFUS - o3.ramAddress
    return dict(
        depart=int(dep[len("mov r2, #"):], 0),
        ouvertes=PV._desas(o3.data, o3.ramAddress, PV.SITE_ABBAYE) == "mov r0, #1",
        embauche=PV._desas(o9.data, o9.ramAddress, PV.SITE_TULIPE)
        == "b #%#x" % PV.ZONE_TULIPE,
        bloquees=bytes(o3.data[z:z + len(bloc)]) == bloc)


def exporter(rom, langue="en"):
    v = lire(rom)
    nm = noms(rom, langue)
    return {"reglages": [{"reglage": "depart", "vocation": v["depart"],
                          "nom": nm.get(v["depart"], "")}]
            + [{"reglage": r, "actif": v[r]} for r in REGLAGES[1:]]}


def tirer_section(rom, graine, langue="en", ouvertes=False, embauche=False,
                  bloquees=False, depart=False):
    PV.patcher(rom, ouvrir=ouvertes, embauche=embauche, bloquer=bloquees,
               depart=PV.tirer_depart(graine) if depart else None,
               bavard=False)
    return exporter(rom, langue)


def _remettre(rom, vanilla, ovl, n, sites):
    """Rend a l'overlay `n` les octets vanilla des plages `sites`
    [(adresse, longueur)]."""
    van = vanilla.loadArm9Overlays()[n]
    o = ovl[n]
    d = bytearray(o.data)
    for adr, lg in sites:
        z = adr - o.ramAddress
        d[z:z + lg] = van.data[z:z + lg]
    o.data = bytes(d)


def _fichier_vanilla(rom, vanilla, chemin):
    rom.files[rom.filenames.idOf(chemin)] = bytes(
        vanilla.files[vanilla.filenames.idOf(chemin)])


def appliquer(rom, section, verrous=True, vanilla=None):
    from config_rom import ConfigInvalide
    from patch_hasard import assembler
    lignes = section.get("reglages")
    if not isinstance(lignes, list) or [l.get("reglage") for l in lignes
                                        if isinstance(l, dict)] != list(REGLAGES):
        raise ConfigInvalide("vocations.reglages : les lignes %s attendues"
                             % ", ".join(REGLAGES))
    voulu = {}
    try:
        voulu["depart"] = int(lignes[0]["vocation"])
        for l in lignes[1:]:
            if not isinstance(l["actif"], bool):
                raise TypeError
            voulu[l["reglage"]] = l["actif"]
    except (KeyError, TypeError, ValueError):
        raise ConfigInvalide("vocations.reglages : 'vocation' entier et "
                             "'actif' vrai ou faux attendus")
    if not 1 <= voulu["depart"] <= 12:
        raise ConfigInvalide("vocations.reglages[0] : vocation %d, hors de "
                             "1..12" % voulu["depart"])
    actuel = lire(rom)
    changes = [r for r in REGLAGES if voulu[r] != actuel[r]]
    if not changes:
        return 0
    retirer = [r for r in REGLAGES[1:] if actuel[r] and not voulu[r]]
    if retirer and vanilla is None:
        raise ConfigInvalide("vocations : la ROM d'origine est necessaire "
                             "pour retirer %s" % ", ".join(retirer))
    ovl = rom.loadArm9Overlays()
    touches = set()
    if voulu["depart"] != actuel["depart"]:
        o = ovl[PV.OVL_DEPART]
        d = bytearray(o.data)
        z = PV.SITE_DEPART - o.ramAddress
        d[z:z + 4] = assembler(["mov r2, #%d" % voulu["depart"]], PV.SITE_DEPART)
        o.data = bytes(d)
        touches.add(PV.OVL_DEPART)
    if "ouvertes" in retirer:
        _remettre(rom, vanilla, ovl, PV.OVL_ABBAYE, [(PV.SITE_ABBAYE, 4)])
        touches.add(PV.OVL_ABBAYE)
    if "bloquees" in retirer:
        lg = len(assembler(PV._lignes_bloque(), PV.BLOC_REFUS))
        _remettre(rom, vanilla, ovl, PV.OVL_ABBAYE,
                  [(PV.BLOC_REFUS, lg)] + [(s, 4) for s in PV.SITES_VOIX]
                  + [(s + 16, 4) for s in PV.SITES_VOIX])
        _fichier_vanilla(rom, vanilla, PV.CHEMIN_DAMA)
        touches.add(PV.OVL_ABBAYE)
    if "embauche" in retirer:
        _remettre(rom, vanilla, ovl, PV.OVL_TULIPE,
                  [(PV.SITE_TULIPE, 4),
                   (PV.ZONE_TULIPE, PV.TAILLE_ZONE_TULIPE)])
        _fichier_vanilla(rom, vanilla, PV.CHEMIN_BAR)
        touches.add(PV.OVL_TULIPE)
    _sauver(rom, vanilla, ovl, touches)
    poser = {r: voulu[r] and not actuel[r] for r in REGLAGES[1:]}
    if any(poser.values()):
        PV.patcher(rom, ouvrir=poser["ouvertes"], embauche=poser["embauche"],
                   bloquer=poser["bloquees"], depart=None, bavard=False)
    return len(changes)


def _sauver(rom, vanilla, ovl, touches):
    """Recompresse les overlays touches ; un overlay revenu a l'identique de
    la vanilla reprend ses octets et son entree de table."""
    import ndspy.code
    if not touches:
        return
    van = vanilla.loadArm9Overlays() if vanilla is not None else {}
    for n in touches:
        o = ovl[n]
        if n in van and o.data == van[n].data:
            ovl[n] = van[n]
            rom.files[o.fileID] = bytes(vanilla.files[van[n].fileID])
        elif not o.compressed:
            # L'OVERLAY 17 DU BLOB EST STOCKE EN CLAIR (patch_amorce) : on le
            # laisse en clair, comme le randomizer qui pose la vocation de
            # depart avant l'amorce.
            o.compressedSize = len(o.data)
            rom.files[o.fileID] = bytes(o.data)
        else:
            rom.files[o.fileID] = o.save(compress=True)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovl)
