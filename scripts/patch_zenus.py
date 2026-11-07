#!/usr/bin/env python3
"""La quete cachee de la 1.8 (ZER-116) : ce qui s'ajoute aux villes.

LE PNJ D'INDICES. Un fantome au chateau d'Ablithia (`C01`), dans la salle
du trone (carte 118), a droite de l'estrade du roi. Il parle des bouts de
page (patch_pages) et, quand on en a quatre, dit ou aller apres la fin du
jeu. Quatre repliques, choisies par des declencheurs (research §111) :

    PNJ 224 et la pierre donnee (0x1FE)      -> condition 202 : le reveil
    PNJ 224 et au moins 4 pages (test 0x30)  -> condition 200 : la revelation
    PNJ 224 et au moins 1 page  (test 0x12)  -> condition 201 : encouragement
    sinon                                    -> la ligne par defaut
    apres sa replique, sans page ni pierre donnee : il donne la premiere
    page (0x72) -- les combats n'en donnent qu'a partir d'une (patch_pages)

CE QUI EST ECRIT, tout en scripts Nitro (nitro_script, aller-retour exact
sur 1 178 fichiers du jeu) :

- `C01.npc` (NARC) : une ligne 0x03 dans `C01npc.bin` (id, genre 0, modele
  du fantome `n005g`, deja employe a Ablithia), une ligne 0x03 (carte, id,
  x, y, z, angle) et une 0x0B dans `C01place.bin`, sans la 0x05 qui
  retire les fantomes du jeu le jour ;
- un membre `224_<lg>.bin` dans chacune des archives d'etape `C01?0.gp2`
  (gp2_ecrire.ajouter : l'archive est refaite) ;
- trois declencheurs de genre 0 et un de genre 1 dans `triggerC01.bin`.

La ligne par defaut est ecrite pour les conditions 0 (les fantomes du jeu)
ET 16 (les autres PNJ), de jour et de nuit : on n'a pas lu le code qui
choisit la ligne, et une ligne qui ne sert pas ne coute rien.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import nitro_script as N
from patch_pages import PAGE, NB_PAGES

PNJ = 224                       # premier id libre a Ablithia
# La salle du trone, pas l'exterieur : le jeu ne charge que 10 modeles de
# PNJ par carte (mesure en jeu, essai 6 et variante n005a). Ablithia
# dehors en charge deja 10 ; le jour, sans les fantomes du jeu, notre
# `n005g` faisait le 11e et le PNJ 1 n'avait plus de modele (invisible,
# mais parlable). La salle du trone en charge 4 ou 5 apres le jeu, et le
# chateau est ferme la nuit (choix du joueur, 30/10).
CARTE = 118                     # chateau d'Ablithia, salle du trone
MODELE = "n005g"                # un fantome (PNJ 26, « ※幽霊 »)
# sur le sol a droite de l'estrade : le roi (PNJ 133) est en (2.1, 0.58,
# -14.5), la reine (131) en (0.9, 0.65, -15.3) ; hauteur des soldats (0.15),
# tourne vers le centre (4.71 : vers -x ; le soldat 40 en x = -2.28 a 1.69)
POSITION = (3.60, 0.15, -11.50)
ANGLE = 4.71
COND_QUATRE, COND_PAGES, COND_APRES = 200, 201, 202
NPC = "data/scenario/C01.npc"
TRIGGER = "data/scenario/triggerC01.bin"

# (par defaut -- il donne la premiere page --, avec des pages, avec les
# quatre, apres le don de la pierre au gluant)
TEXTES = {
    "fr": (
        "*<:> Vous me voyez<?> Alors <'e>coutez-moi.<PAGE>"
        "*<:> De mon vivant<,> j<1>avais un livre tr<`e>s pr<'e>cieux. Ses "
        "pages se sont envol<'e>es<,> et les monstres les gardent sans le "
        "savoir.<PAGE>*<:> Il ne m<1>en reste qu<1>une. Prenez-la<,> et "
        "trouvez les trois autres en combattant. Rapportez-les-moi.<PAGE>"
        "<UKE><Cap><LEADER> re<,c>oit un bout de page.<END>",
        "*<:> Une page de mon livre<!> Mais il en manque encore. Quatre<,> "
        "il m<1>en faut quatre...<END>",
        "*<:> Les quatre pages<!> Laissez-moi les lire...<PAGE>"
        "*<:> <66>Le v<oe>u le plus cher de C<'e>lestelle peut <^e>tre "
        "exauc<'e>.<99><PAGE>*<:> <66>Le monde une fois sauv<'e><,> qu<1>on "
        "aille la trouver au plus profond du royaume du Tout-Puissant.<99>"
        "<PAGE>*<:> ... C<1>est tout ce qu<1>il dit. Gardez ces pages<,> "
        "elles sont <`a> vous.<END>",
        "*<:> Quelque chose s<1>est r<'e>veill<'e> au fond du royaume du "
        "Tout-Puissant... Je le sens d<1>ici. Soyez prudent.<END>"),
    "en": (
        "*: You can see me? Then listen.<PAGE>*: When I was alive<,> I had "
        "a precious book. Its pages blew away<,> and now monsters carry them "
        "without knowing it.<PAGE>*: Only one is left to me. Take it<,> and "
        "find the other three in battle. Bring them to me.<PAGE>"
        "<UKE><Cap><LEADER> receives a torn page.<END>",
        "*: A page from my book! But some are still missing. Four<,> I need "
        "all four...<END>",
        "*: All four pages! Let me read them...<PAGE>*: <6>Celestria<1>s "
        "dearest wish can be granted.<9><PAGE>*: <6>Once the world is "
        "saved<,> seek her in the deepest hall of the Realm of the "
        "Almighty.<9><PAGE>*: ...That is all it says. Keep the pages. They "
        "are yours.<END>",
        "*: Something has awoken in the depths of the Realm of the "
        "Almighty... I can feel it from here. Be careful.<END>"),
    "de": (
        "*: Du kannst mich sehen? Dann h<:o>r mir zu.<PAGE>*: Zu Lebzeiten "
        "hatte ich ein kostbares Buch. Seine Seiten sind fortgeweht<,> "
        "und nun tragen Monster sie bei sich<,> ohne es zu wissen.<PAGE>"
        "*: Mir ist nur eine geblieben. Nimm sie und finde die anderen drei "
        "im Kampf. Bring sie mir.<PAGE><UKE><Cap><LEADER> erh<:a>lt eine "
        "Buchseite.<END>",
        "*: Eine Seite aus meinem Buch! Aber es fehlen noch welche. Vier<,> "
        "ich brauche alle vier...<END>",
        "*: Alle vier Seiten! Lass sie mich lesen...<PAGE>*: Der "
        "innigste Wunsch Celestrias kann erf<:u>llt werden.<PAGE>*: Ist die "
        "Welt erst gerettet<,> so suche sie im tiefsten Saal des Reichs des "
        "Allm<:a>chtigen.<PAGE>*: ...Mehr steht da nicht. Behalte die "
        "Seiten. Sie geh<:o>ren dir.<END>",
        "*: In den Tiefen des Reichs des Allm<:a>chtigen ist etwas "
        "erwacht... Ich sp<:u>re es bis hierher. Sei vorsichtig.<END>"),
    "es": (
        "*: <^?>Puedes verme? Entonces esc<'u>chame.<PAGE>*: En vida tuve "
        "un libro muy valioso. Sus p<'a>ginas se las llev<'o> el viento<,> y "
        "ahora los monstruos las guardan sin saberlo.<PAGE>*: Solo me queda "
        "una. T<'o>mala<,> y encuentra las otras tres luchando. "
        "Tr<'a>emelas.<PAGE><UKE><Cap><LEADER> recibe una p<'a>gina "
        "arrancada.<END>",
        "*: <^!>Una p<'a>gina de mi libro! Pero a<'u>n faltan. Cuatro<,> "
        "necesito las cuatro...<END>",
        "*: <^!>Las cuatro p<'a>ginas! D<'e>jame leerlas...<PAGE>*: <66>El "
        "deseo m<'a>s querido de Dafne puede cumplirse.<99><PAGE>*: <66>Una "
        "vez salvado el mundo<,> b<'u>scala en la sala m<'a>s profunda del "
        "Reino del Todopoderoso.<99><PAGE>*: ...Eso es todo lo que dice. "
        "Qu<'e>date las p<'a>ginas. Son tuyas.<END>",
        "*: Algo ha despertado en lo m<'a>s hondo del Reino del "
        "Todopoderoso... Lo siento desde aqu<'i>. Ten cuidado.<END>"),
    "it": (
        "*: Riesci a vedermi? Allora ascoltami.<PAGE>*: Da vivo avevo un "
        "libro preziosissimo. Le sue pagine sono volate via<,> e ora i mostri "
        "le custodiscono senza saperlo.<PAGE>*: Me ne resta solo una. "
        "Prendila<,> e trova le altre tre combattendo. Portamele.<PAGE>"
        "<UKE><Cap><LEADER> riceve una pagina strappata.<END>",
        "*: Una pagina del mio libro! Ma ne mancano ancora. Quattro<,> me ne "
        "servono quattro...<END>",
        "*: Tutte e quattro le pagine! Lasciami leggere...<PAGE>*: <66>Il "
        "desiderio pi<`u> caro di Angelica pu<`o> essere esaudito.<99><PAGE>"
        "*: <66>Quando il mondo sar<`a> salvo<,> cercala nella sala pi<`u> "
        "profonda del Regno del Misericordioso.<99><PAGE>*: ...Dice solo "
        "questo. Tieni le pagine. Sono tue.<END>",
        "*: Qualcosa si <`e> svegliato nelle profondit<`a> del Regno del "
        "Misericordioso... Lo sento fin qui. Stai attento.<END>"),
}


def _f(x):
    return struct.unpack("<I", struct.pack("<f", x))[0]


def _ligne(cond, texte, nuit=False):
    ps = [(N.ENTIER, 1), (N.ENTIER, 99)]
    if nuit:
        ps.append((N.ENTIER, 1))
    return (0x01, ps + [(N.ENTIER, cond), (N.CHAINE, texte)])


def dialogue(lg):
    defaut, pages, quatre, apres = TEXTES[lg]
    lignes = []
    for cond, texte in ((0, defaut), (16, defaut), (COND_PAGES, pages),
                        (COND_QUATRE, quatre), (COND_APRES, apres)):
        lignes += [_ligne(cond, texte), _ligne(cond, texte, nuit=True)]
    return N.ecrire(lignes)


def _noeud(op, *args):
    """Un noeud de declencheur en parametres u32, poids fort d'abord
    (declencheurs.py) : (op, a1), (a2, a3), ..."""
    hw = [op] + list(args)
    if len(hw) % 2:
        hw.append(0)
    return [(N.ENTIER, (hw[i] << 16) | hw[i + 1]) for i in range(0, len(hw), 2)]


def declencheurs():
    from zenus_royaume import FAIT
    entete = [(N.ENTIER, v) for v in (CARTE, 0, 0, 99, 99, 0)]
    apres = [(N.ENTIER, v) for v in (CARTE, 0, 0, 99, 99, 1)]
    return [
        # genre 0, le premier qui convient gagne
        (0x01, entete + _noeud(0x06, PNJ) + _noeud(0x00, FAIT)
         + _noeud(0x76, PNJ, COND_APRES)),
        (0x01, entete + _noeud(0x06, PNJ) + _noeud(0x30, PAGE, 0, NB_PAGES)
         + _noeud(0x76, PNJ, COND_QUATRE)),
        (0x01, entete + _noeud(0x06, PNJ) + _noeud(0x12, PAGE)
         + _noeud(0x76, PNJ, COND_PAGES)),
        # genre 1, apres sa replique : sans page et avant le gluant, il
        # donne la premiere (patch_pages : rien ne tombe sans page)
        (0x01, apres + _noeud(0x06, PNJ) + _noeud(0x13, PAGE)
         + _noeud(0x01, FAIT) + _noeud(0x72, PAGE)),
    ]


def _archives_etapes(rom):
    def walk(f, p=""):
        for n in f.files:
            yield p + n
        for n, s in f.folders:
            yield from walk(s, p + n + "/")
    return sorted(n for n in walk(rom.filenames)
                  if n.startswith("data/scenario/C01") and n.endswith("0.gp2")
                  and len(n) == len("data/scenario/C01B0.gp2"))


def patcher_pnj(rom):
    import gp2
    import gp2_ecrire
    import treasure
    # la liste des PNJ et leur placement
    d = bytes(rom.getFileByName(NPC))
    m = treasure.membres_narc(d)
    a, b = m["C01npc.bin"]
    _h, liste = N.lire(d[a:b])
    if any(op == 0x03 and ps[0][1] == PNJ for op, ps in liste):
        raise SystemExit("C01npc : le PNJ %d existe deja" % PNJ)
    liste.append((0x03, [(N.ENTIER, PNJ), (N.ENTIER, 0), (N.CHAINE, 0xFFFFFFFF),
                         (N.CHAINE, MODELE), (N.ENTIER, 0)]))
    a, b = m["C01place.bin"]
    _h, place = N.lire(d[a:b])
    x, y, z = POSITION
    place.append((0x03, [(N.ENTIER, CARTE), (N.ENTIER, PNJ), (N.FLOTTANT, _f(x)),
                         (N.FLOTTANT, _f(y)), (N.FLOTTANT, _f(z)),
                         (N.FLOTTANT, _f(ANGLE))]))
    # Lu dans le code (research §111.8) : 0x03 cree le PNJ sur sa carte sans
    # condition ; une 0x05 SANS coordonnees le RETIRE quand sa fenetre
    # d'histoire et son moment k s'appliquent (k = 0 : [jeu+0x3DC] != 0, le
    # jour ; 1 : la nuit ; 2 : toujours). Les fantomes du jeu (26, 27) ont
    # une 0x05 k = 0 : absents le jour. Le notre, visible tout le temps
    # (joueur), n'en a pas. La 0x0B (id, 64) ajoute le drapeau 0x40 a la
    # fiche, comme chez eux. La 0x08 recopiee du PNJ 1 (essai 1) lui donnait
    # les memes mouvements que lui.
    place.append((0x0B, [(N.ENTIER, PNJ), (N.ENTIER, 64)]))
    rom.setFileByName(NPC, treasure.reconstruire_narc(
        d, {"C01npc.bin": N.ecrire(liste), "C01place.bin": N.ecrire(place)}))
    # ses repliques, dans chaque archive d'etape
    archives = _archives_etapes(rom)
    for chemin in archives:
        d = bytes(rom.getFileByName(chemin))
        langues = sorted({n.rsplit("_", 1)[1][:2]
                          for n in gp2.GP2(chemin, donnees=d).noms})
        rom.setFileByName(chemin, gp2_ecrire.ajouter(
            d, {"%03d_%s.bin" % (PNJ, lg): dialogue(lg) for lg in langues}))
    # ses declencheurs
    d = bytes(rom.getFileByName(TRIGGER))
    _h, ins = N.lire(d)
    rom.setFileByName(TRIGGER, N.ecrire(ins + declencheurs()))
    return len(archives)


def patcher(rom, bavard=True):
    import zenus_royaume
    n = patcher_pnj(rom)
    zenus_royaume.patcher(rom)
    if bavard:
        print("  PNJ %d a Ablithia, %d archives d'etape ; Celestelle et le "
              "gluant au royaume" % (PNJ, n))


def verifier(rom):
    """Relit la ROM : le PNJ, son placement, ses repliques, ses declencheurs."""
    import declencheurs as D
    import objets
    import treasure
    d = bytes(rom.getFileByName(NPC))
    m = treasure.membres_narc(d)
    a, b = m["C01npc.bin"]
    if not any(op == 0x03 and ps[0][1] == PNJ and ps[3][1] == MODELE.encode()
               for op, ps in N.lire(d[a:b])[1]):
        raise AssertionError("PNJ %d absent de C01npc" % PNJ)
    a, b = m["C01place.bin"]
    place = N.lire(d[a:b])[1]
    if not any(op == 0x03 and ps[0][1] == CARTE and ps[1][1] == PNJ
               for op, ps in place):
        raise AssertionError("PNJ %d sans placement" % PNJ)
    if any(op == 0x05 and len(ps) > 8 and ps[8][1] == PNJ for op, ps in place):
        raise AssertionError("PNJ %d : une 0x05 le retirerait" % PNJ)
    if any(op == 0x08 and ps[0][1] == PNJ for op, ps in place):
        raise AssertionError("PNJ %d : 0x08 inattendue" % PNJ)
    for chemin in _archives_etapes(rom):
        for lg in TEXTES:
            if objets._membre_archive(rom, chemin, "%03d_%s.bin" % (PNJ, lg)) \
                    != dialogue(lg):
                raise AssertionError("%s : repliques %s" % (chemin, lg))
    t = [x for x in D.lire(rom, "C01") if x["carte"] == CARTE
         and (0x06, [PNJ]) in x["noeuds"]]
    from zenus_royaume import FAIT
    attendu = [[(0x06, [PNJ]), (0x00, [FAIT]), (0x76, [PNJ, COND_APRES])],
               [(0x06, [PNJ]), (0x30, [PAGE, 0, NB_PAGES]), (0x76, [PNJ, COND_QUATRE])],
               [(0x06, [PNJ]), (0x12, [PAGE]), (0x76, [PNJ, COND_PAGES])],
               [(0x06, [PNJ]), (0x13, [PAGE]), (0x01, [FAIT]), (0x72, [PAGE])]]
    # le decodeur garde le demi-mot de bourrage des noeuds impairs
    lus = [[(op, args[:len(a)]) for (op, args), (_o, a) in zip(x["noeuds"], att)]
           for x, att in zip(t, attendu)]
    if len(t) != 4 or lus != attendu or [x["genre"] for x in t] != [0, 0, 0, 1]:
        raise AssertionError("declencheurs du PNJ %d : %r" % (PNJ, t))
    import zenus_royaume
    zenus_royaume.verifier(rom)
    return True


if __name__ == "__main__":
    import ndspy.rom
    if len(sys.argv) < 3:
        sys.exit("usage: patch_zenus.py <rom.nds> <sortie.nds>")
    r = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    patcher(r)
    verifier(r)
    r.saveToFile(sys.argv[2])
    print("ecrit :", sys.argv[2])
