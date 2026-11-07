"""La quete cachee (ZER-116), au royaume du Tout-Puissant (`X03`), apres la fin.

Dans le temple (carte 4304), Celestelle existe deja : PNJ 6, modele `s061`,
qui ne parle que pour la quete 198. On lui ajoute deux repliques, et un
gluant a cote d'elle (PNJ 7, le modele d'evenement `z000a` du gluant du Pic
Lata, genre 5). Avec les quatre bouts de page :

    Celestelle            -> condition 200 : son voeu le plus cher
    gluant, sans la pierre -> condition 201 : il decrit la pierre sans la nommer
    gluant, avec la pierre -> condition 200 : il la demande (OUI / NON)
    OUI (genre 1)          -> on RETIRE la pierre philosophale, on POSE le
                              drapeau FAIT
    drapeau FAIT pose      -> condition 202 pour tous deux : « ca a mal marche »

LE DRAPEAU. Champ de bits de scenario (`0x02108844+0x8C`, tests 0x00/0x01,
actions 0x64/0x65, research §111) : les declencheurs du jeu en citent
0x000-0x1DF ; dans la partie finie du joueur, 0x1E0 est pose (par un
evenement, donc) et 0x1E8-0x1FF sont nuls. On prend tout en haut du bloc :
risque restant, un evenement du jeu qui s'en servirait (le bytecode SB2 des
evenements n'est pas decode).
"""
import struct

import nitro_script as N
from patch_pages import PAGE, NB_PAGES

CARTE = 4304
CELESTELLE = 6
GLUANT = 7
MODELE_GLUANT = "z000a"
POS_GLUANT = (1.30, 1.10, -3.70)        # Celestelle est en (0.0, 1.1, -4.1)
ANGLE_GLUANT = 0.0
PIERRE = 22035                          # pierre philosophale
FAIT = 0x1FE                            # la pierre est donnee (avec combat : Zenus est vaincu)
ENGAGE = 0x1FD                          # avec combat : pierre donnee, Zenus pas encore vaincu
OP_EFFACER = 0x80                       # = patch_charme.OP_EFFACER (le neant)
DESIR, SANS_PIERRE, APRES, REPRISE = 200, 201, 202, 203
# Avec combat : Zenus sur le trone (PNJ 8, salle du trone, carte 4303,
# modele pose par work/zenus_combat/trone.py)
TRONE = 4303
ZENUS = 8
DEFI = 210
NPC = "data/scenario/X03.npc"
TRIGGER = "data/scenario/triggerX03.bin"
ARCHIVE = "data/scenario/X03Q0.gp2"     # l'apres-jeu

# Celestelle : (avec les quatre pages, apres la pierre)
CELESTE = {
    "fr": ("//C<'e>lestelle// Ces pages... Tu les as donc retrouv<'e>es.<PAGE>"
           "//C<'e>lestelle// Mon v<oe>u le plus cher<?> Revoir mon p<`e>re tel "
           "qu<1>il <'e>tait autrefois. Mais aucun pouvoir ne r<'e>veille un "
           "dieu endormi...<END>",
           "//C<'e>lestelle// Qu<1>as-tu fait<?> Sous nos pieds<,> quelque "
           "chose s<1>est r<'e>veill<'e>. Ce n<1>est pas mon p<`e>re... pas "
           "tout <`a> fait.<END>"),
    "en": ("//Celestria// These pages... So you found them.<PAGE>"
           "//Celestria// My dearest wish? To see my father as he once was. "
           "But no power can wake a sleeping god...<END>",
           "//Celestria// What have you done? Something has woken beneath "
           "our feet. It is not my father... not quite.<END>"),
    "de": ("//Celestria// Diese Seiten... Du hast sie also gefunden.<PAGE>"
           "//Celestria// Mein innigster Wunsch? Meinen Vater wiederzusehen<,> "
           "wie er einst war. Doch keine Macht weckt einen schlafenden "
           "Gott...<END>",
           "//Celestria// Was hast du getan? Unter unseren F<:u><ss>en ist "
           "etwas erwacht. Es ist nicht mein Vater... nicht ganz.<END>"),
    "es": ("//Dafne// Estas p<'a>ginas... As<'i> que las encontraste.<PAGE>"
           "//Dafne// <^?>Mi deseo m<'a>s querido? Volver a ver a mi padre "
           "como era antes. Pero ning<'u>n poder despierta a un dios "
           "dormido...<END>",
           "//Dafne// <^?>Qu<'e> has hecho? Algo ha despertado bajo nuestros "
           "pies. No es mi padre... no del todo.<END>"),
    "it": ("//Angelica// Queste pagine... Allora le hai trovate.<PAGE>"
           "//Angelica// Il mio desiderio pi<`u> caro? Rivedere mio padre "
           "com<1>era un tempo. Ma nessun potere risveglia un dio "
           "addormentato...<END>",
           "//Angelica// Che cosa hai fatto? Qualcosa si <`e> risvegliato "
           "sotto i nostri piedi. Non <`e> mio padre... non del tutto.<END>"),
}

# Le gluant : (par defaut, sans la pierre, avec la pierre, apres, reprise)
GLUANT_TEXTES = {
    "fr": ("*<:> Sclurp... Je veille sur la dame. Elle est si triste depuis "
           "si longtemps...<END>",
           "*<:> Mon papa dort en bas depuis toujours. Une pierre bleue qui "
           "gu<'e>rit tout le monde pourrait le r<'e>veiller<,> sclurp<!> Tu "
           "en as une<?><END>",
           "*<:> Oh<!> Cette pierre bleue<!> Avec elle<,> mon papa pourrait "
           "se r<'e>veiller<!> Tu me la donnes<?><YESNO><NO>*<:> Sclurp... "
           "tant pis.<END><YES><UKE><Cap><LEADER> donne la pierre "
           "philosophale au gluant.<PAGE>*<:> Merci<!> Papa<,> r<'e>veille-"
           "toi<!><PAGE>*<:> ...Oh non. Ce qui bouge en bas<,> ce n<1>est pas "
           "papa.<END>",
           "*<:> Ce qui s<1>est r<'e>veill<'e> en bas... ce n<1>est pas mon "
           "papa. Sclurp... J<1>ai peur.<END>",
           "*<:> Sclurp... Il est toujours l<`a>. On y retourne<?><YESNO><NO>"
           "*<:> Sclurp... Reviens vite.<END><YES>*<:> Sois prudent<,> "
           "sclurp<!><END>"),
    "en": ("*: Slurp... I keep watch over the lady. She has been so sad for "
           "so long...<END>",
           "*: My papa has been asleep downstairs forever. A blue stone that "
           "heals everyone could wake him up<,> slurp! Do you have one?<END>",
           "*: Oh! That blue stone! With it<,> my papa could wake up! Will you "
           "give it to me?<YESNO><NO>*: Slurp... never mind.<END><YES><UKE>"
           "<Cap><LEADER> gives the sage<1>s stone to the slime.<PAGE>*: Thank "
           "you! Papa<,> wake up!<PAGE>*: ...Oh no. Whatever is moving down "
           "there<,> it isn<1>t papa.<END>",
           "*: Whatever woke up down there... it isn<1>t my papa. Slurp... "
           "I<1>m scared.<END>",
           "*: Slurp... It<1>s still there. Shall we go back?<YESNO><NO>*: "
           "Slurp... come back soon.<END><YES>*: Be careful<,> slurp!<END>"),
    "de": ("*: Schlabber... Ich wache <:u>ber die Dame. Sie ist schon so "
           "lange so traurig...<END>",
           "*: Mein Papa schl<:a>ft unten schon ewig. Ein blauer Stein<,> der "
           "alle heilt<,> k<:o>nnte ihn wecken! Hast du einen?<END>",
           "*: Oh! Dieser blaue Stein! Damit k<:o>nnte mein Papa aufwachen! "
           "Gibst du ihn mir?<YESNO><NO>*: Schlabber... schade.<END><YES><UKE>"
           "<Cap><LEADER> gibt dem Schleim den Stein der Weisen.<PAGE>*: Danke! "
           "Papa<,> wach auf!<PAGE>*: ...Oh nein. Was sich da unten regt<,> "
           "ist nicht Papa.<END>",
           "*: Was da unten erwacht ist... das ist nicht mein Papa. "
           "Schlabber... ich habe Angst.<END>",
           "*: Schlabber... Es ist immer noch da. Gehen wir zur<:u>ck?<YESNO>"
           "<NO>*: Schlabber... komm bald wieder.<END><YES>*: Sei "
           "vorsichtig<,> schlabber!<END>"),
    "es": ("*: Glop... Cuido de la dama. Lleva tanto tiempo triste...<END>",
           "*: Mi pap<'a> duerme abajo desde siempre. <^!>Una piedra azul que "
           "lo cura todo podr<'i>a despertarlo! <^?>Tienes una?<END>",
           "*: <^!>Oh! <^!>Esa piedra azul! <^!>Con ella mi pap<'a> podr<'i>a "
           "despertar! <^?>Me la das?<YESNO><NO>*: Glop... qu<'e> pena.<END>"
           "<YES><UKE><Cap><LEADER> le da la piedra filosofal al limo.<PAGE>"
           "*: <^!>Gracias! <^!>Pap<'a><,> despierta!<PAGE>*: ...Oh<,> no. Lo "
           "que se mueve ah<'i> abajo no es pap<'a>.<END>",
           "*: Lo que ha despertado ah<'i> abajo... no es mi pap<'a>. Glop... "
           "tengo miedo.<END>",
           "*: Glop... Sigue ah<'i>. <^?>Volvemos?<YESNO><NO>*: Glop... "
           "vuelve pronto.<END><YES>*: <^!>Ten cuidado<,> glop!<END>"),
    "it": ("*: Slurp... Veglio sulla signora. <`E> triste da cos<`i> tanto "
           "tempo...<END>",
           "*: Il mio pap<`a> dorme di sotto da sempre. Una pietra blu che "
           "guarisce tutti potrebbe svegliarlo! Ne hai una?<END>",
           "*: Oh! Quella pietra blu! Con quella il mio pap<`a> potrebbe "
           "svegliarsi! Me la dai?<YESNO><NO>*: Slurp... pazienza.<END><YES>"
           "<UKE><Cap><LEADER> d<`a> la pietra filosofale allo slime.<PAGE>"
           "*: Grazie! Pap<`a><,> svegliati!<PAGE>*: ...Oh no. Quello che si "
           "muove l<`a> sotto non <`e> pap<`a>.<END>",
           "*: Quello che si <`e> svegliato l<`a> sotto... non <`e> il mio "
           "pap<`a>. Slurp... ho paura.<END>",
           "*: Slurp... <`E> ancora l<`a>. Ci torniamo?<YESNO><NO>*: Slurp... "
           "torna presto.<END><YES>*: Stai attento<,> slurp!<END>"),
}


# Avec combat, la QUESTION du don passe dans l'eglise de la maniere 8
# (patch_sauvegarde), comme le journal du jeu pose la sienne : la replique du
# gluant s'arrete avant (intro + <ADD><CHURCH=9>), l'eglise demande, OUI =
# le don puis la sauvegarde, NON = « tant pis » et l'eglise se ferme. Une
# replique <YESNO> qui ouvre l'eglise l'ouvrait aussi sur NON : tout restait
# bloque (joueur, 01/11 ; reproduit au banc). (intro, question sans « *: »)
DON = {
    "fr": ("*<:> Oh<!> Cette pierre bleue<!> Avec elle<,> mon papa pourrait "
           "se r<'e>veiller<!>", "Tu me la donnes<?>"),
    "en": ("*: Oh! That blue stone! With it<,> my papa could wake up!",
           "Will you give it to me?"),
    "de": ("*: Oh! Dieser blaue Stein! Damit k<:o>nnte mein Papa aufwachen!",
           "Gibst du ihn mir?"),
    "es": ("*: <^!>Oh! <^!>Esa piedra azul! <^!>Con ella mi pap<'a> podr<'i>a "
           "despertar!", "<^?>Me la das?"),
    "it": ("*: Oh! Quella pietra blu! Con quella il mio pap<`a> potrebbe "
           "svegliarsi!", "Me la dai?"),
}


def don_eglise(lg):
    """(question, oui, non) du don pour l'eglise de la maniere 8, tires de la
    replique du gluant sans combat (une seule source pour les textes)."""
    intro, question = DON[lg]
    avec = GLUANT_TEXTES[lg][2]
    tete, reste = avec.split("<YESNO><NO>")
    prefixe = intro.split(" ", 1)[0] + " "
    if tete != intro + " " + question:
        raise SystemExit("zenus_royaume.DON[%s] ne suit plus GLUANT_TEXTES" % lg)
    non, oui = reste.split("<END><YES>")
    assert oui.endswith("<END>")
    return prefixe + question + "<YESNO>", oui[:-len("<END>")], non


# Avec combat, le gluant ne lance plus rien : il garde la pierre, le jeu
# sauve (patch_sauvegarde, balise en fin de branche OUI), et Zenus attend
# sur le trone. Sa replique « reprise » devient une simple indication.
ATTEND = {
    "fr": "*<:> Sclurp... Ce qui s<1>est r<'e>veill<'e> t<1>attend en bas<,> "
          "sur le tr<^o>ne. Sois prudent<,> sclurp<!><END>",
    "en": "*: Slurp... Whatever woke up is waiting for you downstairs<,> on the "
          "throne. Be careful<,> slurp!<END>",
    "de": "*: Schlabber... Was da erwacht ist<,> wartet unten auf dem Thron auf "
          "dich. Sei vorsichtig<,> schlabber!<END>",
    "es": "*: Glop... Lo que ha despertado te espera abajo<,> en el trono. "
          "<^!>Ten cuidado<,> glop!<END>",
    "it": "*: Slurp... Quello che si <`e> svegliato ti aspetta di sotto<,> sul "
          "trono. Stai attento<,> slurp!<END>",
}

# Zenus, assis sur le trone : un echange, puis le combat (comme les boss des
# quetes du jeu : replique de condition 192 puis 0x78, triggerD03).
# Zenus EST le Tout-Puissant (joueur, 01/11) : il ne parle pas de lui comme
# d'un autre.
ZENUS_TEXTES = {
    "fr": "//Z<'e>nus// ...Enfin<,> je m<1><'e>veille.<PAGE>//Z<'e>nus// Je suis "
          "le Tout-Puissant. Ce tr<^o>ne est le mien<,> et ce monde<,> je l<1>ai "
          "cr<'e><'e> de mes mains.<PAGE>//Z<'e>nus// Approche<,> petit Gardien. "
          "Voyons ce que vaut la lumi<`e>re que je t<1>ai donn<'e>e<!><END>",
    "en": "//Zenus// ...At last<,> I awaken.<PAGE>//Zenus// I am the Almighty. "
          "This throne is mine<,> and this world was shaped by my own "
          "hands.<PAGE>//Zenus// Come<,> little Guardian. Let us see what the "
          "light I gave you is worth!<END>",
    "de": "//Zenus// ...Endlich erwache ich.<PAGE>//Zenus// Ich bin der "
          "Allm<:a>chtige. Dieser Thron ist mein<,> und diese Welt habe ich mit "
          "eigenen H<:a>nden geschaffen.<PAGE>//Zenus// Komm n<:a>her<,> kleiner "
          "W<:a>chter. Zeig mir<,> was das Licht wert ist<,> das ich dir gab!<END>",
    "es": "//Zenus// ...Por fin despierto.<PAGE>//Zenus// Soy el Todopoderoso. "
          "Este trono es m<'i>o<,> y este mundo lo cre<'e> con mis propias "
          "manos.<PAGE>//Zenus// Ac<'e>rcate<,> peque<~n>o guardi<'a>n. "
          "<^!>Veamos cu<'a>nto vale la luz que te di!<END>",
    "it": "//Zenus// ...Finalmente mi risveglio.<PAGE>//Zenus// Io sono "
          "l<1>Onnipotente. Questo trono <`e> mio<,> e questo mondo l<1>ho "
          "plasmato con le mie mani.<PAGE>//Zenus// Avvicinati<,> piccolo "
          "guardiano. Vediamo quanto vale la luce che ti ho donato!<END>",
}


def _f(x):
    return struct.unpack("<I", struct.pack("<f", x))[0]


def _lignes(cond, texte):
    return [(0x01, [(N.ENTIER, 1), (N.ENTIER, 99), (N.ENTIER, cond), (N.CHAINE, texte)]),
            (0x01, [(N.ENTIER, 1), (N.ENTIER, 99), (N.ENTIER, 1), (N.ENTIER, cond),
                    (N.CHAINE, texte)])]


def dialogue_gluant(lg, combat=None):
    defaut, sans, avec, apres, reprise = GLUANT_TEXTES[lg]
    if combat is not None:
        # l'intro seule, puis l'eglise de la maniere 8 (patch_sauvegarde) :
        # elle pose la question (don_eglise) ; sur OUI elle joue le don
        # (declencheur de genre 12) et sauve
        import patch_sauvegarde
        avec = DON[lg][0] + "<ADD>" + patch_sauvegarde.BALISE
        reprise = ATTEND[lg]
    out = []
    for cond, t in ((0, defaut), (16, defaut), (SANS_PIERRE, sans),
                    (DESIR, avec), (APRES, apres), (REPRISE, reprise)):
        out += _lignes(cond, t)
    return N.ecrire(out)


def dialogue_zenus(lg):
    # <N_TURN> (ARM9 0x0206A490, le jeu l'emploie pour Stella, S14Q0) : il ne se tourne pas vers qui lui parle.
    # Assis, il pivoterait autour de ses genoux et sortirait du trone (joueur, 05/11).
    out = []
    for cond in (0, 16, DEFI):
        out += _lignes(cond, "<N_TURN>" + ZENUS_TEXTES[lg])
    return N.ecrire(out)


def dialogue_celestelle(ancien, lg):
    _h, ins = N.lire(ancien)
    desir, apres = CELESTE[lg]
    return N.ecrire(ins + _lignes(DESIR, desir) + _lignes(APRES, apres))


def _noeud(op, *args):
    hw = [op] + list(args)
    if len(hw) % 2:
        hw.append(0)
    return [(N.ENTIER, (hw[i] << 16) | hw[i + 1]) for i in range(0, len(hw), 2)]


def declencheurs(combat=None):
    """`combat` : numero d'eventbattle lance (action 0x78, research §112)
    juste apres le don de la pierre ; None = pas de combat."""
    def t(genre, *noeuds, carte=CARTE):
        p = [(N.ENTIER, v) for v in (carte, 0, 0, 99, 99, genre)]
        for n in noeuds:
            p += n
        return (0x01, p)
    quatre = _noeud(0x30, PAGE, 0, NB_PAGES)    # objet, 0, nombre
    celestelle = [
        t(0, _noeud(0x06, CELESTELLE), _noeud(0x00, FAIT), _noeud(0x76, CELESTELLE, APRES)),
        t(0, _noeud(0x06, CELESTELLE), quatre, _noeud(0x76, CELESTELLE, DESIR)),
    ]
    if combat is None:
        return celestelle + [
            t(0, _noeud(0x06, GLUANT), _noeud(0x00, FAIT), _noeud(0x76, GLUANT, APRES)),
            t(0, _noeud(0x06, GLUANT), quatre, _noeud(0x12, PIERRE), _noeud(0x76, GLUANT, DESIR)),
            t(0, _noeud(0x06, GLUANT), quatre, _noeud(0x76, GLUANT, SANS_PIERRE)),
            # apres la ligne 200 et OUI : la pierre et les pages contre le drapeau
            # (0x75 : objet, nombre, 0 -- l'ordre des quetes du jeu)
            t(1, _noeud(0x06, GLUANT), _noeud(0x0B, DESIR), _noeud(0x10, 0),
              _noeud(0x01, FAIT), _noeud(0x73, PIERRE), _noeud(0x75, PAGE, NB_PAGES),
              _noeud(0x64, FAIT)),
        ]
    # AVEC COMBAT (31/10). OUI : la replique ouvre l'eglise sans question
    # (patch_sauvegarde) ; le don se fait en GENRE 12, que l'eglise joue
    # juste avant d'ecrire la sauvegarde (le genre 1 ne tourne pas apres une
    # replique qui ouvre une eglise ; en genre 12 les tests de PNJ, de
    # replique et de reponse echouent : mesure 31/10). Le don est donc DANS
    # la sauvegarde. Zenus attend sur le trone (carte 4303) : il n'existe
    # qu'entre ENGAGE et FAIT (op 0x11 de place.bin, work/zenus_combat/
    # trone.py ; 0x95/0x96 ne visent PAS les PNJ mais des objets de carte),
    # il parle puis lance le combat (genre 1, `0B[192] ; 78[n]` chez le jeu).
    # FAIT n'est pose qu'a la VICTOIRE (genre 15, test 0x0C = son numero,
    # research §112). Perdu ou fui : ENGAGE sans FAIT, Zenus est toujours la.
    return celestelle + [
        t(0, _noeud(0x06, GLUANT), _noeud(0x00, FAIT), _noeud(0x76, GLUANT, APRES)),
        t(0, _noeud(0x06, GLUANT), _noeud(0x00, ENGAGE), _noeud(0x76, GLUANT, REPRISE)),
        t(0, _noeud(0x06, GLUANT), quatre, _noeud(0x12, PIERRE), _noeud(0x76, GLUANT, DESIR)),
        t(0, _noeud(0x06, GLUANT), quatre, _noeud(0x76, GLUANT, SANS_PIERRE)),
        t(12, _noeud(0x01, ENGAGE), quatre, _noeud(0x12, PIERRE),
          _noeud(0x73, PIERRE), _noeud(0x75, PAGE, NB_PAGES), _noeud(0x64, ENGAGE)),
        t(0, _noeud(0x06, ZENUS), _noeud(0x76, ZENUS, DEFI), carte=TRONE),
        t(1, _noeud(0x06, ZENUS), _noeud(0x0B, DEFI), _noeud(0x78, combat),
          carte=TRONE),
        # A2(0) : Stella s'en va (drapeau 0x113B, research §112), comme a
        # la fin du jeu ; la quete 039 (interne 201) la ramene par A2(1).
        # 0x80 (patch_charme.OP_EFFACER) : le compagnon reduit au neant
        # pendant le combat quitte l'equipe, son equipement va au sac.
        t(15, _noeud(0x0C, combat), _noeud(0x01, FAIT), _noeud(0x64, FAIT),
          _noeud(0xA2, 0), _noeud(OP_EFFACER), carte=TRONE),
        # apres une DEFAITE (reveil a l'eglise) : l'effacement se fait en
        # revenant dans la salle du trone, avant toute revanche (genre 20 =
        # chargement de la carte ; sans victime marquee, 0x80 ne fait rien)
        t(20, _noeud(OP_EFFACER), carte=TRONE),
    ]


def patcher(rom, combat=None):
    import gp2_ecrire
    import objets
    import treasure
    d = bytes(rom.getFileByName(NPC))
    m = treasure.membres_narc(d)
    a, b = m["X03npc.bin"]
    _h, liste = N.lire(d[a:b])
    if any(ps[0][1] == GLUANT for op, ps in liste if op == 0x03):
        raise SystemExit("X03npc : le PNJ %d existe deja" % GLUANT)
    liste.append((0x03, [(N.ENTIER, GLUANT), (N.ENTIER, 5), (N.CHAINE, 0xFFFFFFFF),
                         (N.CHAINE, MODELE_GLUANT), (N.ENTIER, 2)]))
    a, b = m["X03place.bin"]
    _h, place = N.lire(d[a:b])
    x, y, z = POS_GLUANT
    place.append((0x03, [(N.ENTIER, CARTE), (N.ENTIER, GLUANT), (N.FLOTTANT, _f(x)),
                         (N.FLOTTANT, _f(y)), (N.FLOTTANT, _f(z)),
                         (N.FLOTTANT, _f(ANGLE_GLUANT))]))
    place.append((0x08, [(N.ENTIER, GLUANT), (N.FLOTTANT, _f(ANGLE_GLUANT)),
                         (N.FLOTTANT, _f(1.0))]))
    rom.setFileByName(NPC, treasure.reconstruire_narc(
        d, {"X03npc.bin": N.ecrire(liste), "X03place.bin": N.ecrire(place)}))
    d = bytes(rom.getFileByName(ARCHIVE))
    nouveaux = {"%03d_%s.bin" % (GLUANT, lg): dialogue_gluant(lg, combat) for lg in CELESTE}
    if combat is not None:
        nouveaux.update({"%03d_%s.bin" % (ZENUS, lg): dialogue_zenus(lg) for lg in CELESTE})
    remplaces = {"%03d_%s.bin" % (CELESTELLE, lg): dialogue_celestelle(
        objets._membre_archive(rom, ARCHIVE, "%03d_%s.bin" % (CELESTELLE, lg)), lg)
        for lg in CELESTE}
    rom.setFileByName(ARCHIVE, gp2_ecrire.ajouter(d, nouveaux, remplaces))
    d = bytes(rom.getFileByName(TRIGGER))
    _h, ins = N.lire(d)
    rom.setFileByName(TRIGGER, N.ecrire(ins + declencheurs(combat)))


def brancher(rom, combat):
    """Une ROM qui porte la quete SANS combat (patcher(rom), ce que fait
    randomizer.py) passe a la quete AVEC combat : declencheurs remplaces,
    repliques du gluant refaites, repliques de Zenus ajoutees."""
    import gp2_ecrire
    _h, ins = N.lire(bytes(rom.getFileByName(TRIGGER)))
    anciens = declencheurs()
    if ins[-len(anciens):] != anciens:
        raise SystemExit("la quete sans combat n'est pas en fin de trigger" + "X03")
    rom.setFileByName(TRIGGER, N.ecrire(ins[:-len(anciens)] + declencheurs(combat)))
    d = bytes(rom.getFileByName(ARCHIVE))
    rom.setFileByName(ARCHIVE, gp2_ecrire.ajouter(
        d, {"%03d_%s.bin" % (ZENUS, lg): dialogue_zenus(lg) for lg in CELESTE},
        {"%03d_%s.bin" % (GLUANT, lg): dialogue_gluant(lg, combat) for lg in CELESTE}))
    verifier(rom, combat)


def verifier(rom, combat=None):
    """`combat` : celui passe a `patcher` (None = la quete sans combat)."""
    import objets
    for lg in CELESTE:
        if objets._membre_archive(rom, ARCHIVE, "%03d_%s.bin" % (GLUANT, lg)) \
                != dialogue_gluant(lg, combat):
            raise AssertionError("gluant : repliques %s" % lg)
        if combat is not None and objets._membre_archive(
                rom, ARCHIVE, "%03d_%s.bin" % (ZENUS, lg)) != dialogue_zenus(lg):
            raise AssertionError("Zenus : repliques %s" % lg)
        _h, ins = N.lire(objets._membre_archive(
            rom, ARCHIVE, "%03d_%s.bin" % (CELESTELLE, lg)))
        if [v for t, v in ins[-1][1] if t == N.CHAINE] != [CELESTE[lg][1].encode("latin1")]:
            raise AssertionError("Celestelle : repliques %s" % lg)
    # nos declencheurs, tels qu'ecrits, en fin de fichier (et une seule fois)
    _h, ins = N.lire(bytes(rom.getFileByName(TRIGGER)))
    attendus = declencheurs(combat)
    if ins[-len(attendus):] != attendus:
        raise AssertionError("royaume : les %d declencheurs de la quete" % len(attendus))
    if sum(1 for x in ins if x == attendus[0]) != 1:
        raise AssertionError("royaume : declencheurs poses deux fois")
    return True
