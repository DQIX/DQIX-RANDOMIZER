"""Ajouter un fichier NOMME a un dossier de NitroFS (ZER-116, 30-31/10/2026).

Le jeu ouvre ses fichiers par CHEMIN (`data/scenario/str_ch%d.gp2`,
`data/chara_sub/<modele>.chr`) : le fichier doit donc vivre dans le dossier
ou le jeu le cherche, pas a la fin de l'arborescence (ce que fait
`patch_amorce.ajouter_fichier` pour le blob, qu'on lit par son numero).

L'identifiant d'un fichier est IMPLICITE (ordre des noms) : ajouter un nom en
fin de dossier lui donne le premier numero du dossier suivant, et decale de
un tout ce qui suit. ndspy ne renumerote pas les `firstID` des autres
dossiers : on le fait a la main. Les fichiers sans nom (overlays) sont avant
NitroFS et ne bougent pas ; ceux de fin de table, si la ROM en a, se decalent
avec l'insertion. Verification : `verifier_ajout` relit tout par chemin.
"""


def _dossiers(f):
    yield f
    for _n, s in f.folders:
        yield from _dossiers(s)


def chemins(rom):
    """({chemin: numero}, [numeros sans nom])."""
    out = {}

    def p(f, pre):
        for k, n in enumerate(f.files):
            out[pre + n] = f.firstID + k
        for n, s in f.folders:
            p(s, pre + n + "/")
    p(rom.filenames, "")
    nommes = set(out.values())
    return out, [i for i in range(len(rom.files)) if i not in nommes]


def ajouter(rom, chemin, data):
    """Ajoute `data` sous `chemin` (dossier existant) ; rend son numero."""
    dossier, nom = chemin.rsplit("/", 1)
    sub = rom.filenames[dossier]
    if nom in sub.files:
        raise SystemExit("%s existe deja" % chemin)
    fid = sub.firstID + len(sub.files)
    for f in _dossiers(rom.filenames):
        if f is not sub and f.firstID >= fid:
            f.firstID += 1
    sub.files.append(nom)
    rom.files.insert(fid, data)
    if rom.filenames.idOf(chemin) != fid:
        raise SystemExit("%s : le nom n'a pas pris le numero %d" % (chemin, fid))
    return fid


def verifier_ajout(avant, apres, ajoutes, changes=(), sans_nom_changes=()):
    """Tout fichier de `avant` se relit identique par son chemin dans `apres`,
    sauf `changes` ; les sans-nom aussi (decales des numeros ajoutes) ; chaque
    chemin de `ajoutes` ({chemin: octets}) porte son contenu."""
    ch, sans_nom = chemins(avant)
    for c, i in ch.items():
        if c not in changes and bytes(avant.files[i]) != \
                bytes(apres.files[apres.filenames.idOf(c)]):
            raise AssertionError("fichier change : " + c)
    fids = sorted(apres.filenames.idOf(c) for c in ajoutes)
    for i in sans_nom:
        j = i
        for f in fids:
            if f <= j:
                j += 1
        if i not in sans_nom_changes and bytes(avant.files[i]) != bytes(apres.files[j]):
            raise AssertionError("fichier sans nom %d change" % i)
    for c, d in ajoutes.items():
        if bytes(apres.files[apres.filenames.idOf(c)]) != bytes(d):
            raise AssertionError("contenu de " + c)
    return len(ch), len(sans_nom)
