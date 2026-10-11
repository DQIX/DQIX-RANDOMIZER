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
carte precharge sa liste dans un tas de taille fixe. On refuse donc un tirage
dont la somme des tailles de modeles depasse celle du vanilla pour la meme
carte (jusqu'a ESSAIS tirages, puis on prend des especes au modele au plus
aussi gros que celui qu'elles remplacent).
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


def tirer(rng, especes, pool, tailles):
    """Une correspondance injective `especes` -> `pool`, dont la somme des
    tailles de modeles ne depasse pas celle des especes d'origine."""
    source = sorted(especes)
    budget = sum(tailles.get(e, 0) for e in source)
    for _ in range(ESSAIS):
        cibles = rng.sample(pool, len(source))
        if sum(tailles.get(c, 0) for c in cibles) <= budget:
            return dict(zip(source, cibles))
    # repli : chaque espece prend une cible au modele pas plus gros
    libres = list(pool)
    rng.shuffle(libres)
    out = {}
    for e in sorted(source, key=lambda e: -tailles.get(e, 0)):
        k = next((i for i, c in enumerate(libres)
                  if tailles.get(c, 0) <= tailles.get(e, 0)), None)
        out[e] = libres.pop(k) if k is not None else e
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
    hors_budget          cartes dont la somme des tailles de modeles depasse
                         celle du vanilla
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
    c = collections.Counter(cartes=len(corr))
    for carte, m in corr.items():
        if any(len(s) > 1 for s in m.values()):
            c["non_fonction"] += 1
        images = [next(iter(s)) for s in m.values()]
        if len(set(images)) != len(images):
            c["non_injective"] += 1
        if any(next(iter(s)) != v for v, s in m.items()):
            c["changees"] += 1
        if (sum(tailles.get(next(iter(s)), 0) for s in m.values())
                > sum(tailles.get(v, 0) for v in m)):
            c["hors_budget"] += 1
        if terrain[carte] - precharge[carte]:
            c["terrain_hors_encmons"] += 1
    return c


def appliquer(tables, rng, pool, ids_valides, tailles, globale):
    """Remplace les especes carte par carte. `globale` sert aux especes hors
    de toute carte (les trois aires orphelines d'encbtl) et a celles que le
    pool ne couvre pas (boss, prologue : laissees a `globale`). Rend
    ({carte: correspondance}, nombre de references reecrites)."""
    _cache.clear()
    par, aire_carte = especes_par_carte(tables, ids_valides)
    pool = sorted(pool)
    eligibles = set(pool)
    plan = {}
    for carte in sorted(par):
        especes = [e for e in par[carte] if e in eligibles]
        plan[carte] = tirer(rng, especes, pool, tailles)

    def f(nom, ir, ancien):
        carte = _carte(tables, nom, ir, aire_carte)
        corr = plan.get(carte)
        if corr is not None and ancien in corr:
            return corr[ancien]
        return globale.get(ancien, ancien)
    return plan, tables.appliquer_fonction(f, ids_valides)
