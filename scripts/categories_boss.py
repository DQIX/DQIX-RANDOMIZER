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

EVT_GROTTES = range(34, 46)
EVT_LEGENDES = range(46, 85)


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
        attendu = ("grottes" if evt in EVT_GROTTES else
                   "legendes" if evt in EVT_LEGENDES else "histoire")
        for k in (1, 3, 5):
            c = categorie(r.fields[k])
            if c is not None and c != attendu:
                raise AssertionError("categories_boss : espece %d en %s, "
                                     "evenement %d de la famille %s"
                                     % (r.fields[k], c, evt, attendu))
