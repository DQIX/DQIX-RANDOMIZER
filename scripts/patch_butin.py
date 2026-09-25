#!/usr/bin/env python3
"""Le butin des monstres tire A CHAQUE COMBAT, et non plus fixe par espece.

CE QUE LE JEU FAIT (research §81). Pour chaque monstre vaincu, la fonction de
tirage de l'overlay 23 lit l'enregistrement `mon_btldata` du monstre, tire sa
classe de taux (rare `+0x03`, puis commune `+0x02`), et, si le tirage reussit,
lit l'objet a donner :

    0x021F4A10   ldrh r1, [fp, #6]     l'objet RARE
    0x021F4AD8   ldrh r1, [fp, #4]     l'objet COMMUN

puis le range dans la liste du butin (`strh r1, [sb]`). Un monstre donne donc
toujours les memes deux objets -- c'est ce que le joueur a vu (ZER-39 : « les
gluants drop le meme objet tout le temps »), randomisation de la 1.2 comprise :
elle ne changeait l'objet qu'une fois, a la construction.

CE QUE FAIT CE PATCH. Les deux `ldrh` deviennent un `bl` vers une greffe qui
relit l'objet d'origine puis, s'il n'est pas nul, le REMPLACE par un objet tire
au hasard dans le pool (les 1 088 objets placables : ni objets importants, ni
entrees de debogage). Les CHANCES DE BUTIN NE BOUGENT PAS : seul l'objet change,
et une place vide (objet 0) reste vide.

DEUX MODES, comme toute regle d'equilibrage (garde-fous §4) :

  * `rares`   un objet 4 ou 5 etoiles tire n'est garde qu'une fois sur
              DIVISEUR (sinon on retire) : ils restent possibles partout,
              mais rares ;
  * `libre`   n'importe quel objet a chances egales, l'equipement legendaire
              compris.

POURQUOI PAS UNE TABLE DANS `mon_btldata.nat`. Premiere idee, mesuree fausse
le 25 septembre : au moment du tirage, le fichier n'est plus en memoire. Le
combat en copie les SEULS enregistrements des especes presentes dans une
petite table du tas (`0x02070CF4`, depuis le tampon statique 0x0211E33C qui
sert ensuite a autre chose), et y reecrit meme les classes de taux, l'or et
l'experience depuis la fiche de terrain (overlay 0, 0x02165B90). D'ou aussi :
forcer les classes dans `mon_btldata` (rom_drops_garantis.py) n'a plus d'effet
sur les monstres de terrain.

OU VIT LA GREFFE, ET SA TABLE. Derriere le BSS de l'overlay 23. L'overlay
partage sa place (0x021D8A40) avec les overlays 22 a 30, et le 24 va jusqu'a
0x02200160 : il reste 544 octets apres le BSS du 23 (0x021FFF40). Mesure : le
23 et le 24 se relaient pendant un combat, et ce qu'on lit au-dela du 23 n'est
que le reste du 24, jamais ecrit tant que le 23 est la. Pour que le chargeur y
ecrive la greffe, le BSS devient de la DONNEE (0x560 zeros, ce que le chargeur
aurait ecrit), suivie de la greffe ; `bssSize` passe a 0. Les adresses du BSS
ne bougent pas.

La table tient le pool en suites d'identifiants consecutifs, un octet par
suite (voir `encoder`) : 1 088 objets en moins de 300 octets.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

OVL = 23
SITE_RARE = 0x021F4A10          # ldrh r1, [fp, #6]
SITE_COMMUN = 0x021F4AD8        # ldrh r1, [fp, #4]
ORIGINE_RARE = "ldrh r1, [fp, #6]"
ORIGINE_COMMUN = "ldrh r1, [fp, #4]"
PLAFOND_SLOT = 0x02200160       # fin du plus grand overlay de la place (le 24)
RAND_BELOW = 0x02032380

# MODE `rares` : un objet 4 ou 5 etoiles tire n'est garde qu'une fois sur
# DIVISEUR ; sinon on retire (ESSAIS fois au plus, puis on le garde). Le pool
# compte 132 objets 4-5 etoiles sur 1 088 (12,1 %) : avec 8, il en sort 1,7 %
# des butins (5 etoiles 0,3 %, 4 etoiles 1,4 %).
DIVISEUR = 8
ESSAIS = 8


def encoder(pool, etoiles, drapeau):
    """Le pool en suites d'identifiants consecutifs, un octet par suite.

    Octet b : bit 7 = suite d'objets 4-5 etoiles (si `drapeau`), bits 6-4 =
    ecart depuis la fin de la suite precedente (7 : l'ecart suit sur un octet,
    et 255 sur cet octet : sur deux octets, poids faible d'abord), bits 3-0 =
    longueur (0 : elle suit sur un octet). 1 088 objets tiennent en ~280 octets.
    """
    suites = []
    for i in sorted(pool):
        t = drapeau and etoiles.get(i, 0) >= 4
        if (suites and i == suites[-1][0] + suites[-1][1]
                and suites[-1][2] == t and suites[-1][1] < 255):
            suites[-1][1] += 1
        else:
            suites.append([i, 1, t])
    base = suites[0][0]
    out = bytearray()
    prec = base
    for debut, n, t in suites:
        g = debut - prec
        b = (0x80 if t else 0) | ((g if g < 7 else 7) << 4) | (n if n < 16 else 0)
        out.append(b)
        if g >= 7:
            if g < 255:
                out.append(g)
            else:
                out += bytes([255, g & 0xFF, g >> 8])
        if n >= 16:
            out.append(n)
        prec = debut + n
    return base, bytes(out)


def decoder(base, donnees):
    """Relit `encoder` : rend [(identifiant, drapeau)] dans l'ordre."""
    out, i, cur = [], 0, base
    while i < len(donnees):
        b = donnees[i]; i += 1
        g = (b >> 4) & 7
        if g == 7:
            g = donnees[i]; i += 1
            if g == 255:
                g = donnees[i] | (donnees[i + 1] << 8); i += 2
        n = b & 15
        if n == 0:
            n = donnees[i]; i += 1
        cur += g
        out += [(cur + k, bool(b & 0x80)) for k in range(n)]
        cur += n
    return out


def construire_table(rom, mode):
    """En-tete (u16 nombre, u16 premier identifiant) puis les suites."""
    import objets
    pool = objets.pool(rom)
    etoiles = objets.raretes(rom, "en")
    base, donnees = encoder(pool, etoiles, mode == "rares")
    relu = decoder(base, donnees)
    assert [i for i, _t in relu] == sorted(pool)
    return struct.pack("<HH", len(pool), base) + donnees


def greffe(adr, mode, table):
    """Le code, puis la table. Rend les octets a poser a `adr`."""
    from patch_hasard import assembler

    def lignes(d_table):
        return [
            # DEUX ENTREES, une par site : chacune rejoue son `ldrh`, et `lr`
            # (pose par le `bl` du site) ramene a l'instruction suivante.
            "ldrh r1, [fp, #6]",
            "b #{@tirage}",
            "ldrh r1, [fp, #4]",
            "tirage:",
            "push {r4, r5, r6, r7, lr}",
            "movs r4, r1",                  # place vide : elle le reste
            "beq #{@fin}",
            "mov r7, #%d" % ESSAIS,
            "encore:",
            "ici:",
            "add r5, pc, #%d" % d_table,     # r5 = la table (adresse fixe)
            "ldrh r0, [r5]",                # nombre d'objets du pool
            "bl #%d" % RAND_BELOW,          # r0 = k dans [0, nombre[
            "ldrh r6, [r5, #2]",            # premier identifiant
            "add r5, r5, #4",
            # LE DECODAGE : on saute les suites jusqu'a celle qui contient k.
            "suite:",
            "ldrb r2, [r5], #1",
            "lsr r3, r2, #4",
            "and r3, r3, #7",
            "cmp r3, #7",
            "bne #{@ecart_lu}",
            "ldrb r3, [r5], #1",
            "cmp r3, #255",
            "bne #{@ecart_lu}",
            "ldrb r3, [r5], #1",
            "ldrb ip, [r5], #1",
            "orr r3, r3, ip, lsl #8",
            "ecart_lu:",
            "add r6, r6, r3",
            "ands r1, r2, #15",
            "bne #{@longueur_lue}",
            "ldrb r1, [r5], #1",
            "longueur_lue:",
            "cmp r0, r1",
            "blt #{@trouve}",
            "sub r0, r0, r1",
            "add r6, r6, r1",
            "b #{@suite}",
            "trouve:",
            "add r4, r6, r0",
            # MODE `rares` : une suite 4-5 etoiles ne passe qu'une fois sur
            # DIVISEUR. En mode `libre`, aucune suite n'a le drapeau.
            "tst r2, #0x80",
            "beq #{@fin}",
            "subs r7, r7, #1",
            "beq #{@fin}",
            "mov r0, #%d" % DIVISEUR,
            "bl #%d" % RAND_BELOW,
            "cmp r0, #0",
            "bne #{@encore}",
            "fin:",
            "mov r1, r4",
            "pop {r4, r5, r6, r7, pc}",
            "table:",
        ]
    etiq = {}
    code = assembler(lignes(0), adr, etiquettes_out=etiq)
    d = etiq["table"] - (etiq["ici"] + 8)
    code = assembler(lignes(d), adr, etiquettes_out=etiq)
    return code + table


def _desas(data, base, adr):
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
    o = adr - base
    ins = next(md.disasm(bytes(data[o:o + 4]), adr), None)
    return ("%s %s" % (ins.mnemonic, ins.op_str)) if ins else "?"


def patcher(rom, mode="rares", bavard=True):
    """Pose la greffe et sa table derriere le BSS de l'overlay 23.
    `mode` : `rares` ou `libre`. Rend le nombre d'objets du pool."""
    import ndspy.code
    from patch_hasard import assembler
    if mode not in ("rares", "libre"):
        raise ValueError(mode)
    table = construire_table(rom, mode)
    ovl = rom.loadArm9Overlays()
    o = ovl[OVL]
    base = o.ramAddress
    d = bytearray(o.data)
    for site, attendu in ((SITE_RARE, ORIGINE_RARE),
                          (SITE_COMMUN, ORIGINE_COMMUN)):
        lu = _desas(d, base, site)
        if lu != attendu:
            raise SystemExit("overlay 23 : a %#010x attendu %r, lu %r"
                             % (site, attendu, lu))
    if len(d) != o.ramSize or o.bssSize != 0x560:
        raise SystemExit("overlay 23 : disposition inattendue (deja patche ?)")
    adr = base + o.ramSize + o.bssSize          # 0x021FFF40
    bloc = greffe(adr, mode, table)
    if adr + len(bloc) > PLAFOND_SLOT:
        raise SystemExit("greffe + table : %d o, depasse la place des "
                         "overlays 22-30 (%d o libres)"
                         % (len(bloc), PLAFOND_SLOT - adr))
    # LE BSS DEVIENT DE LA DONNEE : les zeros que le chargeur aurait ecrits,
    # puis la greffe. Les adresses du BSS ne bougent pas.
    d += bytes(o.bssSize) + bloc
    d[SITE_RARE - base:SITE_RARE - base + 4] =         assembler(["bl #%d" % adr], SITE_RARE)
    d[SITE_COMMUN - base:SITE_COMMUN - base + 4] =         assembler(["bl #%d" % (adr + 8)], SITE_COMMUN)
    o.data = bytes(d)
    o.ramSize = len(d)
    o.bssSize = 0
    rom.files[o.fileID] = o.save(compress=True)
    rom.arm9OverlayTable = ndspy.code.saveOverlayTable(ovl)
    n = struct.unpack_from("<H", table, 0)[0]
    if bavard:
        print("  greffe   : %d o de code + %d o de table a %#010x "
              "(%d o libres), pool de %d objets"
              % (len(bloc) - len(table), len(table), adr,
                 PLAFOND_SLOT - adr, n))
        if mode == "rares":
            print("  rarete   : un objet 4-5 etoiles n'est garde qu'une fois "
                  "sur %d" % DIVISEUR)
        print("  sites    : %#010x (rare), %#010x (commun)"
              % (SITE_RARE, SITE_COMMUN))
    return n


def verifier(rom):
    """Relit la ROM : les deux sites visent la greffe, et la table decode
    exactement le pool. Rend le mode lu."""
    import objets
    o = rom.loadArm9Overlays()[OVL]
    base = o.ramAddress
    adr = 0x021FFF40
    if o.bssSize != 0 or base + o.ramSize <= adr:
        raise AssertionError("overlay 23 : greffe absente")
    for site, cible in ((SITE_RARE, adr), (SITE_COMMUN, adr + 8)):
        lu = _desas(o.data, base, site)
        if lu != "bl #%#x" % cible:
            raise AssertionError("overlay 23 : %#010x lit %r" % (site, lu))
    bloc = bytes(o.data[adr - base:])
    for mode in ("rares", "libre"):
        table = construire_table(rom, mode)
        if bloc == greffe(adr, mode, table):
            break
    else:
        raise AssertionError("overlay 23 : greffe ou table inattendue")
    n, premier = struct.unpack_from("<HH", table, 0)
    relu = decoder(premier, table[4:])
    if len(relu) != n or {i for i, _t in relu} != set(objets.pool(rom)):
        raise AssertionError("table du butin : ne decode pas le pool")
    return mode


if __name__ == "__main__":
    import ndspy.rom
    if len(sys.argv) < 3:
        sys.exit("usage: patch_butin.py <rom.nds> <sortie.nds> [rares|libre]")
    r = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    patcher(r, sys.argv[3] if len(sys.argv) > 3 else "rares")
    print(verifier(r))
    r.saveToFile(sys.argv[2])
    print("ecrit :", sys.argv[2])
