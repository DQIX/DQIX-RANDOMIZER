"""Les 256 monstres de Dragon Quest IX, par leur numero de bestiaire.

POURQUOI UNE LISTE BLANCHE. Le projet a essaye deux listes noires avant
celle-ci, et les deux se sont trompees :

  - « n'apparait jamais en vadrouille en vanilla » ecartait 69 monstres
    ordinaires et laissait passer dix-sept vrais boss, qui rodent comme symboles
    dans les antres ;
  - la categorie « bosses » du wiki anglais est editoriale : elle melange une
    page de liste, une faction et un groupe de generaux avec les monstres, et
    rien ne garantit qu'elle soit complete.

Le bestiaire du jeu, lui, NUMEROTE. Les monstres vont de 1 a 256 -- le 256e est
le Pelagosaure -- et tout ce qui suit est un boss. C'est un critere du jeu
lui-meme, pas un jugement, et il se verifie d'un coup d'oeil.

Source : la liste « Par numero » de
https://dragonquest.fandom.com/fr/wiki/Liste_des_monstres_de_Dragon_Quest_IX
tronquee a 256, appariee a la table de noms FRANCAISE de la ROM.

UN NOM, PLUSIEURS IDENTIFIANTS. La table interne compte plusieurs entrees pour
un meme monstre -- variantes de rang, versions d'antre -- d'ou 288 identifiants
pour 256 noms. Cinq noms sont orthographies autrement par le wiki et ont ete
rapproches explicitement : Frapillon/frappillon, Chienlycathrope/chienlycanthrope,
Ruduceros/rudoceros, Canibelle/cannibelle, Hypotermiasme/hypothermiasme.
"""

MONSTRES = {
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11,
    12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23,
    24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35,
    36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47,
    48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
    60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71,
    72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83,
    84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95,
    96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107,
    108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119,
    120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131,
    132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143,
    144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155,
    156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167,
    168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179,
    180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191,
    192, 193, 194, 195, 196, 197, 198, 200, 201, 203, 204, 205,
    206, 207, 209, 211, 212, 213, 214, 215, 216, 218, 219, 220,
    221, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232,
    233, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 244,
    245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255, 256,
    257, 258, 259, 260, 261, 262, 263, 264, 265, 266, 267, 268,
    269, 270, 271, 272, 273, 274, 275, 276, 277, 278, 279, 280,
    281, 303, 305, 306, 307, 309, 310, 311, 312, 313, 315, 316,
}
