#!/usr/bin/env python3
"""Fabrique l'application : un seul .exe Windows, sans rien a installer.

    python scripts/build_exe.py            -> dist/DQIX-Randomizer.exe

POURQUOI UN EXE. Le joueur qui veut randomiser sa partie n'a pas Python, ni
`ndspy`, ni `keystone`, et il n'a pas a les avoir. PyInstaller emballe
l'interpreteur, les modules et les deux bibliotheques natives dans un fichier
qu'on double-clique.

CE QUI EST EMBARQUE, et pourquoi il faut le dire explicitement :

  - `randomizer.py` et TOUS les modules de `scripts/`. La chaine les importe a
    l'execution (`from patch_loot import patcher`), donc l'analyseur statique de
    PyInstaller ne les voit pas : ils vont dans `hiddenimports`, un par un.
  - `keystone` et `capstone`, qui portent chacun une DLL. Les assembler et les
    desassembler sont au coeur des greffes ARM9.
  - `tkinterdnd2`, qui porte le binaire tkdnd du glisser-deposer. Sans lui la
    fenetre marche encore, avec le seul bouton Browse.

CE QUI N'EST PAS EMBARQUE : `xdelta3`. C'est un binaire GPL, l'embarquer
engagerait la licence de ce qu'on distribue, et il ne sert qu'a l'option
« produire aussi un patch ». L'application le cherche a cote d'elle, dans le
PATH, puis dans `tools/xdelta/` ; sans lui, seule cette case est indisponible.

AUCUNE ROM N'EST EMBARQUEE, evidemment : l'application lit celle que le joueur
depose, et la construction ne depend plus de rien d'autre (voir
`scripts/source_rom.py`).
"""
import os
import subprocess
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(RACINE, "scripts")
NOM = "DQIX-Randomizer"


def modules_caches():
    """Les modules que `randomizer` et `interface` atteignent, et eux seuls.

    ON FAIT LE TRI, depuis le 24 septembre. L'ancienne version embarquait tout
    `scripts/` : l'exe distribue au public contenait donc `linear.py` (notre
    outillage Linear) et les outils d'analyse de la branche `local-research`,
    que le joueur a choisi de ne pas publier. Le cout n'etait pas les
    kilo-octets, c'etait la publication.

    La crainte d'origine -- en oublier un, invisible jusqu'a ce qu'un joueur
    coche l'option qui l'utilise -- est levee par construction : on suit les
    `import` du code (y compris ceux ecrits dans le corps des fonctions,
    `from patch_loot import patcher`), recursivement, avec `ast`. Aucun import
    n'est fait par chaine de caracteres (`importlib`, `__import__`) : verifie.
    """
    import ast
    locaux = {f[:-3] for f in os.listdir(SCRIPTS) if f.endswith(".py")}

    def importes(chemin):
        arbre = ast.parse(open(chemin, encoding="utf-8").read())
        out = set()
        for n in ast.walk(arbre):
            if isinstance(n, ast.Import):
                out |= {a.name.split(".")[0] for a in n.names}
            elif isinstance(n, ast.ImportFrom) and n.module:
                out.add(n.module.split(".")[0])
        return out

    vus, pile = set(), ["randomizer", "interface"]
    while pile:
        m = pile.pop()
        if m in vus:
            continue
        vus.add(m)
        chemin = (os.path.join(RACINE, m + ".py") if m in ("randomizer", "interface")
                  else os.path.join(SCRIPTS, m + ".py"))
        pile += [i for i in importes(chemin) if i in locaux and i not in vus]
    return ["randomizer"] + sorted(vus - {"randomizer", "interface"})


def main():
    try:
        import PyInstaller                                  # noqa: F401
    except ImportError:
        raise SystemExit("PyInstaller manque :  python -m pip install --user pyinstaller")

    args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--onefile",
        "--windowed",                  # pas de console derriere la fenetre
        "--name", NOM,
        "--paths", SCRIPTS,
        "--paths", RACINE,
        "--distpath", os.path.join(RACINE, "dist"),
        "--workpath", os.path.join(RACINE, "work", "pyinstaller"),
        "--specpath", os.path.join(RACINE, "work", "pyinstaller"),
        "--collect-all", "tkinterdnd2",
        "--collect-binaries", "keystone",
        "--collect-binaries", "capstone",
    ]
    for m in modules_caches():
        args += ["--hidden-import", m]
    icone = os.path.join(RACINE, "scripts", "data", "randomizer.ico")
    if os.path.isfile(icone):
        args += ["--icon", icone]
    args.append(os.path.join(RACINE, "interface.py"))

    print(" ".join(args))
    r = subprocess.run(args, cwd=RACINE)
    if r.returncode:
        raise SystemExit(r.returncode)
    exe = os.path.join(RACINE, "dist", NOM + ".exe")
    if os.path.isfile(exe):
        print("\necrit : %s  (%.1f Mo)" % (exe, os.path.getsize(exe) / 1e6))


if __name__ == "__main__":
    main()
