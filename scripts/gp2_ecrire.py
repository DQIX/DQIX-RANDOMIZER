#!/usr/bin/env python3
"""Reecrire une archive GPC2 en remplacant le contenu de certains membres.

`gp2.py` sait LIRE une archive ; ce module sait en RENDRE une neuve. Il ne
sert qu'a une chose aujourd'hui : reecrire les prix dans les neuf
`itemdt_<c>.gp2`, dont les membres sont compresses.

CE QUE L'ARCHIVE CONTIENT, et comment on la refait (MESURE sur les neuf
`itemdt_*` et verifie par aller-retour au bit pres) :

    en-tete, 24 octets   magie, nb de membres, header_len, fileinfo_len,
                         first_file, deux longueurs decompressees, total
                         -- les quatre longueurs sont en MOTS de 4 octets
    index                a `header_len * 4`, un bloc de nb x 12 octets
                         (hash, offset, taille). Il est STOCKE EN CLAIR dans
                         les neuf archives d'objets, donc on le corrige sur
                         place sans le recomprimer.
    noms                 a `fileinfo_len * 4`, bloc compresse. On n'y touche
                         pas : il ne bouge pas tant que l'index garde sa
                         taille, et l'index garde sa taille (meme nombre de
                         membres).
    membres              a `first_file * 4 + offset * 4`

CHAMP `taille` DE L'INDEX : c'est la taille du bloc EN-TETE COMPRISE, sans le
bourrage. Le membre suivant commence a `arrondi(taille, 4)` plus loin. Verifie
sur les cinq membres de `itemdt_t.gp2` : 6591 -> 6592, 6471 -> 6472,
6549 -> 6552, 6537 -> 6540, et le dernier tombe pile sur la fin du fichier.
Les octets de poids fort de `offset` et de `taille` portent des drapeaux
d'arbre de recherche : on les preserve.

BLOC : un u32 de controle `type | (taille_decompressee << 3)`, puis les
donnees. Type 0 = brut, type 1 = le LZSS de `lz_dq9.decompresse_a`.

ON REECRIT EN TYPE 1, PAS EN TYPE 0. Le jeu lit bien les deux, mais un membre
d'objets est compresse en vanilla et on ne veut pas parier sur un chemin de
code jamais emprunte pour ce fichier-la. `compresse_a` n'emet que des
litteraux : c'est un flux LZSS valide, simplement plus gros (un octet de
controle pour huit octets de donnees, soit +12,5 %). Ecrire un vrai
compresseur ferait gagner de la place, pas de la surete.

CONSEQUENCE A CONNAITRE : le fichier grossit, donc la disposition de la ROM
change, donc les savestates prises sur une autre construction ne valent plus
(meme piege qu'aux 38, 40, 61 et 82). La sauvegarde de partie, elle, n'est pas
concernee.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gp2

TETE = 24
# en-tete "<IHHHHHHI" : magie, nb, header_len, fileinfo_len, first_file,
# deux longueurs decompressees, puis le total -- a l'offset 16, pas 20.
OFF_TOTAL = 16


MIN_LONGUEUR, MAX_LONGUEUR = 3, 18
MAX_DISTANCE = 4096
CANDIDATS = 64          # positions examinees par prefixe, la plus recente d'abord


def compresse_a(brut):
    """Compresse en LZSS type 1, le format de `lz_dq9.decompresse_a`.

    Un octet de controle porte huit elements, bit de poids fort en premier :
    0 = litteral d'un octet, 1 = couple de deux octets

        ctl = 0x30 + b1        longueur = ctl >> 4        (3 a 18)
        distance = 1 + (((ctl & 0xF) << 8) | b2)          (1 a 4096)

    IL FAUT QUE LE FLUX SOIT PLUS COURT QUE SA SORTIE. Une premiere version
    n'emettait que des litteraux -- flux valide, mais 12,5 % plus GROS que les
    donnees. Resultat en jeu : `ARM9: data abort (02003F18)` des qu'on ouvre la
    liste d'objets. Le jeu decompresse selon toute vraisemblance sur place, et
    un flux plus gros que sa sortie deborde du tampon. Un vrai compresseur rend
    ici 40 a 45 % de la taille d'origine, comme le jeu lui-meme.
    """
    out = bytearray()
    prefixes = {}
    i, n = 0, len(brut)
    jetons, controle, bits = bytearray(), 0, 0
    while i < n:
        meilleure_longueur, meilleure_distance = 0, 0
        cle = bytes(brut[i:i + MIN_LONGUEUR])
        if len(cle) == MIN_LONGUEUR:
            for pos in prefixes.get(cle, ())[-CANDIDATS:][::-1]:
                distance = i - pos
                if distance > MAX_DISTANCE:
                    break
                longueur = 0
                borne = min(MAX_LONGUEUR, n - i)
                while (longueur < borne
                       and brut[pos + longueur] == brut[i + longueur]):
                    longueur += 1
                if longueur > meilleure_longueur:
                    meilleure_longueur, meilleure_distance = longueur, distance
                    if longueur == MAX_LONGUEUR:
                        break

        if meilleure_longueur >= MIN_LONGUEUR:
            ctl = (meilleure_longueur << 4) | ((meilleure_distance - 1) >> 8)
            jetons.append(ctl - 0x30)
            jetons.append((meilleure_distance - 1) & 0xFF)
            controle = (controle << 1) | 1
            avance = meilleure_longueur
        else:
            jetons.append(brut[i])
            controle = (controle << 1)
            avance = 1

        for k in range(i, i + avance):
            if k + MIN_LONGUEUR <= n:
                prefixes.setdefault(bytes(brut[k:k + MIN_LONGUEUR]),
                                    []).append(k)
        i += avance

        bits += 1
        if bits == 8:
            out.append(controle & 0xFF)
            out += jetons
            jetons, controle, bits = bytearray(), 0, 0

    if bits:
        controle <<= (8 - bits)     # les elements manquants restent a zero
        out.append(controle & 0xFF)
        out += jetons
    return bytes(out)


def bloc(brut, typ=1):
    """Un membre complet : u32 de controle puis les donnees."""
    if typ == 0:
        charge = brut
    elif typ == 1:
        charge = compresse_a(brut)
    else:
        raise ValueError("type de bloc non gere a l'ecriture : %d" % typ)
    return struct.pack("<I", typ | (len(brut) << 3)) + charge


def reecrire(d, remplacements):
    """Rend une archive neuve. `remplacements` : {nom de membre: octets clairs}.

    Les membres absents de `remplacements` sont recopies OCTET POUR OCTET,
    bourrage compris : sans remplacement, la fonction rend exactement
    l'archive d'origine, ce que `verifier_aller_retour` controle.
    """
    arc = gp2.GP2("<memoire>", donnees=d)
    ordre = sorted(range(arc.nb), key=lambda i: arc.entrees[i][1] & 0xFFFFFF)
    base = arc.first_file * 4

    # Decoupe d'origine. Un membre non remplace est recopie AVEC son bourrage,
    # c'est-a-dire jusqu'au debut du suivant (jusqu'a la fin du fichier pour le
    # dernier) : c'est ce qui rend l'aller-retour exact.
    tranches = {}
    for rang, i in enumerate(ordre):
        pos = base + (arc.entrees[i][1] & 0xFFFFFF) * 4
        fin = (base + (arc.entrees[ordre[rang + 1]][1] & 0xFFFFFF) * 4
               if rang + 1 < len(ordre) else len(d))
        tranches[i] = (pos, fin, arc.entrees[i][2] & 0xFFFFFF)

    corps = bytearray()
    neuf = {}
    for rang, i in enumerate(ordre):
        nom = arc.noms[rang] if rang < len(arc.noms) else None
        pos, fin, taille = tranches[i]
        depart = len(corps)
        if depart % 4:
            raise AssertionError("membre desaligne")
        if nom in remplacements:
            b = bloc(remplacements[nom])
            corps += b
            corps += b"\x00" * (-len(b) % 4)
            neuf[i] = (depart // 4, len(b))
        else:
            corps += d[pos:fin]
            neuf[i] = (depart // 4, taille)

    out = bytearray(d[:base])
    out += corps

    # l'index, en clair, corrige sur place : on ne touche qu'aux 24 bits bas
    pos_index = arc.header_len * 4 + 4
    for i in range(arc.nb):
        offs_mot, taille = neuf[i]
        h, offs_vieux, _t = arc.entrees[i]
        taille_vieille = struct.unpack_from("<I", d, pos_index + 12 * i + 8)[0]
        struct.pack_into("<I", out, pos_index + 12 * i + 4,
                         (offs_vieux & 0xFF000000) | offs_mot)
        struct.pack_into("<I", out, pos_index + 12 * i + 8,
                         (taille_vieille & 0xFF000000) | taille)

    # le total, en mots, drapeaux preserves
    total = (len(out) - base) // 4
    if (len(out) - base) % 4:
        raise AssertionError("corps non multiple de 4")
    struct.pack_into("<I", out, OFF_TOTAL, (arc.total & 0xF0000000) | total)
    return bytes(out)


def verifier_aller_retour(d):
    """Reecrire sans rien remplacer doit rendre l'archive d'origine."""
    refaite = reecrire(d, {})
    if refaite != d:
        raise AssertionError("aller-retour GP2 : %d octets contre %d, "
                             "premier ecart a %s"
                             % (len(refaite), len(d),
                                next((i for i, (a, b) in
                                      enumerate(zip(refaite, d)) if a != b),
                                     "?")))
    return True


if __name__ == "__main__":
    import ndspy.rom
    import objets
    from rom_vanilla import chemin_vanilla
    rom = ndspy.rom.NintendoDSRom.fromFile(
        sys.argv[1] if len(sys.argv) > 1 else chemin_vanilla())
    for c in objets.CATEGORIES:
        chemin = objets.CHEMIN % c
        d = bytes(rom.files[rom.filenames.idOf(chemin)])
        verifier_aller_retour(d)
        # taille si on reecrivait tous les membres en litteraux
        arc = gp2.GP2(chemin, donnees=d)
        clairs = {n: objets._membre(rom, c, n.split("_")[-1].split(".")[0])
                  for n in arc.noms}
        gros = reecrire(d, clairs)
        print("%-22s aller-retour OK   %7d -> %7d octets (+%d %%)"
              % (chemin.split("/")[-1], len(d), len(gros),
                 round(100 * (len(gros) - len(d)) / len(d))))
