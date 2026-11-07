"""Le son des pas de Zenus (ZER-116, joueur 06/11 : « prends celui de Heroes, cale-le sur chaque appui » ;
le son est public). Un pas du Titan (Heroes V, Titan_Move.wav : 6 pas d'environ 0,75 s) dans
data/sound/se_btl.sdat, sur un numero d'archive LIBRE, propre a Zenus :

- MESURE (banc du 06/11, trace de 0x020BE7B8 = jouer (archive, son)) : op46 [n] d'un .bact joue le son n de
  l'archive du monstre, mon_btldata +0x14/+0x16 (560 = SEQ_EN_z060 pour Zenus, partagee avec les especes 63/64 ;
  elle n'a que les sons 0-24 : le op46 [25] de la v21 ne jouait RIEN) ;
- l'archive N est chargee par le groupe N (GRP_EN_...) : banque N (instruments ; echantillons de WAVE_en, 103)
  et archive de sequences N. On copie la banque et l'archive 560 sur NUMERO, on ajoute une archive d'echantillons
  (le pas, ADPCM 32 728 Hz comme les sons du jeu), l'instrument PROGRAMME de la banque qui le joue (comme
  l'instrument 124 de SE_EN_jumps_024) et le son SON de l'archive, puis un groupe NUMERO qui charge le tout ;
- Zenus (mon_btldata, rang 437) : +0x14/+0x16 = NUMERO.

Usage (banc) : python scripts/son_pas.py <rom entree> <rom sortie>
"""
import os
import struct
import sys

import ndspy.rom
import ndspy.soundArchive as S
import ndspy.soundBank as B
import ndspy.soundGroup as G
import ndspy.soundSequence as Q
import ndspy.soundWave as W
import ndspy.soundWaveArchive as WA

def _corriger_ndspy():
    """ndspy 4 : SDAT.save plante sur une archive de sequences VIDE (None) dans le calcul des symboles
    (`entry.sequences`, ligne ~403) ; se_btl en a 455. Meme fonction, avec la garde que la ligne ~443 a deja."""
    import inspect
    import textwrap
    src = textwrap.dedent(inspect.getsource(S.SDAT.save))
    vieux = "for subSymbol, subEntry in entry.sequences:"
    if vieux not in src:
        return
    src = src.replace(vieux, "for subSymbol, subEntry in (entry.sequences if entry is not None else []):", 1)
    ns = {}
    exec(compile(src, S.__file__, "exec"), S.__dict__, ns)
    S.SDAT.save = ns["save"]


_corriger_ndspy()

SDAT = "data/sound/se_btl.sdat"
MON_BTLDATA = "data/prm/mon_btldata.nat"
INDEX = 437                      # espece 900
ORIGINE = 560                    # SEQ_EN_z060 / EN_z060 / GRP_EN_z060
NUMERO = int(os.environ.get("ZENUS_SON_ARCHIVE", "585"))   # libre en archive, banque et groupe (vanilla)
SON = 25                         # op46 [25] du .bact (zenus_mon.PAS_SON)
PROGRAMME = 125
TAUX = 32728                     # comme les echantillons de WAVE_en
PAS_DEBUT, PAS_FIN = 0.0, 0.80   # le premier pas de Titan_Move (s)
VOLUME = int(os.environ.get("ZENUS_SON_VOLUME", "127"))

def onde():
    w = W.SWAV()
    w.waveType = W.WaveType.ADPCM
    w.isLooped = False
    w.sampleRate = TAUX
    w.time = round(16756991 / TAUX)
    # le pas converti (DS IMA-ADPCM, data/zenus/pas_titan.adpcm) : 0 a 0,8 s de Titan_Move, mono,
    # TAUX Hz, fondu de sortie de 30 ms
    from zenus_mon import donnee
    w.data = donnee("pas_titan.adpcm")
    w.loopOffset = 1
    w.totalLength = len(w.data) // 4
    return w


def sdat_neuf(donnees):
    s = S.SDAT(donnees)
    for liste in (s.sequenceArchives, s.banks, s.groups):
        if liste[NUMERO][1] is not None:
            raise SystemExit("se_btl : le numero %d n'est plus libre" % NUMERO)
    # l'archive d'echantillons du pas, en fin de liste
    swar = WA.SWAR()
    swar.waves = [onde()]
    s.waveArchives.append(("WAVE_zenus", swar))
    n_swar = len(s.waveArchives) - 1
    # la banque : celle de z060 + l'instrument du pas (copie de l'instrument 124 de SE_EN_jumps_024)
    b0 = s.banks[ORIGINE][1]
    banque = B.SBNK(b0.save()[0])
    banque.waveArchiveIDs = list(b0.waveArchiveIDs) + [n_swar]
    ref = banque.instruments[124]
    nd0 = ref.noteDefinitions[0]
    nd = B.NoteDefinition(0, len(banque.waveArchiveIDs) - 1, nd0.pitch, nd0.attack, nd0.decay, nd0.sustain,
                          nd0.release, nd0.pan, nd0.type)
    ins = B.RangeInstrument(ref.firstPitch, [nd])
    while len(banque.instruments) <= PROGRAMME:
        banque.instruments.append(None)
    banque.instruments[PROGRAMME] = ins
    banque.bankOrderKey = NUMERO
    s.banks[NUMERO] = ("EN_zenus", banque)
    # l'archive de sequences : celle de z060 + le son SON (instrument PROGRAMME, note du modele, fin)
    # Au niveau des octets (SSAR non analyse) : 0x81 = changement d'instrument (longueur variable), puis note,
    # velocite, duree 0 (l'echantillon jusqu'au bout), 0xFF = fin ; comme SE_EN_jumps_024 (81 7C 1D 7F 00 FF).
    import ndspy.soundSequenceArchive as SA
    a0 = s.sequenceArchives[ORIGINE][1]
    donnees, unk02, noms = a0.save()
    a = SA.SSAR(donnees, unk02, noms)
    assert not a.parsed and len(a.sequences) == SON
    assert PROGRAMME < 0x80
    off = len(a.eventsData)
    a.eventsData = bytes(a.eventsData) + bytes((0x81, PROGRAMME, ref.firstPitch, 0x7F, 0x00, 0xFF))
    _n, modele = a.sequences[24]
    seq = SA.SSARSequence(off, NUMERO, VOLUME, modele.channelPressure, modele.polyphonicPressure,
                          modele.playerID, parsed=False)
    a.sequences.append(("SE_EN_zenus_pas", seq))
    for _nm, q in a.sequences:
        if q.bankID == ORIGINE:
            q.bankID = NUMERO
    s.sequenceArchives[NUMERO] = ("SEQ_EN_zenus", a)
    # le groupe : comme GRP_EN_z060, sur NUMERO
    g0 = s.groups[ORIGINE][1]
    import copy
    g = []
    for e in g0:
        e2 = copy.copy(e)
        if e2.id == ORIGINE:
            e2.id = NUMERO
        g.append(e2)
    s.groups[NUMERO] = ("GRP_EN_zenus", g)
    return s.save()


def poser(rom):
    fid = rom.filenames.idOf(SDAT)
    rom.files[fid] = sdat_neuf(bytes(rom.files[fid]))
    fb = rom.filenames.idOf(MON_BTLDATA)
    b = bytearray(rom.files[fb])
    p = 4 + INDEX * 132
    assert struct.unpack_from("<H", b, p)[0] & 0x7FFF == 900
    struct.pack_into("<HH", b, p + 0x14, NUMERO, NUMERO)
    rom.files[fb] = bytes(b)


def verifier(rom):
    s = S.SDAT(bytes(rom.getFileByName(SDAT)))
    a = s.sequenceArchives[NUMERO][1]
    assert a is not None and s.banks[NUMERO][1] is not None and s.groups[NUMERO][1] is not None
    a.parse()
    assert len(a.sequences) == SON + 1 and a.sequences[SON][1].bankID == NUMERO
    b = rom.getFileByName(MON_BTLDATA)
    assert struct.unpack_from("<HH", b, 4 + INDEX * 132 + 0x14) == (NUMERO, NUMERO)


if __name__ == "__main__":
    rom = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    poser(rom)
    rom.saveToFile(sys.argv[2])
    verifier(ndspy.rom.NintendoDSRom.fromFile(sys.argv[2]))
    print("son du pas pose : archive", NUMERO)
