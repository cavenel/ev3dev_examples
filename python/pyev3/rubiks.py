
from ev3 import *
from rubiks_rgb_solver import RubiksColorSolver
from pprint import pformat

class ScanError(Exception):
    pass

class Rubiks(Robot):
    scan_order = [
        5, 9, 6, 3, 2, 1, 4, 7, 8,
        23, 27, 24, 21, 20, 19, 22, 25, 26,
        50, 54, 51, 48, 47, 46, 49, 52, 53,
        14, 10, 13, 16, 17, 18, 15, 12, 11,
        41, 43, 44, 45, 42, 39, 38, 37, 40,
        32, 34, 35, 36, 33, 30, 29, 28, 31]

    rotate_speed = 300
    corner_to_edge_diff = 60

    def __init__(self):
        self.mot_push = Motor('A', 'flipper')
        self.mot_bras = Motor('C', 'color arm')
        self.mot_rotate = Motor('B', 'turntable')
        self.color_sensor = Color_sensor()
        self.infrared_sensor = Infrared_sensor()
        self.cube = {}
        self.init_motors()
        self.state = ['U', 'D', 'F', 'L', 'B', 'R']

    def init_motors(self):
        log.info("Initialize %s" % self.mot_push)
        self.mot_push.rotate_forever(-70)
        self.mot_push.wait_for_stop()
        self.mot_push.stop()
        self.mot_push.reset_position()

        log.info("Initialize %s" % self.mot_bras)
        self.mot_bras.rotate_forever(500)
        self.mot_bras.wait_for_stop()
        self.mot_bras.stop()
        self.mot_bras.reset_position()

        log.info("Initialize %s" % self.mot_rotate)
        self.mot_rotate.stop()
        self.mot_rotate.reset_position()

    def apply_transformation(self, transformation):
        self.state = [self.state[t] for t in transformation]

    def rotate_cube(self, direction, nb, wait=1):

        if (self.mot_push.get_position() > 15):
            self.push_arm_away()

        final_dest = 135 * round((self.mot_rotate.get_position() + (270 * direction * nb)) / 135.0)

        self.mot_rotate.goto_position(
            final_dest,
            Rubiks.rotate_speed,
            0,
            300,
            stop_mode='hold', accuracy_sp=100)

        self.mot_rotate.wait_for_stop()
        self.mot_rotate.stop()

        if nb >= 1:
            for i in range(nb):
                if direction > 0:
                    transformation = [0, 1, 5, 2, 3, 4]
                else:
                    transformation = [0, 1, 3, 4, 5, 2]
                self.apply_transformation(transformation)

    def rotate_cube_1(self):
        self.rotate_cube(1, 1)

    def rotate_cube_2(self):
        self.rotate_cube(1, 2)

    def rotate_cube_3(self):
        self.rotate_cube(-1, 1)

    def rotate_cube_blocked(self, direction, nb):

        # Move the arm down to hold the block in place
        self.mot_push.goto_position(120, 300, 0, 300, stop_mode='hold')
        self.mot_push.wait_for_stop()

        OVERROTATE = 55
        final_dest = 135 * round((self.mot_rotate.get_position() + (270 * direction * nb)) / 135.0)
        temp_dest = final_dest + (OVERROTATE * direction)
        #log.info("temp_dest %d, final_dest %d" % (temp_dest, final_dest))

        self.mot_rotate.goto_position(
            temp_dest,
            Rubiks.rotate_speed,
            0,
            300,
            stop_mode='hold', accuracy_sp=100)
        self.mot_rotate.wait_for_stop()
        self.mot_rotate.stop()

        self.mot_rotate.goto_position(
            final_dest,
            Rubiks.rotate_speed/2,
            0,
            0,
            stop_mode='hold', accuracy_sp=100)
        self.mot_rotate.wait_for_stop()
        self.mot_rotate.stop()

    def rotate_cube_blocked_1(self):
        self.rotate_cube_blocked(1, 1)

    def rotate_cube_blocked_2(self):
        self.rotate_cube_blocked(1, 2)

    def rotate_cube_blocked_3(self):
        self.rotate_cube_blocked(-1, 1)

    def push_arm_away(self):
        """
        Move the flipper arm out of the way
        """
        self.mot_push.goto_position(0, 300, 0, 300)
        self.mot_push.wait_for_stop()
        self.mot_push.stop()

    def flip(self):

        if (self.mot_push.get_position() > 15):
            self.mot_push.goto_position(95, 200, 0, 300)
            self.mot_push.wait_for_stop()

        # Grab the cube and pull back
        self.mot_push.goto_position(180, 400, 200, 0)
        self.mot_push.wait_for_stop()
        time.sleep(0.2)

        # At this point the cube is at an angle, push it forward to
        # drop it back down in the turntable
        self.mot_push.goto_position(95, 300, 0, 300)
        self.mot_push.wait_for_stop()

        transformation = [2, 4, 1, 3, 0, 5]
        self.apply_transformation(transformation)

    def bloc_cube(self):
        """
        Function to put the cube in a good position

        Turn the cube one 1/4 rotation and measure the proximity via the
        IR sensor while it is rotating. We get a lower proximity value when
        the cube is square (there is more surface area facing the sensor)
        Record the (proximity, position) tuples in the data list.

        Then sort data by proximity and turn the table to the position for
        that entry.
        """
        log.info("square up the cube turntable")

        data = []

        # Take a few data points before the cube starts turning.  This is in
        # case it is already where it should be, we want a measurement before we
        # move anything.
        data.append((self.infrared_sensor.get_prox(), self.mot_rotate.get_position()))
        data.append((self.infrared_sensor.get_prox(), self.mot_rotate.get_position()))
        data.append((self.infrared_sensor.get_prox(), self.mot_rotate.get_position()))

        self.mot_rotate.rotate_position(540, speed=200)
        while self.mot_rotate.is_running():
            data.append((self.infrared_sensor.get_prox(), self.mot_rotate.get_position()))
            #time.sleep(0.05)

        data = sorted(data)
        log.info("bloc cube data\n%s" % pformat(data))

        best_proximity = data[0][0]
        best_positions = []

        for (proximity, position) in data:
            if proximity == best_proximity:
                best_positions.append(position)
            else:
                break
        log.info("bloc cube best positions\n%s" % pformat(best_positions))

        target_position = median(best_positions)
        log.info("bloc cube target position: %d" % target_position)

        self.mot_rotate.wait_for_stop()
        self.mot_rotate.stop()
        self.mot_rotate.goto_position(target_position, 400)
        self.mot_rotate.wait_for_stop()
        self.mot_rotate.stop()
        self.mot_rotate.reset()

    def put_arm_middle(self):
        self.mot_bras.goto_position(-750, 900, stop_mode='hold')

    def put_arm_corner(self, i):
        if i == 2:
            diff = Rubiks.corner_to_edge_diff
        elif i == 6:
            diff = Rubiks.corner_to_edge_diff * -1
        else:
            diff = 0
        diff = 0
        self.mot_bras.goto_position(-590 - diff, 500, stop_mode='hold')

    def put_arm_edge(self, i):
        #if i >= 2 and i <= 4:
        #    diff = Rubiks.corner_to_edge_diff
        #else:
        #    diff = 0
        diff = 0
        self.mot_bras.goto_position(-650 - diff, 500, stop_mode='hold')

    def remove_arm(self):
        self.mot_bras.goto_position(0, 500)

    def scan_face(self):

        if (self.mot_push.get_position() > 15):
            self.push_arm_away()

        log.info('scanning face')
        self.put_arm_middle()
        self.mot_bras.wait_for_stop()
        self.mot_bras.stop()
        self.colors[int(Rubiks.scan_order[self.k])] = tuple(self.color_sensor.get_rgb())

        self.k += 1
        i = 0
        self.put_arm_corner(i)
        i += 1

        # The gear ratio is 3:1 so 1080 is one full rotation
        self.mot_rotate.reset()
        time.sleep(0.05)
        self.mot_rotate.rotate_position(1080, 200, 0, 0, 'on', stop_mode='hold')
        time.sleep(0.1)

        while math.fabs(self.mot_rotate.get_speed()) > 2:
            current_position = self.mot_rotate.get_position()

            # 135 is 1/8 of full rotation
            if current_position >= (i * 135) - 5:
                current_color = tuple(self.color_sensor.get_rgb())
                self.colors[int(Rubiks.scan_order[self.k])] = current_color
                log.info(
                    "i %d, k %d, current_position %d, current_color %s" %
                    (i, self.k, current_position, current_color))

                i += 1
                self.k += 1

                if i % 2:
                    self.put_arm_corner(i)
                else:
                    self.put_arm_edge(i)

            if not self.mot_rotate.is_running():
                break

            if i == 9:
                self.mot_rotate.stop()
                break

        if i < 9:
            raise ScanError('i is %d..should be 9' % i)

        self.mot_rotate.wait_for_stop()
        self.mot_rotate.stop()

        # If we over rotated at all, back up
        self.mot_rotate.goto_position(1080, 200, 0, 0, 'on', stop_mode='hold', accuracy_sp=100)
        self.mot_rotate.wait_for_stop()
        self.mot_rotate.stop()
        self.mot_rotate.reset()

        #self.mot_rotate.reset_position()
        self.remove_arm()
        self.mot_bras.wait_for_stop()

    def scan(self):
        self.colors = {}
        #self.bloc_cube()
        self.k = 0
        self.scan_face()

        self.flip()
        self.scan_face()

        self.flip()
        self.scan_face()

        self.rotate_cube(-1, 1)
        self.flip()
        self.scan_face()

        self.rotate_cube(1, 1)
        self.flip()
        self.scan_face()

        self.flip()
        self.scan_face()

        log.info("Scanned RGBs\n%s" % pformat(self.colors))
        rgb_solver = RubiksColorSolver()
        rgb_solver.enter_scan_data(self.colors)
        self.cube = rgb_solver.crunch_colors()
        log.info("Colors by numbers %s" % self.cube)

    def move(self, face_down):
        position = self.state.index(face_down)
        actions = {
            0: ["flip", "flip"],
            1: [],
            2: ["rotate_cube_2", "flip"],
            3: ["rotate_cube_1", "flip"],
            4: ["flip"],
            5: ["rotate_cube_3", "flip"]
        }.get(position, None)

        for a in actions:
            getattr(self, a)()

    def run_cubex_actions(self, actions):
        total_actions = len(actions)
        for (i, a) in enumerate(actions):
            (face_down, rotation_dir) = list(a)
            log.info("Move %d/%d: %s%s" % (i, total_actions, face_down, rotation_dir))
            self.move(face_down)

            if rotation_dir == 'R':
                self.rotate_cube_blocked_3()
            else:
                self.rotate_cube_blocked_1()

    def resolve(self, computer):
        if computer:
            output = Popen(
                ['ssh',
                 'login@192.168.3.235',
                 'twophase.py ' + ''.join(self.cube)],
                stdout=PIPE).communicate()[0]
            output = output.strip()
            actions = output.split(' ')
            log.info('Action (twophase.py): %s' % pformat(actions))

            for a in reversed(actions):
                if a != "":
                    face_down = list(a)[0]
                    rotation_dir = list(a)[1]
                    self.move(face_down)
                    if rotation_dir == '1':
                        self.rotate_cube_blocked_1()
                    elif rotation_dir == '2':
                        self.rotate_cube_blocked_2()
                    elif rotation_dir == '3':
                        self.rotate_cube_blocked_3()

        else:
            output = Popen(['./utils/cubex_ev3', ''.join(map(str, self.cube))], stdout=PIPE).communicate()[0]
            output = output.strip()
            actions = output.split(', ')
            log.info('Action (cubex_ev3): %s' % pformat(actions))
            self.run_cubex_actions(actions)

        self.cube_done()

    def cube_done(self):
        self.push_arm_away()

        os.system("beep -f 262 -l 180 -d 20 -r 2 \
            -n -f 392 -l 180 -d 20 -r 2 \
            -n -f 440 -l 180 -d 20 -r 2 \
            -n -f 392 -l 380 -d 20 \
            -n -f 349 -l 180 -d 20 -r 2 \
            -n -f 330 -l 180 -d 20 -r 2 \
            -n -f 294 -l 180 -d 20 -r 2 \
            -n -f 262 -l 400")
        self.rotate_cube(1, 8)

    def wait_for_cube_insert(self):
        rubiks_present = 0
        rubiks_present_target = 10

        while True:
            dist = self.infrared_sensor.get_prox()
            if (dist > 10 and dist < 50):
                rubiks_present += 1
                log.info("wait for cube...proximity %d, present for %d/%d" %\
                         (dist, rubiks_present, rubiks_present_target))
            else:
                if rubiks_present:
                    log.info('wait for cube...cube removed')
                rubiks_present = 0

            if rubiks_present >= rubiks_present_target:
                log.info('wait for cube...cube found and stable')
                break

            time.sleep(0.1)

    def wait_for_cube_removal(self):
        rubiks_missing = 0
        rubiks_missing_target = 10

        i = 0
        while True:
            dist = self.infrared_sensor.get_prox()
            if dist > 50:
                rubiks_missing += 1
                log.info('wait for cube removed...cube out')
            else:
                i += 1
                if i == 100:
                    log.info('wait for cube removed...cube still there')
                    i = 0
                rubiks_missing = 0

            if rubiks_missing >= rubiks_missing_target:
                log.info('wait for cube removed...its removed')
                break

            time.sleep(0.1)
