
from ev3 import *
from pprint import pformat
from subprocess import check_output
import json
import signal

log = logging.getLogger(__name__)

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

    hold_cube_pos = 85
    rotate_speed = 600
    corner_to_edge_diff = 60

    def __init__(self):
        Robot.__init__(self)
        self.shutdown_flag = False
        self.mot_push = Motor('A', 'flipper')
        self.mot_bras = Motor('C', 'color arm')
        self.mot_rotate = Motor('B', 'turntable')
        self.color_sensor = Color_sensor()
        try:
            self.distance_sensor = Infrared_sensor()
        except EnvironmentError:
            self.distance_sensor = Ultrasonic_sensor()
        self.cube = {}
        self.init_motors()
        self.state = ['U', 'D', 'F', 'L', 'B', 'R']
        self.server_ip = None
        self.server_username = None
        self.server_path = None
        self.rgb_solver = None
        signal.signal(signal.SIGTERM, self.signal_term_handler)
        signal.signal(signal.SIGINT, self.signal_int_handler)
        self.parse_server_conf()

    def init_motors(self):
        log.info("Initialize %s" % self.mot_push)
        self.mot_push.rotate_forever(-130)
        self.mot_push.wait_for_stop()
        self.mot_push.stop()
        self.mot_push.reset()

        log.info("Initialize %s" % self.mot_bras)
        self.mot_bras.rotate_forever(500)
        self.mot_bras.wait_for_stop()
        self.mot_bras.stop()
        self.mot_bras.reset()

        log.info("Initialize %s" % self.mot_rotate)
        self.mot_rotate.stop()
        self.mot_rotate.reset()

    def shutdown(self):
        log.info('Shutting down')
        self.leds.set_all('yellow')

        if self.rgb_solver:
            self.rgb_solver.shutdown_flag = True

        self.shutdown_flag = True
        self.mot_push.wait_for_stop()
        self.mot_push.stop()

        self.mot_bras.wait_for_stop()
        self.mot_bras.stop()

        self.mot_rotate.wait_for_stop()
        self.mot_rotate.stop()

    def signal_term_handler(self, signal, frame):
        log.error('Caught SIGTERM')
        self.shutdown()

    def signal_int_handler(self, signal, frame):
        log.error('Caught SIGINT')
        self.shutdown()

    def apply_transformation(self, transformation):
        self.state = [self.state[t] for t in transformation]

    def rotate_cube(self, direction, nb, wait=1):

        if (self.mot_push.get_position() > 35):
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
        if self.mot_push.get_position() < Rubiks.hold_cube_pos:
            self.mot_push.goto_position(Rubiks.hold_cube_pos, 300, stop_mode='hold')
            self.mot_push.wait_for_start()
            self.mot_push.wait_for_stop()
            self.mot_push.stop()

        # This depends on lot on Rubiks.rotate_speed
        OVERROTATE = 18
        final_dest = 135 * round((self.mot_rotate.get_position() + (270 * direction * nb)) / 135.0)
        temp_dest = final_dest + (OVERROTATE * direction)

        self.mot_rotate.goto_position(
            temp_dest,
            Rubiks.rotate_speed,
            0,
            300,
            stop_mode='hold')
        self.mot_rotate.wait_for_stop()

        self.mot_rotate.goto_position(
            final_dest,
            Rubiks.rotate_speed/4,
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
        self.mot_push.goto_position(0, 400)
        self.mot_push.wait_for_stop()
        self.mot_push.stop()


    def flip(self):

        if self.shutdown_flag:
            return

        current_position = self.mot_push.get_position()

        # Push it forward so the cube is always in the same position
        # when we start the flip
        if (current_position <= Rubiks.hold_cube_pos - 10 or
            current_position >= Rubiks.hold_cube_pos + 10):
            self.mot_push.goto_position(Rubiks.hold_cube_pos, 400)
            self.mot_push.wait_for_stop()
            self.mot_push.stop()

        # Grab the cube and pull back
        self.mot_push.goto_position(180, 400)
        self.mot_push.wait_for_stop()
        self.mot_push.stop()

        # At this point the cube is at an angle, push it forward to
        # drop it back down in the turntable
        self.mot_push.goto_position(Rubiks.hold_cube_pos, 600)
        self.mot_push.wait_for_stop()
        self.mot_push.stop()

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
        data.append((self.distance_sensor.get_prox(), self.mot_rotate.get_position()))
        data.append((self.distance_sensor.get_prox(), self.mot_rotate.get_position()))
        data.append((self.distance_sensor.get_prox(), self.mot_rotate.get_position()))

        self.mot_rotate.rotate_position(540, speed=200)
        while self.mot_rotate.is_running():
            data.append((self.distance_sensor.get_prox(), self.mot_rotate.get_position()))

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
        self.mot_bras.goto_position(-750, 1200, stop_mode='hold')
        self.mot_bras.wait_for_stop()

    def put_arm_corner(self, i):
        if i == 2:
            diff = Rubiks.corner_to_edge_diff
        elif i == 6:
            diff = Rubiks.corner_to_edge_diff * -1
        else:
            diff = 0
        diff = 0
        self.mot_bras.goto_position(-580 - diff, 1200, stop_mode='hold')
        self.mot_bras.wait_for_stop()

    def put_arm_edge(self, i):
        #if i >= 2 and i <= 4:
        #    diff = Rubiks.corner_to_edge_diff
        #else:
        #    diff = 0
        diff = 0
        self.mot_bras.goto_position(-650 - diff, 1200, stop_mode='hold')
        self.mot_bras.wait_for_stop()

    def remove_arm(self):
        self.mot_bras.goto_position(0, 1200)
        self.mot_bras.wait_for_stop()

    def remove_arm_halfway(self):
        self.mot_bras.goto_position(-400, 1200)
        self.mot_bras.wait_for_stop()

    def scan_face(self, last_face=False):

        if self.buttons.get_button('ENTER'):
            self.shutdown()

        if self.shutdown_flag:
            return

        if (self.mot_push.get_position() > 35):
            self.push_arm_away()

        log.info('scanning face')
        self.put_arm_middle()
        self.colors[int(Rubiks.scan_order[self.k])] = tuple(self.color_sensor.get_rgb())

        self.k += 1
        i = 0
        self.put_arm_corner(i)
        i += 1

        # The gear ratio is 3:1 so 1080 is one full rotation
        self.mot_rotate.wait_for_stop() # just to be sure
        self.mot_rotate.reset()
        self.mot_rotate.rotate_position(1080, 400, 0, 0, 'on', stop_mode='hold')
        self.mot_rotate.wait_for_start()

        #while math.fabs(self.mot_rotate.get_speed()) > 2:
        while self.mot_rotate.is_running():
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

                if i == 9:
                    # Last face, move the color arm all the way out of the way
                    if last_face:
                        self.remove_arm()

                    # Move the color arm far enough away so that the flipper
                    # arm doesn't hit it
                    else:
                        self.remove_arm_halfway()
                elif i % 2:
                    self.put_arm_corner(i)
                else:
                    self.put_arm_edge(i)

            if i == 9 or self.shutdown_flag:
                self.mot_rotate.stop()
                break

        if not self.shutdown_flag and i < 9:
            raise ScanError('i is %d..should be 9' % i)

        self.mot_rotate.wait_for_stop()

        # If we over rotated at all, back up
        self.mot_rotate.goto_position(1080, 200, 0, 0, 'on', stop_mode='hold', accuracy_sp=100)
        self.mot_rotate.wait_for_stop()
        self.mot_rotate.stop()
        self.mot_rotate.reset()

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
        self.scan_face(last_face=True)

        if self.shutdown_flag:
            return

        run_rgb_solver = True

        if self.server_username and self.server_ip and self.server_path:
            output = Popen(
                ['ssh',
                 '%s@%s' % (self.server_username, self.server_ip),
                 '%s/python/pyev3/rubiks_rgb_solver.py' % self.server_path,
                 '--rgb',
                 "'%s'" % json.dumps(self.colors)],
                stdout=PIPE).communicate()[0]
            output = output.strip().strip()
            self.cube_kociemba = list(output)

            if self.cube_kociemba:
                run_rgb_solver = False
            else:
                log.warning("Our connection to %s failed, we will run rubiks_rgb_solver locally" % self.server_ip)
                self.leds.set_all('orange')

        if run_rgb_solver:
            from rubiks_rgb_solver import RubiksColorSolver
            self.rgb_solver = RubiksColorSolver(False)

            if self.shutdown_flag:
                self.rgb_solver.shutdown_flag = True

            self.rgb_solver.enter_scan_data(self.colors)
            (self.cube_kociemba, self.cube_cubex) = self.rgb_solver.crunch_colors()

        log.info("Scanned RGBs\n%s" % pformat(self.colors))
        log.info("Final Colors: %s" % self.cube_kociemba)

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

            if self.shutdown_flag:
                break

            getattr(self, a)()

    def run_kociemba_actions(self, actions):
        log.info('Action (kociemba): %s' % ' '.join(actions))
        total_actions = len(actions)
        for (i, a) in enumerate(actions):

            if self.buttons.get_button('ENTER'):
                self.shutdown()

            if self.shutdown_flag:
                break

            if a.endswith("'"):
                face_down = list(a)[0]
                rotation_dir = 1
            elif a.endswith("2"):
                face_down = list(a)[0]
                rotation_dir = 2
            else:
                face_down = a
                rotation_dir = 3

            log.info("Move %d/%d: %s%s (a %s)" % (i, total_actions, face_down, rotation_dir, pformat(a)))
            self.move(face_down)

            if rotation_dir == 1:
                self.rotate_cube_blocked_1()
            elif rotation_dir == 2:
                self.rotate_cube_blocked_2()
            elif rotation_dir == 3:
                self.rotate_cube_blocked_3()

    def run_cubex_actions(self, actions):
        log.info('Action (cubex_ev3): %s' % ' '.join(actions))
        total_actions = len(actions)

        for (i, a) in enumerate(actions):

            if self.buttons.get_button('ENTER'):
                self.shutdown_flag = True

            if self.shutdown_flag:
                break

            if not a:
                continue

            (face_down, rotation_dir) = list(a)
            log.info("Move %d/%d: %s%s" % (i, total_actions, face_down, rotation_dir))
            self.move(face_down)

            if rotation_dir == 'R':
                self.rotate_cube_blocked_3()
            else:
                self.rotate_cube_blocked_1()

    def parse_server_conf(self):
        server_conf = check_output('find . -name server.conf', shell=True).splitlines()

        if server_conf:
            server_conf = server_conf[0]
            log.info("server.conf is %s" %  server_conf)

            with open(server_conf, 'r') as fh:
                for line in fh.readlines():
                    line = line.strip()
                    line = line.replace(' ', '')
                    (key, value) = line.split('=')

                    if key == 'username':
                        self.server_username = value
                        log.info("server_username %s" % self.server_username)
                    elif key == 'ip':
                        self.server_ip = value
                        log.info("server_ip %s" % self.server_ip)
                    elif key == 'path':
                        self.server_path = value
                        log.info("server_path %s" % self.server_path)

    def resolve(self):

        run_cubex_ev3 = True

        if self.server_username and self.server_ip and self.server_path:
            output = Popen(
                ['ssh',
                 '%s@%s' % (self.server_username, self.server_ip),
                 '%s/python/pyev3/twophase_python/solve.py %s' %\
                 (self.server_path, ''.join(map(str, self.cube_kociemba)))],
                stdout=PIPE).communicate()[0]
            output = output.strip().strip()

            if output:
                actions = output.split(' ')
                self.run_kociemba_actions(actions)
                run_cubex_ev3 = False
            else:
                log.warning("Our connection to %s failed, we will run cubex_ev3 locally" % self.server_ip)
                self.leds.set_all('orange')

        if run_cubex_ev3:
            if os.path.isfile('../utils/rubiks_solvers/cubex_C_ARM/cubex_ev3'):
                cubex_file = '../utils/rubiks_solvers/cubex_C_ARM/cubex_ev3'
            else:
                cubex_file = check_output('find . -name cubex_ev3', shell=True).splitlines()[0]

            output = Popen([cubex_file, ''.join(map(str, self.cube_cubex))], stdout=PIPE).communicate()[0]
            actions = output.strip().replace(' ', '').split(',')
            self.run_cubex_actions(actions)

        self.cube_done()

    def cube_done(self):
        self.push_arm_away()

        if self.shutdown_flag:
            return

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

            if self.shutdown_flag:
                break

            dist = self.distance_sensor.get_prox()
            if (self.distance_sensor.is_in_range()):
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

            if self.shutdown_flag:
                break

            dist = self.distance_sensor.get_prox()
            if not self.distance_sensor.is_in_range():
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
