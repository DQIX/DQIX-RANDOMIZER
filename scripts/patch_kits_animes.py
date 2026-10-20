#!/usr/bin/env python3
"""Les VRAIES animations des techniques d'un KIT FIXE (joueur, 20/10/2026 :
« option 2 »), dans le modele de combat de chaque espece.

POURQUOI PAS default.bact. Un kit fixe (`patch_actions.fixer`) met ~230
techniques differentes dans le jeu ; une vraie animation coute ~70
commandes, et default.bact n'en tient qu'une dizaine meme avec le tas du
combat agrandi (research §94.7). Les variantes `rnd/aNN.nsarc` ne servent
qu'au tirage a chaque combat (le tirage pioche dans la variante).

CE QUE LE JEU FAIT DEJA. En combat, chaque monstre charge son modele
COMPLET `<code>.mon` (un NARC dans `data/pack_lv5/enemy.gp2` : `.bact`,
`.cchr`, `.cmot`) et compile son `.bact` (overlay 0, `0x021662D8`, dans un
tas propre au monstre, `objet+0x44`). Le cas d'une action dans le `.bact` du
modele PASSE AVANT celui de default.bact (le champignon montre son Haleine
fraiche). Un kit fixe est connu a la construction : on recopie le cas de
chaque technique du kit dans le `.bact` du modele de l'espece, avec les
regles de copie des variantes (patch_animations.corps_cas). Aucune greffe.

BUDGET. Le `.bact` du modele grossit ; le tas qui le recoit n'est pas
mesure. BUDGET_MODELE commandes ajoutees au plus par modele, les cas les
moins chers d'abord ; une technique hors budget garde l'animation
generique de default.bact (que fixer pose toujours). Valide en jeu au
maximum du budget (manguini sanguinaire, 391 commandes, v17z12).

L'ARCHIVE. enemy.gp2 est reecrite par gp2_ecrire.reecrire_index, son index
EN CLAIR (type 0, comme les archives d'objets) : un index recompresse en
type 1 rendait tous les modeles invisibles (v17z10).
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ENEMY = "data/pack_lv5/enemy.gp2"
BUDGET_MODELE = 400


def narc_remplacer(m, nom, donnees):
    """Le NARC `m` avec le membre `nom` remplace, bourrage 0xFF garde (celui
    du jeu : ndspy met des zeros)."""
    from tailles_modeles import fichiers_narc
    noms = list(fichiers_narc(m))
    pos = struct.unpack_from("<H", m, 12)[0]
    blocs = {}
    for _ in range(struct.unpack_from("<H", m, 14)[0]):
        magie, taille = m[pos:pos + 4], struct.unpack_from("<I", m, pos + 4)[0]
        blocs[bytes(magie)] = (pos, taille)
        pos += taille
    p_fat, t_fat = blocs[b"BTAF"]
    p_img, _t_img = blocs[b"GMIF"]
    nb = struct.unpack_from("<H", m, p_fat + 8)[0]
    fat = [struct.unpack_from("<II", m, p_fat + 12 + 8 * i) for i in range(nb)]
    contenus = [m[p_img + 8 + a:p_img + 8 + b] for a, b in fat]
    contenus[noms.index(nom)] = donnees
    img, fat2 = bytearray(), []
    for c in contenus:
        fat2.append((len(img), len(img) + len(c)))
        img += c
        img += b"\xff" * (-len(img) % 4)
    out = bytearray(m[:p_img])
    for i, (a, b) in enumerate(fat2):
        struct.pack_into("<II", out, p_fat + 12 + 8 * i, a, b)
    out += b"GMIF" + struct.pack("<I", 8 + len(img)) + img
    struct.pack_into("<I", out, 8, len(out))
    return bytes(out)


def construire_modele(bd, reels):
    """Le `.bact` d'un modele avec les cas `reels` ([(action, bd donneur,
    cas)]) ajoutes apres ses commandes. Mise en page des .bact de modeles
    (mesuree sur les 312) : commandes, bourrage 0xFF a 16, pool de chaines,
    bourrage 0xFF a 16. Rend (octets, commandes ajoutees)."""
    import patch_animations as A
    h, cmds = A.lire_bact(bd)
    pool = bytearray(bd[h[1]:h[1] + h[2]])
    nch = [h[3]]
    index = {}

    def ajouter(ch):
        if ch not in index:
            index[ch] = len(pool)
            pool.extend(ch + b"\0")
            nch[0] += 1
        return index[ch]

    corps, n = bytearray(), 0
    for action, dbd, cas in reels:
        c, k = A.corps_cas(action, dbd, cas, ajouter)
        corps += c
        n += k
    fin = cmds[-1][0] + cmds[-1][3]
    out = bytearray(bd[:fin]) + corps
    out += b"\xff" * (-len(out) % 16)
    debut = len(out)
    out += pool
    out += b"\xff" * (-len(out) % 16)
    struct.pack_into("<4I", out, 0, h[0] + n, debut, len(pool), nch[0])
    h2, c2 = A.lire_bact(bytes(out))
    if h2[0] != h[0] + n or c2[-1][0] + c2[-1][3] > debut:
        raise AssertionError("bact du modele mal reconstruit")
    return bytes(out), n


def _membres(d):
    from gp2 import GP2
    g = GP2(ENEMY, donnees=d)
    ent = sorted(g.entrees, key=lambda e: e[1] & 0xFFFFFF)
    return {g.noms[k]: d[g.first_file * 4 + (o & 0xFFFFFF) * 4:][:t]
            for k, (_h, o, t) in enumerate(ent)}


def cas_du_bact(bd):
    import patch_animations as A
    _h, cc = A.lire_bact(bd)
    return {a for _p, op, args, _t in cc if op == 1 for a in args}


def poser(rom, bavard=True, budget=BUDGET_MODELE, modeles=None):
    """`modeles` : les seuls codes de modele a toucher (essais)."""
    """Apres `patch_actions.fixer` : les techniques tirees de chaque espece
    recoivent leur vrai cas dans le `.bact` de son modele. Rend le bilan
    {"modeles", "reelles", "generiques", "commandes_max"}."""
    import ndspy.rom
    import gp2_ecrire
    import monnames
    import patch_actions as PA
    import patch_animations as A
    from rom_vanilla import chemin_vanilla
    van = ndspy.rom.NintendoDSRom.fromFile(chemin_vanilla())
    vmod = bytes(van.files[PA._fid(van, PA.MOD)])
    mod = bytes(rom.files[PA._fid(rom, PA.MOD)])
    lignes = monnames.charger(chemin_vanilla(), "en")
    par_modele = {}
    for i in PA.eligibles(mod):
        o = PA.ENTETE + i * PA.MOD_TAILLE + PA.MOD_ACTIONS
        acts = set(struct.unpack_from("<6H", mod, o))
        tirees = acts - set(struct.unpack_from("<6H", vmod, o))
        techs = {a for a in tirees
                 if a >= PA.BORNE_SORTS and not PA.est_sort(a)}
        l = lignes[i] if i < len(lignes) else None
        code = l.get("modele") if isinstance(l, dict) else None
        if techs and code:
            par_modele.setdefault(code, set()).update(techs)
    fid = rom.filenames.idOf(ENEMY)
    d = bytes(rom.files[fid])
    membres = _membres(d)
    donneurs = A.cas_donneurs(van)
    perso = A.cas_personnages(van)
    remplacements = {}
    bilan = {"modeles": 0, "reelles": 0, "generiques": 0, "commandes_max": 0}
    for code, techs in sorted(par_modele.items()):
        if modeles is not None and code not in modeles:
            continue
        nom = code + ".mon"
        if nom not in membres:
            bilan["generiques"] += len(techs)
            continue
        m = membres[nom]
        from tailles_modeles import fichiers_narc
        a, b = fichiers_narc(m)[code + ".bact"]
        bd = m[a:b]
        deja = cas_du_bact(bd)
        reels, n = [], 0
        cands = []
        for t in sorted(techs - deja):
            c = (A.meilleur_cas(donneurs.get(t, []))
                 or A.meilleur_cas(perso.get(t, [])))
            if c:
                cands.append((len(c[2]), t, c))
            else:
                bilan["generiques"] += 1
        for cout, t, (_nom, dbd, cas) in sorted(cands):
            if n + cout > budget:
                bilan["generiques"] += 1
                continue
            reels.append((t, dbd, cas))
            n += cout
        if not reels:
            continue
        neuf, ajout = construire_modele(bd, reels)
        remplacements[nom] = narc_remplacer(m, code + ".bact", neuf)
        bilan["modeles"] += 1
        bilan["reelles"] += len(reels)
        bilan["commandes_max"] = max(bilan["commandes_max"], ajout)
    if remplacements:
        rom.files[fid] = gp2_ecrire.reecrire_index(d, remplacements)
    if bavard:
        print("  vraies animations dans les modeles : %d modeles, %d "
              "techniques (au plus %d commandes ajoutees a un modele), %d "
              "restent generiques" % (bilan["modeles"], bilan["reelles"],
                                      bilan["commandes_max"],
                                      bilan["generiques"]))
    return bilan


def verifier(rom):
    """Chaque technique tiree d'une espece a un cas dans le .bact de son
    modele ou dans default.bact ; les membres non touches sont ceux du jeu
    d'origine. Rend le nombre de modeles changes."""
    import ndspy.rom
    import monnames
    import patch_actions as PA
    from rom_vanilla import chemin_vanilla
    from tailles_modeles import fichiers_narc
    van = ndspy.rom.NintendoDSRom.fromFile(chemin_vanilla())
    m0 = _membres(bytes(van.files[van.filenames.idOf(ENEMY)]))
    m1 = _membres(bytes(rom.files[rom.filenames.idOf(ENEMY)]))
    if set(m0) != set(m1):
        raise AssertionError("enemy.gp2 : membres differents")
    changes = {k for k in m0 if m0[k] != m1[k]}
    for k in changes:
        code = k[:-4]
        f0, f1 = fichiers_narc(m0[k]), fichiers_narc(m1[k])
        if set(f0) != set(f1):
            raise AssertionError("%s : fichiers differents" % k)
        for f, (a, b) in f0.items():
            if f.endswith(".bact"):
                continue
            a1, b1 = f1[f]
            if m0[k][a:b] != m1[k][a1:b1]:
                raise AssertionError("%s : %s change" % (k, f))
    import ndspy.narc
    defaut = PA.actions_default(bytes(ndspy.narc.NARC(
        rom.files[rom.filenames.idOf(PA.ACTDEF)]).files[0]))
    vmod = bytes(van.files[PA._fid(van, PA.MOD)])
    mod = bytes(rom.files[PA._fid(rom, PA.MOD)])
    lignes = monnames.charger(chemin_vanilla(), "en")
    for i in PA.eligibles(mod):
        o = PA.ENTETE + i * PA.MOD_TAILLE + PA.MOD_ACTIONS
        tirees = (set(struct.unpack_from("<6H", mod, o))
                  - set(struct.unpack_from("<6H", vmod, o)))
        code = lignes[i].get("modele") if isinstance(lignes[i], dict) else None
        cas = set()
        if code and code + ".mon" in m1:
            f = fichiers_narc(m1[code + ".mon"]).get(code + ".bact")
            if f:
                cas = cas_du_bact(m1[code + ".mon"][f[0]:f[1]])
        for t in tirees:
            if t >= PA.BORNE_SORTS and not PA.est_sort(t) \
                    and t not in cas and t not in defaut:
                raise AssertionError("fiche %d : technique %#x sans mise en "
                                     "scene" % (i, t))
    return len(changes)
