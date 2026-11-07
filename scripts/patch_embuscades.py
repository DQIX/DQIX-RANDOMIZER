#!/usr/bin/env python3
"""Les COFFRES-EMBUSCADES (ZER-108, 1.8).

La greffe vit dans le blob (`patch_blob`, `greffe_embuscade`) : un coffre qui
libere un monstre essaie l'espece du coffre (38-40) puis un monstre tire au
hasard, ou l'inverse avec `--embuscades-tout-monstre`. Ce module en porte la
partie DONNEES, qui ne va qu'avec l'option :

  * LE MESSAGE. « Oh non ! Ce coffre au tresor etait en fait <str_1> ! »
    (`data/bin/strstd.gp2`, message 42 des cinq langues) : le jeu met dans
    <str_1> le nom de l'espece DU COFFRE, donc « une canniboite » meme quand
    un autre monstre surgit. Il devient « ... un monstre ! ».
  * LES LIGNES D'EMBUSCADE sont ajoutees par `patch_loot` (`embuscades=True`,
    avec les objets) : tout rang de coffre bleu ou de grotto qui n'en avait
    pas en recoit une a 5 %, espece 38 (la greffe tire le monstre).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gp2_ecrire
import objets
import textes_dq9

STRSTD = "data/bin/strstd.gp2"
MESSAGE = 42
GENERIQUE = {
    "fr": b"Oh non<!> Ce coffre au tr<'e>sor <'e>tait en fait un monstre<!>",
    "en": b"Oh no! The chest was really a monster!",
    "de": b"Oh nein! Die Schatztruhe war in Wirklichkeit ein Monster!",
    "es": b"<^!>Oh<,> no! En realidad el cofre era un monstruo.",
    "it": b"Oh<,> no!\\nLo scrigno <`e> un mostro!",
}
ANCIEN = b"<str_1>"


def patcher(rom):
    """Rend le message des coffres-embuscades generique, cinq langues."""
    fid = rom.filenames.idOf(STRSTD)
    neufs = {}
    for lg, texte in GENERIQUE.items():
        nom = "strstd_%s.nat" % lg
        m = objets._membre_archive(rom, STRSTD, nom)
        if ANCIEN not in textes_dq9.messages(m)[MESSAGE]:
            raise SystemExit("%s : message %d inattendu" % (nom, MESSAGE))
        neufs[nom] = textes_dq9.remplacer_message(m, MESSAGE, texte)
    rom.files[fid] = gp2_ecrire.reecrire(bytes(rom.files[fid]), neufs)
    return len(neufs)


def verifier(rom):
    for lg, texte in GENERIQUE.items():
        m = objets._membre_archive(rom, STRSTD, "strstd_%s.nat" % lg)
        if textes_dq9.messages(m)[MESSAGE] != texte:
            raise AssertionError("strstd_%s : message %d non generique"
                                 % (lg, MESSAGE))
