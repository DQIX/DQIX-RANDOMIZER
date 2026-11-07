#!/usr/bin/env python3
"""Randomiser les RECETTES DES BIBLIOTHEQUES (ZER-105, 1.8).

LE FORMAT (mesure le 27/10/2026, research §102). Les bibliotheques sont sept
archives `data/scenario/htana<X>.gp2` (X = C, D, H, M, R, S, X), un membre
`htana<X>_<lg>.bin` par langue : un script Nitro (treasure.lire_script).
Chaque etagere est un opcode 0x66 :

    p0      l'etagere (5704...)              } entiers, les memes dans les
    p1..p3  drapeaux (p3 : livre deja lu)    } cinq langues
    p4      message « aucun livre interessant »  (chaine : deplacement dans
    p5      message du livre, quand il apprend   la zone de donnees du
    p6      message « deja connues »             script)
    p7..    les RECETTES APPRISES (identifiants de recipe.gp2, recettes.py)

Le message du livre nomme les produits (« <LEADER> finds recipes for an ogre
shield... ») par pages de trois, chacune finie par <SE_RECIPE> ; avant, le
titre du livre et une ligne de conseil qui cite des ingredients. 105 livres,
345 emplacements (327 recettes : 18 sont dans deux livres).

DEMANDE DU JOUEUR (27/10/2026) : tirer les recettes de chaque bibliotheque,
JAMAIS DEUX FOIS LA MEME DANS LE JEU, textes generiques. Option
`--alchimie-bibliotheques`, independante de `--alchimie`.

CE QUE FAIT CE PATCH.
  * Chaque emplacement recoit une recette tiree sans remise parmi les 448
    recettes de base (les 22 variantes de grand succes s'apprennent avec leur
    base) : 345 recettes toutes differentes. Le meme tirage dans les cinq
    langues ; chaque livre garde son nombre de recettes.
  * Les messages p5 et p6 sont reecrits EN PLACE, plus courts : le titre du
    livre (la premiere page), puis LES NOMS DES OBJETS TIRES (joueur,
    29/10/2026 : « ca ne m'a pas dit ce que j'apprenais »), trois par page,
    chaque page finie par <SE_RECIPE> ; la page de conseil (des ingredients
    d'avant) disparait. Liste sans articles (« decouvre les recettes
    suivantes : A, B, C. ») : les articles demandent la grammaire de chaque
    langue. Un message qui ne tiendrait pas dans la place d'origine, ou que
    deux etageres aux tirages differents partagent, garde la phrase
    generique (« <LEADER> learns the recipes in this book »). Le reste de
    l'ancienne chaine est mis a zero. Aucune taille de membre ne change ;
    l'archive est recompressee (gp2_ecrire.reecrire).

Generateur a part, derive de la graine : rien d'autre ne bouge.
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gp2_ecrire
import objets
import recettes
import treasure as T

FICHIERS = tuple("data/scenario/htana%s.gp2" % x for x in "CDHMRSX")
LANGUES = ("de", "en", "es", "fr", "it")
OP_ETAGERE = 0x66
P_APPRIS, P_CONNU, P_RECETTES = 5, 6, 7
PAGE, SE = b"<PAGE>", b"<SE_RECIPE>"
# LES PHRASES GENERIQUES, sur le modele de la phrase « deja connues » de
# chaque langue (texte du jeu : <Cap>, <LEADER>, accents en balises).
APPRIS = {
    "en": b"<Cap><LEADER> learns the recipes in this book.",
    "fr": b"<Cap><LEADER> d<'e>couvre les recettes de ce livre.",
    "de": b"<Cap><LEADER> lernt die in dem Buch beschriebenen Rezepte.",
    "es": b"<Cap><LEADER> aprende las recetas de ese libro.",
    "it": b"<Cap><LEADER> impara le ricette contenute in questo libro!",
}
ENCORE = {
    "en": b"There are more recipes in it.",
    "fr": b"Il y en a d<1>autres.",
    "de": b"Es gibt noch weitere Rezepte.",
    "es": b"Hay m<'a>s recetas.",
    "it": b"Ci sono altre ricette.",
}


# LES MESSAGES NOMMES : la premiere page de noms, puis les suivantes. `<:>`
# est le deux-points du jeu (colle au mot, comme « anges<:> l'arbre »),
# `<,>` la virgule.
NOMME = {
    "en": b"<Cap><LEADER> finds these recipes<:> ",
    "fr": b"<Cap><LEADER> d<'e>couvre les recettes suivantes<:> ",
    "de": b"<Cap><LEADER> findet diese Rezepte<:> ",
    "es": b"<Cap><LEADER> encuentra estas recetas<:> ",
    "it": b"<Cap><LEADER> ha trovato queste ricette<:> ",
}
NOMME_SUITE = {
    "en": b"<IF_MALE>He<ELSE_NOT_MALE>She<ENDIF_MALE> also finds<:> ",
    "fr": b"<IF_MALE>Il<ELSE_NOT_MALE>Elle<ENDIF_MALE> d<'e>couvre aussi<:> ",
    "de": b"<IF_MALE>Er<ELSE_NOT_MALE>Sie<ENDIF_MALE> findet auch<:> ",
    "es": b"Tambi<'e>n encuentra<:> ",
    "it": b"Ci sono anche<:> ",
}
PAR_PAGE = 3


def generateur(seed):
    return random.Random("bibliotheques:%d" % seed)


def _membre(rom, chemin, lg):
    nom = os.path.basename(chemin)[:-4]
    return objets._membre_archive(rom, chemin, "%s_%s.bin" % (nom, lg))


def etageres(rom, lg="en"):
    """[(fichier, rang de l'instruction, [recettes], instruction)] des
    etageres qui apprennent quelque chose, dans l'ordre des fichiers."""
    out = []
    for ch in FICHIERS:
        _h, cmds = T.lire_script(_membre(rom, ch, lg), 0)
        for k, c in enumerate(cmds):
            if c.op == OP_ETAGERE and len(c.valeurs) > P_RECETTES:
                out.append((ch, k, list(c.valeurs[P_RECETTES:]), c))
    return out


def recettes_de_base(rom):
    """Les recettes qu'une etagere peut apprendre : sans les variantes de
    grand succes."""
    return sorted(r["id"] for r in recettes.lire(rom) if r["base"] is None)


def _chaine(d, od, o):
    deb = od + o
    return deb, d.index(b"\x00", deb)


def _generique(ancien, lg):
    """Le message reecrit : le titre (premiere page) puis la phrase
    generique, avec autant de <SE_RECIPE> qu'avant."""
    pages = ancien.split(PAGE)
    titre = [pages[0]] if len(pages) > 1 else []
    n = max(1, ancien.count(SE))
    corps = [APPRIS[lg] + SE] + [ENCORE[lg] + SE] * (n - 1)
    return PAGE.join(titre + corps)


def _nomme(ancien, noms, lg):
    """Le message reecrit : le titre (premiere page) puis les noms `noms`
    (octets, balises du jeu), PAR_PAGE par page."""
    pages = ancien.split(PAGE)
    titre = [pages[0]] if len(pages) > 1 else []
    corps = []
    for i in range(0, len(noms), PAR_PAGE):
        tete = NOMME[lg] if i == 0 else NOMME_SUITE[lg]
        corps.append(tete + b"<,> ".join(noms[i:i + PAR_PAGE]) + b"." + SE)
    return PAGE.join(titre + corps)


def _connu(ancien):
    pages = ancien.split(PAGE)
    return PAGE.join([pages[0], pages[-1]]) if len(pages) > 2 else ancien


def _reecrire_membre(d, tirage_fichier, lg, noms=None, bilan=None):
    """`tirage_fichier` : {rang d'instruction: [recettes]} ; `noms` :
    {recette: nom brut du produit, octets} (None : phrase generique) ;
    `bilan` : Counter des messages nommes / generiques. Rend les octets."""
    d = bytearray(d)
    h, cmds = T.lire_script(bytes(d), 0)
    od = h["off_donnees"]
    faits = set()
    # un message partage par des etageres aux tirages differents ne peut
    # nommer les recettes de toutes
    tirages_de = {}
    for k, neuves in tirage_fichier.items():
        tirages_de.setdefault(cmds[k].valeurs[P_APPRIS], set()).add(
            tuple(neuves))

    def appris(s, neuves):
        o = None
        if noms is not None and neuves is not None:
            n = _nomme(s, [noms[r] for r in neuves], lg)
            if len(n) <= len(s):
                o = n
        if bilan is not None:
            bilan["nomme" if o else "generique"] += 1
        return o or _generique(s, lg)

    for k, neuves in tirage_fichier.items():
        c = cmds[k]
        if len(c.valeurs) - P_RECETTES != len(neuves):
            raise AssertionError("etagere %d : %d recettes au lieu de %d"
                                 % (k, len(neuves), len(c.valeurs) - P_RECETTES))
        for off, r in zip(c.offsets[P_RECETTES:], neuves):
            T.ecrire_u32(d, off, r)
        seul = len(tirages_de[c.valeurs[P_APPRIS]]) == 1
        for p, faire in ((P_APPRIS, lambda s, n=(neuves if seul else None):
                          appris(s, n)),
                         (P_CONNU, _connu)):
            o = c.valeurs[p]
            if o in faits or o == 0xFFFFFFFF:
                continue
            faits.add(o)
            deb, fin = _chaine(d, od, o)
            neuf = faire(bytes(d[deb:fin]))
            if len(neuf) > fin - deb:
                raise AssertionError("etagere %d : message plus long (%d > %d)"
                                     % (k, len(neuf), fin - deb))
            d[deb:fin] = neuf + b"\x00" * (fin - deb - len(neuf))
    return bytes(d)


def tirer(rom, rng):
    """{(fichier, rang): [recettes]} : sans remise, dans l'ordre du jeu."""
    eta = etageres(rom)
    n = sum(len(r) for _f, _k, r, _c in eta)
    pool = recettes_de_base(rom)
    if n > len(pool):
        raise SystemExit("bibliotheques : %d emplacements, %d recettes"
                         % (n, len(pool)))
    tir = rng.sample(pool, n)
    out, i = {}, 0
    for ch, k, r, _c in eta:
        out[(ch, k)] = tir[i:i + len(r)]
        i += len(r)
    return out


def patcher(rom, seed, langue="en", journal=None):
    """Tire et pose. Rend le nombre d'emplacements."""
    rng = generateur(seed)
    avant = etageres(rom)
    tirage = tirer(rom, rng)
    import collections
    prod = {r["id"]: r["produit"] for r in recettes.lire(rom)}
    noms = {}
    for lg in LANGUES:
        nm = objets.noms(rom, lg, brut=True)
        noms[lg] = {i: nm[p].encode("latin-1") for i, p in prod.items()}
    bilan = {lg: collections.Counter() for lg in LANGUES}
    for ch in FICHIERS:
        par_rang = {k: v for (c, k), v in tirage.items() if c == ch}
        clairs = {}
        for lg in LANGUES:
            clairs["%s_%s.bin" % (os.path.basename(ch)[:-4], lg)] = \
                _reecrire_membre(_membre(rom, ch, lg), par_rang, lg,
                                 noms[lg], bilan[lg])
        fid = rom.filenames.idOf(ch)
        rom.files[fid] = gp2_ecrire.reecrire(bytes(rom.files[fid]), clairs)
    print("  livres qui nomment leurs recettes : %s" % ", ".join(
        "%s %d/%d" % (lg, b["nomme"], b["nomme"] + b["generique"])
        for lg, b in sorted(bilan.items())))
    if journal is not None:
        nm = objets.noms(rom, langue)
        journal.write("=" * 78 + "\n")
        journal.write("RECETTES DES BIBLIOTHEQUES (ZER-105) : %d emplacements, "
                      "toutes differentes\n" % len(sum(tirage.values(), [])))
        journal.write("=" * 78 + "\n")
        for ch, k, r, _c in avant:
            journal.write("  %s etagere %3d : %s\n      -> %s\n" % (
                os.path.basename(ch), k,
                ", ".join(str(nm.get(prod[i], i)) for i in r),
                ", ".join(str(nm.get(prod[i], i)) for i in tirage[(ch, k)])))
        journal.write("\n")
    return len(sum(tirage.values(), []))


def verifier(rom, vanilla):
    """Memes etageres et memes nombres qu'en vanilla, recettes toutes
    differentes et de base, memes recettes dans les cinq langues, messages
    nommes avec les produits tires, ou generiques. Rend le nombre
    d'emplacements."""
    base = set(recettes_de_base(vanilla))
    prod = {r["id"]: r["produit"] for r in recettes.lire(vanilla)}
    noms = {}
    for lg in LANGUES:
        nm = objets.noms(vanilla, lg, brut=True)
        noms[lg] = {i: nm[p].encode("latin-1") for i, p in prod.items()}
    v = etageres(vanilla)
    ref = None
    for lg in LANGUES:
        e = etageres(rom, lg)
        cles = [(ch, k, len(r)) for ch, k, r, _c in e]
        if cles != [(ch, k, len(r)) for ch, k, r, _c in v]:
            raise AssertionError("bibliotheques (%s) : etageres changees" % lg)
        tout = [i for _ch, _k, r, _c in e for i in r]
        if ref is None:
            ref = tout
        elif tout != ref:
            raise AssertionError("bibliotheques : %s differe de l'allemand" % lg)
        for ch, k, r, c in e:
            if c.valeurs[:P_RECETTES] != dict(
                    ((a, b), x.valeurs[:P_RECETTES])
                    for a, b, _r, x in etageres(vanilla, lg))[(ch, k)]:
                raise AssertionError("%s etagere %d : messages ou drapeaux "
                                     "deplaces" % (ch, k))
    if len(set(ref)) != len(ref):
        raise AssertionError("bibliotheques : une recette en double")
    if set(ref) - base:
        raise AssertionError("bibliotheques : recette hors des recettes de base")
    if ref == [i for _ch, _k, r, _c in v for i in r]:
        raise AssertionError("bibliotheques : rien n'a change")
    for ch in FICHIERS:
        for lg in LANGUES:
            d = _membre(rom, ch, lg)
            h, cmds = T.lire_script(d, 0)
            for c in cmds:
                if c.op != OP_ETAGERE or len(c.valeurs) <= P_RECETTES:
                    continue
                deb, fin = _chaine(d, h["off_donnees"], c.valeurs[P_APPRIS])
                m = d[deb:fin]
                if not m.endswith(SE):
                    raise AssertionError("%s (%s) : message sans <SE_RECIPE>"
                                         % (ch, lg))
                if NOMME[lg] in m:
                    # nomme : exactement les produits tires, dans l'ordre
                    attendus = [noms[lg][r] for r in c.valeurs[P_RECETTES:]]
                    lus = [x for page in m.split(PAGE)
                           if page.endswith(SE) and b"<:> " in page
                           for x in page[:-len(SE) - 1].split(b"<:> ", 1)[1]
                           .split(b"<,> ")]
                    if lus != attendus:
                        raise AssertionError("%s (%s) etagere %d : noms %s, "
                                             "attendus %s" % (ch, lg,
                                                              c.valeurs[0],
                                                              lus, attendus))
                elif APPRIS[lg] not in m:
                    raise AssertionError("%s (%s) : message ni nomme ni "
                                         "generique" % (ch, lg))
    return len(ref)


if __name__ == "__main__":
    import ndspy.rom
    from rom_vanilla import chemin_vanilla
    rom = ndspy.rom.NintendoDSRom.fromFile(
        sys.argv[1] if len(sys.argv) > 1 else chemin_vanilla())
    nm = objets.noms(rom, "fr")
    prod = {r["id"]: r["produit"] for r in recettes.lire(rom)}
    for ch, k, r, c in etageres(rom):
        print("%s %3d (etagere %d) : %s" % (os.path.basename(ch), k,
                                            c.valeurs[0],
                                            ", ".join(str(nm.get(prod[i], i))
                                                      for i in r)))
