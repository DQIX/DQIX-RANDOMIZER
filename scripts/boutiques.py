#!/usr/bin/env python3
"""Les boutiques du jeu, lues DANS LA ROM.

OU SONT LES BOUTIQUES. Un seul fichier : `data/bin/menu/shopdata1.bin`
(3776 octets). C'est un script Nitro generique, le meme format que le loot
(voir `treasure.py`) : en-tete de 16 octets, puis des instructions.

    opcode 0x64 / 0x65   horodatage de construction (2008/12/19), souches vides
    opcode 0x66          un entier : 37, le NOMBRE DE BOUTIQUES
    opcode 0x67          UNE BOUTIQUE, 22 parametres entiers

FORMAT d'une boutique (opcode 0x67), 22 parametres -- MESURE :

    p0        identifiant de la boutique. 0 a 30 pour les 31 boutiques du
              groupe ordinaire, 0x20|n (32 a 37) pour les 6 du second groupe.
    p1        inconnu, 1 a 5. Ne suit ni la categorie ni l'ordre du jeu.
    p2..p19   DIX-HUIT emplacements de vente : un identifiant d'objet, ou 0
              pour un emplacement vide. Les objets sont ranges au debut.
    p20       pourcentage de prix : 100 partout, sauf DEUX boutiques a 500.
    p21       categorie de la boutique (voir CATEGORIE ci-dessous), deduite :
              la valeur est constante pour chaque famille d'etal.

CATEGORIE (p21) -- deduite du contenu, les 37 boutiques sont coherentes :

    0  armes           n'y figurent que des armes (itemdt_w)
    1  armures         boucliers, tete, torse, bras, jambes, pieds
    2  objets          objets courants (itemdt_t) et quelques accessoires
    3  general         objets + armes + armures dans le meme etal
    4  armes+armures   les deux, sans objet courant
    5  un seul cas     boutique melangee (objets, armes, tenues d'ecole)

CE QUE LE FICHIER NE DIT PAS : dans quelle ville se trouve chaque boutique.
Aucune table de donnees de la ROM ne porte les deux ; le lieu a ete etabli en
rapprochant les 37 stocks du releve de la communaute (dragonquest-fan.com), 15
correspondances exactes et aucune ambiguite. Voir `docs/research/11-shops.md`
83.5 pour la table complete.

LES PRIX, deux champs dans la fiche d'objet (32 octets, voir `objets.py`) :

    +0x16  u16  PRIX DE VENTE, ce que la boutique paie au joueur
    +0x18  i16  PRIX D'ACHAT : la valeur elle-meme si elle est positive,
                sinon un code -- -1 : 2 x vente (le cas ordinaire, 731 objets)
                                -2 : 2 x vente + 1
                                -3 : 2 x vente - 1
                                -4 : 10 x vente (l'equipement de depart)
    puis le pourcentage de la boutique (p20) multiplie le prix d'achat.

Temoin : les 511 prix du releve qu'on sait rattacher a un objet sont retrouves
par cette regle, 511 sur 511.

Usage :
  python scripts/boutiques.py <rom.nds> [prefixe_de_sortie]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ndspy.rom
import objets
import treasure as T

CHEMIN = "data/bin/menu/shopdata1.bin"
OP_NOMBRE = 0x66
OP_BOUTIQUE = 0x67
NB_PARAMS = 22
NB_SLOTS = 18
I_PRIX, I_CATEGORIE = 20, 21
OFF_VENTE, OFF_ACHAT = 0x16, 0x18   # dans la fiche d'objet, pas ici

CATEGORIE = {0: "weapons", 1: "armour", 2: "items", 3: "general",
             4: "weapons+armour", 5: "mixed"}

# Les comptes que la ROM europeenne doit rendre. Si l'un change, la lecture
# est fausse : on s'arrete plutot que de randomizer a l'aveugle.
NB_BOUTIQUES = 37


def lire(rom):
    """Rend [ {id, inconnu, objets, pct, categorie, offsets} ], une par boutique.

    `offsets` donne la position dans le fichier de chacun des 18 emplacements
    et `off_pct` celle du pourcentage de prix : de quoi reecrire en place, sans
    changer aucune taille.
    """
    fid = rom.filenames.idOf(CHEMIN)
    if fid is None:
        raise ValueError("absent de la ROM : " + CHEMIN)
    d = bytes(rom.files[fid])
    _h, instrs = T.lire_script(d)

    annonce = [i for i in instrs if i.op == OP_NOMBRE]
    boutiques = [i for i in instrs if i.op == OP_BOUTIQUE]
    if len(boutiques) != NB_BOUTIQUES:
        raise ValueError("%d boutiques, %d attendues" % (len(boutiques),
                                                         NB_BOUTIQUES))
    if annonce and annonce[0].valeurs[0] != NB_BOUTIQUES:
        raise ValueError("l'opcode 0x66 annonce %d boutiques"
                         % annonce[0].valeurs[0])

    out = []
    for b in boutiques:
        if len(b.valeurs) != NB_PARAMS:
            raise ValueError("boutique a %d parametres" % len(b.valeurs))
        v = b.valeurs
        out.append(dict(id=v[0], inconnu=v[1], pct=v[I_PRIX],
                        categorie=v[I_CATEGORIE],
                        objets=list(v[2:2 + NB_SLOTS]),
                        offsets=list(b.offsets[2:2 + NB_SLOTS]),
                        off_pct=b.offsets[I_PRIX]))
    return d, out


def _cat_objet(entree):
    """Entree du catalogue -> famille large, pour verifier le type d'un etal.

    `objets.catalogue()` rend {identifiant: (categorie de fichier, drapeaux)}.
    """
    cat = entree[0] if isinstance(entree, tuple) else entree
    return {"w": "weapon", "s": "shield", "b": "torso", "u": "legs",
            "h": "head", "a": "arms", "l": "feet", "d": "accessory",
            "t": "item"}[cat]


def main(chemin, prefixe=None):
    rom = ndspy.rom.NintendoDSRom.fromFile(chemin)
    _d, boutiques = lire(rom)
    cat = objets.catalogue(rom)          # {id: categorie de fichier}
    imp = objets.objets_importants(rom)  # les 88 objets importants
    nen = objets.noms(rom, "en")
    nfr = objets.noms(rom, "fr")
    vente = prix_catalogue(rom)
    achat = prix_achat(rom)

    lignes = []
    vendus = set()
    for k, b in enumerate(boutiques):
        ids = [o for o in b["objets"] if o]
        vendus.update(ids)
        fam = sorted({_cat_objet(cat[o]) for o in ids if o in cat})
        lignes.append((k, b, ids, fam))

    texte = []
    texte.append("Shops of Dragon Quest IX, read from %s" % CHEMIN)
    texte.append("%d shops, %d slots each, %d slots used"
                 % (len(boutiques), NB_SLOTS,
                    sum(len(l[2]) for l in lignes)))
    texte.append("%d distinct items on sale; key items on sale: %d"
                 % (len(vendus), len(vendus & set(imp))))
    texte.append("")
    for k, b, ids, fam in lignes:
        texte.append("shop #%02d  id=%-2d  kind=%-14s  price=%d%%  slots=%d  %s"
                     % (k, b["id"], CATEGORIE.get(b["categorie"], "?"),
                        b["pct"], len(ids), "+".join(fam)))
        for o in ids:
            texte.append("    %-6d %-26s %-28s %7s %7s  %s"
                         % (o, objets.nettoyer(nen.get(o, "?")),
                            nfr.get(o, "?"), vente.get(o, "?"),
                            achat.get(o, 0) * b["pct"] // 100,
                            _cat_objet(cat[o]) if o in cat else "?"))
        texte.append("")
    rapport = "\n".join(texte)

    if prefixe:
        with open(prefixe + "_shops.txt", "w", encoding="utf-8") as f:
            f.write(rapport)
        import csv
        with open(prefixe + "_shops.csv", "w", encoding="utf-8-sig",
                  newline="") as f:
            w = csv.writer(f, delimiter=";", lineterminator="\r\n")
            w.writerow(["shop", "shopID", "kind", "pricePct", "slot",
                        "itemID", "nameEN", "nameFR", "sellPrice", "buyPrice",
                        "category", "keyItem"])
            for k, b, ids, _fam in lignes:
                for s, o in enumerate(ids):
                    w.writerow([k, b["id"], CATEGORIE.get(b["categorie"], "?"),
                                b["pct"], s, o,
                                objets.nettoyer(nen.get(o, "?")),
                                nfr.get(o, "?"), vente.get(o, ""),
                                achat.get(o, 0) * b["pct"] // 100,
                                _cat_objet(cat[o]) if o in cat else "?",
                                "yes" if o in imp else ""])
    else:
        sys.stdout.write(rapport)
    return boutiques


def prix_catalogue(rom):
    """{identifiant: prix de vente} (u16 a +0x16 de la fiche)."""
    return {i: v for i, (v, _a) in _prix(rom).items()}


def prix_achat(rom):
    """{identifiant: prix d'achat en boutique a 100 %}, regle du module __doc__."""
    out = {}
    for i, (vente, champ) in _prix(rom).items():
        if champ >= 0:
            out[i] = champ
        else:
            out[i] = {-1: 2 * vente, -2: 2 * vente + 1,
                      -3: 2 * vente - 1, -4: 10 * vente}.get(champ, 2 * vente)
    return out


def _prix(rom):
    """{identifiant: (vente, champ d'achat brut)} pour tout le catalogue."""
    out = {}
    for c in objets.CATEGORIES:
        d = objets._membre(rom, c, "en")
        n = struct.unpack_from("<H", d, 0)[0] & 0xFFF
        for i in range(n):
            base = objets.TETE + objets.ENREG * i
            ident = struct.unpack_from("<H", d, base + objets.OFF_ID)[0]
            out[ident] = (struct.unpack_from("<H", d, base + OFF_VENTE)[0],
                          struct.unpack_from("<h", d, base + OFF_ACHAT)[0])
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
