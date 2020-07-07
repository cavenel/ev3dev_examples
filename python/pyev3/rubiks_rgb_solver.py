#!/usr/bin/env python

from colormath.color_objects import sRGBColor, LabColor
from colormath.color_diff import delta_e_cmc
from colormath.color_conversions import convert_color
from itertools import permutations
from math import factorial
from pprint import pformat
from subprocess import Popen, PIPE, check_output
from time import sleep
from twophase_python.verify import verify as verify_parity
import argparse
import json
import logging
import operator
import os
import sys

log = logging.getLogger(__name__)

# Calculating color distances is expensive in terms of CPU so
# cache the results
dcache = {}

def get_color_distance(c1, c2, on_server):
    if (c1, c2) in dcache:
        return dcache[(c1, c2)]

    if (c2, c1) in dcache:
        return dcache[(c2, c1)]

    # Delta E CMC seems to be the most reliable method,
    # slightly more cpu expensive but not dramatically.
    # Other methods coupled with low permutation limit
    # on EV3 tend to mix Yellow/White and Orange/Red so
    # ignore on_server flag here and use Delta E CMC.
    distance = delta_e_cmc(c1, c2)

    dcache[(c1, c2)] = distance
    return distance

def hex_to_rgb(rgb_string):
    """
    Takes #112233 and returns the RGB values in decimal
    """
    if rgb_string.startswith('#'):
        rgb_string = rgb_string[1:]

    red = int(rgb_string[0:2], 16)
    green = int(rgb_string[2:4], 16)
    blue = int(rgb_string[4:6], 16)
    return (red, green, blue)

def rgb_to_labcolor(red, green, blue):
    rgb_obj = sRGBColor(red, green, blue, True)
    return convert_color(rgb_obj, LabColor)

def hashtag_rgb_to_labcolor(rgb_string):
    (red, green, blue) = hex_to_rgb(rgb_string)
    return rgb_to_labcolor(red, green, blue)


class Edge(object):

    def __init__(self, cube, pos1, pos2):
        self.valid = False
        self.square1 = cube.get_square(pos1)
        self.square2 = cube.get_square(pos2)
        self.cube = cube

    def __str__(self):
        return "%s%d/%s%d %s/%s" %\
            (self.square1.side, self.square1.position,
             self.square2.side, self.square2.position,
             self.square1.color.name, self.square2.color.name)

    def colors_match(self, colorA, colorB):
        if (colorA in (self.square1.color, self.square2.color) and
            colorB in (self.square1.color, self.square2.color)):
            return True
        return False

    def _get_color_distances(self, colorA, colorB):
        distanceAB = (get_color_distance(self.square1.rawcolor, colorA, self.cube.on_server) +
                      get_color_distance(self.square2.rawcolor, colorB, self.cube.on_server))

        distanceBA = (get_color_distance(self.square1.rawcolor, colorB, self.cube.on_server) +
                      get_color_distance(self.square2.rawcolor, colorA, self.cube.on_server))

        return (distanceAB, distanceBA)

    def color_distance(self, colorA, colorB):
        """
        Given two colors, return our total color distance
        """
        return min(self._get_color_distances(colorA, colorB))

    def update_colors(self, colorA, colorB):
        (distanceAB, distanceBA) = self._get_color_distances(colorA, colorB)

        if distanceAB < distanceBA:
            self.square1.color = colorA
            self.square2.color = colorB
        else:
            self.square1.color = colorB
            self.square2.color = colorA

    def validate(self):

        if self.square1.color == self.square2.color:
            self.valid = False
            log.info("%s is an invalid edge (duplicate colors)" % self)
        elif ((self.square1.color, self.square2.color) in self.cube.valid_edges or
            (self.square2.color, self.square1.color) in self.cube.valid_edges):
            self.valid = True
        else:
            self.valid = False
            log.info("%s is an invalid edge" % self)


class Corner(object):

    def __init__(self, cube, pos1, pos2, pos3):
        self.valid = False
        self.square1 = cube.get_square(pos1)
        self.square2 = cube.get_square(pos2)
        self.square3 = cube.get_square(pos3)
        self.cube = cube

    def __str__(self):
        return "%s%d/%s%d/%s%d %s/%s/%s" %\
            (self.square1.side, self.square1.position,
             self.square2.side, self.square2.position,
             self.square3.side, self.square3.position,
             self.square1.color.name, self.square2.color.name, self.square3.color.name)

    def colors_match(self, colorA, colorB, colorC):
        if (colorA in (self.square1.color, self.square2.color, self.square3.color) and
            colorB in (self.square1.color, self.square2.color, self.square3.color) and
            colorC in (self.square1.color, self.square2.color, self.square3.color)):
            return True
        return False

    def _get_color_distances(self, colorA, colorB, colorC):
        distanceABC = (get_color_distance(self.square1.rawcolor, colorA, self.cube.on_server) +
                       get_color_distance(self.square2.rawcolor, colorB, self.cube.on_server) +
                       get_color_distance(self.square3.rawcolor, colorC, self.cube.on_server))

        distanceCAB = (get_color_distance(self.square1.rawcolor, colorC, self.cube.on_server) +
                       get_color_distance(self.square2.rawcolor, colorA, self.cube.on_server) +
                       get_color_distance(self.square3.rawcolor, colorB, self.cube.on_server))

        distanceBCA = (get_color_distance(self.square1.rawcolor, colorB, self.cube.on_server) +
                       get_color_distance(self.square2.rawcolor, colorC, self.cube.on_server) +
                       get_color_distance(self.square3.rawcolor, colorA, self.cube.on_server))
        return (distanceABC, distanceCAB, distanceBCA)

    def color_distance(self, colorA, colorB, colorC):
        """
        Given three colors, return our total color distance
        """
        return min(self._get_color_distances(colorA, colorB, colorC))

    def update_colors(self, colorA, colorB, colorC):
        (distanceABC, distanceCAB, distanceBCA) = self._get_color_distances(colorA, colorB, colorC)
        min_distance = min(distanceABC, distanceCAB, distanceBCA)

        if min_distance == distanceABC:
            self.square1.color = colorA
            self.square2.color = colorB
            self.square3.color = colorC

        elif min_distance == distanceCAB:
            self.square1.color = colorC
            self.square2.color = colorA
            self.square3.color = colorB

        elif min_distance == distanceBCA:
            self.square1.color = colorB
            self.square2.color = colorC
            self.square3.color = colorA

    def validate(self):

        if (self.square1.color == self.square2.color or
            self.square1.color == self.square3.color or
            self.square2.color == self.square3.color):
            self.valid = False
            log.info("%s is an invalid edge (duplicate colors)" % self)
        elif ((self.square1.color, self.square2.color, self.square3.color) in self.cube.valid_corners or
            (self.square1.color, self.square3.color, self.square2.color) in self.cube.valid_corners or
            (self.square2.color, self.square1.color, self.square3.color) in self.cube.valid_corners or
            (self.square2.color, self.square3.color, self.square1.color) in self.cube.valid_corners or
            (self.square3.color, self.square1.color, self.square2.color) in self.cube.valid_corners or
            (self.square3.color, self.square2.color, self.square1.color) in self.cube.valid_corners):
            self.valid = True
        else:
            self.valid = False
            log.info("%s (%s, %s, %s) is an invalid corner" % (self, self.square1.color, self.square2.color, self.square3.color))


class Square(object):

    def __init__(self, side, cube, position, red, green, blue):
        self.cube = cube
        self.side = side
        self.position = position
        self.red = red
        self.green = green
        self.blue = blue
        self.rawcolor = rgb_to_labcolor(red, green, blue)
        self.color = None
        self.cie_data = []

    def __str__(self):
        return "%s%d" % (self.side, self.position)

    def find_closest_match(self, crayon_box, debug=False, set_color=True):
        self.cie_data = []

        for (color, color_obj) in crayon_box.iteritems():
            distance = get_color_distance(self.rawcolor, color_obj, self.cube.on_server)
            self.cie_data.append((distance, color_obj))
        self.cie_data = sorted(self.cie_data)

        distance = self.cie_data[0][0]
        color_obj = self.cie_data[0][1]

        if set_color:
            self.distance = distance
            self.color = color_obj

        if debug:
            #log.info("%s is %s\n%s\n" % (self, color, pformat(self.cie_data)))
            log.info("%s is %s" % (self, color_obj))

        return (color_obj, distance)


class CubeSide(object):

    def __init__(self, cube, name):
        self.cube = cube
        self.name = name # U, L, etc
        self.color = None # Will be the color of the middle square
        self.squares = {}

        if self.name == 'U':
            index = 0
        elif self.name == 'L':
            index = 1
        elif self.name == 'F':
            index = 2
        elif self.name == 'R':
            index = 3
        elif self.name == 'B':
            index = 4
        elif self.name == 'D':
            index = 5

        self.min_pos = (index * 9) + 1
        self.max_pos = (index * 9) + 9
        self.mid_pos = (self.min_pos + self.max_pos)/2
        self.edge_pos = (self.min_pos + 1, self.min_pos + 3, self.min_pos + 5, self.min_pos + 7)
        self.corner_pos = (self.min_pos, self.min_pos + 2, self.min_pos + 6, self.min_pos + 8)

        self.middle_square = None
        self.edge_squares = []
        self.corner_squares = []

        log.info("Side %s, min/mid/max %d/%d/%d" % (self.name, self.min_pos, self.mid_pos, self.max_pos))

    def __str__(self):
        return self.name

    def set_square(self, position, red, green, blue):
        self.squares[position] = Square(self, self.cube, position, red, green, blue)

        if position == self.mid_pos:
            self.middle_square = self.squares[position]

        elif position in self.edge_pos:
            self.edge_squares.append(self.squares[position])

        elif position in self.corner_pos:
            self.corner_squares.append(self.squares[position])


class RubiksColorSolver(object):
    """
    This class accepts a RGB value for all 54 squares on a Rubiks cube and
    figures out which of the 6 cube colors each square is.

    The names of the sides are (Up, Left, Front, Right, Back, Down)
      U
    L F R B
      D
    """

    def __init__(self, on_server):
        self.on_server = on_server
        self.width = 3
        self.blocks_per_side = self.width * self.width
        self.colors = []
        self.scan_data = {}
        self.tools_file = None
        self.cubex_file = None
        self.shutdown_flag = False

        # 4! = 24
        # 5! = 120
        # 6! = 720
        # 7! = 5040
        # 8! = 40320
        if on_server:
            # With a limit of 40320 it takes 3.6s to resolve the colors for a cube
            # With a limit of  5040 it takes 1.5s to resolve the colors for a cube
            # With a limit of   720 it takes 1.2s to resolve the colors for a cube
            # These numbers are from a beefy server, not EV3
            self.edge_permutation_limit = 5040
            self.corner_permutation_limit = 5040
        else:
            self.edge_permutation_limit = 720
            self.corner_permutation_limit = 720

        self.sides = {
          'U' : CubeSide(self, 'U'),
          'L' : CubeSide(self, 'L'),
          'F' : CubeSide(self, 'F'),
          'R' : CubeSide(self, 'R'),
          'B' : CubeSide(self, 'B'),
          'D' : CubeSide(self, 'D'),
        }

        self.sideU = self.sides['U']
        self.sideL = self.sides['L']
        self.sideF = self.sides['F']
        self.sideR = self.sides['R']
        self.sideB = self.sides['B']
        self.sideD = self.sides['D']

        self.side_order = ('U', 'L', 'F', 'R', 'B', 'D')
        self.edges = []
        self.corners = []

        self.crayola_colors = {
            'Rd' : hashtag_rgb_to_labcolor('#C91111'), # Red
            'Or' : hashtag_rgb_to_labcolor('#D84E09'), # Red Orange
            'OR' : hashtag_rgb_to_labcolor('#FF8000'), # Orange
            'Ye' : hashtag_rgb_to_labcolor('#F6EB20'), # Yellow
            'Yg' : hashtag_rgb_to_labcolor('#51C201'), # Yellow Green
            'Gr' : hashtag_rgb_to_labcolor('#1C8E0D'), # Green
            'Sy' : hashtag_rgb_to_labcolor('#09C5F4'), # Sky Blue
            'Bu' : hashtag_rgb_to_labcolor('#2862B9'), # Blue
            'Pu' : hashtag_rgb_to_labcolor('#7E44BC'), # Purple
            'Wh' : hashtag_rgb_to_labcolor('#FFFFFF'), # White
             #'Br' : hashtag_rgb_to_labcolor('#943F07'), # Brown...too easy to mistake this for red/orange
            'Bl' : hashtag_rgb_to_labcolor('#000000') # Black
        }

    # ================
    # Printing methods
    # ================
    def print_layout(self):
        log.info("""

           01 02 03
           04 05 06
           07 08 09
 10 11 12  19 20 21  28 29 30  37 38 39
 13 14 15  22 23 24  31 32 33  40 41 42
 16 17 18  25 26 27  34 35 36  43 44 45
           46 47 48
           49 50 51
           52 53 54

""")

    def print_cube(self):
        """
        R R R
        R R R
        R R R
 Y Y Y  B B B  W W W  G G G
 Y Y Y  B B B  W W W  G G G
 Y Y Y  B B B  W W W  G G G
        O O O
        O O O
        O O O
        """
        data = [[], [], [], [], [], [], [], [], []]

        for side_name in self.side_order:
            side = self.sides[side_name]

            if side_name == 'U':
                line_number = 0
                prefix =  '          '
            elif side_name in ('L', 'F', 'R', 'B'):
                line_number = 3
                prefix =  ''
            else:
                line_number = 6
                prefix =  '          '

            for x in xrange(3):
                data[line_number].append(prefix)
                data[line_number].append('%2s' % side.squares[side.min_pos + (x*3)].color.name)
                data[line_number].append('%2s' % side.squares[side.min_pos + 1 + (x*3)].color.name)
                data[line_number].append('%2s' % side.squares[side.min_pos + 2 + (x*3)].color.name)
                line_number += 1

        output = []
        for row in data:
            output.append(' '.join(row))

        log.info("Cube\n\n%s\n" % '\n'.join(output))

    def cube_for_kociemba(self):
        data = []

        color_to_num = {}

        for side in self.sides.itervalues():
            color_to_num[side.middle_square.color] = side.name

        for side in (self.sideU, self.sideR, self.sideF, self.sideD, self.sideL, self.sideB):
            for x in xrange(side.min_pos, side.max_pos+1):
                color = side.squares[x].color
                data.append(color_to_num[color])

        log.info('Cube for kociemba: %s' % ''.join(map(str, data)))
        return data

    def cube_for_cubex(self):
        """
        Return a numerical representation of the colors.  Assign each color a
        number and then print the color number for all squares (from 1 to 54).
        """
        data = []

        color_index = 1
        color_to_num = {}

        for side_name in self.side_order:
            side = self.sides[side_name]
            color_to_num[side.middle_square.color] = color_index
            color_index += 1

        for side_name in self.side_order:
            side = self.sides[side_name]

            for x in xrange(side.min_pos, side.max_pos+1):
                color = side.squares[x].color
                data.append(color_to_num[color])
        log.info('Cube for cubex: %s' % ''.join(map(str, data)))
        return data

    def get_side(self, position):
        """
        Given a position on the cube return the CubeSide object
        that contians that position
        """
        for side in self.sides.itervalues():
            if position >= side.min_pos and position <= side.max_pos:
                return side
        raise Exception("Could not find side for %d" % position)

    def get_square(self, position):
        side = self.get_side(position)
        return side.squares[position]

    def enter_scan_data(self, scan_data):
        self.scan_data = scan_data

        for (position, (red, green, blue)) in self.scan_data.iteritems():
            side = self.get_side(position)
            side.set_square(position, red, green, blue)

    def get_squares_with_color(self, target_color):
        squares = []
        for side in self.sides.itervalues():
            for square in side.squares.itervalues():
                if square.color == target_color:
                    squares.append(square)
        return squares

    def set_color_name(self, square):
        """
        Assign a color name to the square's LabColor object.
        This name is only used for debug output.
        """
        (crayola_color_matched, distance) = square.find_closest_match(self.crayola_colors, set_color=False)

        for (crayola_color_name, crayola_color) in self.crayola_colors.iteritems():
            if crayola_color == crayola_color_matched:
                square.rawcolor.name = crayola_color_name
                break

        del self.crayola_colors[crayola_color_name]

    def find_top_six_colors(self):
        self.crayon_box = {}
        for side in self.sides.itervalues():
            self.crayon_box[side.name] = side.middle_square.rawcolor
            self.set_color_name(side.middle_square)

        output = []
        for side_name in self.side_order:
            output.append("  %s : %s %s" % (side_name, self.crayon_box[side_name].name, self.crayon_box[side_name]))
        log.info("Crayon box (middle square colors):\n%s" % '\n'.join(output))

    def identify_middle_squares(self):
        log.info('ID middle square colors')

        for side_name in self.side_order:
            side = self.sides[side_name]
            side.color = self.crayon_box[side_name]

            # The middle square must match the color in the crayon_box for this side
            # so pass a dictionary with just this one color
            side.middle_square.find_closest_match({'foo' : side.color})
            log.info("%s is %s" % (side.middle_square, side.middle_square.color.name))
        log.info('\n')

        self.valid_edges = []
        self.valid_edges.append((self.sideU.color, self.sideF.color))
        self.valid_edges.append((self.sideU.color, self.sideL.color))
        self.valid_edges.append((self.sideU.color, self.sideR.color))
        self.valid_edges.append((self.sideU.color, self.sideB.color))

        self.valid_edges.append((self.sideF.color, self.sideL.color))
        self.valid_edges.append((self.sideF.color, self.sideR.color))
        self.valid_edges.append((self.sideB.color, self.sideL.color))
        self.valid_edges.append((self.sideB.color, self.sideR.color))

        self.valid_edges.append((self.sideD.color, self.sideF.color))
        self.valid_edges.append((self.sideD.color, self.sideL.color))
        self.valid_edges.append((self.sideD.color, self.sideR.color))
        self.valid_edges.append((self.sideD.color, self.sideB.color))
        self.valid_edges = sorted(self.valid_edges)

        self.valid_corners = []
        self.valid_corners.append((self.sideU.color, self.sideF.color, self.sideL.color))
        self.valid_corners.append((self.sideU.color, self.sideR.color, self.sideF.color))
        self.valid_corners.append((self.sideU.color, self.sideL.color, self.sideB.color))
        self.valid_corners.append((self.sideU.color, self.sideB.color, self.sideR.color))

        self.valid_corners.append((self.sideD.color, self.sideL.color, self.sideF.color))
        self.valid_corners.append((self.sideD.color, self.sideF.color, self.sideR.color))
        self.valid_corners.append((self.sideD.color, self.sideB.color, self.sideL.color))
        self.valid_corners.append((self.sideD.color, self.sideR.color, self.sideB.color))
        self.valid_corners = sorted(self.valid_corners)

    def identify_edge_squares(self):
        log.info('ID edge square colors')

        for side in self.sides.itervalues():
            for square in side.edge_squares:
                square.find_closest_match(self.crayon_box)

    def identify_corner_squares(self):
        log.info('ID corner square colors')

        for side in self.sides.itervalues():
            for square in side.corner_squares:
                square.find_closest_match(self.crayon_box)

    def create_edges_and_corners(self):
        """
        The Edge objects below are used to represent a tuple of two Square objects.
        Not to be confused with self.valid_edges which are the tuples of color
        combinations we know we must have based on the colors of the six sides.
        """

        # Edges
        # U
        self.edges.append(Edge(self, 2, 38))
        self.edges.append(Edge(self, 4, 11))
        self.edges.append(Edge(self, 6, 29))
        self.edges.append(Edge(self, 8, 20))

        # F
        self.edges.append(Edge(self, 15, 22))
        self.edges.append(Edge(self, 24, 31))
        self.edges.append(Edge(self, 26, 47))

        # L
        self.edges.append(Edge(self, 13, 42))
        self.edges.append(Edge(self, 17, 49))

        # R
        self.edges.append(Edge(self, 35, 51))
        self.edges.append(Edge(self, 33, 40))

        # B
        self.edges.append(Edge(self, 44, 53))

        # Corners
        # U
        self.corners.append(Corner(self, 1, 10, 39))
        self.corners.append(Corner(self, 3, 37, 30))
        self.corners.append(Corner(self, 7, 19, 12))
        self.corners.append(Corner(self, 9, 28, 21))

        # B
        self.corners.append(Corner(self, 46, 18, 25))
        self.corners.append(Corner(self, 48, 27, 34))
        self.corners.append(Corner(self, 52, 45, 16))
        self.corners.append(Corner(self, 54, 36, 43))

    def valid_cube_parity(self, fake_corner_parity):
        """
        verify_parity() returns
         0: Cube is solvable
        -1: There is not exactly one facelet of each colour
        -2: Not all 12 edges exist exactly once
        -3: Flip error: One edge has to be flipped
        -4: Not all 8 corners exist exactly once
        -5: Twist error: One corner has to be twisted
        -6: Parity error: Two corners or two edges have to be exchanged

        Given how we assign colors it is not possible for us to generate a cube
        that returns -1, -2, or -4
        """
        cube_string = ''.join(map(str, self.cube_for_kociemba()))

        if fake_corner_parity:

            # Fill in the corners with data that we know to be valid parity
            # We do this when we are validating the parity of the edges
            #log.info('pre  cube string: %s' % cube_string)
            cube_string = list(cube_string)
            cube_string[0] = 'U'
            cube_string[2] = 'U'
            cube_string[6] = 'U'
            cube_string[8] = 'U'

            cube_string[9] = 'R'
            cube_string[11] = 'R'
            cube_string[15] = 'R'
            cube_string[17] = 'R'

            cube_string[18] = 'F'
            cube_string[20] = 'F'
            cube_string[24] = 'F'
            cube_string[26] = 'F'

            cube_string[27] = 'D'
            cube_string[29] = 'D'
            cube_string[33] = 'D'
            cube_string[35] = 'D'

            cube_string[36] = 'L'
            cube_string[38] = 'L'
            cube_string[42] = 'L'
            cube_string[44] = 'L'

            cube_string[45] = 'B'
            cube_string[47] = 'B'
            cube_string[51] = 'B'
            cube_string[53] = 'B'
            cube_string = ''.join(cube_string)
            #log.info('post cube string: %s' % cube_string)

        result = verify_parity(cube_string)

        if not result:
            return True

        # Must ignore this one since we made up the corners
        if fake_corner_parity and result == -6:
            return True

        log.info("parity is %s" % result)
        return False

    def valid_edge_parity(self):
        return self.valid_cube_parity(fake_corner_parity=True)

    def resolve_edge_squares(self):
        log.info('Resolve edges')

        # Initially we flag all of our Edge objects as invalid
        for edge in self.edges:
            edge.valid = False

        # And our 'needed' list will hold all 12 edges
        needed_edges = sorted(self.valid_edges)

        unresolved_edges = [edge for edge in self.edges if edge.valid is False]
        permutation_count = factorial(len(needed_edges))
        best_match_total_distance = 0

        # 12 edges will mean 479,001,600 permutations which is too many.  Examine
        # all 12 edges and find the one we can match against a needed_edge that produces
        # the lowest color distance. update_colors() for this edge, mark it as
        # valid and remove it from the needed_edges.  Repeat this until the
        # number of permutations of needed_edges is down to our permutation_limit.
        while permutation_count > self.edge_permutation_limit:
            scores = []
            for edge in unresolved_edges:
                for (colorA, colorB) in needed_edges:
                    distance = edge.color_distance(colorA, colorB)
                    scores.append((distance, edge, (colorA, colorB)))

            scores = sorted(scores)
            (distance, edge_best_match, (colorA, colorB)) = scores[0]

            log.info("%s/%s best match is %s with distance %d (permutations %d)" %\
                (colorA.name, colorB.name, edge_best_match, distance, permutation_count))
            best_match_total_distance += distance
            edge_best_match.update_colors(colorA, colorB)
            edge_best_match.valid = True
            needed_edges.remove((colorA, colorB))

            unresolved_edges= [edge for edge in self.edges if edge.valid is False]
            permutation_count = factorial(len(needed_edges))

        score_per_permutation = []

        for edge_permutation in permutations(unresolved_edges):

            if self.shutdown_flag:
                return

            total_distance = 0

            for (edge, (colorA, colorB)) in zip(edge_permutation, needed_edges):
                total_distance += edge.color_distance(colorA, colorB)

            score_per_permutation.append((total_distance, edge_permutation))

        score_per_permutation = sorted(score_per_permutation)

        # Now traverse the permutations from best score to worst. The first
        # permutation that produces a set of edges with valid parity is the
        # permutation we want (most of the time the first entry has valid parity).
        for (_, permutation) in score_per_permutation:

            if self.shutdown_flag:
                return

            total_distance = best_match_total_distance

            for (edge_best_match, (colorA, colorB)) in zip(permutation, needed_edges):
                distance = edge_best_match.color_distance(colorA, colorB)
                total_distance += distance

                log.info("%s/%s potential match is %s with distance %d" % (colorA.name, colorB.name, edge_best_match, distance))
                edge_best_match.update_colors(colorA, colorB)
                edge_best_match.valid = True

            if self.valid_edge_parity():
                log.info("Total distance: %d, edge parity is valid" % total_distance)
                break
            else:
                log.info("Total distance: %d, edge parity is NOT valid" % total_distance)

        log.info('\n')

    def resolve_corner_squares(self):
        log.info('Resolve corners')

        # Initially we flag all of our Edge objects as invalid
        for corner in self.corners:
            corner.valid = False

        # And our 'needed' list will hold all 8 corners.
        needed_corners = sorted(self.valid_corners)

        unresolved_corners = [corner for corner in self.corners if corner.valid is False]
        permutation_count = factorial(len(needed_corners))
        best_match_total_distance = 0

        # 8 corners will mean 40320 permutations which is too many.  Examine
        # all 8 and find the one we can match against a needed_corner that produces
        # the lowest color distance. update_colors() for this corner, mark it as
        # valid and remove it from the needed_corners.  Repeat this until the
        # number of permutations of needed_corners is down to our permutation_limit.
        while permutation_count > self.corner_permutation_limit:
            scores = []
            for corner in unresolved_corners:
                for (colorA, colorB, colorC) in needed_corners:
                    distance = corner.color_distance(colorA, colorB, colorC)
                    scores.append((distance, corner, (colorA, colorB, colorC)))

            scores = sorted(scores)
            (distance, corner_best_match, (colorA, colorB, colorC)) = scores[0]

            #if distance > 15:
            #    break

            log.info("%s/%s/%s best match is %s with distance %d (permutations %d)" %\
                (colorA.name, colorB.name, colorC.name, corner_best_match, distance, permutation_count))
            best_match_total_distance += distance
            corner_best_match.update_colors(colorA, colorB, colorC)
            corner_best_match.valid = True
            needed_corners.remove((colorA, colorB, colorC))

            unresolved_corners = [corner for corner in self.corners if corner.valid is False]
            permutation_count = factorial(len(needed_corners))

        score_per_permutation = []

        for corner_permutation in permutations(unresolved_corners):

            if self.shutdown_flag:
                return

            total_distance = 0

            for (corner, (colorA, colorB, colorC)) in zip(corner_permutation, needed_corners):
                total_distance += corner.color_distance(colorA, colorB, colorC)

            score_per_permutation.append((total_distance, corner_permutation))

        score_per_permutation = sorted(score_per_permutation)

        # Now traverse the permutations from best score to worst. The first
        # permutation that produces a cube with valid parity is the permutation
        # we want (most of the time the first entry has valid parity).
        for (_, permutation) in score_per_permutation:

            if self.shutdown_flag:
                return

            total_distance = best_match_total_distance

            for (corner_best_match, (colorA, colorB, colorC)) in zip(permutation, needed_corners):
                distance = corner_best_match.color_distance(colorA, colorB, colorC)
                total_distance += distance
                log.info("%s/%s/%s best match is %s with distance %d" % (colorA.name, colorB.name, colorC.name, corner_best_match, distance))
                corner_best_match.update_colors(colorA, colorB, colorC)
                corner_best_match.valid = True

            if self.valid_cube_parity(fake_corner_parity=False):
                log.info("Total distance: %d, cube parity is valid" % total_distance)
                break
            else:
                log.info("Total distance: %d, cube parity is NOT valid" % total_distance)

        log.info('\n')


    def crunch_colors(self):
        log.info('Discover the six colors')
        self.find_top_six_colors()

        # 6 middles, 12 edges, 8 corners
        self.identify_middle_squares()
        self.identify_edge_squares()
        self.identify_corner_squares()

        self.create_edges_and_corners()
        self.resolve_edge_squares()
        self.resolve_corner_squares()

        if self.shutdown_flag:
            return (None, None)

        self.print_cube()
        self.print_layout()
        return (self.cube_for_kociemba(), self.cube_for_cubex())

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--rgb', help='RGB json', default=None)
    parser.add_argument('--method', help='cubex or kociemba', default='kociemba')
    args = parser.parse_args()

    logging.basicConfig(filename='rubiks-rgb-solver.log',
                        level=logging.INFO,
                        format='%(asctime)s %(levelname)5s: %(message)s')
    log = logging.getLogger(__name__)

    try:
        from testdata import edge_parity, solved_cube1

        cube = RubiksColorSolver(True)

        if args.rgb:
            scan_data_str_keys = json.loads(args.rgb)
            scan_data = {}
            for (key, value) in scan_data_str_keys.iteritems():
                scan_data[int(key)] = value
            cube.enter_scan_data(scan_data)
        else:
            cube.enter_scan_data(solved_cube1)

        (kociemba, cubex) = cube.crunch_colors()

        if args.method == 'kociemba':
            print ''.join(map(str, kociemba))
        else:
            print ''.join(map(str, cubex))

    except Exception as e:
        log.exception(e)
        sys.exit(1)
