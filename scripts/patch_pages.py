#!/usr/bin/env python3
"""Les bouts de page : un objet important qui tombe au hasard des combats.

POUR QUOI. La quete cachee de la 1.8 (ZER-116) : quatre bouts de page. Le
fantome d'Ablithia donne le premier (patch_zenus) ; ensuite un combat gagne
a 1 chance sur TAUX d'en donner un, tant que le sac en a DE 1 A NB_PAGES-1.
Sans page -- avant le fantome, ou apres que le gluant les a prises -- rien
ne tombe (choix du joueur, 30/10). C'est UN SEUL objet, empile (x1 a x4).

L'OBJET. Le jeu n'a pas d'objet vide ; les deux pierres de debogage ne se
trouvent nulle part (objets.DEBUG, hors de tout tirage). La page est la
PIERRE DE BONIMENT (22126) : renommee dans les cinq langues
(`itemname_<lg>.nat`, et le nom des fiches `itemdt`), redecrite
(`itemexpl_<lg>.nat`), et elle prend au permis de conduire (22177) ses
reglages d'objet important : drapeaux (+0x04), icone et pile (+0x08), sans
effet (+0x10), et ses drapeaux de grammaire (`itemname` +0x08). Le permis
lui-meme n'est pas touche : c'est la recompense d'une autre quete (premier
essai : la page le remplacait, refuse par le joueur le 30/10).

LE TIRAGE (research §111, fonction de butin de l'overlay 23, §81). Apres
tous les tirages de butin, la liste des butins (entrees de 6 octets a
`sb`, compte en `sl+0x5900`, 8 au plus) part vers les messages et le sac.
On y ajoute une entree, comme un butin commun du dernier monstre parcouru :
le jeu affiche le coffre, le message et range l'objet lui-meme.

    0x021F4914  bhs 0x021F4B68  ->  bhs 0x021F4B70   (liste pleine : on saute)
    0x021F4B58  bhs 0x021F4B68  ->  bhs 0x021F4B70
    0x021F4B68  add r0, sl, #0x5000  ->  add fp, sl, #0x5900
    0x021F4B6C  ldrb r0, [r0, #0x900] ->  b PAGE

On n'arrive donc a PAGE que si la liste a de la place, et l'on rend la main
a 0x021F4B70 (`cmp r0, #0`) avec r0 = le compte. `fp`, `r5`, `r6` et `r8`
sont morts a cet endroit (relu : la suite n'emploie que r4-r7 apres les
avoir reposes, sl et sp ; le chemin `beq 0x021F4BF4` est l'epilogue, qui
les depile) ; `r8` pointe encore la fiche du dernier monstre
parcouru, d'ou l'espece (le message la masque a 15 bits, 0x021CD3BC).

OU. Derriere le BSS de l'overlay 23, comme la greffe du butin
(patch_butin) : derriere elle si elle y est, sinon a 0x021FFF40. 88 octets ;
avec le butin en mode `rares` il en reste 88 apres alignement, au mot pres.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

OVL = 23
PAGE = 22126                    # l'ancienne pierre de boniment (debogage)
MODELE = 22177                  # le permis de conduire : ses reglages
ICONE = 22250                   # parchemin des anciens : son icone (le
                                # permis fait carte d'identite, joueur 30/10)
NB_PAGES = 4
TAUX = 30                       # une chance sur TAUX par combat gagne
PLAFOND_SLOT = 0x02200160       # fin de l'overlay 24 (patch_butin)
BSS_VANILLA = 0x560
RAND_BELOW = 0x02032380         # r0 = [0, r0[
JEU = 0x0200F398                # l'objet de partie
SAC = 0x02010838                # son sac
COMPTE_OBJET = 0x02086AFC       # (sac, objet) -> nombre (test 0x12, §111)
RETOUR = 0x021F4B70

# (adresse, instruction d'origine, instruction posee ou None = branche)
SITES = (
    (0x021F4914, "bhs #0x21f4b68", "bhs #%d" % RETOUR),
    (0x021F4B58, "bhs #0x21f4b68", "bhs #%d" % RETOUR),
    (0x021F4B68, "add r0, sl, #0x5000", "add fp, sl, #0x5900"),
    (0x021F4B6C, "ldrb r0, [r0, #0x900]", None),
)

# Noms (singulier, pluriel) et description, balises du jeu. Le genre suit
# celui du permis dans chaque langue : masculin en francais, feminin en
# allemand, espagnol et italien.
TEXTES = {
    "fr": ("bout de page", "bouts de page",
           "Lambeau d<1>un livre tr<`e>s ancien. On y devine le nom de "
           "C<'e>lestelle et le mot <66>v<oe>u<99>."),
    "en": ("torn page", "torn pages",
           "A scrap from a very old book. The name Celestria and the word "
           "<6>wish<9> can just be made out."),
    "de": ("Buchseite", "Buchseiten",
           "Fetzen eines uralten Buches. Man erkennt den Namen Celestria und "
           "das Wort Wunsch."),
    "es": ("p<'a>gina arrancada", "p<'a>ginas arrancadas",
           "Trozo de un libro muy antiguo. Se lee el nombre de Dafne y la "
           "palabra <66>deseo<99>."),
    "it": ("pagina strappata", "pagine strappate",
           "Frammento di un libro antichissimo. Si leggono il nome di "
           "Angelica e la parola <66>desiderio<99>."),
}
NOMS = "data/prm/itemname.gp2"
EXPL = "data/prm/itemexpl.gp2"
# Le nom vit AUSSI dans les fiches d'objets : `itemdt.gp2` (la table que le
# jeu lit, research §83.10) et `itemdt_t.gp2`. C'est celui-la que montrent
# les objets importants : le premier essai, `itemname` seul renomme,
# affichait encore « permis de conduire ». Fiches de 32 octets a +0x10
# (nombre sur les 12 bits faibles de +0x00), +0x00 = decalage du nom
# (singulier) dans le pool, +0x14 = identifiant ; le pool finit le membre,
# sa longueur est a +0x08.
FICHES = ("data/prm/itemdt.gp2", "data/prm/itemdt_t.gp2")
# Ce que la page prend a la fiche du permis : +0x04 drapeaux (quartet 9 =
# objet important, classe de prix 0 = invendable), +0x08 (bits 0-11 : la
# pile ; bits 12+ : un rang propre a chaque objet), +0x10 (effets : aucun).
# Et a celle d'ICONE : +0x0C, la reference de l'icone (lettre de categorie
# << 20, puis deux fois id % 1000 sur 10 bits ; la pierre de boniment,
# 0x0691F87E, n'a pas d'image : essai 3, la page s'affichait sans icone).
# +0x14 est l'identifiant : on n'y touche pas.
REGLAGES = ((0x04, MODELE), (0x08, MODELE), (0x0C, ICONE), (0x10, MODELE))
# La description vit en double : `itemexpl.gp2` et le membre `itemexpl_<lg>`
# de `iteminfo_<lg>.gp2`, identique, que le jeu affiche (essai 3 : la page
# disait encore « DEBUG: USE FOR A WIPE-OUT. »).
INFOS = "data/prm/iteminfo_%s.gp2"


def greffe(adr, taux=TAUX):
    from patch_hasard import assembler
    return assembler([
        "ldrb r5, [fp]",                # le compte de la liste (< 8 ici)
        "bl #%d" % JEU,
        "bl #%d" % SAC,
        "ldr r1, [pc, #{L0}]",
        "bl #%d" % COMPTE_OBJET,
        "sub r6, r0, #1",               # pages - 1 : 0..2 voulu, non signe
        "mov r0, #%d" % taux,
        "bl #%d" % RAND_BELOW,
        # tirage != 0 : hs (r0 > 0 en non signe) ; sinon pages - 1 >= 3 : hs
        "cmp r0, #0",
        "cmpeq r6, #%d" % (NB_PAGES - 1),
        "bhs #{@fin}",
        # L'ENTREE, comme 0x021F4AD8-0x021F4B04 : objet, espece, genre 1
        # (commun) et porteur -1 (le monstre) d'un seul strh.
        "ldr r0, [pc, #{L0}]",
        "strh r0, [sb]",
        "ldrh r1, [r8, #2]",
        "strh r1, [sb, #2]",
        "mvn r0, #0xFE",
        "strh r0, [sb, #4]",
        "add r5, r5, #1",
        "strb r5, [fp]",
        "fin:",
        "mov r0, r5",
        "b #%d" % RETOUR,
    ], adr, litteraux=(PAGE,))


def _desas(data, base, adr):
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
    o = adr - base
    ins = next(md.disasm(bytes(data[o:o + 4]), adr), None)
    return ("%s %s" % (ins.mnemonic, ins.op_str)) if ins else "?"


def _emplacement(o):
    """Ou poser la greffe dans l'overlay `o` tel qu'il est."""
    base = o.ramAddress
    if o.bssSize == BSS_VANILLA and len(o.data) == o.ramSize:
        return base + o.ramSize + o.bssSize, True       # 0x021FFF40
    if o.bssSize == 0:
        return (base + len(o.data) + 3) & ~3, False     # derriere le butin
    raise SystemExit("overlay 23 : disposition inattendue")


def patcher_code(rom, taux=TAUX):
    import ndspy.code
    from patch_hasard import assembler
    ovl = rom.loadArm9Overlays()
    o = ovl[OVL]
    base = o.ramAddress
    d = bytearray(o.data)
    for adr, avant, _apres in SITES:
        lu = _desas(d, base, adr)
        if lu != avant:
            raise SystemExit("overlay 23 : a %#010x attendu %r, lu %r"
                             % (adr, avant, lu))
    adr, vierge = _emplacement(o)
    code = greffe(adr, taux)
    if adr + len(code) > PLAFOND_SLOT:
        raise SystemExit("bouts de page : %d o a %#010x, depasse la place "
                         "des overlays 22-30 (%d o libres)"
                         % (len(code), adr, PLAFOND_SLOT - adr))
    if vierge:
        d += bytes(o.bssSize)           # le BSS devient de la donnee
    d += bytes(adr - base - len(d))     # alignement
    d += code
    for site, _avant, apres in SITES:
        ins = assembler([apres if apres else "b #%d" % adr], site)
        d[site - base:site - base + 4] = ins
    o.data = bytes(d)
    o.ramSize = len(d)
    o.bssSize = 0
    rom.files[o.fileID] = o.save(compress=True)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovl)
    return adr, len(code)


def _table_textes(d, pas):
    """(n, debut du pool, longueur du pool) d'un .nat a en-tete
    `n | longueur_pool << 12`, fiches de `pas` octets."""
    h = struct.unpack_from("<I", d, 0)[0]
    n, lpool = h & 0xFFF, h >> 12
    pool = 4 + n * pas
    if pool + lpool != len(d):
        raise AssertionError("en-tete %#x : %d + %d != %d"
                             % (h, pool, lpool, len(d)))
    return n, pool, lpool


def _ajouter(d, pas, ecrits):
    """Ajoute des chaines au bout du pool et rend (octets, {cle: decalage})."""
    n, pool, lpool = _table_textes(d, pas)
    out = bytearray(d)
    decal = {}
    for cle, texte in ecrits:
        decal[cle] = len(out) - pool
        out += texte.encode("latin1") + b"\0"
    while (len(out) - pool) % 4:
        out += b"\0"
    struct.pack_into("<I", out, 0, n | ((len(out) - pool) << 12))
    return out, decal


def patcher_textes(rom, page=PAGE, textes=TEXTES):
    import gp2_ecrire
    import objets
    for chemin, pas in ((NOMS, 16), (EXPL, 8)):
        fid = rom.filenames.idOf(chemin)
        d = bytes(rom.files[fid])
        gp2_ecrire.verifier_aller_retour(d)
        import gp2
        arc = gp2.GP2(chemin, donnees=d)
        clairs = {}
        for nom in arc.noms:
            lg = nom.rsplit("_", 1)[1][:2]
            sing, plur, desc = textes[lg]
            m = objets._membre_archive(rom, chemin, nom)
            n, _pool, _l = _table_textes(m, pas)
            if pas == 16:
                fiches = [i for i in range(n) if struct.unpack_from(
                    "<I", m, 4 + i * 16 + 12)[0] == page]
                if len(fiches) != 1:
                    raise AssertionError("%s : %d fiches %d" % (nom, len(fiches), page))
                gram = [struct.unpack_from("<I", m, 4 + i * 16 + 8)[0]
                        for i in range(n) if struct.unpack_from(
                            "<I", m, 4 + i * 16 + 12)[0] == MODELE]
                m, dec = _ajouter(m, pas, (("s", sing), ("p", plur)))
                o = 4 + fiches[0] * 16
                struct.pack_into("<III", m, o, dec["s"], dec["p"], gram[0])
            else:
                fiches = [i for i in range(n) if struct.unpack_from(
                    "<I", m, 4 + i * 8)[0] == page]
                if len(fiches) != 1:
                    raise AssertionError("%s : %d fiches %d" % (nom, len(fiches), page))
                m, dec = _ajouter(m, pas, (("d", desc),))
                struct.pack_into("<I", m, 4 + fiches[0] * 8 + 4, dec["d"])
            clairs[nom] = bytes(m)
        if chemin == EXPL:
            for nom, m in clairs.items():
                lg = nom.rsplit("_", 1)[1][:2]
                info = INFOS % lg
                if objets._membre_archive(rom, info, nom) != \
                        objets._membre_archive(rom, EXPL, nom):
                    raise AssertionError("%s : %s differe d'itemexpl" % (info, nom))
                fi = rom.filenames.idOf(info)
                di = bytes(rom.files[fi])
                gp2_ecrire.verifier_aller_retour(di)
                rom.files[fi] = gp2_ecrire.reecrire(di, {nom: m})
        rom.files[fid] = gp2_ecrire.reecrire(d, clairs)
    for chemin in FICHES:
        fid = rom.filenames.idOf(chemin)
        d = bytes(rom.files[fid])
        gp2_ecrire.verifier_aller_retour(d)
        import gp2
        clairs = {}
        for nom in gp2.GP2(chemin, donnees=d).noms:
            lg = nom.rsplit("_", 1)[1][:2]
            m = bytearray(objets._membre_archive(rom, chemin, nom))
            r, _debut, lpool = _fiche(m, page)
            for k, source in REGLAGES:
                f, _d, _l = _fiche(m, source)
                m[r + k:r + k + 4] = m[f + k:f + k + 4]
            ecrit = textes[lg][0].encode("latin1") + b"\0"
            struct.pack_into("<I", m, r, lpool)
            struct.pack_into("<I", m, 8, lpool + len(ecrit))
            clairs[nom] = bytes(m + ecrit)
        rom.files[fid] = gp2_ecrire.reecrire(d, clairs)


def _fiche(m, page):
    """(position de la fiche de `page`, debut du pool, longueur du pool)
    dans un membre `itemdt*`."""
    n = struct.unpack_from("<I", m, 0)[0] & 0xFFF
    lpool = struct.unpack_from("<I", m, 8)[0]
    debut = len(m) - lpool
    fiches = [16 + i * 32 for i in range(n)
              if struct.unpack_from("<H", m, 16 + i * 32 + 0x14)[0] == page]
    if len(fiches) != 1 or 16 + n * 32 > debut:
        raise AssertionError("itemdt : %d fiches %d" % (len(fiches), page))
    return fiches[0], debut, lpool


def nom_fiche(m, page):
    r, debut, _l = _fiche(m, page)
    o = debut + struct.unpack_from("<I", m, r)[0]
    return bytes(m[o:m.index(b"\0", o)])


def patcher(rom, taux=TAUX, bavard=True):
    adr, n = patcher_code(rom, taux)
    patcher_textes(rom)
    if bavard:
        print("  %d o a %#010x, 1 chance sur %d par combat, objet %d"
              % (n, adr, taux, PAGE))
    return adr


def lire(rom):
    """L'adresse de la greffe posee dans `rom`, ou None."""
    o = rom.loadArm9Overlays()[OVL]
    base = o.ramAddress
    lu = _desas(o.data, base, SITES[-1][0])
    if not lu.startswith("b #"):
        return None
    return int(lu[3:], 16)


def verifier(rom, taux=TAUX):
    """Relit la ROM : les quatre sites, la greffe, et les textes."""
    import objets
    from patch_hasard import assembler
    o = rom.loadArm9Overlays()[OVL]
    base = o.ramAddress
    adr = lire(rom)
    if adr is None:
        raise AssertionError("bouts de page : greffe absente")
    for site, _avant, apres in SITES:
        attendu = assembler([apres if apres else "b #%d" % adr], site)
        if bytes(o.data[site - base:site - base + 4]) != attendu:
            raise AssertionError("bouts de page : site %#010x" % site)
    code = greffe(adr, taux)
    if bytes(o.data[adr - base:adr - base + len(code)]) != code:
        raise AssertionError("bouts de page : greffe inattendue")
    for lg, (sing, _p, desc) in TEXTES.items():
        if objets.noms(rom, lg, brut=True).get(PAGE) != sing:
            raise AssertionError("bouts de page : nom %s" % lg)
        m = objets._membre_archive(rom, EXPL, "itemexpl_%s.nat" % lg)
        n, pool, _l = _table_textes(m, 8)
        off = dict(struct.unpack_from("<2I", m, 4 + i * 8)
                   for i in range(n))[PAGE]
        if m[pool + off:m.index(b"\0", pool + off)] != desc.encode("latin1"):
            raise AssertionError("bouts de page : description %s" % lg)
        if objets._membre_archive(rom, INFOS % lg, "itemexpl_%s.nat" % lg) != m:
            raise AssertionError("bouts de page : description %s (iteminfo)" % lg)
        for chemin in FICHES:
            membre = chemin.rsplit("/", 1)[1].replace(".gp2", "_%s.nat" % lg)
            if nom_fiche(objets._membre_archive(rom, chemin, membre), PAGE) \
                    != sing.encode("latin1"):
                raise AssertionError("bouts de page : %s %s" % (membre, lg))
            m = objets._membre_archive(rom, chemin, membre)
            r, _d, _l = _fiche(m, PAGE)
            if any(m[r + k:r + k + 4] != m[f + k:f + k + 4]
                   for k, f in ((k, _fiche(m, src)[0]) for k, src in REGLAGES)):
                raise AssertionError("bouts de page : reglages %s" % membre)
    return adr


if __name__ == "__main__":
    import ndspy.rom
    if len(sys.argv) < 3:
        sys.exit("usage: patch_pages.py <rom.nds> <sortie.nds> [taux]")
    r = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    patcher(r, int(sys.argv[3]) if len(sys.argv) > 3 else TAUX)
    verifier(r, int(sys.argv[3]) if len(sys.argv) > 3 else TAUX)
    r.saveToFile(sys.argv[2])
    print("ecrit :", sys.argv[2])
