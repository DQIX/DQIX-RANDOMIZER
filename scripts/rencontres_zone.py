"""Les monstres d'une carte remplaces 1 pour 1, carte par carte (ZER-73).

LE MODE. Sur le modele de « Area 1-to-1 » des randomizers Pokemon : dans une
carte, chaque espece du vanilla devient UNE autre espece, toujours la meme
dans cette carte ; une autre carte a son propre tirage. Aucune greffe de
code : seulement les trois tables de rencontres, donc le moteur fait ce qu'il
fait en vanilla (prechargement des modeles de la carte, groupes de combat).

LA CARTE, PAS L'AIRE. Une carte porte plusieurs aires (`encfld`, `encbtl`),
et `encmons` -- la liste des modeles que la carte precharge -- est par carte.
Un tirage par carte garde donc ensemble le symbole (encfld), le combat
(encbtl : meneuses ET compagnons) et le prechargement (encmons). Mesure : une
aire n'appartient jamais a deux cartes. Les trois aires d'encbtl qu'aucune
carte d'encfld ne porte suivent la correspondance globale.

LE TAS DES MODELES. Sans le blob, rien ne charge un modele a la demande : la
carte precharge sa liste (encmons) dans un tas de taille fixe. On refuse donc
un tirage dont la liste prechargee pese plus lourd que celle du vanilla pour
la meme carte (jusqu'a ESSAIS tirages, puis on prend des especes au modele au plus
aussi gros que celui qu'elles remplacent).

DES APPARITIONS EGALES (ZER-113, joueur, 28/10/2026 : « meme chance de
spawn pour chaque monstre », gros compris, par defaut, sans case). Le tirage
carte par carte, meme pondere par l'usage (ZER-101), laissait les gros
modeles 3 a 8 fois plus rares (scarlatin 0,43 carte par partie contre 3,5).
`appliquer` distribue desormais des QUOTAS : chaque NOM du bestiaire recoit
le meme nombre de places (un nom porte par plusieurs fiches -- gluant : 4 --
partage son quota entre elles, comme un ticket par nom de boss, ZER-112),
prechargees et renforts a part. Les gros modeles sont places d'abord, dans
les cartes qui ont le plus de marge ; les echanges entre cartes rendent
ensuite au budget celles qui le depassent, sans changer les quotas.
"""
import collections

ESSAIS = 40


def especes_par_carte(tables, ids_valides):
    """{carte: set(especes)} sur les trois tables, et {aire: carte}."""
    aire_carte = {}
    for carte, aire in tables.contextes("encfld.bin"):
        if carte is not None and aire is not None:
            aire_carte[aire] = carte
    par = collections.defaultdict(set)
    for nom, ir, _ic, _d, _m, val in tables.references(ids_valides):
        carte = _carte(tables, nom, ir, aire_carte)
        if carte is not None:
            par[carte].add(val)
    return par, aire_carte


_cache = {}


def _carte(tables, nom, ir, aire_carte):
    if nom not in _cache:
        _cache[nom] = tables.contextes(nom)
    carte, aire = _cache[nom][ir]
    if nom == "encbtl.bin":
        return aire_carte.get(aire)
    return carte


def _echantillon(rng, pool, n, usage):
    """`n` especes distinctes de `pool`, chacune avec un poids
    1 / (1 + usage)^POIDS_USAGE (Efraimidis-Spirakis : une cle par espece,
    les n plus grandes)."""
    cles = [(rng.random() ** ((1 + usage[e]) ** POIDS_USAGE), e) for e in pool]
    cles.sort(reverse=True)
    return [e for _c, e in cles[:n]]


# LE TIRAGE PONDERE PAR L'USAGE (ZER-101). Le refus des tirages trop lourds
# pour le tas favorisait les petits modeles : sur 20 graines, le bijou royal
# en platine sortait 2,2 fois plus que la moyenne, le scarlatin 3,5 fois
# moins (des joueurs ont vu des bijoux de platine partout, run apres run).
# Chaque espece deja placee pese moins pour la carte suivante : les petits
# modeles remplissent les cartes serrees, les gros les cartes larges.
POIDS_USAGE = 4


def tirer(rng, especes, pool, tailles, precharge=None, usage=None):
    """Une correspondance injective `especes` -> `pool`, dont la somme des
    tailles de modeles des especes PRECHARGEES (`precharge`, par defaut
    toutes) ne depasse pas celle des especes d'origine.

    SEULE LA LISTE PRECHARGEE PESE. Le tas des modeles ne recoit que la liste
    encmons de la carte ; une espece qui ne vient qu'en renfort de combat n'y
    entre pas. Un budget sur toutes les especes laissait une espece lourde
    entrer dans la liste pendant qu'un renfort leger compensait : +13 a +24 Ko
    sur une quarantaine de cartes (ZER-93, 10 graines).

    `usage` : {espece: cartes ou elle est deja placee}, mis a jour ; sans
    lui, le tirage uniforme d'avant (meme graine, meme resultat)."""
    source = sorted(especes)
    pre = [e for e in source if precharge is None or e in precharge]
    budget = sum(tailles.get(e, 0) for e in pre)
    out = None
    for _ in range(ESSAIS):
        cibles = (rng.sample(pool, len(source)) if usage is None
                  else _echantillon(rng, pool, len(source), usage))
        essai = dict(zip(source, cibles))
        if sum(tailles.get(essai[e], 0) for e in pre) <= budget:
            out = essai
            break
    if out is None:
        out = _repli(rng, source, pre, pool, tailles, usage)
    if usage is not None:
        for c in out.values():
            usage[c] += 1
    return out


def _repli(rng, source, pre, pool, tailles, usage):
    """Chaque espece prechargee prend une cible au modele pas plus gros
    (la moins placee d'abord, avec `usage`), les autres ce qui reste."""
    libres = list(pool)
    rng.shuffle(libres)
    if usage is not None:
        libres.sort(key=lambda c: usage[c])
    out = {}
    for e in sorted(pre, key=lambda e: -tailles.get(e, 0)):
        k = next((i for i, c in enumerate(libres)
                  if tailles.get(c, 0) <= tailles.get(e, 0)), None)
        out[e] = libres.pop(k) if k is not None else e
    for e in source:
        if e not in out:
            out[e] = (libres.pop(0 if usage is not None else -1) if libres
                      else e)
    return out


def permutation_par_bandes(rng, pool, tailles, bandes):
    """Une permutation de `pool` ou chaque espece prend la place d'une espece
    au modele de taille voisine : le pool, trie par taille, est coupe en
    `bandes` paquets egaux, permutes chacun a part. Pour le mode global sans
    blob : une permutation libre met la moitie des cartes au-dela du tas que
    le vanilla leur prevoit (mesure ZER-73, graine 5 : 108 / 211)."""
    tri = sorted(pool, key=lambda e: (tailles.get(e, 0), e))
    n = len(tri)
    out = {}
    for k in range(bandes):
        paquet = tri[k * n // bandes:(k + 1) * n // bandes]
        cibles = list(paquet)
        rng.shuffle(cibles)
        out.update(zip(paquet, cibles))
    return out


# LA MARGE DU MODE GLOBAL. Le vanilla laisse 36 a 99 Ko du tas des modeles
# inutilises a chaque montage (le reliquat que confisque le montage, mesure
# pour --place, research §47-57) : un lot plus lourd de 32 Ko au plus tient
# dans ce reliquat. Mesure ZER-73 sur 10 graines : permutation libre, jusqu'a
# +97 Ko ; 8 bandes, +62 ; 32 bandes, +33.
MARGE_GLOBALE = 32 * 1024


def permutation_globale(rng, pool, tailles, par_carte, marge=MARGE_GLOBALE):
    """La permutation la plus libre possible dont aucune carte ne depasse le
    poids de modeles du vanilla de plus de `marge`. On essaie des bandes de
    plus en plus fines, vingt tirages chacune. Rend (permutation, bandes,
    pire depassement en octets)."""
    for bandes in (1, 2, 4, 8, 16, 32, 64):
        for _ in range(20):
            p = permutation_par_bandes(rng, pool, tailles, bandes)
            pire = max(sum(tailles.get(p.get(e, e), 0) for e in esp)
                       - sum(tailles.get(e, 0) for e in esp)
                       for esp in par_carte.values())
            if pire <= marge:
                return p, bandes, pire
    raise SystemExit("mode global : aucune permutation sous la marge du tas")


def mesurer(rom, rom_vanilla, ids_valides, tailles):
    """Compare position par position les trois tables d'une ROM a celles du
    vanilla, carte par carte. Rend un dict de comptes :

    cartes, changees     cartes lues, cartes dont une espece a change
    non_fonction         cartes ou une meme espece vanilla devient deux especes
    non_injective        cartes ou deux especes vanilla deviennent la meme
    hors_budget          cartes dont la liste prechargee pese plus lourd
                         que celle du vanilla (tailles par IDENTIFIANT)
    terrain_hors_encmons cartes dont une espece de terrain n'est pas dans la
                         liste prechargee (vanilla : 2)
    """
    from enctables import TablesRencontres, FICHIERS_RENCONTRES
    tv = TablesRencontres(rom_vanilla, FICHIERS_RENCONTRES)
    tn = TablesRencontres(rom, FICHIERS_RENCONTRES)
    _cache.clear()
    _p, aire_carte = especes_par_carte(tv, ids_valides)
    ctx = {n: tv.contextes(n) for n in FICHIERS_RENCONTRES}
    neuf = {(n, ir, ic, d): v for n, ir, ic, d, _m, v in tn.references(ids_valides)}
    corr = collections.defaultdict(lambda: collections.defaultdict(set))
    terrain = collections.defaultdict(set)
    precharge = collections.defaultdict(set)
    precharge_v = collections.defaultdict(set)
    for n, ir, ic, d, _m, v in tv.references(ids_valides):
        carte, aire = ctx[n][ir]
        if n == "encbtl.bin":
            carte = aire_carte.get(aire)
        if carte is None:
            continue
        w = neuf.get((n, ir, ic, d), v)
        corr[carte][v].add(w)
        if n == "encfld.bin":
            terrain[carte].add(w)
        elif n == "encmons.bin":
            precharge[carte].add(w)
            precharge_v[carte].add(v)
    c = collections.Counter(cartes=len(corr))
    for carte, m in corr.items():
        if any(len(s) > 1 for s in m.values()):
            c["non_fonction"] += 1
        images = [next(iter(s)) for s in m.values()]
        if len(set(images)) != len(images):
            c["non_injective"] += 1
        if any(next(iter(s)) != v for v, s in m.items()):
            c["changees"] += 1
        if (sum(tailles.get(x, 0) for x in precharge[carte])
                > sum(tailles.get(v, 0) for v in precharge_v[carte])):
            c["hors_budget"] += 1
        if terrain[carte] - precharge[carte]:
            c["terrain_hors_encmons"] += 1
    return c


def _quotas(rng, n, poids):
    """`n` places reparties selon `poids` ({espece: poids}) : la part entiere
    de chacun, puis le reste par un tirage systematique sur les fractions.
    Rend {espece: places}."""
    total = sum(poids.values())
    exact = {e: n * w / total for e, w in poids.items()}
    out = {e: int(x) for e, x in exact.items()}
    reste = n - sum(out.values())
    ordre = sorted(poids)
    rng.shuffle(ordre)
    fr = [exact[e] - out[e] for e in ordre]
    pas = sum(fr) / reste if reste else 0
    u = rng.random() * pas
    cumul = 0.0
    for e, f in zip(ordre, fr):
        cumul += f
        while reste and u < cumul:
            out[e] += 1
            reste -= 1
            u += pas
    for e in ordre[:reste]:
        out[e] += 1
    return out


MARGE_TOTALE = 40000


def plan_egal(rng, cartes, pool, tailles, nom_de=None):
    """Les quotas places carte par carte. `cartes` : {carte: (sources
    prechargees, autres sources)}. Rend ({carte: {source: cible}}, cartes
    restees au-dela de leur budget)."""
    k_nom = collections.Counter(nom_de.get(e, e) for e in pool) if nom_de \
        else None
    poids = {e: 1.0 / k_nom[nom_de.get(e, e)] if k_nom else 1.0 for e in pool}
    t = lambda e: tailles.get(e, 0)
    budget = {c: sum(t(e) for e in pre) for c, (pre, _a) in cartes.items()}
    pris = {c: [] for c in cartes}             # cibles prechargees
    libres = {c: len(pre) for c, (pre, _a) in cartes.items()}
    poids_c = {c: 0 for c in cartes}
    # LES PLACES PRECHARGEES : les gros modeles d'abord, la ou il y a de la
    # marge (une fois garde de quoi loger les places restantes au plus leger)
    q = _quotas(rng, sum(libres.values()), poids)
    # L'ARRONDI PEUT DEPASSER LE BUDGET DE TOUTES LES CARTES ENSEMBLE (la
    # marge n'est que de 0,5 % : graines 17 et 22, +4 et +7 Ko) : quelques
    # places passent alors d'une grosse espece a une plus legere qui en a
    # moins, jusqu'a MARGE_TOTALE sous le budget. L'ecart ne grandit pas.
    cible = sum(budget.values()) - MARGE_TOTALE
    while sum(q[e] * t(e) for e in pool) > cible:
        haut = max(q.values())
        lourds = [e for e in pool if q[e] == haut]
        h = rng.choices(lourds, weights=[t(e) for e in lourds])[0]
        legers = [e for e in pool if q[e] < haut and t(e) < t(h)]
        if not legers:
            break
        x = rng.choice(legers)
        q[h] -= 1
        q[x] += 1
    ordre = sorted(pool, key=lambda e: (-t(e), rng.random()))
    restant = collections.Counter(q)
    for i, e in enumerate(ordre):
        for _ in range(q[e]):
            restant[e] -= 1
            mini = min((t(x) for x in ordre[i:] if restant[x] > 0
                        or x == e), default=0)
            ouvertes = [c for c in cartes if libres[c] and e not in pris[c]]
            if not ouvertes:
                break
            marge = {c: budget[c] - poids_c[c] - t(e) - (libres[c] - 1) * mini
                     for c in ouvertes}
            bonnes = [c for c in ouvertes if marge[c] >= 0]
            if bonnes:
                # au hasard, en proportion de la marge par place
                w = [1 + marge[c] / libres[c] for c in bonnes]
                c = rng.choices(bonnes, weights=w)[0]
            else:
                c = max(ouvertes, key=lambda c: (marge[c], rng.random()))
            pris[c].append(e)
            libres[c] -= 1
            poids_c[c] += t(e)
    # des places encore libres (quota tombe sur une carte qui l'avait deja) :
    # les especes les moins placees qui tiennent
    places = collections.Counter(x for v in pris.values() for x in v)
    for c in cartes:
        while libres[c]:
            cand = sorted((x for x in pool if x not in pris[c]),
                          key=lambda x: (places[x] / poids[x],
                                         poids_c[c] + t(x) > budget[c],
                                         rng.random()))
            pris[c].append(cand[0])
            places[cand[0]] += 1
            libres[c] -= 1
            poids_c[c] += t(cand[0])
    _reparer(rng, pris, poids_c, budget, t)
    _arrondir(rng, pris, poids_c, budget, t, pool)
    # ET SI RIEN NE TIENT (la carte porte deja les especes les plus legeres) :
    # ses especes d'origine, qui tiennent par definition
    for c, (pre, _a) in cartes.items():
        if poids_c[c] > budget[c]:
            pris[c] = list(pre)
            poids_c[c] = budget[c]
    # LES RENFORTS (sources hors de la liste prechargee) : pas de budget,
    # les memes quotas
    autres = {c: list(a) for c, (_p, a) in cartes.items()}
    q2 = _quotas(rng, sum(len(a) for a in autres.values()), poids)
    tickets = [e for e in sorted(q2) for _ in range(q2[e])]
    rng.shuffle(tickets)
    renforts = {c: [] for c in cartes}
    for c in sorted(cartes, key=lambda c: (-len(autres[c]), c)):
        for _ in autres[c]:
            deja = set(pris[c]) | set(renforts[c])
            k = next((k for k, e in enumerate(tickets) if e not in deja), None)
            if k is None:
                e = next(x for x in sorted(pool, key=lambda x: rng.random())
                         if x not in deja)
            else:
                e = tickets.pop(k)
            renforts[c].append(e)
    plan = {}
    for c, (pre, a) in cartes.items():
        cibles = list(pris[c])
        rng.shuffle(cibles)
        plan[c] = dict(zip(sorted(pre), cibles))
        plan[c].update(zip(sorted(a), renforts[c]))
    hors = [c for c in cartes if poids_c[c] > budget[c]]
    return plan, hors


def _reparer(rng, pris, poids_c, budget, t):
    """Echange des cibles entre cartes tant que le depassement TOTAL des
    budgets baisse : une cible d'une carte en trop contre une plus legere
    d'une autre carte, le meilleur echange d'abord. Les quotas ne changent
    pas (un echange garde le nombre de places de chaque espece)."""
    def trop(c, p=None):
        return max(0, (poids_c[c] if p is None else p) - budget[c])
    cartes = list(pris)
    for _tour in range(5000):
        dehors = [c for c in cartes if poids_c[c] > budget[c]]
        if not dehors:
            return
        rng.shuffle(dehors)
        meilleur = None
        for c1 in dehors:
            for h in set(pris[c1]):
                for c2 in cartes:
                    if c2 == c1 or h in pris[c2]:
                        continue
                    for l in set(pris[c2]):
                        d = t(h) - t(l)
                        if d <= 0 or l in pris[c1]:
                            continue
                        gain = (trop(c1) + trop(c2) - trop(c1, poids_c[c1] - d)
                                - trop(c2, poids_c[c2] + d))
                        if gain > 0 and (meilleur is None or gain > meilleur[0]):
                            meilleur = (gain, c1, h, c2, l)
            if meilleur:
                break
        if meilleur is None:
            return
        _g, c1, h, c2, l = meilleur
        d = t(h) - t(l)
        pris[c1][pris[c1].index(h)] = l
        pris[c2][pris[c2].index(l)] = h
        poids_c[c1] -= d
        poids_c[c2] += d


def _arrondir(rng, pris, poids_c, budget, t, pool):
    """DERNIER RECOURS, quand les echanges ne suffisent plus : une carte en
    trop cede une cible a une espece plus legere qui a MOINS de places
    (l'arrondi des quotas passe de l'une a l'autre : l'ecart entre especes
    ne grandit pas), puis on reprend les echanges."""
    for _tour in range(200):
        dehors = [c for c in pris if poids_c[c] > budget[c]]
        if not dehors:
            break
        places = collections.Counter(x for v in pris.values() for x in v)
        c1 = rng.choice(dehors)
        cand = [(t(h) - t(x), h, x) for h in set(pris[c1]) for x in pool
                if x not in pris[c1] and places[x] < places[h]
                and t(x) < t(h)]
        assez = [c for c in cand if poids_c[c1] - c[0] <= budget[c1]]
        if assez:
            _d, h, x = min(assez)
        elif cand:
            _d, h, x = max(cand)
        else:
            break
        pris[c1][pris[c1].index(h)] = x
        poids_c[c1] -= t(h) - t(x)
        _reparer(rng, pris, poids_c, budget, t)
    # LA GARANTIE (graine 69 : une carte a +40 o) : la cible la plus lourde
    # d'une carte encore en trop cede sa place a l'espece la moins placee
    # qui la fait tenir. Une espece gagne une place : rare, mesure par
    # work/zer113/banc_zone.py.
    for c1 in [c for c in pris if poids_c[c] > budget[c]]:
        places = collections.Counter(x for v in pris.values() for x in v)
        while poids_c[c1] > budget[c1]:
            h = max(pris[c1], key=t)
            cand = [x for x in pool if x not in pris[c1] and t(x) < t(h)]
            if not cand:
                break
            tient = [x for x in cand
                     if poids_c[c1] - t(h) + t(x) <= budget[c1]]
            x = (min(tient, key=lambda x: (places[x], rng.random())) if tient
                 else min(cand, key=t))
            pris[c1][pris[c1].index(h)] = x
            poids_c[c1] -= t(h) - t(x)
            places[x] += 1
            places[h] -= 1


def appliquer(tables, rng, pool, ids_valides, tailles, globale, nom_de=None,
              egal=True):
    """Remplace les especes carte par carte. `globale` sert aux especes hors
    de toute carte (les trois aires orphelines d'encbtl) et a celles que le
    pool ne couvre pas (boss, prologue : laissees a `globale`). `egal` : les
    quotas (ZER-113) ; faux, le tirage pondere par l'usage d'avant. Rend
    ({carte: correspondance}, nombre de references reecrites, cartes au-dela
    du budget)."""
    _cache.clear()
    par, aire_carte = especes_par_carte(tables, ids_valides)
    pool = sorted(pool)
    eligibles = set(pool)
    listes = tables.cartes()
    plan = {}
    hors = []
    if egal:
        cartes = {}
        for carte in sorted(par):
            especes = sorted(e for e in par[carte] if e in eligibles)
            pre = set(listes.get(carte, ()))
            cartes[carte] = ([e for e in especes if e in pre],
                             [e for e in especes if e not in pre])
        plan, hors = plan_egal(rng, cartes, pool, tailles, nom_de)

        def f(nom, ir, ancien):
            carte = _carte(tables, nom, ir, aire_carte)
            corr = plan.get(carte)
            if corr is not None and ancien in corr:
                return corr[ancien]
            return globale.get(ancien, ancien)
        return plan, tables.appliquer_fonction(f, ids_valides), hors
    usage = collections.Counter()
    # LES CARTES SERREES D'ABORD : elles ne peuvent prendre que de petits
    # modeles ; les cartes larges, tirees apres, compensent avec les gros.
    moyenne = sum(tailles.get(e, 0) for e in pool) / max(1, len(pool))

    def serrage(carte):
        pre = [e for e in par[carte] if e in eligibles
               and e in set(listes.get(carte, ()))]
        if not pre:
            return (1e9, carte)
        return (sum(tailles.get(e, 0) for e in pre) / len(pre) / moyenne,
                carte)

    for carte in sorted(par, key=serrage):
        especes = [e for e in par[carte] if e in eligibles]
        plan[carte] = tirer(rng, especes, pool, tailles,
                            set(listes.get(carte, ())), usage)

    def f(nom, ir, ancien):
        carte = _carte(tables, nom, ir, aire_carte)
        corr = plan.get(carte)
        if corr is not None and ancien in corr:
            return corr[ancien]
        return globale.get(ancien, ancien)
    return plan, tables.appliquer_fonction(f, ids_valides), hors
