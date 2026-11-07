"""Sauvegarde forcee, sans question (ZER-116, 31/10/2026) : `<CHURCH=9>`.

Le gluant du royaume finit sa replique OUI par `<ADD><CHURCH=9>` : le jeu
ouvre alors une « eglise » qui affiche « Sauvegarde du journal en cours »,
sauve, puis « Sauvegarde du journal reussie », sans rien demander.

CE QUE LE JEU A DEJA (overlay 3, research §113). Une balise `<CHURCH=n>` en
fin de replique ouvre l'eglise de maniere m = n - 1 (objet eglise +0x5A0),
dont les messages sont `data/scenario/str_ch<m>.gp2`. La maniere 2
(`<CHURCH=3>`) est le JOURNAL du prologue (PNJ 217 de M01, sans modele) : elle
pose +0x5B4 et saute le menu du pretre, mais pose sa question (message 1000,
« Le journal est ouvert sur la table. Voulez-vous enregistrer votre
aventure ? <YESNO> »), concatenee au message 100 (« <YES>Sauvegarde du
journal en cours...<ADD><NO><CLOSE> »), et ATTEND la reponse (etat 2 de la
confession : fenetre en etat 6 puis 5, choix 0). Mesure : sans <YESNO>, la
fenetre reste sur « en cours » indefiniment.

CE QU'ON AJOUTE, pour une maniere 8 que le jeu n'emploie jamais (aucun texte
ne porte `<CHURCH=9>`, ni `<CHURCH=8>`) :
- `data/scenario/str_ch8.gp2` : les messages du journal, 1000 vide, 100 =
  « en cours » et 1011 = « reussie » pris a l'evenement de sauvegarde du jeu
  (ev29320) dans les cinq langues. Le prologue (maniere 2) ne change pas.
- overlay 3, deux sites :
  C `0x02159A24` (etat 4 de l'ouverture : la replique du PNJ est FINIE,
    fenetre en etat 3) -> RELAIS : maniere 8 -> +0x5B4 = 1, puis le code du
    jeu en 0x021599DC qui envoie a la confession (+0x588 = 3). Le chemin du
    journal (maniere 2) part, lui, AVANT la fin de la replique et l'ecrase :
    mesure, la question OUI/NON du gluant n'apparaissait jamais ;
  B `0x02159EDC` « +0x5B4 nul -> on continue » : PLUS touche depuis le
    01/11 ; la maniere 8 attend donc la reponse a SA question (celle du
    gluant, messages 1000/100), comme le journal.
  RELAIS (28 o) dans le bourrage de fin de l'overlay 3 (0x02180C84 ; le
  zero de 0x02180C80 termine la chaine "\\n" de 0x02180C7F, citee deux fois).
- Le DON (pierre, pages, drapeau) se fait en declencheur de GENRE 12 : l'eglise
  les joue juste avant d'ecrire (0x02159F58), le don est donc DANS la
  sauvegarde. Le genre 1 (apres la replique) ne tourne pas quand la replique
  ouvre une eglise (mesure : drapeau jamais pose).
"""
import struct

import fichiers_rom

MANIERE = 8
BALISE = "<CHURCH=%d>" % (MANIERE + 1)
SOURCE = "data/scenario/str_ch2.gp2"
CHEMIN = "data/scenario/str_ch%d.gp2" % MANIERE
EV = "data/evspt_lv5/ev29320.gp2"
LANGUES = ("fr", "en", "de", "es", "it")
OVL = 3
SITE_C, SITE_B = 0x02159A24, 0x02159EDC
CONFESSION = 0x021599DC              # « movne r0, #3 ; strbne +0x588 ... »
SUITE_B = 0x02159F40                 # la suite commune (« on continue »)
RELAIS = 0x02180C84
FIN_OVL = 0x02180CA0
ORIG_C = bytes.fromhex("0110a0e3")                   # mov r1, #1
ORIG_B = bytes.fromhex("b405d9e5" "000050e3" "1500000a")


# ---------------------------------------------------------------- messages
def nat_lire(d):
    """(ordre des ids, {id: decalage}, {id: texte}) d'un str_ch<m>_<lg>.nat :
    u32 (taille du pool << 12) | n, n x (id, decalage), pool sans bourrage."""
    h = struct.unpack_from("<I", d, 0)[0]
    n, taille = h & 0xFFF, h >> 12
    debut = 4 + 8 * n
    assert debut + taille == len(d), (debut, taille, len(d))
    ids = [struct.unpack_from("<II", d, 4 + 8 * k) for k in range(n)]
    textes = {i: d[debut + o:d.index(b"\0", debut + o)] for i, o in ids}
    return [i for i, _o in ids], dict(ids), textes


def nat_ecrire(d, remplacements):
    """Le .nat `d` ou les ids de `remplacements` ({id: octets}) changent ;
    les autres chaines gardent leur ordre et leurs partages (1010 = 1016)."""
    ordre, offs, textes = nat_lire(d)
    par_off = {}
    for i in ordre:
        par_off.setdefault(offs[i], []).append(i)
    pool, neuf = bytearray(), {}
    for o in sorted(par_off):
        ids = par_off[o]
        if any(i in remplacements for i in ids):
            for i in ids:
                neuf[i] = len(pool)
                pool += remplacements.get(i, textes[i]) + b"\0"
        else:
            for i in ids:
                neuf[i] = len(pool)
            pool += textes[ids[0]] + b"\0"
    out = bytearray(struct.pack("<I", len(pool) << 12 | len(ordre)))
    for i in ordre:
        out += struct.pack("<II", i, neuf[i])
    return bytes(out + pool)


def textes_jeu(rom, lg):
    """(en cours, reussie) de l'evenement de sauvegarde ev29320 (question,
    en cours, reussie), tels quels."""
    import objets
    d = objets._membre_archive(rom, EV, "ev29320_%s.bin" % lg)
    p = [s for s in d[0x40:].split(b"\0") if s and s[0] != 0xFF]
    if len(p) != 3 or not p[1].endswith(b"<ADD>"):
        raise SystemExit("ev29320_%s : textes inattendus" % lg)
    return p[1], p[2]


def textes(rom, lg):
    """{message: octets} de la maniere 8. Comme le journal du jeu : 1000 = la
    question (celle du gluant, zenus_royaume.don_eglise), 100 = « <YES> le
    don, puis en cours <ADD>\\n<NO> tant pis <CLOSE> », 1011 = reussie. Le
    NON ferme l'eglise comme celui du journal (01/11 : une replique <YESNO>
    qui ouvrait elle-meme l'eglise bloquait tout sur NON)."""
    import zenus_royaume
    en_cours, reussie = textes_jeu(rom, lg)
    question, oui, non = (t.encode("latin-1") for t in zenus_royaume.don_eglise(lg))
    return {1000: question,
            100: b"<YES>" + oui + b"<PAGE>" + en_cours + b"\\n<NO>" + non + b"<PAGE><CLOSE>",
            1011: reussie}


def messages(rom, lg):
    import objets
    d = objets._membre_archive(rom, SOURCE, "str_ch2_%s.nat" % lg)
    return nat_ecrire(d, textes(rom, lg))


def archive(rom):
    """str_ch8.gp2 : l'archive du journal, plus les membres str_ch8_<lg>.nat
    (le jeu cherche `str_ch%d_<LG>.nat` ; les membres str_ch2 restent, inertes)."""
    import gp2_ecrire
    return gp2_ecrire.ajouter(bytes(rom.getFileByName(SOURCE)), {
        "str_ch%d_%s.nat" % (MANIERE, lg): messages(rom, lg) for lg in LANGUES})


# -------------------------------------------------------------------- code
def code():
    from patch_hasard import assembler
    # C : etat 4 de l'ouverture, la replique du PNJ est finie (fenetre en
    # etat 3, r0 = 3). Maniere 8 : +0x5B4 = 1 puis le code du jeu en
    # 0x021599DC (+0x588 = 3 la confession, +0x580 = 0, sortie), sous NE.
    relais = assembler(["ldrb r1, [r4, #0x5a0]",
                        "cmp r1, #%d" % MANIERE,
                        "movne r1, #1",                 # l'instruction remplacee
                        "bne #%d" % (SITE_C + 4),
                        "movs r1, #1",                  # NE pour la suite du jeu
                        "strb r1, [r4, #0x5b4]",
                        "b #%d" % CONFESSION], RELAIS)
    c = assembler(["b #%d" % RELAIS], SITE_C)
    # B (0x02159EDC) n'est PLUS touche (01/11) : +0x5B4 pose, la maniere 8
    # attend la reponse a sa question comme le journal (maniere 2)
    return relais, c


def _poser(data, base, adr, octets, avant):
    o = adr - base
    if bytes(data[o:o + len(octets)]) != avant:
        raise SystemExit("overlay %d %08X : octets inattendus" % (OVL, adr))
    data[o:o + len(octets)] = octets


def patcher(rom):
    import ndspy.code
    ovl = rom.loadArm9Overlays()
    o = ovl[OVL]
    data = bytearray(o.data)
    base = o.ramAddress
    if base + len(data) != FIN_OVL:
        raise SystemExit("overlay 3 : fin %08X" % (base + len(data)))
    relais, c = code()
    _poser(data, base, RELAIS, relais, bytes(len(relais)))
    _poser(data, base, SITE_C, c, ORIG_C)
    o.data = bytes(data)
    rom.files[o.fileID] = o.save(compress=True)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovl)
    fichiers_rom.ajouter(rom, CHEMIN, archive(rom))


def verifier(rom):
    import objets
    o = rom.loadArm9Overlays()[OVL]
    d, base = bytes(o.data), o.ramAddress
    relais, c = code()
    for adr, octets in ((RELAIS, relais), (SITE_C, c), (SITE_B, ORIG_B)):
        if d[adr - base:adr - base + len(octets)] != octets:
            raise AssertionError("overlay 3 %08X" % adr)
    for lg in LANGUES:
        m = objets._membre_archive(rom, CHEMIN, "str_ch%d_%s.nat" % (MANIERE, lg))
        _o, _offs, t = nat_lire(m)
        attendu = textes(rom, lg)
        if any(t[i] != attendu[i] for i in attendu):
            raise AssertionError("str_ch8 %s : messages" % lg)
        # le reste = le journal du jeu, inchange
        _o2, _f2, t2 = nat_lire(objets._membre_archive(rom, SOURCE, "str_ch2_%s.nat" % lg))
        if any(t[i] != t2[i] for i in t2 if i not in (100, 1000, 1011)):
            raise AssertionError("str_ch8 %s : autres messages" % lg)
    return True
