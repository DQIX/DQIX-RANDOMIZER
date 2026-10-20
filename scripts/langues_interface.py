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
               '(monsters in random mode only)'),
        "fr": ('monstres en groupe',
               'un monstre tiré au hasard vient avec des compagnons, comme '
               'dans le jeu de base (monstres en mode aléatoire seulement)'),
        "de": ('Monster in Gruppen',
               'ein zufälliges Monster bringt Begleiter mit, wie im '
               'Originalspiel (nur mit Monstern im Zufallsmodus)'),
        "es": ('monstruos en grupo',
               'un monstruo al azar trae compañeros, como en el juego original '
               '(solo con monstruos en modo aleatorio)'),
        "it": ('mostri in gruppo',
               'un mostro casuale porta compagni, come nel gioco originale '
               '(solo con mostri in modalità casuale)')},
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
    "equilibrer_conso": {
        "en": ('balance equipment and consumables',
               'about a third of herbs, potions and seeds in chests, pots and '
               'grottos; unticked, a plain draw over every item (about 6 '
               'pieces of equipment per consumable)'),
        "fr": ('équilibrer équipement et consommables',
               "environ un tiers d'herbes, de potions et de graines dans les "
               'coffres, les pots et les grottes ; décochée, un tirage simple '
               'parmi tous les objets (environ 6 équipements pour 1 '
               'consommable)'),
        "de": ('Ausrüstung und Verbrauchsgegenstände ausgleichen',
               'etwa ein Drittel Kräuter, Tränke und Samen in Truhen, Töpfen '
               'und Grotten; ohne Haken eine reine Zufallsziehung über alle '
               'Gegenstände (etwa 6 Ausrüstungsteile pro '
               'Verbrauchsgegenstand)'),
        "es": ('equilibrar equipo y consumibles',
               'alrededor de un tercio de hierbas, pociones y semillas en '
               'cofres, vasijas y grutas; sin marcar, un sorteo simple entre '
               'todos los objetos (unas 6 piezas de equipo por consumible)'),
        "it": ('bilanciare equipaggiamento e consumabili',
               'circa un terzo di erbe, pozioni e semi in forzieri, vasi e '
               'grotte; senza spunta, estrazione semplice tra tutti gli '
               'oggetti (circa 6 equipaggiamenti per consumabile)')},
    "objets_chaos": {
        "en": ('rare items everywhere',
               'legendary gear can turn up in the very first barrel, grottos '
               'and red chests included; unticked, each container follows '
               'its rank'),
        "fr": ('objets rares partout',
               'un équipement légendaire peut se trouver dès le premier '
               'tonneau, grottes et coffres rouges compris ; décochée, chaque '
               'conteneur suit son rang'),
        "de": ('seltene Gegenstände überall',
               'legendäre Ausrüstung kann schon im ersten Fass liegen, '
               'Grotten und rote Truhen inbegriffen; ohne Haken folgt jeder '
               'Behälter seinem Rang'),
        "es": ('objetos raros por todas partes',
               'puede haber equipo legendario ya en el primer barril, grutas '
               'y cofres rojos incluidos; sin marcar, cada contenedor sigue '
               'su rango'),
        "it": ('oggetti rari ovunque',
               'un equipaggiamento leggendario può trovarsi già nel primo '
               'barile, grotte e forzieri rossi compresi; senza spunta, ogni '
               'contenitore segue il suo rango')},
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
        "en": ('Monster spells',
               'the spells a monster knows are picked at random among the 53 '
               'battle spells, in every battle (or once for the whole game '
               'with the fixed kit below)'),
        "fr": ('Sorts des monstres',
               'les sorts que connaît un monstre sont tirés au hasard parmi '
               'les 53 sorts de combat, à chaque combat (ou une fois pour '
               'toute la partie avec le kit fixe plus bas)'),
        "de": ('Monsterzauber',
               'die Zauber eines Monsters werden zufällig aus den 53 '
               'Kampfzaubern gewählt, in jedem Kampf (oder einmal für das '
               'ganze Spiel mit dem festen Satz unten)'),
        "es": ('Hechizos de monstruos',
               'los hechizos de un monstruo se eligen al azar entre los 53 '
               'hechizos de combate, en cada combate (o una vez para toda la '
               'partida con el kit fijo de abajo)'),
        "it": ('Magie dei mostri',
               'le magie di un mostro vengono scelte a caso tra le 53 magie '
               'di battaglia, a ogni battaglia (o una volta per tutta la '
               'partita con il kit fisso qui sotto)')},
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
        "en": ('Monster abilities',
               "a monster's abilities are picked at random among those of "
               "monsters and heroes, with their real animation: in every "
               "battle, or once for the whole game with the fixed kit "
               "below"),
        "fr": ('Techniques des monstres',
               "les techniques d'un monstre sont tirées au hasard parmi celles "
               'des monstres et des héros, avec leur vraie animation : à '
               'chaque combat, ou une fois pour toute la partie avec le kit '
               'fixe plus bas'),
        "de": ('Monsterfähigkeiten',
               'die Fähigkeiten eines Monsters werden zufällig aus denen der '
               'Monster und Helden gewählt: in jedem Kampf mit ihrer echten '
               'Animation, oder einmal für das ganze Spiel mit dem festen '
               'Satz unten'),
        "es": ('Habilidades de monstruos',
               'las habilidades de un monstruo se eligen al azar entre las de '
               'monstruos y héroes: en cada combate con su animación real, o '
               'una vez para toda la partida con el kit fijo de abajo'),
        "it": ('Abilità dei mostri',
               "le abilità di un mostro vengono scelte a caso tra quelle di "
               "mostri ed eroi: a ogni battaglia con la loro vera animazione, "
               "o una volta per tutta la partita con il kit fisso qui sotto")},
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
    "actions_fixes": {
        "en": ('a fixed kit for each monster',
               'spells and abilities drawn once, when the ROM is built: every '
               'slime has the same kit for the whole game, abilities with '
               'their real animation'),
        "fr": ('un kit fixe pour chaque monstre',
               'sorts et techniques tirés une fois, à la création de la ROM : '
               'tous les gluants ont le même kit toute la partie, techniques '
               'avec leur vraie animation'),
        "de": ('ein fester Satz für jedes Monster',
               'Zauber und Fähigkeiten werden einmal beim Erstellen des ROMs '
               'gewählt: jeder Schleim hat das ganze Spiel denselben Satz, '
               'Fähigkeiten mit ihrer echten Animation'),
        "es": ('un kit fijo para cada monstruo',
               'hechizos y habilidades elegidos una vez, al crear la ROM: '
               'todos los limos tienen el mismo kit toda la partida, las '
               'habilidades con su animación real'),
        "it": ('un kit fisso per ogni mostro',
               "magie e abilità scelte una volta, alla creazione della ROM: "
               "tutti gli slime hanno lo stesso kit per tutta la partita, le "
               "abilità con la loro vera animazione")},
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
    # A PARTIR DE QUEL BOSS (ZER-80) : deux listes deroulantes.
    "seuil_grottes": {
        "en": ('grotto bosses from',
               'before this story boss, story fights never get a grotto boss '
               '(grotto and legacy boss fights are not limited)'),
        "fr": ('boss des grottes à partir de',
               "avant ce boss de l'histoire, aucun combat de l'histoire ne "
               'reçoit un boss des grottes (les combats de boss des grottes '
               'et des légendes ne sont pas concernés)'),
        "de": ('Grottenbosse ab',
               'vor diesem Story-Boss bekommt kein Story-Kampf einen '
               'Grottenboss (Boss-Kämpfe in Grotten und Legenden sind nicht '
               'betroffen)'),
        "es": ('jefes de las grutas desde',
               'antes de este jefe de la historia, ningún combate de la '
               'historia recibe un jefe de las grutas (los combates de jefes '
               'de las grutas y legendarios no cambian)'),
        "it": ('boss delle grotte da',
               'prima di questo boss della storia, nessuno scontro della '
               'storia riceve un boss delle grotte (gli scontri con i boss '
               'delle grotte e leggendari non cambiano)')},
    "seuil_legendes": {
        "en": ('legacy bosses from',
               'before this story boss, story fights never get a legacy boss '
               '(grotto and legacy boss fights are not limited)'),
        "fr": ('boss des légendes à partir de',
               "avant ce boss de l'histoire, aucun combat de l'histoire ne "
               'reçoit un boss des légendes (les combats de boss des grottes '
               'et des légendes ne sont pas concernés)'),
        "de": ('Legendenbosse ab',
               'vor diesem Story-Boss bekommt kein Story-Kampf einen '
               'Legendenboss (Boss-Kämpfe in Grotten und Legenden sind nicht '
               'betroffen)'),
        "es": ('jefes legendarios desde',
               'antes de este jefe de la historia, ningún combate de la '
               'historia recibe un jefe legendario (los combates de jefes de '
               'las grutas y legendarios no cambian)'),
        "it": ('boss leggendari da',
               'prima di questo boss della storia, nessuno scontro della '
               'storia riceve un boss leggendario (gli scontri con i boss '
               'delle grotte e leggendari non cambiano)')},
    "seuil_debut": {
        "en": 'the start', "fr": 'le début', "de": 'Anfang',
        "es": 'el principio', "it": "l'inizio"},
    "seuil_jamais": {
        "en": 'never', "fr": 'jamais', "de": 'nie', "es": 'nunca',
        "it": 'mai'},
    "boss_legacy_tous": {
        "en": ('all three legacy boss levels (they will come out much more often)',
               'legacy bosses can come out at levels 2 and 3 too (by default, '
               'level 1 only)'),
        "fr": ('les trois niveaux des boss des légendes (ils sortiront beaucoup plus souvent)',
               'les boss des légendes peuvent aussi sortir aux niveaux 2 et 3 '
               '(par défaut, niveau 1 seulement)'),
        "de": ('alle drei Stufen der Legendenbosse (sie erscheinen viel häufiger)',
               'Legendenbosse können auch auf Stufe 2 und 3 erscheinen '
               '(standardmäßig nur Stufe 1)'),
        "es": ('los tres niveles de los jefes legendarios (saldrán mucho más a menudo)',
               'los jefes legendarios también pueden salir en los niveles 2 y '
               '3 (por defecto, solo el nivel 1)'),
        "it": ('tutti e tre i livelli dei boss leggendari (usciranno molto più spesso)',
               'i boss leggendari possono uscire anche ai livelli 2 e 3 '
               '(di base, solo il livello 1)')},
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
               'after a defeat (monsters in random mode only)'),
        "fr": ('nouveau boss à chaque essai',
               "un autre boss est tiré chaque fois qu'on entre dans le "
               'combat, par exemple après une défaite (monstres en mode aléatoire seulement)'),
        "de": ('neuer Boss bei jedem Versuch',
               'bei jedem Betreten des Kampfes, z. B. nach einer Niederlage, '
               'wird ein anderer Boss gezogen (nur mit Monstern im Zufallsmodus)'),
        "es": ('jefe nuevo en cada intento',
               'se sortea otro jefe cada vez que entras en el combate, por '
               'ejemplo tras una derrota (solo con monstruos en modo aleatorio)'),
        "it": ('nuovo boss a ogni tentativo',
               'viene estratto un altro boss ogni volta che entri nello '
               'scontro, per esempio dopo una sconfitta (solo con mostri in modalità casuale)')},
    "boss_terrain": {
        "en": ('Bosses on the field (experimental)',
               'only 14 bosses (those that already roam the grottoes) can '
               'wander the map like monsters; may be buggy (monsters in '
               'random mode only)'),
        "fr": ('Boss sur le terrain (expérimental)',
               'seuls 14 boss (ceux qui rôdent déjà dans les antres) peuvent '
               'se promener sur la carte comme des monstres ; peut être bugué '
               '(monstres en mode aléatoire seulement)'),
        "de": ('Bosse im Gelände (experimentell)',
               'nur 14 Bosse (die schon in den Grotten umherstreifen) können '
               'wie Monster über die Karte streifen; kann fehlerhaft sein '
               '(nur mit Monstern im Zufallsmodus)'),
        "es": ('Jefes en el mapa (experimental)',
               'solo 14 jefes (los que ya rondan las grutas) pueden deambular '
               'por el mapa como monstruos; puede tener fallos (solo con '
               'monstruos en modo aleatorio)'),
        "it": ('Boss sul campo (sperimentale)',
               'solo 14 boss (quelli che già si aggirano nelle grotte) possono '
               'girare sulla mappa come mostri; può avere bug (solo con mostri '
               'in modalità casuale)')},
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
        "en": ('Monster stats',
               'HP, MP, attack, defence, agility and resistances drawn, '
               'bosses in their own option (Bosses tab); each stat between x0.5 and x2 of its value '
               '(a slime with 8 HP: 4 to 16), each resistance one step away '
               'at most. The prologue fight never changes'),
        "fr": ('Statistiques des monstres',
               'PV, PM, attaque, défense, agilité et résistances tirés, boss '
               "à part (onglet Boss) ; chaque stat entre x0,5 et x2 de sa valeur (un gluant "
               "à 8 PV : 4 à 16), chaque résistance à un cran près. Le combat "
               "du prologue ne change jamais"),
        "de": ('Monsterwerte',
               'LP, MP, Angriff, Verteidigung, Beweglichkeit und Resistenzen '
               'gezogen, Bosse separat (Reiter Bosse); jeder Wert zwischen x0,5 und '
               'x2 seines Werts (ein Schleim mit 8 LP: 4 bis 16), jede '
               'Resistenz höchstens eine Stufe daneben. Der Prolog-Kampf '
               'ändert sich nie'),
        "es": ('Estadísticas de los monstruos',
               'PV, PM, ataque, defensa, agilidad y resistencias sorteados, '
               'jefes aparte (pestaña Jefes); cada estadística entre x0,5 y x2 de su valor '
               '(un limo con 8 PV: de 4 a 16), cada resistencia a un nivel '
               'como mucho. El combate del prólogo nunca cambia'),
        "it": ('Statistiche dei mostri',
               'PV, PM, attacco, difesa, agilità e resistenze estratti, boss '
               'a parte (scheda Boss); ogni statistica tra x0,5 e x2 del suo valore (uno '
               'slime con 8 PV: da 4 a 16), ogni resistenza a un livello al '
               'massimo. Il combattimento del prologo non cambia mai')},
    "stats_chaos": {
        "en": ('chaos stats',
               'each stat drawn over its whole range, whatever its value. '
               'Monsters: HP 4-1477, MP 0-255, attack 9-748, defence 6-798, '
               'agility 7-505. Bosses: HP 93-8500, MP 18-255, attack 30-900, '
               'defence 22-637, agility 11-375. Resistances anywhere on '
               'their scale'),
        "fr": ('stats en chaos',
               'chaque stat tirée sur toute sa plage, sans regarder sa valeur. '
               'Monstres : PV 4-1477, PM 0-255, attaque 9-748, défense 6-798, '
               'agilité 7-505. Boss : PV 93-8500, PM 18-255, attaque 30-900, '
               'défense 22-637, agilité 11-375. Résistances n\'importe où sur '
               'leur échelle'),
        "de": ('Werte im Chaos',
               'jeder Wert über seinen ganzen Bereich gezogen, egal wie hoch '
               'er war. Monster: LP 4-1477, MP 0-255, Angriff 9-748, '
               'Verteidigung 6-798, Beweglichkeit 7-505. Bosse: LP 93-8500, '
               'MP 18-255, Angriff 30-900, Verteidigung 22-637, '
               'Beweglichkeit 11-375. Resistenzen beliebig auf ihrer Skala'),
        "es": ('estadísticas en caos',
               'cada estadística sorteada en todo su rango, sin mirar su '
               'valor. Monstruos: PV 4-1477, PM 0-255, ataque 9-748, defensa '
               '6-798, agilidad 7-505. Jefes: PV 93-8500, PM 18-255, ataque '
               '30-900, defensa 22-637, agilidad 11-375. Resistencias en '
               'cualquier punto de su escala'),
        "it": ('statistiche nel caos',
               'ogni statistica estratta su tutto il suo intervallo, senza '
               'guardare il suo valore. Mostri: PV 4-1477, PM 0-255, attacco '
               '9-748, difesa 6-798, agilità 7-505. Boss: PV 93-8500, PM '
               '18-255, attacco 30-900, difesa 22-637, agilità 11-375. '
               'Resistenze ovunque sulla loro scala')},
    "stats_combat": {
        "en": ('drawn again at every battle',
               'HP, MP, attack, defence and agility are drawn again in their '
               'range at the start of every battle (two slimes of the same '
               'battle share them); resistances stay those of the ROM'),
        "fr": ('retirées à chaque combat',
               'PV, PM, attaque, défense et agilité sont retirés dans leur '
               'plage au début de chaque combat (deux gluants du même combat '
               'les partagent) ; les résistances restent celles de la ROM'),
        "de": ('bei jedem Kampf neu gezogen',
               'LP, MP, Angriff, Verteidigung und Beweglichkeit werden zu '
               'Beginn jedes Kampfes in ihrem Bereich neu gezogen (zwei '
               'Schleime desselben Kampfes teilen sie); die Resistenzen '
               'bleiben die der ROM'),
        "es": ('sorteadas en cada combate',
               'PV, PM, ataque, defensa y agilidad se vuelven a sortear en su '
               'rango al empezar cada combate (dos limos del mismo combate '
               'los comparten); las resistencias siguen siendo las de la ROM'),
        "it": ('estratte a ogni combattimento',
               'PV, PM, attacco, difesa e agilità vengono riestratti nel loro '
               'intervallo all\'inizio di ogni combattimento (due slime dello '
               'stesso combattimento li condividono); le resistenze restano '
               'quelle della ROM')},
    "stats_boss": {
        "en": ('Boss stats',
               'HP, MP, attack, defence, agility and resistances of the bosses '
               'drawn, each stat between x0.5 and x2 of its value, each '
               'resistance one step away at most. The prologue fight and '
               'Aquila and Corvus of the cutscenes never change'),
        "fr": ('Statistiques des boss',
               'PV, PM, attaque, défense, agilité et résistances des boss '
               'tirés, chaque stat entre x0,5 et x2 de sa valeur, chaque '
               'résistance à un cran près. Le combat du prologue et Aquila et '
               'Corvus des cinématiques ne changent jamais'),
        "de": ('Bosswerte',
               'LP, MP, Angriff, Verteidigung, Beweglichkeit und Resistenzen '
               'der Bosse gezogen, jeder Wert zwischen x0,5 und x2 seines '
               'Werts, jede Resistenz höchstens eine Stufe daneben. Der '
               'Prolog-Kampf und Aquila und Corvus der Zwischensequenzen '
               'ändern sich nie'),
        "es": ('Estadísticas de los jefes',
               'PV, PM, ataque, defensa, agilidad y resistencias de los jefes '
               'sorteados, cada estadística entre x0,5 y x2 de su valor, cada '
               'resistencia a un nivel como mucho. El combate del prólogo y '
               'Aquila y Corvus de las escenas nunca cambian'),
        "it": ('Statistiche dei boss',
               'PV, PM, attacco, difesa, agilità e resistenze dei boss '
               'estratti, ogni statistica tra x0,5 e x2 del suo valore, ogni '
               'resistenza a un livello al massimo. Il combattimento del '
               'prologo e Aquila e Corvus dei filmati non cambiano mai')},
    "stats_boss_chaos": {
        "en": ('chaos boss stats',
               'each stat drawn over the whole range of the bosses: HP '
               '93-8500, MP 18-255, attack 30-900, defence 22-637, agility '
               '11-375; resistances anywhere on their scale'),
        "fr": ('stats des boss en chaos',
               'chaque stat tirée sur toute la plage des boss : PV 93-8500, '
               'PM 18-255, attaque 30-900, défense 22-637, agilité 11-375 ; '
               "résistances n'importe où sur leur échelle"),
        "de": ('Bosswerte im Chaos',
               'jeder Wert über den ganzen Bereich der Bosse gezogen: LP '
               '93-8500, MP 18-255, Angriff 30-900, Verteidigung 22-637, '
               'Beweglichkeit 11-375; Resistenzen beliebig auf ihrer Skala'),
        "es": ('estadísticas de jefes en caos',
               'cada estadística sorteada en todo el rango de los jefes: PV '
               '93-8500, PM 18-255, ataque 30-900, defensa 22-637, agilidad '
               '11-375; resistencias en cualquier punto de su escala'),
        "it": ('statistiche dei boss nel caos',
               "ogni statistica estratta su tutto l'intervallo dei boss: PV "
               '93-8500, PM 18-255, attacco 30-900, difesa 22-637, agilità '
               '11-375; resistenze ovunque sulla loro scala')},
    "stats_boss_combat": {
        "en": ('boss stats drawn again at every battle',
               'HP, MP, attack, defence and agility of a boss are drawn again '
               'in their range at the start of every battle; resistances stay '
               'those of the ROM'),
        "fr": ('stats des boss retirées à chaque combat',
               "PV, PM, attaque, défense et agilité d'un boss sont retirés "
               'dans leur plage au début de chaque combat ; les résistances '
               'restent celles de la ROM'),
        "de": ('Bosswerte bei jedem Kampf neu gezogen',
               'LP, MP, Angriff, Verteidigung und Beweglichkeit eines Bosses '
               'werden zu Beginn jedes Kampfes neu gezogen; die Resistenzen '
               'bleiben die der ROM'),
        "es": ('estadísticas de jefes sorteadas en cada combate',
               'PV, PM, ataque, defensa y agilidad de un jefe se vuelven a '
               'sortear al empezar cada combate; las resistencias siguen '
               'siendo las de la ROM'),
        "it": ('statistiche dei boss estratte a ogni combattimento',
               'PV, PM, attacco, difesa e agilità di un boss vengono '
               "riestratti all'inizio di ogni combattimento; le resistenze "
               'restano quelle della ROM')},
    "points": {
        "en": ('Sparkly spots',
               'every sparkly spot gives another item, drawn from all items '
               '(never equipment nor a key item)'),
        "fr": ('Points brillants',
               'chaque point brillant donne un autre objet, tiré parmi tous '
               'les objets (jamais un équipement ni un objet important)'),
        "de": ('Glitzernde Stellen',
               'jede glitzernde Stelle gibt einen anderen Gegenstand, aus '
               'allen Gegenständen gezogen (nie Ausrüstung oder '
               'Schlüsselgegenstände)'),
        "es": ('Puntos brillantes',
               'cada punto brillante da otro objeto, sorteado entre todos los '
               'objetos (nunca equipo ni objetos clave)'),
        "it": ('Punti luccicanti',
               'ogni punto luccicante dà un altro oggetto, estratto fra tutti '
               'gli oggetti (mai equipaggiamento né oggetti chiave)')},
    "points_par_rang": {
        "en": ('close to the original',
               'an item within one star of the original one'),
        "fr": ("proches de l'origine",
               "un objet à une étoile près de celui d'origine"),
        "de": ('nah am Original',
               'ein Gegenstand mit höchstens einem Stern Unterschied zum '
               'ursprünglichen'),
        "es": ('cercanos al original',
               'un objeto a una estrella como mucho del original'),
        "it": ("vicini all'originale",
               "un oggetto a una stella al massimo da quello originale")},
    "alchimie": {
        "en": ('Alchemy ingredients',
               'every Krak Pot recipe keeps what it makes and how many of '
               'each, but asks for other items, drawn from all items'),
        "fr": ("Ingrédients de l'alchimie",
               "chaque recette de la Marmite garde ce qu'elle produit et ses "
               "quantités, mais demande d'autres objets, tirés parmi tous"),
        "de": ('Alchemie-Zutaten',
               'jedes Rezept des Alchemietopfs behält sein Ergebnis und die '
               'Mengen, verlangt aber andere Gegenstände, aus allen gezogen'),
        "es": ('Ingredientes de alquimia',
               'cada receta del caldero conserva lo que produce y las '
               'cantidades, pero pide otros objetos, elegidos entre todos'),
        "it": ("Ingredienti dell'alchimia",
               'ogni ricetta del calderone conserva ciò che produce e le '
               'quantità, ma chiede altri oggetti, scelti fra tutti')},
    "medailles": {
        "en": ("Cap'n Max Meddlin' rewards",
               'his ten milestones and his shop give other items, each '
               'within one star of the original; mini medals needed divided '
               'by 4 (they are rare once the loot is randomized)'),
        "fr": ('Récompenses du Capitaine Zac Amédaï',
               "ses dix paliers et sa boutique donnent d'autres objets, à une "
               'étoile près ; mini médailles demandées divisées par 4 (elles '
               'sont rares une fois le butin randomisé)'),
        "de": ('Belohnungen des Medaillen-Kapitäns',
               'seine zehn Stufen und sein Laden geben andere Gegenstände, '
               'auf einen Stern genau; benötigte Minimedaillen durch 4 '
               'geteilt (mit zufälliger Beute sind sie selten)'),
        "es": ('Recompensas del capitán de las minimedallas',
               'sus diez niveles y su tienda dan otros objetos, con una '
               'estrella de margen; minimedallas necesarias divididas entre 4 '
               '(son raras con el botín aleatorio)'),
        "it": ('Ricompense del capitano delle minimedaglie',
               'i suoi dieci traguardi e il suo negozio danno altri oggetti, '
               'con una stella di margine; minimedaglie richieste divise per '
               '4 (sono rare con il bottino casuale)')},
    "medailles_chaos": {
        "en": ('any item, no star limit',
               'otherwise each reward stays within one star of the original'),
        "fr": ("n'importe quel objet, sans limite d'étoiles",
               "sinon chaque récompense reste à une étoile de l'originale"),
        "de": ('jeder Gegenstand, ohne Sternegrenze',
               'sonst bleibt jede Belohnung auf einen Stern beim Original'),
        "es": ('cualquier objeto, sin límite de estrellas',
               'si no, cada recompensa queda a una estrella de la original'),
        "it": ('qualsiasi oggetto, senza limite di stelle',
               "altrimenti ogni ricompensa resta a una stella dall'originale")},
    "medailles_seuils_vanilla": {
        "en": ('original mini medal counts',
               '4 to 80 for the milestones, 3 to 20 in his shop, as in the '
               'original game'),
        "fr": ("nombres de mini médailles d'origine",
               '4 à 80 pour les paliers, 3 à 20 dans sa boutique, comme dans '
               'le jeu de base'),
        "de": ('ursprüngliche Medaillenzahlen',
               '4 bis 80 für die Stufen, 3 bis 20 im Laden, wie im '
               'Originalspiel'),
        "es": ('cantidades originales de minimedallas',
               '4 a 80 para los niveles, 3 a 20 en su tienda, como en el '
               'juego original'),
        "it": ('numeri originali di minimedaglie',
               "da 4 a 80 per i traguardi, da 3 a 20 nel negozio, come nel "
               'gioco originale')},

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
        "en": 'The randomized ROM will be saved next to your ROM, in a folder named after the seed.',
        "fr": 'La ROM randomisée sera enregistrée à côté de votre ROM, dans un dossier au nom de la graine.',
        "de": 'Die randomisierte ROM wird neben deiner ROM gespeichert, in einem Ordner mit dem Namen des Seeds.',
        "es": 'La ROM aleatorizada se guardará junto a tu ROM, en una carpeta con el nombre de la semilla.',
        "it": 'La ROM randomizzata verrà salvata accanto alla tua ROM, in una cartella con il nome del seed.'},
    "dossier": {
        "en": 'The randomized ROM will be saved in %s, in a folder named after the seed.',
        "fr": 'La ROM randomisée sera enregistrée dans %s, dans un dossier au nom de la graine.',
        "de": 'Die randomisierte ROM wird in %s gespeichert, in einem Ordner mit dem Namen des Seeds.',
        "es": 'La ROM aleatorizada se guardará en %s, en una carpeta con el nombre de la semilla.',
        "it": 'La ROM randomizzata verrà salvata in %s, in una cartella con il nome del seed.'},

    # --- l'action --------------------------------------------------------
    # le bouton depuis l'onglet « Creer sa ROM » (sa config seule)
    "lancer_perso": {
        "en": 'Build custom ROM', "fr": 'Créer la ROM personnalisée',
        "de": 'Eigene ROM erstellen', "es": 'Crear ROM personalizada',
        "it": 'Crea ROM personalizzata'},
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
    "modifier_rom": {
        "en": 'Change a randomized ROM...',
        "fr": 'Modifier une ROM randomisée...',
        "de": 'Randomisierte ROM ändern...',
        "es": 'Modificar una ROM aleatorizada...',
        "it": 'Modifica una ROM randomizzata...'},
    "modifier_titre": {
        "en": 'The randomized ROM to change (your save keeps working)',
        "fr": 'La ROM randomisée à modifier (votre sauvegarde continue)',
        "de": 'Die zu ändernde randomisierte ROM (dein Spielstand bleibt)',
        "es": 'La ROM aleatorizada que modificar (tu partida sigue)',
        "it": 'La ROM randomizzata da modificare (il salvataggio resta)'},
    "modifier_vanilla_dabord": {
        "en": 'First drop your original European ROM above: the new ROM is '
              'built from it.',
        "fr": "Déposez d'abord votre ROM d'origine (Europe) au-dessus : la "
              "nouvelle ROM est construite à partir d'elle.",
        "de": 'Lege zuerst oben dein europäisches Original-ROM ab: die neue '
              'ROM wird daraus gebaut.',
        "es": 'Primero deja arriba tu ROM original europea: la nueva ROM se '
              'construye a partir de ella.',
        "it": 'Prima trascina qui sopra la tua ROM originale europea: la '
              'nuova ROM viene costruita da quella.'},
    "modifier_sans_journal": {
        "en": 'No options found for this ROM: its log %s is missing or was '
              'made by an older version. Keep the log next to the ROM.',
        "fr": "Aucune option trouvée pour cette ROM : son journal %s manque "
              "ou vient d'une version plus ancienne. Gardez le journal à "
              "côté de la ROM.",
        "de": 'Keine Optionen für diese ROM gefunden: ihr Protokoll %s fehlt '
              'oder stammt von einer älteren Version. Lass das Protokoll '
              'neben der ROM.',
        "es": 'No se encontraron opciones para esta ROM: falta su registro '
              '%s o es de una versión anterior. Deja el registro junto a la '
              'ROM.',
        "it": 'Nessuna opzione trovata per questa ROM: il suo registro %s '
              'manca o viene da una versione precedente. Tieni il registro '
              'accanto alla ROM.'},
    "modifier_config": {
        "en": 'This ROM was made in Create your ROM: open its file %s in '
              'that tab, change it, and build again.',
        "fr": "Cette ROM vient de « Créer sa ROM » : ouvrez son fichier %s "
              "dans cet onglet, modifiez-le et reconstruisez.",
        "de": 'Diese ROM stammt aus „Eigene ROM erstellen": öffne ihre Datei '
              '%s in diesem Reiter, ändere sie und baue neu.',
        "es": 'Esta ROM viene de «Crear tu ROM»: abre su archivo %s en esa '
              'pestaña, modifícalo y vuelve a construir.',
        "it": 'Questa ROM viene da «Crea la tua ROM»: apri il suo file %s in '
              'quella scheda, modificalo e ricostruisci.'},
    "modifier_inconnus": {
        "en": 'Options not shown in this window, left out: %s',
        "fr": 'Options absentes de cette fenêtre, non reprises : %s',
        "de": 'Optionen, die dieses Fenster nicht kennt, ausgelassen: %s',
        "es": 'Opciones que esta ventana no muestra, omitidas: %s',
        "it": 'Opzioni non presenti in questa finestra, escluse: %s'},
    "modifier_pret": {
        "en": 'Changing %s: its seed and options are ticked. Change what you '
              'want and click Randomize: the ROM is replaced under the same '
              'name (the old one is kept as %s), so your save keeps working. '
              'What is already done in your game stays done.',
        "fr": "Modification de %s : sa graine et ses options sont cochées. "
              "Changez ce que vous voulez puis cliquez sur Randomiser : la ROM "
              "est remplacée sous le même nom (l'ancienne est gardée en %s), "
              "votre sauvegarde continue. Ce qui est déjà fait dans la partie "
              "le reste.",
        "de": 'Änderung von %s: Seed und Optionen sind angehakt. Ändere, was '
              'du willst, und klicke auf Randomisieren: die ROM wird unter '
              'demselben Namen ersetzt (die alte bleibt als %s), dein '
              'Spielstand bleibt. Was im Spiel schon erledigt ist, bleibt.',
        "es": 'Modificando %s: su semilla y sus opciones están marcadas. '
              'Cambia lo que quieras y pulsa Aleatorizar: la ROM se sustituye '
              'con el mismo nombre (la antigua se guarda como %s) y tu '
              'partida sigue. Lo ya hecho en la partida se queda.',
        "it": 'Modifica di %s: seme e opzioni sono spuntati. Cambia ciò che '
              'vuoi e clicca su Randomizza: la ROM viene sostituita con lo '
              "stesso nome (la vecchia resta come %s) e il salvataggio "
              'continua. Ciò che è già fatto nella partita resta fatto.'},
    "modifier_glisse": {
        "en": 'This ROM is randomized: now drop your original European ROM '
              '(its log no longer finds it), then the randomized one is '
              'changed.',
        "fr": "Cette ROM est randomisée : déposez maintenant votre ROM "
              "d'origine (Europe), que son journal ne retrouve plus ; la ROM "
              "randomisée sera modifiée ensuite.",
        "de": 'Diese ROM ist randomisiert: lege jetzt dein europäisches '
              'Original-ROM ab (ihr Protokoll findet es nicht mehr), danach '
              'wird die randomisierte geändert.',
        "es": 'Esta ROM está aleatorizada: deja ahora tu ROM original '
              'europea (su registro ya no la encuentra) y después se '
              'modificará la aleatorizada.',
        "it": 'Questa ROM è randomizzata: trascina ora la tua ROM originale '
              'europea (il suo registro non la trova più), poi quella '
              'randomizzata verrà modificata.'},
    "modifier_indice": {
        "en": 'To change a randomized ROM, its log (..._journal.txt) must be '
              'next to it, and it must have been made with this version of '
              'the application.',
        "fr": "Pour modifier une ROM randomisée, son journal "
              "(..._journal.txt) doit être à côté d'elle, et elle doit avoir "
              "été faite avec cette version de l'application.",
        "de": 'Um eine randomisierte ROM zu ändern, muss ihr Protokoll '
              '(..._journal.txt) daneben liegen und sie muss mit dieser '
              'Version der Anwendung erstellt worden sein.',
        "es": 'Para modificar una ROM aleatorizada, su registro '
              '(..._journal.txt) debe estar a su lado y debe haberse creado '
              'con esta versión de la aplicación.',
        "it": 'Per modificare una ROM randomizzata, il suo registro '
              '(..._journal.txt) deve stare accanto e deve essere stata '
              'creata con questa versione dell\'applicazione.'},
    "modifier_ancienne": {
        "en": 'This ROM was made by an older version: its seed (%s) is taken '
              'back, not its options. Tick the options you had chosen, '
              'change what you want and click Randomize. Shops, chests and '
              'other draws may differ from your ROM.',
        "fr": "Cette ROM vient d'une version plus ancienne : sa graine (%s) "
              "est reprise, pas ses options. Recochez les options que vous "
              "aviez choisies, changez ce que vous voulez et cliquez sur "
              "Randomiser. Boutiques, coffres et autres tirages peuvent "
              "différer de votre ROM.",
        "de": 'Diese ROM stammt aus einer älteren Version: ihr Seed (%s) wird '
              'übernommen, nicht ihre Optionen. Hake die damals gewählten '
              'Optionen an, ändere, was du willst, und klicke auf '
              'Randomisieren. Läden, Truhen und andere Ziehungen können '
              'abweichen.',
        "es": 'Esta ROM viene de una versión anterior: se recupera su semilla '
              '(%s), no sus opciones. Marca las opciones que habías elegido, '
              'cambia lo que quieras y pulsa Aleatorizar. Tiendas, cofres y '
              'otros sorteos pueden variar.',
        "it": 'Questa ROM viene da una versione precedente: il seme (%s) viene '
              'ripreso, non le opzioni. Spunta le opzioni che avevi scelto, '
              'cambia ciò che vuoi e clicca su Randomizza. Negozi, forzieri e '
              'altre estrazioni possono cambiare.'},
    "modifier_fini": {
        "en": '%s replaced (the old ROM: %s). Load your save as usual.',
        "fr": "%s remplacée (l'ancienne ROM : %s). Chargez votre sauvegarde "
              "comme d'habitude.",
        "de": '%s ersetzt (die alte ROM: %s). Lade deinen Spielstand wie '
              'gewohnt.',
        "es": '%s sustituida (la ROM antigua: %s). Carga tu partida como '
              'siempre.',
        "it": '%s sostituita (la vecchia ROM: %s). Carica il salvataggio '
              'come sempre.'},
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
                         ("stats_chaos", 1), ("stats_combat", 1),
                         ("sorts_monstres", 0), ("sorts_monstres_ajout", 1),
                         ("techniques_monstres", 0),
                         ("techniques_monstres_ajout", 1),
                         ("actions_fixes", 1))),
    ("onglet_boss", (("boss", 0), ("garder_hexacorne", 1),
                     ("boss_familles_egales", 1), ("boss_histoire", 1),
                     ("boss_legacy_tous", 1), ("seuil_grottes", 1),
                     ("seuil_legendes", 1), ("boss_mixte", 1),
                     ("boss_chaque_combat", 1), ("boss_terrain", 0),
                     ("stats_boss", 0), ("stats_boss_chaos", 1),
                     ("stats_boss_combat", 1))),
    ("onglet_objets", (("objets", 0), ("objets_chaos", 1),
                       ("rouges_libres", 1), ("equilibrer_conso", 1),
                       ("butin", 0), ("butin_libre", 1),
                       ("boutiques", 0), ("prix_libres", 1),
                       ("boutiques_chaos", 1), ("points", 0),
                       ("points_par_rang", 1), ("alchimie", 0),
                       ("medailles", 0), ("medailles_chaos", 1),
                       ("medailles_seuils_vanilla", 1))),
    ("onglet_equipe", (("sorts", 0), ("sorts_chaos", 1), ("aptitudes", 0),
                       ("aptitudes_chaos", 1), ("aptitudes_arme_origine", 1),
                       ("vocations", 0), ("vocations_embauche", 1),
                       ("vocation_depart", 1), ("vocations_bloquees", 1))),
)
CASES = tuple(c for _o, cases in ONGLETS for c in cases)
# LES LISTES DEROULANTES (ZER-80) : des cases de ONGLETS qui ne sont pas des
# cases a cocher.
LISTES = ("seuil_grottes", "seuil_legendes")

# LES 30 BOSS D'HISTOIRE, dans l'ordre de `categories_boss.ORDRE_HISTOIRE`,
# avec leur nom dans chaque langue du jeu (lus dans la ROM, mon_data_<l>).
NOMS_BOSS_HISTOIRE = {
    "en": ('Hexagoon', 'Wight Knight', 'Morag', "Ragin' Contagion",
           "Master of Nu'un", 'Lleviathan', 'Garth Goyle', 'Tyrantula',
           'Grand Lizzier', 'Dreadmaster', 'Larstastnaras', 'Gadrongo',
           'Greygnarl', 'Goreham-Hogg', 'Hootingham-Gore', 'Goresby-Purrvis',
           'King Godwyn', 'King Godwyn', 'Goreham-Hogg', 'Hootingham-Gore',
           'Goresby-Purrvis', 'Corvus', 'Barbarus', 'Corvus', 'Lleviathan',
           'Yore', 'Rover', 'King Godfrey', 'Tyrannosaura Wrecks', 'Nodoph'),
    "fr": ('Hexacorne', 'chevalier Karbon', 'Sylvane', 'Épidémon',
           'Blaisephème', 'Moby Pick', 'garde Gouille', 'Tyrantule',
           'Balthézard', 'Directueur', 'Larstastnaras', 'Gadrongo', 'Grizius',
           'général Mac Assin', 'général Mac Hulotte', 'général Mac Léo',
           'roi Govin de Klenfer', 'roi Govin de Klenfer',
           'général Mac Assin', 'général Mac Hulotte', 'général Mac Léo',
           'Corvus', 'Barbarus', 'Corvus', 'Moby Pick', 'Fourax', 'Médhor',
           'roi Godefroi de Klenfer', 'Tyrannamort', 'Atoner'),
    "de": ('Hexagoblin', 'Schwarze Ritter', 'Morag', 'Seine Pestilenz',
           'Luziferius', 'Leviatran', 'Gneisbeißer', 'Tyrantula',
           'Kommodore Waran', 'Grausige Pauker', 'Larstastnaras', 'Gadrongo',
           'Graugnarz', 'Hauptmann Grunz', 'Hauptmann Kauz', 'Hauptmann Katz',
           'König Gottfried', 'König Gottfried', 'Hauptmann Grunz',
           'Hauptmann Kauz', 'Hauptmann Katz', 'Corvus', 'Barbarus', 'Corvus',
           'Leviatran', 'Megrusalem', 'Lumpi', 'König Gottlieb',
           'Tyrannosaura Hex', 'Tatzel'),
    "es": ('Hexatauro', 'Caballero Oscuro', 'Morag', 'Pestilencia',
           'Andosiniestro', 'Leviatán', 'Gárgol', 'Tirántula', 'Draco',
           'Dire', 'Larstastnaras', 'Tejujú', 'Dragris', 'Teniente Schwein',
           'Teniente Eule', 'Teniente Katze', 'rey König', 'rey König',
           'Teniente Schwein', 'Teniente Eule', 'Teniente Katze', 'Luzbel',
           'Fafnir', 'Luzbel', 'Leviatán', 'Matasalén', 'Lindo Pulgoso',
           'rey Káiser', 'Cernunnas', 'Leonírico'),
    "it": ('Hexagon', "Cavaliere dell'Ombra", 'Morag', 'Epidemon',
           'Signore del Nulla', 'Baleviatan', 'Gran Goyle', 'Tirantula',
           'Draklin', 'Dyscyplos', 'Ynimiga', 'Gadrongo', 'Dragriphon',
           'Generale Soinos', 'Generale Gufus', 'Generale Pardus',
           'Imperatore Teufel', 'Imperatore Teufel', 'Generale Soinos',
           'Generale Gufus', 'Generale Pardus', 'Corvus', 'Barbarus',
           'Corvus', 'Baleviatan', 'Matsalem', 'Doggy', 'Re Goffredo',
           'Tirannosaura Lex', 'Nodoph'),
}
APPARITIONS = ("aleatoire", "zone", "globale")

# L'ONGLET « CREER SA ROM » (ZER-86) : l'affectation explicite, case par case.
# Les categories dans l'ordre de la maquette validee le 19/10/2026 ; seules
# celles de `config_rom.CATEGORIES` sont actives, les autres disent « bientot ».
CATEGORIES_CREER = ("boss", "boutiques", "coffres", "grottes", "points",
                    "alchimie",
                    "capitaine", "arbres", "sorts", "vocations", "monstres",
                    "butin", "stats", "actions")
T.update({
    "onglet_creer": {
        "en": 'Create your ROM', "fr": 'Créer sa ROM',
        "de": 'Eigene ROM', "es": 'Crea tu ROM', "it": 'Crea la tua ROM'},
    "creer_intro": {
        "en": 'Choose every case yourself: start from a draw or from the original game, change what you want, save it to share. From this tab, the button below builds THIS ROM (options from the other tabs do not count); from the other tabs, it uses their options.',
        "fr": 'Choisissez chaque case vous-même : partez d\'un tirage ou du jeu d\'origine, changez ce que vous voulez, enregistrez pour partager. Depuis cet onglet, le bouton du bas crée CETTE ROM (les options des autres onglets ne comptent pas) ; depuis les autres onglets, il suit leurs options.',
        "de": 'Wähle jedes Feld selbst: Starte mit einer Ziehung oder dem Originalspiel, ändere, was du willst, und speichere zum Teilen. Auf diesem Tab erstellt die Schaltfläche unten DIESE ROM (die Optionen der anderen Tabs zählen nicht); auf den anderen Tabs folgt sie deren Optionen.',
        "es": 'Elige cada casilla tú mismo: parte de un sorteo o del juego original, cambia lo que quieras y guárdalo para compartirlo. Desde esta pestaña, el botón de abajo crea ESTA ROM (las opciones de las otras pestañas no cuentan); desde las otras pestañas, sigue sus opciones.',
        "it": 'Scegli ogni casella da solo: parti da un sorteggio o dal gioco originale, cambia ciò che vuoi e salva per condividere. Da questa scheda, il pulsante in basso crea QUESTA ROM (le opzioni delle altre schede non contano); dalle altre schede, segue le loro opzioni.'},
    "creer_tirer_options": {
        "en": 'Draw with my options', "fr": 'Tirer avec mes options',
        "de": 'Mit meinen Optionen ziehen', "es": 'Sortear con mis opciones',
        "it": 'Sorteggia con le mie opzioni'},
    "creer_vanilla": {
        "en": 'All original', "fr": 'Tout en vanilla', "de": 'Alles original',
        "es": 'Todo original', "it": 'Tutto originale'},
    "creer_ouvrir": {
        "en": 'Open...', "fr": 'Ouvrir...', "de": 'Öffnen...',
        "es": 'Abrir...', "it": 'Apri...'},
    "creer_enregistrer": {
        "en": 'Save...', "fr": 'Enregistrer...', "de": 'Speichern...',
        "es": 'Guardar...', "it": 'Salva...'},
    "creer_tirer_cat": {
        "en": 'Draw unpinned cases', "fr": 'Tirer les cases non figées',
        "de": 'Nicht fixierte Felder ziehen',
        "es": 'Sortear las casillas no fijadas',
        "it": 'Sorteggia le caselle non fissate'},
    "creer_vanilla_cat": {
        "en": 'Back to original', "fr": 'Remettre vanilla',
        "de": 'Zurück zum Original', "es": 'Volver al original',
        "it": 'Torna all\'originale'},
    "creer_defiger": {
        "en": 'Unpin all', "fr": 'Tout défiger', "de": 'Alle lösen',
        "es": 'Soltar todo', "it": 'Sblocca tutto'},
    "creer_tout_oui": {
        "en": 'All to Yes', "fr": 'Tout à Oui', "de": 'Alle auf Ja',
        "es": 'Todo a Sí', "it": 'Tutto su Sì'},
    "creer_tout_non": {
        "en": 'All to No', "fr": 'Tout à Non', "de": 'Alle auf Nein',
        "es": 'Todo a No', "it": 'Tutto su No'},
    "creer_bientot": {
        "en": '%s (soon)', "fr": '%s (bientôt)', "de": '%s (bald)',
        "es": '%s (pronto)', "it": '%s (presto)'},
    "creer_aide_table": {
        "en": 'Double-click a case to change it: it gets pinned (●) and draws leave it alone. Click the first column to pin or unpin a row. ■ locked: the game cannot be finished without it.',
        "fr": 'Double-cliquez une case pour la changer : elle est figée (●) et les tirages n\'y touchent pas. Cliquez la première colonne pour figer ou libérer une ligne. ■ verrouillée : sans elle, le jeu ne se finit pas.',
        "de": 'Doppelklicke ein Feld, um es zu ändern: Es wird fixiert (●) und Ziehungen lassen es in Ruhe. Klicke die erste Spalte, um eine Zeile zu fixieren oder zu lösen. ■ gesperrt: ohne es lässt sich das Spiel nicht beenden.',
        "es": 'Haz doble clic en una casilla para cambiarla: queda fijada (●) y los sorteos no la tocan. Haz clic en la primera columna para fijar o soltar una fila. ■ bloqueada: sin ella no se puede terminar el juego.',
        "it": 'Fai doppio clic su una casella per cambiarla: viene fissata (●) e i sorteggi non la toccano. Clicca la prima colonna per fissare o sbloccare una riga. ■ bloccata: senza di essa il gioco non si può finire.'},
    "creer_col_place": {
        "en": 'Case', "fr": 'Case', "de": 'Feld', "es": 'Casilla',
        "it": 'Casella'},
    "creer_col_vanilla": {
        "en": 'Original', "fr": 'Vanilla', "de": 'Original',
        "es": 'Original', "it": 'Originale'},
    "creer_attente": {
        "en": 'Choose your ROM first.', "fr": 'Choisissez d\'abord votre ROM.',
        "de": 'Wähle zuerst deine ROM.', "es": 'Elige primero tu ROM.',
        "it": 'Scegli prima la tua ROM.'},
    "creer_en_cours": {
        "en": 'Drawing...', "fr": 'Tirage en cours...', "de": 'Ziehung läuft...',
        "es": 'Sorteando...', "it": 'Sorteggio in corso...'},
    "creer_verrous": {
        "en": 'Keep the locks (■): what the game cannot be finished without stays as it is',
        "fr": 'Garder les verrous (■) : ce sans quoi le jeu ne se finit pas reste en place',
        "de": 'Sperren behalten (■): Was zum Beenden des Spiels nötig ist, bleibt, wie es ist',
        "es": 'Mantener los bloqueos (■): lo necesario para terminar el juego se queda como está',
        "it": "Mantieni i blocchi (■): ciò che serve per finire il gioco resta com'è"},
    "creer_sans_verrous": {
        "en": 'Locks lifted: anything goes, the game may no longer be finishable.',
        "fr": 'Verrous levés : tout est permis, le jeu peut ne plus se finir.',
        "de": 'Sperren aufgehoben: Alles ist erlaubt, das Spiel lässt sich vielleicht nicht mehr beenden.',
        "es": 'Bloqueos quitados: todo vale, puede que el juego ya no se pueda terminar.',
        "it": 'Blocchi tolti: tutto è permesso, il gioco potrebbe non essere più completabile.'},
    "creer_controle_ko": {
        "en": 'Refused: %s', "fr": 'Refusé : %s', "de": 'Abgelehnt: %s',
        "es": 'Rechazado: %s', "it": 'Rifiutato: %s'},
    "creer_verrou": {
        "en": 'This case cannot change: without it the game cannot be finished.',
        "fr": 'Cette case ne peut pas changer : sans elle, le jeu ne se finit pas.',
        "de": 'Dieses Feld kann sich nicht ändern: Ohne es lässt sich das Spiel nicht beenden.',
        "es": 'Esta casilla no puede cambiar: sin ella no se puede terminar el juego.',
        "it": 'Questa casella non può cambiare: senza di essa il gioco non si può finire.'},
    "creer_type_fichier": {
        "en": 'DQIX Randomizer configuration',
        "fr": 'Configuration DQIX Randomizer',
        "de": 'DQIX-Randomizer-Konfiguration',
        "es": 'Configuración de DQIX Randomizer',
        "it": 'Configurazione di DQIX Randomizer'},
    "creer_fichier_refuse": {
        "en": 'File refused: %s', "fr": 'Fichier refusé : %s',
        "de": 'Datei abgelehnt: %s', "es": 'Archivo rechazado: %s',
        "it": 'File rifiutato: %s'},
    "creer_config_ecrite": {
        "en": 'Configuration saved: %s', "fr": 'Configuration enregistrée : %s',
        "de": 'Konfiguration gespeichert: %s',
        "es": 'Configuración guardada: %s',
        "it": 'Configurazione salvata: %s'},
    "cat_boss": {"en": 'Bosses', "fr": 'Boss', "de": 'Bosse', "es": 'Jefes',
                 "it": 'Boss'},
    "cat_boutiques": {"en": 'Shops', "fr": 'Boutiques', "de": 'Läden',
                      "es": 'Tiendas', "it": 'Negozi'},
    "cat_coffres": {"en": 'Chests and pots', "fr": 'Coffres et pots',
                    "de": 'Truhen und Töpfe', "es": 'Cofres y vasijas',
                    "it": 'Forzieri e vasi'},
    "cat_grottes": {"en": 'Grotto chests', "fr": 'Coffres des grottes',
                    "de": 'Grottentruhen', "es": 'Cofres de las grutas',
                    "it": 'Forzieri delle grotte'},
    "cat_alchimie": {"en": 'Alchemy', "fr": 'Alchimie', "de": 'Alchemie',
                     "es": 'Alquimia', "it": 'Alchimia'},
    # memes noms que la case `medailles`
    "cat_capitaine": {"en": "Cap'n Max Meddlin'", "fr": 'Capitaine Zac',
                      "de": 'Medaillen-Kapitän',
                      "es": 'Capitán de las minimedallas',
                      "it": 'Capitano delle minimedaglie'},
    "cat_arbres": {"en": 'Skill trees', "fr": 'Arbres de compétences',
                   "de": 'Talentbäume', "es": 'Árboles de habilidades',
                   "it": 'Alberi delle abilità'},
    "cat_sorts": {"en": 'Vocation spells', "fr": 'Sorts des vocations',
                  "de": 'Zauber der Berufe', "es": 'Hechizos de vocación',
                  "it": 'Magie delle vocazioni'},
    "cat_vocations": {"en": 'Vocations', "fr": 'Vocations', "de": 'Berufe',
                      "es": 'Vocaciones', "it": 'Vocazioni'},
    "cat_monstres": {"en": 'Field monsters', "fr": 'Monstres du terrain',
                     "de": 'Monster im Gelände', "es": 'Monstruos del mapa',
                     "it": 'Mostri sul campo'},
    "cat_butin": {"en": 'Battle drops', "fr": 'Butin des combats',
                  "de": 'Kampfbeute', "es": 'Botín de combate',
                  "it": 'Bottino dei combattimenti'},
    "cat_actions": {"en": 'Monster spells and abilities',
                    "fr": 'Sorts et techniques des monstres',
                    "de": 'Zauber und Techniken der Monster',
                    "es": 'Hechizos y técnicas de los monstruos',
                    "it": 'Magie e tecniche dei mostri'},
    "table_paliers": {"en": 'Milestone %s', "fr": 'Palier %s',
                      "de": 'Stufe %s', "es": 'Hito %s', "it": 'Traguardo %s'},
    "table_boutique": {"en": 'Shop %s', "fr": 'Boutique %s',
                       "de": 'Laden %s', "es": 'Tienda %s',
                       "it": 'Negozio %s'},
    "champ_medailles": {"en": 'Medals', "fr": 'Médailles', "de": 'Medaillen',
                        "es": 'Medallas', "it": 'Medaglie'},
    "champ_objet": {"en": 'Item', "fr": 'Objet', "de": 'Gegenstand',
                    "es": 'Objeto', "it": 'Oggetto'},
    # LES BOSS (ZER-88)
    "table_histoire": {"en": 'Story %s', "fr": 'Histoire %s',
                       "de": 'Geschichte %s', "es": 'Historia %s',
                       "it": 'Storia %s'},
    "table_grottes": {"en": 'Grotto %s', "fr": 'Grotte %s', "de": 'Grotte %s',
                      "es": 'Gruta %s', "it": 'Grotta %s'},
    "table_legendes": {"en": 'Legacy %s', "fr": 'Légende %s',
                       "de": 'Legende %s', "es": 'Leyenda %s',
                       "it": 'Leggenda %s'},
    "table_autres": {"en": 'Other fight %s', "fr": 'Autre combat %s',
                     "de": 'Anderer Kampf %s', "es": 'Otro combate %s',
                     "it": 'Altro combattimento %s'},
    "champ_espece": {"en": 'Monster', "fr": 'Monstre', "de": 'Monster',
                     "es": 'Monstruo', "it": 'Mostro'},
    "champ_tirage": {"en": 'Draw', "fr": 'Tirage', "de": 'Ziehung',
                     "es": 'Sorteo', "it": 'Sorteggio'},
    "tirage_fixe": {"en": 'Fixed', "fr": 'Fixe', "de": 'Fest', "es": 'Fijo',
                    "it": 'Fisso'},
    "tirage_visite": {"en": 'Every visit', "fr": 'À chaque visite',
                      "de": 'Bei jedem Besuch', "es": 'En cada visita',
                      "it": 'A ogni visita'},
    "genre_histoire": {"en": 'story', "fr": 'histoire', "de": 'Geschichte',
                       "es": 'historia', "it": 'storia'},
    "genre_grottes": {"en": 'grotto', "fr": 'grotte', "de": 'Grotte',
                      "es": 'gruta', "it": 'grotta'},
    "genre_legendes1": {"en": 'legacy 1', "fr": 'légende 1',
                        "de": 'Legende 1', "es": 'leyenda 1',
                        "it": 'leggenda 1'},
    "genre_legendes2": {"en": 'legacy 2', "fr": 'légende 2',
                        "de": 'Legende 2', "es": 'leyenda 2',
                        "it": 'leggenda 2'},
    "genre_legendes3": {"en": 'legacy 3', "fr": 'légende 3',
                        "de": 'Legende 3', "es": 'leyenda 3',
                        "it": 'leggenda 3'},
    "genre_monstre": {"en": 'monster', "fr": 'monstre', "de": 'Monster',
                      "es": 'monstruo', "it": 'mostro'},
    "type_w": {"en": 'weapon', "fr": 'arme', "de": 'Waffe', "es": 'arma',
               "it": 'arma'},
    "type_s": {"en": 'shield', "fr": 'bouclier', "de": 'Schild',
               "es": 'escudo', "it": 'scudo'},
    "type_b": {"en": 'body', "fr": 'torse', "de": 'Körper', "es": 'torso',
               "it": 'busto'},
    "type_u": {"en": 'legs', "fr": 'jambes', "de": 'Beine', "es": 'piernas',
               "it": 'gambe'},
    "type_h": {"en": 'head', "fr": 'tête', "de": 'Kopf', "es": 'cabeza',
               "it": 'testa'},
    "type_a": {"en": 'arms', "fr": 'bras', "de": 'Arme', "es": 'brazos',
               "it": 'braccia'},
    "type_l": {"en": 'feet', "fr": 'pieds', "de": 'Füße', "es": 'pies',
               "it": 'piedi'},
    "type_d": {"en": 'accessory', "fr": 'accessoire', "de": 'Zubehör',
               "es": 'accesorio', "it": 'accessorio'},
    "type_t": {"en": 'item', "fr": 'objet', "de": 'Gegenstand', "es": 'objeto',
               "it": 'oggetto'},
    # ZER-89..92 : boutiques, coffres, grottes, alchimie, arbres, sorts,
    # vocations
    "champ_pourcentage": {"en": 'Price %', "fr": 'Prix %', "de": 'Preis %',
                          "es": 'Precio %', "it": 'Prezzo %'},
    "champ_ingredient1": {"en": 'Ingredient 1', "fr": 'Ingrédient 1',
                          "de": 'Zutat 1', "es": 'Ingrediente 1',
                          "it": 'Ingrediente 1'},
    "champ_ingredient2": {"en": 'Ingredient 2', "fr": 'Ingrédient 2',
                          "de": 'Zutat 2', "es": 'Ingrediente 2',
                          "it": 'Ingrediente 2'},
    "champ_ingredient3": {"en": 'Ingredient 3', "fr": 'Ingrédient 3',
                          "de": 'Zutat 3', "es": 'Ingrediente 3',
                          "it": 'Ingrediente 3'},
    "champ_sort": {"en": 'Spell', "fr": 'Sort', "de": 'Zauber',
                   "es": 'Hechizo', "it": 'Magia'},
    "champ_palier": {"en": 'Gives', "fr": 'Donne', "de": 'Gibt',
                     "es": 'Otorga', "it": 'Dà'},
    "champ_vocation": {"en": 'Vocation', "fr": 'Vocation', "de": 'Beruf',
                       "es": 'Vocación', "it": 'Vocazione'},
    "champ_actif": {"en": 'On', "fr": 'Actif', "de": 'An', "es": 'Activo',
                    "it": 'Attivo'},
    "champ_or": {"en": 'Gold', "fr": 'Or', "de": 'Gold', "es": 'Oro',
                 "it": 'Oro'},
    "champ_rang_coffre": {"en": 'Rank', "fr": 'Rang', "de": 'Rang',
                          "es": 'Rango', "it": 'Rango'},
    "table_bleus": {"en": 'Blue chests', "fr": 'Coffres bleus',
                    "de": 'Blaue Truhen', "es": 'Cofres azules',
                    "it": 'Forzieri blu'},
    "table_pots": {"en": 'Pots, barrels, drawers',
                   "fr": 'Pots, tonneaux, placards',
                   "de": 'Töpfe, Fässer, Schränke',
                   "es": 'Vasijas, barriles, armarios',
                   "it": 'Vasi, barili, armadi'},
    "table_rouges": {"en": 'Red chest', "fr": 'Coffre rouge',
                     "de": 'Rote Truhe', "es": 'Cofre rojo',
                     "it": 'Forziere rosso'},
    "table_rangs": {"en": 'Blue chest', "fr": 'Coffre bleu',
                    "de": 'Blaue Truhe', "es": 'Cofre azul',
                    "it": 'Forziere blu'},
    "place_boutique": {"en": 'Shop %s · %s · %s', "fr": 'Boutique %s · %s · %s',
                       "de": 'Laden %s · %s · %s', "es": 'Tienda %s · %s · %s',
                       "it": 'Negozio %s · %s · %s'},
    "etal_0": {"en": 'weapons', "fr": 'armes', "de": 'Waffen', "es": 'armas',
               "it": 'armi'},
    "etal_1": {"en": 'armour', "fr": 'armures', "de": 'Rüstungen',
               "es": 'armaduras', "it": 'armature'},
    "etal_2": {"en": 'items', "fr": 'objets', "de": 'Gegenstände',
               "es": 'objetos', "it": 'oggetti'},
    "etal_3": {"en": 'general', "fr": 'général', "de": 'Gemischt',
               "es": 'general', "it": 'generale'},
    "etal_4": {"en": 'weapons and armour', "fr": 'armes et armures',
               "de": 'Waffen und Rüstungen', "es": 'armas y armaduras',
               "it": 'armi e armature'},
    "etal_5": {"en": 'mixed', "fr": 'mélangé', "de": 'gemischt',
               "es": 'mixta', "it": 'misto'},
    "place_sort": {"en": '%s · level %s', "fr": '%s · niveau %s',
                   "de": '%s · Stufe %s', "es": '%s · nivel %s',
                   "it": '%s · livello %s'},
    "place_palier": {"en": '%s · %s pts', "fr": '%s · %s PC',
                     "de": '%s · %s TP', "es": '%s · %s pts',
                     "it": '%s · %s pt'},
    "place_ligne": {"en": 'Rank %s · %s %%', "fr": 'Rang %s · %s %%',
                    "de": 'Rang %s · %s %%', "es": 'Rango %s · %s %%',
                    "it": 'Rango %s · %s %%'},
    "loot_embuscade": {"en": 'ambush', "fr": 'embuscade', "de": 'Hinterhalt',
                       "es": 'emboscada', "it": 'imboscata'},
    "loot_rien": {"en": 'nothing', "fr": 'rien', "de": 'nichts',
                  "es": 'nada', "it": 'niente'},
    "drop_commun": {"en": 'common drop', "fr": 'butin commun',
                    "de": 'normale Beute', "es": 'botín común',
                    "it": 'bottino comune'},
    "drop_rare": {"en": 'rare drop', "fr": 'butin rare',
                  "de": 'seltene Beute', "es": 'botín raro',
                  "it": 'bottino raro'},
    "reglage_depart": {"en": "Hero's starting vocation",
                       "fr": 'Vocation de départ du héros',
                       "de": 'Startberuf des Helden',
                       "es": 'Vocación inicial del héroe',
                       "it": "Vocazione iniziale dell'eroe"},
    "reglage_ouvertes": {"en": 'All 12 vocations from the start',
                         "fr": 'Les 12 vocations dès le début',
                         "de": 'Alle 12 Berufe von Anfang an',
                         "es": 'Las 12 vocaciones desde el principio',
                         "it": 'Tutte le 12 vocazioni fin dall\'inizio'},
    "reglage_embauche": {"en": 'Random vocation for each recruit',
                         "fr": 'Vocation tirée à chaque recrue',
                         "de": 'Zufälliger Beruf bei jeder Anwerbung',
                         "es": 'Vocación aleatoria en cada recluta',
                         "it": 'Vocazione casuale per ogni recluta'},
    "reglage_bloquees": {"en": 'Vocations locked',
                         "fr": 'Vocations bloquées',
                         "de": 'Berufe gesperrt',
                         "es": 'Vocaciones bloqueadas',
                         "it": 'Vocazioni bloccate'},
    # ZER-93 : le butin des combats
    # le texte dit ce que fait le reglage (joueur, 20/10/2026 : « je le
    # comprends mal ») : les chances de butin ne changent pas, seul l'objet
    "reglage_butin_tire": {
        "en": 'Dropped item drawn at every battle',
        "fr": 'Objet lâché tiré à chaque combat',
        "de": 'Fallengelassener Gegenstand in jedem Kampf gezogen',
        "es": 'Objeto soltado sorteado en cada combate',
        "it": 'Oggetto lasciato estratto a ogni battaglia'},
    "reglage_butin_rares": {
        "en": '4-5 star items 8 times rarer',
        "fr": 'Objets 4-5 étoiles 8 fois plus rares',
        "de": '4-5-Sterne-Gegenstände 8-mal seltener',
        "es": 'Objetos de 4-5 estrellas 8 veces más raros',
        "it": 'Oggetti a 4-5 stelle 8 volte più rari'},
    # sous la table (FORME["aide"]) : ce que font les deux reglages
    "aide_butin": {
        "en": 'The chance that a monster drops something stays the game\'s '
              'own; only WHICH item it drops is drawn from the list. 4-5 star '
              'items 8 times rarer: Yes, a 4-5 star item drawn is only kept '
              'once in 8 draws; No, it comes out as often as the others. To '
              'never get them, set them to No in the list.',
        "fr": 'La chance qu\'un monstre lâche quelque chose reste celle du '
              'jeu ; seul L\'OBJET lâché est tiré dans la liste. Objets 4-5 '
              'étoiles 8 fois plus rares : Oui, un objet 4-5 étoiles tiré '
              'n\'est gardé qu\'une fois sur 8 ; Non, il sort aussi souvent '
              'que les autres. Pour ne jamais en avoir, passez-les à Non dans '
              'la liste.',
        "de": 'Die Chance, dass ein Monster etwas fallen lässt, bleibt die '
              'des Spiels; nur WELCHER Gegenstand fällt, wird aus der Liste '
              'gezogen. 4-5-Sterne 8-mal seltener: Ja, ein gezogener '
              '4-5-Sterne-Gegenstand wird nur bei jeder 8. Ziehung behalten; '
              'Nein, er kommt so oft wie die anderen. Um sie nie zu bekommen, '
              'in der Liste auf Nein setzen.',
        "es": 'La probabilidad de que un monstruo suelte algo es la del juego; '
              'solo QUÉ objeto suelta se sortea en la lista. 4-5 estrellas 8 '
              'veces más raros: Sí, un objeto de 4-5 estrellas sorteado solo '
              'se queda una vez de cada 8; No, sale tan a menudo como los '
              'demás. Para no tenerlos nunca, ponlos en No en la lista.',
        "it": 'La probabilità che un mostro lasci qualcosa resta quella del '
              'gioco; solo QUALE oggetto lascia viene estratto dalla lista. '
              '4-5 stelle 8 volte più rari: Sì, un oggetto a 4-5 stelle '
              'estratto viene tenuto solo una volta su 8; No, esce come gli '
              'altri. Per non averli mai, mettili su No nella lista.'},
    # UNE TABLE A LA FOIS (joueur, 20/10/2026) : le selecteur et ses tables
    "creer_liste": {"en": 'Table:', "fr": 'Table :', "de": 'Tabelle:',
                    "es": 'Tabla:', "it": 'Tabella:'},
    "creer_chercher": {"en": 'Search (Enter: next):',
                       "fr": 'Chercher (Entrée : suivant) :',
                       "de": 'Suchen (Eingabe: weiter):',
                       "es": 'Buscar (Intro: siguiente):',
                       "it": 'Cerca (Invio: successivo):'},
    "creer_grise": {
        "en": 'Random at every spawn: these tables do not apply.',
        "fr": 'Aléatoire à chaque apparition : ces tables ne s\'appliquent pas.',
        "de": 'Zufällig bei jedem Erscheinen: Diese Tabellen gelten nicht.',
        "es": 'Aleatorio en cada aparición: estas tablas no se aplican.',
        "it": 'Casuale a ogni comparsa: queste tabelle non si applicano.'},
    "liste_paliers": {"en": 'Milestones', "fr": 'Paliers', "de": 'Stufen',
                      "es": 'Hitos', "it": 'Traguardi'},
    "liste_boutique": {"en": 'Medal shop', "fr": 'Boutique des médailles',
                       "de": 'Medaillenladen', "es": 'Tienda de medallas',
                       "it": 'Negozio delle medaglie'},
    "liste_histoire": {"en": 'Story fights', "fr": 'Combats d\'histoire',
                       "de": 'Story-Kämpfe', "es": 'Combates de la historia',
                       "it": 'Combattimenti della storia'},
    "liste_grottes": {"en": 'Grotto bosses', "fr": 'Boss des grottes',
                      "de": 'Grottenbosse', "es": 'Jefes de grutas',
                      "it": 'Boss delle grotte'},
    "liste_legendes": {"en": 'Legacy bosses', "fr": 'Boss légendaires',
                       "de": 'Legendäre Bosse', "es": 'Jefes legendarios',
                       "it": 'Boss leggendari'},
    "liste_autres": {"en": 'Other fights', "fr": 'Autres combats',
                     "de": 'Andere Kämpfe', "es": 'Otros combates',
                     "it": 'Altri combattimenti'},
    "liste_bleus": {"en": 'Blue chests: item lines',
                    "fr": 'Coffres bleus : lignes d\'objets',
                    "de": 'Blaue Truhen: Gegenstandszeilen',
                    "es": 'Cofres azules: líneas de objetos',
                    "it": 'Forzieri blu: righe di oggetti'},
    "liste_pots": {"en": 'Pots, barrels, drawers: item lines',
                   "fr": 'Pots, tonneaux, placards : lignes d\'objets',
                   "de": 'Töpfe, Fässer, Schränke: Gegenstandszeilen',
                   "es": 'Vasijas, barriles, armarios: líneas de objetos',
                   "it": 'Vasi, barili, armadi: righe di oggetti'},
    "liste_rouges": {"en": 'Red chests', "fr": 'Coffres rouges',
                     "de": 'Rote Truhen', "es": 'Cofres rojos',
                     "it": 'Forzieri rossi'},
    "liste_rangs": {"en": 'Rank of each blue chest',
                    "fr": 'Rang de chaque coffre bleu',
                    "de": 'Rang jeder blauen Truhe',
                    "es": 'Rango de cada cofre azul',
                    "it": 'Rango di ogni forziere blu'},
    "liste_drops": {"en": 'Items carried by monsters',
                    "fr": 'Objets portés par les monstres',
                    "de": 'Gegenstände der Monster',
                    "es": 'Objetos de los monstruos',
                    "it": 'Oggetti dei mostri'},
    "liste_emplacements": {"en": 'Monster actions',
                           "fr": 'Actions des monstres',
                           "de": 'Aktionen der Monster',
                           "es": 'Acciones de los monstruos',
                           "it": 'Azioni dei mostri'},
    "liste_pool": {"en": 'Draw pool', "fr": 'Pool de tirage',
                   "de": 'Ziehungspool', "es": 'Reserva de sorteo',
                   "it": 'Riserva di estrazione'},
    # ZER-93 : les monstres du terrain
    "champ_mode": {"en": 'Mode', "fr": 'Mode', "de": 'Modus', "es": 'Modo',
                   "it": 'Modalità'},
    "monstres_partout": {"en": 'Everywhere', "fr": 'Partout',
                         "de": 'Überall', "es": 'En todas partes',
                         "it": 'Ovunque'},
    "booleen_oui": {"en": 'Yes', "fr": 'Oui', "de": 'Ja', "es": 'Sí',
                    "it": 'Sì'},
    "booleen_non": {"en": 'No', "fr": 'Non', "de": 'Nein', "es": 'No',
                    "it": 'No'},
    # ZER-93 : les sorts et techniques des monstres
    "place_action": {"en": '%s · slot %s', "fr": '%s · emplacement %s',
                     "de": '%s · Platz %s', "es": '%s · espacio %s',
                     "it": '%s · slot %s'},
    "champ_action": {"en": 'Action', "fr": 'Action', "de": 'Aktion',
                     "es": 'Acción', "it": 'Azione'},
    "champ_source": {"en": 'Slot', "fr": 'Emplacement', "de": 'Platz',
                     "es": 'Espacio', "it": 'Slot'},
    "source_fixe": {"en": 'Fixed', "fr": 'Fixe', "de": 'Fest', "es": 'Fijo',
                    "it": 'Fisso'},
    "source_sort": {"en": 'Random spell', "fr": 'Sort tiré',
                    "de": 'Zufälliger Zauber', "es": 'Hechizo al azar',
                    "it": 'Magia casuale'},
    "source_technique": {"en": 'Random ability', "fr": 'Technique tirée',
                         "de": 'Zufällige Technik', "es": 'Técnica al azar',
                         "it": 'Tecnica casuale'},
    "genre_technique": {"en": 'Ability', "fr": 'Technique', "de": 'Technik',
                        "es": 'Técnica', "it": 'Tecnica'},
    # ZER-97 : les points brillants
    "cat_points": {"en": 'Sparkly spots', "fr": 'Points brillants',
                   "de": 'Glitzernde Stellen', "es": 'Puntos brillantes',
                   "it": 'Punti luccicanti'},
    "liste_cartes": {"en": 'Pool of each map (at each pickup)',
                     "fr": 'Pool de chaque carte (au ramassage)',
                     "de": 'Pool jeder Karte (beim Aufheben)',
                     "es": 'Reserva de cada mapa (al recoger)',
                     "it": 'Riserva di ogni mappa (alla raccolta)'},
    "liste_terrain": {"en": 'Spots of the field maps',
                      "fr": 'Points des cartes du terrain',
                      "de": 'Stellen der Geländekarten',
                      "es": 'Puntos de los mapas',
                      "it": 'Punti delle mappe'},
    "liste_speciales": {"en": 'Special zones 98/99 (8 tables, one per save)',
                        "fr": 'Zones spéciales 98/99 (8 tables, une par partie)',
                        "de": 'Sonderzonen 98/99 (8 Tabellen, eine pro Spielstand)',
                        "es": 'Zonas especiales 98/99 (8 tablas, una por partida)',
                        "it": 'Zone speciali 98/99 (8 tabelle, una per partita)'},
    "reglage_ramassage": {"en": 'Draw', "fr": 'Tirage', "de": 'Ziehung',
                          "es": 'Sorteo', "it": 'Estrazione'},
    "champ_ramassage": {"en": 'At each pickup', "fr": 'À chaque ramassage',
                        "de": 'Bei jedem Aufheben',
                        "es": 'En cada recogida', "it": 'A ogni raccolta'},
    # ZER-58 : les statistiques des monstres
    "cat_stats": {"en": 'Monster stats', "fr": 'Statistiques des monstres',
                  "de": 'Monsterwerte', "es": 'Estadísticas de los monstruos',
                  "it": 'Statistiche dei mostri'},
    "liste_valeurs": {"en": 'HP, MP, attack, defence, agility',
                      "fr": 'PV, PM, attaque, défense, agilité',
                      "de": 'LP, MP, Angriff, Verteidigung, Beweglichkeit',
                      "es": 'PV, PM, ataque, defensa, agilidad',
                      "it": 'PV, PM, attacco, difesa, agilità'},
    "liste_elements": {"en": 'Element resistances',
                       "fr": 'Résistances aux éléments',
                       "de": 'Element-Resistenzen',
                       "es": 'Resistencias a elementos',
                       "it": 'Resistenze agli elementi'},
    "liste_alterations": {"en": 'Status resistances',
                          "fr": "Résistances aux altérations d'état",
                          "de": 'Status-Resistenzen',
                          "es": 'Resistencias a estados',
                          "it": 'Resistenze agli status'},
    "champ_pv": {"en": 'HP', "fr": 'PV', "de": 'LP', "es": 'PV', "it": 'PV'},
    "champ_pm": {"en": 'MP', "fr": 'PM', "de": 'MP', "es": 'PM', "it": 'PM'},
    "champ_attaque": {"en": 'Attack', "fr": 'Attaque', "de": 'Angriff',
                      "es": 'Ataque', "it": 'Attacco'},
    "champ_defense": {"en": 'Defence', "fr": 'Défense',
                      "de": 'Verteidigung', "es": 'Defensa', "it": 'Difesa'},
    "champ_agilite": {"en": 'Agility', "fr": 'Agilité',
                      "de": 'Beweglichkeit', "es": 'Agilidad',
                      "it": 'Agilità'},
    "mode_stats_fixe": {"en": 'Fixed', "fr": 'Fixe', "de": 'Fest',
                        "es": 'Fijo', "it": 'Fisso'},
    "mode_stats_tire": {"en": 'Drawn in range', "fr": 'Tiré dans la plage',
                        "de": 'Im Bereich gezogen',
                        "es": 'Sorteado en el rango',
                        "it": "Estratto nell'intervallo"},
    "mode_stats_combat": {"en": 'Drawn at every battle',
                          "fr": 'Tiré à chaque combat',
                          "de": 'Bei jedem Kampf gezogen',
                          "es": 'Sorteado en cada combate',
                          "it": 'Estratto a ogni combattimento'},
    "liste_plages": {"en": 'Ranges (drawn monsters)',
                     "fr": 'Plages (monstres tirés)',
                     "de": 'Bereiche (gezogene Monster)',
                     "es": 'Rangos (monstruos sorteados)',
                     "it": 'Intervalli (mostri estratti)'},
    "creer_grise_stats": {
        "en": 'Not used: a drawn monster takes its values from its ranges, '
              'a fixed one ignores its ranges. Change its mode first.',
        "fr": 'Ne sert pas : un monstre tiré prend ses valeurs dans ses '
              'plages, un monstre fixe ignore ses plages. Changez d\'abord '
              'son mode.',
        "de": 'Nicht verwendet: Ein gezogenes Monster nimmt seine Werte aus '
              'seinen Bereichen, ein festes ignoriert sie. Erst den Modus '
              'ändern.',
        "es": 'No se usa: un monstruo sorteado toma sus valores de sus '
              'rangos, uno fijo ignora sus rangos. Cambia antes su modo.',
        "it": "Non usato: un mostro estratto prende i valori dai suoi "
              "intervalli, uno fisso li ignora. Cambia prima la sua modalità."},
    "creer_grise_points": {
        "en": 'Not used with this draw: at each pickup the pool counts, '
              'otherwise the fixed items. Change the draw first.',
        "fr": 'Ne sert pas avec ce tirage : au ramassage, c\'est le pool qui '
              'compte, sinon les objets fixes. Changez d\'abord le tirage.',
        "de": 'Bei dieser Ziehung nicht verwendet: beim Aufheben zählt der '
              'Pool, sonst die festen Gegenstände. Erst die Ziehung ändern.',
        "es": 'No se usa con este sorteo: al recoger cuenta la reserva, si '
              'no los objetos fijos. Cambia antes el sorteo.',
        "it": "Non usato con questa estrazione: alla raccolta conta la "
              "riserva, altrimenti gli oggetti fissi. Cambia prima "
              "l'estrazione."},
    "aide_stats": {
        "en": 'Mode: Fixed keeps the values of the line; Drawn in range draws '
              'each stat between its min and max (Ranges list) when the ROM '
              'is built. Element resistances: damage taken in % (0 none, 100 '
              'normal, 200 double). Status resistances: in % as the game '
              'stores them. Columns follow the order of the game file; which '
              'element or status each one is has not been identified yet.',
        "fr": "Mode : Fixe garde les valeurs de la ligne ; Tiré dans la plage "
              "tire chaque stat entre son min et son max (liste Plages) à la "
              "création de la ROM. Résistances aux éléments : dégâts subis en "
              "% (0 aucun, 100 normal, 200 double). Altérations : en %, comme "
              "le jeu les range. Les colonnes suivent l'ordre du fichier du "
              "jeu ; quel élément ou quelle altération chacune désigne n'est "
              "pas encore identifié.",
        "de": 'Modus: Fest behält die Werte der Zeile; Im Bereich gezogen '
              'zieht jeden Wert zwischen Min und Max (Liste Bereiche) beim '
              'Erstellen der ROM. Element-Resistenzen: erlittener Schaden in % (0 keiner, 100 '
              'normal, 200 doppelt). Status: in %, wie das Spiel sie '
              'speichert. Die Spalten folgen der Reihenfolge der Spieldatei; '
              'welches Element oder welcher Status jede ist, ist noch nicht '
              'bestimmt.',
        "es": 'Modo: Fijo guarda los valores de la línea; Sorteado en el rango '
              'sortea cada estadística entre su mín. y su máx. (lista Rangos) '
              'al crear la ROM. Resistencias a elementos: daño recibido en % (0 ninguno, 100 normal, 200 '
              'doble). Estados: en %, tal como los guarda el juego. Las '
              'columnas siguen el orden del archivo del juego; aún no se ha '
              'identificado qué elemento o estado es cada una.',
        "it": "Modalità: Fisso tiene i valori della riga; Estratto "
              "nell'intervallo estrae ogni statistica tra min e max (lista "
              "Intervalli) alla creazione della ROM. Resistenze agli elementi: danno subito in % (0 nessuno, 100 "
              "normale, 200 doppio). Status: in %, come li salva il gioco. "
              "Le colonne seguono l'ordine del file del gioco; quale "
              "elemento o status sia ciascuna non è ancora identificato."},
})
# les colonnes des plages des stats (ZER-58)
for _s, _n in (("pv", {"en": 'HP', "fr": 'PV', "de": 'LP', "es": 'PV',
                       "it": 'PV'}),
               ("pm", {"en": 'MP', "fr": 'PM', "de": 'MP', "es": 'PM',
                       "it": 'PM'}),
               ("attaque", {"en": 'Att.', "fr": 'Att.', "de": 'Angr.',
                            "es": 'Atq.', "it": 'Att.'}),
               ("defense", {"en": 'Def.', "fr": 'Déf.', "de": 'Vert.',
                            "es": 'Def.', "it": 'Dif.'}),
               ("agilite", {"en": 'Agi.', "fr": 'Agi.', "de": 'Bew.',
                            "es": 'Agi.', "it": 'Agi.'})):
    T["champ_%s_min" % _s] = {c: _n[c] + " min" for c in _n}
    T["champ_%s_max" % _s] = {c: _n[c] + " max" for c in _n}
# les colonnes des resistances : numerotees, faute de savoir laquelle est
# quel element ou quelle alteration (ZER-58)
for _k in range(1, 8):
    T["champ_e%d" % _k] = {"en": 'Elem. %d' % _k, "fr": 'Élém. %d' % _k,
                           "de": 'Elem. %d' % _k, "es": 'Elem. %d' % _k,
                           "it": 'Elem. %d' % _k}
for _k in range(1, 15):
    T["champ_a%d" % _k] = {"en": 'Status %d' % _k, "fr": 'Altér. %d' % _k,
                           "de": 'Status %d' % _k, "es": 'Estado %d' % _k,
                           "it": 'Status %d' % _k}


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
    for code in CODES:
        if len(NOMS_BOSS_HISTOIRE.get(code, ())) != 30:
            defauts.append("noms des boss d'histoire : %s incomplet" % code)
    return defauts


if __name__ == "__main__":
    d = verifier()
    print("\n".join(d) if d else "%d cles, 5 langues : ok" % len(T))
