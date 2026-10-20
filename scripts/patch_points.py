#!/usr/bin/env python3
"""Randomiser les OBJETS DES POINTS BRILLANTS (ZER-97, patch de la 1.7).

LE FORMAT (research §105). Deux fichiers, des scripts Nitro (treasure.py) :

  data/scenario/flditem.pac   une archive NARC, un membre `Fxxflditem.bin`
                              par carte de terrain (40) ; chaque opcode 0x66
                              est UN GROUPE de points (87 en tout) : param 0 =
                              numero de zone (0..99), param 1 = l'objet,
                              params 2..7 = quantite, reapparition et nombre
                              de points, puis jusqu'a 8 positions (x, y, z).
                              Un seul objet par groupe. L'archive porte aussi
                              `fldbias.bin` (les delais par defaut) et une
                              copie `.svn/` oubliee par les developpeurs, que
                              le jeu ne lit pas (on n'y touche pas).
  data/bin/izmitm.bin         les zones speciales 98 et 99 : deux opcodes 0x66
                              (positions seules) et huit opcodes 0x68, un par
                              groupe de partie (0..7, tire a la creation du
                              personnage) : param 0 = groupe, params 1..16 =
                              les objets.

DECISION DU JOUEUR (20/10/2026) : n'importe quel OBJET, aucun equipement,
jamais un objet important ni `objets.HORS_TIRAGE` ; et UN OBJET DIFFERENT A
CHAQUE RAMASSAGE (un groupe partage son objet entre ses points, et un point
reapparait). Aucun point du jeu d'origine ne porte d'objet important.

DEUX MODES :
  ramassage (defaut)  l'objet est tire a chaque ramassage, dans un pool de
                      la carte. Le jeu sait deja le faire pour les zones 98/99
                      (research §105) : on etend son mecanisme a toutes les
                      cartes --
                        * chaque membre Fxx recoit un opcode 0x68 : son pool
                          (16 a 127 objets), et ses opcodes 0x64 (vides)
                          deviennent des 0x65 (vides aussi), fldbias compris ;
                        * l'entree 0x64 des tables d'opcodes des cartes et des
                          minuteries devient 0x68 (le gestionnaire de table
                          d'izmitm pour les cartes, une fonction vide pour les
                          minuteries) ;
                        * le gestionnaire 0x68 est REECRIT EN PLACE : a chaque
                          entree sur la carte, il tire 16 objets sans doublon
                          parmi le pool, dans la table de 16 d'origine (plus
                          de test du groupe de partie) ; le tirage au
                          ramassage tire parmi ces 16 (au lieu de 8 avant le
                          chapitre 0x13) ;
                        * au chargement de la carte, les NOMS des 16 objets
                          de la table sont charges pour toute carte (sinon
                          seuls ceux des noeuds : un objet sans nom ne se
                          donne pas, research 105.3) ;
                        * au ramassage (overlay 17), la branche « zone < 98 :
                          objet fixe » est neutralisee.
                      izmitm.bin porte alors UN seul opcode 0x68, le pool.
  fixe                un objet tire par groupe, a la construction (u32
                      reecrits en place). Ce que « Creer sa ROM » pose quand
                      le ramassage est decoche.

  par rang            (les deux modes) un objet a une etoile pres de celui
                      d'origine ; au ramassage, le pool d'une carte est
                      l'union des bandes de ses groupes.

Le tirage a SON PROPRE generateur, derive de la graine. Le mode ramassage
change la taille de flditem.pac et d'izmitm.bin (savestates invalides).
"""
import os
import random
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import objets
import treasure as T

PAC = "data/scenario/flditem.pac"
IZM = "data/bin/izmitm.bin"
OP_GROUPE, OP_TABLE, OP_VIDE_A, OP_VIDE_B = 0x66, 0x68, 0x64, 0x65

# LES OBJETS D'UN POOL DE RAMASSAGE : 16, comme les zones 98/99 du jeu.
# Un objet ne se donne que si son NOM a ete charge avec la carte (le
# message « X obtient ... ») : au chargement, 0x0201648C charge les noms des
# objets des noeuds, ou -- si le premier noeud est en mode 9 (zones
# speciales) -- ceux des 16 premieres cases de la table, dans une liste sur
# la pile de 100 objets au plus (mesure en jeu le 20/10/2026 : 127 objets
# tires, 3 donnes, research 105.3). La table garde donc sa taille d'origine
# (allocation 0x20, copie de 16) ; le tirage au ramassage prend 16 au lieu
# de 8 avant le chapitre 0x13. Les fenetres des 40 cartes couvrent les 143
# objets (40 x 16 = 640).
TAILLE_TABLE = 16
# LE POOL D'UNE CARTE : 16 a 127 objets (l'interpreteur de scripts ne lit
# que 128 parametres, 0x020308F4 `cmp sb, #0x80`, dont le groupe). A CHAQUE
# ENTREE SUR LA CARTE (joueur, 20/10/2026 : « jamais les memes objets au meme
# endroit »), le gestionnaire 0x68 reecrit (GESTIONNAIRE) tire 16 objets SANS
# DOUBLON parmi les parametres, dans la table ; leurs noms se chargent
# ensuite. Au moins 16 objets par pool (complete par repetition sinon).
POOL_MIN, POOL_MAX = TAILLE_TABLE, 127
TAILLE_POOL = POOL_MAX

BASE_ARM9 = 0x02000000
# LE GESTIONNAIRE DE L'OPCODE 0x68 (0x0208E454..0x0208E4C4, 29 instructions,
# le litteral de la structure en 0x0208E4C8 garde) : r0 = les parametres
# (8 o chacun), r1 = leur nombre. Reecrit en place : il alloue la table de
# 0x20 octets comme d'origine, puis tire 16 parametres sans remise (echange
# avec le dernier dans le tampon de l'interpreteur, qui ne sert plus apres).
# Plus de test du groupe de partie : izmitm ne porte qu'une table en mode
# ramassage.
GESTIONNAIRE, FIN_GESTIONNAIRE = 0x0208E454, 0x0208E4C8
DONNE_STRUCTURE = 0x0208E0B8    # rend la structure 0x02108FE4
TAS_POINTS = 0x0218B5B0         # rend la base ; le tas est a +0x1A0
ALLOUER = 0x02032554
LIRE_PARAM = 0x02030B1C
RAND_BELOW = 0x02032380         # r0 = [0, r0[


def code_gestionnaire():
    from patch_hasard import assembler
    a = GESTIONNAIRE
    lignes = [
        "push {r4, r5, r6, r7, r8, lr}",
        "mov r6, r0",
        "sub r7, r1, #1",                       # objets restants (1..r7)
        "bl #%d" % DONNE_STRUCTURE,
        "mov r5, r0",
        "bl #%d" % TAS_POINTS,
        "add r0, r0, #0x1a0",
        "mov r1, #0x20",
        "bl #%d" % ALLOUER,
        "mov r4, r0",
        "str r4, [r5, #0xc]",
        "mov r5, #%d" % TAILLE_TABLE,
        "boucle:",
        "mov r0, r7",
        "bl #%d" % RAND_BELOW,
        "add r8, r6, r0, lsl #3",
        "add r8, r8, #8",                       # &parametre[1 + k]
        "mov r0, r8",
        "bl #%d" % LIRE_PARAM,
        "strh r0, [r4], #2",
        "add r2, r6, r7, lsl #3",               # &parametre[r7], le dernier
        "ldr r3, [r2]",
        "str r3, [r8]",
        "ldr r3, [r2, #4]",
        "str r3, [r8, #4]",
        "sub r7, r7, #1",
        "subs r5, r5, #1",
        "bne #{@boucle}",
        "mov r0, #1",
        "pop {r4, r5, r6, r7, r8, pc}",
    ]
    code = assembler(lignes, a)
    place = FIN_GESTIONNAIRE - GESTIONNAIRE
    assert len(code) <= place, len(code)
    if len(code) < place:
        code += assembler(["mov r0, r0"] * ((place - len(code)) // 4),
                          a + len(code))
    return code


# (adresse, instruction d'origine, instruction posee)
SITES_ARM9 = (
    (0x0208E7F8, "mov r5, #8", "mov r5, #%d" % TAILLE_TABLE),
    # les noms : depuis la table pour toute carte, pas seulement en mode 9
    (0x02016748, "bne #0x2016784", "mov r0, r0"),
)
# (adresse de l'entree, (opcode, gestionnaire) d'origine, posee)
ENTREES = (
    (0x020F1290, (0x64, 0x0208E0C4), (0x68, 0x0208E454)),   # cartes Fxx
    (0x020F1308, (0x64, 0x0208E894), (0x68, 0x0208E894)),   # minuteries
)
OVL_RAMASSAGE = 17
SITE_RAMASSAGE = (0x02198A00, "blo #0x2198a28", "mov r0, r0")


def generateur(seed):
    """Le generateur des points brillants, independant du reste."""
    return random.Random("points:%d" % seed)


# --- lecture -------------------------------------------------------------------

def _narc(pac):
    import ndspy.narc
    return ndspy.narc.NARC(bytes(pac))


def _est_carte(nom):
    return "/" not in nom and nom.startswith("F") and nom.endswith("flditem.bin")


def _membres(pac):
    """[(nom, debut, fin)] des membres de l'archive, dans l'ordre de la FAT,
    offsets absolus dans `pac`."""
    narc = _narc(pac)
    pos = struct.unpack_from("<H", pac, 12)[0]
    fat = img = None
    for _ in range(struct.unpack_from("<H", pac, 14)[0]):
        magie, taille = pac[pos:pos + 4], struct.unpack_from("<I", pac, pos + 4)[0]
        if magie == b"BTAF":
            nb = struct.unpack_from("<H", pac, pos + 8)[0]
            fat = [struct.unpack_from("<II", pac, pos + 12 + 8 * i)
                   for i in range(nb)]
        elif magie == b"GMIF":
            img = pos + 8
        pos += taille
    return [(narc.filenames.filenameOf(i), img + a, img + b)
            for i, (a, b) in enumerate(fat)]


def lire(rom):
    """Rend (groupes, tables).
    groupes : [{carte, zone, objet, points, off}] des 87 groupes du terrain ;
    tables  : [{groupe, rang, objet, off}] des cases d'izmitm.bin (128 dans le
              jeu d'origine, le pool en mode ramassage).
    `off` : offset du u32 de l'objet dans son fichier."""
    pac = bytes(rom.files[rom.filenames.idOf(PAC)])
    groupes = []
    for nom, deb, fin in _membres(pac):
        if not _est_carte(nom):
            continue
        for x in T.lire_script(pac[deb:fin], 0)[1]:
            if x.op != OP_GROUPE:
                continue
            groupes.append(dict(carte=nom[:3], zone=x.valeurs[0],
                                objet=x.valeurs[1], points=x.valeurs[7]
                                if x.valeurs[4] == 8 else None,
                                off=deb + x.offsets[1]))
    izm = bytes(rom.files[rom.filenames.idOf(IZM)])
    tables = []
    for x in T.lire_script(izm, 0)[1]:
        if x.op != OP_TABLE:
            continue
        for k in range(1, len(x.valeurs)):
            tables.append(dict(groupe=x.valeurs[0], rang=k,
                               objet=x.valeurs[k], off=x.offsets[k]))
    return groupes, tables


def ecrire(rom, groupes, tables):
    """Pose l'objet de chaque groupe et de chaque case (en place)."""
    for chemin, lignes in ((PAC, groupes), (IZM, tables)):
        fid = rom.filenames.idOf(chemin)
        d = bytearray(rom.files[fid])
        for l in lignes:
            T.ecrire_u32(d, l["off"], l["objet"])
        rom.files[fid] = bytes(d)


def pool(rom):
    """Les objets qu'un point peut donner : le pool du randomizer (sans
    objet important ni HORS_TIRAGE), equipement exclu."""
    cat = objets.catalogue(rom, "en")
    return [i for i in objets.pool(rom, "en") if cat[i][0] == "t"]


def _bande(p, et, vanilla):
    e = et.get(vanilla, 0)
    return [i for i in p if abs(et.get(i, 0) - e) <= 1]


# --- mode fixe -----------------------------------------------------------------

def tirer(rom, rng, par_rang=False):
    """Rend (groupes, tables) tires, sans ecrire (mode fixe)."""
    groupes, tables = lire(rom)
    p = pool(rom)
    et = objets.raretes(rom, "en")
    for l in groupes + tables:
        l["objet"] = rng.choice(_bande(p, et, l["objet"]) if par_rang else p)
    return groupes, tables


# --- mode ramassage --------------------------------------------------------------

def _desas(octets, adr):
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
    i = next(md.disasm(bytes(octets[:4]), adr))
    return "%s %s" % (i.mnemonic, i.op_str)


def _instruction(op, valeurs):
    """Une instruction de script : parametres entiers (type 1)."""
    n = len(valeurs)
    types = bytearray((2 * n + 7) // 8)
    for i in range(n):
        types[i // 4] |= 1 << (2 * (i % 4))
    tete = struct.pack("<HB", op, n) + bytes(types)
    tete += b"\x00" * (-len(tete) % 4)
    return tete + b"".join(struct.pack("<I", v & 0xFFFFFFFF) for v in valeurs)


def _aligner16(b):
    return b + b"\xff" * (-len(b) % 16)


def _reecrire_script(d, ajout=b"", sans_tables=False):
    """Un script neuf : ses 0x64 changes en 0x65, `ajout` (des instructions)
    a la fin du code, et sans ses 0x68 si `sans_tables`. Mise en page de
    treasure.reconstruire_table : code bourre de 0xff a 16, donnees, membre
    bourre a 16."""
    h, instrs = T.lire_script(d, 0)
    code = bytearray()
    n = 0
    for k, x in enumerate(instrs):
        fin = instrs[k + 1].debut if k + 1 < len(instrs) else (
            x.offsets[-1] + 4 if x.offsets else x.debut + 4)
        if sans_tables and x.op == OP_TABLE:
            continue
        b = bytearray(d[x.debut:fin])
        if x.op == OP_VIDE_A:
            struct.pack_into("<H", b, 0, OP_VIDE_B)
        code += b
        n += 1
    code += ajout
    code = _aligner16(bytes(code) + struct.pack("<H", 0xFFFF))
    donnees = bytes(d[h["off_donnees"]:])
    nb = n + _compter(ajout)
    tete = struct.pack("<iIiI", nb, 16 + len(code), h["lg_donnees"],
                       h["nb_chaines"])
    return _aligner16(tete + code + donnees)


def _compter(ajout):
    """Le nombre d'instructions de `ajout` (une suite d'_instruction)."""
    n, p = 0, 0
    while p < len(ajout):
        k = ajout[p + 2]
        q = p + 3 + (2 * k + 7) // 8
        q = (q + 3) & ~3
        p = q + 4 * k
        n += 1
    return n


def _remplir(rng, candidats):
    """Un pool de POOL_MIN a POOL_MAX objets tires de `candidats` (sans
    doublon, melanges) ; moins de POOL_MIN candidats se repetent."""
    c = sorted(set(candidats))
    if not c:
        raise ValueError("pool vide")
    rng.shuffle(c)
    if len(c) >= POOL_MAX:
        return c[:POOL_MAX]
    out = list(c)
    while len(out) < POOL_MIN:
        out.append(c[len(out) % len(c)])
    return out


_cache = {}


def _gestionnaire_origine():
    """Les octets d'origine du gestionnaire 0x68 (ARM9 vanilla)."""
    if "g" not in _cache:
        import ndspy.codeCompression as cc
        import ndspy.rom
        from rom_vanilla import chemin_vanilla
        a = cc.decompress(bytes(ndspy.rom.NintendoDSRom.fromFile(
            chemin_vanilla()).arm9))
        _cache["g"] = bytes(a[GESTIONNAIRE - BASE_ARM9:
                              FIN_GESTIONNAIRE - BASE_ARM9])
    return _cache["g"]


def _sources():
    """Les octets d'origine des deux fichiers (la ROM du joueur, vanilla)."""
    import source_rom
    return bytes(source_rom.lire(PAC)), bytes(source_rom.lire(IZM))


def poser_ramassage(rom, pools, pool_special, objets_groupes=None):
    """Mode ramassage. `pools` : {carte: [objets]} ; `pool_special` : la
    table d'izmitm ; `objets_groupes` : l'objet fixe de chaque groupe (p1,
    garde pour le journal et la config, le jeu ne le lit plus), par defaut
    celui du jeu d'origine. Repart des fichiers d'origine."""
    import ndspy.code
    import ndspy.codeCompression as cc
    from patch_hasard import assembler, COMPRESSED_END
    pac0, izm0 = _sources()
    narc = _narc(pac0)
    k_groupe = 0
    for i, f in enumerate(narc.files):
        nom = narc.filenames.filenameOf(i)
        if nom == "fldbias.bin":
            narc.files[i] = _reecrire_script(f)
            continue
        if not _est_carte(nom):
            continue
        d = bytearray(f)
        for x in T.lire_script(f, 0)[1]:
            if x.op == OP_GROUPE:
                if objets_groupes is not None:
                    struct.pack_into("<I", d, x.offsets[1],
                                     objets_groupes[k_groupe])
                k_groupe += 1
        p = pools.get(nom[:3])
        ajout = _instruction(OP_TABLE, [0] + list(p)) if p else b""
        if p and not POOL_MIN <= len(p) <= POOL_MAX:
            raise ValueError("pool de %s : %d objets (%d a %d)"
                             % (nom[:3], len(p), POOL_MIN, POOL_MAX))
        narc.files[i] = _reecrire_script(bytes(d), ajout)
    rom.files[rom.filenames.idOf(PAC)] = narc.save()
    if not POOL_MIN <= len(pool_special) <= POOL_MAX:
        raise ValueError("pool special : %d objets" % len(pool_special))
    rom.files[rom.filenames.idOf(IZM)] = _reecrire_script(
        izm0, _instruction(OP_TABLE, [0] + list(pool_special)),
        sans_tables=True)

    arm9 = bytearray(cc.decompress(bytes(rom.arm9)))
    g0, g1 = GESTIONNAIRE - BASE_ARM9, FIN_GESTIONNAIRE - BASE_ARM9
    if bytes(arm9[g0:g1]) not in (_gestionnaire_origine(), code_gestionnaire()):
        raise SystemExit("points : le gestionnaire 0x68 (%#010x) n'est ni "
                         "celui du jeu ni le notre" % GESTIONNAIRE)
    arm9[g0:g1] = code_gestionnaire()
    for adr, avant, apres in SITES_ARM9:
        o = adr - BASE_ARM9
        lu = _desas(arm9[o:o + 4], adr)
        if lu != avant and arm9[o:o + 4] != assembler([apres], adr):
            raise SystemExit("points : a %#010x attendu %r, lu %r"
                             % (adr, avant, lu))
        arm9[o:o + 4] = assembler([apres], adr)
    for adr, avant, apres in ENTREES:
        o = adr - BASE_ARM9
        lu = struct.unpack_from("<II", arm9, o)
        if lu not in (avant, apres):
            raise SystemExit("points : table d'opcodes %#010x : %r"
                             % (adr, lu))
        struct.pack_into("<II", arm9, o, *apres)
    struct.pack_into("<I", arm9, COMPRESSED_END, 0)
    rom.arm9 = bytes(arm9)

    ovl = rom.loadArm9Overlays()
    o = ovl[OVL_RAMASSAGE]
    d = bytearray(o.data)
    adr, avant, apres = SITE_RAMASSAGE
    k = adr - o.ramAddress
    lu = _desas(d[k:k + 4], adr)
    if lu != avant and d[k:k + 4] != assembler([apres], adr):
        raise SystemExit("points : overlay 17 %#010x attendu %r, lu %r"
                         % (adr, avant, lu))
    d[k:k + 4] = assembler([apres], adr)
    o.data = bytes(d)
    rom.files[o.fileID] = o.save(compress=True)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovl)


def retirer_ramassage(rom):
    """Defait poser_ramassage : les deux fichiers d'origine, les sites de
    l'ARM9 et de l'overlay 17 remis a leur instruction d'origine."""
    import ndspy.code
    import ndspy.codeCompression as cc
    from patch_hasard import assembler, COMPRESSED_END
    pac0, izm0 = _sources()
    rom.files[rom.filenames.idOf(PAC)] = pac0
    rom.files[rom.filenames.idOf(IZM)] = izm0
    arm9 = bytearray(cc.decompress(bytes(rom.arm9)))
    arm9[GESTIONNAIRE - BASE_ARM9:FIN_GESTIONNAIRE - BASE_ARM9] = \
        _gestionnaire_origine()
    for adr, avant, _apres in SITES_ARM9:
        arm9[adr - BASE_ARM9:adr - BASE_ARM9 + 4] = assembler([avant], adr)
    for adr, avant, _apres in ENTREES:
        struct.pack_into("<II", arm9, adr - BASE_ARM9, *avant)
    struct.pack_into("<I", arm9, COMPRESSED_END, 0)
    rom.arm9 = bytes(arm9)
    ovl = rom.loadArm9Overlays()
    o = ovl[OVL_RAMASSAGE]
    d = bytearray(o.data)
    adr, avant, _apres = SITE_RAMASSAGE
    d[adr - o.ramAddress:adr - o.ramAddress + 4] = assembler([avant], adr)
    o.data = bytes(d)
    rom.files[o.fileID] = o.save(compress=True)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovl)


def lire_ramassage(rom):
    """{actif, pools: {carte: [objets]}, special: [objets]} ; `actif` faux
    si la branche du ramassage est celle du jeu d'origine."""
    from patch_hasard import assembler
    o = rom.loadArm9Overlays()[OVL_RAMASSAGE]
    adr, _avant, apres = SITE_RAMASSAGE
    k = adr - o.ramAddress
    actif = bytes(o.data[k:k + 4]) == assembler([apres], adr)
    pac = bytes(rom.files[rom.filenames.idOf(PAC)])
    pools = {}
    for nom, deb, fin in _membres(pac):
        if _est_carte(nom):
            for x in T.lire_script(pac[deb:fin], 0)[1]:
                if x.op == OP_TABLE:
                    pools[nom[:3]] = list(x.valeurs[1:])
    izm = bytes(rom.files[rom.filenames.idOf(IZM)])
    special = [v for x in T.lire_script(izm, 0)[1] if x.op == OP_TABLE
               for v in x.valeurs[1:]]
    return dict(actif=actif, pools=pools, special=special)


def tirer_ramassage(rom, rng, par_rang=False, candidats=None):
    """Rend (pools, pool_special) : par carte, POOL_MAX objets au plus parmi
    `candidats` (defaut : le pool), l'union des bandes de ses groupes en
    par_rang. Le jeu en tire 16 a chaque entree sur la carte."""
    groupes, tables = lire(rom)
    p = list(candidats) if candidats is not None else pool(rom)
    et = objets.raretes(rom, "en")
    cartes = []
    for l in groupes:
        if l["carte"] not in cartes:
            cartes.append(l["carte"])
    pools = {}
    # TOUS LES OBJETS QUELQUE PART (joueur, 20/10/2026) : sans par_rang,
    # chaque carte prend une fenetre glissante de POOL_MAX objets dans une
    # liste melangee ; les fenetres des cartes successives se suivent, donc
    # chaque objet du pool tombe dans au moins une carte (en fait presque
    # toutes : 127 des 143 par carte).
    melange = list(p)
    rng.shuffle(melange)
    for k, c in enumerate(cartes):
        if par_rang:
            cand = sorted({i for l in groupes if l["carte"] == c
                           for i in _bande(p, et, l["objet"])})
            pools[c] = _remplir(rng, cand)
        elif len(melange) > POOL_MAX:
            fen = [melange[(k * POOL_MAX + j) % len(melange)]
                   for j in range(POOL_MAX)]
            rng.shuffle(fen)
            pools[c] = fen
        else:
            pools[c] = _remplir(rng, melange)
    if par_rang:
        cand = sorted({i for l in tables for i in _bande(p, et, l["objet"])})
    else:
        cand = p
    return pools, _remplir(rng, cand)


# --- les deux modes ------------------------------------------------------------

def patcher(rom, seed, par_rang=False, ramassage=True, langue="en",
            journal=None):
    """Tire et ecrit. Rend (groupes ou cartes changes, cases ou objets du
    pool special)."""
    rng = generateur(seed)
    nm = objets.noms(rom, langue)
    if ramassage:
        pools, special = tirer_ramassage(rom, rng, par_rang=par_rang)
        poser_ramassage(rom, pools, special)
        if journal is not None:
            import zones
            lieux = zones.noms_zones(rom, langue)
            journal.write("=" * 78 + "\n")
            journal.write("POINTS BRILLANTS : TIRES A CHAQUE RAMASSAGE (%s, "
                          "ZER-97)\n" % ("a une etoile pres" if par_rang
                                         else "tout objet"))
            journal.write("=" * 78 + "\n")
            for c, p in sorted(pools.items()):
                journal.write("  %-28s %d objets differents : %s\n"
                              % (lieux.get(c, c)[:28], len(set(p)),
                                 ", ".join(sorted({str(nm.get(i, i))
                                                   for i in p}))))
            journal.write("  zones 98/99 : %d objets differents\n\n"
                          % len(set(special)))
        return len(pools), len(set(special))
    g0, t0 = lire(rom)
    g, t = tirer(rom, rng, par_rang=par_rang)
    ecrire(rom, g, t)
    if journal is not None:
        import zones
        lieux = zones.noms_zones(rom, langue)
        journal.write("=" * 78 + "\n")
        journal.write("POINTS BRILLANTS : OBJETS FIXES (%s, ZER-97)\n"
                      % ("a une etoile pres" if par_rang else "tout objet"))
        journal.write("=" * 78 + "\n")
        for a, b in zip(g0, g):
            journal.write("  %-28s zone %2d  %-26s -> %s\n"
                          % (lieux.get(a["carte"], a["carte"])[:28], a["zone"],
                             nm.get(a["objet"], a["objet"]),
                             nm.get(b["objet"], b["objet"])))
        for a, b in zip(t0, t):
            journal.write("  zones 98/99, groupe %d, case %2d  %-26s -> %s\n"
                          % (a["groupe"], a["rang"],
                             nm.get(a["objet"], a["objet"]),
                             nm.get(b["objet"], b["objet"])))
        journal.write("\n")
    return (sum(a["objet"] != b["objet"] for a, b in zip(g0, g)),
            sum(a["objet"] != b["objet"] for a, b in zip(t0, t)))


def verifier(rom, vanilla, par_rang=False, ramassage=True):
    """Mode ramassage : les sites posent ce qu'il faut, chaque carte a
    groupes porte un pool de TAILLE_POOL objets du pool (bandes en par_rang),
    plus aucun 0x64 dans l'archive lue, les groupes intacts.
    Mode fixe : meme structure, tout objet dans le pool.
    Rend un compte (cartes a pool, ou cases changees)."""
    g0, t0 = lire(vanilla)
    g, t = lire(rom)
    p = set(pool(vanilla))
    et = objets.raretes(vanilla, "en")
    if len(g) != len(g0):
        raise AssertionError("points brillants : %d groupes au lieu de %d"
                             % (len(g), len(g0)))
    for a, b in zip(g0, g):
        if (a["carte"], a["zone"], a["points"]) != (b["carte"], b["zone"],
                                                    b["points"]):
            raise AssertionError("points brillants : groupes changes")
    if ramassage:
        import ndspy.codeCompression as cc
        from patch_hasard import assembler
        lu = lire_ramassage(rom)
        if not lu["actif"]:
            raise AssertionError("overlay 17 : branche du ramassage intacte")
        arm9 = bytes(cc.decompress(bytes(rom.arm9)))
        for adr, _avant, apres in SITES_ARM9:
            o = adr - BASE_ARM9
            if arm9[o:o + 4] != assembler([apres], adr):
                raise AssertionError("ARM9 %#010x non pose" % adr)
        if (arm9[GESTIONNAIRE - BASE_ARM9:FIN_GESTIONNAIRE - BASE_ARM9]
                != code_gestionnaire()):
            raise AssertionError("gestionnaire 0x68 non pose")
        for adr, _avant, apres in ENTREES:
            if struct.unpack_from("<II", arm9, adr - BASE_ARM9) != apres:
                raise AssertionError("table d'opcodes %#010x" % adr)
        cartes = {l["carte"] for l in g0}
        if set(lu["pools"]) != cartes:
            raise AssertionError("pools sur %d cartes au lieu de %d"
                                 % (len(lu["pools"]), len(cartes)))
        for c, pl in list(lu["pools"].items()) + [("98/99", lu["special"])]:
            if not POOL_MIN <= len(pl) <= POOL_MAX:
                raise AssertionError("%s : pool de %d objets" % (c, len(pl)))
            hors = [i for i in pl if i not in p]
            if hors:
                raise AssertionError("%s : objet %d hors du pool" % (c, hors[0]))
            if par_rang:
                bandes = {i for l in (g0 if c != "98/99" else t0)
                          if c == "98/99" or l["carte"] == c
                          for i in _bande(sorted(p), et, l["objet"])}
                if set(pl) - bandes:
                    raise AssertionError("%s : objet hors des bandes" % c)
        pac = bytes(rom.files[rom.filenames.idOf(PAC)])
        for nom, deb, fin in _membres(pac):
            if _est_carte(nom) or nom == "fldbias.bin":
                if any(x.op == OP_VIDE_A
                       for x in T.lire_script(pac[deb:fin], 0)[1]):
                    raise AssertionError("%s : opcode 0x64 restant" % nom)
        return len(lu["pools"])
    for chemin in (PAC, IZM):
        if len(rom.files[rom.filenames.idOf(chemin)]) != len(
                vanilla.files[vanilla.filenames.idOf(chemin)]):
            raise AssertionError("%s : taille changee" % chemin)
    if len(t) != len(t0):
        raise AssertionError("zones 98/99 : %d cases au lieu de %d"
                             % (len(t), len(t0)))
    n = 0
    for a, b in zip(g0 + t0, g + t):
        if a["objet"] == b["objet"]:
            continue
        n += 1
        if b["objet"] not in p:
            raise AssertionError("objet %d hors du pool" % b["objet"])
        if par_rang and abs(et.get(a["objet"], 0) - et.get(b["objet"], 0)) > 1:
            raise AssertionError("objet %d : plus d'une etoile d'ecart"
                                 % b["objet"])
    return n


if __name__ == "__main__":
    # python scripts/patch_points.py [rom.nds] [csv]  : la liste des points
    import csv
    import ndspy.rom
    import zones
    from rom_vanilla import chemin_vanilla
    rom = ndspy.rom.NintendoDSRom.fromFile(
        sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else chemin_vanilla())
    g, t = lire(rom)
    fr = objets.noms(rom, "fr", accents=True)
    en = objets.noms(rom, "en")
    lieux = zones.noms_zones(rom, "fr")
    lignes = ([("terrain", l["carte"], objets.avec_accents(
        lieux.get(l["carte"], "")), l["zone"], "", l["points"] or "",
        l["objet"], fr.get(l["objet"], ""), en.get(l["objet"], ""))
        for l in g]
        + [("special", "izmitm", "zones 98/99", "98/99", l["groupe"],
            l["rang"], l["objet"], fr.get(l["objet"], ""),
            en.get(l["objet"], "")) for l in t])
    entete = ("genre", "carte", "lieu", "zone", "groupe de partie",
              "points / case", "objet", "nom (fr)", "nom (en)")
    if len(sys.argv) > 2:
        with open(sys.argv[2], "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(entete)
            w.writerows(lignes)
        print("ecrit : %s (%d lignes)" % (sys.argv[2], len(lignes)))
    else:
        for l in lignes:
            print(";".join(str(x) for x in l))
