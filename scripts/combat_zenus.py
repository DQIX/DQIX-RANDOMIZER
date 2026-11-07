"""Le combat de Zenus : un enregistrement neuf dans data/event/eventbattle.bin (30/10).

Le combat se lance par l'action de declencheur 0x78(n) (research §112) ;
n est le champ 0 de l'enregistrement. 0-143 sont pris : Zenus = 144.

    champ 0  numero de combat         144
    1-6      espece/nombre x3         900 x1, puis vides
    7        musique                  24 (theme des boss)
    8        decor                    30811 (arene d'Orgodemir, choix du joueur 06/11)

Le tout est assemble par patch_boss_secret.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nitro_script as N

COMBAT = 144
ESPECE = int(os.environ.get("ESPECE_ESSAI", "900"))   # essai seulement : autre espece
# 25 : son propre theme (musique_zenus, joueur 05/11). SANS_MUSIQUE=1 : le theme des boss du jeu.
MUSIQUE = 24 if os.environ.get("SANS_MUSIQUE") else 25
# champ 8 = le DECOR du combat (mesure 30/10 : 0 = plaine, 30709 et 30711
# = ciels de Corvus et Barbarus, 30305 = le temple du Tout-Puissant, celui
# du combat d'Aquila). CHOIX DU JOUEUR (06/11, planche work/arenes/arenes.html) :
# 30811, l'arene d'Orgodemir (antre legendaire)
FOND = int(os.environ.get("FOND", "30811"))
VIDE = 0xFFFFFFFF
CHEMIN = "data/event/eventbattle.bin"


def ajouter(d):
    h, ins = N.lire(d)
    if any(ps[0][1] == COMBAT for _, ps in ins):
        raise ValueError("combat %d deja present" % COMBAT)
    ins.append((0x64, [(N.ENTIER, v) for v in
                       (COMBAT, ESPECE, 1, VIDE, 0, VIDE, 0, MUSIQUE, FOND)]))
    return N.ecrire(ins)


INDEX = 437                      # espece 900 dans mon_btldata / mon_moddata
NOCTURNUS = 344                  # espece 514, le boss dont Zenus s'inspire
# Decision du joueur (30/10) : les stats de Nocturnus NIVEAU 99. Le jeu
# multiplie a l'execution les stats des boss legendaires selon leur niveau ;
# Dragon Quest Wiki (fiche Nokturnus) : base 8 250 PV / 780 att / 610 def /
# 350 vit, niveau 99 : 16 572 / 1 567 / 915 / 560. Notre ROM EUR a 700 en
# attaque (le reste identique) : on applique les rapports du wiki.
# PV : 20 000 (joueur, 31/10 : vers 2 000 PV restants, le neant de
# patch_charme), au lieu des 16 572 de Nokturnus niveau 99
# Reglage du 05/11 (joueur : « gerer les degats, les stats, les faiblesses ») : a 1 406
# d'attaque un coup simple faisait 650-900 (niv. 57-75, 320-440 PV), a 915 de defense
# l'equipe faisait 1-90 : 20 000 PV ne finissaient jamais. Avec 2-3 actions par tour :
# PM 255 : a 24, le baton de Melchior drainait ses PM et le soin ratait (« Pas assez de PM »,
# mesure a froid le 05/11). Le soin unique est garde par la greffe (patch_charme, etat +31).
ZENUS_STATS = {"pv": 20000, "pm": 255, "attaque": 1500, "defense": 1000, "agilite": 450}
# joueur, 05/11, nuit
EXPERIENCE, OR = int(os.environ.get("ZENUS_EXP", "1000000")), 100000   # ZENUS_EXP : banc seulement
# Elements, ordre lu dans les fiches d'action (+12, bits 6-8, 1 = feu ... 6 tenebres,
# 7 lumiere ; research §113.12) : Nokturnus 50 % aux tenebres, 150 % a la lumiere. Zenus
# est l'inverse : le createur craint les tenebres, pas sa propre lumiere.
ELEMENTS = {5: 150, 6: 50}
# BANC SEULEMENT : ATT_ESSAI=50 (l'equipe survit, on voit tous les paliers)
if os.environ.get("ZENUS_PM"):                 # BANC SEULEMENT
    ZENUS_STATS["pm"] = int(os.environ["ZENUS_PM"])
if os.environ.get("ATT_ESSAI"):
    ZENUS_STATS["attaque"] = int(os.environ["ATT_ESSAI"])
# PM = le cout de Soins complets (0x2AA, version monstre) : UN soin par
# combat, ses autres actions sont gratuites (zenus_mon.KIT, 31/10)
# Actions par tour (joueur : 2 ou 3) : bits 9-11 du mot +0x0C de
# mon_moddata (copie au combat en +0x10 bits 8-10). Valeurs du jeu : 0 pour
# 287 especes, 2 pour les boss d'histoire et legendaires (Nokturnus), 3 pour
# les boss de grotte et les legendaires de niveau 2-3 (758-775).
# CORRIGE le 05/11 (research §113.11) : c'est mon_btldata +0x10 bits 8-10 que lit le
# combat scripte ; 2 = une action de plus, 3 = deux. Depart a 2, trois sous 50 %
# (patch_charme.PCT_TROIS).
# Joueur, 06/11 (soir) : 3 actions par tour DES LE DEBUT du combat (avant : 2, trois sous 50 %).
TOURS = int(os.environ.get("TOURS", "3"))
MOD_MOT, MOD_ACTIONS, BTL_ACTIONS = 0x0C, 0x32, 0x18


def stats(rom):
    """Stats de Nocturnus niveau 99, ses resistances, son experience et son
    or, poses sur l'espece 900 dans les deux fichiers de monstres."""
    import struct
    import patch_stats as P
    fiches = P.lire(rom)
    assert P.identifiants(rom)[INDEX] == ESPECE
    assert P.identifiants(rom)[NOCTURNUS] == 514
    f = dict(fiches[NOCTURNUS])
    f.update(ZENUS_STATS)
    f["elements"] = list(f["elements"])
    for k, v in ELEMENTS.items():
        f["elements"][k] = v
    fiches[INDEX] = f
    P.ecrire(rom, fiches)
    # experience et or : mon_btldata +0x08..+0x10, recopies dans mon_moddata
    # +0x28 (cf. patch_stats.synchroniser)
    fm, fb = P._fid(rom, P.MOD), P._fid(rom, P.BTL)
    mod, btl = bytearray(rom.files[fm]), bytearray(rom.files[fb])
    src = P.ENTETE + NOCTURNUS * P.BTL_TAILLE
    ob, om = P.ENTETE + INDEX * P.BTL_TAILLE, P.ENTETE + INDEX * P.MOD_TAILLE
    struct.pack_into("<II", btl, ob + 0x08, EXPERIENCE, OR)
    struct.pack_into("<II", mod, om + 0x28, EXPERIENCE, OR)
    # +0x27..+0x29 : 10 02 04 chez Nokturnus et Aquila, 00 00 00 chez
    # l'espece 900 inemployee (placement / camera en combat, a mesurer) ;
    # +0x2A (taille declaree) reste a zenus_mon
    btl[ob + 0x27:ob + 0x2A] = btl[src + 0x27:src + 0x2A]
    # le kit (zenus_mon.KIT) et l'IA de Nokturnus (type 1, poids
    # decroissants : l'emplacement 0 le plus souvent, le soin en dernier),
    # avec TOURS actions par tour
    from zenus_mon import KIT
    struct.pack_into("<6H", mod, om + MOD_ACTIONS, *KIT)
    struct.pack_into("<6H", btl, ob + BTL_ACTIONS, *KIT)
    # masques des actions tirees a chaque combat (--sorts-monstres,
    # --techniques-monstres, research §94.4) : a zero, Zenus garde son kit
    btl[ob + 0x82] = btl[ob + 0x83] = 0
    mot = struct.unpack_from("<I", mod, P.ENTETE + NOCTURNUS * P.MOD_TAILLE + MOD_MOT)[0]
    mot = (mot & ~(7 << 9)) | (TOURS << 9)
    struct.pack_into("<I", mod, om + MOD_MOT, mot)
    bt = struct.unpack_from("<I", btl, ob + 0x10)[0]
    struct.pack_into("<I", btl, ob + 0x10, (bt & ~(7 << 8)) | (TOURS << 8))
    rom.files[fm], rom.files[fb] = bytes(mod), bytes(btl)
    return struct.unpack_from("<II", btl, ob + 0x08)


# LA LISTE DES MONSTRES (joueur, 05/11 : « a la fin de la liste des boss »). data/prm/mon_list.gp2,
# membres mon_list_<lg>.nat : u16 nombre (12 bits bas), u16 taille du pool / 16, fiches de 32 o, pool
# juste apres. Fiche : +4 code du modele, +8 nom (offsets dans le pool), +0xC espece, +0xE rang de tri,
# +0x10 fiche de description, +0x12 famille (0xD : boss), +0x1A numero (1-308, le jeu borne a 0x134,
# qui sert aussi d'indice aux victoires dans la sauvegarde). 307 est Rhapthorne : 308 est libre.
LISTE = "data/prm/mon_list.gp2"
INFO2 = "data/prm/mons_info2.nat"
NUMERO = 308
NOMS_LISTE = {"de": "Zenus", "en": "Zenus", "es": "Zenus", "fr": "Z<'e>nus", "it": "Zenus"}
MOUVEMENTS = ("stand", "run", "attack1a", "damage", "death", "magic")


def liste(rom):
    """Ajoute Zenus a la liste et sa fiche de bestiaire (mouvements, camera, gains)."""
    import struct
    import gp2_ecrire
    import objets
    fid = rom.filenames.idOf(LISTE)
    neufs = {}
    for lg, nom in NOMS_LISTE.items():
        mb = "mon_list_%s.nat" % lg
        d = objets._membre_archive(rom, LISTE, mb)
        mot, _t = struct.unpack_from("<HH", d, 0)
        n = mot & 0xFFF
        table, pool = 4 + n * 32, d[4 + n * 32:]
        modele = next(struct.unpack_from("<II", d, 4 + k * 32)[0] for k in range(n)
                      if struct.unpack_from("<H", d, 4 + k * 32 + 0xC)[0] == 514)
        dern = d[4 + (n - 1) * 32:table]               # Nokturnus, derniere fiche : famille, description
        assert struct.unpack_from("<H", dern, 0xC)[0] == 514
        rangs = [struct.unpack_from("<H", d, 4 + k * 32 + 0xE)[0] for k in range(n)]
        o_code = len(pool)
        ajout = b"z060c\0"
        o_nom = o_code + len(ajout)
        ajout += nom.encode("latin-1") + b"\0"
        f = bytearray(dern)
        struct.pack_into("<II", f, 4, o_code, o_nom)
        struct.pack_into("<HH", f, 0xC, ESPECE, max(rangs) + 1)
        struct.pack_into("<H", f, 0x1A, NUMERO)
        pool += ajout
        tete = struct.pack("<HH", (mot & 0xF000) | (n + 1), len(pool) // 16)
        neufs[mb] = tete + d[4:table] + bytes(f) + pool
    rom.files[fid] = gp2_ecrire.reecrire(bytes(rom.files[fid]), neufs)
    d = bytearray(rom.getFileByName(INFO2))
    nb, tab = struct.unpack_from("<HH", d, 0)
    fin = 8 + nb * 48
    t = struct.unpack_from("<%dI" % tab, d, fin)
    p = bytes(d[fin + tab * 4:])
    off = {}
    for v in t:
        off.setdefault(p[v:p.index(b"\0", v)].decode(), v)
    ajout = struct.pack("<%dI" % len(MOUVEMENTS), *(off[m] for m in MOUVEMENTS))
    r = 8 + INDEX * 48
    assert struct.unpack_from("<H", d, r + 4)[0] & 0x7FFF == ESPECE
    src = 8 + NOCTURNUS * 48
    d[r + 16:r + 44] = d[src + 16:src + 44]            # sa camera dans la visionneuse
    struct.pack_into("<I", d, r, EXPERIENCE)
    struct.pack_into("<H", d, r + 6, min(OR, 0xFFFF))  # la fiche n'a que 16 bits pour l'or
    struct.pack_into("<I", d, r + 12, len(MOUVEMENTS))
    struct.pack_into("<I", d, r + 44, tab)
    struct.pack_into("<H", d, 2, tab + len(MOUVEMENTS))
    rom.setFileByName(INFO2, bytes(d[:fin + tab * 4]) + ajout + p)

