#!/usr/bin/env python3
"""Les VRAIES animations des techniques des monstres, une dizaine par combat
(ZER-57, piste B ; research §94.7).

CE QUE LE JEU FAIT (mesure du 26/09).

  * Au debut d'un combat, l'overlay 0 charge TOUTE l'archive
    `data/bin/actdef.nsarc` dans un tampon statique (`0x0211E33C`, chemin lu
    en `0x02165018`), puis compile son membre `default.bact` (`0x0216D1C4`,
    appele en `0x02165070`) AVANT le tirage des techniques (`0x02165A30`).
  * Le compile alloue ~15 o par commande dans un TAS DE TRAME dont la taille
    est une constante de l'overlay 17 (`0x1F7DC`, litteral en `0x021B727C`) ;
    combat charge, il n'en reste que ~900 o. D'ou les ecrans noirs au-dela de
    ~660 commandes. Le tas parent (ExpHeap `0x022A3200`) a 77 Ko libres d'un
    seul bloc juste derriere : on agrandit la constante (essai valide en jeu).
  * Une technique d'un autre monstre montre sa vraie animation si son cas
    (`op01 [id] ... op02` du `.bact` d'un modele donneur) est recopie dans
    `default.bact`, chaines remappees (valide en jeu : Haleine fraiche sur un
    gluant). Les 176 cas des techniques du pool coutent ~12 000 commandes :
    trop pour un seul fichier.

CE QUE FAIT CE PATCH (idee du joueur) : une DIZAINE par combat.

  * A la construction, K variantes `rnd/aNN.nsarc`, chacune une archive d'un
    seul membre `default.bact` = le default.bact d'origine + les vraies
    animations d'une dizaine de techniques + quelques techniques sans
    animation propre, rattachees a leur cas generique ; a la fin du fichier,
    128 o : la table de tirage (un bit par action) de la variante.
  * En combat : `choisir` (a la place du chargement du chemin, `0x02165018`)
    tire une variante et rend son chemin ; `copier` (a la place de l'appel du
    compile, `0x02165070`) recopie la table de la variante sur celle du
    tirage (`patch_actions.TABLE`) puis compile. Le tirage des techniques
    (patch_actions) ne pioche donc que dans la dizaine du combat.

OU VIT LE CODE : dans l'ARM9, dans la place gagnee en reecrivant a
l'identique le constructeur `0x02089234..0x02089348` (70 instructions qui
remettent des champs a zero un par un -> 33). `verifier_equivalence()` le
prouve par emulation.
"""
import os
import random
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE_ARM9 = 0x02000000
COMPRESSED_END = 0xBB4               # ModuleParams + 0x14
RAND_BELOW = 0x02032380               # r0 = [0, r0[
MEMCPY = 0x02001A40                   # (dst, src, n)

# Le constructeur reecrit (ARM9) et la suite qu'on rejoint.
BLOC = 0x02089234
SUITE = 0x0208934C
# Crochets de l'overlay 0
SITE_CHEMIN = 0x02165018              # ldr r0, [pc, #0x434] (le chemin)
ORIG_CHEMIN = 0xE59F0434
SITE_COMPILE = 0x02165070             # bl 0x0216D1C4
ORIG_COMPILE = 0xEB002053
COMPILE = 0x0216D1C4
# Le tas de trame du combat (overlay 17)
LITTERAL_TAS = 0x021B727C
TAS_ORIGINE = 0x1F7DC
TAS_PLUS = 0x4000                     # +16 Ko : valide en jeu (haleine3)

DOSSIER = "rnd"
GABARIT = b"rnd/a00.nsarc\0\0\0"     # 16 o ; les chiffres en +5, +6
POS_CHIFFRES = 5
MEMBRE = "default.bact"

# Budget par variante, en commandes AJOUTEES au default.bact d'origine :
# ~15 o par commande, 16 Ko de plus dans le tas -> ~1 000 ; marge gardee.
BUDGET = 900
COMMANDES_ORIGINE = 596               # default.bact vanilla
PAR_VARIANTE = 10                     # vraies animations par combat (joueur)

# Arguments qui sont des chaines du pool (mesure sur les 598 .bact) :
# (opcode, index de l'argument). op21/op22 chargent un modele (`enemy/...`,
# `chara/...`), op70/op75 un effet.
CHAINES = {0x03: 1, 0x12: 0, 0x14: 1, 0x15: 2, 0x3B: 2,
           0x21: 1, 0x22: 0, 0x70: 0, 0x75: 0,
           0x5B: 2}                   # op5b : point `weapon` (boomerangs, persos)
MOUVEMENT_OP = 0x03                   # op03 [emplacement, mouvement]
LANCEUR = 7                           # l'emplacement du lanceur
MODELE_OP = 0x21                      # op21 [emplacement, modele]
EMPLACEMENTS_LIBRES = (41, 64)        # ou reloger le modele du lanceur
NOEUD_OPS = (0x3B,)                   # op3b : point d attache ; PAS op15, dont
# le 3e argument est le nom de l animation de l effet (`0`, `1`, `cut_01`,
# `attack1a`...) : le remplacer bloquait 15 techniques (boomerangs, super-
# coups : familles 1 et 2 du joueur, bissection du 11/10)
# Mouvements que les 312 modeles de combat ont tous (leur .cmot)
MOUVEMENTS_UNIVERSELS = (b"attack1a", b"damage", b"death")
MOUVEMENT_REPLI = b"attack1a"
NOEUDS_UNIVERSELS = (b"0", b"1")
NOEUD_REPLI = b"0"
# Cas a risque (ils chargent un modele ou un effet par un chemin) : gardes,
# mais un cas sans eux est prefere quand il existe (decision du joueur :
# aucune technique exclue, tout se teste en jeu).
OPS_RISQUE = (0x21, 0x22, 0x70, 0x75)
# Les animations des techniques des personnages : un fichier par action,
# `spNNN.bact` (NNN = identifiant en decimal), un seul cas `op01 [] ... op02`.
ARCHIVES_PERSO = ("data/skill/actskl.nsarc", "data/skill/actetc.nsarc",
                  "data/skill/actspl.nsarc")


# --------------------------------------------------------------------------
# .bact

def lire_bact(d):
    """(entete, [(position, op, args, taille)]) ; args entiers bruts."""
    h = struct.unpack_from("<4I", d, 0)
    p, out = 0x10, []
    for _ in range(h[0]):
        op, n, _ty = struct.unpack_from("<HBB", d, p)
        q = p + 4 + (4 if n > 4 else 0)
        args = list(struct.unpack_from("<%dI" % n, d, q))
        q += 4 * n
        out.append((p, op, args, q - p))
        p = q
    return h, out


def _cas(d, cmds, k):
    """Les commandes du cas qui s'ouvre en k (op01 ... op02), ou None si le
    cas n'est pas ferme (un autre op01 ou la fin du fichier d'abord)."""
    m = k + 1
    while m < len(cmds) and cmds[m][1] not in (1, 2):
        m += 1
    if m == len(cmds) or cmds[m][1] != 2:
        return None
    return cmds[k:m + 1]


def cas_donneurs(rom):
    """{action: [(nom du .bact, octets du fichier, index de l'op01)]} pour
    tous les cas propres des modeles de combat (`enemy.gp2`)."""
    from gp2 import GP2
    from tailles_modeles import fichiers_narc
    d = bytes(rom.files[rom.filenames.idOf("data/pack_lv5/enemy.gp2")])
    g = GP2("enemy", donnees=d)
    out = {}
    for _h, o, t in g.entrees:
        p = g.first_file * 4 + (o & 0xFFFFFF) * 4
        m = d[p:p + t]
        if m[:4] != b"NARC":
            continue
        for nom, (a, b) in fichiers_narc(m).items():
            if not nom.endswith(".bact"):
                continue
            bd = m[a:b]
            try:
                _hh, cc = lire_bact(bd)
            except struct.error:
                continue
            for k, (_p, op, args, _t) in enumerate(cc):
                if op == 1:
                    for aid in args:
                        out.setdefault(aid, []).append((nom, bd, k))
    return out


FIN_CAS = (None, 2, [], 4)             # un op02 fabrique


def cas_personnages(rom):
    """{action: [(nom, octets, 0)]} : les `spNNN.bact` des personnages."""
    import ndspy.narc
    out = {}
    for arc in ARCHIVES_PERSO:
        n = ndspy.narc.NARC(bytes(rom.files[rom.filenames.idOf(arc)]))
        noms = []

        def parcourir(f, p=""):
            for x in f.files:
                noms.append(p + x)
            for x, sous in f.folders:
                parcourir(sous, p + x + "/")
        parcourir(n.filenames)
        for nom, bd in zip(noms, n.files):
            base = nom.rsplit("/", 1)[-1]
            if base.startswith("sp") and base.endswith(".bact")                     and base[2:-5].isdigit():
                out.setdefault(int(base[2:-5]), []).append((nom, bytes(bd), 0))
    return out


def meilleur_cas(donneurs):
    """Le cas le moins cher, un cas sans commande a risque d'abord, ou None.
    Rend (nom, octets du fichier, commandes du cas)."""
    best, cle_best = None, None
    for nom, bd, k in donneurs:
        _h, cc = lire_bact(bd)
        if cc[k][1] == 0x10 and cc[-1][1] == 0x11:
            # fichier d'une seule animation en bloc `op10 ... op11` (sp085...)
            cas = [cc[0]] + cc[1:-1] + [FIN_CAS]
        elif cc[k][1] != 1:
            continue
        else:
            cas = _cas(bd, cc, k)
        if cas is None:
            continue
        cle = (any(op in OPS_RISQUE for _p, op, _a, _t in cas), len(cas))
        if best is None or cle < cle_best:
            best, cle_best = (nom, bd, cas), cle
    return best


def _chaine(bd, h, off):
    pool = bd[h[1]:h[1] + h[2]]
    return pool[off:pool.index(b"\0", off)]


def emplacement_libre(cas):
    """Un emplacement que le cas n'utilise pas (premier argument d'aucune de
    ses commandes), pour y accrocher le modele que l'animation mettait sur le
    lanceur."""
    pris = {args[0] for p, _op, args, _t in cas if p is not None and args}
    for n in range(EMPLACEMENTS_LIBRES[0], EMPLACEMENTS_LIBRES[1]):
        if n not in pris:
            return n
    raise SystemExit("aucun emplacement libre pour le modele du lanceur")


def corps_cas(action, bd, cas, ajouter_chaine):
    """Les octets du cas pour `action` (op01 [action] + corps), chaines
    remappees dans le pool cible par `ajouter_chaine(octets) -> offset`."""
    h, _cc = lire_bact(bd)
    libre = emplacement_libre(cas)
    out = bytearray(struct.pack("<HBBI", 1, 1, 1, action))
    for p, op, args, t in cas[1:]:
        if p is None:
            out += struct.pack("<HBB", op, 0, 0)
            continue
        brut = bytearray(bd[p:p + t])
        # op21 [7, modele] accroche un modele de PERSONNAGE (l'arme, le
        # dragon...) a l'emplacement du lanceur : chez un monstre, ca corrompt
        # un tas (data abort en 0x020AF260, chainage 0x10D), et le combat
        # plante ou se bloque selon la disposition de la memoire (Lucifroid,
        # Hypnofouet, Flagellepsie, boomerangs...). Accroche a un emplacement
        # libre : plus d'exception (banc repare, 11/10).
        if op == MODELE_OP and args and args[0] == LANCEUR:
            struct.pack_into("<I", brut, 4 + (4 if len(args) > 4 else 0),
                             libre)
        if op in CHAINES and CHAINES[op] < len(args):
            i = CHAINES[op]
            s = _chaine(bd, h, args[i])
            # op03 [emplacement, mouvement] : 7 = le lanceur (le monstre, qui
            # n'a pas les mouvements du donneur) ; un autre numero est un
            # modele charge par l'animation elle-meme (op21 [n, modele]), qui
            # a les siens. Le remplacer fait attendre sans fin un mouvement
            # absent : Gigentaille (sp067, `cut_01`) gelait (joueur, 26/09).
            if op == MOUVEMENT_OP and args[0] == LANCEUR                     and s not in MOUVEMENTS_UNIVERSELS:
                s = MOUVEMENT_REPLI
            if op in NOEUD_OPS and s not in NOEUDS_UNIVERSELS:
                s = NOEUD_REPLI
            q = 4 + (4 if len(args) > 4 else 0) + 4 * i
            struct.pack_into("<I", brut, q, ajouter_chaine(s))
        out += brut
    return bytes(out), len(cas)


def construire_variante(base, reels, generiques, table):
    """default.bact d'une variante : `base` (le default.bact d'origine), les
    ids de `generiques` ({cas generique: [ids]}) ajoutes a leur liste, les cas
    `reels` ([(action, bd, cas)]) ajoutes a la fin, et la table de tirage
    (128 o) apres le pool. Rend (octets, commandes ajoutees)."""
    import patch_actions as pa
    d = pa._allonger(base, generiques) if generiques else base
    h, cmds = lire_bact(d)
    pool = bytearray(d[h[1]:h[1] + h[2]])
    nch = [h[3]]
    index = {}

    def ajouter(s):
        if s not in index:
            index[s] = len(pool)
            pool.extend(s + b"\0")
            nch[0] += 1
        return index[s]

    corps, n = bytearray(), 0
    for action, bd, cas in reels:
        c, k = corps_cas(action, bd, cas, ajouter)
        corps += c
        n += k
    fin = cmds[-1][0] + cmds[-1][3]
    out = bytearray(d[:fin]) + corps + d[fin:h[1]]
    debut = len(out)
    out += pool
    out += b"\0" * (-len(out) % 4)
    struct.pack_into("<4I", out, 0, h[0] + n, debut, len(pool), nch[0])
    h2, c2 = lire_bact(bytes(out))
    if c2[-1][0] + c2[-1][3] != debut - 4:
        raise AssertionError("default.bact : mot de fin mal place")
    assert len(table) == 128
    return bytes(out) + table, n


# --------------------------------------------------------------------------
# Le code

def _asm(lignes, adr, litteraux=()):
    from patch_hasard import assembler
    return assembler(lignes, adr, litteraux)


def _compact():
    """Le constructeur 0x02089234..0x02089348, a l'identique (memoire et
    registres vivants r0, r1, r2, r4) : les six `bic` successifs sur +0x22
    font un masque 0x7FFF, l'octet +0x3B finit a zero, +0x3C garde ses bits
    6-7."""
    return [
        "mov r1, #0",
        "str r1, [r4, #0x14]", "str r1, [r4, #0x18]", "str r1, [r4, #0x1c]",
        "strb r1, [r4, #0x20]", "strb r1, [r4, #0x21]",
        "ldrh r2, [r4, #0x22]", "bic r2, r2, #0x7f00", "bic r2, r2, #0xff",
        "strh r2, [r4, #0x22]",
        "strb r1, [r4, #0x24]", "strb r1, [r4, #0x25]", "strb r1, [r4, #0x26]",
        "sub r0, r1, #1",
        "strh r0, [r4, #0x28]", "strh r0, [r4, #0x2a]",
        "strh r0, [r4, #0x2c]", "strh r0, [r4, #0x2e]",
        "strh r1, [r4, #0x30]", "strh r0, [r4, #0x32]",
        "strh r0, [r4, #0x34]", "strh r1, [r4, #0x36]",
        "strb r1, [r4, #0x38]", "strb r1, [r4, #0x39]",
        "strb r1, [r4, #0x3a]", "strb r1, [r4, #0x3b]",
        "ldrb r3, [r4, #0x3c]", "and r3, r3, #0xc0", "strb r3, [r4, #0x3c]",
        "strb r1, [r4, #0x3d]",
        "add r0, r4, #0x58",
        "mov r2, #4",
        "b %d" % SUITE,
    ]


def bloc_arm9(k, table):
    """Le bloc de 280 o : le constructeur compact, `choisir`, `copier`, puis
    les litteraux (la table de tirage, le gabarit du chemin). `k` variantes ;
    `table` = adresse de la table de tirage (patch_actions.TABLE). Rend
    (octets, {etiquette: adresse})."""
    if not 1 <= k <= 99:
        raise ValueError(k)
    gab = struct.unpack("<4I", GABARIT)
    lignes = _compact() + [
        # choisir : rend r0 = le chemin d'une variante tiree au hasard
        "choisir:",
        "push {r4, lr}",
        "mov r0, #%d" % k,
        "bl %d" % RAND_BELOW,
        "mov r1, #0x30",
        "dizaine:",
        "cmp r0, #10",
        "subge r0, r0, #10",
        "addge r1, r1, #1",
        "bge {@dizaine}",
        "add r0, r0, #0x30",
        "add r4, pc, #{L1}",
        "strb r1, [r4, #%d]" % POS_CHIFFRES,
        "strb r0, [r4, #%d]" % (POS_CHIFFRES + 1),
        "mov r0, r4",
        "pop {r4, pc}",
        # copier : r0-r3 = arguments du compile ; r1 + r2 - 128 = la table
        "copier:",
        "push {r0, r1, r2, r3, r4, lr}",
        "add r1, r1, r2",
        "sub r1, r1, #128",
        "ldr r0, [pc, #{L0}]",
        "mov r2, #128",
        "bl %d" % MEMCPY,
        "pop {r0, r1, r2, r3, r4, lr}",
        "b %d" % COMPILE,
    ]
    from patch_hasard import assembler
    etq = {}
    out = assembler(lignes, BLOC, (table,) + gab, etiquettes_out=etq)
    if out[-16:] != GABARIT:
        raise AssertionError("gabarit du chemin mal place")
    taille = SUITE - BLOC
    if len(out) > taille:
        raise SystemExit("bloc ARM9 : %d o pour %d" % (len(out), taille))
    return out + bytes(taille - len(out)), etq


def bl(src, dst):
    return 0xEB000000 | (((dst - src - 8) >> 2) & 0xFFFFFF)


# --------------------------------------------------------------------------

def repartir(rom, rattache=None, par_variante=PAR_VARIANTE, seed=0):
    """Repartit le pool en variantes. `rattache` = {cas generique: [ids]},
    le pool de patch_actions (le meme que sa table de tirage) ; a defaut, il
    est recalcule. Rend [(reels, generiques)] : reels = [(action, bd, cas)],
    generiques = {cas generique: [ids]}."""
    import patch_actions as pa
    if rattache is None:
        rattache = pa.techniques(rom)
    cas_de = {a: c for c, l in rattache.items() for a in l}
    pool = sorted(cas_de)
    donneurs = cas_donneurs(rom)
    perso = cas_personnages(rom)
    reels, sans = [], []
    for a in pool:
        b = meilleur_cas(donneurs.get(a, [])) or meilleur_cas(perso.get(a, []))
        (reels if b else sans).append((a, b))
    k = max(1, -(-len(reels) // par_variante))
    groupes = [[[], 0, {}] for _ in range(k)]
    # les plus chers d'abord, chacun dans la variante la moins chargee qui a
    # encore de la place
    cap = -(-len(reels) // k)
    for a, (_nom, bd, cas) in sorted(reels, key=lambda x: -len(x[1][2])):
        g = min((g for g in groupes if len(g[0]) < cap), key=lambda g: g[1])
        g[0].append((a, bd, cas))
        g[1] += len(cas)
    rng = random.Random("animations-%s" % seed)
    rng.shuffle(sans)
    for i, (a, _b) in enumerate(sans):
        g = groupes[i % k]
        g[2].setdefault(cas_de[a], []).append(a)
    return [(g[0], g[2]) for g in groupes], len(reels), len(sans)


def patcher(rom, rattache=None, seed=0, bavard=True):
    """Pose tout. A appeler APRES patch_actions.patcher (techniques)."""
    import ndspy.code
    import ndspy.codeCompression as cc
    import ndspy.fnt
    import ndspy.narc
    import patch_actions as pa
    variantes, nr, ns = repartir(rom, rattache, seed=seed)
    fa = rom.filenames.idOf(pa.ACTDEF)
    narc = ndspy.narc.NARC(rom.files[fa])
    # la base : le default.bact de la ROM, D'ORIGINE (patch_actions ne
    # l'allonge pas quand les animations sont posees : verifie ici)
    base = bytes(narc.files[0])
    if struct.unpack_from("<I", base, 0)[0] != COMMANDES_ORIGINE:
        raise SystemExit("default.bact n'est pas celui d'origine "
                         "(patch_actions doit etre appele avec animations=True)")
    fichiers, bilan = [], []
    for reels, generiques in variantes:
        ids = [a for a, _b, _c in reels] + [a for l in generiques.values()
                                              for a in l]
        d, n = construire_variante(base, reels, generiques, pa.table_bits(ids))
        if n > BUDGET:
            raise SystemExit("variante a %d commandes ajoutees (budget %d)"
                             % (n, BUDGET))
        v = ndspy.narc.NARC(rom.files[fa])
        v.files = [d]
        fichiers.append(v.save())
        bilan.append((len(reels), len(ids) - len(reels), n, len(d)))
    # le dossier rnd/, en fin d'arborescence : aucun identifiant ne bouge
    if any(n == DOSSIER for n, _f in rom.filenames.folders):
        raise SystemExit("dossier %s/ deja present" % DOSSIER)
    premier = len(rom.files)
    noms = ["a%02d.nsarc" % i for i in range(len(fichiers))]
    rom.filenames.folders.append(
        (DOSSIER, ndspy.fnt.Folder(files=noms, firstID=premier)))
    rom.files.extend(fichiers)
    # ARM9 : le bloc
    arm9 = bytearray(cc.decompress(bytes(rom.arm9)))
    o = BLOC - BASE_ARM9
    if bytes(arm9[o:o + len(ORIGINE_BLOC)]) != ORIGINE_BLOC:
        raise SystemExit("ARM9 : constructeur 0x%08X inattendu" % BLOC)
    code, etq = bloc_arm9(len(fichiers), pa.TABLE)
    arm9[o:o + len(code)] = code
    struct.pack_into("<I", arm9, COMPRESSED_END, 0)
    rom.arm9 = bytes(arm9)
    # overlays 0 (crochets) et 17 (tas)
    ovl = rom.loadArm9Overlays()
    o0 = ovl[pa.OVL]
    d0 = bytearray(o0.data)
    for site, orig, cible in ((SITE_CHEMIN, ORIG_CHEMIN, etq["choisir"]),
                              (SITE_COMPILE, ORIG_COMPILE, etq["copier"])):
        i = site - o0.ramAddress
        if struct.unpack_from("<I", d0, i)[0] != orig:
            raise SystemExit("overlay 0 : 0x%08X inattendu" % site)
        struct.pack_into("<I", d0, i, bl(site, cible))
    o0.data = bytes(d0)
    rom.files[o0.fileID] = o0.save(compress=True)
    o17 = ovl[17]
    d17 = bytearray(o17.data)
    i = LITTERAL_TAS - o17.ramAddress
    if struct.unpack_from("<I", d17, i)[0] != TAS_ORIGINE:
        raise SystemExit("overlay 17 : taille du tas inattendue")
    struct.pack_into("<I", d17, i, TAS_ORIGINE + TAS_PLUS)
    o17.data = bytes(d17)
    rom.files[o17.fileID] = o17.save(compress=True)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovl)
    if bavard:
        print("  animations : %d variantes (%s/), %d techniques a vraie "
              "animation, %d generiques ; par variante %d-%d vraies, "
              "%d-%d commandes ajoutees, fichier <= %d o ; tas du combat "
              "+%d o" % (len(fichiers), DOSSIER, nr, ns,
                         min(b[0] for b in bilan), max(b[0] for b in bilan),
                         min(b[2] for b in bilan), max(b[2] for b in bilan),
                         max(b[3] for b in bilan), TAS_PLUS))
    return bilan


def present(rom):
    """Les variantes sont-elles posees ?"""
    return any(n == DOSSIER for n, _f in rom.filenames.folders)


def verifier(rom, pool):
    """Relit la ROM : le bloc ARM9, les deux crochets, le tas agrandi, et les
    variantes -- chacune met en scene toutes les actions de sa table, et
    l'union des tables est le pool de patch_actions."""
    import ndspy.codeCompression as cc
    import ndspy.narc
    import patch_actions as pa
    dossier = [f for n, f in rom.filenames.folders if n == DOSSIER][0]
    k = len(dossier.files)
    arm9 = cc.decompress(bytes(rom.arm9))
    code, etq = bloc_arm9(k, pa.TABLE)
    if arm9[BLOC - BASE_ARM9:SUITE - BASE_ARM9] != code:
        raise AssertionError("ARM9 : bloc des animations inattendu")
    ovl = rom.loadArm9Overlays()
    d0 = ovl[pa.OVL].data
    for site, cible in ((SITE_CHEMIN, etq["choisir"]),
                        (SITE_COMPILE, etq["copier"])):
        if struct.unpack_from("<I", d0, site - ovl[pa.OVL].ramAddress)[0]                 != bl(site, cible):
            raise AssertionError("overlay 0 : crochet 0x%08X absent" % site)
    d17 = ovl[17].data
    if struct.unpack_from("<I", d17, LITTERAL_TAS - ovl[17].ramAddress)[0]             != TAS_ORIGINE + TAS_PLUS:
        raise AssertionError("overlay 17 : tas du combat non agrandi")
    union = set()
    for i in range(k):
        fid = dossier.firstID + i
        d = bytes(ndspy.narc.NARC(rom.files[fid]).files[0])
        table = d[-128:]
        ids = {a for a in range(0x400) if table[a >> 3] >> (a & 7) & 1}
        manque = ids - pa.actions_default(d[:-128])
        if manque:
            raise AssertionError("variante %d : sans mise en scene %s"
                                 % (i, sorted(manque)))
        n = struct.unpack_from("<I", d, 0)[0] - COMMANDES_ORIGINE
        if n > BUDGET:
            raise AssertionError("variante %d : %d commandes" % (i, n))
        union |= ids
    if union != set(pool):
        raise AssertionError("variantes : %d actions, pool %d"
                             % (len(union), len(pool)))
    return k


# Les 70 instructions d'origine du constructeur (0x02089234..0x02089348)
ORIGINE_BLOC = bytes.fromhex(
    "0010a0e3141084e5181084e51c1084e52010c4e52110c4e5b222d4e1010041e2"
    "0320c2e3b222c4e1b222d4e10e2cc2e3b222c4e1b222d4e13c20c2e3b222c4e1"
    "b222d4e1072dc2e3b222c4e1b222d4e1032ac2e3b222c4e12410c4e5b222d4e1"
    "0129c2e3b222c4e12510c4e52610c4e5b802c4e1ba02c4e1bc02c4e1be02c4e1"
    "b013c4e1b203c4e1b403c4e1b613c4e13810c4e53910c4e53a10c4e53b30d4e5"
    "580084e20420a0e301e0c3e3ff300ee20250c3e3ff3005e204c0c3e3ff300ce2"
    "0850c3e33be0c4e5ff3005e23bc0c4e5f030c3e33b30c4e53c30d4e501e0c3e3"
    "ff300ee20250c3e3ff3005e204c0c3e3ff300ce208e0c3e3ff300ee210c0c3e3"
    "3c50c4e5ff300ce23ce0c4e52030c3e33c30c4e53d10c4e5")


def verifier_equivalence(essais=2000, graine=1):
    """Emule le constructeur d'origine et sa reecriture sur des objets au
    hasard : meme memoire, memes r0, r1, r2, r4, sp a l'arrivee en SUITE."""
    from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM
    from unicorn import arm_const as A
    import patch_actions as pa
    neuf, _e = bloc_arm9(18, pa.TABLE)
    rng = random.Random(graine)
    R = [getattr(A, "UC_ARM_REG_R%d" % i) for i in range(13)]
    for e in range(essais):
        regs = [rng.getrandbits(32) for _ in range(13)]
        regs[4] = 0x02300000
        mem = bytes(rng.getrandbits(8) for _ in range(0x100))
        etats = []
        for code in (ORIGINE_BLOC, neuf):
            mu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
            mu.mem_map(0x02000000, 0x400000)
            mu.mem_write(BLOC, code)
            mu.mem_write(0x02300000, mem)
            for r, v in zip(R, regs):
                mu.reg_write(r, v)
            mu.reg_write(A.UC_ARM_REG_SP, 0x023F0000)
            mu.emu_start(BLOC, SUITE, count=200)
            etats.append((bytes(mu.mem_read(0x02300000, 0x100)),
                          [mu.reg_read(R[i]) for i in (0, 1, 2, 4)],
                          mu.reg_read(A.UC_ARM_REG_PC)))
        if etats[0] != etats[1]:
            raise AssertionError("constructeur : ecart a l'essai %d" % e)
    return True


if __name__ == "__main__":
    if "--emuler" in sys.argv:
        verifier_equivalence()
        print("equivalence du constructeur : ok")
