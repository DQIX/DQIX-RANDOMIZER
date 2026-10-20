#!/usr/bin/env python3
"""Fenetre du randomizer : deposer la ROM, cocher, construire.

POURQUOI. Jusqu'ici le livrable public etait un `.xdelta` a graine fixe, qu'il
fallait appliquer soi-meme avec `xdelta3` en ligne de commande. Un joueur qui
n'est pas developpeur s'arrete la. Cette fenetre remplace tout : on depose la
ROM, on choisit ce qu'on randomise, on obtient une ROM jouable.

CE QU'ELLE N'EST PAS. Elle ne refait aucun travail : elle construit la ligne de
commande de `randomizer.py` et appelle son `main()` dans un fil, en detournant
sa sortie standard vers le journal de la fenetre. Une seule implementation, donc
une seule chose a maintenir -- et la ligne de commande reste affichee, pour
qu'un rapport de bug soit reproductible.

LA ROM NE QUITTE JAMAIS LA MACHINE. Aucun reseau, aucun envoi, rien d'ecrit
ailleurs que dans le dossier choisi par le joueur (et le choix de langue, dans
le dossier de configuration de l'utilisateur).

CINQ LANGUES (ZER-48), celles de la ROM, changeables a chaud par le menu en
haut a droite. Tous les textes viennent de `scripts/langues_interface.py` ;
aucun texte affiche n'est ecrit en dur ici. La langue choisie regle aussi
`--langue` (les noms du journal de construction).
"""
import json
import os
import queue
import random
import sys
import threading
import traceback

RACINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(RACINE, "scripts"))

import tkinter as tk
from tkinter import filedialog, font as tkfont, messagebox, ttk

import langues_interface as L

# LE GLISSER-DEPOSER EST UN BONUS, PAS UNE DEPENDANCE. `tkinterdnd2` fournit le
# binaire tkdnd ; s'il manque, la fenetre s'ouvre quand meme et le bouton
# Browse fait le meme travail. Un joueur qui depose la ROM sur l'icone de
# l'application passe, lui, par `sys.argv`.
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except Exception:                                    # pragma: no cover
    DND_FILES, TkinterDnD = None, None

MD5_ATTENDU = "3a63438fff7db282fa3133e8fd020e85"
TITRE = "DQIX Randomizer"

# CE QUE LA 1.3 PUBLIEE PORTE, mot pour mot. Ces cinq options ne sont pas des
# reglages : ce sont les greffes de code qui font apparaitre n'importe quelle
# espece (portier universel, blob relogeable, place dans le tas des modeles).
# Elles accompagnent toujours la randomisation des monstres.
GREFFES_MONSTRES = ["--sans-rotation", "--place", "--blob",
                    "--plafond", "1", "--garde", "163840"]

# OU LE CHOIX DE LANGUE EST GARDE, d'une ouverture a l'autre. Un petit fichier
# dans le dossier de configuration de l'utilisateur, rien d'autre.
# DQIX_RANDOMIZER_LANGUE l'emporte sur tout : la matrice s'en sert pour que
# l'essai d'interface ne depende pas de la langue de Windows.
VAR_LANGUE = "DQIX_RANDOMIZER_LANGUE"


def _fichier_reglages():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "DQIX-Randomizer", "interface.json")


def langue_initiale():
    force = os.environ.get(VAR_LANGUE)
    if force in L.CODES:
        return force
    try:
        with open(_fichier_reglages(), encoding="utf-8") as f:
            lu = json.load(f).get("langue")
        if lu in L.CODES:
            return lu
    except Exception:
        pass
    return L.langue_systeme()


def lire_reglage(cle):
    try:
        with open(_fichier_reglages(), encoding="utf-8") as f:
            return json.load(f).get(cle)
    except Exception:
        return None


def memoriser(cle, valeur):
    """Un reglage de plus dans le fichier, les autres gardes."""
    try:
        chemin = _fichier_reglages()
        try:
            with open(chemin, encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            d = {}
        d[cle] = valeur
        os.makedirs(os.path.dirname(chemin), exist_ok=True)
        with open(chemin, "w", encoding="utf-8") as f:
            json.dump(d, f)
    except Exception:
        pass                    # un choix non memorise n'empeche rien


def memoriser_langue(code):
    memoriser("langue", code)


def empreinte(chemin, progres=None):
    """MD5 du fichier, par blocs de 1 Mo. 256 Mo prennent environ une seconde."""
    import hashlib
    h = hashlib.md5()
    taille = os.path.getsize(chemin) or 1
    lu = 0
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
            lu += len(bloc)
            if progres is not None:
                progres(lu * 100 // taille)
    return h.hexdigest()


class Sortie(object):
    """Detourne `print` vers une file, que la fenetre vide dans son journal.

    Tk n'est pilotable que depuis le fil principal : le fil de construction ne
    touche donc a aucun widget, il ne fait que deposer des lignes ici.
    """

    def __init__(self, file):
        self.file = file
        self.reste = ""

    def write(self, texte):
        self.reste += texte
        while "\n" in self.reste:
            ligne, self.reste = self.reste.split("\n", 1)
            self.file.put(("log", ligne))
        return len(texte)

    def flush(self):
        if self.reste:
            self.file.put(("log", self.reste))
            self.reste = ""


# L'OPTION MERE DE CHAQUE SOUS-OPTION : celle sans laquelle `arguments` ne la
# passe pas. Les sous-options des vocations n'en ont pas (independantes).
MERES = {"groupes": "monstres", "app_aleatoire": "monstres",
         "app_zone": "monstres", "app_globale": "monstres",
         "sorts_monstres_ajout": "sorts_monstres",
         "techniques_monstres_ajout": "techniques_monstres",
         # le kit fixe vaut pour les deux : mere = sorts OU techniques
         "actions_fixes": "sorts_monstres",
         "garder_hexacorne": "boss", "boss_familles_egales": "boss",
         "boss_histoire": "boss", "boss_mixte": "boss",
         "boss_legacy_tous": "boss",
         "seuil_grottes": "boss", "seuil_legendes": "boss",
         "boss_chaque_combat": "boss", "boss_terrain": "monstres",
         "equilibrer_conso": "objets", "objets_chaos": "objets",
         "rouges_libres": "objets", "butin_libre": "butin",
         "prix_libres": "boutiques", "boutiques_chaos": "boutiques",
         "sorts_chaos": "sorts", "aptitudes_chaos": "aptitudes",
         "aptitudes_arme_origine": "aptitudes",
         "medailles_chaos": "medailles",
         "medailles_seuils_vanilla": "medailles",
         "stats_chaos": "stats", "stats_combat": "stats",
         "stats_boss_chaos": "stats_boss", "stats_boss_combat": "stats_boss",
         "points_par_rang": "points"}


class Application(object):

    def __init__(self, racine):
        self.racine = racine
        self.file = queue.Queue()
        self.rom = None
        self.rom_conforme = False
        self.en_cours = False
        self.langue = langue_initiale()
        # CE QUE CHAQUE WIDGET AFFICHE, en cle de traduction : changer de
        # langue, c'est reposer chaque texte depuis ce registre. Un texte qui
        # n'est pas traduisible (le nom du fichier depose) y est range tel quel.
        self._textes = {}

        racine.title(TITRE)
        racine.minsize(560, 560)
        self._construire()
        # LE PREREGLAGE AFFICHE DOIT ETRE LE PREREGLAGE APPLIQUE. Sans cet appel,
        # la fenetre s'ouvrait sur « Balanced » avec les sorts et les arbres
        # decoches : un joueur qui cliquait directement sur Randomize n'avait
        # pas ce que l'ecran annoncait (vu sur une capture, 24 septembre).
        self.appliquer_prereglage()
        racine.after(100, self._vider_file)

    # ----------------------------------------------------------- les langues

    def _t(self, cle, *args):
        return L.texte(cle, self.langue, *args)

    def _poser(self, widget, cle=None, *args, brut=None, partie=None, **cfg):
        """Pose un texte sur un widget et s'en souvient. `partie` : 0 ou 1 pour
        prendre le libelle ou le detail d'une case ; `brut` : un texte a
        afficher tel quel ; les autres arguments nommes vont au widget."""
        self._textes[widget] = (cle, args, brut, partie)
        widget.configure(text=self._rendre(cle, args, brut, partie), **cfg)

    def _rendre(self, cle, args, brut, partie):
        if brut is not None:
            return brut
        t = self._t(cle, *args) if partie is None else L.texte(cle, self.langue)[partie]
        return ("  " + t) if partie == 1 else t

    def changer_langue(self, code, memoriser=True):
        """Retraduit toute la fenetre, sur place. `memoriser` : garder le choix
        pour la prochaine ouverture."""
        if code not in L.CODES:
            return
        self.langue = code
        for widget, (cle, args, brut, partie) in self._textes.items():
            try:
                widget.configure(text=self._rendre(cle, args, brut, partie))
            except tk.TclError:
                pass
        self.choix_langue.set(dict(L.LANGUES)[code])
        for menu, variable in getattr(self, "_listes", ()):
            self._remplir_liste(menu, variable)
        for onglets, page, titre in getattr(self, "_onglets", ()):
            onglets.tab(page, text=self._t(titre))
        if getattr(self, "creer", None) is not None:
            self.creer.retraduire()
        if memoriser:
            memoriser_langue(code)

    # LES SEUILS DE BOSS (ZER-80) : une liste deroulante, « le debut », les
    # 30 boss d'histoire numerotes dans l'ordre du scenario, « jamais ».
    def _choix_seuil(self):
        import categories_boss as CB
        noms = L.NOMS_BOSS_HISTOIRE[self.langue]
        return ([(CB.DEBUT, self._t("seuil_debut"))]
                + [(str(e), "%d. %s" % (k + 1, noms[k]))
                   for k, e in enumerate(CB.ORDRE_HISTOIRE)]
                + [(CB.JAMAIS, self._t("seuil_jamais"))])

    def _remplir_liste(self, menu, variable):
        choix = self._choix_seuil()
        menu.configure(values=[t for _v, t in choix])
        menu.set(dict(choix).get(variable.get(), choix[0][1]))

    def _liste(self, page, cle, variable, retrait):
        ligne = ttk.Frame(page)
        ligne.pack(fill="x", anchor="w", padx=(22 * retrait, 0))
        t = ttk.Label(ligne)
        t.pack(side="left")
        self._poser(t, cle, partie=0)
        menu = ttk.Combobox(ligne, state="readonly", width=30)
        menu.pack(side="left", padx=(6, 0))

        def choisi(_evenement=None):
            texte = menu.get()
            for v, txt in self._choix_seuil():
                if txt == texte:
                    variable.set(v)
            self.choix_manuel()
        menu.bind("<<ComboboxSelected>>", choisi)
        self._listes.append((menu, variable))
        self._remplir_liste(menu, variable)
        # le detail est long : il passe a la ligne au lieu d'elargir la fenetre
        d = ttk.Label(ligne, foreground="#666", wraplength=380,
                      justify="left")
        d.pack(side="left")
        self._poser(d, cle, partie=1)
        return menu

    def _case(self, page, cle, variable, retrait, valeur=None):
        """Une ligne : la case (ou le bouton radio si `valeur`), son libelle
        et son detail. Rend le widget cliquable."""
        ligne = ttk.Frame(page)
        ligne.pack(fill="x", anchor="w", padx=(22 * retrait, 0))
        if valeur is None:
            c = ttk.Checkbutton(ligne, variable=variable,
                                command=self.choix_manuel)
        else:
            c = ttk.Radiobutton(ligne, variable=variable, value=valeur,
                                command=self.choix_manuel)
        c.pack(side="left")
        self._poser(c, cle, partie=0)
        d = ttk.Label(ligne, foreground="#666")
        d.pack(side="left")
        self._poser(d, cle, partie=1)
        return c

    def _etat_cases_blob(self):
        """Griser ce qui ne compterait pas dans la ligne de commande : une
        sous-option dont l'option mere est decochee, les options du blob hors
        du mode aleatoire, << familles egales >> avec << histoire seulement >>
        (une seule famille reste : elle n'y changerait rien). Une case grisee
        garde sa coche ; `arguments` l'ignore."""
        aleatoire = (self.monstres.get()
                     and self.apparitions.get() == "aleatoire")
        for c in getattr(self, "_cases_blob", ()):
            c.configure(state="normal" if aleatoire else "disabled")
        for cle, c in getattr(self, "_cases_filles", ()):
            actif = getattr(self, MERES[cle]).get()
            if cle == "actions_fixes":
                actif = (self.sorts_monstres.get()
                         or self.techniques_monstres.get())
            if (cle in ("boss_familles_egales", "boss_legacy_tous",
                        "seuil_grottes", "seuil_legendes")
                    and self.boss_histoire.get()):
                actif = False
            if isinstance(c, ttk.Combobox):
                c.configure(state="readonly" if actif else "disabled")
                continue
            # les coffres rouges sont deja libres quand les rangs sont ignores
            if cle == "rouges_libres" and self.objets_chaos.get():
                actif = False
            if c not in self._cases_blob or not actif:
                c.configure(state="normal" if actif else "disabled")

    def _langue_choisie(self, _evenement=None):
        nom = self.choix_langue.get()
        code = next((c for c, n in L.LANGUES if n == nom), None)
        if code and code != self.langue:
            self.changer_langue(code)

    # ------------------------------------------------------------------ vue

    def _construire(self):
        cadre = ttk.Frame(self.racine, padding=14)
        cadre.pack(fill="both", expand=True)
        cadre.columnconfigure(0, weight=1)

        # --- la langue ----------------------------------------------------
        haut = ttk.Frame(cadre)
        haut.grid(row=0, column=0, sticky="ew")
        self.choix_langue = tk.StringVar(value=dict(L.LANGUES)[self.langue])
        menu = ttk.Combobox(haut, textvariable=self.choix_langue, state="readonly",
                            width=10, values=[n for _c, n in L.LANGUES])
        menu.pack(side="right")
        menu.bind("<<ComboboxSelected>>", self._langue_choisie)
        etiquette = ttk.Label(haut)
        etiquette.pack(side="right", padx=6)
        self._poser(etiquette, "langue")

        # --- la ROM -------------------------------------------------------
        self.zone = tk.Label(
            cadre, height=4, relief="ridge", borderwidth=2,
            fg="#444", cursor="hand2")
        self._poser(self.zone, "zone_vide")
        self.zone.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        self.zone.bind("<Button-1>", lambda _e: self.choisir_rom())
        if DND_FILES is not None:
            self.zone.drop_target_register(DND_FILES)
            self.zone.dnd_bind("<<Drop>>", self._depose)

        barre = ttk.Frame(cadre)
        barre.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        b = ttk.Button(barre, command=self.choisir_rom)
        b.pack(side="left")
        self._poser(b, "parcourir")
        # MODIFIER UNE ROM D'UNE PARTIE EN COURS (joueur, 20/10/2026)
        b = ttk.Button(barre, command=self.modifier_rom)
        b.pack(side="right")
        self._poser(b, "modifier_rom")
        self.a_modifier = None
        # une ROM randomisee glissee avant sa ROM d'origine (verifiee apres)
        self._modif_attente = None
        self.etat_rom = ttk.Label(barre)
        self.etat_rom.pack(side="left", padx=10)
        self._poser(self.etat_rom, "rom_europe")

        # --- la graine ----------------------------------------------------
        g = ttk.Frame(cadre)
        g.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        e = ttk.Label(g)
        e.pack(side="left")
        self._poser(e, "graine")
        self.graine = tk.StringVar(value=str(random.randrange(1, 10 ** 6)))
        ttk.Entry(g, textvariable=self.graine, width=12).pack(side="left", padx=6)
        b = ttk.Button(g, command=self.nouvelle_graine)
        b.pack(side="left")
        self._poser(b, "hasard")
        e = ttk.Label(g)
        e.pack(side="left")
        self._poser(e, "meme_graine")

        # --- le prereglage -------------------------------------------------
        # DEUX FACONS DE JOUER, et le joueur ne devrait pas avoir a lire une
        # documentation pour choisir : "Balanced" garde les bornes (les objets
        # rares viennent des endroits rares, un armurier vend des armes), "Total
        # chaos" les enleve toutes. PAS DE NUMERO DE VERSION dans la fenetre :
        # demande du joueur, 24 septembre -- l'utilisateur n'a pas a savoir ce
        # que faisait telle version.
        p = ttk.Frame(cadre)
        p.grid(row=4, column=0, sticky="ew", pady=(14, 0))
        self.prereglage = tk.StringVar(value="balanced")
        e = ttk.Label(p)
        e.pack(side="left")
        self._poser(e, "prereglage")
        for valeur in ("balanced", "chaos", "custom"):
            r = ttk.Radiobutton(p, value=valeur, variable=self.prereglage,
                                command=self.appliquer_prereglage)
            r.pack(side="left", padx=6)
            self._poser(r, valeur)
        aide = ttk.Label(cadre, foreground="#666", wraplength=700)
        aide.grid(row=5, column=0, sticky="w")
        self._poser(aide, "prereglage_aide")

        # LES ONGLETS (ZER-64) : les cases rangees par sujet. Le titre d'un
        # onglet ne passe pas par `configure`, d'ou leur registre a part.
        # DES ONGLETS QUI SE VOIENT (ZER-82) : le titre en gras, deux points
        # au-dessus de la police de la fenetre, et plus d'air autour.
        base = tkfont.nametofont("TkDefaultFont").actual()
        ttk.Style(self.racine).configure(
            "TNotebook.Tab", padding=(12, 4),
            font=(base["family"], abs(base["size"]) + 2, "bold"))
        onglets = ttk.Notebook(cadre)
        onglets.grid(row=6, column=0, sticky="ew", pady=(8, 0))
        self._onglets = []
        self.monstres = tk.BooleanVar(value=True)
        self.objets = tk.BooleanVar(value=True)
        # 1.7 (joueur, 14/10/2026) : rarete libre et tirage brut par defaut ;
        # l'equilibre equipement / consommables devient une case a cocher.
        self.equilibrer_conso = tk.BooleanVar(value=False)
        self.objets_chaos = tk.BooleanVar(value=True)
        self.rouges_libres = tk.BooleanVar(value=False)
        self.boutiques = tk.BooleanVar(value=True)
        self.prix_libres = tk.BooleanVar(value=False)
        self.boutiques_chaos = tk.BooleanVar(value=False)
        # L'ALCHIMIE (ZER-53) : dans les deux prereglages depuis sa validation
        # en jeu (joueur, 14/10/2026).
        self.alchimie = tk.BooleanVar(value=False)
        # LE CAPITAINE ZAC AMEDAI (ZER-55) : dans les deux prereglages depuis
        # sa validation en jeu (joueur, 15/10/2026) ; le chaos leve la bande
        # d'etoiles.
        self.medailles = tk.BooleanVar(value=False)
        self.medailles_chaos = tk.BooleanVar(value=False)
        self.medailles_seuils_vanilla = tk.BooleanVar(value=False)
        self.boss = tk.BooleanVar(value=False)
        # COCHEE PAR DEFAUT, et c'est voulu : hexacorne est le seul boss qu'on
        # affronte sans equipe, et n'importe quel autre a sa place peut rendre
        # la partie infaisable des le premier combat de scenario. Qui veut le
        # risque decoche.
        self.garder_hexacorne = tk.BooleanVar(value=True)
        # LES VOCATIONS (ZER-36, ZER-47), prouvees en jeu le 25 septembre.
        self.vocations = tk.BooleanVar(value=False)
        self.vocations_embauche = tk.BooleanVar(value=False)
        self.vocation_depart = tk.BooleanVar(value=False)
        # VOCATIONS BLOQUEES : une regle de defi, dans AUCUN prereglage.
        self.vocations_bloquees = tk.BooleanVar(value=False)
        # LE BUTIN TIRE A CHAQUE COMBAT (ZER-39), deux versions comme toute
        # regle d'equilibrage : 4-5 etoiles rares, ou tout objet a egalite.
        self.butin = tk.BooleanVar(value=False)
        self.butin_libre = tk.BooleanVar(value=False)
        # LES SORTS DES MONSTRES tires a chaque combat (ZER-56) : remplacer
        # ceux qu'ils ont, ou en donner aussi a ceux qui n'en ont pas.
        self.sorts_monstres = tk.BooleanVar(value=False)
        self.sorts_monstres_ajout = tk.BooleanVar(value=False)
        # ET LEURS TECHNIQUES (ZER-57), memes deux versions.
        self.techniques_monstres = tk.BooleanVar(value=False)
        self.techniques_monstres_ajout = tk.BooleanVar(value=False)
        self.actions_fixes = tk.BooleanVar(value=False)
        self.sorts = tk.BooleanVar(value=False)
        self.sorts_chaos = tk.BooleanVar(value=False)
        self.aptitudes = tk.BooleanVar(value=False)
        self.aptitudes_chaos = tk.BooleanVar(value=False)
        self.stats = tk.BooleanVar(value=False)
        self.stats_chaos = tk.BooleanVar(value=False)
        self.stats_combat = tk.BooleanVar(value=False)
        # LES BOSS A PART, dans l'onglet Boss (joueur, 20/10/2026)
        self.stats_boss = tk.BooleanVar(value=False)
        self.stats_boss_chaos = tk.BooleanVar(value=False)
        self.stats_boss_combat = tk.BooleanVar(value=False)
        self.points = tk.BooleanVar(value=False)
        self.points_par_rang = tk.BooleanVar(value=False)
        # LA 1.6. Le mode d'apparition (ZER-73) est un choix exclusif, pas une
        # case : trois boutons sous « Monstres du terrain ». Les groupes
        # (ZER-67) sont un correctif, coches par defaut ; le reste est en
        # option, decoche.
        self.apparitions = tk.StringVar(value="aleatoire")
        self.groupes = tk.BooleanVar(value=True)
        self.boss_familles_egales = tk.BooleanVar(value=False)
        self.boss_histoire = tk.BooleanVar(value=False)
        # LES TROIS NIVEAUX DES LEGENDES (ZER-76) : par defaut, le premier
        # seulement ; la case rend le tirage d'avant la 1.7.
        self.boss_legacy_tous = tk.BooleanVar(value=False)
        # A PARTIR DE QUEL BOSS (ZER-80) : "debut", "jamais" ou l'espece
        # d'un boss d'histoire, en texte.
        self.seuil_grottes = tk.StringVar(value="debut")
        self.seuil_legendes = tk.StringVar(value="debut")
        self._listes = []
        self.boss_mixte = tk.BooleanVar(value=False)
        self.boss_chaque_combat = tk.BooleanVar(value=False)
        # LES BOSS SUR LE TERRAIN (ZER-63) : dans la fenetre depuis le
        # 11/10/2026, a la demande du joueur, decoches et hors des prereglages.
        self.boss_terrain = tk.BooleanVar(value=False)
        self.aptitudes_arme_origine = tk.BooleanVar(value=False)
        self._applique = False
        # L'ORDRE ET LES TEXTES DES CASES viennent de `langues_interface` ;
        # la cle d'une case est le nom de sa variable ici. Les options qui
        # vivent dans le blob ne valent que pour le mode aleatoire : elles se
        # grisent dans les deux autres.
        self._cases_blob = []
        self._cases_filles = []
        for titre, cases in L.ONGLETS:
            page = ttk.Frame(onglets, padding=10)
            onglets.add(page, text=self._t(titre))
            self._onglets.append((onglets, page, titre))
            for cle, retrait in cases:
                if cle in L.LISTES:
                    c = self._liste(page, cle, getattr(self, cle), retrait)
                else:
                    c = self._case(page, cle, getattr(self, cle), retrait)
                if cle in ("groupes", "boss_chaque_combat", "boss_terrain"):
                    self._cases_blob.append(c)
                if cle in MERES:
                    self._cases_filles.append((cle, c))
                if cle == "monstres":
                    for mode in L.APPARITIONS:
                        r = self._case(page, "app_" + mode, self.apparitions,
                                       1, valeur=mode)
                        self._cases_filles.append(("app_" + mode, r))
        self._etat_cases_blob()
        # « CREER SA ROM » (ZER-86) : l'affectation explicite, dans son module.
        from onglet_creer import OngletCreer
        self.creer = OngletCreer(self, onglets, Sortie)
        # LE BOUTON SUIT L'ONGLET (joueur, 20/10/2026) : depuis « Creer sa
        # ROM », la ROM personnalisee (sa config seule) ; depuis les autres
        # onglets, les options seules. Les deux ne se melangent jamais.
        self.notebook = onglets
        onglets.bind("<<NotebookTabChanged>>",
                     lambda _e: self._libelle_bouton())

        # --- sortie --------------------------------------------------------
        s = ttk.LabelFrame(cadre, padding=10)
        self._poser(s, "sortie")
        s.grid(row=7, column=0, sticky="ew", pady=(12, 0))
        self.patch = tk.BooleanVar(value=False)
        # ON NE PROPOSE PAS CE QU'ON NE SAIT PAS FAIRE. `xdelta3` n'est pas
        # embarque (binaire GPL) : sans lui, la case echouerait apres vingt-cinq
        # secondes de construction. On la desactive d'emblee, en disant
        # pourquoi. La recherche se fait dans un fil, pour ne pas retarder
        # l'ouverture de la fenetre -- elle importe `randomizer`.
        self.case_patch = ttk.Checkbutton(s, variable=self.patch,
                                          state="disabled")
        self._poser(self.case_patch, "case_patch")
        self.case_patch.pack(anchor="w")
        self.etat_patch = ttk.Label(s, foreground="#666")
        self._poser(self.etat_patch, "xdelta_cherche")
        self.etat_patch.pack(anchor="w")
        threading.Thread(target=self._chercher_xdelta, daemon=True).start()
        self.dossier = ttk.Label(s, foreground="#666", wraplength=700)
        self._poser(self.dossier, "dossier_defaut")
        self.dossier.pack(anchor="w")

        # --- action --------------------------------------------------------
        a = ttk.Frame(cadre)
        a.grid(row=8, column=0, sticky="ew", pady=(14, 0))
        self.bouton = ttk.Button(a, command=self.lancer, state="disabled")
        self._poser(self.bouton, "lancer")
        self.bouton.pack(side="left")
        self.progres = ttk.Progressbar(a, mode="determinate", length=260)
        self.progres.pack(side="left", padx=12)

        self.journal = tk.Text(cadre, height=5, wrap="none", state="disabled",
                               font=("Consolas", 9))
        self.journal.grid(row=9, column=0, sticky="nsew", pady=(12, 0))
        cadre.rowconfigure(9, weight=1)
        ascenseur = ttk.Scrollbar(cadre, command=self.journal.yview)
        ascenseur.grid(row=9, column=1, sticky="ns", pady=(12, 0))
        self.journal.configure(yscrollcommand=ascenseur.set)

    # ----------------------------------------------------------- la ROM

    def _chercher_xdelta(self):
        """Tourne dans un fil : `randomizer` tire ndspy et keystone avec lui."""
        try:
            import randomizer
            self.file.put(("xdelta", randomizer.trouver_xdelta3()))
        except Exception:
            self.file.put(("xdelta", None))

    def _depose(self, evenement):
        # tkdnd rend une liste style Tcl : un chemin avec espaces vient entre
        # accolades, et plusieurs fichiers sont separes par des espaces.
        chemins = self.racine.tk.splitlist(evenement.data)
        if chemins:
            self.adopter(chemins[0])

    def choisir_rom(self):
        c = filedialog.askopenfilename(
            title=self._t("choisir_titre"),
            filetypes=[(self._t("type_rom"), "*.nds"),
                       (self._t("type_tout"), "*.*")])
        if c:
            self.adopter(c)

    def adopter(self, chemin):
        if self.en_cours:
            return
        if not os.path.isfile(chemin) or not chemin.lower().endswith(".nds"):
            self._refuser(chemin, "pas_nds")
            return
        self.rom = chemin
        self.rom_conforme = False
        self.a_modifier = None
        self.bouton.configure(state="disabled")
        self._poser(self.zone, brut=os.path.basename(chemin), fg="#444")
        self._poser(self.etat_rom, "verification", foreground="")
        threading.Thread(target=self._verifier, args=(chemin,),
                         daemon=True).start()

    def _verifier(self, chemin):
        try:
            md5 = empreinte(chemin, lambda p: self.file.put(("progres", p)))
        except OSError as e:
            self.file.put(("rom", (chemin, None, str(e))))
            return
        self.file.put(("rom", (chemin, md5, None)))

    def _refuser(self, chemin, cle, *args):
        self.rom, self.rom_conforme = None, False
        self.bouton.configure(state="disabled")
        self._poser(self.zone, "zone_vide", fg="#444")
        self._poser(self.etat_rom, cle, *args, foreground="#b00")

    # ------------------------------------------------- modifier une ROM

    # Les cases que la ligne de commande coche d'un drapeau, une a une.
    DRAPEAUX = {
        "--objets-consommables": "equilibrer_conso",
        "--coffres-rouges-libres": "rouges_libres",
        "--boutiques-sans-progression": "prix_libres",
        "--boutiques-chaos": "boutiques_chaos", "--boss": "boss",
        "--boss-garder-premier": "garder_hexacorne",
        "--boss-familles-egales": "boss_familles_egales",
        "--boss-histoire": "boss_histoire",
        "--boss-legacy-tous": "boss_legacy_tous",
        "--boss-mixte": "boss_mixte",
        "--boss-chaque-combat": "boss_chaque_combat",
        "--boss-terrain": "boss_terrain", "--sorts": "sorts",
        "--sorts-chaos": "sorts_chaos", "--aptitudes": "aptitudes",
        "--aptitudes-chaos": "aptitudes_chaos",
        "--aptitudes-arme-origine": "aptitudes_arme_origine",
        "--points-brillants": "points",
        "--points-brillants-par-rang": "points_par_rang",
        "--alchimie": "alchimie", "--medailles": "medailles",
        "--medailles-chaos": "medailles_chaos",
        "--medailles-seuils-vanilla": "medailles_seuils_vanilla",
        "--butin-combat": "butin", "--butin-combat-libre": "butin_libre",
        "--sorts-monstres": "sorts_monstres",
        "--sorts-monstres-ajout": "sorts_monstres_ajout",
        "--techniques-monstres": "techniques_monstres",
        "--techniques-monstres-ajout": "techniques_monstres_ajout",
        "--actions-fixes": "actions_fixes", "--vocations": "vocations",
        "--vocations-embauche": "vocations_embauche",
        "--vocation-depart": "vocation_depart",
        "--vocations-bloquees": "vocations_bloquees", "--stats": "stats",
        "--stats-chaos": "stats_chaos", "--stats-combat": "stats_combat",
        "--stats-boss": "stats_boss", "--stats-boss-chaos": "stats_boss_chaos",
        "--stats-boss-combat": "stats_boss_combat",
        "--patch": "patch"}
    # celles que cochent leur ABSENCE
    ABSENCES = {"--sans-objets": "objets", "--sans-boutiques": "boutiques",
                "--sans-groupes": "groupes", "--objets-par-rang": "objets_chaos"}
    # drapeaux a valeur
    VALEURS = {"--seed": None, "--langue": None, "--apparitions": None,
               "--boss-grottes-des": "seuil_grottes",
               "--boss-legendes-des": "seuil_legendes"}

    def appliquer_arguments(self, opts):
        """Coche les cases d'une ligne de commande (celle qu'`arguments`
        produit) ; rend les options qu'aucune case ne represente."""
        self._applique = True
        inconnus = []
        for var in list(self.DRAPEAUX.values()):
            getattr(self, var).set(False)
        for var in self.ABSENCES.values():
            getattr(self, var).set(True)
        self.monstres.set(True)
        self.apparitions.set("aleatoire")
        for var in (self.seuil_grottes, self.seuil_legendes):
            var.set("debut")
        if all(x in opts for x in GREFFES_MONSTRES):
            self.apparitions.set("aleatoire")
        i = 0
        while i < len(opts):
            x = opts[i]
            if x in self.VALEURS and i + 1 < len(opts):
                v = opts[i + 1]
                if x == "--seed":
                    self.graine.set(v)
                elif x == "--apparitions":
                    if v == "vanilla":
                        self.monstres.set(False)
                    else:
                        self.apparitions.set(v)
                elif self.VALEURS[x]:
                    getattr(self, self.VALEURS[x]).set(v)
                i += 2
                continue
            if x in self.DRAPEAUX:
                getattr(self, self.DRAPEAUX[x]).set(True)
                mere = MERES.get(self.DRAPEAUX[x])
                if mere and mere != "monstres" and x != "--actions-fixes":
                    getattr(self, mere).set(True)
            elif x in self.ABSENCES:
                getattr(self, self.ABSENCES[x]).set(False)
            elif x not in GREFFES_MONSTRES:
                inconnus.append(x)
            i += 1
        if "--boss" not in opts:
            self.garder_hexacorne.set(True)
        for menu, variable in self._listes:
            self._remplir_liste(menu, variable)
        self.prereglage.set("custom")
        self._etat_cases_blob()
        self._applique = False
        return inconnus

    @staticmethod
    def lire_options(chemin_rom):
        """Les options du journal d'une ROM randomisee, ou None."""
        journal = os.path.splitext(chemin_rom)[0] + "_journal.txt"
        try:
            with open(journal, encoding="utf-8") as f:
                for ligne in f:
                    if ligne.startswith("options : "):
                        import json
                        return json.loads(ligne[len("options : "):])
                    if not ligne.strip():
                        break
        except (OSError, ValueError):
            pass
        return None

    @staticmethod
    def lire_graine(chemin_rom):
        """La graine d'un journal, meme d'une version qui n'enregistrait pas
        les options (premiere ligne : « ... seed=N ... »)."""
        import re
        journal = os.path.splitext(chemin_rom)[0] + "_journal.txt"
        try:
            with open(journal, encoding="utf-8") as f:
                m = re.search(r"\bseed=(\d+)", f.readline())
        except OSError:
            return None
        return m.group(1) if m else None

    @staticmethod
    def lire_source(chemin_rom):
        """La ROM d'origine que le journal d'une ROM randomisee nomme."""
        journal = os.path.splitext(chemin_rom)[0] + "_journal.txt"
        try:
            with open(journal, encoding="utf-8") as f:
                for ligne in f:
                    if ligne.startswith("ROM source : "):
                        return ligne[len("ROM source : "):].strip()
                    if not ligne.strip():
                        break
        except OSError:
            pass
        return None

    @staticmethod
    def _ancienne(chemin):
        return os.path.splitext(chemin)[0] + "_avant_modif.nds"

    def modifier_rom(self, c=None):
        """Reprendre une ROM randomisee : ses cases, sa graine, et la
        reconstruire SOUS LE MEME NOM, pour que la sauvegarde (rangee par
        nom de ROM dans melonDS, DeSmuME, BizHawk) continue. `c` : la ROM
        glissee dans la fenetre (sinon, on la demande)."""
        if self.en_cours:
            return
        if not self.rom_conforme:
            messagebox.showinfo(TITRE, self._t("modifier_vanilla_dabord"))
            return
        if c is None:
            c = filedialog.askopenfilename(
                title=self._t("modifier_titre"),
                filetypes=[(self._t("type_rom"), "*.nds"),
                           (self._t("type_tout"), "*.*")])
        if not c:
            return
        opts = self.lire_options(c)
        if opts is None:
            # UN JOURNAL D'UNE VERSION PLUS ANCIENNE : la graine seulement,
            # les cases restent celles de la fenetre (joueur, 20/10/2026)
            graine = self.lire_graine(c)
            if graine is None:
                messagebox.showerror(TITRE, self._t(
                    "modifier_sans_journal",
                    os.path.basename(os.path.splitext(c)[0] + "_journal.txt")))
                return
            if self.personnalise():
                self.notebook.select(0)
            self.graine.set(graine)
            self.a_modifier = os.path.abspath(c)
            texte = self._t("modifier_ancienne", graine)
            self._ecrire("")
            self._ecrire(texte)
            messagebox.showinfo(TITRE, texte)
            return
        if "--config" in opts:
            messagebox.showinfo(TITRE, self._t(
                "modifier_config", os.path.basename(self._chemin_config(c))))
            return
        inconnus = self.appliquer_arguments(opts)
        if self.personnalise():
            self.notebook.select(0)
        self.a_modifier = os.path.abspath(c)
        texte = self._t("modifier_pret", os.path.basename(c),
                        os.path.basename(self._ancienne(c)))
        self._ecrire("")
        self._ecrire(texte)
        if inconnus:
            self._ecrire(self._t("modifier_inconnus", " ".join(inconnus)))
        messagebox.showinfo(TITRE, texte)

    def _remplacer(self, neuve):
        """La ROM construite prend la place de celle qu'on modifie ; son
        journal et son patch aussi. L'ancienne ROM est gardee a cote."""
        cible = self.a_modifier
        self.a_modifier = None
        ancienne = self._ancienne(cible)
        if os.path.exists(ancienne):
            os.remove(ancienne)
        os.replace(cible, ancienne)
        os.replace(neuve, cible)
        b_n, b_c = os.path.splitext(neuve)[0], os.path.splitext(cible)[0]
        for suffixe in ("_journal.txt", ".xdelta"):
            if os.path.exists(b_n + suffixe):
                os.replace(b_n + suffixe, b_c + suffixe)
        return cible, ancienne

    # ---------------------------------------------------------- construire

    def appliquer_prereglage(self):
        """Coche ce que le prereglage dit. `custom` ne touche a rien."""
        choix = self.prereglage.get()
        if choix == "custom":
            return
        chaos = (choix == "chaos")
        self._applique = True
        for var in (self.monstres, self.objets, self.boutiques):
            var.set(True)
        for var in (self.rouges_libres,
                    self.boutiques_chaos, self.boss,
                    self.sorts_chaos, self.aptitudes_chaos, self.prix_libres):
            var.set(chaos)
        # LES OBJETS RARES PARTOUT DANS LES DEUX (joueur, 14/10/2026), et le
        # tirage brut : l'equilibre des consommables reste au choix.
        self.objets_chaos.set(True)
        self.equilibrer_conso.set(False)
        # LES SORTS SONT DANS LES DEUX PREREGLAGES : c'est une randomisation
        # a part entiere, pas une option de chaos. Ce qui change entre les
        # deux, c'est l'ordre de puissance.
        self.sorts.set(True)
        self.aptitudes.set(True)
        # LES VOCATIONS AUSSI, dans les deux : ouvrir les douze et tirer celle
        # d'une recrue n'est pas une borne qu'on leve, c'est une randomisation
        # (demande du joueur, ZER-36).
        self.vocations.set(True)
        self.vocations_embauche.set(True)
        self.vocation_depart.set(True)
        self.vocations_bloquees.set(False)
        # LE BUTIN A CHAQUE COMBAT DANS LES DEUX ; le chaos leve la rarete.
        self.butin.set(True)
        self.butin_libre.set(chaos)
        # LES SORTS ET TECHNIQUES DES MONSTRES : hors des prereglages
        # (decision du joueur, 11/10/2026) ; cases au choix du joueur.
        for var in (self.sorts_monstres, self.sorts_monstres_ajout,
                    self.techniques_monstres, self.techniques_monstres_ajout,
                    self.actions_fixes,
                    self.medailles_seuils_vanilla):
            var.set(False)
        # LE CAPITAINE DANS LES DEUX ; le chaos leve la bande d'etoiles
        # (ZER-55, joueur, 15/10/2026).
        self.medailles.set(True)
        self.medailles_chaos.set(chaos)
        # L'ALCHIMIE DANS LES DEUX (ZER-53, joueur, 14/10/2026).
        self.alchimie.set(True)
        self.garder_hexacorne.set(True)
        # LES STATS DES MONSTRES : hors des prereglages (ZER-58), au choix.
        for var in (self.stats, self.stats_chaos, self.stats_combat,
                    self.stats_boss, self.stats_boss_chaos,
                    self.stats_boss_combat):
            var.set(False)
        # LES POINTS BRILLANTS (ZER-97) DANS LES DEUX (joueur, 20/10/2026) ;
        # « proches de l'origine » reste au choix.
        self.points.set(True)
        self.points_par_rang.set(False)
        # LA 1.6 : le mode aleatoire et ses groupes dans les deux ; les
        # options neuves restent au choix du joueur.
        self.apparitions.set("aleatoire")
        self.groupes.set(True)
        for var in (self.seuil_grottes, self.seuil_legendes):
            var.set("debut")
        for menu, variable in self._listes:
            self._remplir_liste(menu, variable)
        for var in (self.boss_familles_egales, self.boss_histoire,
                    self.boss_legacy_tous, self.boss_mixte,
                    self.boss_chaque_combat, self.boss_terrain,
                    self.aptitudes_arme_origine):
            var.set(False)
        self._etat_cases_blob()
        self._applique = False

    def choix_manuel(self):
        """Une case cochee a la main : on n'est plus sur un prereglage."""
        self._etat_cases_blob()
        if not self._applique:
            self.prereglage.set("custom")

    def nouvelle_graine(self):
        self.graine.set(str(random.randrange(1, 10 ** 6)))

    def _chemin_config(self, sortie):
        """Le fichier de « Creer sa ROM », a cote de la ROM qu'il produit."""
        return os.path.splitext(sortie)[0] + "_config.json"

    def arguments(self, sans_config=False):
        """La ligne de commande, exactement celle qu'on taperait a la main.
        Depuis l'onglet « Creer sa ROM » (et sans `sans_config`, qui sert a
        tirer avec les options), la ROM PERSONNALISEE : sa config seule, sans
        aucune case des autres onglets (joueur, 20/10/2026)."""
        seed = self.graine.get().strip()
        # UN DOSSIER PAR GRAINE (ZER-79, suggestion d'un joueur) : la ROM, son
        # journal et le patch eventuel portent le meme nom et vont ensemble
        # dans un dossier a ce nom, a cote de la ROM d'origine.
        nom = "DQIX-Randomizer-seed%s" % seed
        sortie = os.path.join(
            os.path.dirname(os.path.abspath(self.rom)), nom, nom + ".nds")
        args = [self.rom, "--seed", seed]
        if not sans_config and self.personnalise():
            # le randomizer ne tire d'office que les objets et les boutiques ;
            # le reste (monstres, boss et leur code) vient de la config
            args += ["--sans-objets", "--sans-boutiques"]
            if self.patch.get():
                args.append("--patch")
            args += ["--langue", self.langue,
                     "--config", self._chemin_config(sortie), "-o", sortie]
            return args, sortie
        # LE MODE ALEATOIRE GARDE SA LIGNE D'AVANT (les greffes du blob) : la
        # meme ROM que `--apparitions aleatoire`, verifie par la matrice.
        aleatoire = self.monstres.get() and self.apparitions.get() == "aleatoire"
        if not self.monstres.get():
            args += ["--apparitions", "vanilla"]
        elif aleatoire:
            args += GREFFES_MONSTRES
            if not self.groupes.get():
                args.append("--sans-groupes")
            if self.boss_terrain.get():
                args.append("--boss-terrain")
        else:
            args += ["--apparitions", self.apparitions.get()]
        if self.objets.get():
            if self.equilibrer_conso.get():
                args.append("--objets-consommables")
            if not self.objets_chaos.get():
                args.append("--objets-par-rang")
                if self.rouges_libres.get():
                    args.append("--coffres-rouges-libres")
        else:
            args.append("--sans-objets")
        if self.boutiques.get():
            if self.prix_libres.get():
                args.append("--boutiques-sans-progression")
            if self.boutiques_chaos.get():
                args.append("--boutiques-chaos")
        else:
            args.append("--sans-boutiques")
        if self.boss.get():
            args.append("--boss")
            if self.garder_hexacorne.get():
                args.append("--boss-garder-premier")
            if (self.boss_familles_egales.get()
                    and not self.boss_histoire.get()):
                args.append("--boss-familles-egales")
            if self.boss_histoire.get():
                args.append("--boss-histoire")
            elif self.boss_legacy_tous.get():
                args.append("--boss-legacy-tous")
            if not self.boss_histoire.get():
                for opt, var in (("--boss-grottes-des", self.seuil_grottes),
                                 ("--boss-legendes-des",
                                  self.seuil_legendes)):
                    if var.get() != "debut":
                        args += [opt, var.get()]
            if self.boss_mixte.get():
                args.append("--boss-mixte")
            if self.boss_chaque_combat.get() and aleatoire:
                args.append("--boss-chaque-combat")
        if self.sorts.get():
            args.append("--sorts")
            if self.sorts_chaos.get():
                args.append("--sorts-chaos")
        if self.aptitudes.get():
            args.append("--aptitudes")
            if self.aptitudes_chaos.get():
                args.append("--aptitudes-chaos")
            if self.aptitudes_arme_origine.get():
                args.append("--aptitudes-arme-origine")
        if self.points.get():
            args.append("--points-brillants")
            if self.points_par_rang.get():
                args.append("--points-brillants-par-rang")
        if self.alchimie.get():
            args.append("--alchimie")
        if self.medailles.get():
            args.append("--medailles")
            if self.medailles_chaos.get():
                args.append("--medailles-chaos")
            if self.medailles_seuils_vanilla.get():
                args.append("--medailles-seuils-vanilla")
        if self.butin.get():
            args.append("--butin-combat")
            if self.butin_libre.get():
                args.append("--butin-combat-libre")
        if self.sorts_monstres.get():
            args.append("--sorts-monstres")
            if self.sorts_monstres_ajout.get():
                args.append("--sorts-monstres-ajout")
        if self.techniques_monstres.get():
            args.append("--techniques-monstres")
            if self.techniques_monstres_ajout.get():
                args.append("--techniques-monstres-ajout")
        if self.actions_fixes.get() and (self.sorts_monstres.get()
                                         or self.techniques_monstres.get()):
            args.append("--actions-fixes")
        if self.vocations.get():
            args.append("--vocations")
        if self.vocations_embauche.get():
            args.append("--vocations-embauche")
        if self.vocation_depart.get():
            args.append("--vocation-depart")
        if self.vocations_bloquees.get():
            args.append("--vocations-bloquees")
        if self.stats.get():
            args.append("--stats")
            if self.stats_chaos.get():
                args.append("--stats-chaos")
            if self.stats_combat.get():
                args.append("--stats-combat")
        if self.stats_boss.get():
            args.append("--stats-boss")
            if self.stats_boss_chaos.get():
                args.append("--stats-boss-chaos")
            if self.stats_boss_combat.get():
                args.append("--stats-boss-combat")
        if self.patch.get():
            args.append("--patch")
        # LA LANGUE DU JOURNAL suit celle de la fenetre (noms de monstres et
        # d'objets). Elle ne change pas un octet de la ROM.
        args += ["--langue", self.langue]
        args += ["-o", sortie]
        return args, sortie

    def lancer(self):
        # un tirage de « Creer sa ROM » detourne lui aussi la sortie standard
        if self.en_cours or not self.rom_conforme or self.creer._occupe:
            return
        try:
            int(self.graine.get().strip())
        except ValueError:
            messagebox.showerror(TITRE, self._t("graine_invalide"))
            return
        if not (self.monstres.get() or self.objets.get() or self.boutiques.get()
                or self.boss.get() or self.sorts.get()
                or self.aptitudes.get() or self.stats.get()
                or self.stats_boss.get()
                or self.points.get()
                or self.vocations.get() or self.vocations_embauche.get()
                or self.vocations_bloquees.get() or self.vocation_depart.get()
                or self.butin.get() or self.sorts_monstres.get()
                or self.alchimie.get() or self.medailles.get()
                or self.techniques_monstres.get()
                or (self.personnalise() and self.creer.cfg)
                or (self.boss_terrain.get() and self.monstres.get())):
            messagebox.showerror(TITRE, self._t("rien_coche"))
            return
        args, sortie = self.arguments()
        if self.a_modifier and not self.personnalise():
            # construite a cote, sous un nom provisoire, puis echangee
            # (`_remplacer`) : un echec laisse la ROM de la partie intacte
            sortie = os.path.splitext(self.a_modifier)[0] + "_nouvelle.nds"
            args[args.index("-o") + 1] = sortie
            if os.path.exists(sortie):
                os.remove(sortie)
        elif os.path.exists(sortie) and not messagebox.askyesno(
                TITRE, self._t("existe_deja", os.path.basename(sortie))):
            return
        if "--config" in args:
            # le fichier part avec la ROM, dans son dossier : pret a partager
            self.creer.ecrire(args[args.index("--config") + 1])
        self.en_cours = True
        self.bouton.configure(state="disabled")
        self._poser(self.bouton, "travail")
        self.progres.configure(mode="indeterminate")
        self.progres.start(12)
        self._ecrire("> randomizer.py " + " ".join(
            ('"%s"' % x if " " in x else x) for x in args))
        threading.Thread(target=self._construire_rom, args=(args, sortie),
                         daemon=True).start()

    def _construire_rom(self, args, sortie):
        """Tourne dans un fil. Ne touche a aucun widget : tout passe par la file."""
        ancien_argv, ancien_stdout = sys.argv, sys.stdout
        sortie_texte = Sortie(self.file)
        try:
            import randomizer
            sys.argv = ["randomizer.py"] + args
            sys.stdout = sortie_texte
            randomizer.main()
            sortie_texte.flush()
            self.file.put(("fini", sortie))
        except SystemExit as e:
            # `randomizer.py` refuse par SystemExit, avec un message deja utile.
            sortie_texte.flush()
            self._effacer_incomplet(sortie)
            self.file.put(("echec", str(e) or self._t("annule")))
        except Exception:
            sortie_texte.flush()
            self._effacer_incomplet(sortie)
            self.file.put(("echec", traceback.format_exc()))
        finally:
            sys.argv, sys.stdout = ancien_argv, ancien_stdout

    def _effacer_incomplet(self, sortie):
        """UNE ROM A MOITIE ECRITE EST UN PIEGE : elle a la bonne extension,
        elle s'ouvre dans l'emulateur, et elle plante plus tard sans qu'on
        sache pourquoi. On l'efface, et on le dit dans le journal."""
        if os.path.exists(sortie):
            try:
                os.remove(sortie)
                self.file.put(("log", self._t("incomplet_efface", sortie)))
            except OSError:
                pass

    # -------------------------------------------------------------- la file

    def _ecrire(self, ligne):
        self.journal.configure(state="normal")
        self.journal.insert("end", ligne + "\n")
        self.journal.see("end")
        self.journal.configure(state="disabled")

    def _vider_file(self):
        try:
            while True:
                genre, charge = self.file.get_nowait()
                if genre == "log":
                    self._ecrire(charge)
                elif genre == "progres":
                    self.progres.configure(value=charge)
                elif genre == "rom":
                    self._rom_verifiee(*charge)
                elif genre == "fini":
                    self._termine(charge)
                elif genre == "echec":
                    self._echoue(charge)
                elif genre == "xdelta":
                    self._xdelta_trouve(charge)
                elif genre == "appel":
                    # le retour d'un fil de « Creer sa ROM »
                    charge()
        except queue.Empty:
            pass
        self.racine.after(100, self._vider_file)

    def _rom_verifiee(self, chemin, md5, erreur):
        self.progres.configure(value=0)
        if erreur:
            self._refuser(chemin, "lecture_impossible", erreur)
            return
        if md5 != MD5_ATTENDU and (self.lire_options(chemin) is not None
                                   or self.lire_graine(chemin) is not None):
            # UNE ROM RANDOMISEE GLISSEE (joueur, 20/10/2026) : on reprend
            # sa ROM d'origine (nommee par son journal), puis on la modifie
            # la ROM d'origine : celle du journal, a defaut la derniere
            # deposee (retenue dans les reglages)
            self._modif_attente = chemin
            for src in (self.lire_source(chemin), lire_reglage("vanilla")):
                if (src and os.path.isfile(src)
                        and os.path.abspath(src) != os.path.abspath(chemin)):
                    self.adopter(src)
                    return
            self.rom, self.rom_conforme = None, False
            self.bouton.configure(state="disabled")
            self._poser(self.zone, "zone_vide", fg="#444")
            self._poser(self.etat_rom, brut="")
            messagebox.showinfo(TITRE, self._t("modifier_glisse"))
            return
        if md5 != MD5_ATTENDU:
            self._modif_attente = None
            self.rom_conforme = False
            self.bouton.configure(state="disabled")
            self._poser(self.zone, brut=os.path.basename(chemin), fg="#b00")
            self._poser(self.etat_rom, "rom_refusee", md5[:8],
                        foreground="#b00")
            self._ecrire(self._t("rom_pas_europe"))
            self._ecrire(self._t("md5_lu", md5))
            self._ecrire(self._t("md5_attendu", MD5_ATTENDU))
            self._ecrire(self._t("modifier_indice"))
            return
        self.rom_conforme = True
        # LA ROM DU JOUEUR EST LA VANILLA de reference : les modules qui
        # relisent le jeu d'origine (rom_vanilla.chemin_vanilla) la trouvent
        # ainsi dans l'exe, qui n'a pas de banc/roms (20/10 : onglet « Creer
        # sa ROM » vide, monstres et actions la relisent)
        os.environ["DQ9_VANILLA"] = os.path.abspath(chemin)
        # RETENUE pour « Modifier ma ROM » : glisser une ROM randomisee
        # suffit ensuite, meme si son journal ne retrouve plus l'origine
        memoriser("vanilla", os.path.abspath(chemin))
        self.bouton.configure(state="normal")
        self._poser(self.zone, brut=os.path.basename(chemin), fg="#070")
        self._poser(self.etat_rom, "rom_ok", foreground="#070")
        self._poser(self.dossier, "dossier",
                    os.path.dirname(os.path.abspath(chemin)))
        self.creer.rom_prete()
        if self._modif_attente:
            c, self._modif_attente = self._modif_attente, None
            self.modifier_rom(c)

    def _xdelta_trouve(self, chemin):
        if chemin:
            self.case_patch.configure(state="normal")
            self._poser(self.etat_patch, "xdelta_trouve",
                        os.path.basename(chemin))
        else:
            self._poser(self.etat_patch, "xdelta_absent")

    def _fin_de_travail(self):
        self.en_cours = False
        self.progres.stop()
        self.progres.configure(mode="determinate", value=0)
        self.bouton.configure(state="normal")
        self._libelle_bouton()

    def personnalise(self):
        """L'onglet « Creer sa ROM » est-il celui qu'on regarde ?"""
        try:
            return self.notebook.select() == str(self.creer.page)
        except (AttributeError, tk.TclError):
            return False

    def _libelle_bouton(self):
        if not self.en_cours:
            self._poser(self.bouton, "lancer_perso" if self.personnalise()
                        else "lancer")

    def _termine(self, sortie):
        self._fin_de_travail()
        if self.a_modifier and sortie.endswith("_nouvelle.nds"):
            try:
                cible, ancienne = self._remplacer(sortie)
            except OSError as e:
                self._echoue(str(e))
                return
            self._ecrire("")
            self._ecrire(self._t("modifier_fini", cible,
                                 os.path.basename(ancienne)))
            messagebox.showinfo(TITRE, self._t(
                "modifier_fini", os.path.basename(cible),
                os.path.basename(ancienne)))
            return
        self._ecrire("")
        self._ecrire(self._t("fini", sortie))
        if messagebox.askyesno(TITRE, self._t("prete", sortie)):
            self._ouvrir_dossier(os.path.dirname(sortie))

    def _echoue(self, message):
        self._fin_de_travail()
        self._ecrire("")
        self._ecrire(self._t("echec"))
        for ligne in message.splitlines():
            self._ecrire("  " + ligne)
        messagebox.showerror(TITRE, message.strip().splitlines()[-1]
                             if message.strip() else self._t("echec_court"))

    @staticmethod
    def _ouvrir_dossier(dossier):
        try:
            if sys.platform == "win32":
                os.startfile(dossier)                     # noqa: S606
            else:
                import subprocess
                subprocess.Popen(
                    ["open" if sys.platform == "darwin" else "xdg-open", dossier])
        except Exception:
            pass


class _Muet(object):
    """Une sortie qui avale tout.

    EN APPLICATION FENETREE, PyInstaller met `sys.stdout` a None : le moindre
    `print` leve alors AttributeError, et l'application se ferme sans rien
    dire. On lui donne donc toujours de quoi ecrire.
    """

    def write(self, _texte):
        return 0

    def flush(self):
        pass


def mode_ligne_de_commande(arguments):
    """`DQIX-Randomizer.exe --cli <options de randomizer.py>`.

    POURQUOI DANS L'APPLICATION. D'abord pour la tester : une fenetre ne se
    pilote pas depuis un script, alors que cette porte-la verifie exactement la
    meme chaine emballee -- keystone, ndspy, les soixante modules embarques.
    Ensuite parce que ca ne coute rien a qui veut scripter des graines.

    L'application etant fenetree, elle n'a pas de console : le journal part
    dans un fichier a cote de la ROM produite, et son chemin est annonce par
    une boite de dialogue seulement en cas d'echec.
    """
    import randomizer
    journal = os.path.join(os.getcwd(), "DQIX-Randomizer-cli.log")
    sortie = sys.stdout
    fichier = None
    if sortie is None or isinstance(sortie, _Muet):
        fichier = open(journal, "w", encoding="utf-8", errors="replace")
        sortie = fichier
    ancien, sys.stdout = sys.stdout, sortie
    sys.argv = ["randomizer.py"] + list(arguments)
    try:
        randomizer.main()
        return 0
    except SystemExit as e:
        print("ARRET :", e)
        return 1 if str(e) else 0
    except Exception:
        traceback.print_exc(file=sortie)
        return 1
    finally:
        sys.stdout = ancien
        if fichier is not None:
            fichier.close()


def main():
    if sys.stdout is None:
        sys.stdout = _Muet()
    if sys.stderr is None:
        sys.stderr = _Muet()
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        raise SystemExit(mode_ligne_de_commande(sys.argv[2:]))
    racine = (TkinterDnD.Tk() if TkinterDnD is not None else tk.Tk())
    app = Application(racine)
    # UNE ROM DEPOSEE SUR L'ICONE DE L'APPLICATION arrive par la ligne de
    # commande : c'est le geste naturel sous Windows, et il ne coute rien.
    for argument in sys.argv[1:]:
        if argument.lower().endswith(".nds"):
            app.adopter(argument)
            break
    racine.mainloop()


if __name__ == "__main__":
    main()
