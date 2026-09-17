#!/usr/bin/env python3
"""Placer les objets selon leur rarete (0 a 5 etoiles), sans perdre la
couverture : chaque objet du pool sort au moins une fois.

LES REGLES, decidees par le joueur (17 septembre) :

  drops des monstres, selon la chance de l'emplacement
    toujours, 1/8, 1/16   0-1 etoile
    1/32, 1/64            2-3 etoiles
    1/128                 4 etoiles
    1/256                 4-5 etoiles (les seuls drops a 5 etoiles)
    jamais                n'importe quoi (emplacement inatteignable)

  coffres bleus, selon le rang (6, 7, 8 sont les jumeaux de 3, 4, 5)
    rangs 1-2             0-2 etoiles
    rangs 3 et 6          2-3 etoiles
    rangs 4 et 7          3-4 etoiles
    rangs 5 et 8          3-5 etoiles (le rang maximum, seuls a 5 etoiles)

  pots, tonneaux, placards, selon le rang (1 a 20)
    rangs 1-7             0-1 etoile
    rangs 8-13            1-2 etoiles
    rangs 14-19           2-3 etoiles
    rang 20               3-5 etoiles (le rang maximum, seul a 5 etoiles)

  coffres rouges          n'importe quel objet, 0 a 5 etoiles

L'AFFECTATION. Chaque emplacement accepte un ensemble d'etoiles. On cherche
d'abord a donner a CHAQUE objet du pool une place qui l'accepte : c'est un
probleme de flot (etoiles -> groupes d'emplacements), resolu exactement par
Edmonds-Karp sur un graphe minuscule. Si le flot ne couvre pas tout le pool, on
leve : les regles seraient trop serrees pour la graine. Les places restantes
recoivent ensuite un objet tire au hasard parmi ceux que leur groupe accepte.
"""
import collections

TOUTES = frozenset(range(6))

DROP = {0: {0, 1}, 1: {0, 1}, 2: {0, 1}, 3: {2, 3}, 4: {2, 3}, 5: {4},
        6: {4, 5}, 7: set(TOUTES)}
BLEU = {1: {0, 1, 2}, 2: {0, 1, 2}, 3: {2, 3}, 6: {2, 3}, 4: {3, 4},
        7: {3, 4}, 5: {3, 4, 5}, 8: {3, 4, 5}}


def pot(rang):
    if rang <= 7:
        return {0, 1}
    if rang <= 13:
        return {1, 2}
    if rang <= 19:
        return {2, 3}
    return {3, 4, 5}


def _flot_max(capacites, source, puits):
    """Edmonds-Karp. `capacites` : dict (u, v) -> capacite. Rend le flot par arc."""
    # ORDRE STABLE OBLIGATOIRE. Les noeuds contiennent des chaines, dont le
    # hachage change a chaque lancement de Python : parcourir un `set` rendait un
    # flot different d'une execution a l'autre, donc une ROM differente pour la
    # meme graine. On trie les voisins par `repr`.
    voisins = collections.defaultdict(set)
    for (u, v) in list(capacites):
        voisins[u].add(v)
        voisins[v].add(u)
        capacites.setdefault((v, u), 0)
    voisins = {u: sorted(vs, key=repr) for u, vs in voisins.items()}
    flot = collections.defaultdict(int)
    while True:
        parent = {source: None}
        file = collections.deque([source])
        while file and puits not in parent:
            u = file.popleft()
            for v in voisins[u]:
                if v not in parent and capacites[(u, v)] - flot[(u, v)] > 0:
                    parent[v] = u
                    file.append(v)
        if puits not in parent:
            return flot
        chemin, v = [], puits
        while parent[v] is not None:
            chemin.append((parent[v], v))
            v = parent[v]
        d = min(capacites[e] - flot[e] for e in chemin)
        for (u, v) in chemin:
            flot[(u, v)] += d
            flot[(v, u)] -= d


def affecter(rng, emplacements, etoiles, pool):
    """`emplacements` : liste de (cle, ensemble d'etoiles acceptees).
    `etoiles` : {objet: 0..5}. `pool` : objets a placer.
    Rend {cle: objet}. Chaque objet du pool recoit au moins une place."""
    groupes = collections.OrderedDict()
    for cle, ens in emplacements:
        groupes.setdefault(frozenset(ens), []).append(cle)
    par_etoile = collections.defaultdict(list)
    for o in pool:
        par_etoile[etoiles[o]].append(o)

    cap = {}
    for s, objs in par_etoile.items():
        cap[("S", ("e", s))] = len(objs)
        for g in groupes:
            if s in g:
                cap[(("e", s), ("g", g))] = len(objs)
    for g, cles in groupes.items():
        cap[(("g", g), "T")] = len(cles)
    flot = _flot_max(cap, "S", "T")
    place = sum(flot[("S", ("e", s))] for s in par_etoile)
    if place != len(pool):
        manque = {s: len(o) - flot[("S", ("e", s))] for s, o in par_etoile.items()
                  if flot[("S", ("e", s))] < len(o)}
        raise ValueError("rarete : %d objets sur %d ont une place ; manquants "
                         "par etoiles : %s" % (place, len(pool), manque))

    affecte = {}
    restes = {g: list(cles) for g, cles in groupes.items()}
    for g in restes:
        rng.shuffle(restes[g])
    for s, objs in sorted(par_etoile.items()):
        objs = list(objs)
        rng.shuffle(objs)
        for g in groupes:
            n = flot.get((("e", s), ("g", g)), 0)
            for _ in range(n):
                affecte[restes[g].pop()] = objs.pop()
    # places restantes : un objet quelconque que le groupe accepte
    for g, cles in restes.items():
        candidats = [o for o in pool if etoiles[o] in g]
        for cle in cles:
            affecte[cle] = rng.choice(candidats)
    return affecte
