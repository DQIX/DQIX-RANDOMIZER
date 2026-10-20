"""Les trois familles de boss des combats scriptes (ZER-70, ZER-71).

Les 89 boss de `--boss` (especes des combats scriptes qui ne rodent jamais,
hors bestiaire) se rangent en trois familles, que `eventbattle.bin` separe
lui-meme par le numero d'evenement (champ 0) :

    histoire  evenements 2-33 et 131-138   32 especes  le scenario, les quetes
                                                        d'apres-jeu (Yore,
                                                        Nodoph, Rover, les
                                                        seconds combats des
                                                        trois gardiens...)
    grottes   evenements 34-45             12 especes  les boss de grotto
                                                        (Equinocte, Atlas...)
    legendes  evenements 46-84             45 especes  les boss des anciens
                                                        Dragon Quest, en trois
                                                        niveaux chacun, et les
                                                        deux pinces de Mortamor

POURQUOI LES LEGENDES DOMINENT. Chaque boss legendaire existe en TROIS
especes (niveaux 1, 2, 3 : Dragonlord 500, 600, 601) et Mortamor en porte
neuf avec ses pinces. Une permutation uniforme des 89 especes donne donc a
un combat d'histoire un boss legendaire une fois sur deux, un boss d'histoire
une fois sur trois seulement (mesure sur 40 graines, voir ZER-70).

Les listes sont ecrites en dur et `verifier()` les recompare a la ROM.
"""

HISTOIRE = frozenset(list(range(300, 321)) + list(range(339, 348))
                     + [800, 801])
GROTTES = frozenset([216, 219, 225, 227, 234, 322, 326, 332, 335, 336, 337,
                     338])
LEGENDES = frozenset(list(range(500, 515)) + [
    600, 601, 602, 604, 606, 608, 610, 612, 615, 618, 622, 624, 628, 630,
    633, 635, 639, 641, 645, 647, 650, 652, 655, 658,
    770, 773, 776, 777, 778, 779])
FAMILLES = {"histoire": HISTOIRE, "grottes": GROTTES, "legendes": LEGENDES}
# LE PREMIER NIVEAU DE CHAQUE LEGENDE (ZER-76) : les especes des evenements
# 46-58, un combat par boss (Mortamor : 510 et ses pinces 508/509, puis 514).
# Les niveaux 2 et 3 (evenements 59-84) ne sont plus tires par defaut :
# chaque legende ne pese plus qu'une fois dans le pool au lieu de trois.
LEGENDES_PREMIERES = frozenset(range(500, 515))
LEGENDES_HAUTES = LEGENDES - LEGENDES_PREMIERES
EVT_LEGENDES_PREMIERES = range(46, 59)

EVT_GROTTES = range(34, 46)
EVT_LEGENDES = range(46, 85)

# L'ORDRE DU SCENARIO (ZER-80) : les 30 boss d'histoire tirables, dans
# l'ordre des enregistrements d'`eventbattle.bin` -- celui du jeu, qui suit
# le scenario (Hexacorne d'abord, Corvus II en dernier, puis les quetes
# d'apres-jeu). Aquila et Corvus des cinematiques (800, 801) n'y sont pas :
# ils restent en place (ZER-74). `verifier_ordre()` le recompare a la ROM.
ORDRE_HISTOIRE = (300, 301, 302, 303, 304, 305, 306, 307, 308, 310, 309,
                  311, 312, 313, 314, 315, 316, 317, 344, 345, 346, 319, 318,
                  320, 347, 339, 341, 342, 343, 340)
# Les deux bornes speciales des seuils : des le debut (aucune borne, le
# comportement d'avant la 1.7) et jamais (la famille n'arrive dans aucun
# combat d'histoire).
DEBUT, JAMAIS = "debut", "jamais"


def position(espece):
    """La place d'un boss d'histoire dans le scenario (0 = Hexacorne), ou
    None pour un combat hors histoire (grottes, legendes)."""
    try:
        return ORDRE_HISTOIRE.index(espece)
    except ValueError:
        return None


def familles_permises(source, seuils):
    """Les familles de boss qu'un combat peut recevoir (ZER-80).

    `seuils` : {'grottes': s, 'legendes': s}, s = DEBUT, JAMAIS ou l'espece
    du boss d'histoire a partir duquel (inclus) la famille arrive. Un combat
    hors histoire (grotte, legende) n'a pas de place dans le scenario : il
    accepte tout."""
    out = {"histoire", "grottes", "legendes"}
    p = position(source)
    if p is None:
        return out
    for fam, s in seuils.items():
        if s == DEBUT:
            continue
        if s == JAMAIS or p < ORDRE_HISTOIRE.index(s):
            out.discard(fam)
    return out


def verifier_ordre(eventbattle):
    """Leve si ORDRE_HISTOIRE n'est pas l'ordre des enregistrements."""
    vus = []
    for r in eventbattle:
        if r.tag != 0x64 or len(r.fields) != 9:
            continue
        for k in (1, 3, 5):
            if r.fields[k] in ORDRE_HISTOIRE and r.fields[k] not in vus:
                vus.append(r.fields[k])
    if tuple(vus) != ORDRE_HISTOIRE:
        raise AssertionError("categories_boss : ordre du scenario %s, la ROM "
                             "dit %s" % (ORDRE_HISTOIRE, tuple(vus)))


def categorie(espece):
    """'histoire', 'grottes', 'legendes', ou None si ce n'est pas un boss."""
    for nom, ens in FAMILLES.items():
        if espece in ens:
            return nom
    return None


def verifier(pool_boss, eventbattle):
    """Leve si les listes ne couvrent pas EXACTEMENT le pool des boss, ou si
    un boss n'est pas range sous le numero d'evenement de sa famille.

    `pool_boss` : les identifiants des vrais boss (randomizer.py) ;
    `eventbattle` : les enregistrements (PrmTable.records) du fichier."""
    tous = HISTOIRE | GROTTES | LEGENDES
    if len(tous) != len(HISTOIRE) + len(GROTTES) + len(LEGENDES):
        raise AssertionError("categories_boss : familles non disjointes")
    if set(pool_boss) != tous:
        raise AssertionError("categories_boss : %d boss au pool, %d ranges ; "
                             "en trop %s, manquants %s"
                             % (len(set(pool_boss)), len(tous),
                                sorted(set(pool_boss) - tous),
                                sorted(tous - set(pool_boss))))
    for r in eventbattle:
        if r.tag != 0x64 or len(r.fields) != 9:
            continue
        evt = r.fields[0]
        for k in (1, 3, 5):
            if r.fields[k] in LEGENDES and (
                    (r.fields[k] in LEGENDES_PREMIERES)
                    != (evt in EVT_LEGENDES_PREMIERES)):
                raise AssertionError("categories_boss : espece %d, niveau de "
                                     "legende faux pour l'evenement %d"
                                     % (r.fields[k], evt))
        attendu = ("grottes" if evt in EVT_GROTTES else
                   "legendes" if evt in EVT_LEGENDES else "histoire")
        for k in (1, 3, 5):
            c = categorie(r.fields[k])
            if c is not None and c != attendu:
                raise AssertionError("categories_boss : espece %d en %s, "
                                     "evenement %d de la famille %s"
                                     % (r.fields[k], c, evt, attendu))
