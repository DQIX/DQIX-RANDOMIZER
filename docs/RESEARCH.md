# Formats de données de Dragon Quest IX (NDS) — état des connaissances

> Tout ce qui est marqué **CONFIRMÉ** a été vérifié par recoupement d'au moins deux
> indices indépendants. Ce qui est marqué **HYPOTHÈSE** reste à valider, en général
> par observation en jeu via l'émulateur.

## 1. La ROM

| | |
|---|---|
| Fichier | `Dragon Quest IX - Sentinels of the Starry Skies (Europe) (En,Fr,De,Es,It).nds` |
| Titre interne | `DRAGONQUEST9` |
| Serial | **YDQP** (Europe multi-langue) — JPN = `YDQJ`, USA = `YDQE` |
| Taille | 268 435 456 o (256 Mo) ; données utiles 257 915 964 o |
| CRC32 | `FE8EC0E8` |
| MD5 | `3a63438fff7db282fa3133e8fd020e85` |
| SHA1 | `ff761d349709f329c8ac4bd0023fdce21861e8a1` |

Binaires et systèmes de fichiers :

| Élément | Offset ROM | Adresse RAM | Taille |
|---|---|---|---|
| ARM9 | `0x00004000` | `0x02000000` (entrée `0x02000800`) | 638 216 o |
| ARM7 | `0x001E2400` | `0x02380000` | 167 876 o |
| FNT (noms) | `0x0020B400` | — | 90 629 o |
| FAT | `0x00221800` | — | 60 128 o (**7 516 fichiers**) |
| Overlays ARM9 | `0x0009FE00` | — | **35 overlays** |

Conversion adresse RAM vers offset dans `arm9.bin` :
`offset = adresse_RAM - 0x02000000`, valable uniquement pour
`0x02000000 <= adresse < 0x0209BD08`. Au-delà (tas, objets dynamiques, overlays
chargés), il faut un dump RAM live depuis l'émulateur.

## 2. Arborescence NitroFS

23 répertoires, 7 516 fichiers. Les gros volumes :

| Répertoire | Fichiers | Taille | Contenu |
|---|---|---|---|
| `/data/sound` | 7 | 69,3 Mo | `.sdat` (audio Nitro standard) |
| `/data/map` | 1 386 | 50,1 Mo | cartes |
| `/data/scenario` | 983 | 38,6 Mo | scénario |
| `/data/pack_lv5` | 12 | 27,8 Mo | archives Level-5 |
| `/data/effect` | 1 430 | 22,9 Mo | effets |
| **`/data/prm`** | **60** | **2,25 Mo** | **tables de paramètres — la cible** |
| `/data/enemy` | 26 | 0,48 Mo | modèles `.chr` de quelques ennemis seulement |

`/data/prm` est le répertoire de paramètres du jeu. Noms utiles :

| Fichier | Taille | Rôle probable |
|---|---|---|
| **`mon_btldata.nat`** | 57 820 | **stats de combat des 438 monstres — DÉCODÉ** |
| `mon_moddata.nat` | 28 036 | 438 x 64 o — données de modèle par monstre |
| `mons_info2.nat` | 32 588 | infos monstres (format encore inconnu) |
| `mon_data.gp2` | 59 036 | conteneur GPC2 |
| `mon_list.gp2` | 45 232 | conteneur GPC2 |
| `mon_trv1/2.gp2` | ~105 k | conteneurs GPC2 |
| **`encmons.bin`** | 5 104 | **groupes de rencontre — partiellement décodé** |
| `encbtl.bin` | 27 296 | rencontres en combat (tags 0x68 non gérés) |
| `encfld.bin` | 23 072 | rencontres sur le terrain (tags 0x69 non gérés) |
| `enchab.gp2` | 29 048 | « encounter habitat » — conteneur GPC2 |
| **`fld_mondata.bin`** | 15 840 | **437 monstres de terrain — DÉCODÉ** |
| `mons_dmy.bin` | 1 316 | liste d'index u16 |
| `level0.bin` … `level12.bin` | 5 312 x13 | **tables de progression des 13 vocations — DÉCODÉ** |
| `skilltable.bin` / `spelltable.bin` | 12 704 / 2 576 | compétences / sorts — DÉCODÉ |
| `itemdt*.gp2`, `itemname.gp2` … | — | objets |

## 3. Format de table taggée (`.bin` de `/data/prm`) — CONFIRMÉ

En-tête :

```
+0x00  u32  nb_enregistrements
+0x04  u32  taille_donnees
+0x08  u32  0x1B     (constante ; 0 sur la variante à en-tête court)
+0x0C  u32  0x02     (constante ; 0 sur la variante à en-tête court)
+0x10  u16 tag=0x65, u16 0x0001, u32 0x00000000    } variante longue
+0x18  u16 tag=0x64, u16 0x0001, u32 0x00000014    } uniquement
```

Le corps commence à `0x20` si `0x20 + taille_donnees == taille_fichier`
(variante longue), sinon à `0x10` (variante courte, ex. `encmons.bin`).

Corps : suite d'enregistrements de **taille variable** :

```
u16   tag            0x64, 0x65, 0x66 (et 0x68, 0x69 dans encbtl/encfld — non gérés)
u8    nb_champs
...   descripteur de types + bourrage 0xFF, aligné sur 4 octets
N x u32 les champs
```

Le descripteur est **identique pour tous les enregistrements d'un même type** dans un
fichier donné. On peut donc le traiter comme un préfixe opaque et réécrire les champs
sans en comprendre la sémantique — c'est suffisant pour patcher.

Descripteurs observés : `nb_champs=2` donne 4 o de descripteur ;
`nb_champs=5` donne 8 o (`66 00 05 55 01 ff ff ff`) ; `nb_champs=11` donne 8 o
(`66 00 0b 55 55 15 ff ff`). La règle exacte d'encodage des types n'est pas élucidée
et n'est pas nécessaire.

Implémentation : `scripts/prmtable.py` (classe `PrmTable`, méthode `set_field`).

### `level0.bin` … `level12.bin` — CONFIRMÉ

13 fichiers, un par vocation. 98 enregistrements de 11 champs u32 (niveaux 1 à 99).

```
[0]  = 0,  10, 9, 8, 8, 9, 8, 8, 30, 10, 0
[1]  = 17, 11, 10, 9, 9, 10, 9, 9, 32, 11, 0
[2]  = 44, 13, 12, 11, 11, 12, 11, 11, 35, 13, 0
```

Champ 0 = expérience cumulée requise. Champs 1-7 = stats. Champs 8-9 = HP et MP max
(30 / 10 au niveau 1). Champ 10 = 0 partout. **HYPOTHÈSE** : l'ordre exact des stats
1-7 reste à confirmer en jeu.

### `spelltable.bin` — CONFIRMÉ

175 en-tête / 212 enregistrements de 2 champs u32 : `(index_séquentiel, id)`.
Les `id` vont par groupes de 4 : `(9,10,11,779) (12,16,17,780) (13,14,15,781)…`

### `encmons.bin` — PARTIEL

En-tête court, corps à `0x10`, 209 enregistrements de formes mixtes
(120 x 5 champs, 71 x 4 champs, 17 x 3 champs).

Les champs u32 se relisent en **paires de u16**, ce qui donne des groupes cohérents :

```
[7102, 0, 0x0007002B, 0x0009001E, 0x00040014]
   -> zone 7102, puis (43,7) (30,9) (20,4)
```

**HYPOTHÈSE** : chaque paire est `(id_monstre, quantité ou poids)` et
l'enregistrement décrit un groupe de rencontre pour une zone. À valider en jeu.

### `fld_mondata.bin` — CONFIRMÉ (structure), champs à nommer

437 enregistrements de 7 champs u32, précédés d'un enregistrement de comptage
(tag `0x64`, champ unique = 438).

```
[1, 1,  5, 0x003C0011, 0x3EC8000D, 10,  7]
[2, 7, 12, 0x003C0011, 0x3EC8000D, 23, 18]
```

Champ 0 = id monstre. **Recoupement CONFIRMÉ** : les champs 5 et 6 sont exactement
`mon_btldata.nat +0x60` et `+0x62` (attaque et défense) du même monstre. C'est ce
recoupement qui valide l'alignement des deux tables.

## 4. `mon_btldata.nat` — la table centrale — CONFIRMÉ

**C'est la découverte principale.** Le projet de décompilation communautaire (org
GitHub `DQIX`) considère cette table comme non localisée à ce jour.

Format : `u32 nb = 438`, puis **438 enregistrements de 132 octets**.
`4 + 438 x 132 = 57 820` = taille exacte du fichier.

```
+0x00  u16   0x8000 | id_monstre        id de 1 à 0x384 (900)
+0x02  u16   modèle / famille           paire d'octets, 24 valeurs distinctes
+0x04  u16   id de chaîne : nom         plage ~13000-22200
+0x06  u16   id de chaîne : description plage ~13000-22300
+0x08  u16   EXPÉRIENCE donnée
+0x0A  u16   drapeau, valeurs {0, 1, 3}
+0x0C  u16   OR donné
+0x0E  u16   constante 0
+0x10  u16   ?
+0x12  u16   champ de bits (0x1800, 0x9800, 0x1A00…)
+0x14  u16   ?  (0-605, deux colonnes identiques avec +0x16)
+0x16  u16   ?
+0x18  u16 x 6  ?  valeurs 1 / 225, deux groupes de trois     -> +0x22
+0x24  u16   ?  23 valeurs distinctes
+0x26  u16   ?  11 valeurs distinctes
+0x28  u16   ?  10 valeurs distinctes
+0x2A  u16   ?  0-136, corrélé à la progression
+0x2C  ..    46 octets TOUJOURS À ZÉRO (réservé)             -> +0x5B
+0x5C  u16   HP MAX          <- corrélation 0,86 ; rôle à l'exécution non vérifié,
                              voir la nuance plus bas
+0x5E  u16   MP MAX
+0x60  u16   ATTAQUE
+0x62  u16   DÉFENSE
+0x64  u16   AGILITÉ
+0x66  u16   constante 0
+0x68  u16   constante 0
+0x6A  u16   constante 0
+0x6C  u8 x 7   RÉSISTANCES ÉLÉMENTAIRES en %                -> +0x72
+0x73  u8       toujours 100
+0x74  u8 x 14  RÉSISTANCES AUX ALTÉRATIONS D'ÉTAT en %      -> +0x81
+0x82  u8 x 2   bourrage d'alignement (toujours 0)
```

### Preuves

**1. La signature du Métal Gluant.** L'enregistrement d'index 2 (id 3) :

```
HP 4 · MP 255 · ATT 35 · DÉF 256 · AGI 89 · XP 4096 · or 20
résistances : immunité (0) sur la majorité des colonnes
```

HP 4 avec défense 256 et immunité massive : c'est un Métal Gluant, aucune autre
créature de la série n'a ce profil.

**2. Distribution des octets de résistance.** Sur 10 512 octets échantillonnés,
seulement **15 valeurs distinctes**, toutes des paliers ronds :

| Valeur | % |
|---|---|
| 100 | 31,8 |
| 0 | 27,6 |
| 50 | 14,5 |
| 75 | 11,5 |
| 25 | 3,7 |
| 125 | 3,4 |
| 150 | 3,1 |
| 5 / 10 / 15 / 35 / 200 … | reste |

Et deux blocs nettement séparés : `+0x6C..+0x72` accepte 125/150/200 (donc des
**faiblesses**, un multiplicateur de dégâts), `+0x74..+0x81` plafonne à 100 (donc
une **probabilité** de résister). Une donnée non structurée ne produirait jamais
cette distribution.

**3. Zone témoin.** `+0x2C..+0x5B` est à zéro sur les 438 enregistrements sans
exception : l'alignement des enregistrements est nécessairement correct.

**4. Recoupement inter-fichiers.** `fld_mondata.bin` champs 5-6 égalent `+0x60`
et `+0x62` pour chaque monstre.

**5. Corrélation à la progression.** `+0x5C` (HP) a un rho de Spearman de **0,86**
avec l'index du bestiaire — les tables de monstres sont ordonnées par apparition
dans le jeu, donc les HP doivent croître, et ils croissent.

### Nuance sur le champ HP — signalée par l'observation en jeu

L'utilisateur a constaté qu'un monstre de l'espèce sentinelle, à laquelle
`+0x5C` avait été porté à **111**, est mort après un coup affiché à **73**
dégâts.

Ce qui reste solide pour `+0x5C = HP max` :

- valeurs canoniques de la série retrouvées à l'identique : `metal slime` 4 HP,
  `liquid metal slime` 8 HP, `metal king slime` 16 HP — et ce sont bien ces
  monstres-là, confirmé par leurs noms lus indépendamment (§14) ;
- concordance avec `fld_mondata.bin` sur les champs voisins ;
- corrélation de 0,86 avec l'ordre du bestiaire.

Ce qui n'est **pas** établi : que l'instance de monstre créée en combat prenne
son HP maximal depuis ce champ. Trois explications restent ouvertes et ne sont
pas départagées :

1. les 73 dégâts n'étaient qu'un coup parmi les quatre d'un tour de groupe, et
   le total dépassait 111 ;
2. le jeu applique une variance de HP au moment de l'apparition ;
3. l'instance tire son HP d'une autre source que ce champ.

À noter que ma vérification antérieure (§12) retrouvait le motif
`(HP, MP, attaque, défense)` en mémoire, mais ce motif existe **aussi dans les
octets du fichier chargé en RAM** : je ne peux donc pas exclure d'avoir mesuré le
tampon du fichier plutôt que la structure d'exécution. La conclusion de la §12 sur
l'origine des données reste valable — c'était une comparaison entre deux ROMs —
mais elle ne prouve pas le rôle précis de ce champ à l'exécution.

Trancher demande un savestate pris **pendant** un combat. Quatre tentatives
d'automatisation ont échoué : le pilote atteint la plaine mais ne croise pas de
symbole de monstre, et le sondage d'adresses candidates pour la structure
d'ennemi ne rend que du bruit (`HP 9740/15488`, `MP` courant supérieur au max).
L'adresse `0x022A4C7C` provient de codes Action Replay japonais et n'est peut-être
pas valable en EUR.

**Sans incidence sur le randomizer**, qui par défaut ne touche pas aux
statistiques.

### Reste à faire sur cette table

- Nommer les 7 colonnes élémentaires et les 14 colonnes d'altération d'état
  (méthode : lancer un sort de chaque type sur un monstre à faiblesse connue).
- Identifier les objets lâchés (drops) — **ils ne semblent pas être dans cette
  table** ; chercher dans `mons_info2.nat` ou les conteneurs `.gp2`.
- Élucider `+0x18..+0x22` (valeurs 1/225 en deux groupes de trois).
- Résoudre les id de chaîne `+0x04`/`+0x06` en noms lisibles, ce qui nécessite de
  décoder le conteneur GPC2.

## 5. Conteneur GPC2 (`.gp2`) — NON DÉCODÉ

Magie ASCII `GPC2` en tête. En-tête commun :

```
00000000: 47 50 43 32  05 30 05 00  15 00 20 00  0f 00 14 00   GPC2.0.... .....
00000010: <varie>      e0 01 00 00  <varie>
```

Format Level-5 propriétaire. `Tinke` et `Kuriimu` ne le gèrent pas
([issue Kuriimu #566](https://github.com/IcySon55/Kuriimu/issues/566), jamais
implémentée). L'outil communautaire dédié est
[`DQIX/ArchiveTool`](https://github.com/DQIX/ArchiveTool) (C#, deux exe
glisser-déposer). Aucune spécification écrite publique du format.

## 6. Tables `.nat` — CONFIRMÉ partiellement

Toutes commencent par `u32 = 438` (le nombre de monstres). Stride entier :

| Fichier | Calcul | Stride |
|---|---|---|
| `mon_btldata.nat` | `4 + 438 x 132 = 57 820` OK | 132 |
| `mon_moddata.nat` | `4 + 438 x 64 = 28 036` OK | 64 |
| `mons_info2.nat` | non entier | en-tête différent, à élucider |

## 7. Adresses RAM connues (source : communauté)

Issues de [`DQIX/dqix-functions`](https://github.com/DQIX/dqix-functions) et de
codes Action Replay, recoupées entre elles.

Structure d'un ennemi en combat, en RAM : `enemi(i) = 0x022A4C7C + i x 0xA4`,
5 emplacements (`i = 0..4`) :

```
+0x00 u16 HP courant   +0x02 u16 MP courant
+0x04 u16 HP max       +0x06 u16 MP max
+0x08 u16 attaque      +0x0A u16 défense     +0x0C u16 vitesse
```

Fonctions de spawn, **adresses EUR disponibles** (précieux : le projet de decomp ne
couvre officiellement que JPN et USA) :

| Fonction | EUR | JPN |
|---|---|---|
| `ChooseFieldMonsterId` | `0x02073FEC` | `0x02075168` |
| table de monstres lue par la précédente | `0x020FDDC4` | — |
| `GenerateCompanionByBT` | `0x0209AFE4` | `0x0209CD4C` |
| table associée | `0x020FDE68` | — |
| `GenerateCompanionByAT` | `0x0209B458` | `0x0209D1C0` |
| `initMonsterData` | — | `0x021677AC` |

Structure de la carte : `0x020FDAAC + 0x314 x N`, `N = 0..4`.

## 8. Générateurs pseudo-aléatoires — documentés par la communauté

| Nom | Largeur | Formule | Usage |
|---|---|---|---|
| **AT** | 32 bits | `r = r x 0x41C64E6D + 0x3039` | spawn de monstres, drops, déplacement des symboles |
| **BT** | 64 bits | `s = s x 0x5D588B656C078965 + 0x269EC3` | 2e/3e groupes d'ennemis, alchimie, fuite |
| **CT** | 48 bits | idem BT | actions de combat, caméra ; ré-amorcé à chaque combat |

AT et BT partagent la graine initiale. Le générateur des grottes est différent :
`s = s x 1103515245 + 12345`, sortie `(s >> 16) & 0x7FFF` — réimplémenté en
JavaScript dans [`DQIX/editor`](https://github.com/DQIX/editor)
(`src/game/grotto.js`), avec les tables de correspondance recopiées en dur.

Conséquence pour le randomizer : la formule de préemption est
`dextérité_max x 0,05 + 2` %, +10 % en attaquant de dos.

## 9. Binaires de code — cartographie

### L'ARM9 est compressé (BLZ)

`rom.arm9` tel qu'il sort de la ROM est **compressé** : 638 216 o, qui donnent
1 000 984 o une fois décompressés (facteur 1,57). Pied de compression BLZ sur les
12 derniers octets : `00 00 00 08 08 7d 09 08 10 89 05 00`.

```python
import ndspy.rom, ndspy.codeCompression as cc
rom = ndspy.rom.NintendoDSRom.fromFile(ROM)
plein = cc.decompress(rom.arm9)      # 1 000 984 o
```

**Conséquence pratique : il faut décompresser avant de désassembler.** Chercher un
motif dans `arm9.bin` brut ne donne rien — c'est ce qui explique qu'un octet de code
ARM9 ne se retrouve pas tel quel dans un savestate, alors que l'ARM7 (non compressé)
s'y retrouve immédiatement.

Les 35 overlays ARM9 sont eux aussi compressés, mais `ndspy.loadArm9Overlays()`
rend directement le contenu décompressé (`overlay.data`), il n'y a rien à faire.

Fichier produit : `work/dumps/code/arm9_decompresse.bin`.

### Quel overlay lit quoi

Obtenu en cherchant les chaînes de chemins de fichiers dans chaque overlay
décompressé. Plusieurs overlays partagent la même adresse RAM : ils sont
interchangés à la demande (bank switching).

| Overlay | Adresse RAM | Taille | Fichiers de `/data/prm` référencés |
|---|---|---|---|
| 0 | `0x021536E0` | 199 488 | `mon_btldata`, `mon_data` |
| 2 | `0x021536E0` | 105 664 | `skilltable`, `spelltable` |
| 14 | `0x021842A0` | 21 856 | `enchab`, `mon_list`, `mons_info` |
| **17** | `0x0218B5A0` | 314 688 | **`encbtl`, `encfld`, `encmons`, `fld_mondata`**, `mon_data` |
| 23 | `0x021D8A40` | 159 648 | `mon_data`, `skilltable`, `spelltable` |
| **25** | `0x021D8A40` | 93 984 | **`mon_btldata`**, `mon_data` |
| 26 | `0x021D8A40` | 25 792 | `skilltable`, `spelltable` |

Lecture : les overlays **0 et 25** portent le système de combat, l'overlay **17**
porte le système de rencontres. Ce sont les trois cibles pour Ghidra.

Chaînes présentes aussi dans l'ARM9 décompressé, donc toujours résidentes :

| Chaîne | Offset ARM9 | Adresse RAM |
|---|---|---|
| `data/prm` | `0xEF0B5` | `0x020EF0B5` |
| `mon_btldata` | `0xF0B6D` | `0x020F0B6D` |
| `encmons` | `0xF24CC` | `0x020F24CC` |

À noter : `mon_data_<LG>.nat` apparaît comme gabarit de nom de fichier avec un
marqueur de langue `<LG>`. Il n'existe pas de `mon_data_en.nat` dans le NitroFS :
ces variantes par langue sont donc probablement **à l'intérieur** du conteneur
`mon_data.gp2`. C'est très vraisemblablement là que se trouvent les noms de
monstres, ce qui en fait la clé pour résoudre les id de chaîne `+0x04`/`+0x06`.

## 10. Preuve que le moteur utilise bien `mon_btldata.nat`

Deux constats indépendants, tous deux vérifiables par script.

**1. Le fichier est référencé par son chemin complet dans le code.**
La chaîne littérale `data/prm/mon_btldata.nat` est présente dans l'ARM9 décompressé
(toujours résident) ainsi que dans les overlays 0 et 25 (système de combat).

**2. Il n'existe aucune autre copie de ces données dans la ROM.**
En cherchant l'enregistrement de 132 octets du Métal Gluant dans l'intégralité de la
ROM — `arm9` décompressé, `arm7`, les 35 overlays décompressés, et les
7 481 fichiers du NitroFS — on le trouve dans **un seul fichier** :
`/data/prm/mon_btldata.nat`.

Le moteur n'a donc nulle part ailleurs où prendre ces valeurs.

### Ce que cette preuve ne couvre pas

Elle établit que le fichier est la source unique et qu'il est ouvert par le code.
Elle n'établit pas que **chaque champ** est interprété comme je le suppose. Le
mappage HP/attaque/défense/agilité/expérience/or est par ailleurs confirmé par les
signatures de monstres et par la concordance avec `fld_mondata.bin`, mais les champs
encore marqués `?` en §4 restent des inconnues.

### Pourquoi une recherche d'octets en RAM ne suffit pas

Vérifié : aucun des 60 fichiers de `/data/prm` n'est présent en RAM lors de la
séquence d'ouverture (Observatoire), pas même `level0.bin`. Ils sont chargés à la
demande. Et la structure d'exécution d'un ennemi en combat fait **0xA4 = 164 octets**
(source communautaire) contre 132 dans le fichier : le moteur convertit les données
au chargement au lieu de conserver les octets bruts.

Conclusion : la confirmation en jeu doit comparer des **valeurs** lues dans la
structure d'exécution pendant un combat, pas chercher des octets identiques.

## 11. `encbtl.bin` et `encfld.bin` — jeu de tags élargi

La première version du parseur n'acceptait que les tags `0x64`/`0x65`/`0x66` et
rendait **0 enregistrement** sur ces deux fichiers. En élargissant le jeu accepté à
`0x60`–`0x6F`, les deux se parsent presque entièrement :

| Fichier | Enregistrements | Reste non parsé | Formes rencontrées |
|---|---|---|---|
| `encbtl.bin` | 2 874 / 2 877 | 40 o | tag `0x67` × 1 champ (×1526), `0x66` × 2 champs (×1058), `0x68` × 1 champ (×290) |
| `encfld.bin` | 1 827 / 1 830 | 52 o | tag `0x67` × 2 champs (×1043), `0x68` × 1 champ (×287), `0x66` × 1 champ (×287), `0x69` × 5 champs (×210) |

Les quelques dizaines d'octets restants en fin de fichier sont probablement un
enregistrement de queue d'une forme encore inconnue.

### Les identifiants de carte — CONFIRMÉ par recoupement

Le premier champ des enregistrements `0x69` d'`encfld.bin` et des enregistrements
`0x66` d'`encmons.bin` prend les valeurs `20001`, `20055`, `7301`, `7102`…

La recherche communautaire documente, dans l'interpréteur de `data/map/maplist9.bin`,
une carte d'identifiant **`0x4E22`**. Or `0x4E22 = 20002`, et `0x4E21 = 20001` est
exactement la première valeur trouvée ici.

**Ce champ est donc un identifiant de carte.** Les deux fichiers indexent les
rencontres par zone, ce qui est précisément la structure qu'il faut pour randomiser
les espèces rencontrées (axe B de `PLAN.md`).

### Reste à faire

- Élucider la sémantique des paires de u16 dans les enregistrements `0x66` à
  5 champs d'`encmons.bin`. Pour la carte 20001 : `(57,1) (32,56) (63,23)` ;
  pour la carte 7301 : `(48,36) (15,45)` ; pour la 20055 : `(89,55)`.
  **HYPOTHÈSE** : `(id_monstre, poids)` ou `(id_monstre, niveau)`. Les sommes des
  seconds éléments (80, 81, 55) ne font pas 100, donc ce ne sont pas directement
  des pourcentages.
- Identifier le rôle respectif de `encbtl` (combat) et `encfld` (terrain).
- Croiser avec l'overlay 17, qui référence les quatre fichiers, via Ghidra.

## 12. Confirmation causale en jeu — CONFIRMÉ

La preuve statique de la §10 établissait que le fichier est la source unique et
qu'il est ouvert par le code. Voici la confirmation par observation.

### Montage

`scripts/sentinel_patch.py` produit une ROM où chaque monstre d'index *i* porte
`HP = 20000 + i` et `MP = 3000 + i`. Ces valeurs sont **impossibles dans la table
d'origine**, dont le MP ne dépasse jamais 255. Aucune collision sur les HP non plus
(vérifié : 0 sur 438).

Le mode `shuffle` du randomizer ne convient **pas** pour cette vérification : c'est
une permutation, donc la ROM randomisée contient exactement le même ensemble de
blocs de stats que l'originale. Toute valeur retrouvée matche alors les deux tables
et ne permet de rien conclure. C'est pour cela que les sentinelles existent.

`scripts/lua/monkey.lua` traverse ensuite l'introduction et la création de
personnage en martelant les touches, puis marche au hasard, et enregistre un
savestate périodiquement. Le combat d'introduction est atteint vers la frame 18 000,
soit environ 6 minutes de temps machine, sans aucune intervention.

### Le piège statistique à ne pas reproduire

Une première version du vérificateur concluait dès qu'elle retrouvait les 438
valeurs de MP sentinelles en RAM. **C'était faux.** Dans un bloc mémoire de 16,8 Mo,
une valeur donnée sur 2 octets apparaît par pur hasard environ
`16,8e6 / 65536 ≈ 256` fois. Les comptages observés (94, 34, 24, 40…) sont même
*en dessous* de ce bruit de fond. Retrouver une valeur sur 2 octets ne prouve rien.

Le critère retenu est donc l'**enregistrement complet de 132 octets**. La
probabilité qu'une séquence de 132 octets précise apparaisse par hasard est de
l'ordre de 2⁻¹⁰⁵⁶.

### Résultat

| Savestate | Contexte | Enregistrements de 132 o retrouvés intacts |
|---|---|---|
| frame 12 033 | hors combat (Observatoire) | **0 / 438** — témoin négatif |
| frame 18 030 | **pendant un combat** | **4 / 438** |

Les quatre trouvés sont les index 277, 278, 279 et 280, aux adresses `0xF5F8C2`,
`0xF5F946`, `0xF5F9CA`, `0xF5FA4E` — **espacées exactement de 132 octets**.

### Ce que cela établit

1. Le moteur lit bien `data/prm/mon_btldata.nat`, et il lit la version patchée.
2. Il en charge une **tranche contiguë à la demande**, et non la table entière :
   le fichier complet n'est jamais présent d'un seul tenant en RAM, et hors combat
   aucun enregistrement ne s'y trouve.
3. Les enregistrements sont recopiés **verbatim**, sans conversion de format. La
   structure d'exécution de 0xA4 = 164 octets décrite par la communauté est donc
   une structure *distincte*, construite à côté, et non une transformation de
   l'enregistrement du fichier.

Le chemin complet est donc validé de bout en bout : **modifier ce fichier modifie
ce que le moteur charge en mémoire pendant un combat.**

## 13. Compression interne des archives GPC2 — type 1 porté

Chaque bloc d'une archive GPC2 (index, table de noms, et chaque fichier interne)
est précédé d'un u32 de contrôle : `type = u32 & 7`, `taille = u32 >> 3`.
Types : 0 = brut, 1 = algorithme A, 2 et 3 = B, 4 = C.

### L'algorithme A est un LZSS classique — CONFIRMÉ

Le source C++ d'`ArchiveTool` fait 176 lignes truffées de `goto`, mais il contient
une variable `compressionType` initialisée à 0 et **jamais réassignée**. Toute la
branche `if (compressionType == 1)` est du code mort. Ce qui reste :

```
octet de contrôle -> 8 drapeaux, lus du bit de poids fort vers le poids faible
  drapeau 0 : recopier un octet littéral
  drapeau 1 : lire deux octets b1 b2, puis recopier depuis la sortie
                longueur = (b1 >> 4) + 3                    (3 à 18)
                distance = 1 + (((b1 & 0xF) << 8) | b2)     (1 à 4096)
```

Recoupement avec le compresseur du même dépôt, qui écrit
`((longueur - 3) << 4) | (distance_moins_un >> 8)` puis `distance_moins_un & 0xFF` :
le décompresseur calcule `0x30 + b1`, et comme `0x30 = 3 << 4`, cela reconstitue
`(longueur << 4) | (distance_moins_un >> 8)`. Les deux sens concordent exactement.

Implémentation : `scripts/lz_dq9.py`. Validée du premier coup — la table de noms de
`mon_data.gp2` rend `mon_data_de.nat`, `mon_data_en.nat`, `mon_data_es.nat`,
`mon_data_fr.nat`, `mon_data_it.nat`.

### Types 2, 3 et 4

Portés eux aussi dans `scripts/lz_dq9.py`. Le type 4 est un RLE trivial (bit 7 du
mot de contrôle : littéraux ou répétition). Les types 2 et 3 forment un décodeur
binaire à table, dont le source d'origine contient une soustraction **non signée
qui déborde** — reproduite à l'identique, faute de savoir si c'est un bug ou une
intention.

Bilan sur les 163 fichiers internes des 40 archives `.gp2` de `/data/prm` :
**152 extraits, 11 en échec.**

| Cause de l'échec | Nombre | Statut |
|---|---|---|
| compression de **type 7** | 5 | non documentée. Le source communautaire note lui-même « 5-7 are unknown ». |
| type 2 ou 3, taille annoncée absurde | 6 | 2 à 3,8 Mo annoncés depuis une archive de 212 Ko, soit un ratio de 60x. Le mot de contrôle est probablement mal lu pour ces entrées, ou mon portage de `DecompressB` est fautif. |

Les 11 fichiers concernés sont tous des `actdt_*` — des données de compétences,
sans rapport avec les monstres. Non bloquant, laissé en suspens.

### Piège d'appariement des noms

Dans l'archive, les noms de la table de noms correspondent aux entrées de l'index
**triées par offset masqué**, pas par hash (c'est ce que fait `fileEntrySorter`
dans le source). Vérifié par le contenu : dans l'ordre des offsets, les langues
sortent bien `de, en, es, fr, it`, sur toutes les archives testées. Trier par hash
donne un appariement faux et **silencieux** — on obtient des noms français dans un
fichier étiqueté `_en.nat`.

## 14. Noms des monstres — CONFIRMÉ

Fichier : `mon_data_<lg>.nat`, interne à `data/prm/mon_data.gp2`, une variante par
langue. Le code du jeu référence le gabarit `mon_data_<LG>.nat`.

```
+0x00   u16   nb sur les 12 bits de poids faible : u16 & 0xFFF = 438
              Les 4 bits de poids fort sont des drapeaux qui varient selon la
              langue (0x0, 0x1, 0x3, 0xC). Même convention que le
              packedFileCount de l'en-tête GPC2.
+0x02   u16   ?
+0x04         438 enregistrements de 28 octets :
                +0x00  u32  offset du nom, dans le pool
                +0x04  u32  offset du code de modèle
                +0x14  u32  offset du nom au pluriel
                (les 12 autres octets restent à élucider)
        puis  un éventuel bourrage de zéros
        puis  le pool : chaînes terminées par zéro
```

Contrôle de cohérence : pour l'anglais, `4 + 438 × 28 = 12 268 = 0x2FEC`, qui est
exactement l'offset de la chaîne `slime`. Et les 438 offsets de nom pointent tous
sur un début de chaîne réel, **dans les cinq langues**.

C'est donc une correspondance **directe index → nom**, pour les 438 enregistrements.
Implémentation : `scripts/monnames.py`.

### Balisage du texte

Diacritiques : `<'e>` = é, `` <`a> `` = à, `<^e>` = ê, `<:a>` = ä, `<~n>` = ñ,
`<ss>` = ß. Flexion grammaticale, surtout en allemand et en français :
`[gs]` génitif singulier, `[adjf]` adjectif féminin, `[sgl_inf_1]`… Le moteur les
résout à l'affichage ; ce sont des parasites pour nous.

### Trois validations croisées

**1. Sémantique contre statistiques.** Tout monstre dont le nom contient
« metal slime » a une défense hors norme, sans exception sur 7 entrées :

| index | nom | HP | DÉF | XP |
|---|---|---|---|---|
| 2 | metal slime | 4 | 256 | 4 096 |
| 26 | liquid metal slime | 8 | 256 | 40 200 |
| 112 | metal slime knight | 46 | 140 | 305 |
| 167 | **metal king slime** | 16 | **512** | 54 504 |

**2. Les boss historiques de la série** sont aux index 330 à 344, identifiants
**500 à 514 consécutifs**, modèles `b100a` à `b112a` dans l'ordre exact de DQ1 à
DQ8 — Dragonlord, Malroth, Baramos, Zoma, Psaro, Estark, Nimzo, Murdaw, Mortamor,
Orgodemir, Dhoulmagus, Rhapthorne, Nokturnus — tous entre 6 000 et 8 500 HP.

**3. Les boss du scénario de DQ9** sont aux index 292 à 302, dans l'ordre de
l'histoire, avec **King Godwyn et Corvus en deux formes** chacun
(modèles `b019a`/`b020a` et `b022a`/`b023a`).

Une seule entrée sur 438 n'a pas de nom : l'index 437, identifiant 900 — le
mannequin d'entraînement à 32 000 HP. 55 noms sont portés par plusieurs entrées :
ce sont les variantes renforcées des grottes (`stenchurion` à 160 puis 300 HP).

### Correction d'une erreur de méthode

Un premier essai reconstituait la correspondance en **regroupant** les chaînes du
pool par triplets `(nom, pluriel, code de modèle)`. Cette heuristique donnait un
alignement faux, décalé de 3 à partir de l'index 249, parce que le pool contient
5 groupes dépourvus de nom (deux codes de modèle consécutifs). Elle plaçait
`Dragonlord` là où se trouve en réalité `Dreadmaster`.

La lecture de la table d'enregistrements de 28 octets supprime toute heuristique :
elle donne l'offset exact du nom de chaque monstre.

## 15. Tables de rencontres — DÉCODÉ

Trois fichiers de `/data/prm`, tous au format de table taggée de la §3. L'overlay
ARM9 **17** est celui qui les référence, avec `fld_mondata.bin`.

| Fichier | Enregistrements | Rôle |
|---|---|---|
| `encmons.bin` | 209 | liste des espèces par carte |
| `encfld.bin` | 1 827 | rencontres sur le terrain |
| `encbtl.bin` | 2 874 | rencontres en combat |

### Où sont les identifiants — mesuré, pas supposé

Pour chaque combinaison (fichier, tag, nombre de champs, position), on a compté la
proportion de valeurs non nulles qui sont des identifiants de monstre valides,
selon plusieurs découpages. Le résultat ne laisse pas de place au doute :

| Fichier | Tag | Champ | Valeurs | 12 bits de poids faible = id valide |
|---|---|---|---|---|
| `encbtl.bin` | `0x66` | 0 | 1 058 | **100,0 %** |
| `encbtl.bin` | `0x67` | 0 | 1 526 | **100,0 %** |
| `encfld.bin` | `0x67` | 0 | 1 043 | **100,0 %** |

Soit 3 627 valeurs dont les 12 bits de poids faible sont *toutes* des identifiants
valides. Il n'y a que 438 identifiants valides parmi 65 536 valeurs possibles :
un tel taux est impossible par hasard.

Les bits de poids fort portent autre chose. Dans `encfld.bin` tag `0x67`,
`valeur >> 12` ne prend que les valeurs 0 à 7 — vraisemblablement un poids ou une
probabilité d'apparition. On les préserve tels quels.

### `encmons.bin` — les espèces par carte

Enregistrements de tag `0x66`, de 3 à 5 champs :

```
champ 0        identifiant de carte
champs 1..n    deux u16, chacun pouvant porter un identifiant de monstre
```

Le **u16 de poids fort** est un identifiant valide à 100 % / 99,2 % sur tous les
champs de données. Le u16 de poids faible l'est la plupart du temps, mais seulement
14 % sur un champ : son sens exact n'est pas élucidé.

Confirmation de l'identifiant de carte : la documentation communautaire de
`data/map/maplist9.bin` cite la carte `0x4E22` = 20002 ; la première valeur trouvée
ici est `0x4E21` = 20001.

Validation sémantique, une fois les noms disponibles :

| Carte | Espèces |
|---|---|
| 20001 | cruelcumber, slime, batterfly, teeny sanguini, sacksquatch, bodkin archer |
| 7102 | bag o' laughs, firespirit, spirit, funghoul, mecha-mynah, dracky |
| 40412 | seavern, pale whale, drakulord, hammer horror, prime slime |

Groupes homogènes en difficulté, et les cartes se classent proprement par index
médian du bestiaire : 13 pour les zones de départ, 234 à 268 pour les zones finales.
1 à 6 espèces par carte, 5 le plus souvent.

### Autres tags, non élucidés

- `encfld.bin` tag `0x69`, 5 champs : le champ 0 est un identifiant de carte, les
  quatre autres sont nuls sur les 210 enregistrements. Enregistrement d'en-tête.
- Tag `0x68`, 1 champ, 289 valeurs distinctes toutes inférieures à 4 096 : apparaît
  comme séparateur avant chaque suite de `0x66`/`0x67`. Probablement un
  identifiant de groupe de rencontre.
- `encfld.bin` tag `0x66`, 1 champ : 38 % seulement d'identifiants valides,
  sémantique inconnue.
- Une trentaine d'octets en fin de `encbtl.bin` et `encfld.bin` ne sont pas parsés.

### Règle de prudence appliquée à l'écriture

`scripts/enctables.py` ne réécrit **que les emplacements qui contiennent déjà un
identifiant valide**, aux positions mesurées ci-dessus. Un champ dont le sens est
inconnu reste donc intact par construction — il est impossible de le corrompre.

Total : **4 525 références d'espèce** réécrivables
(`encbtl` 2 584, `encfld` 1 043, `encmons` 898).

### État de la vérification — à lire avant de se fier à cette section

Le décodage ci-dessus est solide au niveau du **fichier** : les positions des
identifiants sont mesurées à 100 % sur 3 627 valeurs, la réécriture est vérifiée
(permutation stricte, 0 incohérence, aucune valeur invalide écrite), et les
groupes par carte sont sémantiquement cohérents.

En revanche, **la confirmation en jeu n'est pas encore obtenue.** Deux constats :

1. Sur la ROM randomisée, le combat du prologue (Observatoire, héros niveau 1
   accompagné d'Aquila) fait apparaître **les mêmes espèces que la ROM d'origine**
   — `slime` et `cruelcumber`, qui sont la liste d'origine de la carte 20001 et
   non la liste randomisée.
2. Aucun enregistrement des trois tables de rencontres, ni d'origine ni patché,
   n'est retrouvé en RAM dans les savestates pris jusqu'ici — alors que la table
   de stats patchée y est retrouvée (4 enregistrements de 132 octets, cf. §12).

Deux explications restent possibles et ne sont pas départagées :

- le prologue est **scripté** et ne consulte pas ces tables, les espèces y étant
  définies dans les données d'événement (`/data/event`, `/data/scenario`) ;
- le moteur **convertit** ces tables au chargement au lieu de les garder telles
  quelles, ce qui rend une recherche d'octets aveugle. La documentation
  communautaire décrit justement une « monster table » en RAM à `0x020FDDC4`
  alimentée par `ChooseFieldMonsterId`, donc une structure d'exécution.

Ne pas confondre « les octets du fichier sont correctement modifiés », qui est
établi, avec « le jeu se comporte différemment », qui ne l'est pas encore.

Test en cours pour trancher : une ROM où **toutes** les espèces rencontrables sont
remplacées par le `metal slime` (identifiant 3, 4 HP, défense 256, apparence
métallique). 4 516 références sur 4 525 remplacées, seul le marqueur
d'emplacement vide `65535` subsiste. Si les tables alimentent le moteur, toute
rencontre non scriptée doit alors faire apparaître un métal gluant et rien
d'autre — une différence qu'on ne peut pas rater à l'œil, contrairement à une
substitution entre deux espèces voisines.
Produit par `scripts/enc_sentinel.py`.

## 16. `data/event/eventbattle.bin` — les combats scriptés — CONFIRMÉ

Trouvé en cherchant les chaînes de chemin de fichier dans le code : la chaîne
`data/event/eventbattle.bin` est référencée par l'**ARM9 décompressé** et par
l'**overlay 17**.

C'est ce fichier qui explique pourquoi randomiser `encmons`/`encfld`/`encbtl` ne
change rien au combat du prologue.

Format : en-tête court (corps à `0x10`), 98 enregistrements de tag `0x64` à
**9 champs u32** :

```
champ 0   identifiant d'événement            1 à 142
champ 1   identifiant du monstre 1           100 % d'identifiants valides
champ 2   effectif du monstre 1              1 à 8
champ 3   identifiant du monstre 2           ou 0xFFFFFFFF si l'emplacement est vide
champ 4   effectif du monstre 2
champ 5   identifiant du monstre 3           ou 0xFFFFFFFF
champ 6   effectif du monstre 3
champ 7   ?                                  15 valeurs distinctes, 23 à 38
champ 8   identifiant de message             30116 à 30903
```

### Validation

Le contenu est le bestiaire de boss complet de DQ9, dans l'ordre du scénario :
Wight Knight, Morag, Ragin' Contagion, Master of Nu'un, Lleviathan, Garth Goyle,
Tyrantula, Grand Lizzier, Dreadmaster, Larstastnaras, Gadrongo, Greygnarl, le trio
Gittish (Goreham-Hogg, Hootingham-Gore, Goresby-Purrvis), King Godwyn, Corvus,
Barbarus — puis les boss historiques Dragonlord → Rhapthorne **répétés trois fois**,
ce qui correspond aux trois paliers de difficulté des re-combats de fin de jeu.

Les combats à plusieurs adversaires sont cohérents :
`[17] bad karmour, Hootingham-Gore, bad karmour` et
`[54] right claw, Mortamor, left claw`.

### La preuve du prologue

L'enregistrement `[26]` vaut `1x slime, 1x cruelcumber, 1x slime` — exactement ce
qu'affiche l'écran lors du combat du prologue (héros niveau 1 accompagné d'Aquila).

Les identifiants employés sont 290 et 292, **pas** 1 et 57 : ce sont les doublons
du bestiaire (`slime` porte les identifiants 1, 249, 250, 290, 291 avec des stats
parfois identiques). C'est cohérent avec la §14, qui relevait 55 noms portés par
plusieurs entrées.

Test décisif : une ROM où **toutes** les espèces des trois tables de rencontres
sont remplacées par le `metal slime` laisse le combat du prologue **inchangé**
(`slime` et `cruelcumber` à l'écran). Le combat est donc bien scripté, et lu depuis
`eventbattle.bin`.

### Randomisation

`scripts/enctables.py` gère ce fichier, mais le randomizer le traite sous un
**drapeau distinct** `--boss`, séparé de `--rencontres`. Raison : toucher aux boss
du scénario est bien plus risqué pour la progression qu'échanger des espèces de
terrain. Un boss de fin trop faible banalise la partie ; un boss précoce trop fort
la bloque.

Références réécrivables : 112 dans `eventbattle.bin`, ce qui porte le total à
**4 637** avec les trois tables de rencontres.

### Confirmation causale en jeu — CONFIRMÉ

Deux ROMs identiques sauf sur un point : dans l'une, `eventbattle.bin` est patché
(toutes les espèces remplacées par le `metal slime`, identifiant 3) ; dans l'autre,
seules les trois tables de rencontres le sont. Même graine de martelage, donc même
déroulement, et savestate pris au même numéro de frame pendant le combat du
prologue.

On cherche ensuite en RAM la structure d'exécution de l'ennemi, décrite par la
communauté comme `+0x04 maxHP, +0x06 maxMP, +0x08 attaque, +0x0A défense`, soit
8 octets consécutifs par monstre.

| Occurrences en RAM | `metal slime` (4/255/35/256) | `slime` id 290 (8/2/10/7) | `cruelcumber` id 292 (10/2/12/9) |
|---|---|---|---|
| `eventbattle` **non** patché | 1 | **3** | **2** |
| `eventbattle` **patché** | **5** | **0** | **0** |

Sans le patch, la RAM contient trois structures de gluant et deux de cruelcumber —
ce que l'écran affiche (deux gluants et un cruelcumber, plus des emplacements
d'état supplémentaires). Avec le patch : plus aucune des deux espèces, et cinq
métaux gluants.

L'inversion est totale et va dans les deux sens. C'est la preuve causale :
**modifier `eventbattle.bin` change les monstres que le moteur instancie.**

### Ce qui reste non confirmé en jeu

Les trois tables de rencontres de terrain (`encmons`, `encfld`, `encbtl`) sont
décodées et réécrites correctement au niveau du fichier, mais leur effet en jeu
n'est pas encore observé : le prologue ne les consulte pas. Il faut atteindre une
zone de jeu libre, ce qui demande un run bien plus long.

## 17. `ChooseFieldMonsterId` désassemblée — le format confirmé par le code

Adresse EUR fournie par la communauté : `0x02073FEC`. Elle tombe dans l'ARM9
(`0x02000000` à `0x020F4618` après décompression), donc à l'offset `0x73FEC` du
fichier `work/dumps/code/arm9_decompresse.bin`. Désassemblé avec `capstone`.

```
02073fec  push  {r3, r4, r5, lr}
02073ff0  mov   r4, r0              ; r0 = pointeur sur la table en RAM
02073ff4  mov   r0, #0              ; total = 0
02073ff8  mov   r2, r0              ; i = 0
; --- premiere boucle : somme des poids ---
02074000  add   r1, r4, r2, lsl #2  ; entree de 4 OCTETS, indexee par i
02074004  ldrh  r1, [r1, #8]        ; u16 de l'entree, table a partir de +8
02074008  add   r2, r2, #1
0207400c  lsl   r1, r1, #0x11       ; << 17
02074010  add   r0, r0, r1, lsr #29 ; total += (x << 17) >> 29
02074014  ldrh  r1, [r4, #2]        ; nombre d'entrees = u16 a +2
0207401c  blt   #0x2074000
02074020  bl    #0x2032380          ; tirage aleatoire
; --- seconde boucle : loterie ponderee ---
02074030  add   r3, r4, #8
0207403c  ldrh  r1, [r3, r1]
02074044  add   lr, lr, r2, lsr #29 ; cumul des poids
02074048  cmp   r0, lr              ; comparaison au tirage
0207404c  lsllt r0, r1, #0x14       ; << 20
02074050  lsrlt ip, r0, #0x14       ; >> 20  -> garde les 12 bits de poids faible
02074068  mov   r0, ip              ; valeur de retour
0207406c  pop   {r3, r4, r5, pc}
```

Lecture des deux extractions de bits :

| Instruction | Effet | Signification |
|---|---|---|
| `(x << 17) >> 29` | garde les bits **12 à 14** | poids sur 3 bits, donc 0 à 7 |
| `(x << 20) >> 20` | garde les bits **0 à 11** | identifiant de monstre sur 12 bits |

**C'est la confirmation par le code du format déduit en §15.** Les deux mesures
statistiques concordent avec la mécanique réelle :

- les 12 bits de poids faible sont un identifiant valide à 100 % sur 3 627 valeurs
  → c'est bien le champ que la fonction retourne ;
- `valeur >> 12` ne prend que les valeurs 0 à 7 dans `encfld.bin` tag `0x67`
  → c'est bien un poids sur 3 bits.

La fonction implémente une loterie pondérée classique : somme des poids, tirage,
puis parcours cumulatif jusqu'à dépasser le tirage.

### Ce qui reste inféré plutôt que prouvé

La fonction lit une table **en RAM**, dont le pointeur lui est passé en `r0`. Le
chaînage fichier → table RAM n'a pas été tracé instruction par instruction. Ce qui
est établi : le fichier contient exactement la disposition que le code consomme
(4 octets, 12 bits d'identifiant, 3 bits de poids), et c'est la seule source de ces
identifiants dans toute la ROM. La conclusion est solide mais reste une inférence
sur ce dernier maillon.

### Pourquoi la confirmation en jeu n'a pas abouti

Trois tentatives, toutes bloquées par le harnais et non par la ROM — détail dans
`docs/JOURNAL.md`. La dernière : le pilote automatique reste coincé dans le combat
du prologue, sans jamais valider d'attaque. Atteindre une zone de jeu libre
demanderait soit un pilotage bien plus fin, soit une sauvegarde de partie déjà
avancée.

## 18. Sauvegarde de partie et adresses RAM issues des codes de triche

### Le dossier fourni

Structure DeSmuME (`Battery`, `Cheats`, `States`, `StateSlots`), issue d'une partie
réellement jouée. La ROM qu'il contenait est **identique au bit près** à la ROM de
référence (`3a63438fff7db282fa3133e8fd020e85`), donc tous les offsets et adresses
de ce document s'y appliquent sans revalidation. Ce doublon de 256 Mo a été
supprimé ; les fichiers utiles sont recopiés dans `work/save_origine/`.

### Format `.dsv` de DeSmuME

```
[donnees de sauvegarde brutes]
"|<--Snip above here to create a raw sav by excluding this DeSmuME savedata footer:"
u32 x6  champs du pied : 0x8011, 0x10000, 0x3, 0x2, 0x10000, 0x0
"|-DESMUME SAVE-|"
```

Le fichier s'auto-documente : le marqueur `|<--Snip above here` indique exactement
la fin des données brutes. Ici **65 536 octets** (64 Kio, soit 512 Kibit), ce que
confirme le champ `0x10000` du pied.

Extraction : `work/save_origine/dq9.sav`.

### Structure interne : deux copies miroir

Le profil d'occupation par bloc de 4 Kio est **rigoureusement identique** entre
`0x00000-0x07FFF` et `0x08000-0x0FFFF` (46,6 / 29,6 / 65,5 / 43,6 / 14,3 / 11,6 /
8,3 / 100 %, deux fois). DQ9 conserve donc deux copies de 32 Kio : une principale
et une de secours. À garder en tête pour tout patch de sauvegarde — modifier une
seule des deux copies risque de faire échouer le contrôle d'intégrité du jeu.

### Conversion vers BizHawk

BizHawk attend la sauvegarde dans `NDS/SaveRAM/`, au format **brut** (identique à
celui extrait ci-dessus), et nomme le fichier d'après le **nom interne du jeu**,
pas d'après le nom du fichier de ROM. Les underscores y deviennent des espaces :
la ROM `dq9_encsent3.nds` attend `dq9 encsent3.SaveRAM`. Une copie nommée
`dq9_encsent3.SaveRAM` est ignorée en silence.

Le nom interne est lisible depuis Lua avec `gameinfo.getromname()`.

### Adresses RAM EUR issues du fichier de triche

Le fichier `.dct` fourni contient des codes Action Replay pour `NTR-YDQP-EUR`,
donc des adresses **EUR authentiques**, vérifiées par l'usage.

| Adresse | Effet du code | Intérêt |
|---|---|---|
| `0x020FD764` | niveau de l'auberge | bloc d'état global |
| `0x020FD768` | livre d'or | idem |
| `0x020FD76C` | améliorations de l'auberge | idem |
| `0x020FD778` | salles de visiteurs débloquées | idem |
| `0x020FA92A` | nombre de visiteurs | idem |
| `0x02108B11`…`0x02108B75` | drapeaux de quêtes | table de progression |
| `0x021098C0`…`0x021098D8` | contenus additionnels | — |
| `0x0215525C`, `0x02155270` | patch de code (2 instructions) | zone d'**overlay** (`0x021536E0`+) |
| `0x02066A58` | patch de code : vitesse du texte | ARM9 |
| `0x020A2358`, `0x020A23C8` | patch de code : caméra libre | ARM9 |
| `0x023893D1`, `0x023893E4`, `0x02389404` | déblocage de la boutique DQVC | haut de la RAM principale |

**Recoupement notable.** Le bloc `0x020FD764`-`0x020FD778` est adjacent aux deux
adresses documentées par la communauté : `0x020FDAAC` (structure de carte) et
`0x020FDDC4` (table de monstres lue par `ChooseFieldMonsterId`, cf. §17). La zone
`0x020FD000`-`0x020FE000` est donc le bloc d'état global du jeu. Deux sources
indépendantes convergent, ce qui renforce la fiabilité des deux.

Le code `94000130 FFFB0000` présent plusieurs fois est le conditionnel standard
« touche SELECT enfoncée » : `0x04000130` est le registre `KEYINPUT` du NDS.

### Confirmation en jeu des rencontres de terrain — CONFIRMÉ

Obtenue avec une sauvegarde de partie avancée fournie par l'utilisateur, qui a
amené le groupe en pleine plaine et enregistré un savestate (`work/save_origine/
plaine_utilisateur.State`).

**Montage.** ROM `dq9_encsent3.nds` : les 4 510 références d'espèce des trois
tables de rencontres remplacées par l'espèce 1, `data/event/eventbattle.bin`
laissé intact. Produit par `scripts/enc_sentinel2.py`.

**Constat visuel.** La plaine ne contient plus que des gluants, là où elle
présentait normalement des espèces variées.

**Lecture en direct de la mémoire**, sur le savestate, à l'adresse EUR
`0x020FDDC4` documentée par la communauté, en appliquant le format déduit du
désassemblage (§17) :

```
ChooseFieldMonsterId @020FDDC4 :  nb = 4
    ids   = {1, 1, 1, 1}
    poids = {3, 3, 5, 5}
```

Les quatre emplacements portent l'identifiant **1**, celui de la sentinelle. Les
poids sont bien des valeurs sur 3 bits.

**La chaîne est donc complète et vérifiée maillon par maillon :**

| Maillon | Vérification |
|---|---|
| fichier patché | 4 510 références réécrites, permutation stricte |
| table en RAM | `ids = {1,1,1,1}` lus à `0x020FDDC4` |
| format des entrées | 4 octets, id sur 12 bits, poids sur 3 bits — désassemblage §17 |
| code consommateur | `ChooseFieldMonsterId` retourne les 12 bits de poids faible |
| rendu à l'écran | uniquement des gluants dans la plaine |

Le maillon « fichier → table RAM », qui restait une inférence en §17, est
maintenant établi par l'observation.

## 19. Patch de code : apparitions totalement aléatoires

### Le problème que ça résout

Randomiser les tables de rencontres ne change que la **liste** des espèces d'une
zone — 4 à 6 par carte. Dans une zone donnée on croise donc toujours les mêmes
4 à 6 monstres, simplement différents de ceux d'origine. Pour que n'importe quel
monstre puisse apparaître n'importe où, à chaque fois, il faut agir sur le code.

### Ce qui a été remplacé

`ChooseFieldMonsterId`, adresse EUR `0x02073FEC` (§17), 132 octets disponibles.
Le corps est remplacé par 68 octets, 18 instructions :

```
push  {r3, lr}
mov   r0, #320          ; 320 + 10 = 330 especes exploitables
add   r0, r0, #10
bl    #0x2032380        ; RNG du jeu : r0 = borne en entree,
                        ; r0 = tirage dans [0, borne) en sortie
add   r0, r0, #1
cmp   r0, #65           ; les quatre trous de la plage d'identifiants,
addge r0, r0, #10       ; franchis par additions conditionnelles :
cmp   r0, #154          ;   65..74, 154..156, 209..211, 299
addge r0, r0, #3
cmp   r0, #209
addge r0, r0, #3
mov   r1, #256          ; 299 n'est pas un immediat encodable, on le construit
add   r1, r1, #43
cmp   r0, r1
addge r0, r0, #1
pop   {r3, lr}
bx    lr
```

La convention d'appel du RNG est déduite du code d'origine : avant le `bl`, `r0`
contient la somme des poids ; après, `r0` est comparé aux cumuls. C'est donc un
`rand_below(n)`.

### Pourquoi 330 espèces

Les identifiants de 1 à 347 comptent **330 espèces valides**, en cinq blocs
contigus séparés par quatre petits trous. Les additions conditionnelles
transforment un tirage dans 0..329 en identifiant valide, et la couverture est
**exacte** : 330 tirages donnent les 330 identifiants, sans doublon ni invalide
(vérifié par énumération).

Au-delà de 347 les identifiants sont clairsemés — 500-514 (boss historiques),
600-660, 747-779, 800-801, 900 (variantes de grotte et entrées de test). Les
inclure exigerait une table injectée, et l'ARM9 décompressé ne contient **aucune
plage libre de 512 octets** (vérifié).

### Trois pièges rencontrés

**1. `mov r0, #330` s'assemble en `MOVW`.** C'est de l'ARMv6T2, alors que l'ARM9
du DS est un ARMv5TE. Keystone l'accepte sans prévenir et le résultat planterait
sur la console. D'où `mov #320` puis `add #10`. Un garde-fou dans
`scripts/patch_spawn.py` redésassemble systématiquement le code produit et refuse
`movw`, `movt`, `sdiv`, `udiv` et compagnie.

**2. `cmp r0, #299` est refusé.** Les immédiats ARM sont des valeurs 8 bits
tournées d'un nombre pair de bits ; 299 n'en fait pas partie. D'où le registre de
travail. **Règle : tout immédiat supérieur à 255 doit être vérifié.**

**3. Un savestate annule un patch de code.** C'est le piège le plus coûteux. Un
savestate restaure l'**intégralité** de la RAM, code compris. Charger un
savestate pris sur une ROM non patchée réécrit donc la fonction patchée par
l'originale — et la lecture mémoire montrait bien le code d'origine, ce qui
faisait croire à un patch défaillant. **Un patch de code ne se teste qu'au
démarrage à froid, en chargeant la partie depuis la SaveRAM.**

### Ce qui est vérifié

| | |
|---|---|
| l'ARM9 se recompresse et la ROM démarre | oui (`ndspy.codeCompression`) |
| le code assemblé ne contient rien d'hors-ARMv5 | oui (garde-fou automatique) |
| le patch survit à la recompression | oui, relu et redésassemblé depuis la ROM |
| le patch est en RAM au démarrage à froid | oui, `0x02073FEC` = `E92D4008` |
| le patch est encore en RAM après chargement de la partie | oui |
| les modèles de monstres se chargent dynamiquement | oui, constaté en jeu |
| **l'effet sur les apparitions en jeu** | **non constaté** |

### Ce qui reste à constater

L'effet visible sur le terrain n'a pas été observé. Atteindre une zone de plaine
demande un démarrage à froid puis de sortir de la ville, ce que le pilotage
automatique n'a jamais réussi. Le savestate qui aurait permis de partir
directement en plaine est inutilisable ici, puisqu'il annule le patch.

Le patch est donc **techniquement établi mais fonctionnellement non confirmé** :
il est bien en mémoire et s'exécute, mais que la variété apparaisse effectivement
à l'écran reste à voir.

### Pourquoi le premier patch seul ne suffisait pas — CORRECTION

Test utilisateur : la ROM patchée se comportait comme la précédente, toujours les
mêmes quelques espèces par zone. Le patch était pourtant bien en RAM.

Diagnostic par recherche des **appelants**. Un `BL` ARM est encodé `0xEB` suivi
d'un déplacement relatif de 24 bits en mots ; en balayant l'ARM9 décompressé et
les 35 overlays, `ChooseFieldMonsterId` n'a que **deux appelants** :

| Appelant | Contexte |
|---|---|
| `0x02073CA0` (ARM9) | appelle si le pointeur de table est non nul |
| `0x021A24CC` (overlay 17) | **appelle seulement en repli** |

Le second est le chemin du terrain, et il est conditionnel :

```
021a23e4  push {r4, ...}
021a23f8  mov  r4, r3        ; r4 = QUATRIEME PARAMETRE de la fonction
...
021a24c4  cmp  r4, #0
021a24c8  bge  #0x21a24dc    ; si l'appelant a fourni un id, on saute le tirage
021a24cc  bl   #0x2073fec    ; sinon seulement, on tire
```

**L'identifiant du monstre est donc fourni en paramètre par l'appelant**, et le
tireur n'est qu'un repli pour le cas où aucun identifiant n'est disponible. Voilà
pourquoi patcher le tireur ne changeait rien au cas courant.

### Le second patch : neutraliser le court-circuit

Deux instructions remplacées par des `NOP` dans l'overlay 17, à `0x021A24C4` :

```
avant : cmp r4, #0 ; bge #0x21a24dc
apres : mov r0, r0 ; mov r0, r0
```

Tous les spawns passent alors par le tireur. `r0` porte déjà le pointeur de table
au moment du `bl`, et le tireur l'ignore de toute façon.

Le NOP employé est `mov r0, r0` (`0xE1A00000`) et non le `NOP` dédié
(`0xE320F000`), qui est de l'ARMv6K et n'existe pas sur l'ARM9 du DS.

**Écriture d'un overlay avec ndspy.** `Overlay.data` est décompressé ;
`Overlay.save(compress=True)` rend les octets compressés, à placer dans
`rom.files[overlay.fileID]`. Il faut **en plus** mettre à jour la table des
overlays : le dernier mot de l'entrée de 32 octets porte la taille compressée sur
24 bits et 8 bits de drapeaux. Sans cette mise à jour, l'overlay est chargé avec
une taille erronée. Ici la recompression rend exactement la même taille
(200 184 o), mais il ne faut pas compter sur cette coïncidence.

Vérifié dans la ROM produite : `cmp r4, #0 ; bge` est devenu
`mov r0, r0 ; mov r0, r0`, et l'ARM9 porte bien `push {r3, lr}`.

## 20. Pourquoi une randomisation « à chaque apparition » est impossible

Retour utilisateur après trois versions : chaque zone garde son lot d'espèces.
Les patchs de code n'y changeaient rien. Voici pourquoi, établi par mesure.

### L'expérience décisive

Depuis un savestate pris en pleine plaine, on écrit le patch **directement en
RAM** depuis Lua — ce qui contourne le fait qu'un savestate annule un patch de
ROM — pour forcer le tireur à toujours rendre la même espèce. Puis on marche et
on compte les appels au tireur avec `event.onmemoryexecute`.

| Espèce forcée | Monstres à l'écran | Appels au tireur |
|---|---|---|
| **1** (celle déclarée par la zone) | apparaissent immédiatement, combat engagé | **2** |
| **200** (non déclarée par la zone) | **aucun monstre** | **3 629** |

### Ce que ça établit

**Le moteur ne peut faire apparaître que les espèces dont il a préchargé le
modèle 3D au chargement de la carte**, et cette liste de préchargement est la
table de la zone. Quand le tireur rend une espèce hors liste, l'apparition
échoue et le jeu **réessaie en boucle** — d'où les 3 629 appels contre 2.

La variété par zone est donc bornée par la **taille de la table**, pas par le
hasard. Aucun patch du tireur ne peut contourner ça : il faudrait faire charger
les modèles à la demande, ce qui est un tout autre chantier (budget mémoire,
chargement d'assets).

### Le plafond réel, et le levier

| Fichier | Situation |
|---|---|
| `encmons.bin` | **564 emplacements libres** sur 209 cartes : la plupart n'utilisent que 5 places sur 8 |
| `encfld.bin` | 5 entrées par zone en moyenne, mais **certaines zones en comptent 13** |

Le second point est le plus utile : **le moteur sait déjà gérer 13 espèces dans
une zone**. Le plafond n'est donc pas 5. Augmenter le nombre d'entrées par zone
est le seul vrai levier, et il reste dans ce que le jeu fait déjà quelque part.

Remplir les emplacements libres d'`encmons.bin` fait passer la variété déclarée
de **4,3 à 6,7 espèces par carte** (`scripts/remplir_zones.py`, actif par défaut
dans le randomizer). C'est une écriture en place, sans risque : on ne touche que
des champs existants.

### Ce qui reste à faire pour aller plus loin

Ajouter des entrées à `encfld.bin` — c'est ce fichier qui semble alimenter la
table lue en RAM (nb=4 observé, cohérent avec ses ~5 entrées par zone, alors
qu'`encmons` en déclare 6 à 8 pour la même carte). Cela change la taille du
fichier, donc il faut le reconstruire : le format est connu (§3, §15), mais c'est
un travail plus engageant que les écritures en place faites jusqu'ici.

### Deux limites de méthode rencontrées

- **Un savestate figé masque les changements de table.** La table en RAM est
  construite au chargement de la carte ; un savestate la restaure telle quelle.
  Modifier les fichiers ne se voit qu'après un rechargement de zone, donc après
  avoir changé de zone en jeu.
- Vérifier qu'un patch est *présent* ne dit rien sur le fait qu'il soit *utile*.
  Il a fallu compter les appels et regarder l'écran pour comprendre.

### Statut de `--spawn-libre`

L'option est conservée mais **déconseillée** : elle produit des plaines vides et
une boucle de réessai. Elle reste documentée parce que le chemin de code qu'elle
emprunte est correct — c'est le préchargement des modèles qui l'invalide.

## 21. Structure par zone d'`encfld.bin`, et le plafond de 6

### La hiérarchie, établie par lecture séquentielle

```
tag 0x69 (5 champs)   EN-TETE DE ZONE, champ 0 = identifiant de carte
  tag 0x68 (1 champ)  debut d'un GROUPE
  tag 0x66 (1 champ)  parametres du groupe (champ de bits)
  tag 0x67 (2 champs) une ENTREE : identifiant sur 12 bits, poids sur 3 bits
  tag 0x67 ...
  tag 0x68            groupe suivant
tag 0x69              zone suivante
```

Une zone contient **plusieurs groupes**, chacun avec sa propre liste d'espèces.
La carte 20001 en compte trois, de 4, 4 et 3 entrées.

**C'est ce qui explique le `nb=4` lu en RAM** (§16) : la table chargée est **un
groupe**, pas la zone entière. Le jeu sélectionne un groupe — selon le
sous-secteur ou un critère porté par le champ de bits du tag `0x66` — et ce
groupe devient la table de spawn.

### Le plafond est 6, établi deux fois

**Par le code.** La fonction `0x02073ED4`, qui prépare la sélection, réserve
`0x30` octets de pile et y bâtit **deux tableaux de candidats** à `sp+0` et
`sp+0x18`. Soit 24 octets chacun, donc **6 entrées de 4 octets**. Aller au-delà
déborderait le cadre de pile.

**Par les données.** Distribution des entrées par groupe en vanilla, sur les
287 groupes d'`encfld.bin` :

| entrées | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| groupes | 21 | 39 | 66 | 66 | 88 | 7 |

Maximum 6, moyenne 3,6. Les deux sources concordent exactement.

### L'agrandissement

`scripts/agrandir_zones.py` porte chaque groupe à **exactement 6 entrées**, en
ajoutant des enregistrements `0x67`. Le fichier passe de 23 072 à 31 220 octets
et de 1 827 à 2 506 enregistrements ; l'en-tête est mis à jour (`nb` et taille de
données), et les 52 octets de queue non parsés sont préservés tels quels.

Résultat : la variété de terrain passe de 3,6 à **6 espèces par groupe**, soit
1,7 fois plus, sans jamais dépasser ce que le jeu fait déjà quelque part.

### Le pool d'espèces, et l'exclusion des boss

On ne tire que parmi les espèces que le jeu utilise **déjà** comme symbole de
terrain (260), moins celles qui apparaissent dans un combat scripté (5 de
recouvrement) : **255 espèces**.

Deux garanties : aucun boss, et chaque espèce a déjà fait la preuve qu'elle peut
être placée comme symbole. Les 77 espèces qui n'apparaissent que dans des groupes
de combat (`Pandora's box`, `stone golem`, `cyclops`…) sont écartées, faute de
savoir si elles disposent d'un modèle de terrain.

À noter que « appartient à un combat scripté » n'est pas une définition exacte de
« boss » : le combat du prologue y met `slime` et `bodkin archer`. Les exclure
coûte 5 espèces sur 260, ce qui est un prix acceptable pour respecter la consigne.

### `encbtl.bin` laissé intact, et pourquoi

Un premier comptage annonçait un maximum de 12 entrées par groupe pour ce
fichier. **Ce comptage était faux** : il additionnait les en-têtes de groupe et
les entrées. En agrandissant sur cette base, des groupes montaient à 16 entrées,
au-delà de tout ce que le jeu fait. Faute de plafond établi, on n'y touche pas —
et c'est de toute façon la composition des combats, pas les symboles visibles.

### Vérifications sur la ROM produite

| | |
|---|---|
| groupes après traitement | **287 groupes, tous à exactement 6** |
| en-tête cohérent | `corps + taille_données == taille_fichier` |
| identifiants invalides écrits | **0** |
| `encbtl`, `encmons`, `mon_btldata` | identiques au bit près |
| démarrage et chargement de partie | vérifiés |

## 22. Lever le plafond de 6, et la partition terrain / boss

### Le plafond n'est pas dans le format, il est dans un cadre de pile

La fonction `0x02073ED4` bâtit deux tableaux de candidats sur son cadre de pile
et **n'a aucun contrôle de borne** :

```
02073f68  str r1, [fp, r7, lsl #2]
02073f6c  add r7, r7, #1            ; aucune verification de r7
```

Le cadre fait `0x30` = 48 octets, soit deux tableaux de 24 octets = 6 entrées de
4 octets. C'est exactement pourquoi aucun groupe vanilla ne dépasse 6 : au-delà,
le jeu écraserait sa propre pile.

Le cadre n'est utilisé qu'à six endroits, tous vérifiés par désassemblage. Quatre
suffisent à le redimensionner :

| Adresse | Rôle | 6 entrées | 12 entrées |
|---|---|---|---|
| `0x02073ED8` | allocation | `#0x30` | `#0x60` |
| `0x02073EF8` | base tableau 1 | `#0` | inchangé |
| `0x02073F7C` | base tableau 2, écriture | `#0x18` | `#0x30` |
| `0x02073FB8` | base tableau 1, lecture | `#0` | inchangé |
| `0x02073FD4` | base tableau 2, lecture | `#0x18` | `#0x30` |
| `0x02073FE4` | libération | `#0x30` | `#0x60` |

`scripts/patch_capacite.py` le fait pour une capacité quelconque, avec un
garde-fou : il refuse de patcher si l'instruction lue n'est pas celle attendue.

**Ce qui n'est pas garanti** : que le jeu puisse précharger douze modèles de
monstres au lieu de six. L'émulateur reproduit fidèlement les 656 Ko de VRAM du
DS, donc cette limite ne disparaît pas en émulation — seule la performance cesse
d'être un souci. Les modes d'échec seraient visibles : monstres invisibles,
textures corrompues, ou plantage au chargement d'une zone. D'où le marquage
expérimental.

### La partition terrain / boss — corrigée deux fois

L'utilisateur a vu des boss apparaître sur le terrain. Deux causes successives.

**Cause 1.** L'exclusion des boss ne s'appliquait qu'aux entrées **ajoutées** par
l'agrandissement. Les entrées existantes étaient réécrites par une permutation
portant sur le bestiaire entier, donc un emplacement de terrain pouvait recevoir
n'importe quoi. Correctif : permuter à l'intérieur d'ensembles séparés.

**Cause 2.** Le premier découpage définissait le pool de terrain comme « espèces
qui rôdent, **moins** celles qui apparaissent dans un combat scripté ». Les
5 espèces de recouvrement basculaient donc dans le pool des boss, et la
permutation des boss les transformait en `Dragonlord`, `Malroth`, `Barbarus`…
dans des emplacements de terrain.

Le critère correct est l'inverse :

```
pool_terrain = especes utilisees comme symbole de terrain en vanilla    (260)
pool_boss    = especes des combats scriptes qui ne rodent JAMAIS        (101)
```

**Une espèce qui rôde en vanilla est une espèce de terrain**, même si elle figure
aussi dans un combat scripté — le jeu lui-même la place comme symbole, donc elle
en a le modèle et le droit. Les deux ensembles sont disjoints, et permuter à
l'intérieur de chacun garantit qu'un emplacement de terrain ne reçoit jamais un
boss.

Vérifié sur la ROM produite : **0 boss** dans `encfld.bin` et `encmons.bin`,
comme dans l'originale.

### Deux réglages qui changent la variété perçue

**Les poids.** Chaque entrée porte une probabilité sur 3 bits. En vanilla,
l'espèce la plus probable d'un groupe capte **36 %** des apparitions, et
3 espèces sur 4 couvrent 80 % du total. Multiplier les entrées sans toucher aux
poids laisse donc les espèces d'origine dominer.

En égalisant tous les poids d'un groupe (`POIDS_UNIFORME = 4`), chaque espèce
devient équiprobable :

| | Espèce la plus probable | Espèces couvrant 80 % des apparitions |
|---|---|---|
| origine (4 entrées) | 36 % | 3 sur 4 |
| capacité 12, poids d'origine | 14 % | 8 sur 12 |
| capacité 24, poids égaux | **4,2 %** | **20 sur 24** |

**Les doublons.** Le premier tirage ne regardait pas le contenu du groupe :
`froicoucass` s'est retrouvé deux fois dans la même zone, gaspillant un
emplacement. Le tirage exclut désormais les espèces déjà présentes.

### Vérifications sur la ROM à capacité 24

| | |
|---|---|
| groupes | 287, tous à exactement 24 entrées |
| doublons dans un groupe | **0** |
| poids employés | un seul, 4 — équiprobabilité stricte |
| boss présents | **0** |
| démarrage et chargement de partie | vérifiés |

**Ce qui reste non vérifié** : que le jeu affiche correctement 24 modèles
préchargés au lieu de 6. La capacité 12 a été testée en jeu sans problème ; 24
est un pas de plus dans l'inconnu. Le mode d'échec serait visible — monstres
invisibles ou textures corrompues.

### Le poids EST la rareté — ne jamais l'égaliser

Signalé par l'utilisateur, et confirmé par la mesure. Les poids ne sont pas un
réglage de variété, ce sont les **taux de rencontre**, et ils encodent l'économie
d'expérience du jeu.

| Poids médian vanilla | Espèces | XP médiane |
|---|---|---|
| 1 | 4 | **23 100** |
| 2 | 16 | 1 035 |
| 3 | 36 | 364 |
| 4 | 46 | 423 |
| 5 | 69 | 580 |
| 7 | 28 | 795 |

Toute la famille métallique est à 1 ou 2 : `liquid metal slime` (40 200 XP),
`platinum king jewel` (43 392 XP), `metal king slime` (54 504 XP). Leur rareté
fait tout leur intérêt.

Une version intermédiaire égalisait les poids à 4 pour maximiser la variété
perçue. **C'était une erreur** : elle transformait chaque jackpot d'expérience en
monstre banal, donc en ferme à XP.

### La solution : une rareté propre à chaque espèce

`construire_rarete()` calcule, pour chaque espèce, la médiane de ses poids dans
le vanilla. Cette rareté est appliquée **après la permutation**, donc en fonction
de l'espèce qui occupe réellement l'emplacement — un gluant de métal reste rare
où qu'il aille.

Vérifié sur la ROM produite, capacité 24 : **0 entrée** dont le poids ne
corresponde pas à la rareté de son espèce.

| Espèce | Poids | Probabilité par rencontre | XP |
|---|---|---|---|
| `gluant de mercure` | 1 | 0,88 % | 40 200 |
| `bijou royal en platine` | 1 | 0,89 % | 43 392 |
| `roi gluant de métal` | 2 | 1,85 % | 54 504 |
| espèces communes | 7 | 6,36 % | — |

**Un effet de bord à connaître.** Ces espèces rares apparaissent désormais dans
22 à 29 zones chacune, contre 1 à 5 en vanilla. La rareté *par rencontre* est
préservée, mais on peut les croiser dans beaucoup plus d'endroits. Chasser le
métal gluant devient possible partout au lieu de quelques lieux précis.

## 23. CORRECTION des §21 et §22 — ce que j'avais mal compris

Établi par désassemblage ciblé (rapport complet dans `work/re/RAPPORT.md`).

**`0x02073ED4` ne construit pas la table de monstres.** Elle choisit **un
groupe** parmi ceux de la zone, et ses deux tableaux de pile contiennent des
**clés de groupes**, pas des entrées de monstres. Le vanilla ne dépasse jamais
4 groupes par zone, contre un plafond code de 6 : ces tableaux ne sont donc
jamais saturés.

**Conséquence : `scripts/patch_capacite.py` n'a jamais rien débloqué ni rien
cassé.** Il agrandissait un tampon sans rapport avec le nombre d'espèces. Les
deux « 6 » — six entrées par groupe et six clés par tableau — étaient une
coïncidence, et je l'ai prise pour une confirmation. Le script est conservé pour
mémoire mais retiré du randomizer.

## 24. La chaîne réelle, et les trois plafonds

```
encmons.bin --parse--> u16 ids[12] + u16 count          (mapstruct+0x44)
                              |
                              +--> collections de modeles (mapstruct+0x2F8, +0x304)
                              |
encfld.bin  --parse--> EncGroupSet : 6 slots de 32 o    (mapstruct+0x60)
                              |
    0x02073ED4 (choisit UN groupe) --> 0x02073FEC (loterie ponderee)
                              |
                              v  identifiant de monstre
              0x021A2128 (overlay 17) : SPAWN
                |- modele absent de mapstruct+0x2F8 ? -> return 0
                +- modele absent de mapstruct+0x304 ? -> return 0
```

| Plafond | Où | Valeur |
|---|---|---|
| entrées par groupe | slot de 32 o alloué par `AddGroup` (`0x0209BD50`, `lsl r4, r0, #5` puis `memset 0x20`) | **6** |
| espèces préchargées par carte | `cmp r3, #0xc` à `0x0209C0A0` | **12** (le fichier n'en fournissait que 6) |
| groupes par zone | `cmp r0, #6` à `0x0209BD60` | 6 (vanilla : 4 au plus) |

**`AddEntry` (`0x0209BE54`) n'a aucun contrôle de borne** : il écrit
`count = n+1` sans vérifier. Les entrées 7 et suivantes débordent dans le slot du
groupe voisin, que le prochain `AddGroup` remet aussitôt à zéro. Déclarer 24
entrées ne conserve donc que les 6 premières — et corrompt le voisin au passage.
C'était le défaut de la version à 24.

### L'invariant que le jeu maintient

**Une espèce ne peut apparaître que si elle figure dans la liste `encmons.bin` de
la carte.** Le test est un `return 0` sec dans le code de spawn. Et le vanilla
respecte `union(espèces des groupes d'une zone) ⊆ liste encmons` sur
**208 cartes sur 208**.

Randomiser les deux fichiers **indépendamment** casse cet invariant : c'est
l'explication unique et suffisante de l'absence d'effet de tout le travail
précédent. Dans la version à 24 entrées, l'intersection tombait à 2 à 4 espèces
réellement produisibles — exactement les « 4 à 6 » observés par le joueur.

### Deux pièges d'`encmons.bin`

**Le champ 1 n'est pas un emplacement libre, c'est une porte de position.** Un
contenu non nul **désactive tout l'enregistrement**, sans ajouter aucune espèce.
C'est ce que ma tentative de remplissage écrasait, et cela explique enfin
pourquoi plus aucun monstre n'apparaissait nulle part.

**Un zéro dans les champs 2 à N est sauté, pas terminateur.** Une liste
partiellement remplie est donc parfaitement légitime.

## 25. La solution retenue : resynchronisation, sans aucun patch de code

`scripts/resync_zones.py` reconstruit les deux fichiers ensemble :

1. par zone, choisir un ensemble de **8 espèces** (≤ 10 ; le plafond code est 12
   mais l'overlay 17 en ajoute 1 à 4 codées en dur, perdues en silence si la
   liste est pleine) ;
2. le répartir en **groupes de 6 entrées au plus**, jamais davantage ;
3. rendre **tous les groupes inconditionnellement éligibles** — bits 0-2 du
   paramètre de groupe à 2 (prédicat « toujours »), bits 13-20 à 0 (masque
   « toujours »), cadence conservée — pour que le sélecteur puisse tirer
   n'importe lequel à tout moment au lieu d'en figer un ;
4. écrire **exactement ce même ensemble** dans `encmons.bin`, rétablissant
   l'invariant par construction.

Résultat mesuré, zone de départ :

| | Espèces | Groupes |
|---|---|---|
| origine | 6 | 3 |
| après | **8** | 2 |

Et les contrôles, tous alignés sur le vanilla : entrées par groupe **6 au plus**,
`encmons` **8 au plus**, portes de position non nulles **1** (la même qu'en
vanilla), violations de l'invariant **2** (les mêmes qu'en vanilla), boss sur le
terrain **0**.

### Pourquoi on s'arrête là

Passer de 6 à 14 entrées par groupe demanderait de changer le pas du conteneur de
32 à 64 octets. Mais `FindGroupByKey` (`0x0209BDA4`) est appelé depuis 9 sites,
dont quatre appartiennent au parseur d'`encbtl.bin` : changer le pas casserait
`encbtl`. Et dépasser 12 espèces préchargées exigerait de relocaliser des membres
de la structure de carte, la liste n'ayant que **2 octets de marge** avant
l'`EncGroupSet`.

Non vérifié : le budget de 192 Kio de modèles (`mov r0, #0x30000` à
`0x021A2928`) tiendra-t-il 8 à 10 modèles. L'échec serait gracieux et visible —
l'espèce ne se montre pas — donc testable par dichotomie.

## 26. Le tirage au chargement de zone (v14)

Le plafond de 12 modeles precharges ne se contourne pas. Ce qu'on peut changer,
c'est **ce qu'on met dans ces 12 emplacements, et a quel moment**. Deux greffes,
posees par `scripts/patch_hasard.py` :

| | Ou | Quoi |
|---|---|---|
| A | les 2 `bl AddSpecies` du parseur d'`encmons` (`0x0209BFD8`, `0x0209BFF0`) | remplace l'identifiant du fichier par un tirage dans un bitmap de 260 especes |
| B | le corps de `ChooseFieldMonsterId` (`0x02073FEC`) | rend une espece prise **dans la liste prechargee**, au lieu de la table ponderee |

B rend l'ordre de parsage des deux fichiers indifferent : au moment du tirage,
les deux structures sont baties depuis longtemps. C'etait le seul point fragile
du montage.

Trouvailles qui ont tout simplifie :

- **`0x02032380` = `rand_below(max)`**, le generateur du jeu, appele par le
  tireur d'origine. Pas besoin d'en embarquer un.
- **`0x02109BC8`** : `[[0x02109BC8]]` est la liste de prechargement, ids en u16 a
  `+0x00`, nombre a `+0x18`. Le premier pointeur vit en **DTCM** (`0x027E3200`),
  ce que le domaine « System Bus » de BizHawk ne couvre pas -- il y rend 0 sans
  erreur, et j'ai cru trois fois que la greffe ne marchait pas.
- La greffe B tient en **56 octets** dans les 132 de la fonction d'origine.

Les boss sont absents du bitmap : l'exclusion ne coute pas une instruction.

## 27. LE PIEGE QUI COUTE UNE JOURNEE : `CompressedStaticEnd`

**Recompresser l'ARM9 apres l'avoir modifie rend la ROM inbootable**, et le
symptome n'a rien a voir avec le patch : PC fige a **`0xFFFF0108`** -- le vecteur
d'exception de la BIOS ARM9 -- des la premiere seconde, ecran blanc, avant meme
l'ecran-titre.

La cause est dans `ModuleParams`, situe a `nitrocode - 0x1C` (le magique
`0xDEC00621` est a l'offset `0xBBC`) :

```
+0x00 AutoloadListStart     0x020F4600
+0x04 AutoloadListEnd       0x020F4618
+0x08 AutoloadStart         0x020F2E60
+0x0C StaticBssStart        0x020F2E60
+0x10 StaticBssEnd          0x021536E0
+0x14 CompressedStaticEnd   0x0209BD08   <-- = 0x02000000 + 638 216
+0x18 SDKVersion            0x04027539
```

`CompressedStaticEnd` porte la fin du flux BLZ, soit **exactement la longueur du
flux d'origine**. ndspy ne le met pas a jour. Des que le contenu change, le flux
recompresse change de taille et le stub de decompression du jeu travaille sur une
fin fausse.

Ce qui m'a egare : un aller-retour decompression/recompression **sans
modification** rendait 638 216 octets, la meme taille, et bootait parfaitement.
J'en ai conclu que la chaine etait saine. Il a fallu ecrire **64 octets de bitmap
dans du bourrage** -- pas une instruction, aucun code appele -- pour voir la meme
ROM refuser de demarrer, et comprendre que ce n'etait pas la greffe.

**La solution** : mettre `CompressedStaticEnd` a zero et stocker l'ARM9 en clair.
Le stub saute alors la decompression. L'ARM9 passe de 638 Ko a 1 001 Ko, absorbes
par les 10 Mo de bourrage de fin de cartouche : la ROM produite fait toujours
268 435 456 octets. Seul effet visible, le patch `.xdelta` passe de 19 Ko a
571 Ko.

## 28. Le gel au premier pas hors de la ville

Signale par le joueur sur la premiere v14. Reproduit en laboratoire, PC releve :
**`0xFFFF0108`**, le vecteur d'exception de la BIOS ARM9 -- une **exception de
donnees**, pas une boucle.

La greffe B suivait la chaine de globales du parseur, `[[0x02109BC8]]`. Le
premier maillon vit en DTCM (`0x027E3200`), et le second y vaut **0** des
qu'aucune carte a rencontres n'est chargee. `ldrh r0, [r4, #0x18]` lisait alors
l'adresse `0x18`. Je testais le nombre d'especes mais **jamais les pointeurs**.

**Correction** : plus de chaine du tout. La greffe A recoit la liste en argument
-- toujours valide -- et la depose dans un mot a `0x020E7368`, dans la meme zone
libre. La greffe B lit ce seul mot et teste sa nullite ; a zero, elle rend -1,
exactement ce que rend la version d'origine quand aucune entree ne convient. Les
appelants savent le traiter (`cmp r5, #-1 ; beq`).

### Le harnais qui a permis de le voir

Le savestate reste l'outil le plus rapide, a condition de savoir ce qu'il fait :
il restaure toute la RAM, **code compris**, donc il annule le patch. On le
recharge donc, puis on **reecrit les 58 mots du patch en RAM** (`memory.write_u32_le`)
juste apres. On se retrouve en plaine avec la version patchee, sans avoir a sortir
de la ville -- ce que le harnais n'a jamais su faire. `scripts/lua/gel_v14.lua`.

Resultat : gel reproduit au tour 2 avec la version fautive, 30 tours sans incident
avec la version corrigee.

### Ce qui reste non verifie en laboratoire

La greffe A ne tourne qu'au **chargement d'une carte**, et le harnais n'a jamais
franchi de limite de zone : 30 tours de marche, le pointeur est reste a zero. La
greffe A a bien tourne au demarrage et au chargement de la partie -- plusieurs
cartes -- sans incident, mais la combinaison « liste tiree au hasard **puis**
tirage dedans sur le terrain » n'a ete exercee que par le joueur.

## 29. FAUX — ce que je croyais du tampon de modeles

**Cette section disait que les 192 Kio a `0x0211E33C` bornaient les 12 modeles
d'une carte, et que le plafond etait donc memoire. C'est faux**, etabli par
desassemblage (`work/re/RAPPORT_CHARGEMENT.md`).

Ce tampon est un **tampon de travail**. Il recoit le sommaire de l'archive
`data/pack_lv5/enemy.gp2`, puis **le membre courant, au meme emplacement a chaque
tour de boucle** :

```
021a2958  ldr r5, [sp, #0x30]     ; octets pris par le SOMMAIRE, une seule fois
021a29e8  add r2, r2, r5          ; MEME destination a chaque tour
021a2a30  bl  #0x2075664          ; decompresse vers le TAS, c'est ca qui survit
021a2ad8  bl  #0x20d962c          ; l'archive est refermee
```

`r5` n'est jamais reecrit dans la boucle. Et `0x0203D038` **rouvre la meme
archive dans le meme tampon en pleine partie**, ce qui serait impossible s'il
contenait des modeles persistants.

Le `cmp sb, r1 ; bhi` de `0x020D92BC` que je citais compare la taille du
**sommaire de l'archive** au tampon, pas la taille cumulee des modeles. Le plus
gros membre de terrain fait 44 220 octets, soit 23 % du tampon : il n'est jamais
pres de saturer.

**Et il n'y a aucune constante de plafond memoire.** Le tas des modeles est cree
au chargement de carte en prenant *tout l'espace libre restant*, et le reliquat
est reverse au tas suivant :

```
021a30b8  bl 0x2032804    ; GetTotalFreeSize(carte+0x1244) -> tout le libre
021a30e0  bl 0x2032500    ; CreateExpHeap(carte+0x113C, bloc, r5)
021a30fc  bl 0x21a28a8    ; prechargement
021a3108  bl 0x2032804    ; ce qui reste
021a312c  bl 0x2032500    ; CreateExpHeap(carte+0x11C0, reste)
```

Ma mesure de « 552 Kio libres, plus grande plage 132 Kio » reste juste, mais elle
ne mesurait pas ce que je croyais : la RAM est occupee par des tas, pas par un
pool de modeles a agrandir.

Le vrai plafond est decrit au paragraphe suivant.

## 29 bis. ARCHIVE de la version fausse (conservee pour memoire)

A 12 especes par zone, des monstres n'apparaissent plus, et certains se montrent
apres un combat. Ce n'est pas un bug du patch : c'est le tampon de modeles qui
deborde, et la VRAM qui se libere puis se recharge apres la bataille.

Le tampon est **fixe et passe en argument** par l'overlay 17 :

```
021a2928  mov r0, #0x30000       ; taille   -> [sp, #4]
021a2940  ldr r3, [pc, #0x1c8]   ; base = 0x0211E33C
021a294c  bl  0x020d91ec         ; PrepareModelSet(..., base, taille, &utilise)
021a2960  rsb r0, r5, #0x30000   ; place restante
```

Et dans `0x020D91EC` :

```
020d92bc  cmp sb, r1             ; taille requise vs taille max
020d92c0  bhi echec              ; ne tient pas -> abandon
020d92d0  addne r0, r5, r1       ; sinon on place EN FIN de tampon
020d92d8  subne r5, r0, sb
```

Trois valeurs a changer, dont une base : techniquement, un patch de trois mots.

**Sauf qu'il n'y a nulle part ou le mettre.** Releve de la RAM principale en jeu
(`scripts/lua/arpente_ram.lua`), pages jamais touchees du demarrage a la balade :

| | |
|---|---|
| total libre | 552 Kio, **fragmente** |
| plus grande plage contigue | `0235F000-0237FFFF`, **132 Kio** |
| deuxieme | `023A9000-023C8FFF`, 128 Kio |
| tampon actuel | **192 Kio** |

La plus grande plage libre est **plus petite que le tampon existant** : on ne peut
meme pas le deplacer a taille egale, encore moins l'agrandir. Derriere lui il
reste 21 Kio de BSS avant `StaticBssEnd` (`0x021536E0`), soit +11 % -- sans
interet.

Et un second mur suit : l'enregistrement du modele (`bl 0x2036814`, echec ->
code 3) travaille en **VRAM**, 656 Kio cables partagees avec tout ce qui est a
l'ecran.

**Conclusion mesuree** : le plafond n'est pas une constante a retourner. Le
franchir demanderait de liberer des centaines de kilo-octets de RAM principale
*et* de VRAM, donc de retoucher le plan memoire du moteur. Le reglage utile reste
`--especes`, et son point de fonctionnement se situe entre 8 (valide) et 12
(deborde).

## 30. Le chargeur a la demande existe deja dans le jeu

Etabli par desassemblage (`work/re/RAPPORT_CHARGEMENT.md`). Deux chemins, tous
deux actifs en cours de partie.

### Asynchrone -- le gestionnaire de requetes de ressources

| Element | Adresse | Preuve |
|---|---|---|
| pointeur du gestionnaire | `[0x02104304 + 4]` | `0202F7BC` |
| file de requetes | `mgr+0x128`, entrees de 0x44 o | `0202FAB4` |
| plafond de la file | **24** | `0202FA9C cmp r0,#0x18` |
| mise en file (membre d'archive) | `0x0202FD3C(mgr, archive, membre, tas) -> id u16` | type 2 |
| sondage | `0x0202FDE0(mgr, id) -> 1 / 0 / -1` | pret / attente / erreur |
| recuperation | `0x0202FED8(mgr, id, void** p, u32* n)` | |
| purge totale | `0x0202F7B8` -> `0x02030120` | |

**Client de reference : l'overlay 14**, la liste des monstres. Il demande
`"%s.mon"` dans `data/pack_lv5/enemy.gp2` (`0x0218521C`), sonde, recupere, puis
`0x0207551C` pour extraire `.cchr` / `.cmot` / `.bact`, `0x02075664` pour
decompresser et `0x02036814` pour enregistrer -- **un monstre a la fois, hors
chargement de carte**.

### Synchrone -- `0x0203D038`, le chargeur d'acteurs de terrain

Un seul appelant : `ovl17 @0x021A2EA4`. Le cas `cmp r0, #5` est le modele de
monstre. Il **rouvre `enemy.gp2` en pleine partie** (`0x0203D4F0`).

**Piege** : `0x0203D4A0` purge la file asynchrone avant l'ouverture synchrone.
Les deux chemins ne cohabitent pas.

### Les briques

- `0x02075664` = `LZ77DecompressToHeap(tas, src, u32* taille)`. La taille
  decompressee est `mot >> 8` ; la decompression est le `svc #0x11` de la BIOS
  (`0x020006CC`), synchrone, RAM vers RAM.
- `0x0207551C` ouvre le `.mon` comme archive NARC et filtre le nom par `strstr`.
- `0x02036814` enregistre le modele.

### Ou vivent les modeles

`data/pack_lv5/enemy.gp2`, 15 843 860 o, **601 membres** : `<code>.mon` (312,
version complete) et `<code>_f.mon` (289, **version terrain**). Les membres ne
sont pas compresses au niveau GPC2 -- ce sont des archives NARC dont les fichiers
`.cchr` et `.cmot` sont, eux, en LZ77.

**Bug latent dans `scripts/gp2.py`** : le champ taille de l'index porte des
drapeaux dans son octet de poids fort, il faut masquer par `0x00FFFFFF`. Sans
cela le lecteur calcule des tailles de 419 Mo.

Cout d'un modele de terrain, mesure sur les 289 `_f` :

| | min | med | p90 | max |
|---|---|---|---|---|
| membre dans l'archive | 3 392 | 12 076 | 22 544 | 44 220 |
| `.cchr` decompresse (RAM) | 5 508 | **18 320** | 29 820 | **61 368** |

## 31. Mesure sur le terrain : ce que v14 fait reellement

Savestate pris par le joueur **en pleine plaine, sur la ROM v14 elle-meme**
(`work/save_origine/terrain_v14.State`). C'est l'outil qui manquait depuis le
debut : le harnais automatique ne sait pas sortir de la ville, et un savestate
pris sur une autre ROM annule le patch de code.

```
carte = 020FDD44
liste de prechargement = 8 especes : 119, 217, 251, 120, 111, 150, 113, 116
emplacements de modele occupes : 7, 8, 9, 10, 11, 12, 13, 14   -> 8 sur 8
emplacements libres derriere   : 15, 16, 17, 18
```

Deux conclusions :

- **la greffe A fonctionne** : les 8 especes de la liste sont bien un tirage, et
  les 8 modeles correspondants sont charges ;
- **il reste 4 emplacements libres** sur les 12 que balaye `FindLoadedModelSlot`
  (`0x021A277C cmp r5,#0xc`). Le refus a 10 especes ne vient donc pas du nombre
  d'emplacements.

*Non mesure : le libre du tas des modeles. La recherche de la signature ExpHeap
en RAM principale n'a rien rendu dans les deux endiannesses, et
`[carte+0x113C]` n'est pas un pointeur RAM -- soit l'offset differe, soit la
structure de carte du parseur n'est pas celle de l'overlay 17. A reprendre.*

### Pourquoi un monstre est invisible

Une espece peut figurer dans les conteneurs `carte+0x2F8` et `carte+0x304` --
donc passer les deux tests de rejet du spawn (`0x021A2180`, `0x021A218C`) --
**sans que son modele soit charge**. Enregistrement present, modele absent :
le symbole existe, rien ne s'affiche. Monter `--especes` fabrique des fantomes.

## 32. Boite a outils complete pour le chargement a la demande

Toutes les briques sont identifiees. Rien ne manque plus que le code de liaison.

### Chargement

| Fonction | Signature | Preuve |
|---|---|---|
| `0x0202FD3C` | `(mgr, archive, membre, tas) -> id u16` | mise en file asynchrone, type 2 |
| `0x0202FDE0` | `(mgr, id) -> 1 / 0 / -1` | pret / attente / erreur |
| `0x0202FED8` | `(mgr, id, void** p, u32* n)` | recuperation |
| `0x0203D038` | chargeur d'acteur synchrone, cas `type == 5` | unique appelant : `ovl17 @0x021A2EA4` |
| `0x0207551C` | `(blob, nom, ...)` | ouvre le `.mon` en NARC, filtre par `strstr` |
| `0x02075664` | `(tas, src, u32* taille) -> void*` | LZ77 de la BIOS (`svc #0x11`) vers le tas |
| `0x02036814` | enregistrement du modele | 46 appelants |

### Liberation -- la brique qui manquait

| Fonction | Signature | Preuve |
|---|---|---|
| **`0x02032628`** | **`HeapFree(tas, ptr)`** | dans la purge de file `0x02030120` : `ldr r0,[r4,#0x34]` (tas), `ldr r1,[r4,#0x38]` (donnees), `bl 0x2032628`, puis remise a zero du champ |
| `0x02032554` | `HeapAlloc(tas, n)` | 1081 appelants |
| `0x02032500` | `CreateExpHeap(handle, bloc, n)` | |
| `0x02032804` | `GetTotalFreeSize(handle)` | compare la magie a `0x45585048` |

### Table des emplacements de modele

| Fonction | Signature |
|---|---|
| `0x0200F398` | rend la table (base `0x020F33D8`, entrees a `+8`, **233** emplacements) |
| `0x0200FD48` | `SetSlot(table, i, obj)` -- ecrit `table[i]` et `obj->4 = i` |
| **`0x0200FD58`** | **`ClearSlot(table, i)`** |
| `0x0200FD68` | `ResetTable(table)` -- `memset(table+8, 0, 0x3A4)` |
| `0x0200FD80` | `GetSlot(table, i)`, borne a 233 |
| `0x021A27E8` | **`ClearAllMonsterModelSlots()`** : vide les emplacements **7 a 18** puis appelle `0x02057F10` pour les indices **120 a 139** (20 emplacements, probablement les textures). Appelee en tete du prechargeur. |

Les modeles de monstres de terrain occupent les emplacements **7 a 18** ; la
recherche `FindLoadedModelSlot` (`0x021A277C cmp r5,#0xc`) ne balaye que ces 12.

### Conteneurs consultes par le spawn

| Conteneur | Nature | Capacite | Source |
|---|---|---|---|
| `carte+0x2F8` | tableau d'enregistrements de **0x1C** o, alloue en un bloc | **512** (`0x0206F324 cmp r7,#0x200`) | `mon_data_<LG>.nat` |
| `carte+0x304` | liste chainee (cle u16 en `+0`, suivant en `+0x10`) | aucune | `data/prm/fld_mondata.bin` |

Champs utiles de l'enregistrement `+0x2F8` : `+0x04` = **code de modele**
(chaine, sert a `sprintf("%s_f.mon")`), `+0x08` = cle de recherche,
`+0x0C` et `+0x0E` = deux shorts relus a l'apparition (`0x021A22C8`,
`0x021A22D8`). Le tampon de transit qui les alimente fait **0x18 octets**, soit
12 u16 (`0x021B52B8`), et c'est **la** que se trouve le vrai goulot -- pas dans
le conteneur.

### Ou loger le code

| Piste | Verdict |
|---|---|
| bourrage ARM9 hors BSS | **406 o en tout**, dont 280 deja pris par v14. Les 3 plages : `0x020E7268` (280), `0x020F1E40` (72), `0x020F1D2C` (54) |
| ajouter a la fin de l'ARM9 | **impossible** : crt0 met a zero de `0x020F2E60` a `0x021536E0`, ce qui effacerait le code |
| bourrage de l'overlay 17 | **zero octet** ; les binaires sont tasses |
| agrandir l'overlay 17 | **impossible** : les 1 888 o derriere lui sont exactement son BSS, et les overlays 22 a 31 commencent juste apres, a `0x021D8A40` |
| **code mort de l'ARM9** | **13,5 Ko** sur les 10 plus grosses fonctions jamais appelees ni referencees |

Les plus grosses : `0x0200341C` (2 080 o), `0x02002CB8` (1 888), `0x0200702C`
(1 732), `0x0204C044` (1 500), `0x0200884C` (1 368).

*Reserve : le critere est « aucune cible de branche, et aucun mot du binaire
n'egale une adresse interne ». Il ne couvre pas les references formees par
`add rX, pc, #imm` ni les tables construites a l'execution. A valider en jeu
avant d'y mettre du code utile.*

### Le plan

1. **Remplir les conteneurs avec les 260 especes** au chargement de carte. Ils
   acceptent 512 ; il suffit d'alimenter la construction avec la liste complete
   au lieu du tampon de 12. Cout : 260 x 0x1C = 7,3 Kio sur le tas de carte.
2. **A l'apparition**, si le modele de l'espece n'est pas charge, le charger sur
   place -- `0x0207551C` + `0x02075664` + `0x02036814` -- dans un des 12
   emplacements.
3. **Evincer** le moins recemment utilise : `ClearSlot` + `0x02057F10` pour la
   texture + `HeapFree(carte+0x113C, ptr)`.

Piege deja identifie : contourner les deux tests de rejet du spawn sans fournir
les enregistrements provoque une lecture a l'adresse `0x0C`. C'est la meme
famille que le gel de la v14.

## 33. La chasse au code mort ne marche pas -- et ce qu'il faut faire a la place

Le critere statique « aucune cible de branche, aucun mot du binaire n'egale une
adresse interne » donnait 23 fonctions ARM9 et 13,5 Kio. **Il est faux.**

Verification en jeu (`scripts/lua/valide_code_mort.lua`) : on remplit chaque
region de `b .` -- branchement sur soi-meme -- depuis la sauvegarde de terrain,
puis on joue en surveillant le compteur ordinal. Une region vivante fige le jeu
immediatement et le PC se retrouve dedans, ce qui la denonce.

| Region | Verdict | Quand |
|---|---|---|
| `0x0204C044` | **vivante** | des la premiere frame |
| `0x02017DA4` | **vivante** | des la premiere frame |
| `0x02005AC8` | **vivante** | au bout de ~50 s de marche |
| `0x0200341C`, `0x02002CB8`, `0x0200702C`, `0x0200884C`, `0x020026B8`, `0x020076F4` | pas encore prises | repos + 30 tours de marche |

**La lecon est dans la troisieme ligne.** Une region peut paraitre morte pendant
quinze secondes et etre appelee a la minute suivante. Le jeu n'a jamais eu
l'occasion, pendant mes tests, d'ouvrir un menu, d'entrer en combat, de
sauvegarder ou de lancer une cinematique. Aucune duree de test ne prouvera qu'une
region est morte ; elle prouve seulement qu'elle ne l'est pas.

Ces adresses tombent d'ailleurs toutes dans `0x02002000`-`0x02009000`, qui a
toutes les allures du runtime C -- `printf`, conversions, flottants. Du code
appele par pointeur, precisement ce que le critere statique ne voit pas.

### La bonne source de place : le prechargeur lui-meme

Le chargement a la demande **rend le prechargeur inutile**. Sa fonction,
`0x021A28A8`, fait environ 600 octets dans l'overlay 17 -- exactement la ou le
code doit vivre, et exactement le code qu'on remplace. La place qu'on libere est
la place dont on a besoin.

S'y ajoutent, sans risque :

| Emplacement | Taille |
|---|---|
| corps de `0x021A28A8` (le prechargeur) | ~600 o |
| reste du corps de `ChooseFieldMonsterId`, deja remplace par la greffe B | 72 o |
| bourrage ARM9 `0x020F1E40` et `0x020F1D2C` | 126 o |

Aucune de ces zones n'est du code dont on ignore l'usage : ce sont des fonctions
dont on connait le role et qu'on retire volontairement. C'est la difference entre
recuperer de la place et esperer que personne ne s'en serve.

## 34. Comment remplir les conteneurs avec les 260 especes

La construction est entierement decodee, dans `ovl17 @0x021B5250` (appelee quand
la requete asynchrone de `mon_data_<LG>.nat` aboutit, etat 2) :

```
021b52ac  ldr r6, [r5, #8]        ; r6 = carte
021b52b0  add r0, sp, #0x18       ; tampon local...
021b52b4  mov r1, #0x18           ; ...de 24 octets = 12 u16
021b52b8  bl  0x200f374           ; mise a zero
021b52bc  add r1, sp, #0x18
021b52c0  add r0, r6, #0x44       ; la liste de prechargement
021b52c4  bl  0x209c0d0           ; CopyList(liste, tampon) -> nombre
021b52d0  asr r7, r0, #0x10       ; r7 = nombre
021b52d4  add r0, r6, #0x2f8 ; bl 0x206efd4    ; vide le conteneur
021b52e0  add r1, sp, #0x18 ; stm sp, {r1, r7} ; arguments : tampon, nombre
021b5308  bl  0x206f240           ; construit le conteneur
```

`0x0209C0D0` est `CopyList(src, dst) -> count` : une boucle de `ldrh`/`strh`
bornee par le nombre a `src+0x18`.

**Le goulot est le tampon local de 24 octets, rien d'autre.** Le conteneur
accepte 512 especes (`0x0206F324 cmp r7,#0x200`), et `0x0206F240` va chercher le
code de modele de chaque espece dans `mon_data_<LG>.nat`, qui contient les 438.

### La greffe

Pas besoin d'agrandir le cadre de pile : il suffit de fournir un autre tampon.

1. remplacer `bl 0x209c0d0` (`0x021B52C4`) par un appel a une greffe qui
   **alloue 520 octets** sur le tas de carte (`HeapAlloc`, `0x02032554` ; le tas
   est deja charge en `0x021B52FC` par `ldr r1,[r2,#0x10]`), y ecrit les **260**
   identifiants en developpant le bitmap de 64 octets deja present, garde le
   pointeur dans un mot statique et rend 260 ;
2. faire pointer les deux `add r1, sp, #0x18` (`0x021B52BC` et `0x021B52E0`) sur
   ce mot -- un `ldr r1, [pc, #x]` suffit, le mot etant loge dans l'overlay 17
   lui-meme, a portee des 4 095 octets d'un deplacement pc-relatif ;
3. liberer apres `0x021B5308` avec `HeapFree` (`0x02032628`).

Meme operation pour `carte+0x304` dans la fonction voisine, `0x021B5348`, qui
lit `data/prm/fld_mondata.bin`.

Cout sur le tas de carte : 260 x 0x1C = 7,3 Kio d'enregistrements, plus les
chaines dupliquees, soit environ 10 Kio.

**Ce que cette greffe donne seule** : le spawn accepte n'importe quelle espece,
et la greffe B peut tirer dans les 260. Mais le modele n'est toujours pas charge,
donc beaucoup de monstres seraient invisibles. C'est une etape intermediaire
verifiable, pas une version jouable -- la suite (chargement a la demande) est
indispensable.

## 35. Etape 1 construite : `scripts/patch_conteneurs.py`

Trois patches, verifies au desassemblage de la ROM produite :

```
ovl17 0x021B52C4   bl 0x209C0D0        -> bl 0x020E7308   (greffe C)
ovl17 0x021B52E0   add r1, sp, #0x18   -> ldr r1, [sp, #0x18]
ARM9  0x020E7308   greffe C, 96 octets exactement, sans litteral
```

La greffe alloue 1 024 octets sur le tas de carte (`[carte+0x10]`, le meme que
celui deja passe au constructeur), y developpe le bitmap des 260 especes,
depose le pointeur dans le premier mot du tampon local et rend le nombre. Le
`strhne` post-indexe evite un branchement dans la boucle -- c'est ce qui la fait
tenir dans les 96 octets libres derriere la greffe A.

Deux pieges payes au passage :

- **1 032 n'est pas un immediat ARM encodable** et keystone y repondait par un
  `MOVW`, absent de l'ARMv5TE. Le garde-fou l'a arrete. Le tampon fait donc
  1 024 octets (`0x400`), ce qui couvre le pire cas de 512 u16.
- **`Overlay.save()` de ndspy rend les DONNEES de l'overlay, pas son entree de
  table.** Les joindre pour reconstruire `arm9OverlayTable` fabrique une
  « table » de 11 Mo et fait echouer `saveToFile` sur un `IndexError`. La table
  se reconstruit avec `ndspy.code.saveOverlayTable(overlays)`. L'overlay 17 est
  desormais stocke en clair, 314 688 o au lieu de 200 184 compresses.

### Ce que le harnais ne peut pas mesurer

La globale `0x02108D14` porte l'adresse du conteneur (`0x0206F24C ldr r3,[pc]` ;
`str sl,[r3]`). Elle donne bien `0x020FE03C`, soit `carte+0x2F8` avec
`carte = 0x020FDD44` -- la meme carte que dans la sauvegarde de terrain.

Mais ses trois mots sont **a zero**, et **ils le sont aussi sur v14**. Le
conteneur n'est simplement pas peuple la ou le harnais se trouve : la sauvegarde
demarre dans un batiment de Stornway, et une carte sans rencontres n'a pas de
conteneur de monstres. Le releve ne vaut donc rien a cet endroit, ni pour v17 ni
pour le temoin.

**Conclusion de methode** : l'etape 1 n'est pas observable seule. Elle n'est pas
non plus jouable seule -- le spawn accepterait toutes les especes sans que leur
modele soit charge. L'etape 1 et l'etape 2 forment donc **un seul lot testable**,
et c'est comme cela qu'il faut les livrer.

## 36. Etape 2 : le mecanisme du monstre invisible, a l'instruction

Confirme dans le spawn `0x021A2128` :

```
021a21f0  mov r0, fp
021a21f4  mov r1, sb              ; sb = l'espece
021a21f8  bl  0x21a2738           ; FindLoadedModel(espece) -> objet ou 0
021a21fc  ldrh r1, [r6]
021a2200  cmp sl, r1 ; bne  ->    saute
021a2208  cmp r0, #0 ; beq  ->    saute
021a2210  mov r1, r8 ; bl 0x2072aec   ; attache le modele a l'acteur
```

**Si `FindLoadedModel` rend 0, l'acteur est cree et aucun modele ne lui est
attache.** Le monstre existe, il ne s'affiche pas. C'est exactement ce que le
joueur decrit a 10 et 12 especes.

`FindLoadedModel` (`0x021A2738`) balaye les emplacements 7 a 18 par
`GetSlot(table, 7+i)` et compare l'espece a `objet+2` (`ldrsh`). Elle rend
l'**objet**, pas l'indice. Les objets sont les enregistrements de **0xB0 octets**
alloues en un bloc par le prechargeur (`0x021A28EC`, `count * 0xB0`), et
l'espece y est ecrite par `0x021A2A60 strh fp, [r0, #2]`.

Quatre appelants, tous de la meme forme : `bl`, `cmp r0,#0`, `beq`, sinon
attacher. Le seul du chemin d'apparition est `0x021A21F8`.

### Pourquoi `0x0203D038` ne fait pas l'affaire

Son cas `type == 5` alloue une fiche d'acteur de 0xD8 octets et la range dans
`[r7+0x18]` : c'est un chargeur d'**acteur**, pas un « charge le modele de
l'espece X dans l'emplacement i ». Le reutiliser depuis le spawn demanderait de
reconstruire son contexte (`r0`, `r5`, `r7`), qu'on ne sait pas fabriquer.

### La forme que doit prendre l'etape 2

Le prechargeur `0x021A28A8` contient deja toute la sequence : vider les
emplacements, allouer le tableau de fiches, ouvrir l'archive, boucler sur la
liste, refermer. Le transformer en **chargeur d'une seule espece dans un seul
emplacement** demande sept points de greffe :

| # | Adresse | Modification |
|---|---|---|
| 1 | trois mots en zone libre | `TABLEAU` (fiches), `TOUR` (rotation), `DEMANDE` (espece voulue) |
| 2 | `0x021A28CC` | ne pas vider les emplacements si `DEMANDE` |
| 3 | `0x021A28E4`-`0x021A28F0` | reutiliser `TABLEAU` au lieu d'allouer |
| 4 | `0x021A295C` | partir de l'emplacement de rotation |
| 5 | `0x021A2974` | rendre `DEMANDE` au lieu de `GetSpecies(liste, i)` |
| 6 | `0x021A2AC8` | sortir apres un tour |
| 7 | `0x021A21F8` | si `FindLoadedModel` echoue : poser `DEMANDE`, appeler le prechargeur, reessayer |

Plus l'eviction : liberer le modele de l'emplacement recycle avec
`HeapFree(carte+0x113C, ptr)`, ce qui suppose de connaitre l'offset du pointeur
de modele dans la fiche de 0xB0 octets -- **non encore identifie**.

**Inconnues restantes** : cet offset, et le fait que le spawn dispose ou non du
`r0` (`sl`) qu'attend le prechargeur. Sans les deux, le montage ne tient pas.

C'est un chantier de plusieurs sessions, et la boucle de test ne se ferme pas en
local : il faut un chargement de carte a rencontres, que le harnais ne sait pas
produire.

## 37. Le cout reel de chaque modele, et le filtre de taille

`scripts/tailles_modeles.py` mesure, pour chaque espece, la taille de son modele
de terrain une fois en RAM. La chaine, verifiee :

`data/pack_lv5/enemy.gp2` -> membre `<code>_f.mon`, **non compresse au niveau
GPC2** -> archive **NARC** Nitro -> fichier `.cchr`, compresse en LZ77 -> taille
decompressee lue dans l'en-tete (`mot >> 8`), sans rien decompresser.

**Deux corrections a `scripts/gp2.py`, toutes deux verifiees :**

- le champ taille de l'index porte des drapeaux d'arbre dans son octet de poids
  fort : il faut masquer par `0xFFFFFF`. Sans cela l'archive annonce des membres
  de 419 Mo. Apres correction, **600 paires consecutives sur 600** verifient
  `pos[i+1] - pos[i] == taille[i] + 4` ;
- la table de noms suit l'ordre des entrees **triees par offset masque**, pas
  l'ordre brut de l'index. Apparier sans trier ne rend aucun `_f.mon` ;
- et il n'y a **pas** de u32 de controle avant un membre : le NARC commence
  directement a `pos`. Les 4 octets d'ecart sont du bourrage apres.

### Resultats sur les 289 modeles de terrain

| min | mediane | moyenne | max |
|---|---|---|---|
| 5 508 | **18 320** | 20 831 | **61 368** |

| seuil | modeles retenus |
|---|---|
| <= 8 Kio | 6 |
| <= 16 Kio | **102** |
| <= 24 Kio | 230 |
| <= 32 Kio | 264 |

Les plus gros sont les monstres a prefixe `b` : `b100a` (Lordragon) 61 368 o,
`b109a` (Orgodemir) 58 996. Les plus petits sont la famille metallique :
`z050a`/`b`/`c` a 5 508 o.

**Un facteur 11 entre le plus petit et le plus gros.** Douze modeles medians
coutent 220 Kio, douze petits en coutent 168 : le filtre est donc le levier le
moins cher pour tenir plus d'especes par zone. D'ou `--taille-max N` dans le
randomizer.

## 38. UN SAVESTATE EST LIE A LA DISPOSITION DES FICHIERS DE LA ROM

v18 (`--especes 12 --taille-max 16384`) **demarre et charge une partie
normalement**, dispersion du compteur ordinal identique a la reference. Mais
charger la sauvegarde de transition prise sur **v14** puis franchir la limite
gele le jeu sur l'ecran noir.

La raison : `--especes 12` grossit `encmons.bin` et `encfld.bin`, donc **tous les
offsets de fichiers de la ROM se decalent**. Le savestate restaure l'etat du
systeme de fichiers tel qu'il etait sur v14 ; la premiere lecture cartouche du
chargement de carte tombe alors a coté, et le chargement ne finit jamais.

**Consequence de methode :** un savestate ne vaut que pour les ROMs de **meme
disposition de donnees**. On peut donc tester par ce biais toutes les variantes
de **code** (greffes, bitmap) sur la disposition de v14, mais aucune variante qui
change la taille d'un fichier. Pour celles-la il faut un savestate pris sur la
ROM elle-meme.

## 39. Le budget des modeles, mesure

Cinq seuils de taille, six transitions de zone chacun, sur v18
(`--especes 12`). Emplacements de modele reellement remplis sur les 12 demandes :

| seuil | especes dans le pool | modeles charges |
|---|---|---|
| **16 Kio** | 102 | **12, 12, 12, 12, 12, 12** |
| 20 Kio | 186 | 11, 10, 11, 11, 12, 12 |
| 24 Kio | 224 | 10, 10, 11, 9, 11, 11 |
| 32 Kio | 256 | 10, 10, 9, 10, 10, 10 |
| aucun | 260 | 10, 10, 9, 10, 10, 10 |

Sans filtre, **2 a 3 modeles sur 12 ne se chargent jamais** : c'est la mesure des
monstres invisibles signales sur v15 et v16. A 16 Kio, les 12 passent a chaque
fois -- ce que le joueur a confirme en jeu sur v18.

Le budget du tas des modeles se situe donc autour de **170 a 190 Kio** : douze
modeles de 14 Kio passent, douze de 18 Kio non.

**Defaut du tirage releve au passage** : `180,114,3,3,83,245,28,83,83,76,15,11`.
L'espece 83 trois fois, la 3 deux fois -- la greffe A ne regarde pas ce qui est
deja dans la liste. Cette zone n'affiche que 9 monstres distincts sur 12
emplacements.

## 40. TOUTE MODIFICATION DE TAILLE DE FICHIER INVALIDE LES SAUVEGARDES D'ETAT

Deja constate au 38 avec `--especes 12`. Confirme de facon nette : **v20**,
c'est-a-dire v18 avec l'overlay 17 simplement stocke en clair et **aucune
modification de code**, gele exactement comme v19 apres une transition.

L'overlay passe de 200 184 a 314 688 octets, tous les offsets de fichiers de la
ROM se decalent, et l'etat du systeme de fichiers restaure par le savestate
pointe a coté. Le chargement de carte ne finit jamais.

**Ce n'etait donc pas la greffe C.** Elle reste non testee.

### La consequence pratique, et comment s'en sortir

La disposition des donnees doit etre **figee une fois pour toutes** avant de
demander une sauvegarde. Elle l'est des que trois choses sont arretees :

| | |
|---|---|
| `encmons.bin` / `encfld.bin` | `--especes 12` |
| ARM9 | stocke en clair, 1 000 984 o |
| overlay 17 | stocke en clair, 314 688 o |

Une fois ces trois tailles fixees, **toute modification de code ulterieure garde
la meme disposition** -- les greffes vivent dans du bourrage ou remplacent du
code existant, sans changer une seule taille de fichier. Une seule sauvegarde
d'etat couvre alors tout le developpement de l'etape 2.

## 41. Greffe C validee : 64 especes acceptees par zone

Mesuree sur v19 avec la sauvegarde de transition prise sur v19 (meme disposition
de fichiers, donc valide), en injectant des bitmaps de densite croissante :

| especes dans le bitmap | especes acceptees par le conteneur |
|---|---|
| 24 | 24, 25, 24 |
| 48 | 48, 48, 48 |
| **64** | **64, 64, 64** |
| 80 | 80, **0**, 80 |
| 102 | 0, 0, 0 |

**La greffe C fonctionne** : le conteneur passe de 12 especes acceptees a 64,
soit cinq fois plus. C'est la premiere validation de l'etape 1.

Le plafond n'est pas dans le conteneur -- il en accepte 512 -- mais dans le
**tas `[carte+0x10]`** d'ou `0x0206F240` alloue ses enregistrements de 0x1C
octets plus deux chaines dupliquees chacun. A 80 especes il echoue une fois sur
trois, a 102 toujours. **64 est la valeur sure.**

Note : les releves donnent parfois 25 pour 24 demandees. L'overlay 17 ajoute 1 a
4 especes en dur apres la lecture du fichier ; l'une d'elles se retrouve dans le
conteneur.

### Ce que cela change pour l'objectif B

Une zone peut desormais **accepter** 64 especes, alors que seulement 12 modeles
tiennent en memoire. C'est exactement la configuration qu'il faut pour la
rotation : le conteneur est large, et il ne reste qu'a faire tourner les 12
modeles residents a l'interieur de ces 64.

## 42. Une voie plus courte vers la rotation

Le montage du tas des modeles, `ovl17 @0x021A30B0` :

```
021a30b8  bl 0x2032804   ; GetTotalFreeSize(carte+0x1244)     -> r5
021a30cc  bl 0x2032554   ; HeapAlloc(carte+0x1244, r5)         -> bloc
021a30e0  bl 0x2032500   ; CreateExpHeap(carte+0x113C, bloc, r5)
021a30fc  bl 0x21a28a8   ; prechargement des 12 modeles
021a3108  bl 0x2032804   ; ce qui reste du tas des modeles
021a312c  bl 0x2032500   ; CreateExpHeap(carte+0x11C0, reste)
```

Plutot que d'ecrire un chargeur par modele avec sa propre eviction, on peut
**rejouer cette sequence** apres avoir rendu les deux blocs au tas parent :
`HeapFree(carte+0x1244, [carte+0x113C])` et de meme pour `carte+0x11C0`. Le
prechargeur repart alors sur une liste fraiche, et les 12 modeles sont remplaces
d'un coup -- en reutilisant le code du jeu au lieu de le reecrire.

Une vingtaine d'instructions de liaison au lieu de plusieurs centaines.

**Le risque, et il est reel** : detruire le tas des modeles pendant qu'un symbole
visible s'en sert. Il faut donc declencher la rotation a un moment ou aucun
monstre n'est affiche -- la fin d'un combat est le candidat naturel, le jeu y
reinitialise deja les symboles du terrain.

Aucune fonction `DestroyExpHeap` n'a ete trouvee : `0x02032498`, seul candidat,
est en fait une variante de creation (`0x20AF714` puis `0x20AFEA4`). On libere
donc les blocs directement, ce qui suppose que `[carte+0x113C]` porte bien
l'adresse du bloc rendu par `CreateExpHeap` -- **a verifier avant d'y toucher**.

## 43. La fiche de modele porte le pointeur a liberer -- eviction debloquee

Releve sur les fiches rendues par `GetSlot(table, 7..18)`, apres une transition
de zone :

```
2 fiches, ecart entre elles : 176 = 0xB0        <- confirme la taille de fiche
fiche +0x08 = 0235E06C   <- pointeur dans le tas des modeles
fiche +0x0C = 0235E118   <- pointeur dans le tas des modeles
```

**C'etait le dernier inconnu de l'eviction.** Le bloc a rendre au tas se lit en
`fiche+0x08` (et un second en `+0x0C`). Avec `ClearSlot` (`0x0200FD58`), la
liberation de texture (`0x02057F10`, indices 120 a 139) et
`HeapFree` (`0x02032628`), la sequence d'eviction est complete.

## 44. La greffe C affame le petit tas -- fausse piste, et ce qu'il faut faire

La greffe C construit bien le conteneur `+0x2F8` (jusqu'a 64 especes, 41), mais
**elle casse le prechargement des modeles**. Mesure, apres transition :

| bitmap | conteneur `+0x2F8` | modeles charges |
|---|---|---|
| 24 | 24 | **2** sur 12 |
| 48 | 48 | **0** |
| 102 | 0 | 0 |

La cause : tout vient du meme petit tas `[carte+0x10]`. Ma reserve de 1 024
octets, plus les enregistrements de 0x1C et leurs deux chaines dupliquees,
l'epuisent -- et le **second** conteneur, `carte+0x304`, construit par la
fonction voisine `0x021B5348` depuis `fld_mondata.bin`, n'a plus de place.

Or la boucle de prechargement exige l'espece dans **les deux** conteneurs :

```
021a2980  add r0, r6, #0x2f8 ; bl 0x206f500   -> [sp+0x18]
021a2994  add r0, r6, #0x304 ; bl 0x206ef28   -> r0
021a29a4  cmp r1, #0 ; cmpne r0, #0 ; beq     -> espece sautee
```

Un conteneur `+0x304` vide rejette donc toutes les especes, et aucun modele ne se
charge. C'est aussi pourquoi v19 ne montrerait **aucun** monstre en jeu.

### La conclusion, et elle renverse le plan

**Le grand conteneur ne sert a rien.** Pour la rotation, il suffit que le
conteneur porte les especes de la generation courante -- soit 12. Si on fait
tourner **les conteneurs en meme temps que les modeles**, la consommation du
petit tas reste exactement celle du jeu d'origine.

La bonne forme de l'etape 2 est donc : rejouer **tout le montage des monstres
d'une carte** (les deux conteneurs plus le prechargement) avec une liste fraiche
de 12 especes, a un moment ou aucun symbole n'est affiche. Pas de grand
conteneur, pas de chargeur par modele, pas d'eviction fine -- une regeneration
complete, avec le code du jeu.

Il reste a trouver : le contexte `ctx` que reclame le prechargeur (les tas vivent
en `ctx+0x113C`, **pas** dans la structure de carte -- ce sont deux objets
distincts, ce qui explique pourquoi `[carte+0x113C]` n'etait pas un pointeur),
et le point de sortie de combat ou greffer la regeneration.

## 45. La greffe R seule ne suffit pas : les conteneurs commandent

`0x021A2FA0(ctx)` est bien le montage complet, et `0x021A316C` en est le
**demontage** : il teste chaque tas (`0x020328C4`), le vide (`0x02032740`) puis
le detruit (`0x0203248C`), pour `ctx+0x11C0` et `ctx+0x113C`. La fonction est
donc reentrante et sans fuite -- le jeu l'appelle depuis sept endroits.

La greffe R rafraichit la liste de prechargement en tete de cette fonction. Elle
s'execute correctement, mesure faite : apres une transition, la liste porte bien
douze especes neuves.

**Mais zero modele ne se charge.**

| | |
|---|---|
| especes demandees | 12 |
| modeles charges | **0** |

La raison est la meme qu'au 44 : la boucle de prechargement exige l'espece dans
les deux conteneurs `carte+0x2F8` et `carte+0x304`. Or ces conteneurs sont batis
par les gestionnaires asynchrones `0x021B5250` et `0x021B5348`, pilotes par une
machine a etats **au chargement de carte uniquement** -- pas par `0x021A2FA0`.
Changer la liste apres eux ne fait que la desynchroniser.

Autre mesure : 24 tours de marche sans franchir de limite ne declenchent **aucun**
appel a `0x021A2FA0`. Aucun des sept appelants ne tourne pendant la marche
simple.

### La forme correcte, enfin

Les conteneurs sont le portier. Il faut donc qu'ils soient **plus larges que la
liste**, et que la rotation se fasse a l'interieur :

| greffe | quand | role |
|---|---|---|
| C | chargement de carte | remplir le conteneur de **36 especes** tirees au hasard |
| R | chaque montage | remplir la liste de **12** especes **prises dans le conteneur** |

La greffe R lit alors les especes directement dans le bloc d'enregistrements du
conteneur (`[conteneur+4]`, pas de 0x1C, cle en `+0x08`), ce qui garantit qu'elle
ne demande jamais une espece que le portier refusera.

Et la greffe C ne doit **rien allouer** : c'est sa reserve de 1 024 octets sur le
petit tas `[carte+0x10]` qui affamait le second conteneur (44). Un tampon statique
de 72 octets dans le bourrage ARM9 `0x020F1E40` tient 36 identifiants, ce qui
fixe le plafond a 36 -- confortablement sous les 64 mesures au 41.

La place se trouve en supprimant la greffe A : si la greffe R remplit la liste a
chaque montage, tirer une espece au moment du parsage d'`encmons` ne sert plus a
rien.

## 46. La chaine complete, validee : greffes B, C et R

Trois greffes, plus de greffe A. Tout est mesure sur la sauvegarde de transition.

| greffe | ou | role |
|---|---|---|
| **C** | les DEUX `bl CopyList` des constructeurs de conteneur (`0x021B52C4` et `0x021B53C8`), plus les deux `add r1, sp, #off` qui suivent | fait porter aux conteneurs 16 especes au lieu des 12 de la liste, depuis un tampon **statique** en `0x020F1E40` -- elle n'alloue rien |
| **R** | `mov r7, r0` en tete du montage `0x021A2FA0` | remplit la liste de prechargement avec 12 especes **consecutives** prises dans le conteneur, a partir d'un index tire au hasard |
| **B** | corps de `ChooseFieldMonsterId` (`0x02073FEC`) | le tireur de terrain rend une espece de la liste, uniformement |

La greffe A -- tirage au moment du parsage d'`encmons` -- est **supprimee** : la
greffe R remplit la liste a chaque montage, ce qui la rend inutile.

### Ce que les mesures ont impose, etape par etape

| ce qui a ete essaye | resultat |
|---|---|
| greffe C allouant 1 Kio sur `[carte+0x10]` | conteneur 1 rempli, **conteneur 2 vide**, 0 modele |
| greffe C sur le seul conteneur 1 | 12 especes demandees, **0 modele** |
| greffe R tirant dans le bitmap | 12 especes, **0 modele** (elles ne sont pas dans les conteneurs) |
| greffe R gardant l'index dans **r2** | listes presque identiques : `AddSpecies` ecrase r2 (il y laisse `nombre * 2`) |
| 12 tirages independants | jusqu'a **trois fois** la meme espece, 10 modeles sur 12 |
| conteneur a 36 | conteneur 2 vide |
| conteneur a 24 | 10 a 12 modeles |
| conteneur a 20 | 11 modeles le plus souvent |
| **conteneur a 16, 12 consecutives** | **12 modeles a chaque transition** |

### L'etat mesure de v27

```
conteneur 16 | liste 12 | modeles 12
transition 1 : 10,11,15,16,17,18,19,20,21,1,2,3
transition 2 : 11,15,16,17,18,19,20,21,1,2,3,4
transition 3 : 19,20,21,1,2,3,4,5,6,9,10,11
transition 4 : 2,3,4,5,6,9,10,11,15,16,17,18
```

Douze especes **distinctes**, douze modeles charges, a chaque regeneration.

### La limite qui reste, et elle est structurelle

Le conteneur ne tient que **16** especes : au-dela, il prend son dû sur le meme
parent que le tas des modeles et des modeles cessent de se charger. Or on en
prend 12 : deux fenetres consecutives partagent donc au moins 8 especes. **La
rotation ne peut deplacer que quatre especes a la fois.**

Elargir la fenetre de rotation demanderait de reduire le nombre visible -- par
exemple 8 especes prises dans 16, ce qui autorise deux fenetres disjointes. C'est
un arbitrage a faire en jeu : douze monstres avec peu de rotation, ou huit avec
une rotation franche.

Et il reste une inconnue qu'aucune mesure de laboratoire ne tranche : **le
montage `0x021A2FA0` tourne-t-il en fin de combat ?** Vingt-quatre tours de
marche n'en declenchent aucun appel. Si oui, la rotation se voit a chaque
bataille ; si non, elle ne se voit qu'aux chargements de zone, et v18 (douze
especes tirees parmi 102 a chaque chargement) reste preferable.

## 47. CORRECTIONS MAJEURES — le tas des modeles est un FRAME HEAP

Etabli dans `work/re/RAPPORT_SPAWN.md`, mesures a l'appui. Trois sections
precedentes sont fausses.

### Ce qui est faux

| section | ce qui y est ecrit | ce qui est mesure |
|---|---|---|
| **43** | « la fiche porte le pointeur a liberer, eviction debloquee » | `fiche+0x08` est un objet de rendu de **0xAC** o (`0x020360E4`), `fiche+0x0C` un objet de **0x2C** o (`0x020368D0`). **Aucun n'est le modele.** Le blob `.cchr` decompresse n'est reference nulle part dans la fiche |
| **32**, **42** | `0x02032500 = CreateExpHeap` | `0x02032500` ecrit la magie **`FRMH`** (litteral `0x020AF88C`) : c'est **`CreateFrmHeap`**. `0x02032498` ecrit **`EXPH`** (`0x020AF338`) : c'est **`CreateExpHeap`** |
| **32** | « `0x02057F10` libere la texture n° i » | `0x02057F10(gestionnaire, etiquette)` balaye **16 entrees de pas 0xD4** et libere celles portant l'etiquette. Ce n'est pas un index de texture |
| relais interne | « maximum 3 acteurs simultanes » | **faux, et c'etait ma lecture** : le journal a 4 salves donnait 3, celui a 40 salves donne **5, en croissance**. Le plafond code est **12** (`0x021A21BC mov r2,#0xc`) |

### Le fait qui commande tout

`[ctx+0x113C]` est un tas de signature **`0x46524D48` = `FRMH`**, 187 440 octets,
**0 libre** apres prechargement. Et `HeapFree` (`0x02032628`) aiguille sur la
signature :

| signature | route | effet |
|---|---|---|
| `EXPH` | `0x020AF788(tas, ptr)` | libere **ce bloc** |
| `FRMH` | `0x020AF9FC(tas, 3)` | **rembobine tout le tas**, `ptr` ignore |
| `UNTH` | rien | no-op |

**Donc l'eviction modele par modele est structurellement impossible en l'etat**,
et il n'y a rien a prendre non plus : le reliquat du tas est reverse a
`ctx+0x11C0` en `0x021A3108`-`0x021A312C`.

187 440 / 18 345 = **10,2 modeles**. Le plafond memoire et le plafond de 12
emplacements sont au meme endroit : **il n'y a pas de marge cachee.**

## 48. Trois pistes neuves, sorties de ces mesures

**(a) Convertir le tas des modeles en `ExpHeap`.** Remplacer
`0x021A30E0 bl 0x02032500` par un appel a `0x02032498`, qui rend `HeapFree(ptr)`
reellement fonctionnel. Elle prend un 4e argument en `r3` (direction), or `r3`
porte `ctx+0x13C` a cet endroit : il faut un petit talon, pas un remplacement en
place. Surcout mesure : en-tete 0x4C au lieu de 0x30 et 0x10 o par bloc, soit
**604 octets sur 187 440**. Le demontage (`0x021A316C`) et le calcul du libre
(`0x02032804`) aiguillent deja les trois magies, donc ils suivront.
**Hypothese non verifiee** ; le test tient en une sonde : poser le talon en RAM,
franchir une limite, lire la signature de `[ctx+0x113C]`.

**(b) `0x021A2B1C` recolle les modeles aux acteurs deja vivants** -- le
prechargeur l'appelle en sortie (`0x021A2AF0`). Une regeneration complete **n'a
donc pas besoin qu'aucun symbole ne soit affiche**, contrairement a ce que
craignait la §42. Il suffit que les especes des acteurs vivants figurent dans la
nouvelle liste. Une greffe R qui construit la liste comme « les especes des
acteurs vivants, puis des especes neuves pour completer » rend la regeneration
**sure a tout instant**. Et `ctx` s'obtient par `0x0218B5B0 = GetFieldCtx()` =
`[[0x021D82E0]+4]`, mesure a `0x022A6C28`.

**(c) Le levier de variete n'est pas le nombre de modeles, c'est leur taille.**
187 440 octets tiennent 10 modeles medians mais **34** de la famille metallique
(5 508 o). Un pool a budget cumule -- plutot qu'un compte fixe de 12 -- remplirait
le tas au plus pres a chaque carte. C'est du travail hors ligne dans
`randomizer.py`, **sans une seule instruction de greffe et sans risque**.

### Un temoin rejouable, a garder

L'espece **254** est dans la liste de prechargement de l'etat de transition mais
pas parmi les modeles charges, et elle occupe pourtant deux emplacements
d'acteur : c'est un **monstre invisible reproductible**, utile pour toute mesure
future.

Et une regle de methode : **la marche du robot quitte la carte a rencontres** au
bout d'une vingtaine de salves de 30 images. Toute mesure de duree sur le terrain
doit verifier que le jeu de modeles reste non vide, sinon elle ne mesure rien.

## 49. Budget de taille cumule : le bestiaire entier, contre trois especes par zone

Piste (c) du 48, implementee et mesuree. La greffe A2 remplace la greffe A : au
lieu d'un bitmap d'un bit par espece, une **table de classes de taille, 2 bits
par espece** (128 octets), et un **budget cumule** remis a plein a la premiere
espece de chaque carte.

| classe | taille du modele | cout facture |
|---|---|---|
| 0 | > 32 Kio, ou sans modele | espece ecartee (4 seulement) |
| 1 | <= 12 Kio | 6 unites de 2 Kio |
| 2 | <= 20 Kio | 10 |
| 3 | <= 32 Kio | 16 |

Budget : **90 unites = 180 Kio**, sur les 183 452 octets d'empreinte mesures.
Quand le budget ne suffit plus, la greffe **n'ajoute rien** -- mieux vaut neuf
monstres visibles que douze dont trois invisibles.

### Mesure en jeu, quatre transitions

```
transition 1 : liste 9 | modeles 9 | 180,149,114,96,163,3,236,3,148
transition 2 : liste 8 | modeles 8 | 149,32,5,261,159,87,276,267
transition 3 : liste 9 | modeles 9 | 28,84,42,99,242,26,191,109,116
transition 4 : liste 8 | modeles 8 | 175,158,125,266,176,56,136,103
```

**Tous les modeles se chargent, a chaque fois.** Et les identifiants montent a
276 : le tirage porte bien sur tout le bestiaire, pas sur les seules petites
especes.

### Un piege ARM a ne plus refaire

La premiere version gardait le compteur d'essais dans **`ip`**. C'est le registre
de travail des appels : `rand_below` l'ecrase, le compteur devient quelconque et
la boucle part a l'infini. Symptome : **ecran noir a la transition**, identique a
celui d'une disposition de fichiers invalide -- deux causes tres differentes pour
un meme ecran. Le compteur doit vivre dans un registre que l'appel preserve.

### Le vrai arbitrage, chiffre

Trois classes sur 2 bits facturent chacune a sa borne haute : le surcout moyen
est de **11,3 unites facturees contre 8,9 reelles**, soit 25 %. Affiner les
bornes ne fait gagner qu'une demi-espece (8,0 -> 8,5). Facturer a la mediane
rendrait 10 especes mais autoriserait des depassements, donc des invisibles.

**Le choix se pose donc en clair :**

| | especes par zone | especes atteignables dans tout le jeu |
|---|---|---|
| v18 (`--taille-max 16384`) | **12** | 102 |
| v29 (budget cumule) | **9** | **256** |

C'est le meme budget memoire vu de deux facons. Douze monstres par zone
n'existent que si l'on renonce aux 158 especes dont le modele depasse 16 Kio.

## 50. (b) La regeneration sure a tout instant : conception, et le mur qui reste

### Pourquoi c'est la seule voie

Sur un frame heap, **la regeneration totale est la seule liberation possible** :
`HeapFree` rembobine tout ou ne fait rien. Ce n'est pas un choix de style, c'est
la seule operation que l'allocateur sait faire. `0x021A2FA0(ctx)` fait exactement
cela -- demontage (`0x021A316C`) puis reconstruction.

### Ce qui la rend sure, et c'est mesure

`0x021A2B1C`, appelee en sortie du prechargeur (`0x021A2AF0`), **recolle les
modeles aux acteurs deja vivants**. Une regeneration n'exige donc pas qu'aucun
monstre ne soit affiche : il suffit que les especes des acteurs vivants figurent
dans la nouvelle liste.

Et on sait les enumerer. Predicat **valide sur temoin** (`sonde_acteurs.lua` :
`[-1 x 12]` avant la transition, `[254 96 57 -1 ...]` apres, les trois especes
etant bien dans la liste de prechargement) :

```
variante = [carte+0x02] & 3                 (0x021A21AC)
base     = 0x70 + 12 * variante
pour i de 0 a 11 : a = GetSlot(table, base+i)
                   si a != 0 et (short)[a+2] >= 0 -> espece [a+2] VIVANTE
```

C'est le predicat que le jeu utilise lui-meme pour trouver un emplacement libre
(`0x021A20C0`). Douze lectures. Il n'existe **aucun compteur de references**
(verifie : `0x02072AEC` n'incremente rien, `0x021A1364` ne decremente rien) : ce
balayage est le seul moyen.

### La greffe R2

Au meme point d'accroche que la greffe R (`0x021A2FA4`) :

1. vider la liste ;
2. y remettre **les especes des acteurs vivants** -- c'est ce qui rend
   l'operation sure ;
3. poser le budget a `90 - 12 x (nombre d'acteurs remis)`, puisque leurs modeles
   consommeront aussi du tas ;
4. completer en appelant douze fois la greffe A2, qui tire dans le budget
   restant. `bl GREFFE_A2` fonctionne comme « ajoute une espece » : A2 termine
   par `b AddSpecies`, qui rend la main par `bx lr` a l'appelant de A2.

Puis un **declencheur** : le montage ne tourne ni pendant la marche ni en fin de
combat (mesure du 46), donc il faut l'appeler soi-meme, avec
`ctx = 0x0218B5B0()` = `[[0x021D82E0]+4]`, mesure a `0x022A6C28`.

### Le mur : la place

R2 fait environ **30 instructions, 120 octets**. Inventaire de ce qui reste :

| emplacement | libre |
|---|---|
| zone `0x020E7268` | **8 o** (table 128 + greffe A2 128 + couts + budget = 0x110 sur 0x118) |
| queue de `ChooseFieldMonsterId` | **76 o** (greffe B en occupe 56 sur 132) |
| bourrage `0x020F1E40` | 72 o |
| bourrage `0x020F1D2C` | 54 o |

**210 octets au total, en quatre morceaux non contigus.** R2 tient donc, mais il
faut la couper en deux moities reliees par un branchement -- par exemple
19 instructions dans la queue du tireur et 18 dans le bourrage `0x020F1E40`.

L'autre voie, plus propre, est de liberer les ~600 octets du prechargeur
`0x021A28A8` : il devient inutile le jour ou R2 remplit la liste a chaque
montage. Mais cela impose de stocker l'overlay 17 en clair, donc de changer la
disposition des fichiers, donc de redemander une sauvegarde d'etat au joueur.

## 51. Le declencheur est dans l'ARM9, et il tient deja `ctx`

Trouvaille qui change la facture de (b) : **tout peut vivre dans l'ARM9**, sans
toucher l'overlay 17 -- donc sans changer la disposition des fichiers, donc sans
invalider les sauvegardes d'etat du joueur. On n'appelle les fonctions de
l'overlay que par leur adresse, et il est resident pendant le jeu de terrain.

Le tic d'apparition est `0x020733E8` (ARM9) :

```
02073430  bl 0x200f398          ; table des emplacements -> [sp+0x24]
02073438  bl 0x218b5b0          ; GetFieldCtx()          -> [sp+0x20]   <<< ctx
0207344c  bl 0x2010220          ; increment de cadence
02073450  ldr r1, [r7, #8] ; add r0, r1, r0 ; str r0, [r7, #8]
0207345c  cmp r0, #0x3e8        ; pas encore -> sortie
02073460  blt 0x2073d4c
02073464  ldrh r1, [r7, #2]     ; <<< POINT D'ACCROCHE : on va faire apparaitre
02073478  bl 0x21a20c0          ; FindFreeActorSlot
```

Deux choses tombent bien : le point d'accroche `0x02073464` n'est atteint que
lorsque le jeu **va reellement faire apparaitre un monstre**, ce qui donne une
cadence naturelle ; et `ctx` est deja sur la pile de l'appelant en `[sp+0x20]`,
donc accessible sans le rechercher.

Le declencheur remplace `ldrh r1, [r7, #2]` par un appel qui compte les
apparitions, et une fois sur K appelle la greffe R2 puis
`0x021A2FA0([sp+0x20])`, avant d'executer l'instruction otee.

### Inventaire de la place, tout en ARM9

| emplacement | libre | usage prevu |
|---|---|---|
| queue de `ChooseFieldMonsterId` `0x02074024` | 72 o | greffe R2, premiere moitie |
| bourrage `0x020F1E40` | 72 o | greffe R2, seconde moitie |
| bourrage `0x020F1D2C` | 54 o | declencheur |
| zone `0x020E7268` | 8 o | compteur et graine |

**Le balayage des acteurs n'est pas optionnel.** Regenerer sans remettre les
especes des acteurs vivants laisse ces acteurs pointer sur de la memoire
rembobinee, que le moteur 3D relit a chaque image : corruption ou exception de
donnees. C'est la seule partie de R2 qui ne peut pas etre simplifiee pour une
premiere version.

## 52. (b) La greffe de rotation est ecrite ; le declencheur reste introuvable

`scripts/patch_rotation2.py`. Trois morceaux dans l'ARM9, relies par des
branchements, tous verifies au desassemblage :

| morceau | adresse | taille | role |
|---|---|---|---|
| C1 | `0x02074024` (queue du tireur, code mort) | 72/72 o | compte, vide la liste, prend la table des emplacements |
| C2 | `0x020F1E40` | 72/72 o | remet dans la liste **les especes des acteurs vivants** |
| C3 | `0x020F1D2C` | 52/54 o | complete au budget par la greffe A2, puis appelle le montage |

Le balayage des acteurs (C2) est la condition de surete : sans lui, les symboles
deja affiches pointent sur de la memoire rembobinee.

### Deux points d'accroche essayes, aucun ne se declenche

| accroche | resultat |
|---|---|
| `0x02073464`, apres le seuil de cadence | **jamais atteinte**. Une sortie anticipee (`0x0207342C bls`) court-circuite le tic des que la carte porte son quota de symboles. Compteur a zero apres 50 s de marche, periode forcee a 1 |
| `0x020733F0` (`movs r7, r0`), entree de la fonction | **jamais atteinte non plus**. Verifie par un temoin minimal -- une greffe qui ne fait qu'incrementer un compteur : il reste a zero |

Donc `0x020733E8` n'est pas le tic par image que je croyais : elle est appelee
sous condition, et dans l'etat de transition -- trois symboles vivants, quota
plein -- elle ne tourne pas du tout.

**Le harnais ne peut pas trancher la suite** : il ne sait pas se battre, donc le
quota reste plein et tout le sous-systeme de rencontre reste au repos. Ce qui
manque n'est plus du desassemblage, c'est un etat de jeu ou le systeme travaille.

### Ce qu'il faudrait, par ordre de cout

1. **Essayer v32 en jeu.** Si l'accroche ne se declenche jamais, la ROM se
   comporte exactement comme v30 -- aucun risque. Si elle se declenche, le lot
   change en marchant. C'est le test le moins cher, et le seul qui reponde.
2. Une sauvegarde d'etat prise **juste apres un combat**, quota non plein : le
   sous-systeme de rencontre travaillerait, et le harnais pourrait mesurer.
3. Chercher une fonction de terrain appelee inconditionnellement a chaque image.
   `0x0200F398` en est une, mais elle est appelee de partout : y greffer un appel
   au montage serait dangereux.

## 53. Pourquoi v32 ne montrait qu'un seul monstre, et l'architecture qui corrige

Retour de jeu sur v32 : la regeneration se declenche bien (~30 s, deux periodes),
aucun plantage, mais **un seul monstre apparait ensuite, partout, jusqu'au
changement de zone**.

La cause : **le montage appele en pleine partie ne reconstruit pas les
conteneurs.** Ils sont batis par une machine a etats asynchrone, uniquement au
chargement de carte. La nouvelle liste ne franchit donc le portier que pour les
especes deja presentes dans les anciens conteneurs -- c'est-a-dire celles des
acteurs vivants, que la greffe y remet par surete. Les trois acteurs etaient de
la meme espece : d'ou un seul monstre. Et un changement de zone reconstruit les
conteneurs, d'ou le retour a la normale.

**La regle qui en decoule : la liste doit toujours etre tiree DANS le conteneur.**
Le conteneur est le portier ; rien d'autre ne passe. C'etait deja la lecon du 45,
mal appliquee.

### L'architecture de `scripts/patch_b.py`

| piece | ou | role |
|---|---|---|
| bitmap 64 o | zone +0x00 | especes autorisees : rodeuses, hors boss, modele <= 20 Kio -> **186 especes** |
| greffe C 96 o | zone +0x40, sur les deux constructeurs | remplit les conteneurs de **20 especes tirees au hasard**, une fois par carte |
| greffe R 212 o | zone +0xD0, puis `0x02074024`, puis `0x020F1E40` | a chaque montage : vide la liste, y remet les especes des **acteurs vivants**, puis **8 especes consecutives** prises dans le conteneur a partir d'un index tire au hasard |
| declencheur 52 o | `0x020F1D2C`, accroche `0x020733EC` | appelle le montage toutes les 1 024 images |

Le tirage de la greffe C est **aleatoire**, corrigeant le defaut de v27 qui
prenait les 16 plus petits identifiants -- les memes pour toutes les zones.

L'accroche est passee sur `sub sp, sp, #0x1c0` : contrairement au `movs r7, r0`
qui suit, elle ne laisse pas de drapeaux a reproduire.

### Ce que le harnais ne peut pas exercer

`0x020733E8` **ne tourne pas** quand la carte porte son quota de symboles :
verifie par un temoin qui ne fait qu'incrementer un compteur, sur les deux
accroches essayees. Or le robot ne se bat jamais, donc le quota reste plein. En
vrai jeu la fonction tourne -- le joueur l'a constate sur v32.

Et depuis la sauvegarde de v30, la marche ne franchit plus la limite de zone : ni
le declencheur ni la transition ne sont donc exercables en laboratoire. **Seul le
joueur peut trancher v33.**

### v33 : plantage au chargement, et un defaut de conception

**v33 ne demarre pas** : exception de donnees a `0xFFFF0108` au moment ou la
partie se charge. Attrapee par le test de demarrage, la ROM n'a pas ete livree.

Et en cherchant la cause, un **second defaut** apparait, independant du
plantage : la greffe C est appelee par **les deux** constructeurs de conteneur,
et elle refait un tirage a chaque fois. Les deux conteneurs recoivent donc
**deux ensembles differents** de 20 especes. Or le spawn exige l'espece dans les
deux : l'intersection vaut environ 20 x 20 / 186 = **2 especes**. Meme sans le
plantage, v33 aurait montre deux monstres.

Le correctif demande que le second appel **reutilise** le tampon du premier,
donc un second talon distinct et un mot pour memoriser le compte -- soit une
vingtaine d'octets qu'il n'y a plus dans la zone. La piste reste ouverte mais
elle demande de reprendre le plan memoire, pas d'ajuster une constante.

**Etat de reference : `work/dq9_v29.nds`** -- 9 especes par zone tirees parmi
256, renouvelees a chaque chargement de carte, aucun monstre invisible, validee
en jeu.

## 54. LE TAS DES MODELES EST CONVERTI EN ExpHeap -- verifie a l'octet

C'est la porte que tout le reste attendait. Sur un frame heap, `HeapFree`
rembobine le tas entier et ignore le pointeur : aucune eviction n'est possible.
Sur un `ExpHeap`, il **libere reellement le bloc**.

### Le talon, deux instructions

```
0x021A30E0   bl 0x02032500        ; CreateFrmHeap  -> devient  bl TALON
TALON        mov r3, #4
             b  0x02032498        ; CreateExpHeap, queue d'appel
```

`0x02032498` prend un **quatrieme argument** que `0x02032500` n'a pas : il
aboutit a `0x020AFEA4`, l'initialisation de l'allocateur. Le frame heap y passe
**4** (`0x02032530 mov r2, #4`). **Avec r3 = 0, plus aucun modele ne se charge ;
avec r3 = 4, tout fonctionne.** C'etait tout le probleme -- et c'est aussi la
preuve que le talon s'applique bien.

Les deux conventions d'arguments sont identiques par ailleurs : `0x020AF984` et
`0x020AF714` font tous deux `add r1, r1, r0`, donc (debut, **taille**). Seuls
diffèrent l'en-tete minimal, 0x30 contre 0x4C, et la signature ecrite.

### Verification

En remontant depuis un pointeur interieur au tas (`fiche+0x08` d'un modele
charge) jusqu'a l'en-tete :

| | en-tete | signature | modeles charges sur 3 transitions |
|---|---|---|---|
| v29 telle quelle | `0x0235AF2C` | **FRMH** | 9, 8, 9 |
| v29 + talon | `0x0235AF2C` | **EXPH** | 9, 8, 9 |

Meme adresse, meme comportement, signature changee. La fiche se decale de 0x18,
ce qui correspond a l'en-tete plus grand.

### Ce que cela debloque

`HeapFree(tas, ptr)` = `0x02032628` libere desormais un bloc precis. Combine
avec :

- le balayage des acteurs vivants, qui dit quelles especes sont **encore
  affichees** et donc intouchables ;
- `ClearSlot` (`0x0200FD58`) pour vider l'emplacement ;
- le fait que **c'est nous qui appellerons le chargeur**, donc que nous
  connaitrons le pointeur a rendre -- ce qui contourne l'obstacle B du 43, ou le
  pointeur du blob etait introuvable dans la fiche.

... l'eviction modele par modele devient possible. Il reste a precharger **moins**
de modeles pour se menager de la place : le joueur observe rarement plus de cinq
monstres a l'ecran, donc six modeles residents suffisent, ce qui libere environ
110 Kio des 187.

**Statut : la conversion est acquise et mesuree.** Le chargement a la demande
reste a ecrire.

## 55. Prechargement reduit : 5 modeles residents, 112 Kio libres

Le budget de la greffe A2 est un seul immediat (`mov r0, #90`, 6e mot). Mesure
sur trois transitions, avec le tas converti en ExpHeap :

| budget | especes | modeles | etendue occupee | libre estime |
|---|---|---|---|---|
| 90 | 9 | 9 | 161 452 o | ~26 Kio |
| **60** | **5** | **5** | **75 240 o** | **~112 Kio** |
| 45 | 4 | 4 | 53 096 o | ~139 Kio |

L'etendue est mesuree comme l'ecart entre le plus bas et le plus haut pointeur de
bloc des fiches chargees (`fiche+0x08`).

Le joueur observe rarement plus de cinq monstres a l'ecran, donc cinq residents
suffisent -- et les 112 Kio restants tiennent six modeles supplementaires
charges a la demande, dans un tas qui sait desormais les rendre un par un.

### Ce qui reste a ecrire, et la voie la moins couteuse

Le chargement a la demande reprend la sequence du prechargeur :
`0x020D91EC` (ouverture d'archive, 8 arguments dont 4 sur la pile),
`0x020D9548` (extraction du membre), `0x0207551C` (`.cchr`),
`0x02075664` (decompression vers le tas), `0x02036814` (enregistrement),
`0x0200FD48` (`SetSlot`), `0x020D962C` (fermeture). Ecrite de zero, cela fait
une cinquantaine d'instructions, plus le `sprintf` du nom de membre -- environ
200 octets, alors qu'il en reste 198 en trois morceaux.

**La voie economique est donc de reutiliser le prechargeur lui-meme** : le
patcher pour qu'il charge UNE espece, lue dans un mot global, dans un emplacement
choisi, sans vider les emplacements ni reallouer le tableau de fiches. La greffe
tombe alors a une quinzaine d'instructions au lieu de cinquante, puisque toute la
mecanique d'archive est deja la. Cela suppose de patcher l'overlay 17, donc de
garder la disposition de v30.

L'eviction, elle, est desormais complete : balayage des acteurs vivants pour
savoir quelles especes sont intouchables, `ClearSlot` pour vider l'emplacement,
`HeapFree` pour rendre les blocs -- dont on connaitra les pointeurs puisque c'est
notre code qui appellera `0x02075664`.

## 56. Les depots communautaires, et le plafond du conteneur qui tombe

Deux depots fournis par le joueur : `DQIX/dqix-functions` (noms de fonctions au
format resymgen) et `DQIX/dqix-decomp` (configuration de decompilation, cibles
JPN et USA).

### Ce qu'ils valident

En croisant deux entrees qui portent les deux adresses -- `ChooseFieldMonsterId`
(eur `0x2073FEC`, usa `0x2073FDC`) et `GenerateCompanionByBT` (eur `0x209AFE4`,
usa `0x209AFD4`) -- on obtient **EU = USA + 0x10** pour l'ARM9. Les adresses de
l'overlay 17 sont **identiques**.

Traduits ainsi, `config/usa/arm9/symbols.txt` et son equivalent overlay 17
donnent **7 402 fonctions avec leurs tailles** (`work/communaute/symboles_eu.txt`).
Et les dix adresses que j'avais etablies a la main tombent **chacune exactement
sur une frontiere de fonction**.

L'allocateur est nomme :

| EU | nom reel | ce que je l'appelais |
|---|---|---|
| `0x02032498` | `SafeAllocator::CreateTypeB(void*, u32, int)` | CreateExpHeap |
| `0x02032500` | `SafeAllocator::CreateTypeA(void*, u32)` | CreateFrmHeap |
| `0x02032554` | `SafeAllocator::Allocate(u32)` | HeapAlloc |
| `0x02032628` | `SafeAllocator::Free(void*)` | HeapFree |
| `0x02032698` | `SafeAllocator::Reset()` | -- |
| `0x02032740` | `SafeAllocator::Destroy()` | « vidage » |

### La table des tailles de tas, et pourquoi mon premier essai avait echoue

`func_ov017_021A02F0` monte les tas du contexte de terrain. Sa boucle lit une
table `{identifiant, taille}` par pas de 8 en `0x021D6984` (terminee par `{0,0}`
en `0x021D6A2C`) et place chaque handle en **`ctx + 0x38 + id * 0x14`**.

Le handle du tas des conteneurs etait mesure a `ctx+0xD8` : `(0xD8-0x38)/0x14`
= **identifiant 8**. Celui du second a `ctx+0x27C` = **identifiant 29**, dont la
table donne 1 024 -- les deux concordent.

**Ces tailles sont lues une seule fois, a la creation du contexte de terrain.**
Les patcher en RAM apres avoir charge une sauvegarde arrive donc toujours trop
tard : il faut les mettre dans la ROM. C'est ce qui avait fait echouer mon
premier essai.

### Le plafond de 16 especes tombe

v34 = v19 avec les identifiants 8-11 portes a 40 960 et 29-32 a 8 192. Mesure sur
la sauvegarde du joueur, prise apres un demarrage a froid :

| | avant | apres |
|---|---|---|
| tas du conteneur 1 | 11 392 o | **40 912 o, dont 20 748 libres** |
| especes acceptees par le conteneur 1 | 16 a 24 | **102** |

En jeu : 9 a 10 especes visibles, une invisible occasionnelle. Le nombre visible
reste borne par le **tas des modeles**, pas par le conteneur -- mais le portier,
lui, ne bride plus.

### Et le conteneur 2 se reconstruit, contrairement a ce que je croyais

`0x0206EE90` n'est pas un constructeur : c'est un **pilote de parseur**. Il range
ses arguments dans un contexte global (`count` en u16, tas, tampon, conteneur)
puis lance le parseur de tables tague (`0x02030744`) sur le blob
`fld_mondata.bin`, la liste d'identifiants servant de **filtre**.

Donc le rebatir en cours de jeu ne demande qu'une chose : **avoir encore le
blob**. Or il est relache aussitot (`0x021B540C bl 0x020301D8`), et de meme pour
`mon_data` (`0x021B5314`).

| | taille |
|---|---|
| `fld_mondata.bin` | 15 840 o |
| libre dans le tas du conteneur 1 apres agrandissement | 20 748 o |

**Le blob tient dans la place liberee.** La recette de l'objectif B devient :
garder une copie des deux blobs au lieu de les relacher, puis rebatir les deux
conteneurs a volonte en rappelant leurs pilotes avec ces copies.

*Non resolu : le conteneur 2 refuse 102 especes -- il n'alloue rien, donc ce
n'est pas la memoire. A trancher avant d'aller plus loin.*

## 57. Le plan memoire complet, et ce que les mesures du jour ont tranche

### L'espace de code disponible, epuise

Balayage des plages a zero de l'image ARM9 decompressee : **529 octets en
tout**, six regions, dont la zone de 280 octets deja utilisee. L'overlay 17
n'en offre aucune -- ses deux « trous » de 48 octets a `0x021D622C` et
`0x021D6298` sont en realite des enregistrements de 0x34 presque vides dans une
table que le jeu lit (mots non nuls a `0x021D6228`, `0x021D625C`, `0x021D628C`).

Les trois candidats restants ont ete valides par canari -- motif ecrit en RAM,
releve intact apres huit marches et deux chargements de carte complets
(`scripts/lua/canari.lua`) :

| region | octets | contenu final |
|---|---|---|
| `0x02073FEC` | 68 | greffe B |
| `0x02074030` | 64 | rotation, morceau A (queue morte du tireur) |
| `0x020F1E40` | 72 | rotation, morceau B |
| `0x020F1D2C` | 52 | rotation, morceau C |
| `0x020F1CB8` | 40 | greffe C, morceau 1 |
| `0x020E7C78` | 40 | greffe C, morceau 2 |
| `0x020E8888` | 40 | greffe C, morceau 3 |
| zone `+0x60` | 32 | greffe C, morceau 4 |

La table des classes est passee de 512 a **384 identifiants** (96 octets au lieu
de 128) pour liberer ces 32 octets : le plus grand identifiant de terrain vaut
334, et 384 reste un immediat ARM encodable.

### Le tas parent est plein : plus d'agrandissement possible

Les tas du contexte de terrain sont tailles dans l'ExpHeap **`0x022A3200`**
(1 297 864 o, 25 enfants de `0x022A3278` a `0x02321BF8`). Sa liste de blocs
libres (`+0x24`, chaque bloc portant sa taille en `+0x00`) ne contient qu'un
bloc : **18 002 octets**. L'agrandissement de v34 (+146 944 o) tenait donc de
justesse ; il n'y a pas de place pour un second.

En-tete NNS, decalages **mesures** (la premiere lecture, a `+0x14`/`+0x18` et
`+0x20`/`+0x24`, rendait des etendues de 36 Mo) :

| decalage | champ |
|---|---|
| `+0x00` | signature `FRMH` / `EXPH` |
| `+0x0C`, `+0x10` | liste des enfants |
| `+0x18`, `+0x1C` | debut, fin |
| `+0x24`, `+0x28` | tete, queue (frame heap) ou liste libre (exp heap) |

### Le cout reel d'une espece dans le conteneur

| | mesure |
|---|---|
| tas du conteneur 1 (id 8) | 40 912 o, 17 884 libres apres 102 especes |
| cout par espece | **226 octets** (0x1C d'enregistrement + trois chaines dupliquees) |
| capacite reelle | **181 especes** |
| tas du conteneur 2 (id 29) | 8 144 o, 5 300 libres apres 102 noeuds -> **28 o par noeud**, 290 especes |

D'ou le plafond de **150** especes de la greffe C : `0x0206F348` alloue le bloc
d'enregistrements en une fois et abandonne proprement s'il echoue, mais la suite
duplique trois chaines par espece (`0x020DA160`) et range le resultat **sans
test de nullite**. Une exhaustion a ce moment-la donne un pointeur de chaine nul
que le prechargeur passe a son formateur.

### La fenetre doit etre en rang, pas en identifiant

Choisir 150 especes parmi 256 en prenant une plage d'identifiants ne marche pas :
les 256 especes occupent la plage 0-334 avec de grands trous, et une fenetre de
160 identifiants contient de **26 a 179** especes selon son depart. La greffe C
saute donc un nombre d'especes (un rang), pas un intervalle d'identifiants.

Le depart vient de `[carte+0x00] & 0x7F` : il doit etre **identique pour les deux
constructeurs**, appeles l'un apres l'autre (0x021B52C4 puis 0x021B53C8). Un
tirage au hasard imposerait de memoriser le rang entre les deux appels, soit sept
instructions qu'il n'y a pas. Resultat mesure : **c1 = 150, c2 = 150**, les memes.

### Le tireur lit desormais les modeles CHARGES

`FindLoadedModel` (`0x021A2738`) parcourt les emplacements **7 a 18** de la table
`0x020F33D8` et compare l'espece en `fiche+0x02` -- confirme par
`strh fp, [r0, #2]` en `0x021A2A60`, qui l'y ecrit. La greffe B tire donc
directement dans ces emplacements : **une espece qui en sort a forcement son
modele en memoire**, et le monstre invisible disparait par construction.

### Le prechargeur n'a traite que six entrees sur douze -- et le budget est mort

Instrumentation des six sorties du prechargeur (`scripts/lua/pourquoi4.lua`,
`event.onmemoryexecute` sans quatrieme argument), controle sur v34 :

```
tours=6 | conteneur=6 nom=5 narc=4 decompression=0 SetSlot=4 enregistrement=0
```

Et l'ordre des evenements (`scripts/lua/ordre.lua`) est bien celui qu'on
esperait : douze `AddSpecies`, puis le constructeur du conteneur, puis **un
seul** appel au montage, avec la liste deja complete a douze.

Le prechargeur n'a donc pas ete interrompu par la memoire ni par un echec de
chargement : il n'a fait que **six tours sur douze** annonces par
`0x0209C0FC` (= `[carte+0x44+0x18]`, le compte de la liste), etale sur cinq
images. Une espece a ete refusee par le conteneur, une au montage du nom, et les
quatre restantes ont abouti.

Conclusion pratique : **le budget cumule de la greffe A2 ne protegeait de rien**
-- ni le tas ni le nombre de modeles n'etaient satures -- et il ne faisait que
priver le prechargeur de candidats. Il est desormais fixe a 200 unites, hors
d'atteinte. Ce qui limite reellement a quatre modeles reste a etablir, mais deux
choses sont sures : la greffe B rend les especes non chargees inoffensives, et le
montage rappele par la rotation redonne au prechargeur une chance complete.

### CE QUI RESTE OUVERT

Mesure de controle sur v34, la version que le joueur a validee :

```
liste 12 (0 hors conteneur) | modeles 4 | tas 187 392 o dont 126 984 LIBRES
```

Quatre modeles seulement, avec 124 Kio de tas encore libres : **le plafond n'est
pas la memoire**, et le budget cumule de la greffe A2 ne sert donc a rien. Le
prechargeur peut abandonner une espece a cinq endroits (conteneur, nom de
fichier, membre de NARC, decompression, enregistrement du modele) ; lequel
domine reste a mesurer. Le harnais ne peut pas trancher seul : son quota de
symboles est plein, donc le tic d'apparition ne tourne pas et rien de neuf n'est
demande.

### v35 : demarrage a froid valide

`scripts/lua/demarrage.lua` sur `work/dq9_v35.nds`, SaveRAM du joueur, sans
aucun savestate -- le seul test qui exerce l'agrandissement des tas :

```
image  3009  ctx=022A6C28  tas8 : etendue 40912, libre 21564 | c1=147 liste=0
image  4509  ctx=022A6C28  tas8 : etendue 40912, libre 21564 | c1=147 liste=12
```

Le contexte de terrain se cree, le tas agrandi est bien la, le conteneur porte
**147 especes** (la fenetre de 150 tronquee par un rang de depart eleve) et la
liste ses douze. La partie se charge et tourne -- capture finale : le joueur dans
l'eglise de Stormway. C'est precisement le test que v33 avait echoue.

**La rotation, elle, n'est pas exercable en laboratoire** : le compteur reste
fige (55 puis plus rien) parce que le tic d'apparition ne tourne pas quand la
carte porte son quota de symboles, et le robot ne se bat jamais. Le joueur avait
en revanche constate son declenchement sur v32, au bout d'une trentaine de
secondes.

## 58. Les deux fautes de deplacement, et ce que la sauvegarde du joueur a permis

Le joueur a fourni une sauvegarde d'etat **sur une carte a rencontres, a l'arret**
(`work/save_origine/transition_v36.State`). C'est l'etat qui manquait au banc
d'essai : le tic d'apparition y tourne vraiment -- 30 appels par 60 images -- donc
la greffe B et la rotation y sont exercees. Les deux fautes ci-dessous etaient
invisibles sans elle.

### Faute 1 : un litteral lu quatre octets trop loin

```
0x02073ff0  ldr r4, [pc, #0x38]   ->  0x02074030   (premier mot de la rotation)
            le litteral est en        0x0207402C
```

`r4` valait donc `0xE92D41F0`, l'opcode `push` lu comme adresse de table :
exception de donnees a la premiere apparition. Symptome exact rapporte par le
joueur -- *« je sors de la ville, tant que je bouge pas ca va, des que je fais un
pas le jeu freeze »*. En ville aucun monstre n'apparait, d'ou un demarrage a froid
irreprochable. Cause : un deplacement de litteral calcule a la main avec le
nombre de MOTS (17) au lieu du nombre d'INSTRUCTIONS (16).

### Faute 2 : une sortie commune deplacee d'une instruction

En retirant l'ecriture du budget en tete du morceau C, le `pop` de sortie a
recule d'une instruction ; les deux branchements du morceau A visaient encore
l'ancienne place, donc le `movs` qui suit le `pop`. **Sept mots fuyaient sur la
pile a chaque appel du tic**, et sa fonction appelante depilait ensuite une
adresse de retour corrompue.

```
temoin v36 : appels=30 par 60 images, compteur regulier
v37 cassee : appels=1, puis plus jamais -- sans plantage visible
```

### Les deux garde-fous adoptes

1. **Etiquettes dans l'assembleur.** `"nom:"` nomme une adresse, `{@nom}` la
   restitue. Plus un seul index d'instruction compte a la main. Et l'adresse de
   la sortie commune de la rotation, partagee entre deux morceaux, est
   **calculee** en cherchant le `pop` dans la liste des lignes.
2. **Verification du pool de litteraux.** Tout `ldr rX, [pc, #N]` produit doit
   viser un mot du pool de sa propre greffe, sinon la construction echoue. La
   faute 1 aurait ete attrapee a la construction.

### Le portier remplace le budget dans la greffe A2

Mesure sur la sauvegarde du joueur : `liste 12 (6 hors conteneur)`. La greffe A2
tirait dans les 256 especes autorisees, le conteneur n'en porte que 150 : la
moitie de la liste ne pouvait pas obtenir de modele. La greffe interroge
desormais `0x0206F500(carte+0x2F8, espece)` -- la recherche que le prechargeur
emploie lui-meme -- et retire tant que le portier refuse, avec un dernier recours
au bout de 24 essais pour ne jamais rendre une liste vide.

### Resultat mesure, de bout en bout

| | avant rotation | apres |
|---|---|---|
| liste hors conteneur | 6 sur 12 | **0 sur 12** |
| modeles charges | **1** | **9 puis 10** |

Sur quatre rotations consecutives : 10, 3, 10, 10 modeles, soit **8,2 en
moyenne**, une rotation tous les 256 appels du tic -- de 8 s en laboratoire a
25 s en jeu reel, selon la cadence a laquelle la carte reclame des symboles.

Et la cadence se compte bien **en appels du tic, pas en images** : le tic n'est
appele que lorsque la carte manque de symboles. A 1 024, la rotation ne partait
qu'une seule fois par carte -- ce que le joueur avait observe comme *« un seul
monstre qui spawn »*.

## 59. Le gel de v37, et la vraie cause : des enregistrements de conteneur mauvais

Symptome rapporte : *« ca plante plus mais j'ai qu'un seul monstre »* sur v36,
puis sur v37 *« le jeu freeze au bout de 2-3 secondes quand je commence a me
balader »*. La sauvegarde d'etat du joueur, prise a l'arret devant la ville,
reproduit le gel en laboratoire -- et c'est elle qui a tout permis.

### Le gel arrive APRES la rotation

```
bloc  8  montages=1  modeles= 3
bloc  9  pc=FFFF0108   r0=r4=r5=006E6F6D   lr=020D903C
```

`0xFFFF0108` est le vecteur d'exception de la BIOS ARM9 : une abort de donnees.
L'instruction fautive est a `lr - 8`, soit `0x020D9034 ldrh r2, [r5, #6]`, avec
`r5 = 0x006E6F6D` -- les octets « mon  », la queue de « _f.mon ».

### La fausse piste : le tampon du formateur

`0x021A29C0` formate le nom par `sprintf("%s_f.mon")` dans un tampon a `sp+0x54`,
qui n'a que 16 octets avant `sp+0x64` et `sp+0x68`, deux arguments passes juste
apres. J'ai deplace le tampon a `sp+0x6C`, ou la fonction ne semble rien
utiliser. **Le gel a change de place sans disparaitre** : l'abort est passee dans
`0x020CBF98`, avec la meme valeur « mon  ». `sp+0x6C` n'est donc pas libre : la
structure passee par `add r0, sp, #0x64` s'etend au-dela de huit octets. Patch
retire.

### Ce qui a tranche : instrumenter l'appel

Accroche sur `0x021A29C0`, en notant `r2` -- le pointeur du code de modele lu
dans l'enregistrement de conteneur :

```
image 5870  code=022F6744  longueur= 5  "z016a"
bloc 8 : GEL
```

**Un seul appel, avec un code parfaitement valide.** Il n'y a donc jamais eu de
debordement de formateur. Mais un releve des 150 enregistrements du conteneur
donne :

```
longueurs des codes : 15 illisibles | 2 vides | 1 d'un octet | 132 de 5 octets
18 enregistrements fautifs : les 18 PREMIERS (especes 35 a 53)
```

Leur champ `+0x04` pointe **dans le bloc d'enregistrements lui-meme**
(0x022F3C98, alors que le bloc va de 0x022F3050 a 0x022F40B8), tandis que les
champs `+0x00` et `+0x14` pointent, eux, sur un autre tas (0x0232xxxx) -- ils
sont dupliques par un allocateur different (`[carte+0x14]` contre
`[carte+0x10]`). Le mecanisme exact de la corruption reste ouvert ; ce qui
compte, c'est qu'elle **preexiste a nos greffes** : v29 et v34 ne la touchaient
jamais, faute de tirer dans le conteneur.

### Le correctif : la greffe A2 valide le code de modele

`0x0206F500` rend l'enregistrement, pas seulement un booleen. La greffe s'en
sert :

```
ldr  r0, [r0, #4]        le code de modele
ldrb r0, [r0, #5]        son zero terminal
cmp  r0, #0
beq  retenue             code valide : on garde l'espece
```

Tous les codes valides font exactement cinq caracteres (« z061a »), donc un zero
en `+0x05` ; un contenu binaire n'y met un zero qu'une fois sur 256. Quatre
instructions -- exactement ce qu'il restait dans les 128 octets de la greffe.

### Resultat

Cinq tirages differents (decalage d'images 0, 137, 401, 913, 2111), soixante
blocs de trente images chacun :

| decalage | rotations | modeles a la fin | gel |
|---|---|---|---|
| 0 | 3 | 11 | non |
| 137 | 4 | 8 | non |
| 401 | 4 | 10 | non |
| 913 | 5 | 9 | non |
| 2111 | 7 | 10 | non |

Contre un gel systematique avant le correctif, aux trois decalages essayes. Et
le demarrage a froid reste bon : contexte cree, tas a 40 912, conteneur a 147
especes, liste a 12.

## 60. Le gel n'etait pas corrige, et ce qui le cause vraiment

v41 (identique a v40 a la seule cadence pres, 512 au lieu de 256) **gele aux
trois decalages d'images essayes**, avec la signature d'origine :

```
lr=020D903C   r0=r4=r5=006E6F6D   pc=FFFF0108
```

v40 avait donc simplement eu de la chance sur mes cinq tirages. La validation du
code de modele (58) etait necessaire mais pas suffisante.

### La chaine d'isolement, par elimination

| variante | gel |
|---|---|
| v41, rotation complete | **oui**, 3 decalages sur 3 |
| v42, rotation SANS montage force (`mov r0, r0`) | **oui** |
| v41, declencheur neutralise (`movs r7, r0` remis) | non, 2 x 60 blocs |
| v41, vidage de la liste neutralise (`strh` -> `mov r0, r0`) | **non**, 2 x 60 blocs, et le montage part quand meme 2 fois |

**Le coupable est le vidage de la liste de prechargement en pleine partie**
(`strh r0, [carte+0x44+0x18]`), pas le montage -- qui se declenche sans dommage
quand la liste n'est pas videe.

L'abort tombe dans `0x020D9034 ldrh r2, [r5, #6]`, atteinte par
`0x020D95D4 ldr r4, [r4]` : le PREMIER MOT de la structure d'archive du
prechargeur (`sp+0x64`) contient des octets de chaine. Le prechargeur, lui, est
etale sur plusieurs images -- six tours en cinq images, mesure du 57 -- et il
relit le compte de la liste **a chaque tour** (`0x021A2AC8`) alors qu'il a
dimensionne son tableau de fiches (`count * 0xB0`) une fois pour toutes a
l'entree. Faire varier le compte sous ses pieds est donc structurellement
dangereux.

### Ce qu'il faudrait, et pourquoi ce n'est pas fait

Il ne faut jamais laisser le compte redescendre : ecrire les douze especes **par
dessus** les anciennes, en place, sans toucher au compte. Cela demande que la
greffe A2 RENDE l'espece au lieu de la confier a `AddSpecies`, plus une boucle
d'ecriture indexee dans la rotation -- une dizaine d'instructions. Or A2 fait
128 octets sur 128, la rotation 16/16, 18/18 et 48/52 : il reste **un mot**.

Piste pour les liberer : la table des classes n'a plus besoin de deux bits par
espece depuis que le budget est mort (58) -- un seul suffit, ce qui la ramene de
96 a 48 octets et libere douze mots dans la zone.

### Le reglage sur, en attendant

`--sans-rotation` garde tout le reste : tirage au chargement de zone, greffe B
(aucun monstre invisible), conteneurs a 150 especes. Verifie sans gel sur
2 x 60 blocs.

**La greffe C reste indispensable meme sans rotation** : la greffe A2 verifie
l'appartenance au conteneur avant d'ajouter une espece, et sans conteneur large
ce test rejetterait presque tout -- le dernier recours ajouterait alors des
especes non validees, precisement celles dont l'enregistrement est corrompu.

### Et l'idee « une seule espece, reset chaque seconde »

Testee (`--tirages 1 --periode 64`). Elle ne tient pas : la liste ne contient
jamais une seule espece mais **une plus les monstres vivants**, dont les modeles
sont rechargeses a chaque rotation. Mesure sur 40 blocs, contre le reglage a 12
tirages :

| | especes distinctes vues | rechargements |
|---|---|---|
| 12 tirages, cadence 512 | 9 | 1 |
| 1 tirage, cadence 64 | 14 | **9** |

Plus de variete, mais neuf fois plus de saccades -- et le gel etait toujours la.

## 61. La rotation reparee : ecriture EN PLACE, et le bit qui a paye la place

### Le principe

Le gel venait de remettre a zero le compte de la liste de prechargement en
pleine partie (60). La rotation ecrit donc desormais les especes **par dessus**
les anciennes, aux index 0, 1, 2... et **ne touche jamais au compte**. Le
prechargeur, qui relit ce compte a chaque tour alors qu'il a dimensionne son
tableau de fiches a l'entree, ne voit plus rien bouger sous ses pieds.

Consequence agreable : `AddSpecies` n'est plus appele du tout par la rotation --
mesure sur un chargement de zone suivi de deux rotations, **12 appels en tout**,
tous au chargement.

### Ou la place a ete prise

La table des classes portait deux bits par espece pour un budget qui est mort
(58). Un bit suffit : 48 octets au lieu de 96, et le plan de la zone devient

| | |
|---|---|
| `+0x000` | bitmap, 48 o, un bit par espece |
| `+0x030` | greffe A2, 144 o (140 utilises) |
| `+0x0C0` | greffe C, dernier morceau, 32 o |
| `+0x0E0` | rotation, morceau D, 48 o (36 utilises) |
| `+0x110` | compteur de cadence |

### Le mode « rendre » de la greffe A2

Le parseur d'encmons appelle A2 a la place de `AddSpecies` avec r1 =
identifiant lu dans le fichier, toujours inferieur a 512. **Le bit 15 est donc
libre** : mis a 1 (`MODE_RENDRE`), la greffe valide l'espece et la REND
dans r0 au lieu de l'ajouter. La rotation s'en sert pour ecrire elle-meme.

### Deux pieges d'assemblage payes

`strh` n'accepte **pas** d'index decale sur ARM (mode d'adressage 3) :
`strh r1, [r4, sb, lsl #1]` est refuse par l'assembleur, il faut calculer le
deplacement dans un registre. Et le decalage `4 * 0x70` des emplacements
d'acteur a ete verse dans le litteral pour recuperer le mot ainsi perdu.

### ET UN PIEGE DE METHODE, PLUS COUTEUX QUE LES DEUX AUTRES

**Une sauvegarde d'etat prise sur une ROM gele sous une autre ROM, meme de
disposition identique.** `ville_v44.State` charge sur `dq9_v45.nds` gele en
trente images -- avec ou sans patch RAM, et sans qu'aucune greffe ne tourne. Les
deux ROMs ne differaient que par 39 plages, toutes dans l'image ARM9.

J'en ai conclu a tort que v45 plantait. La bonne methode est de charger **la ROM
d'ou vient la sauvegarde** et d'y appliquer le code neuf en RAM. Les tests de
terrain precedents y avaient echappe par chance : leurs sauvegardes etaient
prises en pleine carte, pas en ville.

### Mesures

Huit tirages (decalage d'images 0, 137, 401, 613, 913, 1499, 2111, 3001),
soixante blocs de trente images chacun, sur la sauvegarde de terrain :

| | rotations | modeles a la fin | gel |
|---|---|---|---|
| v45 | 1 a 4 | 8 a 11 | **aucun sur 8 essais** |
| v41 (vidage de la liste) | 1 | -- | gel aux 3 essais |

Et sur la sauvegarde de ville, en franchissant la limite : 12 especes demandees,
**2 hors conteneur, 9 modeles charges**, puis un lot neuf a chaque rotation.
Demarrage a froid : contexte cree, conteneur a 147 especes, aucune exception.

### Ce qui reste imparfait

Quand plusieurs monstres vivants sont de la **meme** espece, elle est reecrite
autant de fois (releve : `188, 188, 90, 188`), ce qui coute deux ou trois
emplacements sur douze. Dedupliquer demanderait de balayer la liste avant chaque
ecriture, soit une huitaine d'instructions -- il en reste douze mots libres dans
le morceau D, donc c'est faisable si le lot parait trop pauvre en jeu.

## 62. Le garde-fou qui manquait : ne rien reecrire tant que la liste est incomplete

Retour de jeu sur v45, trois symptomes : un seul monstre en boucle apres une
teleportation, plus AUCUN monstre apres un aller-retour en ville, et un ecran
noir au changement de zone.

### La mesure, sur une sauvegarde prise en ville

```
image 2518  ROTATION  carte=100  liste=0  c1=150     (treize tours, puis montage)
```

**La rotation tournait en ville.** Et elle y faisait deux betises :

1. Elle ecrivait douze especes alors que **le compte de la liste valait zero** :
   le jeu ne les voyait donc jamais. C'est le revers de l'ecriture en place --
   ne plus toucher au compte veut dire ne plus le CREER.
2. Elle appelait le montage pour rien, et celui-ci **demontait tous les
   modeles**.

Le meme mecanisme frappe pendant un chargement de carte, quand le parseur
d'encmons remplit encore la liste : la rotation reecrit alors une liste a moitie
construite et force un montage au pire moment. D'ou les trois symptomes.

### Le correctif

Trois instructions en tete du morceau D, avant toute ecriture :

```
ldrh r0, [r4, #0x18]        le compte de la liste
cmp  r0, #12
blt  sortie                 incomplete : ne rien toucher
```

Un seul test ecarte les deux cas : le compte vaut zero hors carte a rencontres,
et il monte progressivement pendant le parsage. Consequence assumee : avec
`--especes` inferieur a 12, la liste n'atteint jamais le seuil et la rotation ne
part pas -- c'est le prix d'un test qui tient en trois mots.

Le tirage avance desormais `r4` lui-meme (`strh r0, [r4], #2`) au lieu de
recalculer un deplacement : c'est ce qui a libere la place. La greffe A2 ignore
r0 en mode « rendre » et preserve r4, donc rien ne s'y oppose.

### Mesures

| situation | avant | apres |
|---|---|---|
| en ville | 13 tours de tirage + un montage | **un seul passage, aucun montage** |
| sortie de ville | -- | liste 12, **9 modeles** |
| terrain, 5 tirages x 60 blocs | -- | 1 a 4 rotations, 8 a 11 modeles, **aucun gel** |
| retour en ville | -- | liste 0, compteur qui avance, aucun gel |
| demarrage a froid | -- | contexte cree, conteneur a 147 |

## 63. LE MUR : le montage detruit des tas, et l'arbre des allocateurs ne le supporte pas

### Ce que le joueur a rapporte sur v46

Un seul monstre en boucle -- souvent la meme statue -- un autre monstre unique
apres un aller-retour en ville, et un ecran noir au changement de zone, non
reproductible au redemarrage. « Assez flaky ».

### Premier defaut : la boucle de retroaction sur les doublons

Releve sur sa sauvegarde de terrain :

```
modeles 8 : 177,177,177,177,182,84,144,83
```

**Quatre emplacements sur huit pour la meme espece.** Le mecanisme se boucle sur
lui-meme : la greffe B tire parmi les modeles CHARGES, donc 177 sort une fois sur
deux ; ses acteurs occupent alors les emplacements d'acteur ; la rotation, qui
remet les especes des acteurs vivants, reecrit 177 quatre fois ; et ainsi de
suite jusqu'a l'effondrement sur une seule espece.

Verifie : en sautant le balayage des acteurs (un mot patche en RAM), les modeles
redeviennent tous distincts -- `190,144,276,258,204,126`.

### Second defaut, et c'est un mur

Le gel persiste **meme sans le balayage des acteurs**, et il exige un
franchissement de zone SUIVI d'une rotation : sur la carte de depart, soixante
blocs passent sans rien.

L'abort, enfin nommee :

```
0x020AF114  ldr r0, [r4, #0x18]      r4 = 0xFFFEF638
dans AllocatorTree::GetParent(SignedAllocatorList*, SignedAllocatorHeader*)
```

`ElementAfter` a rendu un noeud a `0xFFFEF638` : **l'arbre global des
allocateurs est corrompu**. Ce n'est pas une fuite -- l'ExpHeap parent garde ses
18 002 octets libres et son unique bloc, mesure a chaque montage.

La cause est structurelle. Le montage `0x021A2FA0` appelle d'abord
`0x021A316C`, qui pour chaque tas du contexte verifie (`0x020328C4`), vide
(`0x02032740`) puis **detruit** (`0x0203248C`) -- et `Destroy` delie le tas de
l'arbre des allocateurs. Le refaire hors du cycle de vie prevu, en particulier a
cheval sur un changement de carte qui detruit et recree ces memes tas, finit par
delier deux fois ou delier un tas deja recree.

J'avais ecrit au 61 que le montage etait « reentrant et sans fuite puisque le jeu
l'appelle depuis sept endroits ». C'est faux : il est reentrant **dans le cycle
de vie d'une carte**, pas a un instant arbitraire.

### Ce qu'il faudrait pour une rotation en cours de partie

Ne plus reutiliser le montage du jeu, mais charger les modeles nous-memes : le
prechargeur (`0x021A28A8`) sans le demontage, ou mieux, la conversion du tas des
modeles en ExpHeap (54, validee a l'octet) pour liberer et recharger modele par
modele. Les deux demandent d'ecrire notre propre sequence de chargement --
`0x0207551C` pour trouver le membre, `0x02075664` pour decompresser,
`0x02036814` pour enregistrer, `0x0200FD48` pour poser la fiche -- soit une
trentaine d'instructions et une gestion d'echec propre. Il reste **cinq mots**
libres dans les bourrages.

### Etat livre

`--sans-rotation` : lot neuf a chaque chargement de zone, tire parmi 150 especes,
aucun monstre invisible (greffe B), aucun doublon (pas de balayage d'acteurs),
aucun gel -- verifie sur les deux sauvegardes du joueur et au demarrage a froid.
C'est le point d'arret raisonnable.

## 64. Les deux defauts que la sauvegarde du joueur a fait tomber

Symptomes rapportes sur la version sans rotation : « plus aucun monstre, ca
marche pas ». La sauvegarde fournie -- juste au sud de la ville, un pas de la
transition -- a permis de rejouer six allers-retours ville / terrain et de
trancher les deux, par comparaison directe.

### La greffe C corrompt les enregistrements du conteneur

`0x0206F240` n'est pas fait pour plus de douze especes. Au coeur de sa boucle :

```
0x0206F3E8  ldrb r1, [r8, r5]        r8 = tableau d'octets, r5 = indice d'espece
0x0206F3F0  bl   0x02032554          Allocate(tas de carte, r1)
```

`r8` vient de `[etat+0x14]`, dimensionne pour la liste de prechargement -- douze
entrees. Avec 150 especes, `r5` monte a 149 : la fonction lit 150 octets dans un
tableau de 12, alloue des tailles arbitraires sur le tas de carte, et ses
duplications de chaines finissent par rendre des pointeurs corrompus. Ce sont les
18 enregistrements fautifs du 59, dont j'avais cherche la cause ailleurs.

Comparaison, meme sauvegarde, six passages :

| | modeles charges | gel |
|---|---|---|
| avec la greffe C | 8, puis 2, puis 7 | **au sixieme passage** |
| sans | 11, puis 10 | aucun |

Elle ne servait qu'a donner de la matiere a la rotation. Retiree, avec
l'agrandissement des tas qui l'accompagnait : le tas parent recupere 147 Kio et
le tas du conteneur revient a 11 344 octets.

**Lecon : ne pas faire avaler a une fonction du jeu dix fois ce qu'elle attend,
meme quand sa borne interne le permet.** Le `cmp r7, #0x200` de `0x0206F324`
autorise 512 especes ; un tableau annexe de douze octets, lui, ne dit rien.

### La greffe B fermait une boucle : le jeu devenait muet

Tirer uniquement parmi les modeles CHARGES supprime les monstres invisibles, mais
rend -1 quand il n'y en a aucun. Le jeu ne demande alors plus de monstre, donc
rien ne declenche de rechargement, donc aucun modele ne revient : **silence
definitif**. Mesure : dix modeles apres un chargement de zone, zero apres une
minute de marche, et plus rien ensuite.

La greffe retombe donc sur la liste de prechargement dans ce cas -- au prix d'un
monstre parfois invisible, ce que le joueur avait juge acceptable sur v29. Elle
fait desormais 116 octets et occupe toute la fonction du tireur, y compris les 64
octets ou logeait le morceau A de la rotation : les deux sont devenus
incompatibles, et `--rotation` refuse de construire.

### Etat livre : `work/dq9_rand.nds`

Nom de fichier STABLE, pour que la sauvegarde de BizHawk suive d'une version a
l'autre -- elle est nommee d'apres le fichier ROM (`NDS/SaveRAM/dq9 rand.SaveRAM`),
et chaque nouveau nom repartait a blanc.

Mesure finale, six allers-retours : 10, 10 puis 8 modeles, **qui restent charges
en marchant**, aucun gel, demarrage a froid propre.

## 65. P3 livre et valide en jeu : le portier universel

Le 8 septembre. Objectif atteint pour la moitie visee : **n'importe quelle espece
du bestiaire apparait a chaque apparition**, le combat est juste, seule
l'apparence du symbole sur la carte est empruntee. Retour du joueur : « le
fonctionnement est bien attendu, sur la carte je vois globalement les memes 5-6
modeles mais des que je rentre en combat j'ai bien un mob aleatoire a chaque
fois ».

Construction : `python randomizer.py "<rom>" --seed 35 --especes 12
--sans-rotation --portier -o work/dq9_p3.nds`. Source : `scripts/patch_portier.py`.

### Les quatre pieces

| piece | ou | taille | role |
|---|---|---|---|
| tireur | `0x02073FEC` | **8 o** | `mov r1,#0x8000 ; b A2` -- reutilise le mode « rendre » de la greffe A2, qui tire deja dans le bitmap des 256 especes |
| portier 1 | zone `+0xC0` | 80 o | recherche d'origine, puis SYNTHETISE l'enregistrement absent |
| portier 2 | `0x020F1E40` | 64 o | idem pour le noeud de la liste chainee du conteneur 2 |
| emprunt | `0x02073FF4` | 72 o | `FindLoadedModel`, puis sur echec un modele charge tire au hasard |

Donnees : enregistrement synthetique en `0x020F1CB8` (0x1C o), noeud en
`0x020E7C78` (0x1C o).

Quatre `bl` rediriges dans l'overlay 17 : `0x021A2164` (portier 1 de
l'apparition), `0x021A2178` et `0x021A22F0` (portier 2 et sa relecture),
`0x021A21F8` (`FindLoadedModel`).

### Trois decisions, et pourquoi

**On patche les SITES D'APPEL, pas les fonctions.** `0x0206F500` a **vingt**
appelants dans tout le jeu (combat, overlays 21E/21F) : la remplacer ferait
rendre un enregistrement synthetique la ou l'appelant attend un zero. Comptage
exhaustif des `bl` de l'ARM9 et des 35 overlays : `chercher1` 20 appelants,
`chercher2` 4, `FindLoadedModel` 4.

**Pas les sites du prechargeur** (`0x021A2988`, `0x021A299C`). Si le portier lui
repondait toujours oui, il chargerait douze fois le modele du gabarit. Il garde
son comportement -- cinq a neuf modeles reels -- et c'est parmi eux que
l'apparition emprunte.

**Un seul enregistrement statique partage, pas un pool.** Quatre champs sont
reellement consommes, tous verifies au desassemblage :

| champ | lecteur | destination |
|---|---|---|
| `+0x04` code de modele | greffe A2 (`ldrb [r0,#5]`) | validation du code |
| `+0x0C` short | `0x021A22C8` -> `0x020377D4` | acteur`+0x64` |
| `+0x0E` short | `0x021A22D8` -> `0x020377C4` | acteur`+0x68` |
| `+0x12` short | `0x021A1FEC` `ldrshne sl,[r0,#0x12]` | **echelle**, 0x1000 par defaut |

Le portier recopie les `0x1C` octets du **premier enregistrement du conteneur de
la zone** -- des valeurs reelles, d'un monstre de cette zone -- et n'ecrase que
l'espece en `+0x08`. Le contenu est donc identique pour toutes les especes
substituees, et deux acteurs vivants peuvent le pointer sans se gener. Un pool
par emplacement d'acteur aurait coute 336 octets, qu'on n'a pas.

L'enregistrement EST relu apres l'apparition (`0x021A1FE0 ldr r0,[sb,#0x180]`),
donc un enregistrement de pile ou recycle a chaque appel ne suffisait pas.

### Ce que le joueur constate, et qui est conforme

- Les memes 5 a 6 modeles sur la carte : le prechargeur n'est pas touche.
- Un monstre different a chaque combat : c'est l'objectif.
- **La hitbox suit l'espece reelle, pas le modele emprunte.** Un gros symbole
  dont l'espece est petite se prend comme un petit. La collision ne vient donc
  pas du modele -- P4 fait disparaitre l'ecart par construction.

### Demarrage a froid : valide

`scripts/lua/demarrage.lua` sur `work/dq9_p3.nds`, SaveRAM du joueur, sans
savestate : partie chargee, `ctx=022A6C28`, tas 8 a 11 344 octets (taille
vanilla, donc aucune trace de la greffe C), 9 000 images stables. C'est le test
que `v33` avait echoue.

## 66. Les mesures de la session, et deux corrections au dossier

### La confiscation du reliquat -- instrumentee au montage

`scripts/lua/montage.lua`, temoins sur les quatre points de `0x021A2FA0` :

```
[1] ville   : tas des modeles = 62 280   libre apres prechargement = 62 228  CONFISQUE 62 228
[2] terrain : tas des modeles = 188 384  libre = 93 892  modeles 5 : 123,84,174,147,129  CONFISQUE 93 892
[4] terrain : tas des modeles = 188 384  libre = 99 308  modeles 5                        CONFISQUE 99 308
[6] terrain : tas des modeles = 188 384  libre = 36 532  modeles 9                        CONFISQUE 36 532
```

La sequence `0x021A30B8`-`0x021A312C` cree le tas des modeles avec **tout** le
libre de `ctx+0x1244`, lance le prechargeur, puis **reprend tout le reliquat**
pour en faire le tas `ctx+0x11C0`. C'est systematique, a chaque montage, et ca
represente **36 a 99 Ko** sur le terrain -- deux a cinq modeles jetes.

Le tas des modeles a donc **0 octet libre par construction**, ce qui interdisait
tout chargement a la demande. Correctif de P4 : borner `r5` en `0x021A310C`.

### `ctx+0x11C0` n'est jamais consomme en jeu

`scripts/lua/tas_confiscation.lua`, echantillonnage image par image : occupation
**0 octet** sur 16 zigzags de marche, sur le terrain comme en ville. Le tas est
cree puis reste vide.

Mais il n'est pas inutile : `0x021C20B4` le passe en `r2` a `0x0202FD0C`, la mise
en file d'une requete de fichier **asynchrone**. C'est le tas des requetes
asynchrones du terrain. Notre chargeur y allouera donc son membre compresse,
comme le jeu le fait.

Piege de mesure paye au passage : lire ces en-tetes **pendant** une transition
rend des valeurs incoherentes (`0x11C0` absent, une « occupation » de 160 080
octets qui etait en fait le libre de `0x113C`). Instrumenter le montage, ne pas
echantillonner en aveugle.

### VRAM de textures : eviction individuelle IMPOSSIBLE

Le jeu installe le gestionnaire **watermark** (`Frm`) :

```
0218ba54  mov r0,#4 ; mov r1,#1 ; bl 0x20bb49c   ; InitFrmTexVramManager(4 slots)
0218ba60  mov r0,#0x4000 ; mov r1,#1 ; bl 0x20bb790 ; InitFrmPlttVramManager(16 Ko)
```

- `NNS_GfdDefaultFuncFreeTexVram` (`0x020F1EEC`) pointe sur `0x020BB708` =
  `mov r0,#0 ; bx lr`. **Un stub vide.** Idem palettes (`0x020BB918`).
- L'allocateur installe (`0x020BB598`) est deux curseurs par region, sans
  structure de suivi des blocs : rien a mettre a jour meme en ecrivant un `free`.
- Ni `BitArray` ni `Lnk` ne sont lies dans le binaire.
- Table de 5 descripteurs de 0x18 o en `0x020F1F14`, total `0x80000` = 512 Ko,
  exactement la VRAM d'image de texture du DS, avec la regle des textures 4x4
  compressees (`kind 0 -> R1`, `kind 3 -> R2`, moitie de la taille).
- Substituer un gestionnaire est un chantier : les 10 sites chauds appellent
  `0x020BB598` par `BL` **direct**, et ~15 sites font du checkpoint/rollback
  (`0x0207DFBC` marque, `0x0207DFA0` restaure), idiome incompatible avec un
  allocateur a blocs libres.

Le seul « free » du jeu est le rollback de watermark, et **le prechargeur
commence par la** (`0x021A2900 bl 0x207dfa0`) : les 12 textures de monstres
vivent dans une seule region liberee tout ou rien. Meme discipline que le `FRMH`
cote RAM.

D'ou la piece a ajouter a P4 : **allocation monotone + rafraichissement en bloc**.
On charge en avancant le curseur ; a saturation, rollback puis re-liaison des
textures des N residents depuis les blobs qu'on garde en RAM. Avec 256 Ko
reserves au terrain et des textures de 8 a 30 Ko, cela fait une saccade **toutes
les 10 a 20 apparitions**, pas une par pop.

### Le chargement d'une espece existe dans l'ARM9 resident

Cas `type == 5` de `0x0203D038`, tout en RAM en permanence :

```
0203d47c  cmp r0, #5
0203d4c0  bl 0x2003ce8    ; sprintf(nom, fmt, r5+4)   <- r5+4 = code de modele
0203d4f0  bl 0x20d91ec    ; ouvre enemy.gp2, tampon 0x30000
0203d53c  bl 0x20d9548    ; extrait le membre (SYNCHRONE)
0203d584  bl 0x207551c    ; sous-chunk .cchr
0203d5b8  bl 0x2075664    ; LZ77 -> tas
0203d5f0  bl 0x2036814    ; enregistre le modele
```

`0x02075664` est bien le decompresseur, contrairement a ce qu'un rapport avait
conclu : `ldr r1,[r5] ; lsr r1,#8 ; str r1,[r2]` (taille), `bl 0x2032554`
(allocation), `blx 0x20006cc` (thunk LZ77 de la BIOS), et **elle rend le
pointeur du blob** -- donc notre table d'eviction se remplit gratuitement.

`0x020D9548` est **synchrone**, pas asynchrone. Le vrai chemin asynchrone est
`0x0202FD3C` / `0x0202FDE0` / `0x0202FED8`, et toute ouverture synchrone
d'archive **purge la file** (`0x021A2908`, `0x0203D4A0`).

### Le spawn reessaie indefiniment, donc l'asynchrone est gratuit

```
02073d3c  bl 0x21a2128     ; l'apparition
02073d40  cmp r0, #0
02073d44  movne r0, #0
02073d48  strne r0, [r7,#8] ; l'accumulateur n'est remis a zero QUE si ca a marche
```

Un echec conserve l'accumulateur et **reessaie a l'image suivante**. Un chargeur
asynchrone n'a donc besoin que d'un mot de verrou d'espece en attente : zero
image bloquee, contre une a deux en synchrone.

### `0x0206F500` est un trampoline

```
0206f500  ldr ip, [pc, #4]   ; -> 0x0206F480  recherche dichotomique generique
0206f504  ldr r2, [pc, #4]   ; -> 0x0206EF50  extracteur de cle : ldrsh r0,[r0,#8]
0206f508  bx  ip
```

Le portier 1 est donc une recherche dichotomique sur le tableau
d'enregistrements, cle = l'espece en `enreg+0x08`.

### CORRECTION : `EU = USA + 0x10` est faux en bas de l'ARM9

Verifie sur 22 246 sites de `bl` : decalage **0x00** de `0x02000814` a
`0x0200F3B4` (808 sites), **+0x10** de `0x0200FD24` a `0x020E6918` (21 427
sites). Les 0x10 octets supplementaires de l'EU sont inseres **dans** la version
EU de `func_0200F3A4`. Les ~200 premieres entrees de
`work/communaute/symboles_eu.txt` sont donc fausses de 0x10 (thunks BIOS, libc).
L'overlay 17 est bien identique.

### CORRECTION : le 43 est faux, et les « textures 120-139 » n'existent pas

- `fiche+0x08` est un objet de rendu de 0xAC o, `fiche+0x0C` un objet de config
  de 0x2C : les liberer rend 216 octets sur 18 500. **Le pointeur du blob n'est
  nulle part dans la fiche** -- c'est notre chargeur qui doit le memoriser,
  puisque c'est lui qui appelle `0x02075664`.
- `0x02057F10` n'est pas un gestionnaire de textures : il balaie 16 entrees de
  pas 0xD4, compare `[entree+0xD0]` a une etiquette et fait
  `ClearSlot(0xD0 + i)`. Ce sont **16 instances d'objets 3D** (effets), dans les
  emplacements 208-223 de la table globale. Allocateur `0x02057FE8`, liberation
  par indice `0x02057DC8`, acces par indice `0x02058668`. Rien a voir avec les
  modeles de monstres.

### Le banc `dq9_banc.nds` est mort cote monstres -- ne pas s'y fier

`scripts/lua/diag.lua` sur `rand.State` : le tic tourne (`tic=1200`), le tireur
est appele 877 fois en 40 blocs, mais **le spawn `0x021A2128` n'est jamais
atteint**, zero modele charge, douze emplacements d'acteur a -1. Et `c1=150` :
c'est un vieux build **a greffe C**, celle qui corrompt les enregistrements. Tout
zero mesure sur ce banc est un artefact. Banc valide : `work/dq9_p3.nds` +
`work/save_origine/terrain_p3.State`.

Lecon de methode : mettre un temoin sur une fonction **qu'on sait appelee** avant
de croire un zero. Ici `getCurrentFieldStructure` (`0x02027CC0`) restait a zero
elle aussi -- elle n'est simplement pas appelee sur ce chemin -- alors que le tic
et le tireur comptaient normalement.

## 67. P4 etape 1 : la place existe enfin, et l'enigme du 57 tombe

Le 9 septembre. `scripts/patch_place.py`, option `--place`. Trois talons de
quatre a huit octets, tous dans le morceau C de l'ancienne rotation
(`0x020F1D2C`, 52 octets valides par canari). Tout est mesure au temoin de
montage (`scripts/lua/montage.lua`, six montages par essai).

| talon | ou | quoi |
|---|---|---|
| ExpHeap | `0x021A30E0` -> `mov r3,#4 ; b 0x02032498` | le tas des modeles devient un ExpHeap |
| borne | `0x021A310C` -> `min(r0, 0x4000)` | la confiscation ne prend plus que 16 Ko |
| plafond | `0x021A2ACC` -> `min([liste+0x18], N)` | le prechargeur ne fait que N tours |

### L'ExpHeap ne fait pas que permettre l'eviction : il DEBLOQUE le prechargeur

Mesure comparative, meme banc, meme savestate, trois sorties de ville :

| | modeles charges | libre apres prechargement |
|---|---|---|
| frame heap (vanilla) | **5, 5, 9** | 93 892 / 99 308 / 36 532 |
| ExpHeap, sans plafond | **11, 10, 8** | 7 608 / 2 072 / 8 |

La borne agit APRES le prechargement : elle ne peut pas etre la cause. C'est donc
la conversion en ExpHeap qui double le nombre de modeles charges -- sur le frame
heap, des allocations du prechargeur echouaient et il abandonnait des especes.

**C'est l'enigme du 57 qui tombe** : « quatre modeles seulement, avec 124 Kio de
tas encore libres -- le plafond n'est pas la memoire ». Il n'etait pas la memoire
en effet : c'etait le type d'allocateur.

Consequence pratique immediate : `--place` sans plafond ameliore deja P3, deux
fois plus de modeles sur la carte donc des apparences empruntees bien plus
variees. C'est `work/dq9_p3b.nds`.

### Mais sans plafond il ne reste rien : la place vient du plafond

Le prechargeur remplit alors le tas a huit octets pres, et la borne de la
confiscation ne sert plus a rien -- elle ne fait que REDUIRE, elle ne garantit
aucun plancher. D'ou le troisieme talon. Avec `--plafond 5` :

```
[2] terrain : modeles 5 : 120,237,142,17,107   libre 104 284  CONFISCATION 16 384
[4] terrain : modeles 5 : 16,27,115,149,2      libre 108 416  CONFISCATION 16 384
[6] terrain : modeles 5 : 328,140,247,214,265  libre  66 124  CONFISCATION 16 384
```

et le tas des modeles conserve, liste des blocs libres parcourue :

```
terrain : libre 87 884 / 92 016 / 49 724   en 1 SEUL bloc, plus gros = tout
ville   : libre 45 788                     en 1 seul bloc
```

104 284 - 16 384 = 87 900, a 16 octets d'en-tete de bloc pres. **Trois a cinq
modeles de streaming par-dessus les cinq residents, d'un seul tenant.** Aucune
fragmentation au depart, et le plus gros modele du bestiaire (61 368 o) rentre
dans deux cas sur trois.

### Le plafond n'est PAS le gel du 60

Le gel du 60 venait de MODIFIER le compte de la liste en memoire pendant que le
prechargeur iterait, alors qu'il avait dimensionne son tableau de fiches une
fois pour toutes a l'entree (`count * 0xB0` en `0x021A28EC`). Ici on ne touche
pas la liste : on borne seulement la valeur rendue au test de boucle
`0x021A2AD0 cmp sb, r0`. Le tableau reste dimensionne au vrai compte, on en
utilise moins. Six montages, aucun gel, demarrage a froid propre.

### Lire le libre d'un tas : la formule depend du type

Piege paye ici. Sur un frame heap le libre est `[h+0x28] - [h+0x24]` (queue moins
tete). Sur un ExpHeap, `+0x24` est la **tete d'une liste de blocs libres**, et la
meme formule rend un zero trompeur. En-tete de bloc NNS ExpHeap : taille en
`+0x04`, suivant en `+0x0C`. `scripts/lua/montage.lua` parcourt desormais la
liste et rend le total, le nombre de blocs et le plus gros -- c'est-a-dire la
mesure de fragmentation, gratuite.

### Ce qui reste pour P4

1. **Le chargeur**, transcrit du cas `type == 5` de `0x0203D038`, accroche a
   `0x021A2154` (rendre 0 avant la creation de l'acteur) plutot qu'a
   `0x021A21F8`, pour que la boucle de reessai de `0x02073D40` refasse le tour
   proprement. En asynchrone : `0x0202FD3C` met en file, `0x0202FDE0` sonde,
   `0x0202FED8` recupere. Un mot de verrou d'espece en attente.
2. **L'eviction** : table de 12 mots de pointeurs de blob (que `0x02075664` rend),
   predicat d'acteur vivant du 50, `HeapFree` sur les trois blocs. Allouer par la
   queue (`SafeAllocator::AllocateReversed`, `0x02032594`) pour isoler le
   va-et-vient des residents.
3. **La table espece -> code de modele**, injectee : le contexte `mon_data` n'a
   pas ete retrouve (`0x02108D18` est vide en permanence, ce n'est pas lui), et
   on a la correspondance hors ligne dans `work/tailles_modeles.txt`.
4. **Le rafraichissement VRAM en bloc** : la VRAM de textures est un watermark
   dont le `free` est un stub vide (66). Allouer en avancant le curseur, puis a
   saturation `0x0207DFA0` (rollback) suivi d'une re-liaison des textures des
   residents depuis les blobs gardes. Une saccade toutes les 10 a 20 apparitions.

### La savestate de reference, et sa limite

`work/save_origine/terrain_p3.State` (appariee a `work/dq9_p3.nds`) est **au
centre de la zone 20002** : aucune limite de zone atteignable en 15 s de marche
dans les quatre directions (`scripts/lua/reperage.lua`). Elle sert donc a
observer les apparitions, pas les montages. Pour les montages, seul
`rand.State` + `dq9_banc.nds` franchit -- et c'est legitime, le montage ne depend
pas du sous-systeme de monstres, mort sur ce banc.

## 68. LA TABLE SOURCE : le jeu sait la batir, sur le tas qu'on veut

C'est la piece qui fait basculer P4, et elle etait dans le jeu depuis le debut.

### Le probleme qu'elle resout

Le prechargeur prend le code de modele dans l'enregistrement du conteneur 1 :

```
021a29b4  ldr r2, [r0, #4]     ; r0 = l'enregistrement, +0x04 = le code (chaine)
021a29c0  bl  0x2003ce8        ; sprintf("%s_f.mon", ce code)
```

Donc pour charger le modele d'une espece arbitraire, il suffit que l'enregistrement
porte le BON code. La version precedente du portier recopiait le premier
enregistrement de la zone et n'ecrasait que l'espece : code faux, echelle fausse.
D'ou la hitbox qui ne correspondait pas au symbole -- defaut rapporte par le
joueur sur `dq9_p3.nds`.

Il fallait donc la correspondance espece -> code pour les 438 monstres. Trois
pistes ont ete essayees avant la bonne :

- **`0x02108D18`** (rendu par le getter `0x0206F514`) : vide en permanence, ce
  n'est pas le contexte `mon_data`. Mesure faite.
- **Retenir le blob** en neutralisant les deux relachements (`0x021B5314`,
  `0x021B540C` -> `mov r0, r0`) : ne casse rien, verifie en jeu -- mais on ne
  savait toujours pas ou la table vivait.
- **Le tampon de 0x30000** (`0x0211E33C`) : la capture des arguments du
  constructeur `0x0206F240` y a montre `{compte = 438, bloc}` juste apres le
  montage... puis n'importe quoi ensuite. C'est le SCRATCH PARTAGE de l'archive,
  ecrase des la lecture suivante. Ce n'est pas une table persistante.

### La fonction, et sa signature

```
0206efe8  push {r3, r4, r5, lr}
0206efec  mov r5, r0            ; le contexte a remplir
0206eff0  mov r4, r1            ; LE TAS
0206eff4  bl 0x202f7d8          ; suspend l'asynchrone
0206eff8  ldr r0, [pc, #0x24]   ; "data/prm/mon_data.gp2"
0206effc  ldr r1, [pc, #0x24]   ; le membre
0206f000  add r2, sp, #0
0206f004  bl 0x207569c          ; lit le fichier -> blob, taille en [sp]
0206f008  mov r2, r0
0206f00c  ldr r3, [sp]
0206f018  bl 0x206f02c          ; batit {compte, bloc} SUR LE TAS r4
0206f01c  bl 0x202f7f8          ; reprend l'asynchrone
```

**`0x0206EFE8(contexte, tas)`** -- deux arguments, et le contexte produit est au
format que la recherche generique du jeu comprend deja. `0x0206F108` le confirme :

```
0206f108  ldr r1, [r0]
0206f10c  mov r0, #0x1c
0206f110  lsl r1, r1, #0x14
0206f114  lsr r1, r1, #0x14     ; le compte tient sur DOUZE bits
0206f118  mul r0, r1, r0        ; taille = 0x1C * compte
```

Donc : **pas 0x1C, compte sur 12 bits du mot 0, bloc en +0x04** -- exactement le
conteneur de la carte. `0x0206F480(ctx, espece, 0x0206EF50)` marche dessus tel
quel.

Piege de lecture paye ici : `lsl #20 ; lsr #20` garde les douze bits BAS, pas les
vingt. Avec un masque de 20 bits on lit 328 118 au lieu de 438.

### Mesure en jeu

`scripts/lua/p4.lua`, deux allers-retours ville / terrain, patch injecte en RAM :

```
avant tout montage  SRC=[00000000 00000000] compte=0
terrain 1           SRC=[822501B6 0237E9C4] compte=438
      [  0] espece=1    code=z000a  echelle=4096
      [  1] espece=2    code=z000b  echelle=4096
      [ 50] espece=51   code=z058a  echelle=5406
      [200] espece=217  code=z034a  echelle=13926
      [437] espece=900  code=z060c  echelle=4915
      modeles charges=5 : 120,237,142,17,107
```

Especes croissantes, vrais codes, vraies echelles -- 4096 = 0x1000 = 1.0, et
13926 = 3.4x pour l'espece 217, le geant, dont le code `z034a` figure bien dans
la liste des modeles lourds du 37. La table est rebatie a chaque montage (adresse
differente en ville et sur le terrain), le jeu tourne, et les cinq modeles se
chargent malgre les ~12 Ko qu'elle coute (438 x 0x1C).

### Le talon

`talon_source`, 44 octets, remplace `0x021A30FC bl 0x021A28A8` dans le montage :

```
push {r0, lr}
ldr r0, [pc, #L0]      ; SRC
mov r2, #0
str r2, [r0]           ; invalider : le tas vient d'etre recree
ldr r1, [sp]           ; le contexte de terrain
add r1, r1, #0x1100
add r1, r1, #0x3c      ; r1 = ctx + 0x113C  (0x113C n'est pas encodable)
bl 0x0206efe8
pop {r0, lr}
b  0x021a28a8          ; puis le prechargeur, comme prevu
```

C'est le seul point du cycle de vie ou l'on tient a la fois un tas neuf et le
contexte. Et comme le tas est recree a chaque montage, la table doit l'etre
aussi.

### Ce que le portier devient

Il MAIGRIT : 52 octets au lieu de 80, et il dit la verite au lieu d'approcher.

```
push {r4, lr}
mov r4, r1
ldr r2, [pc, #L0]      ; l'extracteur de cle
bl 0x0206f480          ; le conteneur de la carte
cmp r0, #0
popne {r4, pc}
ldr r0, [pc, #L1]      ; SRC
mov r1, r4
ldr r2, [pc, #L0]
bl 0x0206f480          ; la table source des 438
pop {r4, pc}
```

Plus de synthese, plus d'enregistrement statique partage, plus de pool. Si la
table n'a pas pu etre batie, `SRC` vaut {0, 0} et la recherche rend 0 sans
deborder (`ldr r5,[r0,#4]` puis `cmp r5,#0`).

### Ce qui reste, et c'est peu

Le prechargeur a desormais tout : on lui demande une espece, il trouve son
enregistrement par le portier, il en lit le vrai code, il construit
`<code>_f.mon` et il charge. Il ne manque que le mode « une seule espece dans un
seul emplacement » -- les sept points de greffe du 36, dont deux sont a revoir a
la lumiere du 66 : ne pas vider les emplacements, et surtout NE PAS faire le
rollback du watermark VRAM (`0x021A2900 bl 0x207dfa0`), qui jetterait les
textures des autres modeles.

## 69. LA PLACE DE CODE : inventaire, et la reserve pour plus tard

A lire avant tout nouveau chantier qui demande du code dans l'ARM9. Ce sujet a
coute plus de temps que n'importe quelle autre contrainte du projet.

### La regle qui evite le probleme : donnees ou code ?

| ce qu'on veut | ou ca se fait | place de code |
|---|---|---|
| quelles especes dans quelle zone | fichiers `encfld`/`encmons`/`encbtl` | **zero** |
| statistiques des monstres | `mon_btldata.nat` | **zero** |
| objets, equipements, sorts, competences | `itemdt.gp2`, `spelltable.bin`, `skilltable.bin` | **zero** |
| combats scriptes | `eventbattle.bin` | **zero** |
| **une espece differente a CHAQUE apparition** | code | ~600 octets |
| **un butin different a chaque mise a mort** | code | idem |
| **une boutique qui se reapprovisionne au hasard** | code | idem |

Autrement dit : tout ce qui se decide **une fois, a la generation de la ROM**
est du travail de donnees et ne consomme rien. Tout ce qui doit se decider **en
jeu, a chaque fois** demande une greffe. Un randomizer d'objets classique est
donc entierement du cote donnees ; seul un alea PAR EVENEMENT retombe sur le mur
de la place.

### Inventaire mesure, au 9 septembre

Balayage des plages a zero de l'ARM9 decompresse (1 000 984 octets) : **1 119
octets en 27 regions**, dont la zone de 280 octets. L'overlay 17 n'en offre
**aucune** -- ses deux « trous » de 48 octets a `0x021D622C` et `0x021D6298` sont
des enregistrements de 0x34 presque vides dans une table que le jeu lit.

Occupation au 9 septembre (P3 + P4 etape 1) :

| region | taille | contenu |
|---|---|---|
| `0x020E7268` zone, `+0x00` | 48 | bitmap des especes autorisees |
| zone `+0x30` | 140 | greffe A2 (tirage dans le bitmap) |
| zone `+0xC0` | 52 / 88 | portier 1 -- **36 libres** |
| `0x02073FEC` | 8 / 132 | tireur (2 instructions) |
| `0x02073FF4` | 72 | emprunt de modele |
| `0x0207403C` | 44 / 52 | talon de la table source -- **8 libres** |
| `0x020F1E40` | 64 / 72 | portier 2 -- **8 libres** |
| `0x020F1D2C` | 48 / 52 | talons ExpHeap, borne, plafond -- **4 libres** |
| `0x020F1CB8` | 8 / 40 | `SRC` (contexte de la table source) -- **32 libres** |
| `0x020E7C78` | 28 / 40 | noeud synthetique du conteneur 2 -- **12 libres** |
| `0x020E8888` | 0 / 40 | **libre** |

Reste, tous fragments confondus : environ **600 octets en une vingtaine de
morceaux de 24 a 40 octets**. Les autres plages, non encore utilisees et **non
validees par canari** : `0x020E70FE` (34), `0x020E7129` (27), `0x020E7182` (30),
`0x020E71A8`/`C7`/`E8`/`0x020E7208`/`28`/`48` (24-25 chacune), `0x020E7C0A` (26),
`0x020E7C2E` (34), `0x020E7DA4` (25), `0x020E9449` (26), `0x020F0320` (32),
`0x020F03A1`/`C1`/`E1` (31 chacune), `0x020F0405` (29), `0x020F1DA6` (26),
`0x020F1DEE` (26), `0x020F2E3C` (37).

**Toute region non listee au 57 doit etre validee par canari avant d'y mettre du
code** (`scripts/lua/canari.lua` : motif ecrit en RAM, relu apres avoir joue et
franchi deux zones).

### Consequence pratique : le decoupage

`assembler()` produit un bloc contigu. Une fonction de plus de 40 octets doit
donc etre decoupee en morceaux relies par des branchements, comme l'ancienne
rotation le faisait (morceaux A, B, C). C'est faisable et le mecanisme
d'etiquettes le supporte, mais **chaque decoupe est une occasion de se tromper
d'une instruction** -- les deux pannes les plus couteuses du projet viennent de
la (58, 61). Regle : jamais d'adresse de branchement ecrite a la main, toujours
`{@etiquette}`.

### LA RESERVE : le bootstrap BSS, jamais fait

`static_bss_start = 0x020F2E60`, `static_bss_end = 0x021536E0` -- **395 Kio**.
Lu dans ModuleParams (`0x02000BA0`), verifie :

```
autoload_list_start   +0x00 = 020F4600
autoload_list_end     +0x04 = 020F4618
autoload_start        +0x08 = 020F2E60
static_bss_start      +0x0C = 020F2E60
static_bss_end        +0x10 = 021536E0
compressed_static_end +0x14 = 0209BD08
```

Liste d'autoload, deux entrees : `{dest=0x01FF8000, taille=5952, bss=23360}`
(ITCM) et `{dest=0x027E0000, taille=96, bss=32}` (DTCM). L'image de l'ARM9 va de
`0x02000000` a `0x020F4618` ; sa queue, de `0x020F2E60` a `0x020F4618`, porte les
donnees d'autoload puis la liste. crt0 recopie ces blocs vers ITCM/DTCM, **puis
met a zero `0x020F2E60`-`0x021536E0`**.

Donc trois voies fermees, une ouverte :

- **Agrandir l'image et y mettre du code** : les octets ajoutes tombent dans la
  plage mise a zero. Ferme.
- **Deplacer `static_bss_start`** pour proteger notre code : les variables BSS du
  jeu placees la par l'editeur de liens ne seraient plus initialisees. Ferme.
- **Agrandir un bloc d'autoload** (ITCM) : deplace le debut de son BSS, donc
  fait chevaucher nos donnees et les variables ITCM du jeu, adressees en absolu.
  Ferme.
- **RECOPIER A L'EXECUTION.** La mise a zero n'a lieu qu'**une fois, au
  demarrage**. Un blob place dans un fichier NitroFS, lu au chargement de carte
  dans une allocation du tas, puis execute, survit sans probleme. Ouverte.

Recette du bootstrap, pour le jour ou il faudra plus de 600 octets :

1. Ajouter un fichier a la ROM avec `ndspy` (le blob de code, assemble en
   position-independant : branchements relatifs, donnees via un registre de
   base).
2. Le lire avec **`0x0207569C(chemin, membre, &taille)`** -- deja utilise par le
   jeu, cf. 68 -- ou avec le chargeur NitroFS generique dont l'adresse EU est
   dans `]0x020750A0 ; 0x02075258[` (`candidate_loadNitroFsFileToBuffer` cote
   dqix-functions).
3. L'allouer sur un tas qui vit assez longtemps. Le tas des modeles
   (`ctx+0x113C`) est recree a chaque montage : il conviendrait pour du code
   utilise seulement sur le terrain, et il a 50 a 92 Ko libres depuis patch_place.
4. **Invalider le cache d'instructions** avant de brancher dedans : l'ARM9 a des
   caches separes. `ClearDataCacheByAddr` et `ClearInstructionCacheByAddr` sont
   dans le bloc `0x020C82B8`+ (noms de dqix-functions, adresses EU derivees par
   alignement -- **a verifier avant usage**).
5. Garder le pointeur du blob dans un mot statique, et brancher dessus depuis un
   talon de trois instructions place dans le bourrage existant.

Cout estime : une a deux sessions, dont l'essentiel en verification. Gain :
la place de code cesse d'etre une contrainte pour tout le reste du projet.

**Quand le faire** : si un chantier demande un alea PAR EVENEMENT (butin
different a chaque mise a mort, boutique qui se reapprovisionne, apparence tiree
a chaque rencontre). Pas pour un randomizer d'objets, d'equipements ou de sorts
classique -- celui-la est integralement du cote donnees.

### Le code mort, et pourquoi il reste une mauvaise piste

Le 32 avait releve 13,5 Ko de fonctions « jamais appelees ni referencees ». Le 33
a montre que le critere ne tient pas : il ne couvre ni les references formees par
`add rX, pc, #imm`, ni les tables construites a l'execution. A n'utiliser
qu'apres une validation par execution surveillee (`event.onmemoryexecute` sur la
fonction candidate pendant une longue partie), pas par simple canari -- un canari
prouve que la region n'est pas ECRITE, pas qu'elle n'est pas EXECUTEE.

## 70. P4 etape 2 : le chargement a la demande, par le prechargeur lui-meme

`scripts/patch_chargeur.py`, option `--chargeur` (implique `--portier --place`).
204 octets en huit morceaux, cinq sites detournes dans le prechargeur.

### L'idee : ne pas ecrire de chargeur

Le prechargeur `0x021A28A8` fait deja toute la sequence -- ouvrir `enemy.gp2`,
extraire le membre, trouver le sous-chunk `.cchr`, decompresser sur le tas,
enregistrer le modele, poser la fiche. On le transforme en « charge UNE espece
dans UN emplacement ».

Ce qui rend cela possible et ne l'etait pas avant le 68 : il prend le code de
modele dans l'enregistrement du conteneur 1 (`0x021A29B4 ldr r2, [r0, #4]`), et
le portier rend desormais l'enregistrement REEL de n'importe laquelle des 438
especes. Lui demander l'espece X suffit donc.

### Trois mots plutot qu'un test partout

`DEMANDE` (0 = normal, espece+1 = chargement unique), `DEPART` et `BORNE`
(l'index de depart et la borne de la boucle). Le prechargeur les lit betement ;
c'est la greffe A, qui tourne en tete dans les deux modes, qui remet `DEPART` a 0
et `BORNE` au plafond en mode normal.

Cette indirection fait tomber deux greffes de douze instructions a quatre, et
supprime le talon de plafond de `patch_place` -- son role devient la valeur
initiale de `BORNE`.

| # | site | en mode DEMANDE |
|---|---|---|
| A | `0x021A28CC` `bl 0x021A27E8` | ne pas vider les emplacements ; sinon init DEPART/BORNE |
| B | `0x021A28E0` `bl 0x0209C0FC` | rendre 1 : une seule fiche a dimensionner |
| C | `0x021A2900` `bl 0x0207DFA0` | **ne pas faire le rollback du watermark VRAM** |
| D | `0x021A295C` `mov sb, #0`    | `sb = DEPART` |
| F | `0x021A2ACC` `bl 0x0209C0FC` | rendre `BORNE` |

La greffe C est la plus importante : sans elle, chaque chargement unique
jetterait les textures de tous les autres modeles (66). La greffe B borne une
fuite : 0xB0 octets par chargement au lieu de douze fois plus, et elle meurt avec
le tas au changement de zone.

### LE DECLENCHEUR VA DANS `emprunt`, PAS DANS LE PORTIER -- deux regressions payees

Premier essai : le declencheur dans le portier 1, avec un garde « suis-je deja en
chargement ». Resultat mesure : **zero modele charge sur six montages**.

Cause : le prechargeur consulte ce meme portier (`0x021A2988`), et des qu'une
espece de sa liste manquait au conteneur de la carte -- ce que le 57 avait deja
mesure -- le portier declenchait un chargement **depuis l'interieur de la boucle
du prechargeur**. Celui-ci se rappelait lui-meme, ecrasait `DEPART`/`BORNE`, et
repartait sur un etat incoherent. Le garde empechait la recursion infinie, pas la
premiere reentree.

Le declencheur vit donc dans `emprunt`, au site `0x021A21F8` : cette fonction ne
tourne que dans le chemin d'apparition, jamais dans le prechargeur, et son role
est deja exactement « le modele manque ». Le portier redevient sa version simple
de 52 octets, partageable par les deux sites sans risque.

`emprunt` a trois etages : la fonction d'origine, puis le chargement a la
demande, puis l'emprunt en repli. Il fait 104 octets en trois morceaux
(`0x02073FF4` 32, `0x020E735C` 32, `0x02074014` 40).

Economie qui a fait tenir le tout : **`0x021A2738` IGNORE son premier argument**
(`movs r6, r1` puis `bl 0x200f398` pour aller chercher la table lui-meme), donc
inutile de preserver r0 -- deux instructions de moins.

### LE PIEGE QUI A COUTE LES DEUX REGRESSIONS : la taille du contexte source

Second essai : le montage du terrain ne se terminait plus. Le releve des mots de
commande a tout dit :

```
MOTS = [37357140  2  3]      <- DEMANDE = 0x02392FD4, un POINTEUR
```

`0x0206F02C` alloue un **second bloc** -- les chaines -- et le range en `+0x08`
(`0206f098 str r0, [r8, #8]`). Le contexte de la table source fait donc au moins
douze octets, pas huit. Avec les mots de commande a `SRC+8`, le jeu ecrasait
`DEMANDE` avec ce pointeur a chaque montage : le prechargeur se croyait en mode
demande en permanence, sautait son initialisation et le vidage des emplacements,
et bouclait sur des `DEPART`/`BORNE` aleatoires.

**Une seule cause pour les deux symptomes** -- zero modele, puis montage
apparemment sans fin. `SRC` reserve desormais SEIZE octets et les mots suivent en
`GREFFE_C + 16`.

Regle a retenir : avant de placer des donnees derriere une structure du jeu, lire
la fonction qui la remplit jusqu'a son dernier `str`.

### Etat apres correctif, mesure

```
[1] ville   : libre apres prechargement 41 108  modeles 0  CONFISCATION 16 384
[2] terrain : libre 83 204  modeles 5 : 120,237,142,17,107  CONFISCATION 16 384
```

188 384 - 83 204 = 105 180 consommes, soit la table source (~21 Ko) et cinq
modeles (~84 Ko). Il reste **~66 Ko** au tas des modeles apres confiscation :
trois a quatre chargements a la demande de front.

### Ce qui reste, et ne se mesure qu'en jouant

Le declencheur ne part qu'a une apparition, et le harnais ne sait pas en
provoquer : la carte garde son quota de symboles et le robot ne se bat jamais
(REPRISE.md 6, piege 3). Vider les emplacements d'acteur depuis Lua ne suffit
pas -- le jeu compte ses symboles ailleurs, mesure faite.

Ce qu'il faut observer en jeu :

1. **L'apparence est-elle juste ?** C'est l'objectif. Elle doit l'etre pour toute
   espece dont le chargement reussit.
2. **La saccade.** Un chargement synchrone coute une a deux images (66). A
   surveiller au moment ou un symbole apparait.
3. **La saturation de la VRAM de textures.** C'est le point faible connu : le
   watermark s'alloue sans jamais se liberer, donc apres dix a vingt chargements
   le curseur sature, l'allocation echoue et les modeles se chargent sans
   texture. Symptome attendu : des symboles noirs ou blancs. Le correctif est le
   **rafraichissement en bloc** -- appeler le prechargeur en mode NORMAL, ce qui
   fait le rollback et recharge les residents. Il n'est pas encore ecrit, parce
   qu'il faut d'abord savoir si le probleme se manifeste vraiment.

## 71. Le chargement a la demande fonctionne -- et les quatre defauts qui ont suivi

Premiere preuve mesuree, `scripts/lua/chargeur.lua` sur
`work/save_origine/sortie_p5.State` (la savestate du joueur, juste hors de la
ville -- **le premier banc ou les apparitions tournent vraiment**, la carte y
etant fraichement peuplee) :

```
depart   : modeles 172,260,208,224,241
zigzag 1 : modeles 172,182,85,224,241     <- 260 -> 182 et 208 -> 85
```

Deux emplacements ont change d'espece **en cours de marche, sans aucun montage**.
Le mecanisme est donc bon. Restent quatre defauts, tous trouves par la mesure et
trois d'entre eux par un retour du joueur.

### Defaut 1 : la greffe E perdue -- le chargeur ne chargeait rien d'utile

`spawn=4 decl1=4 prech=4` mais les emplacements ne changeaient jamais. La greffe
sur `0x021A2974` (`bl GetSpecies`) existait dans la premiere version du module et
avait disparu dans la reecriture autour des trois mots. Le prechargeur chargeait
donc `GetSpecies(liste, DEPART)` -- une espece de la zone deja chargee -- au lieu
de celle qu'on venait de tirer.

**Lecon** : quand on reecrit un module, comparer la liste des sites detournes
avant et apres. Une greffe manquante ne se voit ni a l'assemblage ni au
demarrage.

### Defaut 2 : un tableau dimensionne par une valeur, indexe par une autre

Le prechargeur appelle `0x0209C0FC` a DEUX endroits : `0x021A28E0` pour
dimensionner son tableau de fiches (`compte * 0xB0`) et `0x021A2ACC` pour borner
sa boucle. Si les deux valeurs divergent, la boucle ecrit hors du tableau.

- Une version bornait la boucle a 5 sans regarder le compte reel : **en ville la
  liste est vide**, donc `Allocate(tas, 0)` puis cinq fiches de 0xB0 ecrites
  dedans -- 880 octets debordes. Symptome : textures cassees et decor qui bouge.
- Une autre annoncait un compte de 1 en mode demande alors que l'index vaut
  `DEPART`, jusqu'a 7 : 1 232 octets debordes, donc plantage a la premiere
  apparition hors de la ville.

**Correctif** : les deux sites vont sur la MEME fonction, qui rend
`min(compte reel, BORNE)`. La divergence devient impossible par construction.

### Defaut 3 : j'affamais le tas des requetes asynchrones

`talon_source` batit la table des 438 especes (~21 Ko) et `talon_borne` ne laisse
que 16 Ko a `ctx+0x11C0` -- **le tas des requetes de fichiers asynchrones**
(`0x021C20B4` le passe en r2 a `0x0202FD0C`). Sur une carte qui charge beaucoup
par ce chemin, PNJ, boutiques et decors n'arrivent plus : **textures etirees**.

Premiere tentative de correctif : ne rien prendre quand le tas des modeles est
petit, seuil 0x18000, sur l'idee « une carte interieure a un petit tas ».
**Faux, et mesure** :

| carte | tas des modeles |
|---|---|
| ville (100) | 62 280 |
| **eglise (109)** | **171 424** |
| terrain (20002) | 188 384 |

L'eglise passait donc pour du terrain. Seuil porte a **0x2C000** (180 224), entre
l'eglise et le terrain.

### Defaut 4 : deux decisions, deux criteres -- et le second etait gratuit

Avec un seuil unique compare au libre RESTANT, la borne ne se declenchait plus du
tout : sur le terrain le libre apres prechargement tombe a ~77 Ko, sous n'importe
quel seuil qui exclut l'eglise.

Il fallait deux criteres, et le second existait sans rien coder :
**`SRC[0] != 0` est exactement le drapeau « cette carte a des monstres »**,
puisque c'est `talon_source` qui decide de batir la table. `talon_source` decide
donc AVANT le prechargement sur la taille du tas ; `talon_borne` agit APRES et
lit seulement si une table a ete batie.

### Ce qui reste, et pourquoi ca ne rentre pas

**L'eviction.** On ne libere jamais le modele qu'on remplace : la rotation
reutilise l'EMPLACEMENT, pas la memoire. Chaque chargement consomme donc ~18 Ko
definitivement. Mesure : `greffeA=9` mais `greffeC=6` -- sur trois appels le
prechargeur abandonne entre les deux, et il n'y a la qu'un
`Allocate(tas, compte * 0xB0)` suivi de `beq`. Le tas est plein. D'ou **deux a
trois bonnes apparences par zone, puis retour a l'emprunt**.

Deux remedes chiffres, aucun ne rentre :

| remede | coût |
|---|---|
| memoriser le blob par emplacement (greffe sur `0x021A2A30`, qui rend le pointeur) + table de 8 mots | 56 + 32 = **88 o** |
| vider et recharger en bloc a l'echec (`Reset` du tas, rebatir la table, prechargement normal) | **~48 o** |

Place restante apres P4 : **~70 octets en quatre fragments de 4 a 28**. Le plus
gros trou fait 28 octets, et trois decoupages ont deja produit deux des quatre
defauts ci-dessus.

**LE SEUIL EST AUSSI UNE DETTE.** Le bon critere de `talon_source` est « la liste
de prechargement est-elle vide », pas « le tas est-il gros ». Il coute une
quinzaine d'instructions. Trois cartes seulement ont ete mesurees : un autre
interieur au tas superieur a 180 Ko retomberait dans le defaut 3.

Les deux dettes pointent au meme endroit : **le bootstrap BSS** (69), qui donne
395 Kio et permettrait a la fois l'eviction et le vrai test. C'est desormais le
chemin critique du projet.

## 72. LA PLACE DE CODE : trois echecs, et la seule methode qui ne parie pas

Cette section remplace la promesse du 69 (« le bootstrap BSS debloquera tout ») :
le BSS n'a pas ete utilise, et trois autres emplacements ont echoue avant qu'on
trouve la bonne methode. C'est le vrai acquis de la journee du 9 septembre.

### Ce que le joueur a observe, et qui a lance la chasse

Sur quatre builds de suite : « toujours des bugs de texture dans la ville, en
mode certaines textures sont etirees ». Et, en intérieur comme en ville, jamais
sur le terrain. Les monstres, eux, fonctionnaient : « le premier qui spawn, le
modele correspond bien au monstre ».

### Echec 1 : les bourrages a zero de l'ARM9

**LE CANARI EST LE MAUVAIS TEST, et c'est ecrit dans le 69 lui-meme** : il
prouve qu'une region n'est pas ECRITE par le jeu ; il ne dit rien sur le fait
qu'elle soit LUE. Une plage de zeros peut parfaitement etre une table que le
moteur consulte -- des parametres par defaut, une matrice, des coordonnees.

Bissection avec le joueur pour oracle, puisque lui seul voit les textures :

| build | contenu | intérieurs |
|---|---|---|
| `A` | portier + table source | **propres** |
| `B` | `A` + borne de confiscation | **propres** |
| `D` | `B` + UNE greffe, en passe-plat, a `0x020E7100` | **cassés** |

Une seule greffe, qui ne fait rien d'autre que rappeler la fonction d'origine,
et les textures cassent. Ce n'est donc pas ce qu'elle fait : c'est ou elle est.
Les huit regions « validees par canari » ce jour-la sont toutes suspectes.

Sonde de lectures (`scripts/lua/lectures.lua`) : **inutilisable**,
`event.onmemoryread` ne declenche pas dans ce coeur -- zero lecture partout, y
compris sur les temoins certainement lus. Lecon : un zero sans temoin positif ne
vaut rien.

### Echec 2 : la queue de l'ITCM

Mesure sur la liste d'autoload : bloc 0 vers `0x01FF8000`, donnees 5 952, bss
23 360, donc fin a `0x01FFF280` -- et l'ITCM fait 32 Kio. **3 456 octets que rien
ne declare**, ni les donnees du bloc, ni son BSS, ni l'editeur de liens.

Pour y mettre du code sans bootstrap : agrandir le bloc (`taille` 5 952 ->
29 532, `bss` 23 360 -> 0, donnees = origine + 23 360 zeros + notre code). crt0
recopie, le BSS du jeu se retrouve mis a zero comme avant, notre code atterrit a
une adresse fixe. Elegant -- et **crt0 refuse** : la ROM se bloque au demarrage,
PC fige dans la boucle d'attente (`work/dq9_E.nds`).

Isole du contenu : meme agrandissement rempli de ZEROS, aucune redirection de
site -- **bloque aussi** (`work/dq9_F.nds`). C'est donc la restructuration, pas
l'emplacement. Module conserve : `scripts/patch_itcm.py`, avec ses mesures.

### Echec 3 : le code mort

Le bon test pour du CODE existe et fonctionne -- la surveillance d'execution,
avec temoin positif obligatoire. Deux sessions tres differentes, savestate hors
ville puis demarrage a froid avec menus et interieurs, temoin `Allocate` a 5 692
puis 1 754 :

```
0200341C (2080 o)    779 /    669   VIVANT (muet au chargement, revele par les MENUS)
0204C044 (1500 o) 136594 /  80576   VIVANT
02002CB8 (1888 o)      0 /      0   muet
0200702C (1732 o)      0 /      0   muet
0200884C (1368 o)      0 /      0   muet
```

Ecrit par-dessus `0x02002CB8` : **la ROM se bloque au demarrage**
(`work/dq9_G.nds`), alors que le meme chargeur dans les bourrages demarrait
(`work/dq9_p10.nds`). Il etait donc appele -- pendant l'amorcage, ou par une
table construite a l'execution : la reserve exacte que le 33 avait formulee.

**La surveillance d'execution ne suffit pas non plus.** Et `0200341C`, muet au
chargement puis revele par un menu, montre pourquoi : aucune session ne couvre
tout.

### La methode qui ne parie pas : demander la memoire au jeu

`SafeAllocator::Allocate` rend un bloc dont le jeu GARANTIT qu'il est libre.
Plus de canari, plus de surveillance, plus de « probablement ».

Quatre primitives, toutes identifiees par desassemblage ce jour :

| adresse EU | role | comment trouvee |
|---|---|---|
| `0x02032554` | `Allocate(tas, taille)` | connue |
| **`0x020750A8`** | **lecture d'un fichier NitroFS** `(chemin, tampon, &taille)` | par l'appelant de `data/prm/skilltable.bin` (`0x0209A410`) |
| **`0x020C8300`** | `DC_FlushRange(adresse, taille)` | balayage des `mcr p15, c7` |
| **`0x020C833C`** | `IC_InvalidateRange(adresse, taille)` | idem |

Les deux dernieres sont indispensables : on ecrit du CODE par le cache de
donnees, et le prefetch d'instructions ne le verrait pas.

### L'architecture

**L'amorce**, 100 octets, dans l'espace POSSEDE -- des regions jouees des heures
par le joueur (`v14`, `v29`, `v40`, `B`). Elle tourne a chaque montage : alloue
1 024 octets sur le tas des modeles (ou la borne a laisse 50 a 92 Kio), lit
`data/prm/dq9rand.bin` dedans, vide le cache de donnees, invalide celui
d'instructions, puis passe la main a l'installateur du blob. Elle depile avant de
sauter, si bien que l'installateur rend directement a son appelant -- les quatre
octets ainsi gagnes sont exactement ce qui manquait pour tenir dans 100.

Sur echec -- allocation refusee, fichier absent -- elle rend la main sans rien
installer : les sites gardent leurs appels d'origine et le jeu se comporte comme
sans chargeur. Degradation propre et gratuite.

**Les 48 octets qui manquaient** viennent de la greffe A2, passee de 140 a 92 :
sa validation d'appartenance au conteneur et son test du code de modele n'ont
plus de sens depuis que le portier consulte la table source (68), qui trouve
toujours l'espece et toujours avec un vrai code.

**Le blob**, 404 octets sur les 1 024 alloues, entierement RELOGEABLE :

```
+0x00   en-tete : le deplacement de l'installateur
+0x04   mots     DEMANDE / DEPART / BORNE
+0x10   table    sept paires {site, deplacement de la cible}, puis un zero
+0x50   installateur
+0xB8   les cinq greffes
+0x12C  le declencheur, EN UNE SEULE PIECE
fin     le pool de litteraux
```

Les donnees precedent le code pour que tous les acces soient des deplacements
ARRIERE, seul sens que `sub rX, pc, #n` sait exprimer.

Ce que « relogeable » impose :

- appel vers le jeu : `ldr ip, [pc, #{Lx}] ; mov lr, pc ; bx ip`
- branchement : `ldr pc, [pc, #{Lx}]`
- acces a nos donnees : `sub rX, pc, #{@@etiquette}`

Verifie a la relecture : `greffe_a` commence par `sub r1, pc, #0xbc`, soit
`base+0xc0-0xbc = base+0x04` -- les mots, quelle que soit l'adresse du bloc.

Ce surcout de deux instructions par appel etait impensable a vingt-quatre octets
pres ; il est indolore dans un bloc de 1 024, et il fait disparaitre le
DECOUPAGE -- source de deux des defauts du 71 et des deux pannes du 58 et du 61.

**SEPT sites reecrits a l'execution**, pas six : les six du prechargeur, plus
l'appel au declencheur dans `emprunt`. Ce septieme est un `mov r0, r0` dans la
ROM, ce qui donne la degradation propre.

### Deux outils ajoutes a l'assembleur, et pourquoi

- **`{@@etiquette}`** : le deplacement pc-relatif jusqu'a une etiquette, soit
  `(ici + 8) - cible`. Indispensable pour qu'un bloc relogeable atteigne ses
  propres donnees. **L'assembleur le calcule, jamais nous** : un litteral lu
  quatre octets trop loin (58) et une sortie commune decalee d'une instruction
  (61) sont les deux pannes les plus couteuses du projet.
- **`etiquettes_out`** : rend la position des etiquettes, pour ecrire les donnees
  reservees (table des sites, mots de commande) apres l'assemblage.

### Ce qui reste a faire

1. Ajouter `data/prm/dq9rand.bin` a la ROM (ndspy), poser l'amorce dans l'espace
   possede -- 100 octets qui n'y sont pas contigus, donc **en deux morceaux** --
   et l'accrocher au montage.
2. Mettre le `mov r0, r0` a la place du `bl declencheur` d'`emprunt`, a l'adresse
   que la table attend.
3. Retirer le detournement des sites a la construction : l'installateur s'en
   charge.
4. Demarrage a froid, puis test en jeu.
5. **Enfin l'eviction**, avec 620 octets de marge dans le blob : liberer le
   modele remplace, pour que TOUTES les apparitions aient le bon modele et plus
   seulement la premiere.

## 73. Le chargeur relogeable : chaine complete, mais la ROM se bloque

Suite du 72. Tout a ete construit et verifie piece par piece ; l'ensemble ne
demarre pas. Etat exact au terme de la session du 9 septembre.

### Ce qui est acquis, verifie

- **Les quatre primitives**, identifiees par desassemblage : `0x02032554`
  (Allocate), **`0x020750A8`** (lecture d'un fichier NitroFS), **`0x020C8300`**
  (DC_FlushRange), **`0x020C833C`** (IC_InvalidateRange).
- **Le blob**, 836 octets, entierement relogeable : douze sites dans sa table,
  en-tete portant le deplacement de l'installateur (`+0xB0`), acces pc-relatifs
  verifies justes (`sub r1, pc, #0xbc` retombe sur les mots).
- **L'amorce**, 140 octets, tient exactement dans l'espace possede (zone : 280
  sur 280, avec le bitmap a 48 et A2 degraissee a 92).
- **Le fichier** correctement ajoute : `dwc/dq9rand.bin`, id 7516, 836 octets,
  en-tete juste.
- **Aucun abort** : `scripts/lua/abort.lua` ne declenche plus.

### Ce qui ne marche pas

`work/dq9_J.nds` se bloque au demarrage : PC constant a `0x020C9C0C` sur les cinq
releves de `demarrage.lua` -- la signature malade, celle de `E`, `F` et `G`. Les
builds sains (`p9`, `p10`) montrent des PC varies. Et l'overlay 17 n'est jamais
charge : les douze sites lisent `0x00000000`.

### Deux defauts trouves en route, tous deux du meme type

**`r1` n'est pas la destination du fichier.** `0x020750A8(chemin, tampon,
&taille)` utilise `r1` comme plan de travail du systeme de fichiers, et c'est la
VALEUR DE RETOUR qui pointe sur le contenu. L'appelant du jeu le dit a trois
lignes de la : `bl 0x20750A8` puis `movs r4, r0` (`0x0209A410`). Symptome :
abort a `0xFFFF0108`, `lr = 34793DFE`.

**Dans NitroFS, l'identifiant d'un fichier est IMPLICITE** -- il decoule de
l'ordre des noms dans l'arborescence, aucun champ ne le porte. Ajouter un nom
dans `data/prm` lui donne l'identifiant suivant DE CE DOSSIER, celui d'un fichier
existant, et decale tout le reste : le jeu lisait une archive GPC2 de 52 320
octets. Et la ROM porte des fichiers SANS NOM en fin de table, donc « le dernier
identifiant » n'est pas « la fin de `rom.files` » : il faut **inserer** a
l'identifiant que le nom vient de recevoir. Correctif dans
`patch_amorce.ajouter_fichier`.

### La bissection qui reste a faire

L'amorce fait quatre choses ; chacune se teste seule avec `demarrage.lua`, dont
la signature saine (PC varies) et malade (PC constant) est connue :

1. **allouer seulement**, puis enchainer sur le prechargeur ;
2. **+ lire le fichier** ;
3. **+ synchroniser les caches** ;
4. **+ installer**.

Le premier qui bloque nomme le coupable. Soupcons, par ordre :

- **L'allocation de 16 Kio a chaque montage**, jamais liberee : sur une carte
  interieure le tas des modeles est plus petit, et l'echec d'une allocation du
  jeu plus loin bloquerait. A verifier en premier -- reduire a la taille reelle
  du blob (836 o) et voir.
- **`0x020750A8` appelee depuis le montage** : elle purge la file asynchrone
  (`0x0202F7B8`) comme toutes les lectures synchrones, en pleine construction de
  carte. C'est le meme mecanisme qui etait suspecte au 71.
- **L'ecriture dans le code de l'overlay 17** pendant que le jeu tourne, meme
  avec les caches synchronises.

### Ce que le joueur a en main

`work/dq9_B.nds` : toutes les especes apparaissent, le combat, l'echelle et la
hitbox sont justes, les interieurs sont propres. Seule l'apparence du symbole est
empruntee -- le chargeur n'y est pas. Ce n'est pas l'objectif, c'est le dernier
etat sain.

## 74. Le chargeur relogeable s'installe -- et les quatre fautes qui le cachaient

Le 73 concluait « chaine complete, mais la ROM se bloque ». **Elle ne se bloquait
pas.** Aucune des ROM soupconnees ne se bloquait. Ce qui se bloquait, c'etait la
lecture.

### 74.1 L'instrument qui declarait le gel

La sonde de demarrage relevait `ARM9 r15` une fois par image et concluait au gel
si elle ne voyait qu'un seul PC :

    PC vus = pc=020C9C0C          -> « GEL »

`emu.frameadvance()` rend la main **toujours au meme point du tour de boucle**.
Le PC y vaut donc toujours la meme chose, quel que soit l'etat du jeu : la sonde
mesurait sa propre periodicite. Le temoin « sain » qui l'avait validee
(`p10`, six PC distincts) avait ete pris sur une sonde qui echantillonnait
autrement -- comparaison entre deux instruments differents, presentee comme une
comparaison entre deux ROM.

**Preuve** : `dq9_B3.nds`, declaree bloquee, est **identique octet pour octet** a
`dq9_B.nds`, que le joueur avait validee en jeu (meme MD5,
`f4ea3c169e68102e7c35b129f06c75df`). Et la capture d'ecran prise par la sonde
elle-meme, dans le meme dossier, montre le jeu dans l'eglise en train de
sauvegarder.

C'est la **quatrieme** fois dans le projet qu'une mesure est prise avec un
instrument non valide : la sonde de lectures sans temoin (`event.onmemoryread`
qui ne se declenche pas), la bissection contaminee par le tireur, la
« validation » par canari, et celle-ci. La regle qui en sort et qui vaut pour
tout ce qui suit :

> **Aucune sonde ne rend un verdict tant qu'elle n'a pas rendu le verdict
> attendu sur un cas connu.** Une capture d'ecran vaut mieux qu'une deduction :
> elle ne peut pas se tromper sur « le jeu tourne ».

Corollaire immediat : la greffe A2 n'avait rien casse, son degraissage de 144 a
92 octets etait innocent, et la bissection de l'amorce en cinq etages mesurait
un gel qui n'existait pas.

### 74.2 Les trois defauts reels, trouves par relecture

Une fois l'instrument disqualifie, les defauts se lisent dans le code.

**a) Le fichier etait ajoute deux fois.** `patcher()` appelait
`ajouter_fichier(rom, blob)` en tete -- pour connaitre le chemin avant d'ecrire
la chaine -- et une seconde fois en queue, reliquat de la version d'avant. La
deuxieme entree `dq9rand.bin` dans le meme dossier redecalait tous les
identifiants suivants : le jeu lisait un fichier de rang voisin.

**b) L'amorce chevauchait la greffe A2.** Elle etait posee a `ZONE_LIBRE + 0x30
+ 92`, c'est-a-dire derriere une greffe A2 supposee degraissee a 92 octets. Une
fois A2 rendue a ses 140 octets, l'amorce lui rentrait dedans sur 48 octets.

**c) `patch_place` posait un talon de plafond dont le blob n'a pas besoin.**
Avec `--chargeur` il etait deja neutralise ; avec `--blob` il ne l'etait pas, et
il tombait sur les 36 octets que la borne occupe deja (`0x020f1d50 n'est pas
libre`). C'est le mot `BORNE` du blob qui joue ce role.

### 74.3 L'amorce demenage dans la fonction du tireur

`ZONE_LIBRE` (280 octets) porte le bitmap (48) et la greffe A2 (144) : il n'en
reste que 88, et l'amorce en demandait 140. Plutot que de rogner une greffe
validee en jeu -- l'erreur du 73 -- on la met ou la place existe vraiment :

    0x02073FEC   le tireur, deux instructions             8 o
    0x02073FF4   L'AMORCE                               116 o    -> 124 sur 132

`0x02073FEC` est la **fonction d'origine du tireur de terrain**, 132 octets que
le projet possede depuis P3 (la greffe B l'occupait entiere, et P3 est validee en
jeu). Le tireur du blob n'en garde que huit : `mov r1, #0x8000 ; b GREFFE_A2`.
L'ordre d'ecriture est impose -- effacer les 132, poser le tireur a l'entree,
poser l'amorce derriere -- car l'entree est l'adresse que le jeu appelle.

L'amorce passe de 140 a 116 octets par trois economies, sans rien perdre :

| economie | gain |
|---|---|
| `push {r0, r4, r5, lr}` au lieu de `push {r4,r5,lr}` + `mov r4, r0` : le `pop` restitue `r0` directement, les deux `mov r0, r4` de sortie disparaissent | 12 o |
| l'installateur rend le talon dans `r1` et non `r0` : plus de `mov r1, r0` | 4 o |
| la sortie d'echec branche sur `PRECHARGEUR` en relatif (`b`, portee 32 Mio) au lieu de passer par un litteral | 8 o |

### 74.4 Le miroir du compte

`talon_borne` vit dans l'ARM9 et doit savoir si la carte porte des monstres ; son
critere est « la table source a-t-elle ete batie ». Mais la table vit desormais
dans le blob, dont l'adresse change a chaque montage. Le talon de source recopie
donc son compte dans le premier mot de `GREFFE_C` (`SRC_MIROIR = 0x020F1CB8`),
l'ancien emplacement de `SRC`, fixe et libre. La chaine du chemin se decale de
seize octets, a `0x020F1CC8`.

### 74.5 Mesure : douze sites sur douze

Sonde `scripts/lua/k.lua`, demarrage a froid sur la sauvegarde du joueur, avec
trois temoins positifs (`T1` l'accroche de l'overlay 17 est bien un `bl` vers
l'amorce, `T2` l'amorce est bien en RAM, `T3` une capture d'ecran).

    tour  6  image   2041  carte=  118  accroche=EBFB43BC
    T1 accroche 021A30FC -> 02073FF4   OK
    T2 amorce   02073FF4 = E92D4031   OK (push {r0,r4,r5,lr})
    12 / 12 sites installes

Deux pieges de harnais valent d'etre notes, tous deux capables de rendre un faux
negatif :

- **la SaveRAM est nommee d'apres la ROM.** Une ROM neuve demarre sans
  sauvegarde et s'arrete sur « Create a new adventure log ». Il faut copier
  `work/save_origine/dq9.sav` sur `tools/bizhawk/NDS/SaveRAM/dq9 <etiquette>.SaveRAM`
  avant de lancer.
- **l'overlay 17 arrive avant le jeu**, des le menu de chargement. S'arreter a
  « l'overlay est charge » laisse la sonde dans la boite de dialogue, ou les
  fleches deplacent un curseur. Le bon critere est `carte != 0` (`0x020FDD44`).

## 75. L'ecran noir : un pointeur mort, pas un manque de place

Symptome rapporte : une entree en combat sur deux ou trois se fige sur un ecran
noir. Trois hypotheses successives, dont deux fausses -- et c'est une savestate
prise **pendant** l'ecran noir par le joueur qui a tranche.

### 75.1 Les deux hypotheses fausses

**Le tas des requetes asynchrones affame.** La borne plafonnait a 16 Kio ce que
le tas des modeles lui cede, la ou le vanilla lui en cede ~77 sur le terrain. On
a inverse le sens de la borne (garder une reserve fixe, ceder le reste) et
construit `dq9_L.nds`. **Aucun changement.** L'explication est instructive :
`talon_borne` sort immediatement quand le miroir vaut zero, et le miroir valait
justement zero -- la borne n'avait donc jamais ete active sur le terrain, et K et
L y etaient identiques.

**La tempete de reessais.** Un portier qui rejette tout fait exploser le compte
d'appels a l'apparition (3 629 contre 2, cf. 20). Mesure sur l'etat fige :
`portier1=0 emprunt=0 prechargeur=0 montage=0 alloue=0` sur 900 images. Rien ne
tourne. Ce n'est pas une tempete.

### 75.2 Le vrai defaut, lu dans l'etat fige

    PC au bord d'image sur 900 : FFFF0108

`0xFFFF0108` est le vecteur d'exception de l'ARM9. Le jeu ne boucle pas, il a
plante. En mode abort `lr` porte l'adresse de retour :

    lr = 0235ACDC     et le blob avait ete installe a 0235A9CC

L'adresse fautive tombe donc DANS le blob -- mais les mots qu'on y lit
(`023501FF`, `7CCC809B`) ne sont pas des instructions. La memoire a ete reprise.

Confirmation directe, dans le meme etat, en lisant le contexte de terrain que
`r11` designe encore :

    modeles  handle 00000000 : hors RAM
    parent   handle 00000000 : hors RAM

**A l'entree en combat, le contexte de terrain est entierement demonte.** Le tas
des modeles, qui portait le blob, n'existe plus. Les douze sites, eux, gardent
leur `bl` : le premier rappele saute dans des donnees.

Le defaut n'etait donc pas un manque de place mais un **pointeur mort**, et
aucune des trois pistes memoire n'y pouvait quoi que ce soit.

### 75.3 Ce qui ferme les autres portes

- **Le bootstrap BSS est clos**, et la doc du 69 le disait deja : tout ce qu'on
  ajoute a l'image tombe dans la plage que crt0 met a zero au demarrage. Il n'y a
  pas de RAM statique permanente a prendre.
- **Aucun tas du contexte de terrain ne convient**, parent compris : les deux
  meurent ensemble.
- Un balayage de la RAM sur l'etat fige trouve 85 tas `FRMH`, dont deux gros et
  bas (`02200190`, 69 Ko libres ; `02257190`, 94 Ko libres). Ils survivraient
  peut-etre, mais leur poignee n'a pas d'adresse fixe connue, et un frame heap
  rembobine tout a la premiere liberation : le pari serait du meme ordre que
  celui du canari.

### 75.4 Le desinstalleur

Le demontage se lit en clair dans l'overlay 17 :

    021A31A4  add r0, r6, #0x13c ; add r0, r0, #0x1000 ; bl 0x20328c4
    021A31B8  ... bl 0x2032740      (vider)
    021A31C4  ... bl 0x203248c      (detruire)

On accroche **le premier appel** : le blob y est encore vivant, c'est le dernier
instant ou il peut se retirer. Le talon (44 octets, `0x020E7328`) ne connait du
blob qu'un mot fixe dans l'ARM9 (`BLOB_BASE = GREFFE_C + 0x20`), ecrit par
l'installateur ; il n'a donc rien a savoir de l'allocation. Si ce mot est nul --
amorce en echec, ou desinstallation deja faite -- il ne fait rien.

Le desinstalleur vit dans le blob, ou la place est gratuite. La table des sites
passe de deux mots par entree a trois : `{site, deplacement de la cible, mot
d'origine}`. L'en-tete du blob passe de un mot a deux : `{installateur,
desinstalleur}`.

**Valide en jeu par le joueur : plus aucun ecran noir.**

### 75.5 Deux autres defauts corriges au passage

**`r0` ecrase avant `CHARGE_SOURCE`.** `0x0206EFE8(contexte, tas)` ecrit
`{compte, bloc, chaines}` a l'adresse que `r0` designe. Les ecritures du miroir,
ajoutees entre le chargement de `r0` et l'appel, l'ecrasaient : la table des 438
se batissait DANS le miroir et la vraie table du blob restait vide. Le portier ne
connaissait donc aucune espece. Symptomes expliques d'un coup : le miroir a zero,
et « le premier monstre est bon quatre fois sur cinq » -- les seules especes
acceptees etaient celles de la carte, dont le modele etait deja charge.

**Le tampon du systeme de fichiers, 16 Kio pris sur le tas des modeles.** Mesure
sur le terrain, table enfin batie : `tas 188180/188832`, soit 652 octets libres.
La reserve de 32 Kio etait amputee de moitie par ce seul tampon, jamais rendu
avant le demontage. Ramene a 4 Kio (le blob fait 1 Ko), reserve portee a 48 Kio.

### 75.6 Etat mesure

Trois modeles a la demande tiennent : le joueur observe les deux premiers
monstres toujours conformes, le troisieme jamais. La suite est l'**eviction** --
liberer un modele pour en charger un autre -- qui suppose de passer ce tas en
ExpHeap sur les seules cartes a monstres, ce que le miroir permet enfin de
conditionner.

## 76. Le budget du chargement a la demande, et ce que coutera l'eviction

### 76.1 Le budget, enfin calculable

Le tas des modeles fait 188 832 octets sur le terrain. Ce qui s'y passe au
montage, dans l'ordre :

    tampon du systeme de fichiers (amorce)              4 096
    prechargeur, `BORNE` modeles                    ~21 500 chacun
    confiscation : tout sauf `GARDE`, au tas asynchrone
    reste pour le chargement a la demande            GARDE - 4 096

Mesure sur la savestate du joueur (`dq9_Q`, `GARDE = 98 304`, `BORNE = 2`) :
`tas 152 020 / 188 832` au chargement, `173 796` apres une apparition de plus --
soit **21 776 octets par modele charge a la demande**. 94 208 utiles divises par
21 776 donnent 4,3 modeles, et le joueur en observe « 4 surs, parfois 5 ».

La progression est donc entierement expliquee par un seul chiffre :

| version | GARDE | tampon | modeles a la demande | observe |
|---|---|---|---|---|
| N, O | 32 puis 48 Ko | 16 puis 4 Ko | 0,6 puis 2,0 | « les deux premiers » |
| P | 48 Ko | 4 Ko | 2,0 | « les deux premiers » |
| Q | 96 Ko | 4 Ko | 4,3 | « 4 surs, parfois 5 » |

**Et le plafond est atteint.** Avec `BORNE = 2` il ne reste que ~141 Ko libres
avant la confiscation : monter `GARDE` a 120 Ko ne gagnerait qu'un modele et
laisserait 21 Ko au tas asynchrone, contre 77 en vanilla. Le joueur n'a signale
aucun defaut de texture a 58 Ko, mais il n'y a plus de marge a prendre.

### 76.2 Ce qu'un chargement alloue, exactement

Sonde `scripts/lua/couts.lua`, accrochee a l'allocateur pendant une apparition :

    alloc 1 :    704 a 1 056 o   appele de 021A28F4   (la table de fiches)
    alloc 2 : 16 136 a 20 100 o  appele de 0207567C   (le modele lui-meme)

Deux blocs, tous deux sur `ctx+0x113C`. La table de fiches vaut
`176 x (DEPART + 1)` : elle grandit avec la rotation, et **elle ne peut pas etre
rendue** puisque les emplacements deja remplis pointent dedans. C'est un fuite
structurelle, mais d'un kilo-octet : le prix a payer est le second bloc.

### 76.3 La fiche, et le pointeur qui manque

Sonde `scripts/lua/fiche.lua`. Une fiche fait 176 octets :

    +0x00  halfword : un drapeau (1)
    +0x02  halfword : l'espece          (`ldrsh r1, [r0, #2]`, cf. TROUVE_MODELE)
    +0x04  halfword : l'emplacement     (0x0A pour l'emplacement 3 : 7 + 3)
    +0x08  pointeur : LA FIN du bloc du modele
    +0x0C  pointeur : cette fin + 0xAC

Verification : emplacement 4, fiche `0237FE50`, bloc rendu `0237FF00` de 20 100
octets ; `0237FF00 + 0x4E84 = 02384D84`, exactement le mot a `+0x08`.

**La fiche ne porte donc pas la base du bloc.** Sur le frame heap actuel elle se
deduit (`fiche + 0xB0`, les allocations etant contigues) mais cette egalite
disparait des qu'on passe en ExpHeap -- c'est-a-dire exactement quand on en
aurait besoin. Il faudra capturer la base nous-memes.

### 76.4 Le plan de l'eviction

1. **ExpHeap sur les seules cartes a monstres.** `talon_expheap` compare `r2` --
   la taille du bloc, deja en main a `CreateTypeA` -- au seuil de terrain. Les
   villes et l'eglise gardent le frame heap, ce qui est precisement ce qui a
   repare leurs textures ; le terrain gagne un `Free` par bloc.
2. **Capturer la base du modele.** Une greffe sur `0x0207567C` qui, lorsque
   `DEMANDE` est arme, note l'adresse rendue dans `MODELES[DEPART]`, un tableau
   de huit mots dans le blob. C'est un treizieme site, dans l'ARM9 cette fois.
3. **Rendre avant de charger.** Dans le declencheur, si `MODELES[DEPART]` est
   arme : liberer ce bloc, vider l'emplacement `7 + DEPART` par `0x0200FD58`, et
   seulement ensuite appeler le prechargeur.
4. **Reste a identifier** : la methode de `SafeAllocator` qui libere UN bloc sur
   un ExpHeap. Celle qu'on connait (`0x02032628`) passe la constante 3 sur le
   chemin EXPH -- c'est une liberation globale, pas celle d'un pointeur.

## 77. L'eviction, le pool des especes, et le comportement des monstres

### 77.1 Ce qui limitait a quatre modeles

Trois causes successives, chacune trouvee par la mesure et non par raisonnement.

**Le tampon du systeme de fichiers.** 16 Kio pris sur le tas des modeles a chaque
montage, jamais rendus, sur une reserve de 32. Ramene a 4 Kio.

**L'eviction s'appliquait au mauvais emplacement.** Elle cherchait un emplacement
libre parmi les huit et en trouvait toujours un -- le tas ne tient que six
modeles pour huit emplacements -- donc elle ne liberait rien et le chargement
echouait quand meme. Elle procede desormais en **deux passes** : d'abord un
emplacement OCCUPE dont aucun acteur vivant ne porte l'espece, seul choix qui
rende de la memoire ; a defaut seulement, un emplacement vide.

**Le tas concurrent etait surestime.** On croyait laisser 58 Kio au tas des
requetes asynchrones ; mesure sur le terrain (`scripts/lua/asynchrone.lua`) :

    async HMRF  0 / 16736   modeles HPXE 188328

Il n'en recevait que 16 736 et n'en utilisait **aucun**, seize tours de mesure
durant. La reserve des modeles est donc passee de 96 a 135 Kio et le
prechargeur de deux especes a une.

### 77.2 Ce qu'un modele coute, et comment on le rend

    alloc 1 :   704 a 1 056 o   depuis 021A28F4   la table de fiches
    alloc 2 : 16 136 a 20 100 o depuis 0207567C   le modele

La fiche (176 octets) porte l'espece a `+0x02`, l'emplacement a `+0x04` et la
**fin** du bloc a `+0x08` -- jamais sa base. Sur un frame heap la base se
deduisait par contiguite ; en ExpHeap non. Une greffe sur `0x02075678` note donc
l'adresse rendue, et seulement pour les gros blocs en mode demande.

`SafeAllocator::Free` est `0x02032628(tas, pointeur)` : sur `EXPH` elle appelle
`0x020AF788(tas, pointeur)`, une liberation par bloc ; sur `FRMH` elle passe la
constante 3, une liberation globale. D'ou l'ExpHeap **conditionne au seuil de
terrain** dans `talon_expheap` -- villes et eglise gardent le frame heap.

### 77.3 Le pool : une liste blanche de 256

Deux listes noires ont echoue avant. Le critere mecanique « n'apparait jamais en
vadrouille » ecartait 69 monstres ordinaires et laissait dans le pool de terrain
**dix-sept vrais boss** qui rodent comme symboles d'antre -- Zoma, Psaro,
Malroth, Lordragon, Atlas, Nemee, Equinocte, Moby Pick, Epidemon, Fourax, Medhor,
Monte-gluancien, les trois generaux, roi Godefroi, Tyrannamort. Le joueur a vu
Equinocte et le general Mac Assin en plaine.

Le bestiaire, lui, numerote : **les monstres vont de 1 a 256, le 256e est le
Pelagosaure, et tout ce qui suit est un boss.** C'est un critere du jeu.
`scripts/monstres_nommes.py` porte les 288 identifiants internes correspondants
(un monstre a plusieurs entrees, une par rang). Il faut filtrer aux DEUX
endroits : le bitmap gouverne le tirage a l'apparition, les tables de rencontres
decident de ce que la carte precharge et de ce que son conteneur accepte.

Le plafond de taille passe de 32 a 48 Kio : il datait du temps ou le prechargeur
tenait cinq a onze modeles ; le plus gros modele du jeu fait 42 408 octets, donc
plus personne n'est ecarte pour son poids.

### 77.4 Le comportement : le noeud du conteneur 2

L'apparition garde deux enregistrements dans l'acteur : `+0x180` celui du
conteneur 1 (`carte+0x2F8`, l'echelle et la boite, issu de `mon_data`) et
`+0x184` celui du conteneur 2 (`carte+0x304`). Le portier 2 fabriquait le second
de toutes pieces. Releve sur des monstres vivants :

    natif       050B0093 003C0309 00371333 00000037 <suivant> 632600AA ...
    synthetique 00000075 00000000 00000000 00000000 00000000  00000000 ...

Huit mots de parametres de comportement contre un seul champ. D'ou des monstres
immobiles et sans reaction, puis un abort : la machine a scripts (`0x020B4B00`,
`ldrh lr, [r2]`) lit sa ressource en `[r4+0xD8]`, la trouve nulle, prend une
branche qui met `r2` a zero et dereference quand meme.

**Et il n'y avait qu'un seul noeud pour tous les monstres** : deux acteurs
vivants pointaient sur la meme adresse et le champ espece basculait de l'un a
l'autre. Il y en a huit desormais, en rotation, chacun **copie d'un noeud
natif** de la carte avec la seule espece corrigee : comportement emprunte mais
valide.

CE QUI RESTE POUR LES VRAIS PARAMETRES. Le conteneur 2 est bati au montage par
`0x021B5348`, une par une, a partir des entrees de la liste de prechargement de
la carte (`carte+0x44`) : `0x0209C0D0` en extrait l'espece, `0x0202FED8` recupere
la ressource, `0x0206EE90` en fait un noeud. Les parametres sont donc bien
**attaches a l'espece** et non a la carte -- ils sont atteignables. Il reste a
identifier le nom de la ressource et a declencher son chargement a l'apparition.

### 77.5 L'adressage pc-relatif, en deux temps

Trois assemblages ont echoue parce qu'un `sub rX, pc, #{@@etiquette}` avait cesse
d'etre encodable quand le blob grandissait (1 048 puis 1 044 octets). Les quinze
adressages du blob se font desormais en deux instructions, `d & 0xFF00` puis
`d & 0xFF`, encodables par construction quelle que soit la taille. Le couple doit
rester sur deux lignes consecutives : la seconde retrouve le `d` de la premiere
en RETRANCHANT quatre a la sienne -- l'avoir ajoute decalait la cible de huit
octets. L'assembleur nomme desormais la ligne fautive quand keystone refuse.
