"""Les monstres ordinaires des combats scriptes, tires dans le bestiaire
(ZER-104, decision du joueur du 27/10/2026).

AVANT. `--boss` permutait les 12 especes ordinaires des combats scriptes
entre elles (une correspondance par espece) : les deux cuirassassins du
general Mac Hulotte devenaient deux fois la meme espece, prise parmi douze.
Desormais, avec `--boss`, chaque EMPLACEMENT ordinaire (la table `autres` de
config_boss, 20 cases) recoit une espece du bestiaire, differente des autres
emplacements de son combat. `--boss-escortes-permutees` rend l'ancien
comportement.

LE POIDS DU COMBAT. Trop lourd, un combat scripte n'affiche que ses premiers
emplacements, sans gel (hypothermiasme / Barbarus / vampivolle : le premier
seul ; mesure du joueur, 27/10). Un combat ne depasse donc jamais `PLAFOND`,
boss compris. Un emplacement de boss tire a chaque visite par le blob compte
pour le plus lourd boss qu'il peut recevoir.

LA REGLE DU JEU (ZER-110, lue dans le code le 29/10/2026, research §108) :
avant de charger ses modeles, le combat retire de la place libre de son tas
(156 648 a 156 852 o mesures) la taille DECLAREE de chaque espece distincte
(`mon_btldata` +0x2A, en Ko : `tailles_modeles.tailles_declarees`), especes
amenees comprises (`SUPPLEMENTS`), et coupe la liste a la premiere qui ne
tient pas. Les tailles reelles des fichiers n'y sont pour rien : deux
plafonds en octets (160 312, puis 131 452) se sont reveles faux en jeu.

UN GENERATEUR A PART (graine du randomizer) : le reste de la ROM ne change
pas.
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import categories_boss as CB
import config_boss
from tailles_modeles import SUPPLEMENTS, modeles_combat, tailles_declarees

ESSAIS = 60
VIDE = 0xFFFFFFFF
# EN KO DECLARES. Le plus petit libre mesure tient 152 Ko (156 648 o) ; la
# place varie de quelques centaines d'octets avec les fiches chargees (132 o
# chacune) : 2 Ko de marge. En jeu : 153 Ko passe a 4 o pres (gluant /
# Barbarus / gluante), 155 et 159 Ko non (ZER-110).
PLAFOND = 150


def _especes(records):
    return [[r.fields[1 + 2 * k] for k in range(3)] if
            (r.tag == 0x64 and len(r.fields) == 9) else None for r in records]


def poids(especes, tailles):
    """Le poids d'un combat, en Ko declares : chaque espece distincte une
    fois, avec celles qu'elle amene (`SUPPLEMENTS`, en chaine). Un
    emplacement de nombre 0 compte aussi : non mesure, la prudence."""
    vus = set()
    pile = [e for e in especes if e != VIDE]
    while pile:
        e = pile.pop()
        if e not in vus:
            vus.add(e)
            pile.extend(SUPPLEMENTS.get(e, ()))
    return sum(tailles.get(e, 0) for e in vus)


def plafond(records_vanilla, tailles):
    """`PLAFOND` (le plus lourd combat du vanilla, Corvus seul, declare
    136 Ko)."""
    return PLAFOND


def appliquer(table, records_vanilla, graine, pool, masques=None,
              tailles=None):
    """Ecrit dans `table` (PrmTable d'eventbattle, deja permutee) une espece
    de `pool` a chaque emplacement ordinaire. `masques` : ceux de
    tirage_boss (bit k de l'evenement = emplacement k tire a chaque visite).
    Rend [(rang, emplacement, ancienne, nouvelle)]."""
    tailles = tailles or tailles_declarees()
    rng = random.Random("escortes-%s" % graine)
    limite = plafond(records_vanilla, tailles)
    ids = {e for esp in _especes(records_vanilla) if esp for e in esp}
    cases = [(r, k) for t, r, k, _e in config_boss.cases(records_vanilla, ids)
             if t == "autres"]
    par_rang = {}
    for r, k in cases:
        par_rang.setdefault(r, []).append(k)
    boss_max = max(tailles.get(e, 0)
                   for e in CB.TOUS)
    pool = [e for e in pool if tailles.get(e)]
    out = []
    for r in sorted(par_rang):
        rec = table.records[r]
        evt = rec.fields[0]
        libres = par_rang[r]
        fixes = [k for k in range(3) if k not in libres
                 and rec.fields[1 + 2 * k] != VIDE]
        m = masques[evt] if masques is not None and evt < len(masques) else 0
        # UN EMPLACEMENT TIRE A CHAQUE VISITE (masque) recoit un boss du
        # blob : il compte pour le plus lourd, escorte ou non. L'evenement 1
        # a deux fiches (Sylvane, rang 3, et le rang 97) : le masque de
        # Sylvane vaut aussi pour le premier emplacement du rang 97.
        masques_libres = [i for i, k in enumerate(libres) if m & (1 << k)]
        poids_masques = boss_max * (sum(1 for k in fixes if m & (1 << k))
                                    + len(masques_libres))
        fixes_pleins = [rec.fields[1 + 2 * k] for k in fixes
                        if not m & (1 << k)]
        deja = {rec.fields[1 + 2 * k] for k in fixes}
        candidats = [e for e in pool if e not in deja]
        budget = limite - poids_masques

        def pese(essai):
            return poids(fixes_pleins + [e for i, e in enumerate(essai)
                                         if i not in masques_libres], tailles)
        choix = None
        for _ in range(ESSAIS):
            essai = rng.sample(candidats, len(libres))
            if pese(essai) <= budget:
                choix = essai
                break
        if choix is None:
            # REPLI : a chaque emplacement, une espece qui laisse de quoi
            # loger les suivants au plus leger
            choix, reste = [], list(candidats)
            rng.shuffle(reste)
            leger = sorted(tailles[e] for e in candidats)
            comptes = [i for i in range(len(libres)) if i not in masques_libres]
            for i in range(len(libres)):
                if i in masques_libres:
                    e = reste[0]
                else:
                    apres = sum(leger[:len([j for j in comptes if j > i])])
                    e = next((c for c in reste if pese(choix + [c]) + apres
                              <= budget), None)
                    if e is None:
                        e = min(reste, key=lambda c: tailles[c])
                choix.append(e)
                reste.remove(e)
        for k, e in zip(libres, choix):
            out.append((r, k, rec.fields[1 + 2 * k], e))
            table.set_field(r, 1 + 2 * k, e)
    return out


def verifier(table, records_vanilla, masques=None, tailles=None,
             config=False):
    """Leve si un combat a escortes depasse le plafond, ou si deux de ses
    emplacements portent la meme espece tiree. `config` : une config de
    « Creer sa ROM » qui tire un emplacement a chaque visite est le choix du
    joueur, jamais un blocage (ZER-81) : ce combat-la n'est pas pese."""
    tailles = tailles or tailles_declarees()
    limite = plafond(records_vanilla, tailles)
    ids = {e for esp in _especes(records_vanilla) if esp for e in esp}
    rangs = {r for t, r, _k, _e in config_boss.cases(records_vanilla, ids)
             if t == "autres"}
    boss_max = max(tailles.get(e, 0)
                   for e in CB.TOUS)
    for r in rangs:
        rec = table.records[r]
        m = (masques[rec.fields[0]] if masques is not None
             and rec.fields[0] < len(masques) else 0)
        esp = [rec.fields[1 + 2 * k] for k in range(3)]
        p = (boss_max * sum(1 for k, e in enumerate(esp)
                            if e != VIDE and m & (1 << k))
             + poids([VIDE if m & (1 << k) else e for k, e in enumerate(esp)],
                     tailles))
        if p > limite and not (config and m):
            raise AssertionError("escortes : rang %d pese %d Ko, plafond %d"
                                 % (r, p, limite))
        pleins = [e for e in esp if e != VIDE]
        if len(set(pleins)) != len(pleins):
            raise AssertionError("escortes : rang %d, especes %s" % (r, esp))


def reserves(records_vanilla, pool, tailles=None):
    """{rang: Ko} des combats a escortes : le poids des escortes les plus
    legeres de `pool` qu'il faut y loger (une par emplacement ordinaire).
    L'allegement des boss le leur laisse (ZER-110)."""
    tailles = tailles or tailles_declarees()
    ids = {e for esp in _especes(records_vanilla) if esp for e in esp}
    legers = sorted(tailles[e] for e in pool if tailles.get(e))
    n = {}
    for t, r, k, _e in config_boss.cases(records_vanilla, ids):
        if t == "autres":
            n[r] = n.get(r, 0) + 1
    return {r: sum(legers[:k]) for r, k in n.items()}


# --- les combats a plusieurs boss (ZER-110) ----------------------------------
#
# Les trois combats de Mortamor (rangs 63, 76, 89) portent trois boss. Sous
# --boss, trois boss tires au hasard pesent jusqu'a 330 Ko : bien plus que le
# plafond, un seul s'affiche. Apres le tirage, on echange les cibles trop
# lourdes de ces combats avec les cibles legeres d'autres combats de boss :
# l'ensemble des cibles ne change pas (une permutation reste une permutation),
# et chaque echange respecte les familles permises des deux combats.

def combats_multiples(records_vanilla, sources):
    """{rang: [especes sources]} des combats qui portent au moins deux des
    `sources` (boss tires)."""
    out = {}
    for r, esp in enumerate(_especes(records_vanilla)):
        if not esp:
            continue
        s = [e for e in esp if e in sources]
        if len(s) >= 2:
            out[r] = s
    return out


def alleger_boss(corresp, records_vanilla, sources, graine, accepte=None,
                 tailles=None, cibles=(), reserves=None):
    """Modifie `corresp` ({source: cible}) pour que chaque combat a plusieurs
    boss tienne sous le plafond. `sources` : les boss tires (cles de
    `corresp` qui sont des boss) ; `accepte(source, cible)` -> bool, les
    seuils (ZER-80/107) ; `cibles` : les boss tirables, pour le dernier
    recours ; `reserves` : {rang: octets} laisses aux escortes (`reserves`),
    leur combat est allege aussi, meme avec un seul boss. Rend [(source,
    ancienne cible, nouvelle)]. Leve si un combat ne peut pas etre allege."""
    tailles = tailles or tailles_declarees()
    accepte = accepte or (lambda s, t: True)
    base = plafond(records_vanilla, tailles)
    sources = [s for s in sources if s in corresp]
    combats = combats_multiples(records_vanilla, set(sources))
    # LE COMBAT DE MAC HULOTTE (rang 19 : un boss, deux escortes) : un boss
    # lourd ne laissait pas la place des deux escortes (--boss, graine 5,
    # 28/10/2026). Le boss tire doit la leur laisser.
    especes = _especes(records_vanilla)
    for r in sorted(reserves or {}):
        s = [e for e in especes[r] or () if e in set(sources)]
        if s and r not in combats:
            combats[r] = s
    limite = {r: base - (reserves or {}).get(r, 0) for r in combats}
    fixes = {s for ss in combats.values() for s in ss}
    mobiles = sorted(s for s in sources if s not in fixes)
    # LES TROIS COMBATS SE PARTAGENT LES BOSS LEGERS (une dizaine sous
    # 60 Ko) : un choix au hasard pour le premier peut ne plus rien laisser
    # au dernier (graine 4 de --boss, 28/10/2026).
    # Alors on reprend avec un autre tirage ; le premier essai est celui
    # d'avant (meme graine, meme ROM quand il reussit), le dernier prend le
    # plus lourd qui tient (il garde les legers pour la suite).
    avant = dict(corresp)
    for essai in range(ESSAIS_ALLEGER + 1):
        corresp.update(avant)
        try:
            return _alleger(corresp, combats, mobiles, tailles, limite,
                            accepte, random.Random(
                                "alleger-%s" % graine if essai == 0
                                else "alleger-%s-%d" % (graine, essai)),
                            serre=(essai == ESSAIS_ALLEGER))
        except ValueError as e:
            erreur = e
    # ET SI LES ECHANGES UN PAR UN N'Y ARRIVENT PAS (graines 29 et 75 de
    # --boss, mesure du 28/10 sur 200 graines) : les neuf cibles choisies
    # ensemble.
    corresp.update(avant)
    out = _alleger_global(corresp, combats, mobiles, tailles, limite,
                          accepte, random.Random("alleger-global-%s" % graine))
    if out is None:
        # DERNIER RECOURS (ZER-110, 28/10/2026) : les
        # boss legers en usage ne suffisent pas -- familles egales, graine
        # 10 : une seule source vise une griffe gauche, aucune une griffe
        # droite, et chaque combat en veut deux. Les cibles de ces combats
        # sont alors prises parmi TOUS les boss tirables des familles deja
        # tirees, les cibles actuelles d'abord ; l'ensemble des cibles
        # change pour ces seuls combats.
        corresp.update(avant)
        out = _alleger_direct(corresp, combats, cibles, tailles, limite,
                              accepte, random.Random("alleger-direct-%s"
                                                     % graine),
                              {corresp[s] for s in sources})
    if out is None:
        raise erreur
    return out


def _alleger_direct(corresp, combats, cibles, tailles, limite, accepte, rng,
                    en_usage):
    """Chaque combat a plusieurs boss choisit ses cibles parmi `en_usage`
    (les cibles des boss, PAS celles des monstres du terrain) et `cibles`
    (memes familles que le tirage), sous le plafond, distinctes dans le
    combat (retour arriere, la cible actuelle d'abord). Modifie `corresp` et
    rend les echanges, ou None."""
    import categories_boss as CB
    familles = {CB.categorie(t) for t in en_usage} - {None}
    # une fiche par modele (griffe gauche : 509, 776, 777), celle en usage
    # s'il y en a une : le tirage donne un ticket par nom (ZER-112)
    modeles = modeles_combat()
    par_modele = {}
    for t in sorted(cibles, key=lambda t: (t not in en_usage, t)):
        if CB.categorie(t) in familles:
            par_modele.setdefault(modeles.get(t, t), t)
    candidats = sorted(en_usage | set(par_modele.values()))
    candidats = [t for t in candidats if t in tailles]
    out = []
    for r in sorted(combats):
        ss = combats[r]
        choix = []

        def chercher(k):
            if k == len(ss):
                return True
            s = ss[k]
            cand = [t for t in candidats if t not in choix and accepte(s, t)]
            rng.shuffle(cand)
            cand.sort(key=lambda t: t != corresp[s])
            for t in cand:
                if poids(choix + [t], tailles) + sum(sorted(
                        tailles[u] for u in candidats
                        if u not in choix and u != t)[:len(ss) - k - 1]) \
                        > limite[r]:
                    continue
                choix.append(t)
                if chercher(k + 1):
                    return True
                choix.pop()
            return False
        if not chercher(0):
            return None
        for s, t in zip(ss, choix):
            if corresp[s] != t:
                out.append((s, corresp[s], t))
                corresp[s] = t
    return out


ESSAIS_ALLEGER = 20
NOEUDS_GLOBAL = 200000


def _alleger_global(corresp, combats, mobiles, tailles, limite, accepte, rng):
    """Les cibles de tous les combats a plusieurs boss choisies ENSEMBLE
    (recherche avec retour arriere, la cible actuelle d'abord), parmi les
    cibles que portent ces combats et les sources mobiles ; puis chaque
    cible prise a une source mobile lui laisse une cible rendue (permutation
    gardee). Modifie `corresp` et rend les echanges, ou None."""
    import collections
    fixes = [s for r in sorted(combats) for s in combats[r]]
    rang_de = {s: r for r in combats for s in combats[r]}
    dispo = collections.Counter(corresp[x] for x in fixes + list(mobiles))
    legeres = sorted(dispo, key=lambda t: (tailles.get(t, 0), t))
    choix = {}
    noeuds = [0]

    def solutions(k):
        noeuds[0] += 1
        if noeuds[0] > NOEUDS_GLOBAL:
            return
        if k == len(fixes):
            yield dict(choix)
            return
        s = fixes[k]
        r = rang_de[s]
        pris = [choix[x] for x in combats[r] if x in choix]
        n_reste = sum(1 for x in combats[r] if x not in choix) - 1
        cand = [t for t in legeres if dispo[t] > 0 and t not in pris
                and accepte(s, t)]
        rng.shuffle(cand)
        cand.sort(key=lambda t: t != corresp[s])
        for t in cand:
            dispo[t] -= 1
            # borne : les places restantes prennent au moins les plus legeres
            mini = sum(tailles.get(u, 0) for u in [
                u for u in legeres for _ in range(dispo[u])][:n_reste])
            if poids(pris + [t], tailles) + mini <= limite[r]:
                choix[s] = t
                for sol in solutions(k + 1):
                    yield sol
                del choix[s]
            dispo[t] += 1

    for sol in solutions(0):
        avant = collections.Counter(corresp[s] for s in fixes)
        apres = collections.Counter(sol.values())
        entrent = list((apres - avant).elements())
        sortent = list((avant - apres).elements())
        rng.shuffle(sortent)
        donne = {}
        libres = list(mobiles)
        rng.shuffle(libres)
        for t in entrent:
            m = next((m for m in libres if corresp[m] == t and m not in donne
                      and any(accepte(m, o) for o in sortent)), None)
            if m is None:
                break
            o = next(o for o in sortent if accepte(m, o))
            sortent.remove(o)
            donne[m] = o
        else:
            out = [(s, corresp[s], t) for s, t in sol.items()
                   if corresp[s] != t]
            out += [(m, corresp[m], o) for m, o in donne.items()]
            corresp.update(sol)
            corresp.update(donne)
            return out
    return None


def _alleger(corresp, combats, mobiles, tailles, limite, accepte, rng,
             serre=False):
    out = []

    def pese(ss):
        return poids([corresp[s] for s in ss], tailles)
    for r in sorted(combats):
        ss = combats[r]
        while pese(ss) > limite[r]:
            lourd = max(ss, key=lambda s: (tailles.get(corresp[s], 0), s))
            t_l = corresp[lourd]
            cand = [m for m in mobiles
                    if tailles.get(corresp[m], 0) < tailles.get(t_l, 0)
                    and corresp[m] not in [corresp[s] for s in ss]
                    and accepte(lourd, corresp[m]) and accepte(m, t_l)]
            if not cand:
                raise ValueError("combat de rang %d : %d Ko, plafond %d, aucun "
                                 "boss assez leger a echanger"
                                 % (r, pese(ss), limite[r]))
            autres = [corresp[s] for s in ss if s != lourd]
            assez = [m for m in cand
                     if poids(autres + [corresp[m]], tailles) <= limite[r]]
            if assez and serre:
                m = max(assez, key=lambda m: (tailles.get(corresp[m], 0), m))
            else:
                m = (rng.choice(assez) if assez else
                     min(cand, key=lambda m: (tailles.get(corresp[m], 0), m)))
            out.append((lourd, t_l, corresp[m]))
            corresp[lourd], corresp[m] = corresp[m], t_l
    return out


def verifier_boss(table, records_vanilla, sources, tailles=None):
    """Leve si un combat a plusieurs boss depasse le plafond."""
    tailles = tailles or tailles_declarees()
    limite = plafond(records_vanilla, tailles)
    for r in combats_multiples(records_vanilla, set(sources)):
        rec = table.records[r]
        esp = [rec.fields[1 + 2 * k] for k in range(3)]
        p = poids(esp, tailles)
        if p > limite:
            raise AssertionError("boss : rang %d pese %d Ko, plafond %d"
                                 % (r, p, limite))
