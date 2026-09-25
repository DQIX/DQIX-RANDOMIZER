#!/usr/bin/env python3
"""Vocations : les douze ouvertes des le debut, et une vocation tiree au hasard
quand on recrute un compagnon chez Tulipe.

CE QUE LE JEU FAIT (mesure le 25 septembre, research §89). Les six vocations
de base sont toujours proposees ; les six autres (gladiateur, paladin,
armagicien, ranger, sage, luminaire) sont des DRAPEAUX D'EVENEMENT, allumes par
le script de leur quete. Le tableau des drapeaux vit a 0x021088D0 (sauvegarde
+0x2DCC) ; le drapeau de la vocation `id` porte l'indice 0x113F + id, ce qui
tombe dans le mot 0x02108AF8 des mesures du 22 septembre (bits 6 a 11). Le jeu
les lit par une fonction generique, `test_drapeau(ctx, tableau, indice)` en
0x0206DFC0.

LEVIER 1 -- L'ABBAYE (overlay 3). Quand on engage la conversation avec le pere
Blaise, 0x02156054 batit la liste : les identifiants 1 a 6 sans condition,
puis, pour chaque identifiant de la table 0x0217F304, un appel a
`test_drapeau` (en 0x021560B0) qui decide de l'ajout. On remplace cet appel
par `mov r0, #1` : la liste recoit les douze. Les drapeaux, eux, ne bougent
pas -- les quetes 103 a 118 restent jouables et donnent leurs recompenses.
Guet memoire en jeu : c'est le SEUL lecteur des drapeaux 0x1146-0x114B quand
on parle au pere Blaise.

LEVIER 2 -- LE RECRUTEMENT (overlay 9, le Carre de Tulipe). Le menu ne propose
que les six vocations de base (vu en jeu, meme avec quatre vocations
debloquees). A la validation du compagnon (« Ajouter ce personnage ? » Oui),
l'overlay lit le choix dans son contexte, `ldrb r1, [sl, #0xda2]` en
0x021876C8, et le passe au regleur de vocation 0x02083CB0 ; la suite relit
0xda2 pour le niveau 1 de la vocation, le fichier `level%d.bin`, etc. On
detourne ce `ldrb` vers une greffe qui tire `rand_below(12) + 1` (le
generateur du jeu, 0x02032380), l'ECRIT en 0xda2, et revient. Toute la
creation voit donc la vocation tiree : stats, niveau, equipement.

Pourquoi le detour est sur : a 0x021876C8, r0-r3, ip et lr sont morts (un
`bl` vient d'avoir lieu en 0x021876C4), et la greffe revient par un `b`.

OU LOGE LA GREFFE. Les 28 derniers octets de l'overlay 9 sont le bourrage
d'alignement qui suit sa derniere chaine (`data/prm/level%d.bin`) ; la greffe
en prend 20. L'overlay 9 partage sa base (0x021842A0) avec les overlays 7-14 :
il ne vit que pendant le menu de Tulipe.

PISTE MORTE (22 septembre) : allumer le mot a l'entree du menu, en 0x021575DC.
L'injection RAM de l'epoque ne prouvait rien (cache d'instructions de
l'ARM9, garde-fous §4) et le bon levier est ailleurs.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TEST_DRAPEAU = 0x0206DFC0
RAND_BELOW = 0x02032380

# overlay 3 : l'abbaye
OVL_ABBAYE = 3
SITE_ABBAYE = 0x021560B0        # bl test_drapeau, dans la liste du pere Blaise

# overlay 9 : le Carre de Tulipe
OVL_TULIPE = 9
SITE_TULIPE = 0x021876C8        # ldrb r1, [sl, #0xda2]
ORIGINE_TULIPE = "ldrb r1, [sl, #0xda2]"
ZONE_TULIPE = 0x0218AD44        # bourrage de fin d'overlay
TAILLE_ZONE_TULIPE = 28

# LEVIER 3 -- LES VOCATIONS BLOQUEES (overlay 3). Le choix du menu du pere
# Blaise arrive en [sl+0x1e0] : 8 = changer de vocation, 9 = renouvocation
# (0x02156B9C). La branche 8 est remplacee par un refus : le message 0x43,
# ajoute a `str_dam`, puis l'etat 7 (fin de dialogue) -- exactement ce que fait
# le jeu pour refuser un personnage maudit (0x02156BE4). Le refus s'ecrit
# par-dessus le debut de la branche 8. LA RENOUVOCATION RESTE OUVERTE
# (decision du joueur, 25 septembre) : elle ne change pas de vocation, elle
# ramene un personnage de niveau 99 au niveau 1 dans la sienne.
BLOC_REFUS = 0x02156BB0             # debut de la branche 8
FIN_TOUR = 0x02156CFC
MSG_BLOQUE = 0x43
CHEMIN_DAMA = "data/bin/menu/str_dam.gp2"
TEXTE_BLOQUE = {
    "fr": b"//P<`e>re Blaise// Dans ce monde<,> les vocations sont scell<'e>es"
          b"<,> mon enfant. Nul ne peut en changer ici. Seul le rite de"
          b" renouvocation reste permis.<PAGE>//P<`e>re Blaise// Que le"
          b" Tout-Puissant te garde sur le chemin qui t<1>a <'e>t<'e> donn<'e>.",
    "en": b"//Jack of Alltrades// In this world<,> vocations are sealed<,> my"
          b" child. None may change their calling here. Only the rite of"
          b" revocation remains open to you.<PAGE>//Jack of Alltrades// May the"
          b" Almighty guide you along the path you were given.",
    "de": b"//Abt Luzius// In dieser Welt sind die Berufungen versiegelt<,>"
          b" mein Kind. Niemand kann hier seine Berufung wechseln. Nur ein"
          b" Neubeginn ist noch m<:o>glich.<PAGE>//Abt Luzius// M<:o>ge der"
          b" Allm<:a>chtige Euch auf dem Weg leiten<,> der Euch gegeben wurde.",
    "es": b"//Andos<'i>n de Vocationis// En este mundo las vocaciones est<'a>n"
          b" selladas<,> hijo m<'i>o. Nadie puede cambiar de vocaci<'o>n aqu<'i>."
          b" Solo el rito de la revocaci<'o>n sigue permitido.<PAGE>//Andos<'i>n"
          b" de Vocationis// Que el Todopoderoso te gu<'i>e por el camino que te"
          b" ha sido dado.",
    "it": b"//Episkopio// In questo mondo le vocazioni sono sigillate<,>"
          b" pecorella. Nessuno pu<`o> cambiare vocazione qui. Solo il rito"
          b" della rivocazione <`e> ancora concesso.<PAGE>//Episkopio// Che il"
          b" Misericordioso ti guidi sul cammino che ti <`e> stato dato.",
}

# LA « VOIX DE LA VOCATION ». Un second chemin du meme menu (drapeau 1 de
# [sl+0x1fc], pose a l'ouverture selon un parametre de l'evenement) saute le
# menu : « Papouz se laisse inspirer par l'esprit des vocations », puis la
# liste des personnages. Il ne passe pas par le choix 8. On le bloque apres le
# choix du personnage, dans les trois gestionnaires qui le traitent selon le
# chemin d'entree : le test « est-il maudit ? » (bl 0x02155F88) rend toujours
# oui, et le message du refus pour malediction (mov r2, #8, quatre
# instructions plus loin) devient 0x44, le meme refus dit par la Voix. En
# mode normal ces gestionnaires ne sont plus atteints (refus au menu). Vu en
# jeu en forcant le drapeau (guet.lua, DQ9_REG) : c'est 0x02156FB4 qui sert.
SITES_VOIX = (0x021569CC, 0x02156DD0, 0x02156FB4)
MSG_VOIX = 0x44
TEXTE_VOIX = {
    "fr": b"//Voix de la vocation// Dans ce monde<,> les vocations sont"
          b" scell<'e>es. Nul ne peut en changer.",
    "en": b"//Voice of Vocation// In this world<,> vocations are sealed. None"
          b" may change their calling.",
    "de": b"//Stimme der Berufung// In dieser Welt sind die Berufungen"
          b" versiegelt. Niemand kann seine Berufung wechseln.",
    "es": b"//Voz de la vocaci<'o>n// En este mundo las vocaciones est<'a>n"
          b" selladas. Nadie puede cambiar de vocaci<'o>n.",
    "it": b"//Voce della vocazione// In questo mondo le vocazioni sono"
          b" sigillate. Nessuno pu<`o> cambiare vocazione.",
}

# LEVIER 4 -- LA VOCATION DU HEROS (ZER-47). Le heros N'EST PAS gardien : a
# la creation de la partie, l'overlay 17 appelle 0x020897C4(personnage 0,
# niveau 1, vocation, ...) avec `mov r2, #6` en dur (0x0218BF14) -- il est
# troubadour des le debut, et « Gardien » n'est qu'un affichage du prologue
# (mesure le 25 septembre : l'objet du heros, 0x020F384C, vaut 6 a
# l'Observatoire comme devant l'Yggdrasil, et rien n'ecrit sa vocation
# pendant la chute). On remplace le 6 par une vocation tiree AVEC LA GRAINE :
# un seul immediat, aucune place de code. 0x020897C4 charge ensuite le
# `level%d.bin` de cette vocation, donc tout est coherent.
OVL_DEPART = 17
SITE_DEPART = 0x0218BF14            # mov r2, #6

# LEVIER 2 BIS -- « ALEATOIRE » DANS LE MENU DE TULIPE. Le menu des vocations
# du bar est la fenetre 8 de `bm_lui_wnd.bin` : un titre (element 37,
# chaine 0x11 « Vocation ») et six elements 38-43 (chaines 0x12-0x17). Le
# choix rendu vaut `element - 0x25` (overlay 3, 0x02163018) : l'element 38
# donne « Guerrier », que la greffe de l'overlay 9 remplace de toute facon.
# On ne garde que l'element 38, qui affiche une chaine neuve 0x21
# « Aleatoire » ; sa navigation vers le bas est coupee, et la fenetre ne
# dessine plus que le titre et cet element. Les chaines 0x12-0x1D ne sont pas
# touchees : la liste des amis du bar s'en sert pour afficher les vocations.
CHEMIN_BAR = "data/bin/menu/bm_lui.gp2"
TXT_ALEATOIRE = 0x21
TEXTE_ALEATOIRE = {"fr": b"Al<'e>atoire", "en": b"Random", "de": b"Zuf<:a>llig",
                   "es": b"Aleatoria", "it": b"Casuale"}
FENETRE_VOC, ELEMENT_PREMIER = 8, 38


def _desas(data, base, adr):
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
    o = adr - base
    ins = next(md.disasm(bytes(data[o:o + 4]), adr), None)
    return ("%s %s" % (ins.mnemonic, ins.op_str)) if ins else "?"


def _bl_vers(data, base, adr):
    w = struct.unpack_from("<I", data, adr - base)[0]
    if (w >> 24) != 0xEB:
        return None
    d = w & 0xFFFFFF
    if d & 0x800000:
        d -= 0x1000000
    return adr + 8 + 4 * d


def greffe_tulipe():
    from patch_hasard import assembler
    return assembler([
        "mov r0, #12",
        "bl #%d" % RAND_BELOW,          # r0 = [0, 12[
        "add r1, r0, #1",               # vocation 1 a 12
        "strb r1, [sl, #0xda2]",        # la suite de la creation relit 0xda2
        "b #%d" % (SITE_TULIPE + 4),
    ], ZONE_TULIPE)


def _lignes_bloque():
    return ["mov r1, #%d" % MSG_BLOQUE,
            "strh r1, [r5]",
            "mov r1, #7",
            "strb r1, [sl, #0x1f8]",
            "b #%d" % FIN_TOUR]


def _poser_textes(rom, chemin, fabrique):
    """Reecrit les membres d'une archive de textes : `fabrique(nom, octets)`
    rend le membre neuf, ou None pour le laisser tel quel."""
    import gp2
    import gp2_ecrire
    import objets as _objets
    fid = rom.filenames.idOf(chemin)
    donnees = bytes(rom.files[fid])
    arc = gp2.GP2(chemin, donnees=donnees)
    clairs = {}
    for nom in arc.noms:
        neuf = fabrique(nom, _objets._membre_archive(rom, chemin, nom))
        if neuf is not None:
            clairs[nom] = neuf
    rom.files[fid] = gp2_ecrire.reecrire(donnees, clairs)


def _langue(nom):
    """`bm_lui_fr.bin` -> `fr`, `str_dam_de.nat` -> `de`, sinon None."""
    lg = nom.rsplit(".", 1)[0].rsplit("_", 1)[-1]
    return lg if lg in TEXTE_ALEATOIRE else None


def _menu_aleatoire(nom, m):
    """Le membre `nom` de `bm_lui.gp2`, retouche pour le menu « Aleatoire »."""
    import textes_dq9
    lg = _langue(nom)
    if lg:
        return textes_dq9.ajouter_table(m, TXT_ALEATOIRE, TEXTE_ALEATOIRE[lg])
    m = bytearray(m)
    recs = textes_dq9._enregistrements(m)
    if nom == "bm_lui_txt.bin":
        # element 38 : l'enregistrement qui le suit porte sa chaine dans son
        # tag, le suivant sa navigation (haut, bas, gauche, droite)
        i = next(k for k, (p, tag, f) in enumerate(recs)
                 if tag == 0x65 and len(f) > 1 and f[1] == ELEMENT_PREMIER)
        p_txt, tag_txt, _f = recs[i + 1]
        p_nav, tag_nav, nav = recs[i + 2]
        if tag_txt != 0x12 or tag_nav != 0x66 or nav[1] != ELEMENT_PREMIER + 1:
            raise SystemExit("bm_lui_txt : element 38 inattendu")
        struct.pack_into("<H", m, p_txt, TXT_ALEATOIRE)
        struct.pack_into("<I", m, p_nav + 4 + 4, 0xFFFFFFFF)
        return bytes(m)
    if nom == "bm_lui_wnd.bin":
        p, _tag, f = next(r for r in recs
                          if r[1] == 0x65 and len(r[2]) == 9
                          and r[2][1] == FENETRE_VOC)
        if f[5] != 14 or f[8] != 7:
            raise SystemExit("bm_lui_wnd : fenetre 8 inattendue %r" % f)
        struct.pack_into("<I", m, p + 4 + 4 * 5, 4)      # hauteur
        struct.pack_into("<I", m, p + 4 + 4 * 8, 2)      # titre + 1 element
        return bytes(m)
    return None


def tirer_depart(graine):
    """La vocation de depart du heros, tiree avec la graine (1 a 12).

    UN GENERATEUR A PART, derive de la graine : tirer dans celui du
    randomizer decalerait tous les tirages qui suivent (sorts, arbres...) et
    changerait la ROM des autres options quand on coche celle-ci."""
    import random
    return random.Random("vocation-depart-%s" % graine).randint(1, 12)


def patcher(rom, ouvrir=True, embauche=True, bloquer=False, depart=None,
            bavard=True):
    """Pose les leviers demandes. `depart` : la vocation de depart du heros
    (1 a 12), ou None pour la laisser. Rend le nombre de sites modifies."""
    import ndspy.code
    import textes_dq9
    from patch_hasard import assembler
    ovl = rom.loadArm9Overlays()
    n = 0
    if depart is not None:
        if not 1 <= depart <= 12:
            raise ValueError("vocation de depart %r" % depart)
        o = ovl[OVL_DEPART]
        d = bytearray(o.data)
        lu = _desas(d, o.ramAddress, SITE_DEPART)
        if lu != "mov r2, #6":
            raise SystemExit("heros : a %#010x attendu mov r2, #6, lu %r"
                             % (SITE_DEPART, lu))
        d[SITE_DEPART - o.ramAddress:SITE_DEPART - o.ramAddress + 4] = \
            assembler(["mov r2, #%d" % depart], SITE_DEPART)
        o.data = bytes(d)
        rom.files[o.fileID] = o.save(compress=True)
        n += 1
        if bavard:
            print("  heros    : vocation de depart %d (au lieu de 6, "
                  "troubadour), visible apres le prologue" % depart)
    if bloquer:
        o = ovl[OVL_ABBAYE]
        d = bytearray(o.data)
        base = o.ramAddress
        lu = _desas(d, base, BLOC_REFUS)
        if lu != "ldrb r1, [sl, #0x1fb]":
            raise SystemExit("abbaye : a %#010x lu %r" % (BLOC_REFUS, lu))
        for site in SITES_VOIX:
            if (_bl_vers(d, base, site) != 0x02155F88
                    or _desas(d, base, site + 16) != "mov r2, #8"):
                raise SystemExit("abbaye : chemin de la Voix inattendu en "
                                 "%#010x" % site)
        bloc = assembler(_lignes_bloque(), BLOC_REFUS)
        d[BLOC_REFUS - base:BLOC_REFUS - base + len(bloc)] = bloc
        for site in SITES_VOIX:
            d[site - base:site - base + 4] = assembler(["mov r0, #1"], site)
            d[site + 16 - base:site + 20 - base] = \
                assembler(["mov r2, #%d" % MSG_VOIX], site + 16)
        o.data = bytes(d)
        rom.files[o.fileID] = o.save(compress=True)
        _poser_textes(rom, CHEMIN_DAMA, lambda nom, m: textes_dq9.ajouter_message(
            textes_dq9.ajouter_message(m, MSG_BLOQUE, TEXTE_BLOQUE[_langue(nom)]),
            MSG_VOIX, TEXTE_VOIX[_langue(nom)]))
        n += 1
        if bavard:
            print("  bloquees : changer de vocation refuse chez le pere "
                  "Blaise et par la Voix (messages %#x/%#x, 5 langues) ; "
                  "renouvocation permise" % (MSG_BLOQUE, MSG_VOIX))
    if ouvrir:
        o = ovl[OVL_ABBAYE]
        d = bytearray(o.data)
        if _bl_vers(d, o.ramAddress, SITE_ABBAYE) != TEST_DRAPEAU:
            raise SystemExit("abbaye : %#010x n'est pas l'appel attendu (%s)"
                             % (SITE_ABBAYE, _desas(d, o.ramAddress, SITE_ABBAYE)))
        d[SITE_ABBAYE - o.ramAddress:SITE_ABBAYE - o.ramAddress + 4] = \
            assembler(["mov r0, #1"], SITE_ABBAYE)
        o.data = bytes(d)
        rom.files[o.fileID] = o.save(compress=True)
        n += 1
        if bavard:
            print("  abbaye   : %#010x  bl test_drapeau -> mov r0, #1"
                  % SITE_ABBAYE)
    if embauche:
        o = ovl[OVL_TULIPE]
        d = bytearray(o.data)
        base = o.ramAddress
        lu = _desas(d, base, SITE_TULIPE)
        if lu != ORIGINE_TULIPE:
            raise SystemExit("Tulipe : a %#010x attendu %r, lu %r"
                             % (SITE_TULIPE, ORIGINE_TULIPE, lu))
        z = ZONE_TULIPE - base
        if z + TAILLE_ZONE_TULIPE != len(d) or any(d[z:]):
            raise SystemExit("Tulipe : la zone %#010x n'est pas le bourrage "
                             "vierge de fin d'overlay" % ZONE_TULIPE)
        g = greffe_tulipe()
        if len(g) > TAILLE_ZONE_TULIPE:
            raise SystemExit("greffe Tulipe : %d o pour %d"
                             % (len(g), TAILLE_ZONE_TULIPE))
        d[z:z + len(g)] = g
        d[SITE_TULIPE - base:SITE_TULIPE - base + 4] = \
            assembler(["b #%d" % ZONE_TULIPE], SITE_TULIPE)
        o.data = bytes(d)
        rom.files[o.fileID] = o.save(compress=True)
        _poser_textes(rom, CHEMIN_BAR, _menu_aleatoire)
        n += 1
        if bavard:
            print("  Tulipe   : %#010x -> greffe de %d o a %#010x "
                  "(vocation tiree 1-12), menu reduit a Aleatoire"
                  % (SITE_TULIPE, len(g), ZONE_TULIPE))
    if n:
        rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovl)
    return n


def verifier(rom, ouvrir=True, embauche=True, bloquer=False, depart=None):
    """Relit les overlays et les textes DEPUIS LA ROM : c'est la seule preuve
    que l'ecriture a pris (piege ndspy du 22 septembre)."""
    import objets as _objets
    import textes_dq9
    ovl = rom.loadArm9Overlays()
    if depart is not None:
        o = ovl[OVL_DEPART]
        lu = _desas(o.data, o.ramAddress, SITE_DEPART)
        if lu != "mov r2, #%d" % depart and lu != "mov r2, #%#x" % depart:
            raise AssertionError("heros : %#010x lit %r" % (SITE_DEPART, lu))
    if bloquer:
        from patch_hasard import assembler
        o = ovl[OVL_ABBAYE]
        bloc = assembler(_lignes_bloque(), BLOC_REFUS)
        z = BLOC_REFUS - o.ramAddress
        if bytes(o.data[z:z + len(bloc)]) != bloc:
            raise AssertionError("abbaye : refus absent")
        if _desas(o.data, o.ramAddress, 0x02156BA8) != "beq #0x2156c48":
            raise AssertionError("abbaye : la renouvocation doit rester ouverte")
        for site in SITES_VOIX:
            if (_desas(o.data, o.ramAddress, site) != "mov r0, #1"
                    or _desas(o.data, o.ramAddress, site + 16)
                    != "mov r2, #%#x" % MSG_VOIX):
                raise AssertionError("abbaye : chemin de la Voix non bloque "
                                     "en %#010x" % site)
        for lg, texte in TEXTE_BLOQUE.items():
            m = _objets._membre_archive(rom, CHEMIN_DAMA, "str_dam_%s.nat" % lg)
            msgs = textes_dq9.messages(m)
            if msgs.get(MSG_BLOQUE) != texte or msgs.get(MSG_VOIX) != TEXTE_VOIX[lg]:
                raise AssertionError("str_dam_%s : messages de refus absents" % lg)
    if ouvrir:
        o = ovl[OVL_ABBAYE]
        lu = _desas(o.data, o.ramAddress, SITE_ABBAYE)
        if lu != "mov r0, #1":
            raise AssertionError("abbaye : %#010x lit %r" % (SITE_ABBAYE, lu))
    if embauche:
        o = ovl[OVL_TULIPE]
        lu = _desas(o.data, o.ramAddress, SITE_TULIPE)
        if lu != "b #%#x" % ZONE_TULIPE:
            raise AssertionError("Tulipe : %#010x lit %r" % (SITE_TULIPE, lu))
        g = greffe_tulipe()
        z = ZONE_TULIPE - o.ramAddress
        if bytes(o.data[z:z + len(g)]) != g:
            raise AssertionError("Tulipe : la greffe n'est pas en place")
        for lg, texte in TEXTE_ALEATOIRE.items():
            m = _objets._membre_archive(rom, CHEMIN_BAR, "bm_lui_%s.bin" % lg)
            if textes_dq9.chaines_table(m).get(TXT_ALEATOIRE) != texte:
                raise AssertionError("bm_lui_%s : « Aleatoire » absent" % lg)
    return True


if __name__ == "__main__":
    import ndspy.rom
    if len(sys.argv) < 3:
        sys.exit("usage: patch_vocations.py <rom.nds> <sortie.nds> "
                 "[bloquer] [depart=N]")
    r = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    b = "bloquer" in sys.argv[3:]
    dep = next((int(a[7:]) for a in sys.argv[3:] if a.startswith("depart=")),
               None)
    patcher(r, bloquer=b, depart=dep)
    verifier(r, bloquer=b, depart=dep)
    r.saveToFile(sys.argv[2])
    print("ecrit :", sys.argv[2])
