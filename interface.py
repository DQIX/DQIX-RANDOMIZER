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
from tkinter import filedialog, messagebox, ttk

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


def memoriser_langue(code):
    try:
        chemin = _fichier_reglages()
        os.makedirs(os.path.dirname(chemin), exist_ok=True)
        with open(chemin, "w", encoding="utf-8") as f:
            json.dump({"langue": code}, f)
    except Exception:
        pass                    # un choix non memorise n'empeche rien


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
        if memoriser:
            memoriser_langue(code)

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

        boite = ttk.LabelFrame(cadre, padding=10)
        self._poser(boite, "quoi")
        boite.grid(row=6, column=0, sticky="ew", pady=(8, 0))
        self.monstres = tk.BooleanVar(value=True)
        self.objets = tk.BooleanVar(value=True)
        self.sans_consommables = tk.BooleanVar(value=False)
        self.objets_chaos = tk.BooleanVar(value=False)
        self.rouges_libres = tk.BooleanVar(value=False)
        self.boutiques = tk.BooleanVar(value=True)
        self.prix_libres = tk.BooleanVar(value=False)
        self.boutiques_chaos = tk.BooleanVar(value=False)
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
        self.sorts = tk.BooleanVar(value=False)
        self.sorts_chaos = tk.BooleanVar(value=False)
        self.aptitudes = tk.BooleanVar(value=False)
        self.aptitudes_chaos = tk.BooleanVar(value=False)
        self.stats = tk.BooleanVar(value=False)
        self._applique = False
        # L'ORDRE ET LES TEXTES DES CASES viennent de `langues_interface.CASES` ;
        # la cle d'une case est le nom de sa variable ici.
        for cle, retrait in L.CASES:
            ligne = ttk.Frame(boite)
            ligne.pack(fill="x", anchor="w", padx=(22 * retrait, 0))
            c = ttk.Checkbutton(ligne, variable=getattr(self, cle),
                                command=self.choix_manuel)
            c.pack(side="left")
            self._poser(c, cle, partie=0)
            d = ttk.Label(ligne, foreground="#666")
            d.pack(side="left")
            self._poser(d, cle, partie=1)

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
        self.dossier = ttk.Label(s, foreground="#666")
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
        for var in (self.objets_chaos, self.rouges_libres,
                    self.boutiques_chaos, self.boss,
                    self.sorts_chaos, self.aptitudes_chaos, self.prix_libres,
                    self.sans_consommables):
            var.set(chaos)
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
        self.garder_hexacorne.set(True)
        self.stats.set(False)
        self._applique = False

    def choix_manuel(self):
        """Une case cochee a la main : on n'est plus sur un prereglage."""
        if not self._applique:
            self.prereglage.set("custom")

    def nouvelle_graine(self):
        self.graine.set(str(random.randrange(1, 10 ** 6)))

    def arguments(self):
        """La ligne de commande, exactement celle qu'on taperait a la main."""
        seed = self.graine.get().strip()
        sortie = os.path.join(
            os.path.dirname(os.path.abspath(self.rom)),
            "DQIX-Randomizer-seed%s.nds" % seed)
        args = [self.rom, "--seed", seed]
        if self.monstres.get():
            args += GREFFES_MONSTRES
        else:
            args += ["--sans-rencontres", "--sans-hasard"]
        if self.objets.get():
            if self.sans_consommables.get():
                args.append("--objets-sans-consommables")
            if self.rouges_libres.get():
                args.append("--coffres-rouges-libres")
            if self.objets_chaos.get():
                args.append("--objets-chaos")
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
        if self.sorts.get():
            args.append("--sorts")
            if self.sorts_chaos.get():
                args.append("--sorts-chaos")
        if self.aptitudes.get():
            args.append("--aptitudes")
            if self.aptitudes_chaos.get():
                args.append("--aptitudes-chaos")
        if self.butin.get():
            args.append("--butin-combat")
            if self.butin_libre.get():
                args.append("--butin-combat-libre")
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
        if self.patch.get():
            args.append("--patch")
        # LA LANGUE DU JOURNAL suit celle de la fenetre (noms de monstres et
        # d'objets). Elle ne change pas un octet de la ROM.
        args += ["--langue", self.langue]
        args += ["-o", sortie]
        return args, sortie

    def lancer(self):
        if self.en_cours or not self.rom_conforme:
            return
        try:
            int(self.graine.get().strip())
        except ValueError:
            messagebox.showerror(TITRE, self._t("graine_invalide"))
            return
        if not (self.monstres.get() or self.objets.get() or self.boutiques.get()
                or self.boss.get() or self.sorts.get()
                or self.aptitudes.get() or self.stats.get()
                or self.vocations.get() or self.vocations_embauche.get()
                or self.vocations_bloquees.get() or self.vocation_depart.get()
                or self.butin.get()):
            messagebox.showerror(TITRE, self._t("rien_coche"))
            return
        args, sortie = self.arguments()
        if os.path.exists(sortie) and not messagebox.askyesno(
                TITRE, self._t("existe_deja", os.path.basename(sortie))):
            return
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
        except queue.Empty:
            pass
        self.racine.after(100, self._vider_file)

    def _rom_verifiee(self, chemin, md5, erreur):
        self.progres.configure(value=0)
        if erreur:
            self._refuser(chemin, "lecture_impossible", erreur)
            return
        if md5 != MD5_ATTENDU:
            self.rom_conforme = False
            self.bouton.configure(state="disabled")
            self._poser(self.zone, brut=os.path.basename(chemin), fg="#b00")
            self._poser(self.etat_rom, "rom_refusee", md5[:8],
                        foreground="#b00")
            self._ecrire(self._t("rom_pas_europe"))
            self._ecrire(self._t("md5_lu", md5))
            self._ecrire(self._t("md5_attendu", MD5_ATTENDU))
            return
        self.rom_conforme = True
        self.bouton.configure(state="normal")
        self._poser(self.zone, brut=os.path.basename(chemin), fg="#070")
        self._poser(self.etat_rom, "rom_ok", foreground="#070")
        self._poser(self.dossier, "dossier",
                    os.path.dirname(os.path.abspath(chemin)))

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
        self._poser(self.bouton, "lancer")

    def _termine(self, sortie):
        self._fin_de_travail()
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
