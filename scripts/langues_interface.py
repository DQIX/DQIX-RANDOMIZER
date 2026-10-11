#!/usr/bin/env python3
"""Les textes de la fenetre, dans les cinq langues de la ROM (ZER-48).

Demande du joueur, 25 septembre : un selecteur de langue dans la fenetre,
changement immediat. SEULE LA FENETRE est traduite ; le README, les notes de
version et le journal technique de `randomizer.py` restent en anglais (et le
journal en francais sans accents, comme toutes les sorties console).

LES NOMS DU JEU sont ceux de la ROM, lus dans ses fichiers le 25 septembre :
l'abbaye (`mapname`), Tulipe (`str_lui`), le premier boss (`mon_data`), la
vocation et la renouvocation (`bm_dama`, `str_dam`). Un joueur allemand lit
« Allesneu-Abtei » et « Hilda » dans son jeu : la fenetre dit la meme chose.

Chaque cle doit exister dans les cinq langues : `verifier()` le controle, et
la matrice l'appelle (essai d'interface).
"""

LANGUES = (("en", "English"), ("fr", "Français"), ("de", "Deutsch"),
           ("es", "Español"), ("it", "Italiano"))
CODES = tuple(c for c, _n in LANGUES)

T = {

    # --- la ROM ----------------------------------------------------------
    "langue": {
        "en": 'Language',
        "fr": 'Langue',
        "de": 'Sprache',
        "es": 'Idioma',
        "it": 'Lingua'},
    "zone_vide": {
        "en": 'Drop your Dragon Quest IX ROM here',
        "fr": 'Déposez ici votre ROM de Dragon Quest IX',
        "de": 'Lege deine Dragon-Quest-IX-ROM hier ab',
        "es": 'Suelta aquí tu ROM de Dragon Quest IX',
        "it": 'Trascina qui la tua ROM di Dragon Quest IX'},
    "parcourir": {
        "en": 'Browse...',
        "fr": 'Parcourir...',
        "de": 'Durchsuchen...',
        "es": 'Examinar...',
        "it": 'Sfoglia...'},
    "rom_europe": {
        "en": 'European release (En, Fr, De, Es, It) only',
        "fr": 'Version européenne (En, Fr, De, Es, It) uniquement',
        "de": 'Nur die europäische Version (En, Fr, De, Es, It)',
        "es": 'Solo la versión europea (En, Fr, De, Es, It)',
        "it": 'Solo la versione europea (En, Fr, De, Es, It)'},
    "choisir_titre": {
        "en": 'Choose your Dragon Quest IX ROM',
        "fr": 'Choisissez votre ROM de Dragon Quest IX',
        "de": 'Wähle deine Dragon-Quest-IX-ROM',
        "es": 'Elige tu ROM de Dragon Quest IX',
        "it": 'Scegli la tua ROM di Dragon Quest IX'},
    "type_rom": {
        "en": 'Nintendo DS ROM',
        "fr": 'ROM Nintendo DS',
        "de": 'Nintendo-DS-ROM',
        "es": 'ROM de Nintendo DS',
        "it": 'ROM Nintendo DS'},
    "type_tout": {
        "en": 'All files',
        "fr": 'Tous les fichiers',
        "de": 'Alle Dateien',
        "es": 'Todos los archivos',
        "it": 'Tutti i file'},
    "pas_nds": {
        "en": 'This is not a .nds file.',
        "fr": "Ce n'est pas un fichier .nds.",
        "de": 'Das ist keine .nds-Datei.',
        "es": 'Este archivo no es un .nds.',
        "it": 'Questo non è un file .nds.'},
    "verification": {
        "en": 'checking the file...',
        "fr": 'vérification du fichier...',
        "de": 'Datei wird geprüft...',
        "es": 'comprobando el archivo...',
        "it": 'controllo del file in corso...'},
    "lecture_impossible": {
        "en": 'Could not read the file: %s',
        "fr": 'Impossible de lire le fichier : %s',
        "de": 'Die Datei konnte nicht gelesen werden: %s',
        "es": 'No se pudo leer el archivo: %s',
        "it": 'Impossibile leggere il file: %s'},
    "rom_refusee": {
        "en": 'This is not the supported ROM (MD5 %s...)',
        "fr": "Ce n'est pas la ROM prise en charge (MD5 %s...)",
        "de": 'Das ist nicht die unterstützte ROM (MD5 %s...)',
        "es": 'Esta no es la ROM compatible (MD5 %s...)',
        "it": 'Questa non è la ROM supportata (MD5 %s...)'},
    "rom_pas_europe": {
        "en": 'This ROM is not the European multi-language release.',
        "fr": "Cette ROM n'est pas la version européenne multilingue.",
        "de": 'Diese ROM ist nicht die mehrsprachige europäische Version.',
        "es": 'Esta ROM no es la versión europea multilingüe.',
        "it": 'Questa ROM non è la versione europea multilingue.'},
    "md5_lu": {
        "en": '  read     : %s',
        "fr": '  lu       : %s',
        "de": '  gelesen  : %s',
        "es": '  leído    : %s',
        "it": '  letto    : %s'},
    "md5_attendu": {
        "en": '  expected : %s',
        "fr": '  attendu  : %s',
        "de": '  erwartet : %s',
        "es": '  esperado : %s',
        "it": '  atteso   : %s'},
    "rom_ok": {
        "en": 'European release, file verified',
        "fr": 'Version européenne, fichier vérifié',
        "de": 'Europäische Version, Datei geprüft',
        "es": 'Versión europea, archivo verificado',
        "it": 'Versione europea, file verificato'},

    # --- la graine et le prereglage --------------------------------------
    "graine": {
        "en": 'Seed',
        "fr": 'Graine',
        "de": 'Seed',
        "es": 'Semilla',
        "it": 'Seed'},
    "hasard": {
        "en": 'Random',
        "fr": 'Au hasard',
        "de": 'Zufällig',
        "es": 'Al azar',
        "it": 'Casuale'},
    "meme_graine": {
        "en": '  same seed = same game',
        "fr": '  même graine = même partie',
        "de": '  gleicher Seed = gleiches Spiel',
        "es": '  misma semilla = misma partida',
        "it": '  stesso seed = stessa partita'},
    "prereglage": {
        "en": 'Preset',
        "fr": 'Préréglage',
        "de": 'Voreinstellung',
        "es": 'Preajuste',
        "it": 'Preimpostazione'},
    "balanced": {
        "en": 'Balanced',
        "fr": 'Équilibré',
        "de": 'Ausgewogen',
        "es": 'Equilibrado',
        "it": 'Bilanciato'},
    "chaos": {
        "en": 'Total chaos',
        "fr": 'Chaos total',
        "de": 'Totales Chaos',
        "es": 'Caos total',
        "it": 'Caos totale'},
    "custom": {
        "en": 'Custom',
        "fr": 'Personnalisé',
        "de": 'Benutzerdefiniert',
        "es": 'Personalizado',
        "it": 'Personalizzato'},
    "prereglage_aide": {
        "en": '  Balanced: rare items stay rare and each shop keeps its '
              'specialty. Total chaos: no limits at all.',
        "fr": '  Équilibré : les objets rares restent rares et chaque boutique'
              ' garde sa spécialité. Chaos total : plus aucune limite.',
        "de": '  Ausgewogen: Seltenes bleibt selten, und jeder Laden behält '
              'sein Sortiment. Totales Chaos: keinerlei Grenzen.',
        "es": '  Equilibrado: los objetos raros siguen siendo raros y cada '
              'tienda conserva su especialidad. Caos total: sin ningún límite.',
        "it": '  Bilanciato: gli oggetti rari restano rari e ogni negozio '
              'mantiene la sua specialità. Caos totale: nessun limite.'},
    "quoi": {
        "en": 'What gets randomized',
        "fr": 'Ce qui est randomisé',
        "de": 'Was randomisiert wird',
        "es": 'Qué se aleatoriza',
        "it": 'Cosa viene randomizzato'},

    # --- les cases : (libelle, detail) -----------------------------------
    "monstres": {
        "en": ('Field monsters',
               'which monsters appear, in the mode chosen below'),
        "fr": ('Monstres du terrain',
               'quels monstres apparaissent, dans le mode choisi ci-dessous'),
        "de": ('Monster im Gelände',
               'welche Monster erscheinen, im unten gewählten Modus'),
        "es": ('Monstruos del mapa',
               'qué monstruos aparecen, en el modo elegido abajo'),
        "it": ('Mostri sul campo',
               'quali mostri compaiono, nella modalità scelta sotto')},
    # --- les modes d'apparition (ZER-73) : (libelle, detail) ------------
    "app_aleatoire": {
        "en": ('Random at every spawn',
               'any monster each time one appears (the most varied)'),
        "fr": ('Aléatoire à chaque apparition',
               "n'importe quel monstre chaque fois qu'un monstre apparaît "
               '(le plus varié)'),
        "de": ('Zufällig bei jedem Erscheinen',
               'bei jedem Erscheinen ein beliebiges Monster (am '
               'abwechslungsreichsten)'),
        "es": ('Aleatorio en cada aparición',
               'cualquier monstruo cada vez que aparece uno (lo más variado)'),
        "it": ('Casuale a ogni comparsa',
               'un mostro qualsiasi a ogni comparsa (il più vario)')},
    "app_zone": {
        "en": ('1-to-1 per area',
               'in each area, a monster is always replaced by the same other '
               'one; more stable, less varied'),
        "fr": ('1 pour 1 par zone',
               'dans chaque zone, un monstre est toujours remplacé par le même '
               'autre ; plus stable, moins varié'),
        "de": ('1 zu 1 pro Gebiet',
               'in jedem Gebiet wird ein Monster immer durch dasselbe andere '
               'ersetzt; stabiler, weniger abwechslungsreich'),
        "es": ('1 a 1 por zona',
               'en cada zona, un monstruo se sustituye siempre por el mismo '
               'otro; más estable, menos variado'),
        "it": ('1 a 1 per zona',
               'in ogni zona un mostro è sempre sostituito dallo stesso altro; '
               'più stabile, meno vario')},
    "app_globale": {
        "en": ('1-to-1 for the whole game',
               'a monster is replaced by the same other one everywhere; more stable, '
               'less varied'),
        "fr": ('1 pour 1 dans tout le jeu',
               'un monstre est remplacé par le même autre partout ; plus stable, '
               'moins varié'),
        "de": ('1 zu 1 im ganzen Spiel',
               'ein Monster wird überall durch dasselbe andere ersetzt; stabiler, '
               'weniger abwechslungsreich'),
        "es": ('1 a 1 en todo el juego',
               'un monstruo se sustituye por el mismo otro en todas partes; '
               'más estable, menos variado'),
        "it": ('1 a 1 in tutto il gioco',
               'un mostro è sostituito dallo stesso altro ovunque; più '
               'stabile, meno vario')},
    "groupes": {
        "en": ('monsters in groups',
               'a random monster brings companions, as in the base game '
               '(random mode)'),
        "fr": ('monstres en groupe',
               'un monstre tiré au hasard vient avec des compagnons, comme '
               'dans le jeu de base (mode aléatoire)'),
        "de": ('Monster in Gruppen',
               'ein zufälliges Monster bringt Begleiter mit, wie im '
               'Originalspiel (Zufallsmodus)'),
        "es": ('monstruos en grupo',
               'un monstruo al azar trae compañeros, como en el juego original '
               '(modo aleatorio)'),
        "it": ('mostri in gruppo',
               'un mostro casuale porta compagni, come nel gioco originale '
               '(modalità casuale)')},
    "objets": {
        "en": ('Chest and pot contents',
               'chests, pots, barrels and cupboards, plus the item each '
               'monster carries'),
        "fr": ('Contenu des coffres et des pots',
               "coffres, pots, tonneaux et placards, ainsi que l'objet que "
               'porte chaque monstre'),
        "de": ('Inhalt von Truhen und Töpfen',
               'Truhen, Töpfe, Fässer und Schränke sowie der Gegenstand, den '
               'jedes Monster bei sich trägt'),
        "es": ('Contenido de cofres y vasijas',
               'cofres, vasijas, barriles y armarios, además del objeto que '
               'lleva cada monstruo'),
        "it": ('Contenuto di forzieri e vasi',
               "forzieri, vasi, barili e armadi, oltre all'oggetto che porta "
               'ogni mostro')},
    "sans_consommables": {
        "en": ('mostly equipment',
               'a plain draw over every item: about 6 pieces of equipment per '
               'consumable; unticked, more herbs and potions'),
        "fr": ("surtout de l'équipement",
               'un tirage simple parmi tous les objets : environ 6 '
               "équipements pour 1 consommable ; décochée, plus d'herbes et "
               'de potions'),
        "de": ('vor allem Ausrüstung',
               'reine Zufallsziehung über alle Gegenstände: etwa 6 '
               'Ausrüstungsteile pro Verbrauchsgegenstand; ohne Haken mehr '
               'Kräuter und Tränke'),
        "es": ('sobre todo equipo',
               'un sorteo simple entre todos los objetos: unas 6 piezas de '
               'equipo por consumible; sin marcar, más hierbas y pociones'),
        "it": ('soprattutto equipaggiamento',
               'estrazione semplice tra tutti gli oggetti: circa 6 '
               'equipaggiamenti per consumabile; senza spunta, più erbe e '
               'pozioni')},
    "objets_chaos": {
        "en": ('rare items everywhere',
               'legendary gear can turn up in the very first barrel'),
        "fr": ('objets rares partout',
               'un équipement légendaire peut se trouver dès le premier '
               'tonneau'),
        "de": ('seltene Gegenstände überall',
               'legendäre Ausrüstung kann schon im ersten Fass liegen'),
        "es": ('objetos raros por todas partes',
               'puede haber equipo legendario ya en el primer barril'),
        "it": ('oggetti rari ovunque',
               'un equipaggiamento leggendario può trovarsi già nel primo '
               'barile')},
    "rouges_libres": {
        "en": ('red chests without guarantee',
               'a red chest can hold anything, even an ordinary item'),
        "fr": ('coffres rouges sans garantie',
               "un coffre rouge peut contenir n'importe quoi, même un objet "
               'ordinaire'),
        "de": ('rote Truhen ohne Garantie',
               'eine rote Truhe kann alles enthalten, auch einen gewöhnlichen '
               'Gegenstand'),
        "es": ('cofres rojos sin garantía',
               'un cofre rojo puede contener cualquier cosa, incluso un objeto'
               ' corriente'),
        "it": ('forzieri rossi senza garanzia',
               'un forziere rosso può contenere di tutto, anche un oggetto '
               'comune')},
    "butin": {
        "en": ('New drops every battle',
               'in every battle, the item a monster can drop is picked at '
               'random'),
        "fr": ('Objets lâchés tirés à chaque combat',
               "à chaque combat, l'objet que peut lâcher un monstre est tiré "
               'au hasard'),
        "de": ('Neue Beute in jedem Kampf',
               'in jedem Kampf wird der Gegenstand, den ein Monster fallen '
               'lassen kann, zufällig bestimmt'),
        "es": ('Botín nuevo en cada combate',
               'en cada combate, el objeto que puede soltar un monstruo se '
               'elige al azar'),
        "it": ('Bottino nuovo a ogni battaglia',
               "a ogni battaglia, l'oggetto che un mostro può lasciare viene "
               'scelto a caso')},
    "butin_libre": {
        "en": ('4- and 5-star items as common as the rest',
               'otherwise they stay rare: about one drop in 60'),
        "fr": ('objets 4 et 5 étoiles aussi fréquents que les autres',
               'sinon, ils restent rares : environ un objet lâché sur 60'),
        "de": ('4- und 5-Sterne-Gegenstände so häufig wie andere',
               'sonst bleiben sie selten: etwa eine von 60 Beuten'),
        "es": ('objetos de 4 y 5 estrellas tan comunes como los demás',
               'si no, siguen siendo raros: más o menos uno de cada 60 botines'),
        "it": ('oggetti a 4 e 5 stelle comuni come gli altri',
               'altrimenti restano rari: circa un bottino su 60')},
    "sorts_monstres": {
        "en": ('Monster spells drawn every battle (experimental)',
               'in every battle, the spells a monster knows are picked at '
               'random among the 53 battle spells'),
        "fr": ('Sorts des monstres tirés à chaque combat (expérimental)',
               'à chaque combat, les sorts que connaît un monstre sont tirés '
               'au hasard parmi les 53 sorts de combat'),
        "de": ('Monsterzauber in jedem Kampf neu (experimentell)',
               'in jedem Kampf werden die Zauber eines Monsters zufällig aus '
               'den 53 Kampfzaubern gewählt'),
        "es": ('Hechizos de monstruos nuevos en cada combate (experimental)',
               'en cada combate, los hechizos de un monstruo se eligen al azar '
               'entre los 53 hechizos de combate'),
        "it": ('Magie dei mostri nuove a ogni battaglia (sperimentale)',
               'a ogni battaglia, le magie di un mostro vengono scelte a caso '
               'tra le 53 magie di battaglia')},
    "sorts_monstres_ajout": {
        "en": ('monsters without spells get one too',
               'one extra action among their six, not a spellcaster'),
        "fr": ('les monstres sans sort en reçoivent un aussi',
               'une action de plus parmi leurs six, pas un lanceur de sorts'),
        "de": ('Monster ohne Zauber bekommen auch einen',
               'eine Aktion mehr unter ihren sechs, kein Zauberer'),
        "es": ('los monstruos sin hechizos también reciben uno',
               'una acción más entre sus seis, no un lanzador de hechizos'),
        "it": ('anche i mostri senza magie ne ricevono una',
               "un'azione in più tra le loro sei, non un incantatore")},
    "techniques_monstres": {
        "en": ('Monster abilities drawn every battle (experimental)',
               "in every battle, a monster's abilities are picked at random "
               "among those of monsters and heroes, with their real animation"),
        "fr": ('Techniques des monstres tirées à chaque combat (expérimental)',
               "à chaque combat, les techniques d'un monstre sont tirées au "
               'hasard parmi celles des monstres et des héros, avec leur vraie '
               'animation'),
        "de": ('Monsterfähigkeiten in jedem Kampf neu (experimentell)',
               'in jedem Kampf werden die Fähigkeiten eines Monsters zufällig '
               'aus denen der Monster und Helden gewählt, mit ihrer echten '
               'Animation'),
        "es": ('Habilidades de monstruos nuevas en cada combate (experimental)',
               'en cada combate, las habilidades de un monstruo se eligen al '
               'azar entre las de monstruos y héroes, con su animación real'),
        "it": ('Abilità dei mostri nuove a ogni battaglia (sperimentale)',
               "a ogni battaglia, le abilità di un mostro vengono scelte a "
               "caso tra quelle di mostri ed eroi, con la loro vera animazione")},
    "techniques_monstres_ajout": {
        "en": ('monsters without abilities get one too',
               'one extra action among their six'),
        "fr": ('les monstres sans technique en reçoivent une aussi',
               'une action de plus parmi leurs six'),
        "de": ('Monster ohne Fähigkeit bekommen auch eine',
               'eine Aktion mehr unter ihren sechs'),
        "es": ('los monstruos sin habilidades también reciben una',
               'una acción más entre sus seis'),
        "it": ("anche i mostri senza abilità ne ricevono una",
               "un'azione in più tra le loro sei")},
    "boutiques": {
        "en": ('Shops',
               'what the 37 shops sell'),
        "fr": ('Boutiques',
               'ce que vendent les 37 boutiques'),
        "de": ('Läden',
               'das Angebot der 37 Läden'),
        "es": ('Tiendas',
               'lo que venden las 37 tiendas'),
        "it": ('Negozi',
               'la merce dei 37 negozi')},
    "prix_libres": {
        "en": ('expensive gear for sale from the start',
               'otherwise each shop sells gear suited to its point in the '
               'story'),
        "fr": ('équipement cher en vente dès le début',
               'sinon, chaque boutique vend des objets adaptés à son moment de'
               " l'histoire"),
        "de": ('teure Ausrüstung von Anfang an zu kaufen',
               'sonst verkauft jeder Laden, was zu seinem Abschnitt der '
               'Geschichte passt'),
        "es": ('equipo caro a la venta desde el principio',
               'si no, cada tienda vende lo que corresponde a su momento de la'
               ' historia'),
        "it": ('equipaggiamento costoso in vendita da subito',
               'altrimenti ogni negozio vende ciò che si addice al suo momento'
               ' della storia')},
    "boutiques_chaos": {
        "en": ('any item in any shop',
               'an armourer may sell herbs, and an item shop may sell armour'),
        "fr": ("n'importe quel objet dans n'importe quelle boutique",
               "un armurier peut vendre des herbes, et une boutique d'objets "
               'des armures'),
        "de": ('jeder Gegenstand in jedem Laden',
               'ein Waffenschmied kann Kräuter verkaufen, ein '
               'Gemischtwarenladen Rüstungen'),
        "es": ('cualquier objeto en cualquier tienda',
               'un armero puede vender hierbas, y una tienda de objetos, '
               'armaduras'),
        "it": ('qualsiasi oggetto in qualsiasi negozio',
               'un armaiolo può vendere erbe e un emporio armature')},
    "boss": {
        "en": ('Boss fights',
               'every boss fight (story, grottos, legacy bosses) is against '
               'another boss, picked at random'),
        "fr": ('Combats de boss',
               'chaque combat de boss (histoire, grottes, légendes) se fait '
               'contre un autre boss, tiré au hasard'),
        "de": ('Bosskämpfe',
               'jeder Bosskampf (Geschichte, Grotten, Legenden) findet gegen '
               'einen anderen, zufälligen Boss statt'),
        "es": ('Combates contra jefes',
               'cada combate contra un jefe (historia, grutas, leyendas) es '
               'contra otro jefe elegido al azar'),
        "it": ('Scontri con i boss',
               'ogni scontro con un boss (storia, grotte, leggende) è contro '
               'un altro boss scelto a caso')},
    "boss_familles_egales": {
        "en": ('equal boss families',
               'story, grotto and legacy bosses come out as often as each '
               'other'),
        "fr": ('familles de boss égales',
               "les boss de l'histoire, des grottes et des légendes sortent "
               'aussi souvent les uns que les autres'),
        "de": ('gleiche Boss-Familien',
               'Geschichts-, Grotten- und Legendenbosse erscheinen gleich oft'),
        "es": ('familias de jefes iguales',
               'los jefes de la historia, de las grutas y legendarios salen '
               'con la misma frecuencia'),
        "it": ('famiglie di boss alla pari',
               'i boss della storia, delle grotte e leggendari escono con la '
               'stessa frequenza')},
    "boss_histoire": {
        "en": ('story bosses only',
               'only story bosses are shuffled; grotto and legacy fights stay '
               'as they are'),
        "fr": ("boss de l'histoire seulement",
               "seuls les boss de l'histoire sont mélangés ; les combats des "
               'grottes et des légendes ne changent pas'),
        "de": ('nur Geschichtsbosse',
               'nur die Bosse der Geschichte werden gemischt; Grotten- und '
               'Legendenkämpfe bleiben gleich'),
        "es": ('solo jefes de la historia',
               'solo se mezclan los jefes de la historia; los combates de '
               'grutas y legendarios no cambian'),
        "it": ('solo boss della storia',
               'si mescolano solo i boss della storia; gli scontri delle '
               'grotte e leggendari restano uguali')},
    "boss_mixte": {
        "en": ('bosses or monsters',
               'a boss fight can also be against an ordinary monster'),
        "fr": ('boss ou monstres',
               'un combat de boss peut aussi se faire contre un monstre '
               'ordinaire'),
        "de": ('Bosse oder Monster',
               'ein Bosskampf kann auch gegen ein gewöhnliches Monster '
               'stattfinden'),
        "es": ('jefes o monstruos',
               'un combate de jefe también puede ser contra un monstruo '
               'normal'),
        "it": ('boss o mostri',
               'uno scontro con un boss può essere anche contro un mostro '
               'comune')},
    "boss_chaque_combat": {
        "en": ('new boss every attempt',
               'another boss is drawn each time you enter the fight, e.g. '
               'after a defeat (random mode)'),
        "fr": ('nouveau boss à chaque essai',
               "un autre boss est tiré chaque fois qu'on entre dans le "
               'combat, par exemple après une défaite (mode aléatoire)'),
        "de": ('neuer Boss bei jedem Versuch',
               'bei jedem Betreten des Kampfes, z. B. nach einer Niederlage, '
               'wird ein anderer Boss gezogen (Zufallsmodus)'),
        "es": ('jefe nuevo en cada intento',
               'se sortea otro jefe cada vez que entras en el combate, por '
               'ejemplo tras una derrota (modo aleatorio)'),
        "it": ('nuovo boss a ogni tentativo',
               'viene estratto un altro boss ogni volta che entri nello '
               'scontro, per esempio dopo una sconfitta (modalità casuale)')},
    "boss_terrain": {
        "en": ('Bosses on the field (experimental)',
               'some bosses can also wander the map like monsters (random '
               'mode)'),
        "fr": ('Boss sur le terrain (expérimental)',
               'certains boss peuvent aussi se promener sur la carte comme '
               'des monstres (mode aléatoire)'),
        "de": ('Bosse im Gelände (experimentell)',
               'einige Bosse können auch wie Monster über die Karte streifen '
               '(Zufallsmodus)'),
        "es": ('Jefes en el mapa (experimental)',
               'algunos jefes también pueden deambular por el mapa como '
               'monstruos (modo aleatorio)'),
        "it": ('Boss sul campo (sperimentale)',
               'alcuni boss possono anche girare sulla mappa come mostri '
               '(modalità casuale)')},
    "aptitudes_arme_origine": {
        "en": ('techniques keep their weapon',
               'a weapon technique moved to another tree still needs its '
               'original weapon'),
        "fr": ('les techniques gardent leur arme',
               "une technique d'arme déplacée dans un autre arbre demande "
               "toujours son arme d'origine"),
        "de": ('Techniken behalten ihre Waffe',
               'eine Waffentechnik in einem anderen Baum braucht weiterhin '
               'ihre ursprüngliche Waffe'),
        "es": ('las técnicas conservan su arma',
               'una técnica de arma movida a otro árbol sigue necesitando su '
               'arma original'),
        "it": ("le tecniche mantengono l'arma",
               "una tecnica d'arma spostata in un altro albero richiede ancora "
               "la sua arma originale")},
    # --- les onglets (ZER-64) --------------------------------------------
    "onglet_monstres": {
        "en": 'Monsters', "fr": 'Monstres', "de": 'Monster',
        "es": 'Monstruos', "it": 'Mostri'},
    "onglet_boss": {
        "en": 'Bosses', "fr": 'Boss', "de": 'Bosse', "es": 'Jefes',
        "it": 'Boss'},
    "onglet_objets": {
        "en": 'Items & shops', "fr": 'Objets et boutiques',
        "de": 'Gegenstände & Läden', "es": 'Objetos y tiendas',
        "it": 'Oggetti e negozi'},
    "onglet_equipe": {
        "en": 'Party', "fr": 'Équipe', "de": 'Gruppe', "es": 'Grupo',
        "it": 'Squadra'},
    "garder_hexacorne": {
        "en": ('keep the first boss',
               'Hexagoon stays as he is: you fight him alone, without a party'),
        "fr": ('garder le premier boss',
               "Hexacorne ne change pas : on l'affronte seul, sans équipe"),
        "de": ('ersten Boss behalten',
               'Hexagoblin bleibt unverändert: Man kämpft allein gegen ihn, '
               'ohne Gruppe'),
        "es": ('mantener el primer jefe',
               'Hexatauro no cambia: te enfrentas a él solo, sin grupo'),
        "it": ('mantieni il primo boss',
               'Hexagon non cambia: lo affronti da solo, senza gruppo')},
    "sorts": {
        "en": ('Spells',
               'the spells each vocation learns as it levels up'),
        "fr": ('Sorts',
               'les sorts que chaque vocation apprend en gagnant des niveaux'),
        "de": ('Zauber',
               'die Zauber, die jede Berufung beim Stufenaufstieg lernt'),
        "es": ('Hechizos',
               'los hechizos que aprende cada vocación al subir de nivel'),
        "it": ('Magie',
               'le magie che ogni vocazione impara salendo di livello')},
    "sorts_chaos": {
        "en": ('powerful spells from the start',
               'a top-tier spell can be learned at level 1'),
        "fr": ('sorts puissants dès le début',
               "un sort de haut niveau peut s'apprendre dès le niveau 1"),
        "de": ('starke Zauber von Anfang an',
               'ein mächtiger Zauber kann schon auf Stufe 1 erlernt werden'),
        "es": ('hechizos potentes desde el principio',
               'un hechizo de alto nivel puede aprenderse ya en el nivel 1'),
        "it": ("magie potenti fin dall'inizio",
               'una magia di alto livello si può imparare già al livello 1')},
    "aptitudes": {
        "en": ('Skill trees',
               'the abilities and stat bonuses unlocked with skill points'),
        "fr": ('Arbres de compétences',
               'les aptitudes et les bonus débloqués avec les points de '
               'compétence'),
        "de": ('Fertigkeitsbäume',
               'die Fähigkeiten und Wertboni, die man mit Fertigkeitspunkten '
               'freischaltet'),
        "es": ('Árboles de habilidades',
               'las habilidades y bonificaciones que se desbloquean con puntos'
               ' de habilidad'),
        "it": ('Alberi delle abilità',
               'le abilità e i bonus che si sbloccano con i punti abilità')},
    "aptitudes_chaos": {
        "en": ('mix the trees together',
               'a sword ability can turn up in the whip tree'),
        "fr": ('mélanger les arbres entre eux',
               "une aptitude d'épée peut apparaître dans l'arbre du fouet"),
        "de": ('Bäume untereinander mischen',
               'eine Schwertfähigkeit kann im Peitschenbaum auftauchen'),
        "es": ('mezclar los árboles entre sí',
               'una habilidad de espada puede aparecer en el árbol del látigo'),
        "it": ('mescola gli alberi tra loro',
               "un'abilità della spada può comparire nell'albero della frusta")},
    "vocations": {
        "en": ('Vocations',
               'all 12 vocations available at Alltrades Abbey from the start'),
        "fr": ('Vocations',
               "les 12 vocations disponibles à l'Abbaye des Vocations dès le "
               'début'),
        "de": ('Berufungen',
               'alle 12 Berufungen von Anfang an in der Allesneu-Abtei '
               'verfügbar'),
        "es": ('Vocaciones',
               'las 12 vocaciones disponibles en la Abadía Vocationis desde el'
               ' principio'),
        "it": ('Vocazioni',
               "tutte le 12 vocazioni disponibili all'Abbazia Mutationis fin "
               "dall'inizio")},
    "vocations_embauche": {
        "en": ('random vocation for recruits',
               "companions created at Patty's get a random vocation"),
        "fr": ('vocation des recrues au hasard',
               'les compagnons créés chez Tulipe reçoivent une vocation au '
               'hasard'),
        "de": ('zufällige Berufung für Gefährten',
               'bei Hilda erstellte Gefährten erhalten eine zufällige Berufung'),
        "es": ('vocación aleatoria para los reclutas',
               'los compañeros creados con Petricia reciben una vocación '
               'aleatoria'),
        "it": ('vocazione casuale per le reclute',
               'i compagni creati da Patty ricevono una vocazione casuale')},
    "vocation_depart": {
        "en": ('random vocation for the hero',
               'new game only; it shows after the prologue'),
        "fr": ('vocation du héros au hasard',
               'nouvelle partie uniquement ; elle apparaît après le prologue'),
        "de": ('zufällige Berufung für den Helden',
               'nur bei einem neuen Spiel; sie ist nach dem Prolog sichtbar'),
        "es": ('vocación aleatoria para el héroe',
               'solo en una partida nueva; se ve después del prólogo'),
        "it": ("vocazione casuale per l'eroe",
               'solo in una nuova partita; si vede dopo il prologo')},
    "vocations_bloquees": {
        "en": ('locked vocations',
               'no one can change vocation at the abbey, but revocation is '
               'still allowed (not in any preset)'),
        "fr": ('vocations bloquées',
               "impossible de changer de vocation à l'abbaye, mais la "
               'renouvocation reste permise (hors préréglages)'),
        "de": ('gesperrte Berufungen',
               'in der Abtei kann niemand die Berufung wechseln, der Neubeginn'
               ' bleibt aber erlaubt (in keiner Voreinstellung)'),
        "es": ('vocaciones bloqueadas',
               'nadie puede cambiar de vocación en la abadía, pero la '
               'revocación sigue permitida (fuera de los preajustes)'),
        "it": ('vocazioni bloccate',
               "nessuno può cambiare vocazione all'abbazia, ma la rivocazione "
               'resta possibile (fuori dalle preimpostazioni)')},
    "stats": {
        "en": ('Monster stats (experimental)',
               'HP, attack, defence, experience and gold are swapped between '
               'all monsters, bosses included'),
        "fr": ('Statistiques des monstres (expérimental)',
               'PV, attaque, défense, expérience et or sont échangés entre '
               'tous les monstres, boss compris'),
        "de": ('Monsterwerte (experimentell)',
               'LP, Angriff, Verteidigung, Erfahrung und Gold werden zwischen '
               'allen Monstern getauscht, Bosse eingeschlossen'),
        "es": ('Estadísticas de los monstruos (experimental)',
               'PV, ataque, defensa, experiencia y oro se intercambian entre '
               'todos los monstruos, jefes incluidos'),
        "it": ('Statistiche dei mostri (sperimentale)',
               'PV, attacco, difesa, esperienza e oro vengono scambiati tra '
               'tutti i mostri, boss compresi')},

    # --- la sortie -------------------------------------------------------
    "sortie": {
        "en": 'Output',
        "fr": 'Sortie',
        "de": 'Ausgabe',
        "es": 'Salida',
        "it": 'Uscita'},
    "case_patch": {
        "en": 'Also create an .xdelta patch (to share this seed without '
              'sharing the ROM)',
        "fr": 'Créer aussi un patch .xdelta (pour partager cette graine sans '
              'partager la ROM)',
        "de": 'Zusätzlich einen .xdelta-Patch erstellen (um diesen Seed ohne '
              'die ROM zu teilen)',
        "es": 'Crear también un parche .xdelta (para compartir esta semilla '
              'sin compartir la ROM)',
        "it": 'Crea anche una patch .xdelta (per condividere questo seed senza'
              ' condividere la ROM)'},
    "xdelta_cherche": {
        "en": 'looking for xdelta3...',
        "fr": 'recherche de xdelta3...',
        "de": 'xdelta3 wird gesucht...',
        "es": 'buscando xdelta3...',
        "it": 'ricerca di xdelta3 in corso...'},
    "xdelta_trouve": {
        "en": 'xdelta3 found: %s',
        "fr": 'xdelta3 trouvé : %s',
        "de": 'xdelta3 gefunden: %s',
        "es": 'xdelta3 encontrado: %s',
        "it": 'xdelta3 trovato: %s'},
    "xdelta_absent": {
        "en": 'xdelta3 not found: put xdelta3.exe next to this application to '
              'enable this option. Sharing the seed works too.',
        "fr": 'xdelta3 introuvable : placez xdelta3.exe à côté de '
              "l'application pour activer cette option. Partager la graine "
              'fonctionne aussi.',
        "de": 'xdelta3 nicht gefunden: Lege xdelta3.exe neben dieses Programm,'
              ' um die Option zu aktivieren. Den Seed zu teilen, funktioniert '
              'auch.',
        "es": 'No se encontró xdelta3: pon xdelta3.exe junto a esta aplicación'
              ' para activar esta opción. Compartir la semilla también '
              'funciona.',
        "it": 'xdelta3 non trovato: metti xdelta3.exe accanto a questa '
              "applicazione per attivare l'opzione. Anche condividere il seed "
              'funziona.'},
    "dossier_defaut": {
        "en": 'The randomized ROM will be saved next to your ROM.',
        "fr": 'La ROM randomisée sera enregistrée à côté de votre ROM.',
        "de": 'Die randomisierte ROM wird neben deiner ROM gespeichert.',
        "es": 'La ROM aleatorizada se guardará junto a tu ROM.',
        "it": 'La ROM randomizzata verrà salvata accanto alla tua ROM.'},
    "dossier": {
        "en": 'The randomized ROM will be saved in %s',
        "fr": 'La ROM randomisée sera enregistrée dans %s',
        "de": 'Die randomisierte ROM wird gespeichert in: %s',
        "es": 'La ROM aleatorizada se guardará en %s',
        "it": 'La ROM randomizzata verrà salvata in %s'},

    # --- l'action --------------------------------------------------------
    "lancer": {
        "en": 'Randomize',
        "fr": 'Randomiser',
        "de": 'Randomisieren',
        "es": 'Aleatorizar',
        "it": 'Randomizza'},
    "travail": {
        "en": 'Working...',
        "fr": 'En cours...',
        "de": 'Läuft...',
        "es": 'Trabajando...',
        "it": 'In corso...'},
    "graine_invalide": {
        "en": 'The seed must be a whole number.',
        "fr": 'La graine doit être un nombre entier.',
        "de": 'Der Seed muss eine ganze Zahl sein.',
        "es": 'La semilla debe ser un número entero.',
        "it": 'Il seed deve essere un numero intero.'},
    "rien_coche": {
        "en": 'Nothing is selected to randomize.',
        "fr": "Aucune option n'est cochée.",
        "de": 'Es ist keine Option ausgewählt.',
        "es": 'No hay ninguna opción seleccionada.',
        "it": 'Non è selezionata nessuna opzione.'},
    "existe_deja": {
        "en": '%s already exists.\nOverwrite it?',
        "fr": '%s existe déjà.\nLe remplacer ?',
        "de": '%s existiert bereits.\nÜberschreiben?',
        "es": '%s ya existe.\n¿Quieres sobrescribirlo?',
        "it": '%s esiste già.\nVuoi sovrascriverlo?'},
    "incomplet_efface": {
        "en": 'incomplete file deleted: %s',
        "fr": 'fichier incomplet supprimé : %s',
        "de": 'unvollständige Datei gelöscht: %s',
        "es": 'archivo incompleto eliminado: %s',
        "it": 'file incompleto eliminato: %s'},
    "fini": {
        "en": 'Done: %s',
        "fr": 'Terminé : %s',
        "de": 'Fertig: %s',
        "es": 'Listo: %s',
        "it": 'Fatto: %s'},
    "prete": {
        "en": 'Your randomized ROM is ready:\n\n%s\n\nOpen the folder?',
        "fr": 'Votre ROM randomisée est prête :\n\n%s\n\nOuvrir le dossier ?',
        "de": 'Deine randomisierte ROM ist fertig:\n\n%s\n\nOrdner öffnen?',
        "es": 'Tu ROM aleatorizada está lista:\n\n%s\n\n¿Abrir la carpeta?',
        "it": 'La tua ROM randomizzata è pronta:\n\n%s\n\nAprire la cartella?'},
    "echec": {
        "en": 'FAILED',
        "fr": 'ÉCHEC',
        "de": 'FEHLGESCHLAGEN',
        "es": 'ERROR',
        "it": 'ERRORE'},
    "echec_court": {
        "en": 'Failed.',
        "fr": 'Échec.',
        "de": 'Fehlgeschlagen.',
        "es": 'Ha fallado.',
        "it": 'Operazione non riuscita.'},
    "annule": {
        "en": 'cancelled',
        "fr": 'annulé',
        "de": 'abgebrochen',
        "es": 'cancelado',
        "it": 'annullato'},
}

# L'ordre des cases dans la fenetre : (cle, retrait).
# LES ONGLETS DE LA FENETRE (ZER-64) : (cle du titre, cases), chaque case
# (cle, retrait). La cle d'une case est le nom de sa variable dans
# l'interface. Les modes d'apparition (`APPARITIONS`) sont des boutons radio,
# poses en tete de l'onglet des monstres, sous la case `monstres`.
ONGLETS = (
    ("onglet_monstres", (("monstres", 0), ("groupes", 1), ("stats", 0),
                         ("sorts_monstres", 0), ("sorts_monstres_ajout", 1),
                         ("techniques_monstres", 0),
                         ("techniques_monstres_ajout", 1))),
    ("onglet_boss", (("boss", 0), ("garder_hexacorne", 1),
                     ("boss_familles_egales", 1), ("boss_histoire", 1),
                     ("boss_mixte", 1), ("boss_chaque_combat", 1),
                     ("boss_terrain", 0))),
    ("onglet_objets", (("objets", 0), ("sans_consommables", 1),
                       ("objets_chaos", 1), ("rouges_libres", 1),
                       ("butin", 0), ("butin_libre", 1),
                       ("boutiques", 0), ("prix_libres", 1),
                       ("boutiques_chaos", 1))),
    ("onglet_equipe", (("sorts", 0), ("sorts_chaos", 1), ("aptitudes", 0),
                       ("aptitudes_chaos", 1), ("aptitudes_arme_origine", 1),
                       ("vocations", 0), ("vocations_embauche", 1),
                       ("vocation_depart", 1), ("vocations_bloquees", 1))),
)
CASES = tuple(c for _o, cases in ONGLETS for c in cases)
APPARITIONS = ("aleatoire", "zone", "globale")


def texte(cle, langue, *args):
    """Le texte `cle` dans `langue`, l'anglais a defaut, formate par `args`."""
    t = T[cle].get(langue) or T[cle]["en"]
    return (t % args) if args else t


def langue_systeme():
    """La langue de l'interface de Windows, si c'est l'une des cinq ; sinon
    celle de la locale ; sinon l'anglais."""
    try:
        import ctypes
        lid = ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF
        code = {0x09: "en", 0x0C: "fr", 0x07: "de", 0x0A: "es", 0x10: "it"}.get(lid)
        if code:
            return code
    except Exception:
        pass
    try:
        import locale
        loc = (locale.getlocale()[0] or "").lower()
        for code in CODES:
            if loc.startswith(code):
                return code
        for code, mot in (("fr", "french"), ("de", "german"), ("es", "spanish"),
                          ("it", "italian")):
            if mot in loc:
                return code
    except Exception:
        pass
    return "en"


def verifier():
    """Chaque cle dans les cinq langues, chaque case avec (libelle, detail),
    et les memes %s partout. Rend la liste des defauts (vide si tout va)."""
    defauts = []
    for cle, trad in T.items():
        manque = [c for c in CODES if c not in trad]
        if manque:
            defauts.append("%s : pas de %s" % (cle, ", ".join(manque)))
            continue
        ref = trad["en"]
        for c in CODES:
            t = trad[c]
            if isinstance(ref, tuple) != isinstance(t, tuple):
                defauts.append("%s/%s : forme differente de l'anglais" % (cle, c))
            elif not isinstance(ref, tuple) and t.count("%s") != ref.count("%s"):
                defauts.append("%s/%s : nombre de %%s different" % (cle, c))
    for cle, _r in CASES:
        if cle not in T or not isinstance(T[cle]["en"], tuple):
            defauts.append("case %s : pas de (libelle, detail)" % cle)
    for mode in APPARITIONS:
        if "app_" + mode not in T:
            defauts.append("mode d'apparition %s : pas de texte" % mode)
    for onglet, _c in ONGLETS:
        if onglet not in T:
            defauts.append("onglet %s : pas de titre" % onglet)
    return defauts


if __name__ == "__main__":
    d = verifier()
    print("\n".join(d) if d else "%d cles, 5 langues : ok" % len(T))
