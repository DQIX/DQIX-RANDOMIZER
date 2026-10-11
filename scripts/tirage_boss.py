"""Le tirage des boss des combats scriptes, dans ses modes de la 1.6.

`--boss` seul garde son chemin d'origine (permutation des 89 boss dans
randomizer.py, greffe d'antre de ZER-37) : ce module ne sert que si l'une des
options suivantes est demandee.

    --boss-familles-egales  ZER-70  un combat de boss tire d'abord sa FAMILLE
                                    (histoire, grottes, legendes : un tiers
                                    chacune), puis un boss dans la famille.
                                    Sans elle, les legendes (45 especes en
                                    trois niveaux) prennent 52 % des combats
                                    d'histoire et l'histoire 34 %.
    --boss-histoire         ZER-71  seuls les boss d'HISTOIRE sont tires, et
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

    +0   u8   nombre de familles de boss (1 a 3)
    +1   u8   1 si les monstres forment une famille de plus (--boss-mixte)
    +2   u8   1 si le tirage d'un antre est retenu pour la visite (ZER-37)
    +3   u8   NEVT, le nombre d'evenements couverts par les masques
    +4   u16  compte de la famille 0, puis 1, puis 2
    +10  u16  deplacement des especes depuis +0
    +12  u16  deplacement du bitmap des monstres depuis +0
    +14  u16  0
    +16  u8   masque par evenement : bit k = l'emplacement k est retire
    ...  u16  les especes des familles, bout a bout
    ...  u8   bitmap des monstres, 48 octets, bit i = espece i tirable
"""
import struct

import categories_boss as CB

NEVT = 143                # evenements 0 a 142 (eventbattle.bin en a 98)
BITMAP_N = 48             # 384 especes, comme le bitmap du tireur de terrain
ANTRE_PREMIER, ANTRE_N = 34, 12


class Pioche(object):
    """Tirage sans remise, paquet reconstitue quand il est vide."""

    def __init__(self, rng, pool):
        self.rng = rng
        self.pool = sorted(pool)
        self.paquet = []

    def __call__(self):
        if not self.paquet:
            self.paquet = list(self.pool)
            self.rng.shuffle(self.paquet)
        return self.paquet.pop()


def demande(a):
    """Vrai si l'une des options de ce module est demandee."""
    return bool(a.boss_familles_egales or a.boss_histoire or a.boss_mixte
                or a.boss_chaque_combat)


def familles(pool_boss, histoire, egales):
    """Les familles de boss du perimetre, dans l'ordre histoire, grottes,
    legendes ; une seule famille sans --boss-familles-egales."""
    pool = set(pool_boss)
    if histoire:
        pool &= CB.HISTOIRE
    if not egales:
        return [sorted(pool)]
    out = [sorted(pool & CB.FAMILLES[f])
           for f in ("histoire", "grottes", "legendes")]
    return [f for f in out if f]


def plan(rng, pool_boss, monstres, records, histoire=False, egales=False,
         mixte=False, chaque_combat=False):
    """Rend (correspondance, table ou None).

    `pool_boss` : les vrais boss tirables (garde et prologue deja retires) ;
    `monstres` : les especes du bestiaire que --boss-mixte peut mettre a la
    place d'un boss ; `records` : les enregistrements VANILLA
    d'eventbattle.bin (PrmTable.records), pour les masques.
    """
    fams = familles(pool_boss, histoire, egales)
    sources = sorted(set().union(*fams))
    if not (egales or mixte):
        # une permutation, comme --boss, mais sur le perimetre choisi
        cibles = list(sources)
        rng.shuffle(cibles)
        corresp = dict(zip(sources, cibles))
    else:
        pioches = [Pioche(rng, f) for f in fams]
        if mixte:
            pioches.append(Pioche(rng, monstres))
        corresp = {s: pioches[rng.randrange(len(pioches))]() for s in sources}

    # LA GREFFE : pour les antres (hors --boss-histoire, qui laisse les
    # grottes vanilla) ou pour tous les combats du perimetre.
    masques = bytearray(NEVT)
    for r in records:
        if r.tag != 0x64 or len(r.fields) != 9 or r.fields[0] >= NEVT:
            continue
        evt = r.fields[0]
        antre = ANTRE_PREMIER <= evt < ANTRE_PREMIER + ANTRE_N
        if not (chaque_combat or antre):
            continue
        for k, j in enumerate((1, 3, 5)):
            if r.fields[j] in corresp and (chaque_combat or k == 0):
                masques[evt] |= 1 << k
    if not any(masques):
        return corresp, None
    return corresp, table(fams, monstres if mixte else (), masques,
                          retenir=not chaque_combat)


def table(fams, monstres, masques, retenir):
    """Les octets de la table (voir le format en tete du module)."""
    if not 1 <= len(fams) <= 3:
        raise ValueError("de 1 a 3 familles de boss")
    especes = [e for f in fams for e in f]
    off_esp = 16 + ((len(masques) + 3) & ~3)
    off_bitmap = off_esp + ((2 * len(especes) + 3) & ~3)
    comptes = [len(f) for f in fams] + [0] * (3 - len(fams))
    t = bytearray(off_bitmap + (BITMAP_N if monstres else 0))
    struct.pack_into("<BBBB3HHHH", t, 0, len(fams), 1 if monstres else 0,
                     1 if retenir else 0, len(masques), *comptes,
                     off_esp, off_bitmap if monstres else 0, 0)
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
    nf, mixte, retenir, nevt, c0, c1, c2, off_esp, off_bm, _ = \
        struct.unpack_from("<BBBB3HHHH", t, 0)
    masques = bytes(t[16:16 + nevt])
    fams, k = [], off_esp
    for c in (c0, c1, c2)[:nf]:
        fams.append([struct.unpack_from("<H", t, k + 2 * i)[0]
                     for i in range(c)])
        k += 2 * c
    monstres = []
    if mixte:
        monstres = [i for i in range(8 * BITMAP_N)
                    if t[off_bm + (i >> 3)] & (1 << (i & 7))]
    return fams, monstres, masques, bool(retenir)
