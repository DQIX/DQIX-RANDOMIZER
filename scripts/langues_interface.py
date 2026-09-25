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
               'any of the 256 monsters can appear anywhere'),
        "fr": ('Monstres du terrain',
               "n'importe lequel des 256 monstres peut apparaître partout"),
        "de": ('Monster im Gelände',
               'jedes der 256 Monster kann überall auftauchen'),
        "es": ('Monstruos del mapa',
               'cualquiera de los 256 monstruos puede aparecer en cualquier '
               'sitio'),
        "it": ('Mostri sul campo',
               'ognuno dei 256 mostri può comparire ovunque')},
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
               'the game has six times more equipment than consumables; '
               'without this option, the two are rebalanced'),
        "fr": ("surtout de l'équipement",
               "le jeu compte six fois plus d'équipements que de consommables "
               '; sans cette option, on rééquilibre les deux'),
        "de": ('vor allem Ausrüstung',
               'das Spiel hat sechsmal mehr Ausrüstung als '
               'Verbrauchsgegenstände; ohne diese Option wird das ausgeglichen'),
        "es": ('sobre todo equipo',
               'el juego tiene seis veces más equipo que consumibles; sin esta'
               ' opción, se reequilibran'),
        "it": ('soprattutto equipaggiamento',
               'il gioco ha sei volte più equipaggiamento che consumabili; '
               'senza questa opzione, vengono ribilanciati')},
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
        "en": ('Story bosses',
               'each boss fight is against another boss, picked at random'),
        "fr": ("Boss de l'histoire",
               'chaque combat de boss se fait contre un autre boss, tiré au '
               'hasard'),
        "de": ('Bosse der Geschichte',
               'jeder Bosskampf findet gegen einen anderen, zufälligen Boss '
               'statt'),
        "es": ('Jefes de la historia',
               'cada combate contra un jefe es contra otro jefe elegido al '
               'azar'),
        "it": ('Boss della storia',
               'ogni scontro con un boss è contro un altro boss scelto a caso')},
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
CASES = (("monstres", 0), ("objets", 0), ("sans_consommables", 1),
         ("objets_chaos", 1), ("rouges_libres", 1), ("butin", 0),
         ("butin_libre", 1), ("boutiques", 0), ("prix_libres", 1),
         ("boutiques_chaos", 1), ("boss", 0), ("garder_hexacorne", 1),
         ("sorts", 0), ("sorts_chaos", 1), ("aptitudes", 0),
         ("aptitudes_chaos", 1), ("vocations", 0), ("vocations_embauche", 1),
         ("vocation_depart", 1), ("vocations_bloquees", 1), ("stats", 0))


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
    return defauts


if __name__ == "__main__":
    d = verifier()
    print("\n".join(d) if d else "%d cles, 5 langues : ok" % len(T))
