#!/usr/bin/env python
# -*- coding: utf8 -*-

import subprocess, os, sys

facets_name = [
"UF",
"UR",
"UB",
"UL",
"DF",
"DR",
"DB",
"DL",
"FR",
"FL",
"BR",
"BL",
"UFR",
"URB",
"UBL",
"ULF",
"DRF",
"DFL",
"DLB",
"DBR",
]

#   L1   : UF UR UB BL DF DR DB FL FR UL BR DL UFR URB DLB UBL DRF ULF DFL DBR
facets_position = {
'UF': (8,20),
'UR': (6,29),
'UB': (2,38),
'UL': (4,11),
'DF': (47,26),
'DR': (51,35),
'DB': (53,44),
'DL': (49,17),
'FR': (24,31),
'FL': (22,15),
'BR': (40,33),
'BL': (42,13),
'UFR': (9,21,28),
'URB': (3,30,37),
'UBL': (1,39,10),
'ULF': (7,12,19),
'DRF': (48,34,27),
'DFL': (46,25,18),
'DLB': (52,16,45),
'DBR': (54,43,36)
}

cube = sys.argv[1]
cube = list(cube)

faces_color= {}
faces_color["U"] = cube[4]
faces_color["L"] = cube[13]
faces_color["F"] = cube[22]
faces_color["R"] = cube[31]
faces_color["B"] = cube[40]
faces_color["D"] = cube[49]
faces_color = {v:k for k, v in faces_color.items()}

def colors_to_facet(colors):
    faces = [faces_color[c] for c in colors]
    name = "".join(faces)
    return name

faces = ["U","L","F","R","B","D"]
twophase_in = ""
for n in facets_name:
    colors = [cube[i-1] for i in facets_position[n]]
    twophase_in += colors_to_facet(colors) + " "

cmd = ["./twophase", "-s", "25", "-t", "1", "-q"]
print ' '.join(cmd)
print twophase_in

process = subprocess.Popen(cmd,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
process.stdin.write(twophase_in)

result = process.communicate()[0].split("\n")
moves = result[0]
chunks, chunk_size = len(moves), 2
list_moves = [ moves[i:i+chunk_size] for i in range(0, chunks, chunk_size) ]
print " ".join(list_moves)
