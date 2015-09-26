#!/usr/bin/env python

from colormath.color_objects import sRGBColor, LabColor
from colormath.color_diff import delta_e_cie1976
from colormath.color_conversions import convert_color
from itertools import permutations
from math import factorial
from pprint import pformat
from subprocess import Popen, PIPE
from time import sleep
import logging
import os
import sys

log = logging.getLogger(__name__)

# Calculating color distances is expensive in terms of CPU so
# cache the results
dcache = {}

def get_color_distance(c1, c2):
    if (c1, c2) in dcache:
        return dcache[(c1, c2)]

    if (c2, c1) in dcache:
        return dcache[(c2, c1)]

    # delta_e_cie2000 is better but is 3x slower on an EV3...1976 is good enough
    #distance = delta_e_cie2000(c1, c2)
    distance = delta_e_cie1976(c1, c2)
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
        distanceAB = (get_color_distance(self.square1.rawcolor, colorA) +
                      get_color_distance(self.square2.rawcolor, colorB))

        distanceBA = (get_color_distance(self.square1.rawcolor, colorB) +
                      get_color_distance(self.square2.rawcolor, colorA))

        return (distanceAB, distanceBA)

    def color_distance(self, colorA, colorB):
        """
        Given two colors, return our total color distance
        """
        # log.info('colorA %s, colorB %s, sq1 %s, sq2 %s, distanceAB %d, distanceBA %d' % (colorA, colorB, self.square1.rawcolor, self.square2.rawcolor, distanceAB, distanceBA))
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
        distanceABC = (get_color_distance(self.square1.rawcolor, colorA) +
                       get_color_distance(self.square2.rawcolor, colorB) +
                       get_color_distance(self.square3.rawcolor, colorC))

        distanceCAB = (get_color_distance(self.square1.rawcolor, colorC) +
                       get_color_distance(self.square2.rawcolor, colorA) +
                       get_color_distance(self.square3.rawcolor, colorB))

        distanceBCA = (get_color_distance(self.square1.rawcolor, colorB) +
                       get_color_distance(self.square2.rawcolor, colorC) +
                       get_color_distance(self.square3.rawcolor, colorA))
        return (distanceABC, distanceCAB, distanceBCA)

    def color_distance(self, colorA, colorB, colorC):
        """
        Given three colors, return our total color distance
        """
        return min(self._get_color_distances(colorA, colorB, colorC))

    def update_colors(self, colorA, colorB, colorC):
        (distanceABC, distanceCAB, distanceBCA) = self._get_color_distances(colorA, colorB, colorC)
        min_distance = min(distanceABC, distanceCAB, distanceBCA)
        #log.info("update_colors min %d, distanceABC %d, distanceCAB %d, distanceBCA %d" % distanceABC, distanceCAB, distanceBCA)

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
            #log.info("%s (%s, %s, %s) is a valid corner" % (self, self.square1.color, self.square2.color, self.square3.color))
        else:
            self.valid = False
            log.info("%s (%s, %s, %s) is an invalid corner" % (self, self.square1.color, self.square2.color, self.square3.color))


class Square(object):

    def __init__(self, side, position, red, green, blue):
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
            distance = get_color_distance(self.rawcolor, color_obj)
            self.cie_data.append((distance, color_obj))
        self.cie_data = sorted(self.cie_data)

        distance = self.cie_data[0][0]
        color = self.cie_data[0][1]

        if set_color:
            self.distance = distance
            self.color = color

        if debug:
            #log.info("%s is %s\n%s\n" % (self, color, pformat(self.cie_data)))
            log.info("%s is %s" % (self, color))

        return (color, distance)


class CubeSide(object):

    def __init__(self, name):
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
        self.squares[position] = Square(self, position, red, green, blue)

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

    def __init__(self):
        self.width = 3
        self.blocks_per_side = self.width * self.width
        self.colors = []
        self.scan_data = {}

        self.sides = {
          'U' : CubeSide('U'),
          'L' : CubeSide('L'),
          'F' : CubeSide('F'),
          'R' : CubeSide('R'),
          'B' : CubeSide('B'),
          'D' : CubeSide('D'),
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
        crayola_colors = {
            'Rd' : hashtag_rgb_to_labcolor('#C91111'), # Red
            'Ro' : hashtag_rgb_to_labcolor('#D84E09'), # Red Orange
            'Or' : hashtag_rgb_to_labcolor('#FF8000'), # Orange
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
        (crayola_color_matched, distance) = square.find_closest_match(crayola_colors, set_color=False)

        for (crayola_color_name, crayola_color) in crayola_colors.iteritems():
            if crayola_color == crayola_color_matched:
                square.rawcolor.name = crayola_color_name
                break

    def find_top_six_colors(self):

        log.info('Populate the crayon box with the six colors of the middle squares')
        self.crayon_box = {}
        for side_name in self.side_order:
            side = self.sides[side_name]
            self.crayon_box[side.name] = side.middle_square.rawcolor
            self.set_color_name(side.middle_square)

        output = []
        for side_name in self.side_order:
            output.append("  %s : %s" % (side_name, self.crayon_box[side_name].name))
        log.info("Crayon box:\n%s" % '\n'.join(output))

        '''
        The following turned out to be overkill but it worked so I will leave it
        as a comment just in case.

        log.info('ID all 54 squares based on the middle square colors')
        for side_name in self.side_order:
            side = self.sides[side_name]

            for square in side.squares.itervalues():
                square.find_closest_match(self.crayon_box, debug=True)

        # There will be 9 squares for each color (it won't be exact at this
        # point though).  Find the square among those 9 that provides the
        # least color distance among the time.  Basically find the square that
        # is the midpoint color among those nine. Use those six midpoint squares
        # to build the final crayon box.
        log.info('Rebuild the crayon box (find the 6 color midpoint squares)')
        for side_name in self.side_order:
            side = self.sides[side_name]
            side_color = side.middle_square.color
            squares_with_side_color = self.get_squares_with_color(side_color)

            foo = {}

            for sq1 in squares_with_side_color:
                temp_crayon_box = {}

                for sq2 in squares_with_side_color:
                    # Do not compare a square against itself...that would always be a distance of 0
                    if sq1 is not sq2:
                        temp_crayon_box[sq2.position] = sq2.rawcolor

                #log.info("temp crayon box\n%s" % pformat(temp_crayon_box))
                (color, _) = sq1.find_closest_match(temp_crayon_box, set_color=False)

                if color not in foo:
                    foo[color] = 0
                foo[color] += 1
                #raw_input('Paused')

            # At this point all 9 squares have been compared against the
            # other 8...find the color that was the most popular and put that in
            # the crayon box as the color for this side
            sorted_foo = sorted(foo.items(), key=operator.itemgetter(1), reverse=True)
            #log.info("%s color popularity\n%s" % (side, pformat(sorted_foo)))

            # TODO there could be a tie...need to handle this:
            #[(LabColor(lab_l=30.626785538389214,lab_a=29.864352167725787,lab_b=30.031945460862175), 3),
            # (LabColor(lab_l=30.39277536960828,lab_a=30.261979610325508,lab_b=31.446448273216898), 3),
            # (LabColor(lab_l=28.969608061170973,lab_a=30.74656331835321,lab_b=35.38884117489387), 1),
            # (LabColor(lab_l=29.8088145006421,lab_a=31.85654695908241,lab_b=30.301232023478686), 1),
            # (LabColor(lab_l=31.851487373878392,lab_a=32.66039756821765,lab_b=32.2372603765823), 1),
            # (LabColor(lab_l=27.931101652554908,lab_a=25.37466834649582,lab_b=27.62787975085021), 1),
            # (LabColor(lab_l=31.34443578320309,lab_a=30.52412919898051,lab_b=31.494460965331882), 1)]
            #
            #[(LabColor(lab_l=27.86036466873822,lab_a=-13.2834726963951,lab_b=-8.915176734633345), 2),
            # (LabColor(lab_l=28.33962119547708,lab_a=-16.56411006327929,lab_b=-3.6550220126744803), 2),
            # (LabColor(lab_l=29.05801904503408,lab_a=-13.80885329144016,lab_b=-9.03989132743721), 2),
            # (LabColor(lab_l=26.547887212482145,lab_a=-10.164625015115364,lab_b=-12.213412613744712), 1),
            # (LabColor(lab_l=25.535908528467232,lab_a=-15.373542751586672,lab_b=-2.588992836467119), 1),
            # (LabColor(lab_l=30.2220672289314,lab_a=-17.84738998577959,lab_b=-5.3753856103857744), 1)]
            self.crayon_box[side.name] = sorted_foo[0][0]

        log.info("Final crayon box (midpoint color for each side)\n%s" % pformat(self.crayon_box))

        log.info('ID all 54 squares based on the final crayon box')
        for side in self.sides.itervalues():
            for square in side.squares.itervalues():
                (match, distance) = square.find_closest_match(self.crayon_box)
        '''

    def identify_middle_squares(self):
        log.info('ID middle square colors')

        middle_squares = []
        for side_name in self.side_order:
            side = self.sides[side_name]
            middle_squares.append(side.middle_square)

        for square in middle_squares:
            square.find_closest_match(self.crayon_box)

        log.info("Set the side color by middle square")
        for square in middle_squares:
            square.side.color = square.color

        log.info('Final middle squares')
        for square in middle_squares:
            log.info("%s is %s" % (square, square.color))
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

        edge_squares = []
        for side_name in self.side_order:
            side = self.sides[side_name]
            edge_squares.extend(side.edge_squares)

        for square in edge_squares:
            square.find_closest_match(self.crayon_box)

    def identify_corner_squares(self):
        log.info('ID corner square colors')

        corner_squares = []
        for side_name in self.side_order:
            side = self.sides[side_name]
            corner_squares.extend(side.corner_squares)

        for square in corner_squares:
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

    def resolve_needed_edges(self):
        self.needed_edges = sorted(self.needed_edges)

        output = []
        for (colorA, colorB) in self.needed_edges:
            output.append("%s/%s" % (colorA.name, colorB.name))
        log.info('Needed edges: %s' % ', '.join(output))

        score_per_permutation = []
        unresolved_edges = [edge for edge in self.edges if edge.valid is False]
        permutation_count = factorial(len(self.needed_edges))
        log.info("Evaluating %d permutations" % permutation_count)

        for edge_permutation in permutations(unresolved_edges):
            total_distance = 0

            for (edge, (colorA, colorB)) in zip(edge_permutation, self.needed_edges):
                total_distance += edge.color_distance(colorA, colorB)

            score_per_permutation.append((total_distance, edge_permutation))

        score_per_permutation = sorted(score_per_permutation)
        best_permutation = score_per_permutation[0][1]

        total_distance = 0
        for (edge_best_match, (colorA, colorB)) in zip(best_permutation, self.needed_edges):
            distance = edge_best_match.color_distance(colorA, colorB)
            total_distance += distance

            log.info("%s/%s best match is %s with distance %d" % (colorA.name, colorB.name, edge_best_match, distance))
            edge_best_match.update_colors(colorA, colorB)
            edge_best_match.valid = True
        log.info("Total distance: %d" % total_distance)

    def valid_parity(self):
        """
        cubex will barf with one of the following errors if you give it an invalid cube

        511 ERROR: cubelet error - incorrect cubelets - cube mispainted.
        512 ERROR: parity error - nondescript - cube misassembled.
        513 ERROR: parity error - center rotation - cube misassembled.
        514 ERROR: cubelet error - backward centers or corners - cube mispainted.
        515 ERROR: parity error - edge flipping - cube misassembled.
        516 ERROR: parity error - edge swapping - cube misassembled.
        517 ERROR: parity error - corner rotation - cube misassembled.
        http://www.gtoal.com/src/rubik/solver/readme.txt

        Long term we should add this parity logic to this class but for now
        just call cubex and see if it found an error.
        """
        arg = ''.join(map(str, self.cube_for_cubex()))
        output = Popen([self.cubex_file, arg], stdout=PIPE).communicate()[0]
        output = output.strip()
        if 'error' in output:
            log.info("Invalid parity:\n\n%s\n" % output)
            return False
        return True

    def resolve_needed_corners(self):
        self.needed_corners = sorted(self.needed_corners)

        output = []
        for (colorA, colorB, colorC) in self.needed_corners:
            output.append("%s/%s/%s" % (colorA.name, colorB.name, colorC.name))
        log.info('Needed corners: %s' % ', '.join(output))

        score_per_permutation = []
        unresolved_corners = [corner for corner in self.corners if corner.valid is False]
        permutation_count = factorial(len(self.needed_corners))

        # 6! = 720
        # 7! = 5040
        while permutation_count > 720:
            log.info("Permutation count is %d which is too high...resolve one corner" % permutation_count)

            scores = []
            for corner in unresolved_corners:
                for (colorA, colorB, colorC) in self.needed_corners:
                    distance = corner.color_distance(colorA, colorB, colorC)
                    scores.append((distance, corner, (colorA, colorB, colorC)))

            scores = sorted(scores)
            (distance, corner_best_match, (colorA, colorB, colorC)) = scores[0]

            log.info("%s/%s/%s best match is %s with distance %d" % (colorA.name, colorB.name, colorC.name, corner_best_match, distance))
            corner_best_match.update_colors(colorA, colorB, colorC)
            corner_best_match.valid = True
            self.needed_corners.remove((colorA, colorB, colorC))

            unresolved_corners = [corner for corner in self.corners if corner.valid is False]
            permutation_count = factorial(len(self.needed_corners))

        log.info("Evaluating %d permutations" % permutation_count)

        for corner_permutation in permutations(unresolved_corners):
            total_distance = 0

            for (corner, (colorA, colorB, colorC)) in zip(corner_permutation, self.needed_corners):
                total_distance += corner.color_distance(colorA, colorB, colorC)

            score_per_permutation.append((total_distance, corner_permutation))

        score_per_permutation = sorted(score_per_permutation)

        if os.path.isfile('./utils/rubiks_solvers/cubex_C_ARM/cubex_ev3'):
            self.cubex_file = './utils/rubiks_solvers/cubex_C_ARM/cubex_ev3'
        elif os.path.isfile('../utils/cubex_ev3'):
            self.cubex_file = '../utils/rubiks_solvers/cubex_C_ARM/cubex_ev3'

        for (_, permutation) in score_per_permutation:
            total_distance = 0

            for (corner_best_match, (colorA, colorB, colorC)) in zip(permutation, self.needed_corners):
                distance = corner_best_match.color_distance(colorA, colorB, colorC)
                total_distance += distance
                log.info("%s/%s/%s best match is %s with distance %d" % (colorA.name, colorB.name, colorC.name, corner_best_match, distance))
                corner_best_match.update_colors(colorA, colorB, colorC)
                corner_best_match.valid = True
            log.info("Total distance: %d" % total_distance)

            if self.valid_parity():
                break

    def sanity_edge_squares(self):
        log.info('Sanity check edge squares')
        #log.info("valid edges\n%s\n" % pformat(self.valid_edges))

        for edge in self.edges:
            edge.validate()

        # Find duplicates and mark them as invalid
        for edge1 in self.edges:
            for edge2 in self.edges:

                if edge1 == edge2 or not edge1.valid or not edge2.valid:
                    continue

                if (edge1.square1.color in (edge2.square1.color, edge2.square2.color) and
                    edge1.square2.color in (edge2.square1.color, edge2.square2.color)):
                    edge1.valid = False
                    edge2.valid = False
                    log.info("Duplicate edge %s" % edge1)
                    log.info("Duplicate edge %s" % edge2)

        self.needed_edges = []
        for (colorA, colorB) in self.valid_edges:

            for edge in self.edges:
                if edge.valid and edge.colors_match(colorA, colorB):
                    break
            else:
                self.needed_edges.append((colorA, colorB))

        if self.needed_edges:
            self.resolve_needed_edges()

        log.info('\n')

    def sanity_corner_squares(self):
        log.info('Sanity check corner squares')
        #log.info("valid corners\n%s\n" % pformat(self.valid_corners))

        for corner in self.corners:
            corner.validate()

        for corner1 in self.corners:
            for corner2 in self.corners:

                if corner1 == corner2 or not corner1.valid or not corner2.valid:
                    continue

                if (corner1.square1.color in (corner2.square1.color, corner2.square2.color, corner2.square3.color) and
                    corner1.square2.color in (corner2.square1.color, corner2.square2.color, corner2.square3.color) and
                    corner1.square3.color in (corner2.square1.color, corner2.square2.color, corner2.square3.color)):
                    corner1.valid = False
                    corner2.valid = False
                    log.info("Duplicate corner %s" % corner1)
                    log.info("Duplicate corner %s" % corner2)

        self.needed_corners = []
        for (colorA, colorB, colorC) in self.valid_corners:

            for corner in self.corners:
                if corner.valid and corner.colors_match(colorA, colorB, colorC):
                    break
            else:
                self.needed_corners.append((colorA, colorB, colorC))

        if self.needed_corners:
            self.resolve_needed_corners()

        log.info('\n')

    def crunch_colors(self):
        log.info('Discover the six colors')
        self.find_top_six_colors()

        # 6 middles, 12 edges, 8 corners
        self.identify_middle_squares()
        self.identify_edge_squares()
        self.identify_corner_squares()

        self.create_edges_and_corners()
        self.sanity_edge_squares()
        self.sanity_corner_squares()

        self.print_cube()
        self.print_layout()
        return self.cube_for_cubex()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)5s: %(message)s')
    log = logging.getLogger(__name__)

    from testdata import corner_parity1, solved_cube1, color_parity2, color_parity3
    cube = RubiksColorSolver()
    cube.enter_scan_data(color_parity2)
    cube.crunch_colors()
    print ''.join(map(str, cube.cube_for_cubex()))
    print ''.join(cube.cube_for_kociemba())
