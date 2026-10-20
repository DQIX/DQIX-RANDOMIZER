"""L'onglet « Creer sa ROM » de la fenetre (ZER-86), et ses categories.

CE QU'IL FAIT. Il tient une configuration complete (le format de
`config_rom`), la montre categorie par categorie dans un tableau, et laisse
le joueur changer chaque case. Quand la case « appliquer » est cochee, le
bouton principal ajoute `--config <dossier de la graine>/<nom>_config.json` a
sa ligne de commande : le fichier part avec la ROM, pret a partager.

D'OU VIENNENT LES CASES. Rien n'est tire ici :
  - « Tout en vanilla »        config_rom.exporter sur la ROM du joueur ;
  - « Tirer avec mes options »  randomizer.py avec les options des autres
                                onglets, --exporter-config et --sans-rom ;
  - « Tirer les cases non figees » config_rom.tirer, une categorie, une graine
                                neuve, sur la ROM du joueur rechargee.
Les cases figees (punaise) ne bougent dans aucun tirage.

DECISIONS DU JOUEUR (maquette validee le 19/10/2026) : tout est permis, sans
message ; seul ce qui empeche de finir le jeu est verrouille ; listes d'objets
avec type et etoiles ; le fichier ecrit tout.

FILS. Tout ce qui lit la ROM tourne dans un fil ; le resultat revient par la
file de l'application sous la forme ("appel", fonction), executee dans le fil
de Tk.
"""
import copy
import os
import random
import shutil
import sys
import tempfile
import threading
import traceback

import tkinter as tk
from tkinter import filedialog, ttk

import langues_interface as L

FIGEE, VERROU = "●", "■"
COULEUR_FIGEE = "#fbf0d9"
COULEUR_CHANGEE = "#e3eaf8"


class OngletCreer(object):

    def __init__(self, app, onglets, sortie_cls):
        import config_rom
        self.app = app
        self.Sortie = sortie_cls
        self.cfg = None              # sections courantes {categorie: section}
        self.vanilla = None          # sections du jeu d'origine
        self.figees = set()          # (categorie, table, index, champ)
        self.objets = []             # [(id, nom, type, etoiles)], TOUS
        self.etiquettes = {}         # id -> texte affiche
        self.interdits = {}          # categorie -> objets refuses (verrous)
        self.especes = []            # [(id, nom, genre)] (ZER-88)
        self.etiq_especes = {}       # id -> texte affiche
        # ZER-89..92 : sorts, paliers d'arbres, vocations -> texte affiche
        # ZER-93 : monstres du terrain (`monstre`)
        # et actions des monstres (`action`)
        self.etiq = {"sort": {}, "palier": {}, "vocation": {}, "monstre": {},
                     "action": {}}
        self.choix = {}              # genre -> [(id, texte)] pour l'editeur
        self.cat = config_rom.CATEGORIES[0]
        self.vue = {}                # categorie -> table montree (selecteur)
        self._champs_vus = []        # [(champ, genre)] des colonnes montrees
        self.editeur = None
        # LES VERROUS SE LEVENT (joueur, 19/10/2026) : la par defaut.
        self.verrous = tk.BooleanVar(value=True)
        self._occupe = False

        page = ttk.Frame(onglets, padding=10)
        onglets.add(page, text=app._t("onglet_creer"))
        app._onglets.append((onglets, page, "onglet_creer"))
        self.page = page

        intro = ttk.Label(page, foreground="#666", wraplength=900,
                          justify="left")
        intro.pack(anchor="w")
        app._poser(intro, "creer_intro")

        barre = ttk.Frame(page)
        barre.pack(fill="x", pady=(8, 0))
        self.boutons = []
        for cle, fn in (("creer_tirer_options", self.tirer_options),
                        ("creer_vanilla", self.tout_vanilla),
                        ("creer_ouvrir", self.ouvrir),
                        ("creer_enregistrer", self.enregistrer)):
            b = ttk.Button(barre, command=fn, state="disabled")
            b.pack(side="left", padx=(0, 6))
            app._poser(b, cle)
            self.boutons.append(b)
        # PLUS DE CASE « appliquer » (joueur, 20/10/2026) : le bouton
        # principal suit l'onglet ouvert (interface.personnalise)
        ligne_v = ttk.Frame(page)
        ligne_v.pack(fill="x", anchor="w", pady=(6, 0))
        self.case_verrous = ttk.Checkbutton(ligne_v, variable=self.verrous,
                                            state="disabled",
                                            command=self._verrous_changes)
        self.case_verrous.pack(side="left")
        app._poser(self.case_verrous, "creer_verrous")
        self.sans_verrous = ttk.Label(ligne_v, foreground="#666")
        self.sans_verrous.pack(side="left", padx=(8, 0))
        app._poser(self.sans_verrous, brut="")

        corps = ttk.Frame(page)
        corps.pack(fill="both", expand=True, pady=(8, 0))
        self.liste = tk.Listbox(corps, height=12, width=40,
                                exportselection=False, activestyle="none")
        self.liste.pack(side="left", fill="y")
        self.liste.bind("<<ListboxSelect>>", self._categorie_choisie)

        droite = ttk.Frame(corps)
        droite.pack(side="left", fill="both", expand=True, padx=(10, 0))
        ligne = ttk.Frame(droite)
        ligne.pack(fill="x")
        self.boutons_cat = []
        for cle, fn in (("creer_tirer_cat", self.tirer_categorie),
                        ("creer_vanilla_cat", self.vanilla_categorie),
                        ("creer_defiger", self.defiger)):
            b = ttk.Button(ligne, command=fn, state="disabled")
            b.pack(side="left", padx=(0, 6))
            app._poser(b, cle)
            self.boutons_cat.append(b)
        # TOUT A OUI / TOUT A NON (ZER-93), pour les categories dont la forme
        # nomme une table a cocher (`cocher`) : la liste du butin, ~1 080
        # lignes. Montres seulement la.
        # UNE TABLE A LA FOIS (joueur, 20/10/2026) : les categories a
        # plusieurs tables (coffres, boss, capitaine, actions) en montrent
        # une, avec ses seules colonnes ; les reglages restent au-dessus.
        self.cadre_liste = ttk.Frame(ligne)
        lab = ttk.Label(self.cadre_liste)
        lab.pack(side="left", padx=(6, 4))
        app._poser(lab, "creer_liste")
        self.choix_liste = ttk.Combobox(self.cadre_liste, state="readonly",
                                        width=34)
        self.choix_liste.pack(side="left", padx=(0, 6))
        self.choix_liste.bind("<<ComboboxSelected>>", self._liste_choisie)
        self.cadre_cocher = ttk.Frame(ligne)
        for cle, v in (("creer_tout_oui", True), ("creer_tout_non", False)):
            b = ttk.Button(self.cadre_cocher, state="disabled",
                           command=lambda v=v: self.tout_a(v))
            b.pack(side="left", padx=(0, 6))
            app._poser(b, cle)
            self.boutons_cat.append(b)

        # CHERCHER UNE LIGNE (joueur, 20/10/2026 : 438 monstres dans les
        # stats) : la frappe saute a la premiere ligne qui contient le texte
        # (sans accents ni casse), Entree a la suivante.
        ligne_c = ttk.Frame(droite)
        ligne_c.pack(fill="x", pady=(6, 0))
        lab = ttk.Label(ligne_c)
        lab.pack(side="left", padx=(0, 4))
        app._poser(lab, "creer_chercher")
        self.cherche = tk.StringVar()
        champ = ttk.Entry(ligne_c, textvariable=self.cherche, width=30)
        champ.pack(side="left")
        champ.bind("<KeyRelease-Return>", lambda _e: self.chercher(True))
        champ.bind("<KeyRelease>", lambda e: e.keysym == "Return"
                   or self.chercher(False))

        cadre_t = ttk.Frame(droite)
        cadre_t.pack(fill="both", expand=True, pady=(6, 0))
        self.table = ttk.Treeview(cadre_t, show="headings", height=10,
                                  selectmode="browse")
        asc = ttk.Scrollbar(cadre_t, command=self.table.yview)
        hsc = ttk.Scrollbar(cadre_t, orient="horizontal",
                            command=self.table.xview)
        hsc.pack(side="bottom", fill="x")
        self.table.pack(side="left", fill="both", expand=True)
        asc.pack(side="left", fill="y")
        self.table.configure(yscrollcommand=asc.set, xscrollcommand=hsc.set)
        self.table.tag_configure("figee", background=COULEUR_FIGEE)
        self.table.tag_configure("changee", background=COULEUR_CHANGEE)
        self.table.tag_configure("grise", foreground="#a0a0a0")
        self.table.bind("<Double-1>", self._double_clic)
        self.table.bind("<Button-1>", self._clic)
        self.table.bind("<MouseWheel>", lambda _e: self._fermer_editeur())

        aide = ttk.Label(droite, foreground="#666", wraplength=760,
                         justify="left")
        aide.pack(anchor="w", pady=(4, 0))
        app._poser(aide, "creer_aide_table")
        # l'aide propre a la categorie (FORME["aide"]), sous l'aide generale
        self.aide_cat = ttk.Label(droite, foreground="#444", wraplength=760,
                                  justify="left")
        self.aide_cat.pack(anchor="w", pady=(2, 0))
        app._poser(self.aide_cat, brut="")
        self.etat = ttk.Label(droite, foreground="#666", wraplength=760,
                              justify="left")
        self.etat.pack(anchor="w", pady=(2, 0))
        app._poser(self.etat, "creer_attente")
        self.retraduire()

    # ------------------------------------------------------------ affichage

    @staticmethod
    def _plat(texte):
        import unicodedata
        t = unicodedata.normalize("NFKD", str(texte))
        return "".join(c for c in t if not unicodedata.combining(c)).lower()

    def chercher(self, suivant=False):
        """Selectionne et montre la premiere ligne (apres la selection si
        `suivant`) dont une colonne contient le texte cherche."""
        txt = self._plat(self.cherche.get().strip())
        lignes = self.table.get_children()
        if not txt or not lignes:
            return False
        debut = 0
        sel = self.table.selection()
        if sel and sel[0] in lignes:
            debut = lignes.index(sel[0]) + (1 if suivant else 0)
        for k in range(len(lignes)):
            it = lignes[(debut + k) % len(lignes)]
            if any(txt in self._plat(v)
                   for v in self.table.item(it, "values")):
                self._fermer_editeur()
                self.table.selection_set(it)
                self.table.see(it)
                return True
        return False

    def _t(self, cle, *args):
        return self.app._t(cle, *args)

    def retraduire(self):
        """Ce que `_poser` ne couvre pas : la liste, les en-tetes, les cases."""
        import config_rom
        self.liste.delete(0, "end")
        for c in L.CATEGORIES_CREER:
            nom = self._t("cat_" + c)
            if c in config_rom.CATEGORIES:
                self.liste.insert("end", nom)
            else:
                self.liste.insert("end", self._t("creer_bientot", nom))
                self.liste.itemconfig("end", foreground="#999")
        k = L.CATEGORIES_CREER.index(self.cat)
        self.liste.selection_set(k)
        if self.app.rom_conforme and self.objets:
            self._charger_objets()
        self._remplir()

    def _forme(self, cat=None):
        import config_rom
        return config_rom.forme(cat or self.cat)

    @staticmethod
    def _nb(section, table, nb):
        """Le nombre de cases d'une table : fixe, ou celui de la section
        (les lignes des tables de loot, que le tirage multiplie)."""
        return nb if nb is not None else len(section.get(table, ()))

    def _ligne_vanilla(self, cat, table, k, nb_courant):
        """La ligne vanilla en face de la case k, ou None si la table n'a
        plus la meme forme (lignes de loot ajoutees par un tirage)."""
        van = (self.vanilla or {}).get(cat, {}).get(table, [])
        return van[k] if len(van) == nb_courant else None

    def _verrou(self, cat, table, k, champ, ligne_v=None):
        """Case verrouillee (si les verrous tiennent) : la forme le dit, ou
        sa valeur vanilla est un objet que la categorie refuse (la clef
        magique reste dans son coffre)."""
        if not self.verrous.get():
            return False
        f = self._forme(cat)
        if (table, k, champ) in f["verrous"]:
            return True
        if ligne_v is None:
            return False
        if f.get("verrou_ligne") and f["verrou_ligne"](table, ligne_v):
            return True
        genre = dict(f["champs"]).get(champ)
        return (genre == "objet" and champ in ligne_v
                and ligne_v[champ] in self.interdits.get(cat, ()))

    def _autres_tables(self, f=None):
        """Les tables entre lesquelles le selecteur choisit (pas les
        reglages, toujours montres)."""
        f = f or self._forme()
        return [t for t, _n in f["tables"] if t != "reglages"]

    def _tables_vues(self):
        """([tables montrees], {tables grisees}). La forme peut decider
        (`vue`, les monstres selon leur mode) ; sinon les reglages et la
        table du selecteur."""
        f = self._forme()
        if not self.cfg:
            return [], set()
        if "vue" in f:
            return f["vue"](self.cfg[self.cat])
        autres = self._autres_tables(f)
        t = self.vue.get(self.cat)
        if t not in autres:
            t = autres[0] if autres else None
        return [x for x, _n in f["tables"] if x == "reglages" or x == t], set()

    def _liste_choisie(self, _e=None):
        par_texte = {self._t("liste_" + t): t for t in self._autres_tables()}
        t = par_texte.get(self.choix_liste.get())
        if t:
            self.vue[self.cat] = t
            self._remplir()

    def _remplir(self):
        self._fermer_editeur()
        f = self._forme()
        vues, grises = self._tables_vues()
        autres = self._autres_tables(f)
        self.cadre_liste.pack_forget()
        self.cadre_cocher.pack_forget()
        if len(autres) > 1 and "vue" not in f:
            self.choix_liste.configure(
                values=[self._t("liste_" + t) for t in autres])
            courante = next((t for t in vues if t != "reglages"), autres[0])
            self.choix_liste.set(self._t("liste_" + courante))
            self.cadre_liste.pack(side="left")
        self.app._poser(self.aide_cat, f.get("aide"),
                        brut=None if f.get("aide") else "")
        if f.get("cocher") in vues:
            self.cadre_cocher.pack(side="left")
        # LES COLONNES DE LA TABLE MONTREE : un champ qu'aucune de ses lignes
        # ne porte n'a pas de colonne (le rang des coffres, joueur 20/10)
        section = self.cfg[self.cat] if self.cfg else {}
        presents = {c for t in vues for l in section.get(t, ()) for c in l}
        self._champs_vus = [(c, g) for c, g in f["champs"]
                            if c in presents or not self.cfg]
        champs = [c for c, _t in self._champs_vus]
        cols = ["figee", "place", "vanilla"] + champs
        self.table.configure(columns=cols)
        self.table.heading("figee", text="")
        self.table.column("figee", width=28, stretch=False, anchor="center")
        self.table.heading("place", text=self._t("creer_col_place"))
        self.table.column("place", width=100 if "place" not in f else 220,
                          stretch=False)
        self.table.heading("vanilla", text=self._t("creer_col_vanilla"))
        self.table.column("vanilla", width=200)
        for c, genre in self._champs_vus:
            self.table.heading(c, text=self._t("champ_" + c))
            self.table.column(c, width=90 if genre in ("nombre", "booleen") else
                              130 if genre in ("tirage", "source",
                                               "mode_stats") else 260,
                              stretch=genre not in ("nombre", "tirage",
                                                    "source", "booleen",
                                                    "mode_stats"))
        self.table.delete(*self.table.get_children())
        if not self.cfg:
            return
        for table, nb in f["tables"]:
            if table not in vues:
                continue
            n = self._nb(section, table, nb)
            for k in range(n):
                ligne = section[table][k]
                lv = self._ligne_vanilla(self.cat, table, k, n)
                verrou = any(self._verrou(self.cat, table, k, c, lv)
                             for c in champs if c in ligne)
                figee = any((self.cat, table, k, c) in self.figees
                            for c in champs)
                marque = FIGEE if figee else (VERROU if verrou else "")
                place = (f["place"](self._t, table, k, ligne) if "place" in f
                         else self._t("table_" + table, k + 1))
                # le vanilla ne tire rien a chaque visite : sa colonne
                # tirage serait du bruit
                vals = [marque, place,
                        "" if lv is None else
                        " · ".join(self._montrer(lv[c], g, lv, c)
                                        for c, g in self._champs_vus
                                        if g != "tirage" and c in lv)]
                # UNE CASE QUI NE SERT PAS (les valeurs d'un monstre aux
                # stats tirees, ZER-58) : un tiret ; UNE LIGNE QUI NE SERT
                # PAS (ses plages s'il est fixe) : grisee
                vals += ["—" if c in ligne and f.get("case_grise") and
                         f["case_grise"](section, table, k, c) else
                         self._montrer(ligne[c], g, ligne, c) if c in ligne
                         else "" for c, g in self._champs_vus]
                grisee = table in grises or bool(
                    f.get("ligne_grise") and f["ligne_grise"](section, table, k))
                tags = (("grise",) if grisee else
                        ("figee",) if figee else
                        ("changee",) if lv is None or any(
                            ligne.get(c) != lv.get(c) for c in champs)
                        else ())
                self.table.insert("", "end", iid="%s:%d" % (table, k),
                                  values=vals, tags=tags)

    def _montrer(self, v, genre, ligne=None, champ=None):
        if genre == "objet":
            texte = self.etiquettes.get(v, str(v))
            q = self._forme().get("quantites", {}).get(champ)
            if q and ligne and q in ligne:
                texte = "%d × %s" % (ligne[q], texte)
            return texte
        if genre == "espece":
            return self.etiq_especes.get(v, str(v))
        if genre == "tirage":
            return self._t("tirage_" + v)
        if genre == "apparition":
            return self._mode(v)
        if genre == "source":
            return self._t("source_" + v)
        if genre == "mode_stats":
            return self._t("mode_stats_" + v)
        if genre == "booleen":
            return self._t("booleen_oui" if v else "booleen_non")
        if genre in self.etiq:
            return self.etiq[genre].get(v, str(v))
        return str(v)

    def _mode(self, v):
        """Le libelle d'un mode d'apparition (le meme que l'onglet des
        monstres : la premiere moitie de `app_<mode>`)."""
        t = self._t("app_" + v)
        return t[0] if isinstance(t, tuple) else t

    def _etat(self, cle, *args, couleur="#666"):
        self.app._poser(self.etat, cle, *args, foreground=couleur)

    def _activer(self, oui):
        for b in self.boutons + self.boutons_cat:
            b.configure(state="normal" if oui else "disabled")
        self.case_verrous.configure(state="normal" if oui else "disabled")

    # ------------------------------------------------------------ les fils

    def _fil(self, travail, fini, apres=None):
        """`travail()` dans un fil, puis `fini(resultat)` dans celui de Tk ;
        une exception devient un message d'etat. `apres()` dans tous les cas."""
        if self._occupe or self.app.en_cours:
            if apres:
                apres()
            return
        self._occupe = True
        self._activer(False)

        def corps():
            try:
                r = travail()
                self.app.file.put(("appel", lambda: self._fin(fini, r, apres)))
            except (Exception, SystemExit) as e:
                # SystemExit aussi : un module qui s'arrete avec un message
                # (ROM d'origine introuvable) ne doit pas tuer le fil en
                # silence, l'onglet resterait vide et bloque
                msg = str(e) or traceback.format_exc().splitlines()[-1]
                self.app.file.put(("appel", lambda: self._fin(None, msg, apres)))
        threading.Thread(target=corps, daemon=True).start()

    def _fin(self, fini, r, apres=None):
        self._occupe = False
        self._activer(True)
        if apres:
            apres()
        if fini is None:
            self._etat("creer_controle_ko", r, couleur="#b00")
        else:
            fini(r)

    def _rom(self):
        import ndspy.rom
        return ndspy.rom.NintendoDSRom.fromFile(self.app.rom)

    def rom_prete(self):
        """Appele quand la ROM du joueur est reconnue : on lit le vanilla."""
        verrous = self.verrous.get()

        def travail():
            import config_rom
            rom = self._rom()
            cfg = config_rom.exporter(rom, self.app.langue)
            return ({c: cfg[c] for c in config_rom.CATEGORIES},
                    self._listes(rom, verrous))

        def fini(r):
            self.vanilla, listes = r
            self._poser_objets(listes)
            if self.cfg is None:
                self.cfg = copy.deepcopy(self.vanilla)
            self._remplir()
            self.app._poser(self.etat, brut="")
        self._fil(travail, fini)

    def _charger_objets(self):
        verrous = self.verrous.get()

        def travail():
            return self._listes(self._rom(), verrous)

        def fini(listes):
            self._poser_objets(listes)
            self._remplir()
        self._fil(travail, fini)

    def _listes(self, rom, verrous):
        """Ce que les cases peuvent recevoir. Les objets : TOUS (pour les
        etiquettes), chaque categorie retirant les siens a l'edition tant que
        les verrous tiennent."""
        import config_rom
        lg = self.app.langue
        return dict(
            objets=config_rom.objets_choisissables(rom, lg, verrous=False),
            interdits={c: config_rom.interdits(c, rom)
                       for c in config_rom.CATEGORIES},
            especes=config_rom.especes_choisissables(rom, lg, verrous),
            sort=config_rom.sorts_choisissables(rom, lg),
            palier=config_rom.paliers_choisissables(rom, lg),
            vocation=sorted(config_rom.vocations(rom, lg).items()),
            monstre=config_rom.monstres_choisissables(rom, lg),
            action=config_rom.actions_choisissables(rom, lg))

    def _objets_cat(self, cat=None):
        """Les objets qu'une case de la categorie peut recevoir."""
        refuses = (self.interdits.get(cat or self.cat, set())
                   if self.verrous.get() else set())
        return [o for o in self.objets if o[0] not in refuses]

    def _poser_objets(self, listes):
        objets, especes = listes["objets"], listes["especes"]
        self.objets, self.especes = objets, especes
        self.interdits = listes["interdits"]
        self.choix = {g: listes[g] for g in self.etiq}
        for g in self.etiq:
            self.etiq[g] = dict(listes[g])
        self.etiquettes = {
            i: "%s · %s%s" % (n, self._t("type_" + t),
                                   (" " + "★" * e) if e else "")
            for i, n, t, e in objets}
        # DEUX ESPECES DU MEME NOM ET DU MEME GENRE (le roi Govin, deux
        # combats) : l'identifiant les separe, sinon la liste les confond.
        textes = {}
        for i, n, g in especes:
            textes.setdefault("%s · %s" % (n, self._t("genre_" + g)),
                              []).append(i)
        self.etiq_especes = {}
        for t, ids in textes.items():
            for i in ids:
                self.etiq_especes[i] = t if len(ids) == 1 else "%s #%d" % (t, i)
        # les cases verrouillees (clef de voleur, Aquila et Corvus des
        # cinematiques) n'ont pas d'etiquette sinon
        if self.vanilla:
            for sec in self.vanilla.values():
                for lignes in sec.values():
                    if not isinstance(lignes, list):
                        continue
                    for l in lignes:
                        for c, etiq in (("objet", self.etiquettes),
                                        ("espece", self.etiq_especes)):
                            if c in l and l[c] not in etiq:
                                etiq[l[c]] = l.get("nom", str(l[c]))

    # ------------------------------------------------------------ actions

    def configuration(self, titre="DQIX-Randomizer"):
        import config_rom
        cfg = {"format": config_rom.FORMAT, "rom": config_rom.SERIE,
               "randomizer": titre, "langue": self.app.langue,
               "figees": sorted([list(f) for f in self.figees]),
               "verrous": self.verrous.get()}
        cfg.update(copy.deepcopy(self.cfg or {}))
        return cfg

    def ecrire(self, chemin):
        import config_rom
        config_rom.ecrire(chemin, self.configuration())

    def _changer(self):
        """Apres toute modification par le joueur. PAS DE VOYANT de controle
        (joueur, 19/10/2026 : << les gens font ce qu'ils veulent >>)."""
        self.app._poser(self.etat, brut="")
        self._remplir()

    def _verrous_changes(self):
        """Lever les verrous ouvre les cases ■ et les objets de quete."""
        self.app._poser(self.sans_verrous,
                        None if self.verrous.get() else "creer_sans_verrous",
                        brut="" if self.verrous.get() else None)
        self._charger_objets()

    @staticmethod
    def cle_nom(champ):
        """La cle du nom lisible qui accompagne une case dans le fichier."""
        return ("nom" if champ in ("objet", "espece", "sort", "palier",
                                   "vocation") else champ + "_nom")

    def _fusionner(self, sections):
        """Remplace les cases non figees par celles de `sections`."""
        import config_rom
        for cat, sec in sections.items():
            if cat not in config_rom.CATEGORIES:
                continue
            f = config_rom.forme(cat)
            noms = {t for t, _n in f["tables"]}
            # ce qui n'est pas une table (les prix fabriques des boutiques)
            # suit le tirage
            for cle, v in sec.items():
                if cle not in noms:
                    self.cfg[cat][cle] = copy.deepcopy(v)
            for table, nb in f["tables"]:
                cour, neuve = self.cfg[cat][table], sec[table]
                if len(cour) != len(neuve):
                    # UNE TABLE QUI CHANGE DE FORME (les lignes de loot que
                    # le tirage multiplie) se remplace entiere ; ses
                    # punaises n'ont plus de case en face.
                    self.cfg[cat][table] = copy.deepcopy(neuve)
                    self.figees = {x for x in self.figees
                                   if x[:2] != (cat, table)}
                    continue
                for k in range(len(cour)):
                    ligne, l2 = cour[k], neuve[k]
                    lv = self._ligne_vanilla(cat, table, k, len(cour))
                    gardes = {c for c, _g in f["champs"]
                              if (cat, table, k, c) in self.figees
                              or self._verrou(cat, table, k, c, lv)}
                    if not gardes:
                        cour[k] = copy.deepcopy(l2)
                        continue
                    for c, _g in f["champs"]:
                        if c in gardes or c not in l2 or c not in ligne:
                            continue
                        ligne[c] = l2[c]
                        n = self.cle_nom(c)
                        if n in l2:
                            ligne[n] = l2[n]

    def tout_vanilla(self):
        self.cfg = copy.deepcopy(self.vanilla)
        self.figees.clear()
        self._changer()

    def vanilla_categorie(self):
        self.cfg[self.cat] = copy.deepcopy(self.vanilla[self.cat])
        self.figees = {f for f in self.figees if f[0] != self.cat}
        self._changer()

    def tout_a(self, valeur):
        """Toutes les cases de la table a cocher a `valeur`, sauf les
        verrouillees ; chaque case changee est figee, comme a la main."""
        f = self._forme()
        table = f.get("cocher")
        if not table or not self.cfg:
            return
        lignes = self.cfg[self.cat][table]
        for k, l in enumerate(lignes):
            if l.get("actif") == valeur or self._verrou(
                    self.cat, table, k, "actif",
                    self._ligne_vanilla(self.cat, table, k, len(lignes))):
                continue
            l["actif"] = valeur
            self.figees.add((self.cat, table, k, "actif"))
        self._changer()

    def defiger(self):
        self.figees = {f for f in self.figees if f[0] != self.cat}
        self._remplir()

    def _options_categorie(self):
        a = self.app
        if self.cat == "capitaine":
            return dict(chaos=a.medailles_chaos.get(),
                        seuils_vanilla=a.medailles_seuils_vanilla.get())
        if self.cat == "boss":
            def seuil(v):
                v = v.get()
                return int(v) if v.isdigit() else v
            return dict(garder_premier=a.garder_hexacorne.get(),
                        egales=a.boss_familles_egales.get(),
                        histoire=a.boss_histoire.get(),
                        mixte=a.boss_mixte.get(),
                        chaque_combat=a.boss_chaque_combat.get(),
                        legacy_tous=a.boss_legacy_tous.get(),
                        seuils={"grottes": seuil(a.seuil_grottes),
                                "legendes": seuil(a.seuil_legendes)},
                        blob=(a.monstres.get()
                              and a.apparitions.get() == "aleatoire"))
        if self.cat == "boutiques":
            return dict(chaos=a.boutiques_chaos.get(),
                        progression=not a.prix_libres.get())
        if self.cat in ("coffres", "grottes"):
            chaos = a.objets_chaos.get()
            return dict(chaos=chaos, consommables=a.equilibrer_conso.get(),
                        rang_rouges=chaos or not a.rouges_libres.get())
        if self.cat in ("arbres", "sorts"):
            return dict(chaos=(a.aptitudes_chaos if self.cat == "arbres"
                               else a.sorts_chaos).get())
        if self.cat == "butin":
            return dict(libre=a.butin_libre.get())
        if self.cat == "stats":
            return dict(chaos=a.stats_chaos.get(),
                        combat=a.stats_combat.get())
        if self.cat == "points":
            return dict(par_rang=a.points_par_rang.get())
        if self.cat == "monstres":
            # LE MODE CHOISI DANS L'ONGLET, pas celui de l'onglet Monstres
            # (joueur, 20/10/2026 : les deux sont separes)
            return dict(mode=self.cfg["monstres"]["reglages"][0]["mode"])
        if self.cat == "actions":
            def mode(oui, ajout):
                return (("ajouter" if ajout.get() else "remplacer")
                        if oui.get() or ajout.get() else None)
            return dict(sorts=mode(a.sorts_monstres, a.sorts_monstres_ajout),
                        techniques=mode(a.techniques_monstres,
                                        a.techniques_monstres_ajout))
        if self.cat == "vocations":
            return dict(ouvertes=a.vocations.get(),
                        embauche=a.vocations_embauche.get(),
                        bloquees=a.vocations_bloquees.get(),
                        depart=a.vocation_depart.get())
        return {}

    def tirer_categorie(self):
        cat, opts = self.cat, self._options_categorie()
        graine = random.randrange(1, 10 ** 9)
        self._etat("creer_en_cours")

        def travail():
            import config_rom
            return config_rom.tirer(cat, self._rom(), graine, self.app.langue,
                                    **opts)

        def fini(section):
            self._fusionner({cat: section})
            self._changer()
        self._fil(travail, fini)

    def tirer_options(self):
        """Tout le tirage des autres onglets, sans ecrire de ROM."""
        args, _sortie = self.app.arguments(sans_config=True)
        dossier = tempfile.mkdtemp(prefix="dqix_creer_")
        fichier = os.path.join(dossier, "tirage.json")
        i = args.index("-o")
        args = [x for x in args[:i] if x != "--patch"] + [
            "--exporter-config", fichier, "--sans-rom",
            "-o", os.path.join(dossier, "tirage.nds")]
        self.app._ecrire("> randomizer.py " + " ".join(
            ('"%s"' % x if " " in x else x) for x in args))
        self._etat("creer_en_cours")
        self.app.progres.configure(mode="indeterminate")
        self.app.progres.start(12)

        def travail():
            import config_rom
            import randomizer
            ancien_argv, ancien_stdout = sys.argv, sys.stdout
            sortie = self.Sortie(self.app.file)
            try:
                sys.argv = ["randomizer.py"] + args
                sys.stdout = sortie
                try:
                    randomizer.main()
                except SystemExit as e:
                    if e.code not in (None, 0):
                        raise RuntimeError(str(e))
                sortie.flush()
                return config_rom.lire(fichier)
            finally:
                sys.argv, sys.stdout = ancien_argv, ancien_stdout
                shutil.rmtree(dossier, ignore_errors=True)

        def fini(cfg):
            self._fusionner(cfg)
            self._changer()

        def arreter():
            self.app.progres.stop()
            self.app.progres.configure(mode="determinate", value=0)
        self._fil(travail, fini, apres=arreter)

    def ouvrir(self):
        chemin = filedialog.askopenfilename(
            filetypes=[(self._t("creer_type_fichier"), "*.json"),
                       (self._t("type_tout"), "*.*")])
        if not chemin:
            return

        def travail():
            import config_rom
            cfg = config_rom.lire(chemin)
            config_rom.appliquer(self._rom(), cfg,        # leve si refuse
                                 vanilla=self._rom())
            return cfg

        def fini(cfg):
            import config_rom
            self.cfg = copy.deepcopy(self.vanilla)
            for c in config_rom.CATEGORIES:
                if c in cfg:
                    self.cfg[c] = cfg[c]
            self.figees = {tuple(f) for f in cfg.get("figees", [])
                           if isinstance(f, list) and len(f) == 4}
            if self.verrous.get() != (cfg.get("verrous", True) is not False):
                self.verrous.set(not self.verrous.get())
                self._verrous_changes()
            self._changer()
        self._etat("creer_en_cours")
        self._fil(travail, fini)

    def enregistrer(self):
        chemin = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[(self._t("creer_type_fichier"), "*.json")])
        if chemin:
            self.ecrire(chemin)
            self._etat("creer_config_ecrite", os.path.basename(chemin))

    # ------------------------------------------------------------ le tableau

    def _categorie_choisie(self, _e=None):
        import config_rom
        sel = self.liste.curselection()
        if not sel:
            return
        cat = L.CATEGORIES_CREER[sel[0]]
        if cat not in config_rom.CATEGORIES:
            self.liste.selection_clear(0, "end")
            self.liste.selection_set(L.CATEGORIES_CREER.index(self.cat))
            return
        self.cat = cat
        self._remplir()

    def _cellule(self, evenement):
        iid = self.table.identify_row(evenement.y)
        col = self.table.identify_column(evenement.x)
        if not iid or not col:
            return None, None
        return iid, int(col[1:]) - 1

    def _clic(self, evenement):
        self._fermer_editeur()
        iid, col = self._cellule(evenement)
        if iid is None or col != 0 or not self.cfg:
            return
        table, k = iid.split(":")
        cles = {(self.cat, table, int(k), c) for c, _g in self._forme()["champs"]}
        if cles & self.figees:
            self.figees -= cles
        else:
            self.figees |= cles
        self._remplir()

    def _double_clic(self, evenement):
        iid, col = self._cellule(evenement)
        f = self._forme()
        if iid is None or col < 3 or not self.cfg or self._occupe:
            return
        champ, genre = self._champs_vus[col - 3]
        table, k = iid.split(":")
        k = int(k)
        section = self.cfg[self.cat]
        if table in self._tables_vues()[1] or (
                f.get("ligne_grise") and f["ligne_grise"](section, table, k)
        ) or (f.get("case_grise") and f["case_grise"](section, table, k,
                                                      champ)):
            self._etat(f.get("grise", "creer_grise"), couleur="#b00")
            return
        ligne = self.cfg[self.cat][table][k]
        if champ not in ligne:
            return                      # une ligne d'or n'a pas d'objet
        n_table = len(self.cfg[self.cat][table])
        if self._verrou(self.cat, table, k, champ,
                        self._ligne_vanilla(self.cat, table, k, n_table)):
            self._etat("creer_verrou", couleur="#b00")
            return
        x, y, l, h = self.table.bbox(iid, "#%d" % (col + 1))
        actuel = ligne[champ]

        def valider(valeur):
            self._fermer_editeur()
            if valeur is None or valeur == actuel:
                return
            ligne[champ] = valeur
            nom = self.cle_nom(champ)
            if genre == "objet":
                ligne[nom] = next(
                    (n for i, n, _t, _e in self.objets if i == valeur), "")
            elif genre == "espece":
                ligne[nom] = next(
                    (n for i, n, _g in self.especes if i == valeur), "")
            elif genre in self.etiq and nom in ligne:
                ligne[nom] = self.etiq[genre].get(valeur, "")
            if champ in f.get("liees", {}):
                # UNE VALEUR DE LA BOUTIQUE (son pourcentage) : toutes ses
                # lignes la portent, elles changent ensemble
                cle = f["liees"][champ]
                for k2, l2 in enumerate(self.cfg[self.cat][table]):
                    if l2.get(cle) == ligne.get(cle):
                        l2[champ] = valeur
                        self.figees.add((self.cat, table, k2, champ))
            elif champ == "tirage":
                # LE MEME COMBAT SUR DEUX LIGNES (evenement 1) : le blob tire
                # par evenement et emplacement, les deux changent ensemble.
                l0 = self.cfg[self.cat][table][k]
                for t2, lignes in self.cfg[self.cat].items():
                    for k2, l2 in enumerate(lignes):
                        if (l2.get("evenement"), l2.get("emplacement")) == (
                                l0.get("evenement"), l0.get("emplacement")):
                            l2["tirage"] = valeur
                            self.figees.add((self.cat, t2, k2, champ))
            self.figees.add((self.cat, table, k, champ))
            self._changer()

        if genre == "nombre":
            bas, haut = f.get("bornes", {}).get(champ, (1, 65535))
            e = ttk.Spinbox(self.table, from_=bas, to=haut, width=8)
            e.set(actuel)

            def lu(_e=None):
                try:
                    v = int(e.get())
                except ValueError:
                    v = None
                valider(v if v is not None and bas <= v <= haut else None)
            e.bind("<Return>", lu)
        elif genre in ("booleen", "vocation"):
            choix = ([(True, self._t("booleen_oui")),
                      (False, self._t("booleen_non"))] if genre == "booleen"
                     else self.choix["vocation"])
            par_texte = {t: v for v, t in choix}
            e = ttk.Combobox(self.table, values=[t for _v, t in choix],
                             height=12, state="readonly")
            e.set(self._montrer(actuel, genre))

            def lu(_e=None):
                valider(par_texte.get(e.get()))
            e.bind("<<ComboboxSelected>>", lu)
            e.bind("<Return>", lu)
        elif genre == "apparition":
            import config_monstres
            par_texte = {self._mode(m): m for m in config_monstres.MODES}
            e = ttk.Combobox(self.table, values=list(par_texte), height=4,
                             state="readonly")
            e.set(self._mode(actuel))

            def lu(_e=None):
                valider(par_texte.get(e.get()))
            e.bind("<<ComboboxSelected>>", lu)
            e.bind("<Return>", lu)
        elif genre == "source":
            # l'emplacement d'une action de monstre (ZER-93)
            import config_actions
            par_texte = {self._t("source_" + c): c
                         for c in config_actions.SOURCES}
            e = ttk.Combobox(self.table, values=list(par_texte), height=4,
                             state="readonly")
            e.set(self._t("source_" + actuel))

            def lu(_e=None):
                valider(par_texte.get(e.get()))
            e.bind("<<ComboboxSelected>>", lu)
            e.bind("<Return>", lu)
        elif genre == "mode_stats":
            # les stats d'un monstre : fixes ou tirees (ZER-58)
            import config_stats
            par_texte = {self._t("mode_stats_" + c): c
                         for c in config_stats.MODES}
            e = ttk.Combobox(self.table, values=list(par_texte), height=4,
                             state="readonly")
            e.set(self._t("mode_stats_" + actuel))

            def lu(_e=None):
                valider(par_texte.get(e.get()))
            e.bind("<<ComboboxSelected>>", lu)
            e.bind("<Return>", lu)
        elif genre == "tirage":
            # TOUTE LIGNE (joueur, 19/10/2026 : « laisse choisir le joueur »)
            choix = ["fixe", "visite"]
            par_texte = {self._t("tirage_" + c): c for c in choix}
            e = ttk.Combobox(self.table, values=list(par_texte), height=4,
                             state="readonly")
            e.set(self._t("tirage_" + actuel))

            def lu(_e=None):
                valider(par_texte.get(e.get()))
            e.bind("<<ComboboxSelected>>", lu)
            e.bind("<Return>", lu)
        else:
            if genre == "espece":
                textes = [self.etiq_especes[i] for i, _n, _g in self.especes]
                par_texte = {self.etiq_especes[i]: i
                             for i, _n, _g in self.especes}
                courant = self.etiq_especes.get(actuel, "")
            elif genre in self.etiq:
                # deux paliers peuvent porter le meme libelle : le texte
                # de la liste est unique (arbre et cout le suivent)
                textes = [t for _i, t in self.choix[genre]]
                par_texte = {t: i for i, t in self.choix[genre]}
                courant = self.etiq[genre].get(actuel, "")
            else:
                objs = self._objets_cat()
                textes = [self.etiquettes[i] for i, _n, _t, _e in objs]
                par_texte = {self.etiquettes[i]: i
                             for i, _n, _t, _e in objs}
                courant = self.etiquettes.get(actuel, "")
            e = ttk.Combobox(self.table, values=textes, height=15)
            e.set(courant)

            def filtrer(ev):
                if ev.keysym in ("Return", "Escape", "Up", "Down"):
                    return
                q = e.get().lower()
                e.configure(values=[t for t in textes if q in t.lower()] or textes)

            def lu(_e=None):
                valider(par_texte.get(e.get()))
            e.bind("<KeyRelease>", filtrer)
            e.bind("<<ComboboxSelected>>", lu)
            e.bind("<Return>", lu)
        e.bind("<Escape>", lambda _e: self._fermer_editeur())
        e.place(x=x, y=y, width=max(l, 120), height=h)
        e.focus_set()
        self.editeur = e

    def _fermer_editeur(self):
        if self.editeur is not None:
            try:
                self.editeur.destroy()
            except tk.TclError:
                pass
            self.editeur = None
