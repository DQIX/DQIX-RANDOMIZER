"""Ou trouver la ROM VANILLA, et pourquoi ca compte.

Le pool d'especes, les noms de monstres et les tailles de modeles doivent
toujours etre lus dans la ROM d'ORIGINE, jamais dans celle en cours de patch :
sinon on randomise une randomisation, et le resultat n'est plus reproductible a
partir de la seule graine.

Historiquement la ROM etait attendue a la racine du projet, sous son nom
commercial, et six endroits du code portaient ce nom en dur. Un `glob(...)[0]`
rendait alors un `IndexError` nu quand elle n'y etait pas. Elle vit desormais
dans `banc/roms/dq9_vanilla.nds` ; ce module regle la question une seule fois.

Ordre de recherche : la variable `DQ9_VANILLA`, puis `banc/roms/dq9_vanilla.nds`,
puis la racine du projet (ancienne convention, toujours acceptee). Les chemins
relatifs sont resolus depuis le repertoire courant ET depuis la racine du projet,
pour qu'une sonde lancee d'ailleurs fonctionne quand meme.
"""
import glob
import os

NOM_COMMERCIAL = ("Dragon Quest IX - Sentinels of the Starry Skies "
                  "(Europe) (En,Fr,De,Es,It).nds")
MD5_ATTENDU = "3a63438fff7db282fa3133e8fd020e85"

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _candidats():
    env = os.environ.get("DQ9_VANILLA", "")
    if env:
        yield env
    for base in (".", RACINE):
        yield os.path.join(base, "banc", "roms", "dq9_vanilla.nds")
        yield os.path.join(base, NOM_COMMERCIAL)
        for t in sorted(glob.glob(os.path.join(base, "Dragon Quest IX*.nds"))):
            yield t


def chemin_vanilla():
    """Rend le chemin de la ROM vanilla, ou s'arrete avec un message utile."""
    for c in _candidats():
        if c and os.path.isfile(c):
            return c
    raise SystemExit(
        "ROM vanilla introuvable.\n"
        "  Attendue dans banc/roms/dq9_vanilla.nds,\n"
        "  ou designee par la variable d'environnement DQ9_VANILLA.\n"
        f"  MD5 de la version supportee (Europe) : {MD5_ATTENDU}\n"
        "  Elle doit rester INTACTE : le pool d'especes en est lu.")


def verifier_vanilla(chemin=None):
    """Controle l'empreinte. Rend (chemin, md5, conforme)."""
    import hashlib
    chemin = chemin or chemin_vanilla()
    h = hashlib.md5()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    md5 = h.hexdigest()
    return chemin, md5, md5 == MD5_ATTENDU


if __name__ == "__main__":
    c, md5, ok = verifier_vanilla()
    print(f"vanilla : {c}")
    print(f"md5     : {md5}  {'conforme' if ok else 'NON CONFORME'}")
