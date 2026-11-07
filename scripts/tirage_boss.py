"""Le tirage des boss des combats scriptes, dans ses modes de la 1.6.

`--boss` seul garde son chemin d'origine (permutation des 89 boss dans
randomizer.py, greffe d'antre de ZER-37) : ce module ne sert que si l'une des
options suivantes est demandee.

    --boss-familles-egales  ZER-70  un combat de boss tire d'abord sa FAMILLE
                                    (histoire, grottes, legendes, wifi : un
                                    quart chacune, ZER-100), puis un boss
                                    dans la famille.
                                    Sans elle, les legendes (45 especes en
                                    trois niveaux) prennent 52 % des combats
                                    d'histoire et l'histoire 34 %.
    --boss-histoire         ZER-71  seuls les boss d'HISTOIRE (et des quetes
                                    wifi, comme avant ZER-100) sont tires, et
                                    seulement entre eux ; les combats des
                                    grottes et des legendes restent vanilla.
    --boss-mixte            ZER-62  le remplacant peut etre un monstre du
                                    bestiaire : les monstres forment une
                                    famille de plus, au meme poids que chaque
                                    famille de boss (1/2 sans familles egales,
                                    1/4 avec).
    --boss-chaque-combat    ZER-60  un boss neuf A CHAQUE ENTREE dans le
                                    combat, tire par la greffe du blob a la
                                    lecture d'`eventbattle.bin`. Ou le blob
                                    n'est pas monte (carte sans monstres), le
                                    tirage fait a la construction s'applique.

DEUX MOITIES. `plan()` rend la substitution ECRITE dans `eventbattle.bin` (le
jeu la lit partout, blob ou non) et, si une greffe est necessaire, la TABLE
que la greffe du blob consulte. La table ne sert qu'aux antres (un boss par
visite, comme ZER-37) ou, avec --boss-chaque-combat, a tous les combats de
boss du perimetre.

FORMAT DE LA TABLE (octets, petit-boutiste) :

    +0   u8   nombre de familles de boss (1 a 4)
    +1   u8   1 si les monstres forment une famille de plus (--boss-mixte)
    +2   u8   1 si le tirage d'un antre est retenu pour la visite (ZER-37)
    +3   u8   NEVT, le nombre d'evenements couverts par les masques
    +4   u16  compte de la famille 0, puis 1, 2, 3 (ZER-100 : quatre)
    +12  u16  deplacement des especes depuis +0
    +14  u16  deplacement du bitmap des monstres depuis +0
    +16  u8   masque par evenement : bit k = l'emplacement k est retire
    ...  u16  les especes des familles, bout a bout
    ...  u8   bitmap des monstres, 48 octets, bit i = espece i tirable
"""
import struct

import categories_boss as CB

NEVT = 143                # evenements 0 a 142 (eventbattle.bin en a 98)
VIDE = 0xFFFFFFFF         # emplacement sans espece
BITMAP_N = 48             # 384 especes, comme le bitmap du tireur de terrain
ANTRE_PREMIER, ANTRE_N = 34, 12


# UN TICKET PAR NOM (ZER-112, joueur, 28/10/2026). Sept noms sont portes par
# deux especes (Corvus 319/320, Moby Pick, Grizius, roi Govin de Klenfer, les
# trois generaux Mac) : a un ticket par espece, chacun sortait deux fois plus
# qu'un autre boss (2,6 combats par partie, jusqu'a 4 ; mesure_tirages.py).
# Les pioches tirent donc un NOM, puis une espece de ce nom dans son propre
# petit paquet -- « si ca empeche pas la deuxieme version du boss de sortir ».
# Sans `nom_de`, chaque espece est son propre nom : le tirage d'avant, graine
# pour graine.

def groupes_par_nom(pool, nom_de=None):
    """Les especes de `pool` groupees par nom, dans l'ordre de leur plus
    petite espece ; une espece sans nom est seule."""
    par = {}
    for e in sorted(set(pool)):
        cle = (nom_de or {}).get(e) or ("#", e)
        par.setdefault(cle, []).append(e)
    return sorted(par.values())


class _ParNom(object):
    """Le petit paquet de chaque nom : ses especes, rebattues quand il est
    vide. Un nom d'une espece ne consomme pas de hasard."""

    def __init__(self, rng, pool, nom_de):
        self.rng = rng
        self.groupes = groupes_par_nom(pool, nom_de)
        self.sous = {}

    def espece(self, g, accepte=None):
        especes = self.groupes[g]
        if len(especes) == 1:
            return especes[0]
        ok = accepte or (lambda t: True)
        sous = self.sous.setdefault(g, [])
        i = next((i for i in range(len(sous) - 1, -1, -1) if ok(sous[i])),
                 None)
        if i is None:
            frais = list(especes)
            self.rng.shuffle(frais)
            sous[:0] = frais
            i = next(i for i in range(len(sous) - 1, -1, -1) if ok(sous[i]))
        return sous.pop(i)


class Pioche(_ParNom):
    """Tirage sans remise, paquet reconstitue quand il est vide ; un ticket
    par nom (voir plus haut)."""

    def __init__(self, rng, pool, nom_de=None):
        _ParNom.__init__(self, rng, pool, nom_de)
        self.paquet = []

    def __call__(self):
        if not self.paquet:
            self.paquet = list(range(len(self.groupes)))
            self.rng.shuffle(self.paquet)
        return self.espece(self.paquet.pop())


class PiocheBornee(_ParNom):
    """Une Pioche dont chaque tirage n'accepte qu'une partie du pool (ZER-80).

    On prend la carte acceptable la plus haute du paquet ; s'il n'y en a plus,
    un paquet neuf passe DESSOUS, pour que les cartes restantes sortent avant
    d'etre redistribuees : chaque cible sort au moins une fois si le nombre
    de tirages le permet. Une carte est un nom : acceptable si l'une de ses
    especes l'est."""

    def __init__(self, rng, pool, nom_de=None):
        _ParNom.__init__(self, rng, pool, nom_de)
        self.pool = sorted(set(pool))
        self.paquet = []

    def _accepte(self, g, accepte):
        return any(accepte(t) for t in self.groupes[g])

    def _chercher(self, accepte):
        for i in range(len(self.paquet) - 1, -1, -1):
            if self._accepte(self.paquet[i], accepte):
                return i
        return None

    def possible(self, accepte):
        return any(accepte(t) for t in self.pool)

    def __call__(self, accepte):
        i = self._chercher(accepte)
        if i is None:
            frais = list(range(len(self.groupes)))
            self.rng.shuffle(frais)
            self.paquet[:0] = frais
            i = self._chercher(accepte)
        if i is None:
            raise ValueError("aucune cible acceptable")
        return self.espece(self.paquet.pop(i), accepte)


def ordre_contraint(sources, cibles, accepte):
    """Les sources les plus contraintes d'abord ; a egalite, par espece."""
    uniques = sorted(set(cibles))
    return sorted(sources, key=lambda s: (sum(1 for t in uniques
                                              if accepte(s, t)), s))


def tirer_borne(rng, sources, cibles, accepte, nom_de=None):
    """Un tirage ou chaque source n'accepte qu'une partie des cibles (ZER-80).
    `accepte(source, cible)` -> bool. Rend {source: cible}."""
    pioche = PiocheBornee(rng, cibles, nom_de)
    return {s: pioche(lambda t, s=s: accepte(s, t))
            for s in ordre_contraint(sources, cibles, accepte)}


def bornes_actives(seuils, fins=None):
    """Vrai si un seuil de ZER-80 ou une fin de ZER-107 restreint quelque
    chose."""
    return (any(s != CB.DEBUT for s in (seuils or {}).values())
            or any(f != CB.JAMAIS for f in (fins or {}).values()))


def demande(a):
    """Vrai si l'une des options de ce module est demandee."""
    return bool(a.boss_familles_egales or a.boss_histoire or a.boss_mixte
                or a.boss_chaque_combat)


def familles(pool_boss, histoire, egales, noms=False):
    """Les familles de boss du perimetre, dans l'ordre histoire, grottes,
    legendes, wifi ; une seule famille sans --boss-familles-egales. Avec
    `noms`, des couples (nom, especes) ; la famille unique s'appelle None.
    --boss-histoire garde les quetes wifi (son perimetre d'avant ZER-100)."""
    pool = set(pool_boss)
    if histoire:
        pool &= CB.HISTOIRE | CB.WIFI
    if not egales:
        return [(None, sorted(pool))] if noms else [sorted(pool)]
    out = [(f, sorted(pool & ens)) for f, ens in CB.FAMILLES.items()]
    out = [(f, e) for f, e in out if e]
    return out if noms else [e for _f, e in out]


def plan(rng, pool_boss, monstres, records, histoire=False, egales=False,
         mixte=False, chaque_combat=False, exclus=frozenset(), seuils=None,
         fins=None, nom_de=None):
    """Rend (correspondance, table ou None).

    `pool_boss` : les vrais boss tirables (garde et prologue deja retires) ;
    `monstres` : les especes du bestiaire que --boss-mixte peut mettre a la
    place d'un boss ; `records` : les enregistrements VANILLA
    d'eventbattle.bin (PrmTable.records), pour les masques ;
    `exclus` : des boss qui restent des COMBATS (sources) mais ne sont
    jamais tires (cibles) -- les niveaux 2 et 3 des legendes (ZER-76) ;
    `seuils`, `fins` : a partir de quel boss d'histoire une famille arrive
    (ZER-80) et a partir duquel elle n'est plus tiree (ZER-107),
    `categories_boss.familles_permises`. Sans borne active, le chemin
    d'avant, graine pour graine.
    """
    fams_src = familles(pool_boss, histoire, egales)
    sources = sorted(set().union(*fams_src))
    nommees = [(n, f) for n, f in
               ((n, [e for e in g if e not in exclus])
                for n, g in familles(pool_boss, histoire, egales, noms=True))
               if f]
    fams = [f for _n, f in nommees]
    borne = bornes_actives(seuils, fins) and not histoire
    if borne:
        def permises(s):
            return CB.familles_permises(s, seuils, fins)
    if borne and not (egales or mixte):
        corresp = tirer_borne(
            rng, sources, fams[0],
            lambda s, t: CB.categorie(t) in permises(s), nom_de)
    elif borne:
        # LES FAMILLES (ou la famille unique) PUIS UN BOSS, comme plus bas,
        # mais un combat ne choisit que parmi ce que ses seuils permettent.
        pioches = [(n, PiocheBornee(rng, f, nom_de)) for n, f in nommees]
        if mixte:
            pioches.append(("monstres", PiocheBornee(rng, monstres)))
        tous = [t for _n, f in nommees for t in f]
        corresp = {}
        for s in ordre_contraint(sources, tous,
                                 lambda s, t: CB.categorie(t) in permises(s)):
            def ok(t, s=s):
                return CB.categorie(t) is None or CB.categorie(t) in permises(s)
            choix = [p for _n, p in pioches if p.possible(ok)]
            corresp[s] = choix[rng.randrange(len(choix))](ok)
    elif (not (egales or mixte) and not set(sources) & set(exclus)
          and all(len(g) == 1 for g in groupes_par_nom(sources, nom_de))):
        # une permutation, comme --boss, mais sur le perimetre choisi
        cibles = list(sources)
        rng.shuffle(cibles)
        corresp = dict(zip(sources, cibles))
    elif not (egales or mixte):
        # MOINS DE CIBLES QUE DE COMBATS : un paquet qu'on epuise avant de le
        # rebattre, pour que chaque boss tirable sorte au moins une fois.
        pioche = Pioche(rng, fams[0], nom_de)
        corresp = {s: pioche() for s in sources}
    else:
        pioches = [Pioche(rng, f, nom_de) for f in fams]
        if mixte:
            pioches.append(Pioche(rng, monstres))
        corresp = {s: pioches[rng.randrange(len(pioches))]() for s in sources}

    # LA GREFFE : pour les antres (hors --boss-histoire, qui laisse les
    # grottes vanilla) ou pour tous les combats du perimetre.
    masques = bytearray(NEVT)
    # LES EVENEMENTS A ESCORTES (ZER-110) : une de leurs fiches porte un
    # monstre ordinaire. L'evenement 1 a deux fiches (Sylvane, rang 3, et le
    # rang 97, deux escortes) : un masque pose pour Sylvane vaudrait aussi au
    # rang 97.
    a_escortes = {r.fields[0] for r in records
                  if r.tag == 0x64 and len(r.fields) == 9 and any(
                      r.fields[j] not in corresp
                      and r.fields[j] not in (0, VIDE) for j in (1, 3, 5))}
    for r in records:
        if r.tag != 0x64 or len(r.fields) != 9 or r.fields[0] >= NEVT:
            continue
        evt = r.fields[0]
        antre = ANTRE_PREMIER <= evt < ANTRE_PREMIER + ANTRE_N
        if not (chaque_combat or antre):
            continue
        # UN COMBAT A PLUSIEURS BOSS (Mortamor, ZER-110) n'est pas tire au
        # combat : un boss du blob compte pour le plus lourd (136 Ko
        # declares), il ne resterait pas de quoi loger les deux autres sous
        # le tas (150). Le tirage de la construction, allege
        # (escortes.alleger_boss), s'applique.
        if sum(1 for j in (1, 3, 5) if r.fields[j] in corresp) >= 2:
            continue
        # NI UN EVENEMENT A ESCORTES (Mac Hulotte, Sylvane et le rang 97) :
        # 136 Ko de boss et des escortes ne tiennent pas sous le tas ; le
        # boss tire a la construction, allege pour leur laisser la place,
        # s'applique.
        if evt in a_escortes:
            continue
        for k, j in enumerate((1, 3, 5)):
            # UN COMBAT BORNE PAR UN SEUIL (ZER-80) N'EST PAS RETIRE AU
            # COMBAT : la greffe tire dans toutes les familles, elle ne
            # connait pas l'avancement du scenario. Le tirage fait a la
            # construction, qui respecte le seuil, s'applique.
            if borne and len(permises(r.fields[j])) < len(CB.FAMILLES):
                continue
            if r.fields[j] in corresp and (chaque_combat or k == 0):
                masques[evt] |= 1 << k
    if not any(masques):
        return corresp, None
    return corresp, table(fams, monstres if mixte else (), masques,
                          retenir=not chaque_combat)


def table(fams, monstres, masques, retenir):
    """Les octets de la table (voir le format en tete du module)."""
    if not 1 <= len(fams) <= 4:
        raise ValueError("de 1 a 4 familles de boss")
    especes = [e for f in fams for e in f]
    off_esp = 16 + ((len(masques) + 3) & ~3)
    off_bitmap = off_esp + ((2 * len(especes) + 3) & ~3)
    comptes = [len(f) for f in fams] + [0] * (4 - len(fams))
    t = bytearray(off_bitmap + (BITMAP_N if monstres else 0))
    struct.pack_into("<BBBB4HHH", t, 0, len(fams), 1 if monstres else 0,
                     1 if retenir else 0, len(masques), *comptes,
                     off_esp, off_bitmap if monstres else 0)
    t[16:16 + len(masques)] = masques
    for k, e in enumerate(especes):
        struct.pack_into("<H", t, off_esp + 2 * k, e)
    for e in monstres:
        if not 0 < e < 8 * BITMAP_N:
            raise ValueError("espece %d hors du bitmap" % e)
        t[off_bitmap + (e >> 3)] |= 1 << (e & 7)
    return bytes(t)


def relire(t):
    """Decode une table : (familles, monstres, masques, retenir)."""
    nf, mixte, retenir, nevt, c0, c1, c2, c3, off_esp, off_bm = \
        struct.unpack_from("<BBBB4HHH", t, 0)
    masques = bytes(t[16:16 + nevt])
    fams, k = [], off_esp
    for c in (c0, c1, c2, c3)[:nf]:
        fams.append([struct.unpack_from("<H", t, k + 2 * i)[0]
                     for i in range(c)])
        k += 2 * c
    monstres = []
    if mixte:
        monstres = [i for i in range(8 * BITMAP_N)
                    if t[off_bm + (i >> 3)] & (1 << (i & 7))]
    return fams, monstres, masques, bool(retenir)
