"""The secret boss (ZER-116, 1.8): always applied, after the quest
(`patch_pages`, `patch_zenus`). Same steps, in the same order, as the test
ROM the player validated (v25, 06/11):

  - fight 144 in eventbattle (species 900, its own theme, arena 30811),
    stats, kit and actions per turn (`combat_zenus`), its entry at the end
    of the monster list and its bestiary page;
  - its theme in bgm.sdat (`musique_zenus`, converted data);
  - the quest WITH the fight (`zenus_royaume.brancher`): the slime takes
    the stone and the pages, the game saves, the boss waits on the throne;
  - the throne model (`trone`, data/chara_sub/s300.chr), its two effects
    (data/effect/zn0500.chr, zb1200.chr), the NPC on the throne;
  - the church save (`patch_sauvegarde`), the empty world after the victory
    (`patch_monde_vide`), the charm / void / action table graft and the
    boss's line (`patch_charme`);
  - its battle model, declared size, footstep sound, name and bestiary text
    (`zenus_mon`, `son_pas`);
  - its weapon, item 20030 (`patch_arme`), LAST: it inserts an item and a
    file, and `objets.noms` expects the game's catalogue.

Nothing of it is ever drawn by a randomizer pool (player, 06/11): species
900, its four own actions and its weapon -> `verifier_exclusions`.

    python scripts/patch_boss_secret.py <randomized rom> <output>
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ESPECE = 900
FICHE = 437                       # species 900 in mon_btldata / mon_moddata
# its own actions: charm, void, heal, blue spell (patch_charme)
ACTIONS_PROPRES = (0x1F6, 0x386, 0x39E, 0x3AE)
ARME = 20030


def patcher(rom, vanilla=None, bavard=True):
    """`vanilla`: the original ROM (the donors of its animations); None =
    rom_vanilla.chemin_vanilla()."""
    import combat_zenus
    import musique_zenus
    import patch_arme
    import patch_charme
    import patch_monde_vide
    import patch_sauvegarde
    import trone as T
    import zenus_mon
    import zenus_royaume as Z
    if bavard:
        print("boss secret :")
    rom.setFileByName(combat_zenus.CHEMIN, combat_zenus.ajouter(
        bytes(rom.getFileByName(combat_zenus.CHEMIN))))
    combat_zenus.stats(rom)
    combat_zenus.liste(rom)
    musique_zenus.poser(rom, bavard=bavard)
    Z.brancher(rom, combat_zenus.COMBAT)
    T.ajouter_fichier(rom, T.chr_zenus(rom))
    effet = zenus_mon.effet_zenus(rom)
    T.ajouter_effet(rom, effet, zenus_mon.EFFET_ZENUS + ".chr")
    effet_b = zenus_mon.effet_zenus(rom, zenus_mon.EFFET_BLEU, zenus_mon._bleu, zenus_mon.EFFET_DECUPLO)
    T.ajouter_effet(rom, effet_b, zenus_mon.EFFET_BLEU + ".chr")
    T.placer(rom, T.POS, T.ANGLE)
    patch_sauvegarde.patcher(rom)
    patch_sauvegarde.verifier(rom)
    patch_monde_vide.patcher(rom)
    patch_monde_vide.verifier(rom)
    patch_charme.patcher(rom, patch_charme.ACTION)
    patch_charme.replique(rom)
    zenus_mon.poser(rom, vanilla, bavard=bavard)
    patch_arme.patcher(rom, bavard=bavard)
    verifier(rom)


def verifier(rom):
    import combat_zenus
    import patch_arme
    import patch_charme
    import patch_sauvegarde
    import son_pas
    import zenus_royaume as Z
    Z.verifier(rom, combat_zenus.COMBAT)
    patch_sauvegarde.verifier(rom)
    patch_charme.verifier(rom, patch_charme.ACTION)
    patch_charme.verifier_replique(rom)
    son_pas.verifier(rom)
    patch_arme.verifier(rom)
    verifier_exclusions(rom)
    return True


def lieux_espece(rom, espece=ESPECE):
    """Every place `espece` is named for a fight: [(file, record)]. The zone
    tables (encmons, encfld, encbtl, by enctables' measured slots) and the
    scripted fights (eventbattle, read whole: PrmTable can drop the LAST
    record, and fight 144 is the last one)."""
    import enctables
    import nitro_script as N
    out = []
    t = enctables.TablesRencontres(rom, enctables.FICHIERS_RENCONTRES)
    for nom, ir, _ic, _d, _m, _v in t.references({espece}):
        out.append((nom, ir))
    _h, ins = N.lire(bytes(rom.getFileByName("data/event/eventbattle.bin")))
    for _op, ps in ins:
        v = [x for _t, x in ps]
        if any(v[k] == espece for k in (1, 3, 5) if k < len(v)):
            out.append(("eventbattle.bin", v[0]))
    return out


def actions_ailleurs(rom):
    """[(where, action)] of the boss's own actions anywhere but its own
    record: the kits of every other species (mon_moddata +0x32, mon_btldata
    +0x18), the per-fight draw table of overlay 0 and of each rnd/aNN variant
    (one bit per action), the skill trees."""
    import ndspy.narc
    import patch_actions as PA
    import patch_animations as AN
    propres = set(ACTIONS_PROPRES)
    out = []
    lu = PA.lire(rom)
    for i, kit in enumerate(lu["actions"]):
        if i != FICHE:
            out += [("mon_moddata %d" % i, a) for a in kit if a in propres]
    btl = bytes(rom.files[PA._fid(rom, PA.BTL)])
    for i in range(len(lu["actions"])):
        if i != FICHE:
            kit = struct.unpack_from("<6H", btl, PA.ENTETE + i * PA.BTL_TAILLE + PA.BTL_ACTIONS)
            out += [("mon_btldata %d" % i, a) for a in kit if a in propres]
    out += [("overlay 0", a) for a in lu["sorts"] + lu["techniques"] if a in propres]
    if AN.present(rom):
        dossier = [f for n, f in rom.filenames.folders if n == AN.DOSSIER][0]
        for k in range(len(dossier.files)):
            d = bytes(ndspy.narc.NARC(rom.files[dossier.firstID + k]).files[0])
            table = d[-128:]
            out += [("%s/%d" % (AN.DOSSIER, k), a) for a in propres if table[a >> 3] >> (a & 7) & 1]
    out += [("arbres", a) for a in _actions_des_arbres(rom) if a in propres]
    return out


def _actions_des_arbres(rom):
    """The action of every skill-tree step (skilltable, field 3 = the skill
    or spell it teaches, research §87)."""
    from prmtable import PrmTable
    t = PrmTable(bytes(rom.getFileByName("data/prm/skilltable.bin")), selon_entete=True)
    return {r.fields[3] for r in t.records if len(r.fields) > 3}


def lieux_arme(rom, objet=ARME):
    """Every place `objet` is handed out but the boss's own drop: loot tables
    and containers, monster drops, shops, the Captain's rewards and shop,
    the per-fight loot pool."""
    import boutiques
    import patch_butin
    import patch_medailles
    import treasure as T
    from patch_loot import MON_ENTETE, MON_ENREG, OFF_DROPS, _lot_zones
    out = []
    arc = bytes(rom.getFileByName("data/scenario/treasure.nsarc"))
    membres = T.membres_narc(arc)
    for table in (T.TABLE_COFFRES_BLEUS, T.TABLE_POTS, T.TABLE_GROTTOS):
        for _off, o in T.outcomes(arc, membres[table][0]):
            if o["loot"] == T.TYPE_OBJET and o["id"] == objet:
                out.append(table)
    for zone, (deb, _f) in _lot_zones(membres).items():
        for c in T.conteneurs(arc, deb):
            if c["loot"] == T.TYPE_OBJET and c["item"] == objet:
                out.append(zone)
    mon = bytes(rom.getFileByName("data/prm/mon_btldata.nat"))
    for k in range(struct.unpack_from("<I", mon, 0)[0]):
        for off, _genre in OFF_DROPS:
            if k != FICHE and struct.unpack_from("<H", mon, MON_ENTETE + k * MON_ENREG + off)[0] == objet:
                out.append("drop %d" % k)
    _d, etals = boutiques.lire(rom)
    out += ["boutique %d" % e["id"] for e in etals if objet in e["objets"]]
    paliers, boutique = patch_medailles.lire(rom)
    out += ["capitaine" for _n, o in paliers + boutique if o == objet]
    lu = patch_butin.lire(rom)
    if lu is not None and objet in lu[1]:
        out.append("butin a chaque combat")
    return out


def verifier_exclusions(rom):
    """Species 900, its four own actions and its weapon in NO draw (player,
    06/11: "this weapon / this boss / the boss's skills must not be drawn
    anywhere, it is unique to the boss"). The pools are built from the
    original game, where none of them exists, and from `objets.HORS_TIRAGE`;
    this reads the finished ROM."""
    import combat_zenus
    import objets
    lieux = lieux_espece(rom)
    assert lieux == [("eventbattle.bin", combat_zenus.COMBAT)], "espece %d : %s" % (ESPECE, lieux[:6])
    ailleurs = actions_ailleurs(rom)
    assert not ailleurs, "actions du boss ailleurs : %s" % ["%s:%#x" % x for x in ailleurs[:6]]
    assert ARME in objets.HORS_TIRAGE
    places = lieux_arme(rom)
    assert not places, "arme %d distribuee : %s" % (ARME, places[:6])
    return True


if __name__ == "__main__":
    import ndspy.rom
    src, dst = sys.argv[1], sys.argv[2]
    rom = ndspy.rom.NintendoDSRom.fromFile(src)
    patcher(rom)
    data = bytearray(rom.save())
    taille = os.path.getsize(src)
    if len(data) > taille:
        raise SystemExit("ROM plus grande que l'entree")
    data += b"\xff" * (taille - len(data))
    open(dst, "wb").write(data)
    print("ecrit", dst)
