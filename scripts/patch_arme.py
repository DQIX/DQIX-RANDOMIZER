"""L'arme de Zenus (ZER-116) : un objet NEUF, l'epee 20030, inseree a sa place
d'identifiant dans toutes les tables par objet du jeu (research §114).

Toutes ces tables portent l'identifiant et sont triees par lui ; le jeu y
cherche par identifiant (dichotomie dans `itemdt`, 0x020DE660) et le sac de la
sauvegarde garde des identifiants : inserer a sa place ne decale aucun nom.

    itemdt.gp2, itemdt_w.gp2   fiche d'objet (32 o, a +0x0C) + fiche d'equipement
                               (32 o) + bloc de 44 comptes ; pool des noms
    itemname.gp2               nom, pluriel, grammaire, id (16 o)
    itemexpl.gp2, iteminfo_<lg>.gp2   description (8 o : id, texte)
    itembtlprm.nat             44 o par objet, id a +40, parallele a itemdt
    itemsort.gp2               script Nitro : [id, n de liste, rang alpha, a, b]

La fiche d'equipement est inseree EN FIN DE SECTION DES ARMES (index 268 dans
itemdt) : les index suivants glissent de 1, les comptes « armes » et « epees »
du bloc de comptes aussi. Hors de toute liste : numero de liste 0 (le champ de
bits « trouve » de la sauvegarde est plein), 9999 dans itemsort. Invendable
(classe de prix 0, prix 0). Jamais tiree : `objets.HORS_TIRAGE`.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ID = 20030
SOURCE = 20029            # epee cosmique : la fiche recopiee (classe epee)
GENRE = 19164             # marteau de guerre : masculin dans les 4 langues a genre
ATTAQUE = 500             # 10 bits signes : 511 au plus (research §114.1)
VOCATIONS = 0xFFF         # les 12 vocations
MODELE = 30               # numero de modele p_w/d_w (poser_modeles) ; None = celui de SOURCE

TEXTES = {
    "fr": ("<'e>clair de Z<'e>nus", "<'e>clairs de Z<'e>nus",
           "<'E>clair forg<'e> par le Tout-Puissant. Rien ne r<'e>siste <`a> sa col<`e>re."),
    "en": ("bolt of Zenus", "bolts of Zenus",
           "A bolt forged by the Almighty himself. Nothing can withstand it."),
    "de": ("Zenus-Blitz[ges]", "Zenus-Blitze[dn]",
           "Ein vom Allm<:a>chtigen geschmiedeter Blitz. Nichts h<:a>lt ihm stand."),
    "es": ("rayo de Zenus", "rayos de Zenus",
           "Rayo forjado por el Todopoderoso. Nada resiste a su poder."),
    "it": ("fulmine di Zenus", "fulmini di Zenus",
           "Un fulmine forgiato dall<1>Onnipotente. Nulla gli resiste."),
}

ITEMDT = ("data/prm/itemdt.gp2", "data/prm/itemdt_w.gp2")
NOMS = "data/prm/itemname.gp2"
EXPL = "data/prm/itemexpl.gp2"
INFOS = "data/prm/iteminfo_%s.gp2"
BTLPRM = "data/prm/itembtlprm.nat"
TRI = "data/prm/itemsort.gp2"


def _lg(nom):
    return nom.rsplit("_", 1)[1][:2]


def _membres(rom, chemin):
    import gp2
    import gp2_ecrire
    import objets
    d = bytes(rom.files[rom.filenames.idOf(chemin)])
    gp2_ecrire.verifier_aller_retour(d)
    return d, {n: objets._membre_archive(rom, chemin, n)
               for n in gp2.GP2(chemin, donnees=d).noms}


def _ecrire(rom, chemin, d, clairs):
    import gp2_ecrire
    rom.files[rom.filenames.idOf(chemin)] = gp2_ecrire.reecrire(d, clairs)


# --- itemdt -----------------------------------------------------------------

def lire_itemdt(m):
    """(fiches, equipements, comptes, pool) d'un membre itemdt*."""
    n, ne = struct.unpack_from("<HH", m, 0)
    n &= 0xFFF
    lpool = struct.unpack_from("<I", m, 8)[0] & 0x7FFFFFFF
    neq, extra = ne & 0x7FFF, ne >> 15
    p = 0x0C
    fiches = [bytearray(m[p + 32 * i:p + 32 * i + 32]) for i in range(n)]
    p += 32 * n
    equip = [bytearray(m[p + 32 * i:p + 32 * i + 32]) for i in range(neq)]
    p += 32 * neq
    comptes = list(struct.unpack_from("<44H", m, p)) if extra else None
    p += 0x58 if extra else 0
    if p + lpool != len(m):
        raise AssertionError("itemdt : %d + %d != %d" % (p, lpool, len(m)))
    return fiches, equip, comptes, bytearray(m[p:])


def ecrire_itemdt(m, fiches, equip, comptes, pool):
    out = bytearray(m[:0x0C])
    struct.pack_into("<HH", out, 0, (struct.unpack_from("<H", m, 0)[0] & 0xF000) | len(fiches),
                     len(equip) | (0x8000 if comptes is not None else 0))
    struct.pack_into("<I", out, 8, len(pool))
    for f in fiches + equip:
        out += f
    if comptes is not None:
        out += struct.pack("<44H", *comptes)
    return bytes(out + pool)


def _id(f):
    return struct.unpack_from("<H", f, 0x18)[0]


def inserer_itemdt(m, lg, attaque=ATTAQUE, modele=MODELE):
    fiches, equip, comptes, pool = lire_itemdt(m)
    ids = [_id(f) for f in fiches]
    if ID in ids:
        raise ValueError("objet %d deja present" % ID)
    src = fiches[ids.index(SOURCE)]
    ie_src = struct.unpack_from("<I", src, 0)[0]
    # fin de la section des armes : apres la derniere fiche d'equipement d'arme
    armes = [struct.unpack_from("<I", f, 0)[0] for f in fiches
             if 19000 <= _id(f) < 21000]
    ie = max(armes) + 1
    if ie != len([a for a in armes]):
        raise AssertionError("armes : index %d pour %d armes" % (ie, len(armes)))
    for f in fiches:
        k = struct.unpack_from("<I", f, 0)[0]
        if k != 0xFFFFFFFF and k >= ie:
            struct.pack_into("<I", f, 0, k + 1)
    e = bytearray(equip[ie_src])
    w1 = struct.unpack_from("<I", e, 4)[0]
    struct.pack_into("<I", e, 4, (w1 & ~0xFFF) | VOCATIONS)
    w2 = struct.unpack_from("<I", e, 8)[0]
    struct.pack_into("<I", e, 8, (w2 & ~0x3FF) | (attaque & 0x3FF))
    equip.insert(ie, e)
    f = bytearray(src)
    struct.pack_into("<I", f, 0, ie)
    struct.pack_into("<I", f, 4, len(pool))
    pool += TEXTES[lg][0].encode("latin-1") + b"\0"
    fl = struct.unpack_from("<I", f, 8)[0]
    struct.pack_into("<I", f, 8, fl & ~0xE000)                  # classe de prix 0 : invendable
    w3 = struct.unpack_from("<I", f, 0x0C)[0]
    struct.pack_into("<I", f, 0x0C, w3 & 0xFFF)                 # numero de liste 0 : hors liste
    if modele is not None:
        # +0x10 = lettre << 20 | a << 10 | b : a et b egaux pour toutes les armes ;
        # MESURE (06/11) : b (bits 0-9) = modele ET icone ; a garde celui de SOURCE
        ic = struct.unpack_from("<I", f, 0x10)[0]
        struct.pack_into("<I", f, 0x10, (ic & ~0x3FF) | modele)
    struct.pack_into("<HH", f, 0x18, ID, 0)                     # prix de vente 0
    pos = next(i for i, x in enumerate(ids) if x > ID)
    fiches.insert(pos, f)
    if comptes is not None:
        cl = (w1 >> 12) & 0xF
        if comptes[0] != len(armes) or comptes[12] != 30 or cl != 1:
            raise AssertionError("comptes inattendus : %r" % comptes[:13])
        comptes[0] += 1
        comptes[12] += 1
    return ecrire_itemdt(m, fiches, equip, comptes, pool)


# --- tables a en-tete « n | pool << 12 » --------------------------------------

def _inserer_texte(m, pas, cle, valeurs, textes):
    """Insere une fiche de `pas` octets a la place de ID (cle = position de
    l'id dans la fiche) ; `valeurs(decalages)` rend la fiche."""
    h = struct.unpack_from("<I", m, 0)[0]
    n, lpool = h & 0xFFF, h >> 12
    base = 4 + n * pas
    if base + lpool != len(m):
        raise AssertionError("en-tete %#x" % h)
    ids = [struct.unpack_from("<H", m, 4 + i * pas + cle)[0] for i in range(n)]
    if ids != sorted(ids) or ID in ids:
        raise AssertionError("table non triee ou %d present" % ID)
    pool = bytearray(m[base:])
    dec = []
    for t in textes:
        dec.append(len(pool))
        pool += t.encode("latin-1") + b"\0"
    pos = next(i for i, x in enumerate(ids) if x > ID)
    fiches = bytearray(m[4:base])
    fiches[pos * pas:pos * pas] = valeurs(dec)
    return struct.pack("<I", (n + 1) | (len(pool) << 12)) + bytes(fiches) + bytes(pool)


def inserer_nom(m, lg):
    h = struct.unpack_from("<I", m, 0)[0]
    n = h & 0xFFF
    gram = [struct.unpack_from("<I", m, 4 + i * 16 + 8)[0] for i in range(n)
            if struct.unpack_from("<I", m, 4 + i * 16 + 12)[0] == GENRE]
    sing, plur, _d = TEXTES[lg]
    return _inserer_texte(m, 16, 12, lambda d: struct.pack("<IIII", d[0], d[1], gram[0], ID),
                          (sing, plur))


def inserer_expl(m, lg):
    return _inserer_texte(m, 8, 0, lambda d: struct.pack("<II", ID, d[0]), (TEXTES[lg][2],))


def inserer_btlprm(d):
    n = struct.unpack_from("<I", d, 0)[0]
    if 4 + n * 44 != len(d):
        raise AssertionError("itembtlprm : taille")
    ids = [struct.unpack_from("<H", d, 4 + i * 44 + 40)[0] for i in range(n)]
    if ids != sorted(ids) or ID in ids:
        raise AssertionError("itembtlprm : tri")
    r = bytearray(d[4 + ids.index(SOURCE) * 44:4 + ids.index(SOURCE) * 44 + 44])
    struct.pack_into("<H", r, 40, ID)
    pos = next(i for i, x in enumerate(ids) if x > ID)
    corps = bytearray(d[4:])
    corps[pos * 44:pos * 44] = r
    return struct.pack("<I", n + 1) + bytes(corps)


def _cle_alpha(s):
    import objets
    return objets.nettoyer(s).lower()


def inserer_tri(m, nom_lg):
    """itemsort : fiche [ID, 9999, rang, 0, 0] a la fin des 9999 tries par id ;
    le rang alphabetique prend sa place parmi les noms (les suivants +1)."""
    import prmtable
    t = prmtable.PrmTable(m, selon_entete=True)
    recs = t.records
    if recs[0].fields != [len(recs) - 1]:
        raise AssertionError("itemsort : compte")
    corps = recs[1:]
    if any(ID == r.fields[0] for r in corps):
        raise AssertionError("itemsort : deja present")
    src = next(r for r in corps if r.fields[0] == SOURCE)
    # rang : apres le plus grand nom <= le notre
    noms = nom_lg
    moi = _cle_alpha(TEXTES[noms["lg"]][0])
    avant = [r.fields[2] for r in corps if r.fields[0] in noms["noms"]
             and _cle_alpha(noms["noms"][r.fields[0]]) <= moi]
    rang = (max(avant) if avant else 0) + 1
    out = bytearray(m)
    for r in corps:
        if r.fields[2] >= rang:
            off = r.offset + (r.size - 4 * len(r.fields)) + 8
            struct.pack_into("<I", out, off, r.fields[2] + 1)
    neuf = bytes(out[src.offset:src.offset + src.size - 20]) + struct.pack(
        "<5I", ID, 9999, rang, src.fields[3], src.fields[4])
    # place : par numero de liste, puis par id parmi les 9999
    apres = [r for r in corps if (r.fields[1], r.fields[0]) > (9999, ID)]
    ou = apres[0].offset if apres else corps[-1].offset + corps[-1].size
    out[ou:ou] = neuf
    off0 = recs[0].offset + (recs[0].size - 4)
    struct.pack_into("<I", out, off0, len(corps) + 1)
    nb, taille = struct.unpack_from("<II", out, 0)
    struct.pack_into("<II", out, 0, nb + 1, taille + len(neuf))
    return bytes(out)


def _noms_par_id(m):
    h = struct.unpack_from("<I", m, 0)[0]
    n = h & 0xFFF
    base = 4 + n * 16
    out = {}
    for i in range(n):
        o, _p, _g, iid = struct.unpack_from("<IIII", m, 4 + i * 16)
        out[iid] = m[base + o:m.index(b"\0", base + o)].decode("latin-1")
    return out


# --- qui peut l'equiper -------------------------------------------------------
# « Peut-il equiper ? » (ARM9 0x020DD500, research §114.5) : pour une arme ou un
# bouclier, la classe (mot 0 bits 7-10) doit etre celle d'un des 4 arbres de la
# vocation (0x020DD164) ou d'une exception (0x020DD210) ; le masque de vocations
# (mot 1 bits 0-11) ne sert qu'aux autres pieces. Reecrit en place, meme taille :
# une arme dont le masque est NON NUL saute le test de classe (et le test du
# masque reste saute pour les armes : tout le monde). Toutes les armes et tous
# les boucliers du jeu ont un masque nul : rien ne change pour eux.
VOC_SITE = 0x020DD5A8
VOC_ORIGINE = (0xE5951000, 0xE20600FF, 0xE5911000, 0xE1A01A81, 0xE1A01E21,
               0xE20110FF, 0xEBFFFF12, 0xE3500000, 0x13A01000, 0x1A000009,
               0xE5951000, 0xE1A00006, 0xE5911000, 0xE1A01A81, 0xE1A01E21,
               0xE20110FF, 0xEBFFFEDD, 0xE3500000, 0x13A01000, 0x03A01001)
VOC_GREFFE = [
    "ldr r1, [r5]",
    "ldr r0, [r1, #4]",
    "movs r0, r0, lsl #20",         # masque de vocations non nul ?
    "bne #0x020DD5CC",              # -> r0 != 0 : permis, sans test de classe
    "ldr r1, [r1]",
    "mov r1, r1, lsr #7",
    "and r1, r1, #0xf",             # classe, bits 7-10
    "and r0, r6, #0xff",
    "bl #0x020DD210",
    "cmp r0, #0",                   # 0x020DD5CC
    "movne r1, #0",
    "bne #0x020DD5F8",
    "ldr r1, [r5]",
    "ldr r1, [r1]",
    "mov r1, r1, lsr #7",
    "and r1, r1, #0xf",
    "mov r0, r6",
    "bl #0x020DD164",
    "clz r1, r0",                   # r1 = (r0 == 0)
    "mov r1, r1, lsr #5",
]


def poser_vocations(rom):
    import ndspy.codeCompression as cc
    from patch_hasard import COMPRESSED_END, assembler
    arm9 = bytearray(cc.decompress(bytes(rom.arm9)))
    o = VOC_SITE - 0x02000000
    code = assembler(VOC_GREFFE, VOC_SITE)
    if len(code) != 4 * len(VOC_ORIGINE):
        raise AssertionError("greffe des vocations : %d o" % len(code))
    lu = struct.unpack_from("<20I", arm9, o)
    if bytes(arm9[o:o + len(code)]) == code:
        return
    if lu != VOC_ORIGINE:
        raise SystemExit("arme : ARM9 %#010x inattendu" % VOC_SITE)
    arm9[o:o + len(code)] = code
    struct.pack_into("<I", arm9, COMPRESSED_END, 0)
    rom.arm9 = bytes(arm9)


# Le panneau « Convient a » (overlay 23, 0x021DF2F4) fait le meme choix pour
# chacune des 12 icones : classe non nulle -> 0x020DD1AC(vocation, classe),
# sinon le masque. Reecrit en place, meme taille : masque non nul -> masque
# d'abord. r8 (0xE / 0xF) ne servait qu'a porter le resultat : les drapeaux
# le portent directement.
PAN_OVL = 23
PAN_SITE = 0x021DF2F4
PAN_ORIGINE = (0xE5990000, 0xE3A0800E, 0xE1A00A80, 0xE1B00E20, 0x0A000004,
               0xE20010FF, 0xE1A00006, 0xEBFBF7A5, 0xE3500000, 0xEA000005,
               0xE1A0071B, 0xE5991004, 0xE1A00800, 0xE1A01A01, 0xE1A00820,
               0xE1100A21, 0x13A0800F, 0xE358000E, 0x03A00001, 0x01844710)
PAN_GREFFE = [
    "ldr r0, [sb, #4]",
    "movs r0, r0, lsl #20",         # masque de vocations non nul ?
    "bne #0x021DF320",
    "ldr r0, [sb]",
    "mov r0, r0, lsl #21",
    "movs r1, r0, lsr #28",         # classe, bits 7-10
    "beq #0x021DF320",
    "mov r0, r6",
    "bl #0x020DD1AC",
    "cmp r0, #0",
    "b #0x021DF338",
    "lsl r0, fp, r7",               # 0x021DF320 : le masque, comme le jeu
    "ldr r1, [sb, #4]",
    "lsl r0, r0, #0x10",
    "lsl r1, r1, #0x14",
    "lsr r0, r0, #0x10",
    "tst r0, r1, lsr #20",
    "moveq r0, #1",                 # 0x021DF338 : pas permis -> bit de l'icone
    "orreq r4, r4, r0, lsl r7",
    "mov r0, r0",
]


def poser_panneau(rom):
    import ndspy.code
    from patch_hasard import assembler
    ovl = rom.loadArm9Overlays()
    o = ovl[PAN_OVL]
    d = bytearray(o.data)
    p = PAN_SITE - o.ramAddress
    code = assembler(PAN_GREFFE, PAN_SITE)
    if len(code) != 80:
        raise AssertionError("greffe du panneau : %d o" % len(code))
    if bytes(d[p:p + 80]) == code:
        return
    if struct.unpack_from("<20I", d, p) != PAN_ORIGINE:
        raise SystemExit("arme : overlay 23 %#010x inattendu" % PAN_SITE)
    d[p:p + 80] = code
    o.data = bytes(d)
    rom.files[o.fileID] = o.save(compress=True)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovl)


def panneau_pose(rom):
    from patch_hasard import assembler
    o = rom.loadArm9Overlays()[PAN_OVL]
    p = PAN_SITE - o.ramAddress
    return bytes(o.data[p:p + 80]) == assembler(PAN_GREFFE, PAN_SITE)


def vocations_posees(rom):
    import ndspy.codeCompression as cc
    from patch_hasard import assembler
    arm9 = cc.decompress(bytes(rom.arm9))
    o = VOC_SITE - 0x02000000
    return bytes(arm9[o:o + 80]) == assembler(VOC_GREFFE, VOC_SITE)


# --- le butin de Zenus ----------------------------------------------------------
# Espece 900 (fiche 437 de mon_btldata) : objet RARE = l'arme, classe 0
# (« toujours », research §81 ; un combat scripte garde les classes de
# mon_btldata, §90.1), objet commun vide.
ZENUS_FICHE = 437
ZENUS_ESPECE = 900


def butin_zenus(rom):
    import patch_stats as P
    fb = P._fid(rom, P.BTL)
    btl = bytearray(rom.files[fb])
    o = P.ENTETE + ZENUS_FICHE * P.BTL_TAILLE
    if struct.unpack_from("<H", btl, o)[0] & 0x7FFF != ZENUS_ESPECE:
        raise AssertionError("mon_btldata : fiche %d n'est pas l'espece %d" % (ZENUS_FICHE, ZENUS_ESPECE))
    btl[o + 2] = 0                       # classe commune (objet vide : rien)
    btl[o + 3] = 0                       # classe rare : toujours
    struct.pack_into("<HH", btl, o + 4, 0, ID)
    rom.files[fb] = bytes(btl)


# Avec --butin-combat, la greffe de l'overlay 23 (patch_butin, research §90.2)
# remplace tout objet non nul : `patch_butin.poser_garde` la reecrit en place,
# meme longueur, pour qu'elle rende l'arme telle quelle (patch_butin.GARDE).
# Pas de place pour un relais : l'overlay 23 est plein jusqu'a 0x02200160.


# --- le modele ------------------------------------------------------------------
# Deux modeles par arme : p_wNNN (chara_pc.gp2) et d_wNNN (chara_pd.gp2), NNN =
# numero de modele de la fiche (+0x10, research §114.4). Le 030 est libre. Les
# deux sont faits a la construction depuis l'epee du guerrier (000) par
# work/arme/eclair.py : lame remplacee par un eclair, palette or / jaune-blanc.
NUM_MODELE = 30
MODELES = (("data/pack_lv5/chara_pc.gp2", "p_w%03d.nsbmd", 4.0),   # s < 4 : la lame
           ("data/pack_lv5/chara_pd.gp2", "d_w%03d.nsbmd", 16.0))
SOURCE_MODELE = 0


def poser_modeles(rom):
    import gp2
    import gp2_ecrire
    import objets
    import eclair
    for chemin, gabarit, s_lame in MODELES:
        fid = rom.filenames.idOf(chemin)
        d = bytes(rom.files[fid])
        nom = gabarit % NUM_MODELE
        if nom in gp2.GP2(chemin, donnees=d).noms:
            continue
        base = objets._membre_archive(rom, chemin, gabarit % SOURCE_MODELE)
        rom.files[fid] = gp2_ecrire.ajouter(d, {nom: eclair.construire(base, s_lame)})


# L'ICONE vient du meme numero (bits 0-9 de +0x10, mesure : avec 30, modele
# ET icone 30, case vide sans fichier) : `data/ani/d_w%03d.spr`. Copie de
# l'icone de l'epee source, palette (16 couleurs a +0x150) passee a l'or et au
# jaune-blanc comme le modele ; l'indice 0 (transparent) garde sa valeur.
ICONE = "data/ani/d_w%03d.spr"
ICONE_PALETTE = 0x150


def icone(rom):
    import eclair
    d = bytearray(rom.getFileByName(ICONE % SOURCE_MODELE))
    if struct.unpack_from("<HHH", d, 0x170)[0] != 0x28:
        raise AssertionError("icone : format inattendu")
    for k in range(1, 16):
        p = ICONE_PALETTE + 2 * k
        c = struct.unpack_from("<H", d, p)[0]
        struct.pack_into("<H", d, p, eclair.dorer(c))
    return bytes(d)


def poser_icone(rom):
    import fichiers_rom
    if rom.filenames.idOf(ICONE % NUM_MODELE) is None:
        fichiers_rom.ajouter(rom, ICONE % NUM_MODELE, icone(rom))


def modeles_poses(rom):
    import gp2
    return all((g % NUM_MODELE) in gp2.GP2(c, donnees=bytes(rom.files[rom.filenames.idOf(c)])).noms
               for c, g, _s in MODELES)


# --- tout ---------------------------------------------------------------------

def patcher(rom, attaque=ATTAQUE, modele=MODELE, bavard=True):
    for chemin in ITEMDT:
        d, ms = _membres(rom, chemin)
        _ecrire(rom, chemin, d, {n: inserer_itemdt(m, _lg(n), attaque, modele) for n, m in ms.items()})
    d, ms = _membres(rom, NOMS)
    noms = {_lg(n): _noms_par_id(m) for n, m in ms.items()}
    _ecrire(rom, NOMS, d, {n: inserer_nom(m, _lg(n)) for n, m in ms.items()})
    d, ms = _membres(rom, EXPL)
    neufs = {n: inserer_expl(m, _lg(n)) for n, m in ms.items()}
    _ecrire(rom, EXPL, d, neufs)
    import objets
    for n, m in neufs.items():
        info = INFOS % _lg(n)
        di, mi = _membres(rom, info)
        if n not in mi:
            raise AssertionError("%s sans %s" % (info, n))
        _ecrire(rom, info, di, {n: m})
    fid = rom.filenames.idOf(BTLPRM)
    rom.files[fid] = inserer_btlprm(bytes(rom.files[fid]))
    d, ms = _membres(rom, TRI)
    _ecrire(rom, TRI, d, {n: inserer_tri(m, {"lg": _lg(n), "noms": noms[_lg(n)]})
                          for n, m in ms.items()})
    poser_vocations(rom)
    if modele is not None:
        poser_modeles(rom)
    poser_panneau(rom)
    butin_zenus(rom)
    import patch_butin
    if patch_butin.GARDE != ID:
        raise AssertionError("patch_butin.GARDE != %d" % ID)
    if patch_butin.poser_garde(rom) and bavard:
        print("  butin a chaque combat : l'arme gardee")
    import bestiaire
    bestiaire.accorder(rom, None)      # la fiche de Zenus montre l'arme (ESPECES_FIXES)
    if modele is not None:
        poser_icone(rom)               # en dernier : insere un fichier NitroFS
    if bavard:
        print("  arme %d : attaque %d, vocations %#x" % (ID, attaque, VOCATIONS))
    verifier(rom, attaque)


def verifier(rom, attaque=ATTAQUE):
    """Relit la ROM : l'arme a sa place partout, les autres objets inchanges
    (memes champs, index d'equipement suivis)."""
    for chemin in ITEMDT:
        _d, ms = _membres(rom, chemin)
        for n, m in ms.items():
            fiches, equip, comptes, pool = lire_itemdt(m)
            ids = [_id(f) for f in fiches]
            assert ids == sorted(ids) and ids.count(ID) == 1, (n, "tri")
            f = fiches[ids.index(ID)]
            e = equip[struct.unpack_from("<I", f, 0)[0]]
            w1, w2 = struct.unpack_from("<II", e, 4)
            att = ((w2 & 0x3FF) ^ 0x200) - 0x200
            assert att == attaque and w1 & 0xFFF == VOCATIONS and (w1 >> 12) & 0xF == 1, n
            nom = pool[struct.unpack_from("<I", f, 4)[0]:].split(b"\0")[0]
            assert nom == TEXTES[_lg(n)][0].encode("latin-1"), (n, nom)
            assert struct.unpack_from("<I", f, 0x0C)[0] >> 12 == 0, n
            assert (struct.unpack_from("<I", f, 8)[0] >> 13) & 7 == 0, n
            # chaque fiche pointe une fiche d'equipement de sa classe
            for g in fiches:
                k = struct.unpack_from("<I", g, 0)[0]
                assert k == 0xFFFFFFFF or k < len(equip), (n, _id(g))
    _d, ms = _membres(rom, NOMS)
    for n, m in ms.items():
        assert _noms_par_id(m)[ID] == TEXTES[_lg(n)][0], n
    d = bytes(rom.files[rom.filenames.idOf(BTLPRM)])
    ids = [struct.unpack_from("<H", d, 4 + i * 44 + 40)[0] for i in range(struct.unpack_from("<I", d, 0)[0])]
    assert ids == sorted(ids) and ID in ids
    import prmtable
    _d, ms = _membres(rom, TRI)
    for n, m in ms.items():
        t = prmtable.PrmTable(m, selon_entete=True)
        c = t.records[1:]
        # rangs alphabetiques : 1..n (l'espagnol a 3 doublons d'origine, noms identiques)
        rk = [r.fields[2] for r in c]
        assert t.records[0].fields == [len(c)] and min(rk) == 1 and max(rk) <= len(c), n
        assert sum(r.fields[0] == ID for r in c) == 1, n
        cle = [(r.fields[1], r.fields[0]) for r in c]
        assert cle == sorted(cle) or [x[0] for x in cle] == sorted(x[0] for x in cle), n
    assert vocations_posees(rom), "greffe des vocations absente"
    assert panneau_pose(rom), "greffe du panneau absente"
    assert MODELE is None or modeles_poses(rom), "modeles de l'arme absents"
    assert MODELE is None or rom.filenames.idOf(ICONE % NUM_MODELE) is not None, "icone absente"
    import patch_butin
    import patch_stats as P
    btl = rom.files[P._fid(rom, P.BTL)]
    o = P.ENTETE + ZENUS_FICHE * P.BTL_TAILLE
    assert btl[o + 3] == 0 and struct.unpack_from("<H", btl, o + 6)[0] == ID, "butin de Zenus"
    assert patch_butin.lire(rom) is None or patch_butin.garde_posee(rom), "garde du butin absente"
    import bestiaire
    info = rom.files[rom.filenames.idOf(bestiaire.CHEMIN)]
    assert struct.unpack_from("<H", info, bestiaire.ENTETE + ZENUS_FICHE * bestiaire.PAS + 10)[0] == ID, "bestiaire de Zenus"
    return True


if __name__ == "__main__":
    import ndspy.rom
    src, dst = sys.argv[1], sys.argv[2]
    rom = ndspy.rom.NintendoDSRom.fromFile(src)
    patcher(rom)
    data = bytearray(rom.save())
    taille = os.path.getsize(src)
    if len(data) < taille:
        data += b"\xff" * (taille - len(data))
    open(dst, "wb").write(data)
    print("ecrit", dst)
