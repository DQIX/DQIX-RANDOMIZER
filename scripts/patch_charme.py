#!/usr/bin/env python3
"""Le CHARME de Zenus (ZER-116) : un compagnon passe « en face » et agit seul.

CE QUE VOIT LE JOUEUR. Quand Zenus utilise l'action du charme, un des trois
compagnons (jamais le heros ; personne tant que Paradin, coup de grace du
paladin, retient Zenus : le charme part sur le paladin et echoue, research
§113.17), vivant, tire au hasard, est charme pour 1 ou 2
de ses decisions : le menu le saute, l'IA d'equipe choisit son action comme en
« Sans pitie » (ses sorts et techniques appris), puis la REGLE B du joueur
(research §113.5) la retourne contre l'equipe. La portee vient de la fiche de l'action, comme pour le
constructeur de cibles du jeu (overlay 0 `0x021540FC`) : camp `[fiche+8]` bits 8-9 (1 = en face), portee
`[fiche+0x14] >> 28` (2 une cible, 3 tous, 4 un groupe, 5 l'attaque, selon l'arme : 2, 3 ou 4). Une action sur
l'autre camp garde son action : sur une cible, elle vise un des trois autres membres tire au hasard ; de zone
(tous, groupe, boomerang, fouet), elle touche tous les coequipiers vivants, lui exclu, comme un groupe de
monstres (joueur, 06/11 ; G_ZONE). Tout le reste (soin, soutien, defense) devient Attaque sur l'un d'eux.

CE QUE LE JEU FAIT, ET OU ON S'ACCROCHE (research §113.5-113.6, mesure au banc
le 31/10/2026 sur b33_24) :
  * menu, overlay 26 : au debut du menu d'un membre (index sb), `0x021DCE1C`
    dit s'il ne peut pas recevoir d'ordre (fiche+0x14 bit 8). Son appel en
    `0x021DCDC8` passe par G_MENU : un charme fait sauter le membre (« OK! »,
    commande 01 00 00 00, file a 1).
  * IA d'equipe, overlay 24 : la pre-verification `0x021F9030` et le
    repartiteur des tactiques `0x021F8F20` lisent la tactique
    ([membre+0x94C], 5 = « Suivre les ordres » : pas d'IA). Les deux `and`
    qui la lisent passent par G_PRE / G_DISP : 0 (« Sans pitie ») si charme.
  * le retour du repartiteur `0x021F9020` (r4 acteur, r6 entree de la file,
    r7 index) devient G_B : la regle B, et une decision de charme consommee.
  * decision de chaque acteur, overlay 0 : `0x02157C24` appelle le test de
    confusion (`0x021543F4`) avec r7 = id de l'acteur, sb = entree de la file
    (son action deja choisie). G_POSE : si un monstre a choisi l'action du
    charme, un compagnon est charme. Le tour se compile acteur par acteur dans
    l'ordre (decision puis resolution) : un compagnon plus lent que Zenus est
    charme des ce tour, comme la confusion du jeu.

L'ETAT. Quatre octets a nous, derriere le code (un par index : decisions de
charme restantes). Le jeu n'a pas d'octet libre dans la commande d'un membre
(+8 est un compteur 32 bits, +4..+7 remis a zero). Deux gardes le rendent sur :
il ne vaut que si l'acteur 0xC0 est Zenus (espece ESPECE), sinon il s'efface ;
et le menu du premier tour d'un combat (compteur de tours du membre a 0) efface
celui du membre. Un charme ne survit donc pas au combat, victoire ou defaite.

OU VIT LE CODE. Derriere l'overlay 11 (0x02188B80) : la place des overlays 7
a 14 court jusqu'a 0x0218B5A0, le 11 est charge sur le terrain comme en combat
(vidages du banc), et ses 10 784 octets de queue sont a zero dans les 58
vidages du projet. L'overlay 11 grandit (pas de BSS a convertir).
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

OVL = 11
PLAFOND = 0x0218B5A0            # fin de la place des overlays 7-14 (le 8)
ESPECE = 900                    # Zenus (zenus_mon, espece 900)
RAND_BELOW = 0x02032380         # r0 = n -> r0 dans [0, n[
MGR = 0x0200F398                # r0 = le gestionnaire des combattants
ACTEUR = 0x0200FE78             # (gestionnaire, id) -> acteur ou 0
EST_ENDORMI = 0x021DCE1C        # overlay 26, le test d'origine du menu
EST_CONFUS = 0x021543F4         # overlay 0

# LE NEANT (ZER-116, joueur 31/10 : « vers 2 000 PV restants il supprime un
# compagnon pour toujours, jamais le heros ; son equipement va dans le sac »).
#   * decision de Zenus (G_POSE) : PV <= SEUIL, aucune victime encore marquee
#     -> son action devient NEANT, une victime est tiree parmi les membres
#     vivants qui ne sont pas le heros ([gestionnaire+0x3AC]) et MARQUEE dans
#     des drapeaux de jeu (VICTIME_*) : id + 1 sur trois bits, l'etat survit au
#     combat et a la sauvegarde ;
#   * cibles d'une action de MONSTRE (overlay 0 `0x02154A04` : r0 contexte,
#     r1 id de l'acteur, r2 action, r3 liste de sortie, rend le compte ; celui
#     de l'equipe, `0x021540FC`, ne sert pas aux monstres -- mesure 01/11) :
#     pour NEANT, la liste est la victime seule, et ses PV tombent a 0 ;
#   * apres le combat, l'action de declencheur 0x80 (aucun declencheur du jeu
#     ne l'emploie ; alias de 0x77 dans le lanceur `0x0206F834`, entree de sa
#     table de sauts en `0x0206F8E8`, a elle seule ; 0x92, que le lanceur
#     saute, n'est jamais mis en file : mesure 01/11) fait ce que font les
#     adieux chez Tulipe : objets
#     portes au sac (`0x021B6BB8`), fiche tiree du groupe (`0x021B6D60`, la
#     sortie du groupe du Carre), son equipement au sac (`0x0207C388`, tables
#     de l'overlay 3 `0x0217F494` / `0x0217F4A6`) ; la fiche n'entre jamais
#     dans la liste du Carre. zenus_royaume.declencheurs(combat) l'appelle a
#     la victoire (genre 15) et a l'entree de la salle du trone (genre 20,
#     apres une defaite).
# 0x386, PAS 0x1F7 : c'est l'action que le jeu met lui-meme dans la file de qui ne peut pas
# encore agir (overlay 0, `mvn fp, #0` puis `add r0, fp, #0x1f8`, 0x0215DDD0). Sa fiche est vide,
# ce qui l'a fait croire libre le 01/11. Avec 2-3 actions par tour, elle passe a chaque tour, et
# le jeu fait dire « Zenus reduit X au neant » sur un autre monde que notre decision (05/11).
# 0x386 : fiche vide, aucun immediat dans le code de combat (work/zenus_tours/ids_libres.py).
NEANT = 0x386
NEANT_MSG = 0x270
SEUIL = 3500                    # joueur, 05/11, nuit
FLAGS = 0x02108844 + 0x8C       # champ de bits des drapeaux de jeu
VICTIME_DRAPEAU = 0x1FA         # 0x1FA-0x1FC : id + 1 de la victime
VICTIME_OCTET = FLAGS + (VICTIME_DRAPEAU >> 3)
VICTIME_DEC = VICTIME_DRAPEAU & 7
VICTIME_MASQUE = 7 << VICTIME_DEC
# Un seul neant par partie (joueur, 05/11) : une fois le compagnon sorti du
# groupe, la marque ne revient pas a 0 mais a 7 (aucun id). Elle est dans la
# sauvegarde : apres une defaite, le combat suivant ne refait pas de neant.
VICTIME_FAIT = 7
OP_EFFACER = 0x80
TABLE_SAUTS = 0x0206F8B0        # lanceur d'actions, op - 0x72
SUITE_ACTIONS = 0x02070290      # noeud suivant (le cas « rien »)
SITE_EFFACER = TABLE_SAUTS + 4 * (OP_EFFACER - 0x72)
CIBLES = 0x02154A04             # cibles d'une action de monstre, overlay 0
DEGATS = 0x0215A004             # application des degats (r2 cible, r3 degats)
DEGATS_NEANT = 9999             # le coup du neant : plus que tous les PV
# Le CHIFFRE affiche (« environ 9999 points de degats ») ne vient pas de
# DEGATS : l'appelant de l'effet, overlay 24 `0x021EC92C` (blx), garde les
# degats en [sp+0x54] et les passe en 5e argument ([sp]) a l'effet physique
# `0x021DA9E0` (r1 attaquant, r2 cible) ; le message lit sa copie. Mesure a
# froid le 01/11 (soir) : les deux cases a 9999 a l'entree de `0x021DA9E0`
# -> « Papouz et Cie subissent tous environ 9999 points de degats ».
EFFET = 0x021DA9E0              # effet physique, overlay 24
EFFET_RETOUR = 0x021EC930       # son seul appelant mesure (lr)

# LES ACTIONS DE ZENUS (joueur, 05/11, nuit). Le kit est fixe et tout est la des le depart, sauf le
# neant (sous SEUIL). Chaque decision en tire une, jamais deux fois la meme dans un tour ; le charme si
# personne n'est charme ; le soin une fois par combat, sous 75 % de ses PV. Les paliers parlent
# seulement : plus d'action imposee. Remplacer une action demande de la rendre au menu suivant
# (research §113.8) : jusqu'a 3 entrees gardees.
# ZENUS_TABLE=0x21F,0x22D : BANC SEULEMENT, comme KIT_ESSAI de zenus_mon.
# Son soin a lui : la fiche de 0x2AA (Soins complets des monstres, actdt_a) sur un identifiant libre d'actdt_b. Le
# jeu ne rend tous les PV qu'aux actions 0x21 et 0x310 (overlay 24 0x021DB3EC : montant = PV max) ; les autres
# plafonnent a 999, quelle que soit la puissance (+30, mesure a froid : 20 000 donnent encore 999). G_SOIN ajoute
# SOIN a ce test ; 0x2AA reste la fiche des autres monstres. 0x39E : fiche vide, aucun immediat proche (ids_libres.py).
SOIN = 0x39E
SOIN_DONNEUR = 0x2AA
ACTION_CHARME = 0x1F6
# BANC SEULEMENT (comme ZENUS_TABLE) : l'action imposee au compagnon charme, pour voir un sort de zone.
CHARME_ACTION = int(os.environ["CHARME_ACTION"], 0) if os.environ.get("CHARME_ACTION") else None
FICHES = 0x020797EC             # r0 = la table des fiches d'action
FICHE_ACTION = 0x02079E3C       # (table, id) -> fiche ou 0
LISTE_EQUIPE = 0x0215E9FC       # (contexte, liste, max, 1 = vivants) -> nombre de membres
ZONE = 0x021541FC               # constructeur de cibles de l'equipe, la portee calculee (r2)
ZONE_SUITE = 0x02154348         # sa fin commune (r6 = nombre de cibles)
DECUPLO = 0x31
# LE SORT BLEU (joueur, 05/11 : « a la place de Decuplo », +1 cran d'attaque, de defense et d'agilite, l'animation de
# Decuplo en bleu ; hors du tirage une fois au maximum). Sa fiche : celle de Decuplo sur un identifiant libre (0x3AE :
# fiche vide, aucun immediat proche, ids_libres.py), son message de lancement neuf. Son effet est E_BLEU (G_APPLI le
# substitue a celui de la fiche), ecrit sur l'effet du jeu qui monte plusieurs stats (overlay 24 `0x021E1ED4`) :
# pour chaque stat, le test du jeu (peut monter), le cran (+1, borne a 2, duree posee), l'avis au combat, le message
# du jeu (« ... augmente ») pousse dans la file. Crans : fiche +0x58, attaque bits 0-2, defense 3-5, agilite 6-8.
BLEU = 0x3AE
CRANS = (  # (peut monter, cran, avis, message) : arm9, overlay 0, overlay 24
    (0x0208777C, 0x020877D0, 0x02155A50, 0x021E94C4),   # attaque
    (0x02087870, 0x020878C4, 0x02155AF4, 0x021E95D4),   # defense
    (0x02087964, 0x020879B8, 0x02155B98, 0x021E96E4),   # agilite
)
CIBLE_ACTEUR = 0x021536E0       # (combat, id) -> acteur
FILE_MSG = 0x0215E958           # (combat) -> la file de messages de l'action
POUSSER_MSG = 0x0215A88C        # (combat, file, message)
FIN_EFFET = 0x0215CD44          # (combat, file, acteur, 0, [sp] 0, 0, drapeau)
TABLE = tuple(int(x, 0) for x in os.environ["ZENUS_TABLE"].split(",")) if os.environ.get(
    "ZENUS_TABLE") else (0x01, 0x219, 0x21F, 0x23F, 0xBD,      # attaque, nuage, eclair, rugissement, Perturbonde
                         ACTION_CHARME, SOIN,
                         BLEU, 0x2C,                           # le sort bleu, Megaleration (votre defense)
                         # Joueur, 06/11 (soir) : Colere des dieux (« la colere du Tout-Puissant »), Desastre (la comete),
                         # Vague de panique (defense et agilite -50 %), Megakill (mort a toute l'equipe, plus rare),
                         # Hypnoeil (sommeil). Toutes d'actions de monstres du jeu (inventaire du 06/11).
                         0x22C, 0x22A, 0x230, 0x1A, 0x233)
# Chaque action de la table a un poids ; une action exclue sort du tirage sans rien donner a sa voisine (joueur,
# 05/11 : « elles doivent toutes pouvoir sortir au meme taux, peut-etre l'attaque un peu plus »). Nokturnus (IA
# type 1) : 68 58 48 38 27 17 sur 256, son premier emplacement a 26,6 %. Zenus : attaque 16,7 %, le reste 11,1 %.
# Le soin, une fois sous 75 % : poids 2 sur 19 = 10,5 % par decision (emu_tirage_zenus), donc en moyenne vers
# 45-55 % de ses PV ; v14 en jeu, lance a 1 500 PV (joueur, 06/11 : « il est cense arriver beaucoup plus tot »).
# Poids 255 : 94 % a sa premiere decision sous le seuil, plus de 99 % dans le tour (ZENUS_POIDS_SOIN=2 : avant).
POIDS_SOIN = int(os.environ.get("ZENUS_POIDS_SOIN", "255"))
MEGAKILL = 0x1A
# Megakill « un peu plus rare » (joueur, 06/11) : poids 1, la moitie des autres.
# L'attaque simple : 3 jusqu'au 06/11, 5 depuis (joueur : « augmenter un peu le taux de sortie de l'attaque normale »).
POIDS_ATTAQUE = 5
POIDS = tuple(POIDS_ATTAQUE if a == 0x01 else POIDS_SOIN if a == SOIN else 1 if a == MEGAKILL else 2 for a in TABLE)
assert len(TABLE) <= 16, "etat+28 : un bit par action de la table (u16)"
# BANC SEULEMENT (comme ZENUS_TABLE) : ZENUS_POIDS=0x01:255,0x219:0 change des poids sans toucher au kit.
if os.environ.get("ZENUS_POIDS"):
    _p = dict((int(a, 0), int(b, 0)) for a, b in (x.split(":") for x in os.environ["ZENUS_POIDS"].split(",")))
    POIDS = tuple(_p.get(a, w) for a, w in zip(TABLE, POIDS))
# Pas 0x25B, l'action cachee de Corvus : aucun PM rendu (mesure a froid, depart a 40 : 40, 26, 18). A 255
# PM, ses PM ne baissent jamais, ni par les sorts ni par le drain : pas besoin d'en regagner.
# BANC ET ESSAI JOUEUR SEULEMENT (ZENUS_ESSAI=1, jamais livre, joueur 05/11) : equipe a 999 PV
# remis a chaque menu, chaque coup sur un monstre fait 999.
# ZENUS_ESSAI=2 : les coups restent normaux tant que le neant n'est pas parti (sinon 3 501 PV ne
# passent pas le premier tour : il mourrait avant de le lancer).
ESSAI = bool(os.environ.get("ZENUS_ESSAI"))
# ZENUS_ESSAI=3 : pareil, mais PV remis a leur vrai maximum : a 999, les PV depassent le maximum en sortie de combat
# et la jauge du menu deborde de sa barre (824/430, mesure a froid le 05/11).
ESSAI_APRES_NEANT = os.environ.get("ZENUS_ESSAI") in ("2", "3")
ESSAI_VRAIS_PV = os.environ.get("ZENUS_ESSAI") == "3"
ESSAI_VAL = 999
# Etat, apres les 4 octets de charme : +4 victime en attente ; +16 et +20 l'affichage du
# charme ; +24 action imposee (rang du palier + 1) ; +25 replique affichee (rang + 1, 5 = sa
# mort) ; +26 repliques dites (bit 4 : sa mort) ; +27 palier a dire ; +28 u16 actions de ce
# tour ; +30 entrees gardees ; +31 bit 0 soin fait, bit 1 neant ce tour ;
# +32 trois entrees de 8 octets (u32 entree, u16 action, u8 octet +9).
# +56 actions compilees ce tour ; +57 rang de celle qui tue Zenus (0 : aucune) ; +58 actions
# rejouees. Sa derniere replique s'ouvre juste avant l'action fatale (research §113.13).
# +59 compagnon a charmer + 1 (lu par G_CIBLE) ; +60 rang de l'action du charme : le bleu ne vient
# qu'a son rejeu ; +61 le prochain effet est celui du charme : il ne fait rien ; +62 le compagnon a
# afficher en bleu + 1 ; +63 le compagnon charme de ce tour + 1, pour G_ZONE.
ETAT_TAILLE = 64
# LES REPLIQUES (joueur, 05/11 : « par pallier de vie », la boite du combat d'Aquila,
# research §113.11). Un palier franchi est lu au menu du heros et dit au debut du tour.
# Sous PCT_TROIS % de ses PV, Zenus agit trois fois par tour.
PALIERS = (75, 50, 25, 18)      # 18 % de 20 000 : juste avant le neant
PCT_TROIS = 50
BOITE_MSG = 0x271               # apres NEANT_MSG : un message par palier
BOITE_TEST = 0x0215FC60         # overlay 0 : 1 Aquila, 2 Corvus, 0 sinon
BOITE_DRAPEAU = 0x02160FA8      # overlay 0 : (sl, masque) leve un drapeau du rejeu
BOITE_PREP = 0x021DBE10         # overlay 25 : prepare le rejeu du tour (remet le tas a zero)
BOITE_TAS = 0x021E8A54          # overlay 25 : le tas du rejeu, nul avant la preparation
TAS_RAZ = 0x02032698            # (tas) le remet a zero, premier geste de BOITE_PREP
AQUILA_MSG = 0x1EE
COPIE = 0x148                   # [acteur+0x148] : sa fiche de combat
TOURS_BITS = 8                  # +0x10 bits 8-10 : valeur 2 = une action de plus, 3 = deux

# LE CHARME VISIBLE (joueur, 01/11 soir : « nom en bleu », « les etoiles,
# mais en bleu »). Ecran du bas, mesure a froid (research §113.9) :
#   * le tour est COMPILE d'un coup a son debut, puis rejoue a l'ecran : le
#     compteur de decisions (etat+0) est deja retombe quand l'action charmee
#     se montre. L'affichage a donc son propre octet par membre (etat+16),
#     pose avec le charme (G_POSE), efface a l'ouverture d'un menu si le
#     compteur est a 0 (G_MENU) ;
#   * la ligne d'un membre (nom, niveau, PV, PM) est en sprites ; leur palette
#     OBJ est la « couleur » rendue par `0x02170C7C` (overlay 0, r0 = fiche
#     d'affichage de 0x448 o, +8 PV max, +0xC PV, +0x4C id) : 6 mort, 5 sous
#     8 %, 4 sous 25 %, 0 sinon. G_COULEUR rend 2 pour un charme vivant et
#     ecrit une palette bleue dans la rangee 2 (jamais employee dans les cinq
#     etats de combat releves : 0, 3-7, 11, 13) ;
#   * l'icone de statut vient de la COPIE des statuts dans la fiche
#     d'affichage (+0x28). La synchro `0x02174550` ne tourne qu'au menu
#     (G_STATUT) ; `0x021706B8`, lue pour chaque membre une image sur deux au
#     menu comme au rejeu, passe par G_PANNEAU : la copie porte 0x20 (la
#     confusion : etoiles) pour un charme vivant. Le vrai statut ne bouge pas ;
#   * les etoiles sont en palette OBJ 13, indices 3-8 (jaunes). Pendant le
#     combat de Zenus, ces six couleurs sont bleues tant qu'un charme vivant
#     existe, jaunes (vanilla) sinon.
# L'EFFACE HORS DU COMBAT (joueur, 01/11 : « B »). Mesure a froid (research
# §113.9). Retirer les drapeaux de l'acteur (0x80, 0x100) GELE, deux fois sur
# deux, a des endroits differents : ces tests sont partout et le code suppose
# l'acteur present (`0x02010098` et `0x0208AA8C` lisent un pointeur nul). On
# garde donc l'acteur, mort, et on l'efface de ce qui le montre ou le vise :
#   * la barre : objet d'interface O = [0x02184290] ; O+0x958 = fiches de 0x448 o
#     par id, fiche+0x4C = id (< 0 : sautee par toutes les boucles) ; O+0x6C
#     = les 4 ids dans l'ordre des barres, O+0x70 = pareil avec -1 pour
#     un absent, O+0x79 = nombre de barres. L'interface se recale seule, et le
#     curseur des cibles alliees ne le propose plus. RETIRE, a la synchro du
#     menu (G_STATUT) : la barre reste rouge pendant le rejeu de sa mort ;
#   * tout effet qui le viserait : l'appel unique des effets, overlay 24
#     `0x021EC92C` (blx ip, r2 = cible) rend 0 sans rien faire (G_APPLI). Le
#     coup du neant passe : la marque n'est posee que dans G_DEGATS, apres ;
#   * l'IA : une action sur lui devient Attaque sur Zenus (G_B).
O_PTR = 0x02184290
O_FICHES = 0x958
O_LISTE = 0x6C
O_LISTE2 = 0x70
O_BARRES = 0x79
FICHE_TAILLE = 0x448
APPLI = 0x021EC92C              # appel de l'effet, overlay 24
COULEUR = 0x02170C7C            # couleur de la ligne d'un membre, overlay 0
STATUT = 0x02174558             # synchro des statuts (menu)
PANNEAU = 0x021706B8            # lecture de la copie, chaque image
PAL_TEXTE = 2                   # rangee OBJ du moteur B pour la ligne bleue
PAL_OBJ_B = 0x05000600
PAL_ETOILES = PAL_OBJ_B + 13 * 32 + 3 * 2   # indices 3-8 de la rangee 13


def _bgr(rvb):
    return ((rvb >> 19) & 31) | (((rvb >> 11) & 31) << 5) | (((rvb >> 3) & 31) << 10)


# rangee 0 (texte blanc) avec la rampe 3-7 et l'indice 15 (les glyphes) bleus
TEXTE_BLEU = (0xF800F8, 0x303030, 0x505050, 0x3060C0, 0x3468C8, 0x3870D0,
              0x4080E0, 0x4890F8, 0x000000, 0xC0C0C0, 0x000000, 0x000000,
              0x888888, 0x000000, 0xE0E0E0, 0x4890F8)
ETOILES_JAUNES = (0x201800, 0x402800, 0x503800, 0xA87000, 0xF8B000, 0xF8C850)
ETOILES_BLEUES = (0x001820, 0x002840, 0x003850, 0x0070A8, 0x00B0F8, 0x50C8F8)
SORTIR_OBJETS = 0x021B6BB8      # (id) objets portes -> sac
SORTIR_GROUPE = 0x021B6D60      # (id, fiche 572 o) -> fiche, hors du groupe
SAUVE = 0x02010838              # (gestionnaire) -> sauvegarde (sacs, Carre)
SAC_EQUIPEMENT = 0x0207C388     # (sauvegarde+0x1D4, objet, n, categorie)
HEROS = 0x3AC                   # [gestionnaire+0x3AC] = id du heros
# (emplacement de la fiche +0x160, categorie) : tables des adieux de Tulipe
EQUIPEMENT = ((0, 2), (1, 3), (4, 5), (5, 6), (6, 4), (7, 0), (8, 1), (9, 7))

# (overlay, site, instruction d'origine, etiquette de la greffe, bl ou b)
SITES = (
    (26, 0x021DCDC8, "bl #0x21dce1c", "g_menu", "bl"),
    (24, 0x021F9078, "and r4, r0, #0xff", "g_pre", "bl"),
    (24, 0x021F8F6C, "and r5, r0, #0xff", "g_disp", "bl"),
    (24, 0x021F9020, "add sp, sp, #0x38", "g_b", "b"),
    (0, 0x02157C24, "bl #0x21543f4", "g_pose", "bl"),
    (0, CIBLES, "push {r3, r4, r5, r6, r7, r8, sb, lr}", "g_cible", "b"),
    (0, DEGATS, "push {r4, r5, r6, r7, r8, sb, sl, lr}", "g_degats", "b"),
    (24, EFFET, "push {r4, r5, r6, r7, r8, sb, sl, fp, lr}", "g_effet", "b"),
    (0, COULEUR, "push {r4, r5, r6, lr}", "g_couleur", "b"),
    (0, STATUT, "ldrne r2, [r2, #0x14]", "g_statut", "blne"),
    (0, PANNEAU, "ldr r2, [r7, #0x28]", "g_panneau", "bl"),
    (24, APPLI, "blx ip", "g_appli", "bl"),
    (25, 0x021DB09C, "cmp r0, #1", "g_eac", "bl"),
    (25, 0x021DB0AC, "bl #0x215fc60", "g_bx0", "bl"),
    (25, 0x021DB1C4, "bl #0x21dbe10", "g_prep", "bl"),
    (25, 0x021DB0EC, "cmp r0, #1", "g_bx1", "bl"),
    (25, 0x021DB18C, "ldrh r0, [r8, #0x20]", "g_bx3", "bl"),
    (25, 0x021DB238, "bl #0x21e8a54", "g_tas", "bl"),
    (25, 0x021DB260, "bl #0x215fc60", "g_bx2", "bl"),
    (25, 0x021DB26C, "ldr r1, [pc, #0x1d8]", "g_r1", "bl"),
    (24, 0x021DB3EC, "cmp r0, #0x21", "g_soin", "bl"),
    (0, ZONE, "cmp r2, #1", "g_zone", "b"),
)
# l'ARM9 : l'entree OP_EFFACER de la table de sauts
SITE_ARM9 = (SITE_EFFACER, "b #0x206f9f4", "g_effacer", "b")

# L'OVERLAY 11 AU DEBUT DE CHAQUE COMBAT (ZER-119, 07/11/2026). La greffe vit
# derriere l'overlay 11, mais la place 7-14 n'est pas toujours a lui : la
# creation du personnage y charge l'overlay 9 (ovl21 0x0218B618) et le terrain
# du prologue demarre SANS recharger le 11 ; le recrutement chez Tulipe
# (ovl3), la fenetre de Stella (8), le bestiaire (14) font de meme. Les sites
# du combat sautaient alors dans le code d'un autre overlay : gel au premier
# combat de toute partie neuve (PC 0xFFFF0108). Mesure par guet du chargeur
# (0x020A1950) sur une partie neuve vanilla : le combat empile l'overlay 0 par
# 0x020A1E08 (image 12737), place 7-14 = 9 ; table des overlays charges en ITCM
# 0x01FFD364 (un octet par place).
# CORRECTIF : la fonction d'empilement 0x020A1E08 est reecrite EN PLACE (aucune
# place neuve) : quand l'overlay empile est le 0 (le combat, le seul de la place
# 0-6 a n'etre charge qu'en combat, research §113), elle charge aussi le 11 par
# le chargeur du jeu, qui ne fait rien s'il est deja la (cas de toutes les
# parties chargees). La place vient de l'assertion de debordement de la pile
# (`cmp #8 ; blo ; bl 0x020C9BF0`, jamais atteinte) et d'un `ldrb` redondant ;
# les trois litteraux restent a leurs adresses. Aucune reference statique a
# l'interieur de la fonction (`zone_libre.py 0x020A1E0C 0x58`).
EMPILER = 0x020A1E08
EMPILER_ORIGINE = bytes.fromhex(
    "10402de9" "44109fe5" "0040a0e1" "0000d1e5" "080050e3" "0000003a" "729f00eb"
    "070054e3" "1080bd28" "28009fe5" "d40090e1" "c5feffeb" "18009fe5" "1c109fe5"
    "0020d0e5" "0240c1e7" "0010d0e5" "011081e2" "0010c0e5" "1080bde8"
    "a49d1002" "62190f02" "ae9d1002")
CHARGER = 0x020A1950            # chargeur synchrone d'overlay (r0 = id)
OVL_COMBAT = 0
EMPILER_LITTERAUX = (0x02109DA4, 0x020F1962, 0x02109DAE)   # compte, table, pile


def _empiler():
    """Les 92 octets de 0x020A1E08 : 20 instructions puis les 3 litteraux d'origine."""
    from patch_hasard import assembler
    lignes = [
        "push {r3, r4, r5, lr}",
        "mov r4, r0",
        "cmp r4, #7",
        "pophs {r3, r4, r5, pc}",
        "ldr r0, [pc, #{L1}]",           # table des ecrans
        "ldrsb r5, [r0, r4]",            # r5 = l'overlay empile
        "mov r0, r5",
        "bl #%d" % CHARGER,
        "cmp r5, #%d" % OVL_COMBAT,
        "moveq r0, #%d" % OVL,
        "bleq #%d" % CHARGER,            # le combat : l'overlay 11 aussi
        "ldr r0, [pc, #{L0}]",           # compte de la pile
        "ldr r1, [pc, #{L2}]",           # la pile
        "ldrb r2, [r0]",
        "strb r4, [r1, r2]",
        "add r2, r2, #1",
        "strb r2, [r0]",
        "pop {r3, r4, r5, pc}",
        "mov r0, r0",
        "mov r0, r0",
    ]
    b = assembler(lignes, EMPILER, EMPILER_LITTERAUX)
    if len(b) != len(EMPILER_ORIGINE) or b[80:] != EMPILER_ORIGINE[80:]:
        raise SystemExit("empilement : litteraux deplaces")
    return b


def _essai(lignes):
    """ZENUS_ESSAI : 999 PV a chaque menu, 999 a chaque coup porte a un monstre."""
    out = list(lignes)
    i = out.index("g_menu:") + 2
    pv = (["ldrh ip, [r1, #4]", "strh ip, [r1]"] if ESSAI_VRAIS_PV else
          ["mov ip, #%d" % (ESSAI_VAL & 0xFF00), "orr ip, ip, #%d" % (ESSAI_VAL & 0xFF),
           "strh ip, [r1, #4]", "strh ip, [r1]"])
    out[i:i] = ["ldr r1, [r0, #0x138]", "cmp r1, #0", "beq #{@essai_pv}", "ldrh r2, [r1]",
                "cmp r2, #0", "beq #{@essai_pv}"] + pv + ["essai_pv:"]
    garde = ["ldr ip, [pc, #{L3}]", "ldrb ip, [ip]", "tst ip, #%d" % VICTIME_MASQUE] if ESSAI_APRES_NEANT else []
    i = out.index("g_degats:") + 1
    out[i:i] = (garde + ["beq #{@essai_deg}"] if garde else []) + [
                "cmp r1, #0xc0", "bhs #{@essai_deg}", "cmp r2, #0xc0", "blo #{@essai_deg}",
                "cmp r3, #0", "movgt r3, #%d" % (ESSAI_VAL & 0xFF00),
                "orrgt r3, r3, #%d" % (ESSAI_VAL & 0xFF), "essai_deg:"]
    i = out.index("g_effet:") + 1
    out[i:i] = (garde + ["beq #{@essai_eff}"] if garde else []) + [
                "cmp r1, #0xc0", "bhs #{@essai_eff}", "cmp r2, #0xc0", "blo #{@essai_eff}",
                "ldr ip, [sp]", "cmp ip, #0", "ble #{@essai_eff}",
                "mov ip, #%d" % (ESSAI_VAL & 0xFF00), "orr ip, ip, #%d" % (ESSAI_VAL & 0xFF),
                "str ip, [sp]", "str ip, [sp, #0x54]", "essai_eff:"]
    return out


def greffe(adr, action):
    """Le code, puis ses litteraux, puis l'etat (4 octets). Rend (octets,
    etiquettes)."""
    from patch_hasard import assembler
    lignes = [
        # ---- VIVANT : r0 = id exclu (-1 : aucun), r1 = 1 pour exclure aussi
        # le heros ([gestionnaire+0x3AC]) -> r0 = id d'un membre vivant tire
        # au hasard parmi les autres, -1 s'il n'y en a pas. Detruit r1-r3, ip.
        "vivant:",
        "push {r4, r5, r6, r7, lr}",
        "mov r5, r0",
        "mvn r4, #0",
        "cmp r1, #0",
        "beq #{@viv_tire}",
        "bl #%d" % MGR,
        "ldr r4, [r0, #%d]" % HEROS,
        "viv_tire:",
        "mov r0, #4",
        "bl #%d" % RAND_BELOW,
        "mov r7, r0",                       # premier id essaye : 0 a 3
        "mov r6, #4",
        "viv_boucle:",
        "cmp r7, r4",
        "beq #{@viv_suivant}",              # le heros, si exclu
        "cmp r7, r5",
        "beq #{@viv_suivant}",              # l'id exclu
        "bl #%d" % MGR,
        "mov r1, r7",
        "bl #%d" % ACTEUR,
        "cmp r0, #0",
        "beq #{@viv_suivant}",
        "ldr r1, [r0, #0x138]",
        "cmp r1, #0",
        "ldrhne r1, [r1]",
        "cmpne r1, #0",
        "movne r0, r7",
        "popne {r4, r5, r6, r7, pc}",
        "viv_suivant:",
        "add r7, r7, #1",
        "and r7, r7, #3",
        "subs r6, r6, #1",
        "bne #{@viv_boucle}",
        "mvn r0, #0",
        "pop {r4, r5, r6, r7, pc}",
        # ---- PARADIN : r0 = fiche de Zenus ([acteur+0x138]) -> r0 = id du paladin qui le retient
        # (Paradin, coup de grace 0x201), -1 sinon. Le test de la cible unique des monstres (overlay 0
        # `0x02154F30`, research §113.17) : fiche +0x18 bit 0x1000, paladin en +0x2E, vivant (+0x14
        # bit 0 nul), sans +0x18 bit 0x2000. Detruit r1-r3, ip.
        "paradin:",
        "push {r4, lr}",
        "ldr r1, [r0, #0x18]",
        "tst r1, #0x1000",
        "beq #{@pa_non}",
        "ldrsh r4, [r0, #0x2e]",
        "bl #%d" % MGR,
        "mov r1, r4",
        "bl #%d" % ACTEUR,
        "cmp r0, #0",
        "beq #{@pa_non}",
        "ldr r0, [r0, #0x138]",
        "cmp r0, #0",
        "beq #{@pa_non}",
        "ldr r1, [r0, #0x14]",
        "tst r1, #1",
        "bne #{@pa_non}",
        "ldr r1, [r0, #0x18]",
        "tst r1, #0x2000",
        "bne #{@pa_non}",
        "mov r0, r4",
        "pop {r4, pc}",
        "pa_non:",
        "mvn r0, #0",
        "pop {r4, pc}",
        # ---- CH : r0 = index -> r0 = decisions de charme restantes (0 si
        # aucune, ou si Zenus n'est pas l'acteur 0xC0 : l'etat s'efface).
        # Detruit r1-r3, ip.
        "ch:",
        "push {r4, lr}",
        "ldr r4, [pc, #{L0}]",              # ETAT
        "add r4, r4, r0",
        "ldrb r0, [r4]",
        "cmp r0, #0",
        "popeq {r4, pc}",
        "bl #%d" % MGR,
        "mov r1, #0xc0",
        "bl #%d" % ACTEUR,
        "cmp r0, #0",
        "ldrhne r0, [r0, #2]",
        "cmp r0, #%d" % ESPECE,
        "ldrbeq r0, [r4]",
        "movne r0, #0",
        "strbne r0, [r4]",
        "pop {r4, pc}",
        # ---- G_MENU : r0 = acteur du membre sb ; rend r0 = 1 pour le sauter.
        "g_menu:",
        "push {r0, lr}",
        "bl #{@zenus}",                     # r0 = son acteur, 0 si ce n'est pas Zenus
        "ldr r2, [pc, #{L0}]",
        "mov r3, #0xff",                    # chaque menu : plus de neant en attente
        "strb r3, [r2, #4]",
        "mov r3, #0",
        "strh r3, [r2, #28]",               # ni d'action deja prise ce tour
        "strb r3, [r2, #56]",               # les comptes d'actions repartent
        "strb r3, [r2, #57]",
        "strb r3, [r2, #58]",
        "strb r3, [r2, #59]",
        "strb r3, [r2, #60]",
        "strb r3, [r2, #61]",
        "strb r3, [r2, #63]",
        "ldrb r1, [r2, #31]",
        "bic r1, r1, #2",
        "strb r1, [r2, #31]",
        "ldrb r1, [r2, #30]",               # les entrees gardees
        "strb r3, [r2, #30]",
        "cmp r0, #0",
        "beq #{@menu_paliers}",
        "menu_rend:",
        "cmp r1, #0",
        "beq #{@menu_paliers}",
        "sub r1, r1, #1",
        "add r3, r2, r1, lsl #3",
        "ldr ip, [r3, #32]",
        "ldrh lr, [r3, #36]",
        "strh lr, [ip]",
        "ldrb lr, [r3, #38]",
        "strb lr, [ip, #9]",
        "b #{@menu_rend}",
        "menu_paliers:",
        "cmp r0, #0",                       # Zenus, au menu du heros
        "beq #{@menu_r0}",
        "cmp sb, #0",
        "bleq #{@paliers}",
        "menu_r0:",
        "ldr r0, [sp]",                     # r0 = l'acteur du membre (la suite le lit)
        "menu_suite:",
        "ldr r2, [pc, #{L0}]",              # compteur a 0 : plus d'affichage
        "mov r1, #4",
        "menu_aff:",
        "sub r1, r1, #1",
        "ldrb r3, [r2, r1]",
        "cmp r3, #0",
        "addeq r3, r2, #16",
        "moveq ip, #0",
        "strbeq ip, [r3, r1]",
        "cmp r1, #0",
        "bne #{@menu_aff}",
        "ldr r1, [r0, #0x19c]",
        "cmp r1, #0",
        "ldrne r1, [r1, #8]",               # ses tours joues dans ce combat
        "cmpne r1, #0",
        "bne #{@menu_ch}",
        "ldr r2, [pc, #{L0}]",              # premier tour : etat efface
        "mov r3, #0",
        "strb r3, [r2, sb]",
        "cmp sb, #0",                       # premier menu du heros : tout repart
        "strheq r3, [r2, #26]",
        "strbeq r3, [r2, #31]",
        "pop {r0, lr}",
        "b #%d" % EST_ENDORMI,
        "menu_ch:",
        "mov r0, sb",
        "bl #{@ch}",
        "cmp r0, #0",
        "pop {r0, lr}",
        "movne r0, #1",
        "bxne lr",
        "b #%d" % EST_ENDORMI,
        # ---- G_PRE (r8 = index) et G_DISP (r7 = index) : la tactique lue
        # devient 0 (« Sans pitie ») si charme. Tout le reste est preserve.
        "g_pre:",
        "push {r0, r1, r2, r3, ip, lr}",
        "and r4, r0, #0xff",
        "mov r0, r8",
        "bl #{@ch}",
        "cmp r0, #0",
        "movne r4, #0",
        "pop {r0, r1, r2, r3, ip, pc}",
        "g_disp:",
        "push {r0, r1, r2, r3, ip, lr}",
        "and r5, r0, #0xff",
        "mov r0, r7",
        "bl #{@ch}",
        "cmp r0, #0",
        "movne r5, #0",
        "pop {r0, r1, r2, r3, ip, pc}",
        # ---- G_B : fin du repartiteur (r4 acteur, r6 file, r7 index).
        "g_b:",
        "add sp, sp, #0x38",
        "ldr r5, [r4, #0x19c]",             # une action sur l'efface : Attaque
        "cmp r5, #0",                       # sur Zenus
        "beq #{@b_ch}",
        "bl #{@victime}",
        "ldrb r1, [r5, #2]",
        "cmp r0, r1",
        "bne #{@b_ch}",
        "mov r0, #1",
        "strh r0, [r5]",
        "strh r0, [r6]",
        "mov r0, #0xc0",
        "strb r0, [r5, #2]",
        "mov r0, #0",
        "strb r0, [r5, #3]",
        "b_ch:",
        "mov r0, r7",
        "bl #{@ch}",
        "cmp r0, #0",
        "beq #{@b_fin}",
        "ldr r1, [pc, #{L0}]",
        "sub r0, r0, #1",
        "strb r0, [r1, r7]",                # une decision de charme consommee
        "ldr r5, [r4, #0x19c]",
        "cmp r5, #0",
        "beq #{@b_fin}",
    ] + ([] if CHARME_ACTION is None else [
        "mov r0, #%d" % (CHARME_ACTION & 0xFF00), "orr r0, r0, #%d" % (CHARME_ACTION & 0xFF),
        "strh r0, [r5]", "strh r0, [r6]"]) + [
        "bl #%d" % FICHES,                  # sa fiche : camp et portee
        "ldrsh r1, [r5]",
        "bl #%d" % FICHE_ACTION,
        "movs r1, r0",
        "mov r8, #1",                       # par defaut : Attaque
        "beq #{@b_cible}",
        "ldr r0, [r1, #8]",
        "lsr r0, r0, #8",
        "and r0, r0, #3",
        "cmp r0, #1",                       # l'autre camp
        "bne #{@b_cible}",
        "ldr r0, [r1, #0x14]",
        "lsr r0, r0, #28",
        "sub r0, r0, #2",
        "cmp r0, #3",                       # portee 2 a 5 : il garde son action
        "ldrhls r8, [r5]",
        "b_cible:",
        "mov r0, r7",                       # un autre membre VIVANT (le
        "mov r1, #0",                       # heros compris) ; personne :
        "bl #{@vivant}",                    # il agit comme il l'a choisi
        "cmp r0, #0",
        "blt #{@b_fin}",
        "strh r8, [r5]",
        "strb r0, [r5, #2]",
        "mov r0, #0",
        "strb r0, [r5, #3]",                # groupe 0 : l'equipe
        "strh r8, [r6]",
        "ldr r1, [pc, #{L0}]",              # de zone, G_ZONE prend toute l'equipe
        "add r0, r7, #1",
        "strb r0, [r1, #63]",
        "b_fin:",
        "pop {r3, r4, r5, r6, r7, r8, sb, pc}",
        # ---- G_POSE : r0 = acteur, r7 = id, sb = entree de la file.
        "g_pose:",
        "ldr ip, [pc, #{L0}]",
        "ldrb r1, [ip, #56]",
        "add r1, r1, #1",
        "strb r1, [ip, #56]",
        "cmp r7, #0xc0",
        "blo #{@pose_orig}",
        "push {r0, r4, r5, r6, r7, lr}",
        "mov r6, r0",
        "bl #{@neant}",
        "ldrh r1, [sb]",
        "ldr r2, [pc, #{L1}]",              # l'action du charme
        "cmp r1, r2",
        "bne #{@pose_sortie}",
        # Retenu par Paradin (coup de grace du paladin) : le charme se lance sur le paladin, sa
        # seule cible (G_CIBLE ; sans cible notee, il visait Zenus lui-meme), et il echoue
        # (« Mais rien ne se passe ») ; personne n'est charme (joueur, 06/11, choix A).
        "ldr r0, [r6, #0x138]",
        "cmp r0, #0",
        "beq #{@pose_sortie}",
        "bl #{@paradin}",
        "cmp r0, #0",
        "blt #{@pose_tire}",
        "add r0, r0, #1",
        "ldr r1, [pc, #{L0}]",
        "strb r0, [r1, #59]",
        "b #{@pose_sortie}",
        "pose_tire:",
        "mvn r0, #0",
        "mov r1, #1",                       # un compagnon vivant, jamais le heros
        "bl #{@vivant}",
        "cmp r0, #0",
        "blt #{@pose_sortie}",
        "mov r4, r0",
        "mov r0, #2",
        "bl #%d" % RAND_BELOW,
        "add r0, r0, #1",                   # 1 ou 2 decisions
        "ldr r1, [pc, #{L0}]",
        "strb r0, [r1, r4]",
        "add r0, r4, #1",
        "strb r0, [r1, #59]",               # sa cible, pour G_CIBLE
        "strb r0, [r1, #62]",               # le bleu, au rejeu de cette action
        "ldrb r0, [r1, #56]",
        "strb r0, [r1, #60]",
        "pose_sortie:",
        "pop {r0, r4, r5, r6, r7, lr}",
        "pose_orig:",
        "b #%d" % EST_CONFUS,
        # ---- NEANT : r6 = acteur qui decide (id >= 0xC0), sb = son entree de file. Zenus
        # a SEUIL PV ou moins, pas de victime marquee, pas de neant ce tour, quelqu'un a
        # effacer : NEANT. Sinon une action de TABLE. L'entree, son action et son +9 sont
        # gardes pour le menu suivant ; le +9 passe a 0, comme le jeu pour la confusion
        # (research §113.8). Detruit r0-r5, r7 (sauves par G_POSE).
        "neant:",
        "push {lr}",
        "ldrh r0, [r6, #2]",
        "cmp r0, #%d" % ESPECE,
        "bne #{@neant_fin}",
        "ldr r5, [r6, #0x138]",
        "cmp r5, #0",
        "beq #{@neant_fin}",
        "ldrh r0, [r5]",
        "cmp r0, #0",
        "beq #{@neant_fin}",
        "mov ip, #%d" % (SEUIL & 0xF00),    # 3 500 n'est pas un immediat ARM
        "orr ip, ip, #%d" % (SEUIL & 0xFF),
        "cmp r0, ip",
        "bhi #{@choisir}",
        "ldr r1, [pc, #{L3}]",
        "ldrb r1, [r1]",
        "tst r1, #%d" % VICTIME_MASQUE,
        "bne #{@choisir}",
        "ldr r1, [pc, #{L0}]",
        "ldrb r1, [r1, #31]",
        "tst r1, #2",
        "bne #{@choisir}",
        "mvn r0, #0",
        "mov r1, #1",
        "bl #{@vivant}",
        "cmp r0, #0",
        "blt #{@choisir}",
        "ldr r1, [pc, #{L0}]",
        "ldrb r0, [r1, #31]",
        "orr r0, r0, #2",
        "strb r0, [r1, #31]",
        "ldr r4, [pc, #{L2}]",
        "b #{@poser}",
        # Somme des poids des actions permises, tirage, puis la tranche ou il tombe.
        "choisir:",
        "mov r4, #0",
        "mov r7, #0",
        "ch_somme:",
        "bl #{@permise}",
        "add r7, r7, r0",
        "add r4, r4, #1",
        "cmp r4, #%d" % len(TABLE),
        "blo #{@ch_somme}",
        "cmp r7, #0",
        "beq #{@neant_fin}",
        "mov r0, r7",
        "bl #%d" % RAND_BELOW,
        "mov r7, r0",
        "mov r4, #0",
        "ch_cherche:",
        "bl #{@permise}",
        "cmp r7, r0",
        "blo #{@ch_pris}",
        "sub r7, r7, r0",
        "add r4, r4, #1",
        "cmp r4, #%d" % len(TABLE),
        "blo #{@ch_cherche}",
        "b #{@neant_fin}",
        "ch_pris:",
        "ldr r3, [pc, #{L0}]",
        "ldrh r2, [r3, #28]",
        "mov ip, #1",
        "orr r2, r2, ip, lsl r4",
        "strh r2, [r3, #28]",
        "ldr r3, [pc, #{L12}]",
        "add r3, r3, r4, lsl #1",
        "ldrh r4, [r3]",
        "ldr r1, [pc, #{L16}]",
        "cmp r4, r1",
        "ldr r3, [pc, #{L0}]",
        "ldrbeq r2, [r3, #31]",
        "orreq r2, r2, #1",                 # le soin : une fois par combat
        "strbeq r2, [r3, #31]",
        "b #{@poser}",
        "poser:",                           # r4 = l'action
        "ldr r1, [pc, #{L0}]",
        "ldrb r2, [r1, #30]",
        "cmp r2, #3",
        "bhs #{@neant_fin}",
        "add r3, r1, r2, lsl #3",
        "str sb, [r3, #32]",
        "ldrh r0, [sb]",
        "strh r0, [r3, #36]",
        "ldrb r0, [sb, #9]",
        "strb r0, [r3, #38]",
        "add r2, r2, #1",
        "strb r2, [r1, #30]",
        "strh r4, [sb]",
        "mov r0, #0",
        "strb r0, [sb, #9]",
        "neant_fin:",
        "pop {pc}",
        # ---- PERMISE : r4 = rang dans TABLE, r5 = la fiche de Zenus -> r0 = son poids, 0 si exclue :
        # deja prise ce tour ; le charme si quelqu'un l'est ou s'il n'y a personne a charmer ; le soin
        # deja fait, ou au-dessus de 75 % de ses PV ; le sort bleu si attaque, defense et agilite sont
        # toutes a 2 crans (fiche+0x58 bits 0-2, 3-5, 6-8, lus a l'overlay 24 0x021FDB14). Garde r4-r7.
        "permise:",
        "push {lr}",
        "ldr r3, [pc, #{L0}]",
        "ldrh r2, [r3, #28]",
        "mov ip, #1",
        "tst r2, ip, lsl r4",
        "bne #{@pe_non}",
        "ldr r3, [pc, #{L12}]",
        "add r3, r3, r4, lsl #1",
        "ldrh r0, [r3]",
        "ldr r1, [pc, #{L1}]",
        "cmp r0, r1",
        "bne #{@pe_soin}",
        "ldr r3, [pc, #{L0}]",
        "ldr r2, [r3]",
        "cmp r2, #0",
        "bne #{@pe_non}",
        "mvn r0, #0",
        "mov r1, #1",
        "bl #{@vivant}",
        "cmp r0, #0",
        "blt #{@pe_non}",
        "b #{@pe_oui}",
        "pe_soin:",
        "ldr r1, [pc, #{L16}]",
        "cmp r0, r1",
        "bne #{@pe_force}",
        "ldr r3, [pc, #{L0}]",
        "ldrb r2, [r3, #31]",
        "tst r2, #1",
        "bne #{@pe_non}",
        "ldrh r1, [r5]",                    # PV x 4 <= PV max x 3
        "ldrh r2, [r5, #4]",
        "mov r1, r1, lsl #2",
        "add r2, r2, r2, lsl #1",
        "cmp r1, r2",
        "bhi #{@pe_non}",
        "b #{@pe_oui}",
        "pe_force:",
        "mov r1, #%d" % (BLEU & 0xF00),
        "orr r1, r1, #%d" % (BLEU & 0xFF),
        "cmp r0, r1",
        "bne #{@pe_oui}",
        "ldr r1, [r5, #0x58]",
        "lsl r2, r1, #29",
        "asr r2, r2, #29",
        "cmp r2, #2",
        "blt #{@pe_oui}",
        "lsl r2, r1, #26",
        "asr r2, r2, #29",
        "cmp r2, #2",
        "blt #{@pe_oui}",
        "lsl r2, r1, #23",
        "asr r2, r2, #29",
        "cmp r2, #2",
        "bge #{@pe_non}",
        "pe_oui:",
        "ldr r3, [pc, #{L17}]",
        "ldrb r0, [r3, r4]",
        "pop {pc}",
        "pe_non:",
        "mov r0, #0",
        "pop {pc}",
        # ---- G_SOIN : `cmp r0, #0x21`, suivi de `cmpne r0, #0x310` : Z a 1 aussi pour son soin.
        "g_soin:",
        "ldr ip, [pc, #{L16}]",
        "cmp r0, ip",
        "bxeq lr",
        "cmp r0, #0x21",
        "bx lr",
        # ---- ZENUS : r0 = l'acteur 0xC0 s'il est Zenus, sinon 0. Detruit r1-r3, ip.
        "zenus:",
        "push {lr}",
        "bl #%d" % MGR,
        "mov r1, #0xc0",
        "bl #%d" % ACTEUR,
        "cmp r0, #0",
        "popeq {pc}",
        "ldrh r1, [r0, #2]",
        "cmp r1, #%d" % ESPECE,
        "movne r0, #0",
        "pop {pc}",
        # ---- PALIERS : r0 = acteur de Zenus, au menu du heros. Le palier le plus bas
        # franchi et pas encore dit va en +27, ceux d'avant passent pour dits. Sous
        # PCT_TROIS %, trois actions par tour. Garde r4-r7 ; detruit r0-r3, ip.
        "paliers:",
        "push {r4, r5, r6, r7, lr}",
        "ldr r5, [r0, #0x138]",
        "ldr r4, [r0, #%d]" % COPIE,
        "cmp r5, #0",
        "cmpne r4, #0",
        "popeq {r4, r5, r6, r7, pc}",
        "ldrh r2, [r5]",
        "cmp r2, #0",
        "popeq {r4, r5, r6, r7, pc}",
        "mov r3, #100",
        "mul r6, r3, r2",                   # PV x 100
        "ldrh r7, [r5, #4]",                # PV max
        "mov r1, #%d" % PCT_TROIS,
        "mul r3, r1, r7",
        "cmp r6, r3",
        "ldrls r1, [r4, #0x10]",
        "bicls r1, r1, #%d" % (7 << TOURS_BITS),
        "orrls r1, r1, #%d" % (3 << TOURS_BITS),
        "strls r1, [r4, #0x10]",
        "ldr r4, [pc, #{L0}]",
        "ldr r5, [pc, #{L15}]",
        "mov r2, #0",
        "pal_boucle:",
        "ldrb r1, [r5, r2]",
        "mul r3, r1, r7",
        "cmp r6, r3",
        "bhi #{@pal_fin}",
        "mov ip, #1",
        "ldrb r1, [r4, #26]",
        "tst r1, ip, lsl r2",
        "orreq r1, r1, ip, lsl r2",
        "strbeq r1, [r4, #26]",
        "addeq r1, r2, #1",
        "strbeq r1, [r4, #27]",
        "add r2, r2, #1",
        "cmp r2, #%d" % len(PALIERS),
        "blt #{@pal_boucle}",
        "pal_fin:",
        "pop {r4, r5, r6, r7, pc}",
        # ---- LA BOITE D'AQUILA, overlay 25, debut d'un rejeu (research §113.11). Elle passe
        # AVANT la preparation du tour : ouverte apres, l'action preparee ne repart plus
        # (mesure a froid le 05/11, helper+4 occupe a jamais, etat 3, avec ou sans cadrage).
        # G_EAC : `cmp r0, #1` (etat 1 ?). Tant que la fenetre tient (drapeau), le bloc de
        # l'etat 1 ne repasse pas : Z a 0. Fermee, le palier s'efface et l'etat 1 repart.
        "g_eac:",
        "ldr ip, [pc, #{L0}]",
        "ldrb ip, [ip, #25]",
        "cmp ip, #0",
        "beq #{@eac_orig}",
        "add ip, sl, #0x5000",
        "ldr ip, [ip, #0x5f4]",
        "tst ip, #0x1000000",
        "bxne lr",
        "ldr ip, [pc, #{L0}]",
        "push {r1}",
        "mov r1, #0",
        "strb r1, [ip, #25]",
        "ldrb r1, [ip, #58]",
        "sub r1, r1, #1",
        "strb r1, [ip, #58]",
        "pop {r1}",
        "eac_orig:",
        "cmp r0, #1",
        "bx lr",
        # G_PREP : `bl 0x021DBE10` : pas de preparation pendant un palier.
        "g_prep:",
        "ldr ip, [pc, #{L0}]",
        "ldrb ip, [ip, #25]",
        "cmp ip, #0",
        "bxne lr",
        "b #%d" % BOITE_PREP,
        # G_BX0 : le test d'espece ; le palier a dire devient le palier affiche.
        "g_bx0:",
        "push {r4, lr}",
        "bl #%d" % BOITE_TEST,
        "ldr r1, [pc, #{L0}]",
        "ldrb r2, [r1, #58]",
        "add r2, r2, #1",
        "strb r2, [r1, #58]",
        "ldrb r3, [r1, #60]",               # l'action du charme arrive : le bleu
        "cmp r3, #0",
        "beq #{@bx0_mort}",
        "cmp r2, r3",
        "blo #{@bx0_mort}",
        "mov r3, #0",
        "strb r3, [r1, #60]",
        "ldrb r3, [r1, #62]",
        "add r3, r3, r1",
        "mov ip, #1",
        "strb ip, [r3, #15]",               # +16 + (compagnon + 1) - 1
        "bx0_mort:",
        "ldrb r3, [r1, #57]",
        "cmp r3, #0",
        "beq #{@bx0_palier}",
        "cmp r2, r3",
        "blo #{@bx0_palier}",
        "ldrb r3, [r1, #26]",
        "tst r3, #0x10",
        "bne #{@bx0_palier}",
        "orr r3, r3, #0x10",
        "strb r3, [r1, #26]",
        "mov r4, #%d" % (len(PALIERS) + 1),
        "mov r2, #0",
        "strb r2, [r1, #27]",
        "strb r4, [r1, #25]",
        "b #{@bx0_fin}",
        "bx0_palier:",
        "ldrb r4, [r1, #27]",
        "mov r2, #0",
        "strb r2, [r1, #27]",
        "strb r4, [r1, #25]",
        "bx0_fin:",
        "cmp r0, #0",
        "moveq r0, r4",
        "pop {r4, pc}",
        # G_BX1 : `cmp r0, #1` (premier tour ?), suivi de `cmpeq r6, #0xc0` et `bne`. Pendant
        # un palier : jamais le cadrage d'Aquila. Il zoome et bloque le rejeu ensuite (mesure
        # a froid le 05/11, l'equipe n'a plus la main) : Z a 0, on passe a G_BX3.
        "g_bx1:",
        "ldr ip, [pc, #{L0}]",
        "ldrb ip, [ip, #25]",
        "cmp ip, #0",
        "bxne lr",
        "cmp r0, #1",
        "bx lr",
        # G_BX2 : le meme test plus loin : 1 (Aquila) pendant un palier.
        "g_bx2:",
        "ldr ip, [pc, #{L0}]",
        "ldrb ip, [ip, #25]",
        "cmp ip, #0",
        "movne r0, #1",
        "bxne lr",
        "b #%d" % BOITE_TEST,
        # G_BX3 : `ldrh r0, [r8, #0x20]`, le premier acteur. Pendant un palier : r0 non nul
        # (le cas « heros » du jeu, son action retiree, ne vaut pas), le message dans sb et
        # le drapeau qui suspend le rejeu le temps de la fenetre.
        "g_bx3:",
        "ldrh r0, [r8, #0x20]",
        "ldr ip, [pc, #{L0}]",
        "ldrb ip, [ip, #25]",
        "cmp ip, #0",
        "bxeq lr",
        "ldr sb, [pc, #{L13}]",
        "add sb, sb, ip",
        "push {lr}",
        "add r0, sl, #0x30",                # le tas du tour precedent ne sert plus
        "bl #%d" % TAS_RAZ,
        "mov r0, sl",
        "mov r1, #0x1000000",
        "bl #%d" % BOITE_DRAPEAU,
        "pop {lr}",
        "mov r0, #1",
        "bx lr",
        # G_TAS : le tas du chargeur de messages. Avant la preparation, le jeu rend 0 (mesure
        # a froid, 05/11 : texte nul, fenetre jamais ouverte) : le tas du rejeu, sl+0x30.
        "g_tas:",
        "ldr ip, [pc, #{L0}]",
        "ldrb ip, [ip, #25]",
        "cmp ip, #0",
        "addne r0, sl, #0x30",
        "bxne lr",
        "b #%d" % BOITE_TAS,
        # G_R1 : `ldr r1, =0x1EE` : le meme message, une fois charge. r0 garde.
        "g_r1:",
        "ldr ip, [pc, #{L0}]",
        "ldrb ip, [ip, #25]",
        "ldr r1, [pc, #{L14}]",
        "cmp ip, #0",
        "ldrne r1, [pc, #{L13}]",
        "addne r1, r1, ip",
        "bx lr",
        # ---- G_ZONE : constructeur de cibles de l'equipe (overlay 0 `0x021540FC`), la portee
        # calculee (r2 ; r7 camp, sb id de l'acteur, sl contexte, r8 liste, r4 fiche). Le compagnon
        # charme de ce tour, une action de zone sur l'autre camp : tous les membres vivants, lui exclu,
        # comme un groupe de monstres ; la fin du jeu (ordre, effacement de la liste) suit.
        "g_zone:",
        "ldr ip, [pc, #{L0}]",
        "ldrb ip, [ip, #63]",
        "sub ip, ip, #1",
        "cmp ip, sb",
        "cmpeq r7, #1",
        "bne #{@zone_orig}",
        "cmp r2, #3",
        "cmpne r2, #4",
        "bne #{@zone_orig}",
        "mov r0, sl",
        "mov r1, r8",
        "mov r2, #8",
        "mov r3, #1",
        "bl #%d" % LISTE_EQUIPE,
        "mov r1, #0",
        "mov r6, #0",
        "zone_boucle:",
        "cmp r1, r0",
        "bge #{@zone_fin}",
        "lsl r3, r1, #1",
        "ldrh r2, [r8, r3]",
        "add r1, r1, #1",
        "cmp r2, sb",
        "beq #{@zone_boucle}",
        "lsl r3, r6, #1",
        "strh r2, [r8, r3]",
        "add r6, r6, #1",
        "b #{@zone_boucle}",
        "zone_fin:",
        "b #%d" % ZONE_SUITE,
        "zone_orig:",
        "cmp r2, #1",
        "b #%d" % (ZONE + 4),
        # ---- G_CIBLE : entree des cibles d'une action de monstre (r0
        # contexte, r1 id, r2 action, r3 liste). NEANT : une victime tiree
        # AU COUP parmi les vivants (jamais le heros), seule cible ; elle est
        # notee « en attente » (etat+4) pour G_DEGATS. Sinon la fonction du jeu.
        "g_cible:",
        "cmp r1, #0xc0",
        "blo #{@cible_orig}",
        "ldr ip, [pc, #{L1}]",              # le charme : le compagnon choisi, seule cible
        "cmp r2, ip",
        "bne #{@cible_neant}",
        "ldr ip, [pc, #{L0}]",
        "ldrb ip, [ip, #59]",
        "cmp ip, #0",
        "beq #{@cible_orig}",
        "sub ip, ip, #1",
        "strh ip, [r3]",
        "ldr r0, [pc, #{L0}]",
        "mov ip, #0",
        "strb ip, [r0, #59]",
        "mov r0, #1",
        "bx lr",
        "cible_neant:",
        "ldr ip, [pc, #{L2}]",
        "cmp r2, ip",
        "bne #{@cible_orig}",
        # Seulement si la decision de ce tour a pose le neant (+31 bit 1) : le jeu demande
        # aussi les cibles d'une action hors de toute decision (appelant 0x021549F0). Mesure a
        # froid le 05/11 : a 19 687 PV, une victime en attente, et le coup suivant de Zenus
        # faisait 9 999 et l'effacait.
        "ldr ip, [pc, #{L0}]",
        "ldrb ip, [ip, #31]",
        "tst ip, #2",
        "beq #{@cible_orig}",
        "push {r0, r1, r2, r3, lr}",
        "mvn r0, #0",
        "mov r1, #1",
        "bl #{@vivant}",
        "mov ip, r0",
        "pop {r0, r1, r2, r3, lr}",
        "cmp ip, #0",
        "blt #{@cible_orig}",
        "strh ip, [r3]",
        "ldr r0, [pc, #{L0}]",
        "strb ip, [r0, #4]",
        "mov r0, #1",
        "bx lr",
        "cible_orig:",
        "push {r3, r4, r5, r6, r7, r8, sb, lr}",
        "b #%d" % (CIBLES + 4),
        # ---- G_DEGATS : entree de l'application des degats (overlay 0
        # `0x0215A004` : r0 contexte, r1 id de l'attaquant, r2 id de la
        # cible, r3 degats ; tous les effets y passent, coups rates compris
        # avec 0). Un monstre qui frappe la victime en attente : DEGATS_NEANT
        # (la defense n'y peut rien), la victime est MARQUEE (drapeaux
        # 0x1FA-0x1FC), plus rien en attente.
        "g_degats:",
        "cmp r2, #0xc0",                    # sur Zenus : ce coup le tue-t-il ?
        "bne #{@deg_suite}",
        "push {r0, r1, r2, r3, lr}",
        "bl #{@zenus}",
        "cmp r0, #0",
        "beq #{@deg_fatal_fin}",
        "ldr r0, [r0, #0x138]",
        "ldrh r0, [r0]",
        "ldr r3, [sp, #12]",
        "cmp r3, #0",
        "cmpgt r0, #0",
        "ble #{@deg_fatal_fin}",
        "cmp r3, r0",
        "blt #{@deg_fatal_fin}",
        "ldr ip, [pc, #{L0}]",
        "ldrb r1, [ip, #57]",
        "cmp r1, #0",
        "ldrbeq r1, [ip, #56]",
        "strbeq r1, [ip, #57]",
        "deg_fatal_fin:",
        "pop {r0, r1, r2, r3, lr}",
        "deg_suite:",
        "cmp r1, #0xc0",
        "blo #{@deg_orig}",
        "ldr ip, [pc, #{L0}]",
        "ldrb ip, [ip, #4]",
        "cmp ip, r2",
        "bne #{@deg_orig}",
        "push {r0, r1}",
        "ldr r0, [pc, #{L0}]",
        "mov r1, #0xff",
        "strb r1, [r0, #4]",
        "ldr r0, [pc, #{L3}]",
        "ldrb r1, [r0]",
        "bic r1, r1, #%d" % VICTIME_MASQUE,
        "add ip, r2, #1",
        "orr r1, r1, ip, lsl #%d" % VICTIME_DEC,
        "strb r1, [r0]",
        "pop {r0, r1}",
        "mov r3, #%d" % (DEGATS_NEANT & 0xFF00),
        "orr r3, r3, #%d" % (DEGATS_NEANT & 0xFF),
        "deg_orig:",
        "push {r4, r5, r6, r7, r8, sb, sl, lr}",
        "b #%d" % (DEGATS + 4),
        # ---- G_EFFET : entree de l'effet physique (overlay 24, r1
        # attaquant, r2 cible, [sp] degats). Appele par `0x021EC92C` et un
        # monstre qui frappe la victime en attente : les degats ([sp]) et
        # la case de l'appelant que lit le message ([sp+0x54]) valent
        # DEGATS_NEANT. Les registres sont rendus intacts.
        "g_effet:",
        "cmp r1, #0xc0",
        "blo #{@eff_orig}",
        "ldr ip, [pc, #{L5}]",
        "cmp lr, ip",
        "bne #{@eff_orig}",
        "ldr ip, [pc, #{L0}]",
        "ldrb ip, [ip, #4]",
        "cmp ip, r2",
        "bne #{@eff_orig}",
        "mov ip, #%d" % (DEGATS_NEANT & 0xFF00),
        "orr ip, ip, #%d" % (DEGATS_NEANT & 0xFF),
        "str ip, [sp]",
        "str ip, [sp, #0x54]",
        "eff_orig:",
        "push {r4, r5, r6, r7, r8, sb, sl, fp, lr}",
        "b #%d" % (EFFET + 4),
        # ---- CV : r0 = id -> r0 non nul si ce membre s'AFFICHE charme : octet
        # etat+16, Zenus est l'acteur 0xC0 (sinon l'octet s'efface) et le
        # membre est vivant. Detruit r1-r3, ip.
        "cv:",
        "push {r4, lr}",
        "mov r4, r0",
        "ldr r1, [pc, #{L0}]",
        "add r1, r1, r4",
        "ldrb r0, [r1, #16]",
        "cmp r0, #0",
        "popeq {r4, pc}",
        "bl #%d" % MGR,
        "mov r1, #0xc0",
        "bl #%d" % ACTEUR,
        "cmp r0, #0",
        "ldrhne r0, [r0, #2]",
        "cmp r0, #%d" % ESPECE,
        "beq #{@cv_vivant}",
        "ldr r1, [pc, #{L0}]",
        "add r1, r1, r4",
        "mov r0, #0",
        "strb r0, [r1, #16]",
        "pop {r4, pc}",
        "cv_vivant:",
        "bl #%d" % MGR,
        "mov r1, r4",
        "bl #%d" % ACTEUR,
        "cmp r0, #0",
        "ldrne r0, [r0, #0x138]",
        "cmpne r0, #0",
        "ldrhne r0, [r0]",
        "pop {r4, pc}",
        # ---- G_COULEUR : entree de la couleur d'une ligne (r0 = fiche
        # d'affichage, +0x4C l'id). Charme vivant : palette 2, ecrite bleue.
        "g_couleur:",
        "push {r0, lr}",
        "ldr r0, [r0, #0x4c]",
        "cmp r0, #4",
        "bhs #{@coul_orig}",
        "bl #{@cv}",
        "cmp r0, #0",
        "beq #{@coul_orig}",
        "ldr r0, [pc, #{L6}]",              # TEXTE_BLEU
        "ldr r1, [pc, #{L7}]",              # rangee PAL_TEXTE
        "mov r2, #16",
        "coul_copie:",
        "ldrh r3, [r0], #2",
        "strh r3, [r1], #2",
        "subs r2, r2, #1",
        "bne #{@coul_copie}",
        "pop {r0, lr}",
        "mov r0, #%d" % PAL_TEXTE,
        "bx lr",
        "coul_orig:",
        "pop {r0, lr}",
        "push {r4, r5, r6, lr}",
        "b #%d" % (COULEUR + 4),
        # ---- G_STATUT : `ldrne r2, [r2, #0x14]` de la synchro du menu
        # (r6 = id, r0 fiche d'affichage, r1 sa copie). Charme vivant : le
        # 0x20 reste, sinon la synchro l'effacerait. Rend r2 ; r0, r1, r3
        # gardes ; Z a 0 (le `cmpne` qui suit doit s'executer).
        "g_statut:",
        "push {r0, r1, r3, lr}",
        "ldr r2, [r2, #0x14]",
        "push {r2}",
        "cmp r6, #0",
        "bleq #{@retire}",
        "mov r0, r6",
        "bl #{@cv}",
        "pop {r2}",
        "cmp r0, #0",
        "orrne r2, r2, #0x20",
        "pop {r0, r1, r3, lr}",
        "movs ip, #1",
        "bx lr",
        # ---- G_PANNEAU : `ldr r2, [r7, #0x28]` (r7 = fiche d'affichage), une
        # image sur deux par membre. Pour un charme vivant la copie porte
        # 0x20 ; quand il cesse de l'etre, le 0x20 pose par nous s'en va
        # (etat+20). Au membre 0, les etoiles (rangee 13). Rend r2 ; r0, r1,
        # r3 gardes (lr et ip ne vivent pas ici : un `bl` suit).
        "g_panneau:",
        "push {r0, r1, r3, r4, r5, lr}",
        "ldr r4, [r7, #0x4c]",
        "cmp r4, #4",
        "bhs #{@pan_fin}",
        "cmp r4, #0",
        "bne #{@pan_membre}",
        "bl #%d" % MGR,                     # ---- les etoiles, Zenus seulement
        "mov r1, #0xc0",
        "bl #%d" % ACTEUR,
        "cmp r0, #0",
        "beq #{@pan_membre}",
        "ldrh r0, [r0, #2]",
        "cmp r0, #%d" % ESPECE,
        "bne #{@pan_membre}",
        "mov r5, #3",
        "mov r4, #0",
        "pan_boucle:",
        "mov r0, r5",
        "bl #{@cv}",
        "cmp r0, #0",
        "movne r4, #1",
        "subs r5, r5, #1",
        "bpl #{@pan_boucle}",
        "ldr r0, [pc, #{L8}]",              # ETOILES_JAUNES puis BLEUES
        "cmp r4, #0",
        "addne r0, r0, #%d" % (2 * len(ETOILES_JAUNES)),
        "ldr r1, [pc, #{L9}]",              # PAL_ETOILES
        "mov r2, #%d" % len(ETOILES_JAUNES),
        "pan_copie:",
        "ldrh r3, [r0], #2",
        "strh r3, [r1], #2",
        "subs r2, r2, #1",
        "bne #{@pan_copie}",
        "ldr r4, [r7, #0x4c]",
        "pan_membre:",
        "mov r0, r4",
        "bl #{@cv}",
        "ldr r1, [pc, #{L0}]",
        "add r1, r1, r4",
        "ldr r2, [r7, #0x28]",
        "cmp r0, #0",
        "beq #{@pan_non}",
        "orr r2, r2, #0x20",
        "str r2, [r7, #0x28]",
        "mov r0, #1",
        "strb r0, [r1, #20]",
        "b #{@pan_fin}",
        "pan_non:",
        "ldrb r0, [r1, #20]",
        "cmp r0, #0",
        "beq #{@pan_fin}",
        "mov r0, #0",
        "strb r0, [r1, #20]",
        "bic r2, r2, #0x20",
        "str r2, [r7, #0x28]",
        "pan_fin:",
        "ldr r2, [r7, #0x28]",
        "pop {r0, r1, r3, r4, r5, pc}",
        # ---- VICTIME : r0 = id de l'efface marque, -1 s'il n'y en a pas.
        # Ne touche que r0.
        "victime:",
        "ldr r0, [pc, #{L3}]",
        "ldrb r0, [r0]",
        "and r0, r0, #%d" % VICTIME_MASQUE,
        "mov r0, r0, lsr #%d" % VICTIME_DEC,
        "sub r0, r0, #1",
        "cmp r0, #%d" % (VICTIME_FAIT - 1),
        "mvneq r0, #0",
        "bx lr",
        # ---- G_APPLI : `blx ip` de l'appel des effets (r2 = cible). L'efface
        # : rien, 0 rendu (le cas « pas de cible » du jeu). lr garde le retour
        # du jeu : G_EFFET le compare a EFFET_RETOUR.
        "g_appli:",
        "push {r0, lr}",
        "ldr r0, [pc, #{L0}]",              # l'effet du charme : rien (la fiche est celle d'un coup)
        "ldrb lr, [r0, #61]",
        "cmp lr, #0",
        "movne lr, #0",
        "strbne lr, [r0, #61]",
        "pop {r0, lr}",
        "movne r0, #0",
        "bxne lr",
        "push {r0, lr}",
        "bl #{@victime}",
        "cmp r0, r2",
        "pop {r0, lr}",
        "moveq r0, #0",
        "bxeq lr",
        "push {r0, r1}",                    # le sort bleu : E_BLEU au lieu de l'effet de sa fiche
        "ldrh r0, [r3, #4]",                # r3 = la fiche, son identifiant sur 10 bits
        "lsl r0, r0, #22",
        "lsr r0, r0, #22",
        "mov r1, #%d" % (BLEU & 0xF00),
        "orr r1, r1, #%d" % (BLEU & 0xFF),
        "cmp r0, r1",
        "pop {r0, r1}",
        "beq #{@e_bleu}",
        "bx ip",
        # ---- E_BLEU : un effet (r0 le combat, r2 la cible, r3 la fiche ; rend la file de messages), sur celui du
        # jeu en 0x021E1ED4 (meme famille que Decuplo, 0x021DB5EC) : chaque stat qui peut monter monte d'un cran, son
        # message dans la file ; aucune : le message d'echec de la fiche (+0x24) ; puis la fin du jeu.
        "e_bleu:",
        "push {r4, r5, r6, r7, r8, sb, sl, fp, lr}",
        "sub sp, sp, #0x1c",
        "mov sl, r0",
        "str r2, [sp, #0xc]",
        "mov sb, r3",
        "mov r7, #0",
        "mov fp, #0",
        "ldr r0, [sl, #0x10]",
        "mov r1, r2",
        "bl #%d" % CIBLE_ACTEUR,
        "movs r4, r0",
        "beq #{@eb_fin}",
        "ldr r0, [sl, #0x10]",
        "bl #%d" % FILE_MSG,
        "movs fp, r0",
        "beq #{@eb_fin}",
    ] + [l for k, (peut, cran, avis, msg) in enumerate(CRANS) for l in (
        "ldr r0, [r4, #0x138]",
        "mov r1, #0",
        "bl #%d" % peut,
        "cmp r0, #0",
        "beq #{@eb_%d}" % k,
        "ldr r0, [r4, #0x138]",
        "mov r1, #1",
        "bl #%d" % cran,
        "mov r5, r0",
        "ldr r0, [sl, #0x10]",
        "ldr r1, [sp, #0xc]",
        "bl #%d" % avis,
        "lsl r0, r5, #24",
        "asr r0, r0, #24",
        "str r0, [sp]",
        "mov r3, #1",
        "str r3, [sp, #4]",
        "str r3, [sp, #8]",
        "mov r0, sl",
        "ldr r1, [sp, #0xc]",
        "mov r2, sb",
        "mov r3, #0",
        "bl #%d" % msg,
        "mov r2, r0",
        "ldr r0, [sl, #0x10]",
        "mov r1, fp",
        "bl #%d" % POUSSER_MSG,
        "mov r7, #1",
        "eb_%d:" % k)] + [
        "cmp r7, #0",
        "bne #{@eb_suite}",
        "ldr r1, [sb, #0x24]",              # rien n'a monte : le message d'echec de la fiche
        "lsl r1, r1, #12",
        "lsr r1, r1, #22",
        "lsl r2, r1, #16",
        "lsr r2, r2, #16",
        "ldr r0, [sl, #0x10]",
        "mov r1, fp",
        "bl #%d" % POUSSER_MSG,
        "eb_suite:",
        "ldr r0, [sl, #0xc]",               # la fin du jeu (0x021E2074)
        "mov r3, #0",
        "ldrb r0, [r0, #0x1c]",
        "mov r1, fp",
        "mov r2, r4",
        "lsl r0, r0, #24",
        "lsrs r0, r0, #31",
        "movne r0, #1",
        "str r3, [sp]",
        "moveq r0, #0",
        "str r3, [sp, #4]",
        "str r0, [sp, #8]",
        "ldr r0, [sl, #0x10]",
        "bl #%d" % FIN_EFFET,
        "eb_fin:",
        "mov r0, fp",
        "add sp, sp, #0x1c",
        "pop {r4, r5, r6, r7, r8, sb, sl, fp, pc}",
        # ---- RETIRE : la barre de l'efface sort de l'interface, une fois.
        # Detruit r0-r3, ip.
        "retire:",
        "push {r4, r5, lr}",
        "bl #{@victime}",
        "movs r4, r0",
        "bmi #{@ret_fin}",
        "ldr r5, [pc, #{L10}]",
        "ldr r5, [r5]",
        "cmp r5, #0",
        "beq #{@ret_fin}",
        "ldr r1, [pc, #{L11}]",
        "mul r1, r4, r1",
        "add r1, r1, r5",
        "add r1, r1, #%d" % (O_FICHES & 0xF00),
        "add r1, r1, #%d" % (O_FICHES & 0xFF),
        "ldr r0, [r1, #0x4c]",
        "cmp r0, r4",
        "bne #{@ret_fin}",                  # deja fait
        "mvn r0, #0",
        "str r0, [r1, #0x4c]",
        "add r1, r5, #%d" % O_LISTE,
        "bl #{@ret_liste}",
        "strb r4, [r1, r3]",                # O+0x6C reste une permutation
        "add r1, r5, #%d" % O_LISTE2,
        "bl #{@ret_liste}",
        "mvn r0, #0",
        "strb r0, [r1, r3]",                # O+0x70 : -1 pour l'absent
        "ldrb r0, [r5, #%d]" % O_BARRES,
        "sub r0, r0, #1",
        "strb r0, [r5, #%d]" % O_BARRES,
        "ret_fin:",
        "pop {r4, r5, pc}",
        # r1 = liste de 4 octets, r4 = id : l'id en sort, les suivants
        # remontent ; r3 = la derniere place, libre. Detruit r0, r2, r3.
        "ret_liste:",
        "mov r2, #0",
        "mov r3, #0",
        "ret_boucle:",
        "ldrb r0, [r1, r2]",
        "cmp r0, r4",
        "strbne r0, [r1, r3]",
        "addne r3, r3, #1",
        "add r2, r2, #1",
        "cmp r2, #4",
        "blt #{@ret_boucle}",
        "bx lr",
        # ---- G_EFFACER : cas 0x80 du lanceur d'actions (terrain). Garde
        # r4-fp et sp, repart au noeud suivant. Sans victime marquee : rien.
        "g_effacer:",
        "push {r4, r5, r6, r7, r8, sb}",
        "sub sp, sp, #0x240",               # une fiche de 572 o
        "ldr r7, [pc, #{L3}]",
        "ldrb r0, [r7]",
        "ands r8, r0, #%d" % VICTIME_MASQUE,
        "beq #{@eff_fin}",
        "cmp r8, #%d" % VICTIME_MASQUE,     # deja efface : rien
        "beq #{@eff_fin}",
        "orr r0, r0, #%d" % VICTIME_MASQUE,
        "strb r0, [r7]",                    # la marque passe a VICTIME_FAIT d'abord
        "mov r8, r8, lsr #%d" % VICTIME_DEC,
        "sub r8, r8, #1",
        "mov r0, r8",
        "bl #%d" % SORTIR_OBJETS,
        "mov r0, r8",
        "mov r1, sp",
        "bl #%d" % SORTIR_GROUPE,
        "cmp r0, #0",
        "beq #{@eff_fin}",
        "bl #%d" % MGR,
        "bl #%d" % SAUVE,
        "add sb, r0, #0x1d4",
        "ldr r6, [pc, #{L4}]",              # EQUIPEMENT
        "mov r5, #%d" % len(EQUIPEMENT),
        "eff_boucle:",
        "ldrb r0, [r6], #1",                # emplacement
        "ldrb r3, [r6], #1",                # categorie
        "add r0, sp, r0, lsl #1",
        "add r0, r0, #0x160",
        "ldrsh r1, [r0]",
        "cmp r1, #0",
        "blt #{@eff_suivant}",
        "mov r0, sb",
        "mov r2, #1",
        "bl #%d" % SAC_EQUIPEMENT,
        "eff_suivant:",
        "subs r5, r5, #1",
        "bne #{@eff_boucle}",
        "eff_fin:",
        "add sp, sp, #0x240",
        "pop {r4, r5, r6, r7, r8, sb}",
        "b #%d" % SUITE_ACTIONS,
    ]
    if ESSAI:
        lignes = _essai(lignes)
    n = sum(1 for l in lignes if not (l.endswith(":") and " " not in l))
    lits = 18
    table = adr + 4 * n + 4 * lits
    tab = bytes(b for paire in EQUIPEMENT for b in paire)
    texte = table + len(tab)
    couleurs = struct.pack("<16H", *map(_bgr, TEXTE_BLEU))
    etoiles = texte + len(couleurs)
    couleurs += struct.pack("<12H", *map(_bgr, ETOILES_JAUNES + ETOILES_BLEUES))
    tab += couleurs
    actions = table + len(tab)
    tab += struct.pack("<%dH" % len(TABLE), *TABLE)
    paliers = table + len(tab)
    tab += bytes(PALIERS)
    poids = table + len(tab)
    tab += bytes(POIDS)
    tab += bytes(-len(tab) % 2)
    tab += bytes(-len(tab) % 4)
    etat = table + len(tab)
    etiq = {}
    code = assembler(lignes, adr, litteraux=(etat, action, NEANT, VICTIME_OCTET, table,
                                                 EFFET_RETOUR, texte,
                                                 PAL_OBJ_B + 32 * PAL_TEXTE,
                                                 etoiles, PAL_ETOILES,
                                                 O_PTR, FICHE_TAILLE, actions,
                                                 BOITE_MSG - 1, AQUILA_MSG, paliers, SOIN, poids),
                     etiquettes_out=etiq)
    assert adr + len(code) == table
    etiq["etat"] = etat
    # etat : 4 octets de charme (un par index), puis l'id de la victime du
    # neant en attente (0xFF = aucune), bourrage, puis l'entree de file de
    # Zenus au neant (+8), son action (+12) et son octet +9 (+14)
    # ; +16 : le membre s'affiche charme ; +20 : la copie porte notre 0x20
    return code + tab + bytes(4) + bytes((0xFF, 0, 0, 0)) + bytes(ETAT_TAILLE - 8), etiq


def _desas(data, base, adr):
    from patch_butin import _desas as d
    return d(data, base, adr)


def patcher(rom, action, bavard=True):
    """Pose la greffe derriere l'overlay 11 et detourne les cinq sites.
    `action` : l'identifiant d'action qui charme quand un monstre le choisit."""
    import ndspy.code
    from patch_hasard import assembler
    ovl = rom.loadArm9Overlays()
    o = ovl[OVL]
    if o.bssSize != 0 or len(o.data) != o.ramSize:
        raise SystemExit("overlay 11 : disposition inattendue (deja patche ?)")
    adr = o.ramAddress + o.ramSize                  # 0x02188B80
    bloc, etiq = greffe(adr, action)
    if adr + len(bloc) > PLAFOND:
        raise SystemExit("greffe du charme : depasse la place des overlays 7-14")
    for k, site, attendu, _e, _i in SITES:
        lu = _desas(ovl[k].data, ovl[k].ramAddress, site)
        if lu != attendu:
            raise SystemExit("overlay %d : a %#010x attendu %r, lu %r"
                             % (k, site, attendu, lu))
    o.data = bytes(o.data) + bloc
    o.ramSize = len(o.data)
    touches = {OVL}
    for k, site, _a, e, ins in SITES:
        d = bytearray(ovl[k].data)
        p = site - ovl[k].ramAddress
        d[p:p + 4] = assembler(["%s #%d" % (ins, etiq[e])], site)
        ovl[k].data = bytes(d)
        touches.add(k)
    for k in touches:
        rom.files[ovl[k].fileID] = ovl[k].save(compress=True)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovl)
    # l'ARM9 : l'entree OP_EFFACER de la table de sauts du lanceur d'actions
    from patch_monde_vide import _arm9_clair, BASE_ARM9
    arm9 = _arm9_clair(rom)
    site, attendu, e, ins = SITE_ARM9
    lu = _desas(bytes(arm9), BASE_ARM9, site)
    if lu != attendu:
        raise SystemExit("ARM9 : a %#010x attendu %r, lu %r" % (site, attendu, lu))
    arm9[site - BASE_ARM9:site - BASE_ARM9 + 4] = assembler(["%s #%d" % (ins, etiq[e])], site)
    # l'overlay 11 charge au debut de chaque combat (ZER-119)
    p = EMPILER - BASE_ARM9
    if bytes(arm9[p:p + len(EMPILER_ORIGINE)]) != EMPILER_ORIGINE:
        raise SystemExit("ARM9 : fonction d'empilement %#010x inattendue" % EMPILER)
    arm9[p:p + len(EMPILER_ORIGINE)] = _empiler()
    rom.arm9 = bytes(arm9)
    if bavard:
        print("  charme   : %d o a %#010x (etat %#010x), action %#x, sites %s"
              % (len(bloc), adr, etiq["etat"], action,
                 ", ".join("%#010x" % s for _k, s, *_r in SITES)))
        print("  neant    : action %#x sous %d PV, victime en drapeaux %#x-%#x,"
              " effacement = action de declencheur %#x (%#010x)"
              % (NEANT, SEUIL, VICTIME_DRAPEAU, VICTIME_DRAPEAU + 2, OP_EFFACER, site))
    return etiq


# LA REPLIQUE (joueur, 31/10 : « obeis-moi, tu es ma creation », voulue a la facon
# d'Aquila, actmsg 0x1EE). Le charme ne prend pas une action du kit : celles-ci
# sont aussi a Nokturnus ou au pool des techniques, Zenus parlerait ailleurs.
# 0x1F6 n'est portee par rien (ni espece, ni pool, ni nom, message 0) ; elle
# recoit la fiche de 0x169 (« grand sourire malicieux », aucun effet) et un
# message neuf, 0x26F, apres le dernier du jeu (0x26E ; l'entree 0 de la
# table est un DUMMY d'identifiant 0x390000). Le numero de message d'une
# action tient sur 10 bits (fiche +35, bits 2-11, research §94.5).
ACTION = ACTION_CHARME
FICHE = 0x169
MESSAGE = 0x26F
LANGUES = ("de", "en", "es", "fr", "it")
# PAS la forme d'Aquila (mesure a froid, 31/10, work/zenus_charme/
# variantes_replique.py) : dans un message d'ACTION, « //Nom// » est avale
# (aucun nom affiche) et « <PAD_WAIT_NOCUR><CLOSE> » cache tout le texte (le
# combat attend une touche sur une fenetre vide). Le nom est donc ecrit en
# clair (pas <DEF_ART_ACTOR> : pas d'article ajoute selon la langue), le
# texte reste affiche pendant l'animation et part seul.
REPLIQUE = {
    "fr": "Z<'e>nus tonne : Ob<'e>is-moi<,> tu es ma cr<'e>ation<!>",
    "en": "Zenus booms: Obey me<,> for you are my creation!",
    "de": "Zenus donnert: Gehorche mir<,> du bist meine Sch<:o>pfung!",
    "es": "Zenus truena: <^!>Obed<'e>ceme<,> eres mi creaci<'o>n!",
    "it": "Zenus tuona: Obbediscimi<,> tu sei una mia creazione!",
}
FIN_REPLIQUE = ""
# Le NEANT (meme moule : fiche de 0x169, message neuf apres 0x26F). La cible
# est la victime (G_CIBLE) : son nom par la balise de cible de chaque langue
# (accusatif en allemand ; en espagnol « a <TARGET> », un membre d'equipe a
# toujours un nom propre).
TEXTE_NEANT = {
    "fr": "Z<'e>nus r<'e>duit <DEF_ART_TARGET> au n<'e>ant...",
    "en": "Zenus reduces <DEF_ART_TARGET> to nothingness...",
    "de": "Zenus tilgt <DEF_ART_SGL_ACC_TARGET> aus dem Dasein...",
    "es": "Zenus reduce a <TARGET> a la nada...",
    "it": "Zenus riduce <DEF_ART_TARGET> al nulla...",
}
# La fiche du neant : celle de 0x22D (« ecrase X comme un insecte », du kit
# de Zenus), une technique a CIBLE UNIQUE. Celle de 0x169 vise son lanceur
# (octet 11 = 0x0A, contre 0x09 aux actions a cible) : le jeu n'appelle pas
# le constructeur de cibles et le message disait « Zenus reduit Zenus au
# neant » (mesure a froid, 01/11).
FICHE_NEANT = 0x22D
# (action, message, textes, fiche donneuse) : dans l'ordre des messages ajoutes
REPLIQUES = ((ACTION, MESSAGE, REPLIQUE, FICHE),
             (NEANT, NEANT_MSG, TEXTE_NEANT, FICHE_NEANT))
# LES REPLIQUES DES PALIERS, dans l'ordre de PALIERS : la forme d'Aquila (actmsg 0x1EE).
FIN_BOITE = "<PAD_WAIT_NOCUR><CLOSE>"
TEXTES_BOITE = {
    "fr": ("//Z<'e>nus// Ainsi<,> la poussi<`e>re griffe la main qui l<1>a p<'e>trie. Savoure : ce frisson sera ton dernier.",
           "//Z<'e>nus// Assez<!> D<1>un souffle je t<1>ai fait na<^i>tre. D<1>un souffle<,> je t<1><'e>teindrai<!>",
           "//Z<'e>nus// Ce feu... en moi ? Impossible. Le cr<'e>ateur ne saigne pas devant sa cr<'e>ature<!>",
           "//Z<'e>nus// Je sens la fin venir... Soit. Si je m<1><'e>teins<,> les tiens sombreront avant moi dans le n<'e>ant<!>",
           "//Z<'e>nus// Sans moi<,> tout retourne au silence... Ce monde s<1>efface<,> Gardien. Et c<1>est toi qui l<1>as voulu."),
    "en": ("//Zenus// So the dust claws at the hand that shaped it. Savour this thrill: it will be your last.",
           "//Zenus// Enough! With a breath I gave you life. With a breath<,> I shall snuff you out!",
           "//Zenus// This fire... within me? Impossible. A creator does not bleed before his creation!",
           "//Zenus// I feel the end drawing near... So be it. If I fade<,> yours shall sink into nothingness first!",
           "//Zenus// Without me<,> all returns to silence... This world fades<,> Guardian. And you willed it so."),
    "de": ("//Zenus// So kratzt der Staub an der Hand<,> die ihn formte. Genie<ss>e diesen Schauer: Es ist dein letzter.",
           "//Zenus// Genug! Mit einem Hauch gab ich dir Leben. Mit einem Hauch l<:o>sche ich dich aus!",
           "//Zenus// Dieses Feuer... in mir? Unm<:o>glich. Ein Sch<:o>pfer blutet nicht vor seinem Gesch<:o>pf!",
           "//Zenus// Ich sp<:u>re das Ende... Sei es drum. Erlische ich<,> versinken die Deinen zuerst im Nichts!",
           "//Zenus// Ohne mich kehrt alles zur Stille zur<:u>ck... Diese Welt vergeht<,> W<:a>chter. Und du hast es gewollt."),
    "es": ("//Zenus// As<'i> que el polvo ara<~n>a la mano que lo model<'o>. Saborea este escalofr<'i>o: ser<'a> el <'u>ltimo.",
           "//Zenus// <^!>Basta! Con un soplo te di la vida. <^!>Con un soplo te apagar<'e>!",
           "//Zenus// Este fuego en m<'i>... Imposible. <^!>Un creador no sangra ante su criatura!",
           "//Zenus// Siento llegar el fin... Sea. <^!>Si me apago<,> los tuyos caer<'a>n antes en la nada!",
           "//Zenus// Sin m<'i><,> todo vuelve al silencio... Este mundo se borra<,> guardi<'a>n. Y t<'u> lo has querido."),
    "it": ("//Zenus// Dunque la polvere graffia la mano che l<1>ha plasmata. Assapora questo brivido: sar<`a> l<1>ultimo.",
           "//Zenus// Basta! Con un soffio ti ho dato la vita. Con un soffio ti spegner<`o>!",
           "//Zenus// Questo fuoco... in me? Impossibile. Un creatore non sanguina davanti alla sua creatura!",
           "//Zenus// Sento giungere la fine... Sia. Se mi spengo<,> i tuoi cadranno per primi nel nulla!",
           "//Zenus// Senza di me<,> tutto torna al silenzio... Questo mondo svanisce<,> guardiano. E sei stato tu a volerlo."),
}
ACTDT = "data/prm/actdt_b.gp2"
ACTDT_A = "data/prm/actdt_a.gp2"
ACTMSG = "data/prm/actmsg.gp2"
# Le message de sa fiche donneuse (« lance le sort <ACTION> ») lit le nom dans le pool d'actdt_a : on l'ecrit en clair.
MSG_SORT = 0x2E
SOIN_MSG = BOITE_MSG + 5
BLEU_MSG = SOIN_MSG + 1
# Le lancement du sort bleu (le nom en clair, comme les repliques) ; les trois « ... augmente » suivent, du jeu.
TEXTE_SORT_BLEU = {
    "fr": "Z<'e>nus s<1>entoure d<1>une aura divine<!>",
    "en": "Zenus surrounds himself with a divine aura!",
    "de": "Zenus h<:u>llt sich in eine g<:o>ttliche Aura!",
    "es": "<^!>Zenus se envuelve en un aura divina!",
    "it": "Zenus si avvolge in un<1>aura divina!",
}
# ajoute apres le soin (BLEU_MSG suit SOIN_MSG)
REPLIQUES_APRES = ((BLEU, BLEU_MSG, TEXTE_SORT_BLEU, DECUPLO),)
NOM_ZENUS = {"de": "Zenus", "en": "Zenus", "es": "Zenus", "fr": "Z<'e>nus", "it": "Zenus"}


def _actdt(rom, chemin=ACTDT, prefixe="actdt_b_"):
    """{nom de membre: octets} des membres de langue d'actdt_b (EN CLAIR,
    sans bloc de controle ; nom n = n-ieme membre par offset)."""
    import gp2
    d = bytes(rom.getFileByName(chemin))
    g = gp2.GP2(chemin, donnees=d)
    ent = sorted(g.entrees, key=lambda e: e[1] & 0xFFFFFF)
    out = {}
    for nom, (_h, o, t) in zip(g.noms, ent):
        if nom.startswith(prefixe):
            p = g.first_file * 4 + (o & 0xFFFFFF) * 4
            out[nom] = d[p:p + t]
    return out


def _fiche_soin(m, a):
    """m : le membre d'actdt_b ; a : celui d'actdt_a, meme langue. Son nom (+2) reste celui de la place."""
    f = bytearray(a[_rang(a, SOIN_DONNEUR):][:60])
    f[2:4] = m[_rang(m, SOIN) + 2:_rang(m, SOIN) + 4]
    struct.pack_into("<H", f, 6, (struct.unpack_from("<H", f, 6)[0] & ~0x3FF) | SOIN)
    v = struct.unpack_from("<H", f, 35)[0]
    struct.pack_into("<H", f, 35, (v & ~(0x3FF << 2)) | (SOIN_MSG << 2))
    return bytes(f)


def _nom_action(a, action):
    """Le nom d'une action dans son membre (research §91.2 : +2, relatif au pool + 2)."""
    n = struct.unpack_from("<H", a, 0)[0] & 0x3FF
    o = 2 + 60 * n + 2 + struct.unpack_from("<H", a, _rang(a, action) + 2)[0]
    return a[o:a.index(b"\0", o)]


def _texte_soin(rom, lg):
    import objets
    import textes_dq9
    t = textes_dq9.messages(objets._membre_archive(rom, ACTMSG, "actmsg_%s.nat" % lg))[MSG_SORT]
    a = _actdt(rom, ACTDT_A, "actdt_a_")["actdt_a_%s.nat" % lg]
    t = t.replace(b"<ACTION>", _nom_action(a, SOIN_DONNEUR))
    for art in (b"<Cap><DEF_ART_ACTOR>", b"<DEF_ART_ACTOR>", b"<ACTOR>"):
        if art in t:
            return t.replace(art, NOM_ZENUS[lg].encode("latin-1"))
    raise SystemExit("actmsg_%s : message %#x sans acteur : %r" % (lg, MSG_SORT, t))


def _rang(m, action):
    n = struct.unpack_from("<H", m, 0)[0] & 0x3FF
    for i in range(n):
        if struct.unpack_from("<H", m, 2 + i * 60 + 6)[0] & 0x3FF == action:
            return 2 + i * 60
    raise ValueError("action %#x absente d'actdt_b" % action)


def _fiche_replique(m, action=ACTION, message=MESSAGE, fiche=FICHE):
    """La fiche de `fiche`, identifiant `action`, message `message`."""
    f = bytearray(m[_rang(m, fiche):][:60])
    if action == ACTION:
        f[11] = 0x09                    # une cible : la camera et l'effet vont sur le compagnon
    v = struct.unpack_from("<H", f, 6)[0]
    struct.pack_into("<H", f, 6, (v & ~0x3FF) | action)
    v = struct.unpack_from("<H", f, 35)[0]
    struct.pack_into("<H", f, 35, (v & ~(0x3FF << 2)) | (message << 2))
    return bytes(f)


def _texte(lg, textes=REPLIQUE):
    return (textes[lg] + FIN_REPLIQUE).encode("latin-1")


def replique(rom, bavard=True):
    """Donne a chaque action de REPLIQUES la fiche de FICHE et son texte
    (5 langues) : la replique du charme et le neant."""
    import gp2_ecrire
    import objets
    import textes_dq9
    from patch_actions import message_action
    neufs = {}
    dons = _actdt(rom, ACTDT_A, "actdt_a_")
    textes_soin = {lg: _texte_soin(rom, lg) for lg in LANGUES}
    for nom, m in _actdt(rom).items():
        for action, message, _t, fiche in REPLIQUES:
            p = _rang(m, action)
            f = bytes(m[p:p + 60])
            if message_action(f) or f[10]:
                raise SystemExit("actdt : l'action %#x n'est plus libre" % action)
            m = m[:p] + _fiche_replique(m, action, message, fiche) + m[p + 60:]
        for action, message, _t, fiche in REPLIQUES_APRES:
            p = _rang(m, action)
            if message_action(m[p:p + 60]) or m[p + 10]:
                raise SystemExit("actdt : l'action %#x n'est plus libre" % action)
            m = m[:p] + _fiche_replique(m, action, message, fiche) + m[p + 60:]
        p = _rang(m, SOIN)
        if message_action(m[p:p + 60]) or m[p + 10]:
            raise SystemExit("actdt : l'action %#x n'est plus libre" % SOIN)
        a = dons["actdt_a_" + nom[len("actdt_b_"):]]
        m = m[:p] + _fiche_soin(m, a) + m[p + 60:]
        neufs[nom] = m
    fid = rom.filenames.idOf(ACTDT)
    rom.files[fid] = gp2_ecrire.reecrire(bytes(rom.files[fid]), neufs, brut=True)
    neufs = {}
    for lg in LANGUES:
        nom = "actmsg_%s.nat" % lg
        m = objets._membre_archive(rom, ACTMSG, nom)
        for _a, message, textes, _f in REPLIQUES:
            m = textes_dq9.ajouter_message(m, message, _texte(lg, textes))
        for k, t in enumerate(TEXTES_BOITE[lg]):
            m = textes_dq9.ajouter_message(m, BOITE_MSG + k, (t + FIN_BOITE).encode("latin-1"))
        m = textes_dq9.ajouter_message(m, SOIN_MSG, textes_soin[lg])
        for _a, message, textes, _f in REPLIQUES_APRES:
            m = textes_dq9.ajouter_message(m, message, _texte(lg, textes))
        neufs[nom] = m
    fid = rom.filenames.idOf(ACTMSG)
    rom.files[fid] = gp2_ecrire.reecrire(bytes(rom.files[fid]), neufs)
    if bavard:
        for action, message, _t, fiche in REPLIQUES:
            print("  replique : action %#x (fiche de %#x), message %#x, %d langues"
                  % (action, fiche, message, len(LANGUES)))


def verifier_replique(rom):
    """Chaque action de REPLIQUES porte la fiche de FICHE et son message dans
    les 5 langues ; le reste d'actdt_b est intact ; le message dit son texte."""
    import objets
    import textes_dq9
    from patch_actions import message_action
    membres = _actdt(rom)
    if len(membres) != len(LANGUES):
        raise AssertionError("actdt_b : %d membres de langue" % len(membres))
    for nom, m in membres.items():
        for action, message, _t, fiche in REPLIQUES + REPLIQUES_APRES:
            p = _rang(m, action)
            if m[p:p + 60] != _fiche_replique(m, action, message, fiche):
                raise AssertionError("%s : fiche de %#x differente" % (nom, action))
            if message_action(m[p:p + 60]) != message:
                raise AssertionError("%s : message de %#x" % (nom, action))
        a = _actdt(rom, ACTDT_A, "actdt_a_")["actdt_a_" + nom[len("actdt_b_"):]]
        p = _rang(m, SOIN)
        if m[p:p + 60] != _fiche_soin(m, a):
            raise AssertionError("%s : fiche du soin" % nom)
    for lg in LANGUES:
        msgs = textes_dq9.messages(objets._membre_archive(
            rom, ACTMSG, "actmsg_%s.nat" % lg))
        for _a, message, textes, _f in REPLIQUES + REPLIQUES_APRES:
            if msgs.get(message) != _texte(lg, textes):
                raise AssertionError("actmsg_%s : message %#x" % (lg, message))
        for k, t in enumerate(TEXTES_BOITE[lg]):
            if msgs.get(BOITE_MSG + k) != (t + FIN_BOITE).encode("latin-1"):
                raise AssertionError("actmsg_%s : palier %d" % (lg, k))
        if msgs.get(SOIN_MSG) != _texte_soin(rom, lg):
            raise AssertionError("actmsg_%s : soin" % lg)
    return True


def verifier(rom, action):
    """Relit la ROM : le bloc derriere l'overlay 11 est le notre et chaque
    site branche sur sa greffe."""
    ovl = rom.loadArm9Overlays()
    o = ovl[OVL]
    adr = 0x02188B80
    bloc, etiq = greffe(adr, action)
    if o.ramAddress + o.ramSize != adr + len(bloc) or \
            bytes(o.data[adr - o.ramAddress:]) != bloc:
        raise AssertionError("overlay 11 : greffe du charme absente ou differente")
    for k, site, _a, e, ins in SITES:
        lu = _desas(ovl[k].data, ovl[k].ramAddress, site)
        if lu != "%s #%#x" % (ins, etiq[e]):
            raise AssertionError("overlay %d : %#010x lit %r" % (k, site, lu))
    from patch_monde_vide import _arm9_clair, BASE_ARM9
    site, _a, e, ins = SITE_ARM9
    arm9 = bytes(_arm9_clair(rom))
    lu = _desas(arm9, BASE_ARM9, site)
    if lu != "%s #%#x" % (ins, etiq[e]):
        raise AssertionError("ARM9 : %#010x lit %r" % (site, lu))
    p = EMPILER - BASE_ARM9
    if arm9[p:p + len(EMPILER_ORIGINE)] != _empiler():
        raise AssertionError("ARM9 : l'empilement %#010x ne charge pas l'overlay 11 (ZER-119)"
                             % EMPILER)
    return True


if __name__ == "__main__":
    import ndspy.rom
    if len(sys.argv) < 4:
        sys.exit("usage: patch_charme.py <rom.nds> <sortie.nds> <action>")
    r = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    a = int(sys.argv[3], 0)
    patcher(r, a)
    verifier(r, a)
    r.saveToFile(sys.argv[2])
    # ndspy retire le bourrage 0xFF : on rend la taille d'entree
    n, cible = os.path.getsize(sys.argv[2]), os.path.getsize(sys.argv[1])
    if n > cible:
        sys.exit("ROM plus grande que l'entree")
    with open(sys.argv[2], "ab") as fo:
        fo.write(b"\xff" * (cible - n))
