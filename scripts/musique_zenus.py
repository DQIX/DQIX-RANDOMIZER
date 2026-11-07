"""Le theme de Zenus (joueur, 05/11) : un morceau dans data/sound/bgm.sdat, emplacement de theme 25 (vide).

Les themes du jeu sont des sequences (SSEQ + SBNK + SWAR), charges en memoire par le groupe de meme
numero. Le morceau devient UNE onde IMA-ADPCM en boucle, jouee par une seule note tenue. L'onde doit
tenir dans le tas du son : le plus gros theme du jeu pese 583 988 o, celui des boss 314 424 o. FREQ
regle la taille : 4 bits par echantillon, soit FREQ/2 octets par seconde.

Le morceau est deja converti (data/zenus/theme.adpcm : mono, FREQ Hz, normalise puis compresse
tanh(COMPRESSION x), IMA-ADPCM du DS) ; le joueur a choisi de le publier (06/11).
"""
import struct

FREQ = 7700
THEME = 25
# LE VOLUME. Une voix du DS est deja au maximum (volume, velocite et expression a 127) et un theme du jeu en fait
# sonner 8 ou plus en meme temps : une seule voix s'entend a peine. VOIES pistes jouent donc la meme onde, en
# phase (+12 dB a 4). COMPRESSION : tanh(C x), les passages calmes montent sans depasser le maximum.
VOIES = 4
COMPRESSION = 2.5
SDAT = "data/sound/bgm.sdat"


def swar():
    from zenus_mon import donnee
    d = donnee("theme.adpcm")
    temps = 16756991 // FREQ
    mots = len(d) // 4
    # boucle depuis le debut du corps : mot 1, juste apres les 4 octets d'etat
    onde = struct.pack("<BBHHHI", 2, 1, FREQ, temps, 1, mots - 1) + d
    corps = bytes(32) + struct.pack("<II", 1, 0x10 + 8 + 32 + 8 + 4 - 4) + onde
    data = b"DATA" + struct.pack("<I", 8 + len(corps)) + corps
    return b"SWAR\xff\xfe\x00\x01" + struct.pack("<IHH", 0x10 + len(data), 0x10, 1) + data


def sbnk():
    # un instrument PCM (type 1) : onde 0, archive 0, note de base 60, enveloppe pleine
    instr = struct.pack("<HHBBBBBB", 0, 0, 60, 127, 127, 127, 127, 64)
    tete = 0x10 + 8 + 32 + 4 + 4
    corps = bytes(32) + struct.pack("<I", 1) + struct.pack("<BHB", 1, tete, 0) + instr
    corps += bytes(-len(corps) % 4)
    data = b"DATA" + struct.pack("<I", 8 + len(corps)) + corps
    return b"SBNK\xff\xfe\x00\x01" + struct.pack("<IHH", 0x10 + len(data), 0x10, 1) + data


def sseq():
    # VOIES pistes identiques : 0xFE masque des pistes, 0x93 ouvre une piste (numero, decalage sur 3 octets depuis le
    # debut des evenements). Chacune : tempo 60, volume plein, instrument 0, note 60 tenue quasi sans fin ; l'onde boucle seule.
    piste = bytes((0xE1, 60, 0, 0xC1, 127, 0x81, 0, 60, 127, 0xFF, 0xFF, 0x7F, 0xFF))
    tete = 3 + 5 * (VOIES - 1)
    ev = bytes((0xFE,)) + struct.pack("<H", (1 << VOIES) - 1)
    for k in range(1, VOIES):
        ev += bytes((0x93, k)) + struct.pack("<I", tete + k * len(piste))[:3]
    ev += piste * VOIES
    ev += bytes(-len(ev) % 4)
    data = b"DATA" + struct.pack("<II", 12 + len(ev), 0x1C) + ev
    return b"SSEQ\xff\xfe\x00\x01" + struct.pack("<IHH", 0x10 + len(data), 0x10, 1) + data


def poser(rom, bavard=True):
    """Ajoute le theme dans l'emplacement THEME. Rend le numero de theme."""
    d = bytes(rom.getFileByName(SDAT))
    symb, sl, info, il, fat, fl, fi, fil = struct.unpack_from("<8I", d, 0x10)
    assert symb + sl <= info and info + il <= fat and fat + fl <= fi
    ib = bytearray(d[info:info + il])
    tables = struct.unpack_from("<8I", ib, 8)
    seq, bank, war, grp = tables[0], tables[2], tables[3], tables[5]
    for t in (seq, bank, war, grp):
        assert struct.unpack_from("<I", ib, t + 4 + 4 * THEME)[0] == 0, "emplacement %d pris" % THEME
    nfat = struct.unpack_from("<I", d, fat + 8)[0]
    fs = sseq()
    fb = sbnk()
    fw = swar()
    ref = struct.unpack_from("<I", ib, seq + 4 + 4 * 24)[0]
    _f, un, _b, vol, cpr, ppr, ply = struct.unpack_from("<HHHBBBB", ib, ref)
    bout = bytearray()

    def rec(tab, octets):
        struct.pack_into("<I", ib, tab + 4 + 4 * THEME, len(ib) + len(bout))
        bout.extend(octets)

    rec(seq, struct.pack("<HHHBBBBH", nfat, un, THEME, 127, cpr, ppr, ply, 0))
    rec(bank, struct.pack("<HH4H", nfat + 1, 0, THEME, 0xFFFF, 0xFFFF, 0xFFFF))
    rec(war, struct.pack("<I", nfat + 2))
    ref_g = struct.unpack_from("<I", ib, grp + 4 + 4 * 24)[0]
    assert struct.unpack_from("<I", ib, ref_g)[0] == 2
    t1 = struct.unpack_from("<I", ib, ref_g + 4)[0]
    t2 = struct.unpack_from("<I", ib, ref_g + 12)[0]
    rec(grp, struct.pack("<IIIII", 2, t1, THEME, t2, THEME))
    ib2 = bytes(ib) + bytes(bout)
    ib2 += bytes(-len(ib2) % 4)
    ib2 = ib2[:4] + struct.pack("<I", len(ib2)) + ib2[8:]
    ajout_info = len(ib2) - il
    ajout_fat = 3 * 16
    fatb = bytearray(d[fat:fat + fl])
    nfichier = struct.unpack_from("<I", d, fi + 8)[0]
    filb = bytearray(d[fi:fi + fil])
    delta = ajout_info + ajout_fat
    for i in range(nfat):
        o = struct.unpack_from("<I", fatb, 12 + i * 16)[0]
        struct.pack_into("<I", fatb, 12 + i * 16, o + delta)
    fi2 = fi + delta
    pos = fi2 + len(filb)
    for x in (fs, fb, fw):
        pad = -pos % 32
        filb += bytes(pad)
        pos += pad
        fatb += struct.pack("<IIII", pos, len(x), 0, 0)
        filb += x
        pos += len(x)
    pad = -pos % 32
    filb += bytes(pad)
    struct.pack_into("<I", fatb, 4, len(fatb))
    struct.pack_into("<I", fatb, 8, nfat + 3)
    struct.pack_into("<I", filb, 4, len(filb))
    struct.pack_into("<I", filb, 8, nfichier + 3)
    tete = bytearray(d[:info])
    struct.pack_into("<8I", tete, 0x10, symb, sl, info, len(ib2), fat + ajout_info, len(fatb), fi2, len(filb))
    neuf = bytes(tete) + ib2 + bytes(fatb) + bytes(filb)
    struct.pack_into("<I", tete, 8, len(neuf))
    neuf = bytes(tete) + neuf[len(tete):]
    rom.setFileByName(SDAT, neuf)
    if bavard:
        print("  musique  : theme %d, onde %d o (%d Hz), sdat %d -> %d o" % (THEME, len(fw), FREQ, len(d), len(neuf)))
    return THEME
