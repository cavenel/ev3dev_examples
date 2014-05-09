from ev3 import *

class Rubiks(Robot):
    scan_order = [5, 9, 6, 3, 2, 1, 4, 7, 8, 23, 27, 24, 21, 20, 19, 22, 25, 26, 50, 54, 51, 48, 47, 46, 49, 52, 53, 14, 10, 13, 16, 17, 18, 15, 12, 11, 41, 43, 44, 45, 42, 39, 38, 37, 40, 32, 34, 35, 36, 33, 30, 29, 28, 31]

    rotate_speed = 60
    
    def __init__(self):
        self.mot_push = Motor('A')
        self.mot_bras = Motor('B')
        self.mot_rotate = Motor('C')
        self.color_sensor = Color_sensor()
        self.infrared_sensor = Infrared_sensor()
        self.cube = {}
        self.init_motors()
        self.state = ['U', 'D', 'F', 'L', 'B', 'R']

    def init_motors(self):
        self.mot_bras.rotate_forever(40, regulate=1, brake=1, hold=0)
        self.mot_push.rotate_forever(-30, regulate=1, brake=1, hold=0)
        self.mot_push.wait_for_stop()
        self.mot_push.stop()
        self.mot_bras.wait_for_stop()
        self.mot_bras.rotate_position(-380, 100, regulate=0, brake=1, hold=1)
        self.mot_bras.wait_for_stop()
        self.mot_bras.stop()
        self.mot_bras.reset_position()
        self.mot_rotate.stop()
        self.mot_rotate.reset_position()
        self.mot_push.reset_position()
        self.mot_bras.set_hold_mode(0)
        self.mot_push.set_hold_mode(0)
        self.mot_rotate.set_hold_mode(0)

    def apply_transformation(self, transformation):
        self.state = [ self.state[t] for t in transformation ]
    
    def rotate_cube(self, direction, nb, wait = 1):
        if (self.mot_push.get_position() > 15):
            self.mot_push.goto_position(5, 35, regulate=1, brake=1, hold=0)
            self.mot_push.wait_for_stop()
        
        pre_rotation = 135 * round(self.mot_rotate.get_position() / 135.0)
        self.mot_rotate.goto_position(pre_rotation + 270 * direction * nb, Rubiks.rotate_speed, 0, 300, 1, 1, hold=1)
        time.sleep(nb * 60 * 0.7 / Rubiks.rotate_speed)
        self.mot_rotate.stop()
        if nb >= 1:
            for i in range(nb):
                if direction > 0:
                    transformation = [0, 1, 5, 2, 3, 4]
                else:
                    transformation = [0, 1, 3, 4, 5, 2]
                self.apply_transformation(transformation)

    def rotate_cube_1(self):
        self.rotate_cube(1,1)

    def rotate_cube_2(self):
        self.rotate_cube(1,2)
        
    def rotate_cube_3(self):
        self.rotate_cube(-1,1)

    def rotate_cube_blocked(self, direction, nb):
        self.mot_push.goto_position(120, 30, 0, 300, regulate=1, brake=1, hold=1)
        self.mot_push.wait_for_stop()
        pre_rotation = 135 * round(self.mot_rotate.get_position() / 135.0)
        self.mot_rotate.goto_position(pre_rotation + 270 * direction * nb + 65 * direction, Rubiks.rotate_speed, 0, 300, 1, 1, hold=1)
        time.sleep(nb * 60 * 0.7 / Rubiks.rotate_speed)
        self.mot_rotate.goto_position(pre_rotation + 270 * direction * nb, Rubiks.rotate_speed, 0, 0, 1, 1, hold=1)
        time.sleep(0.3)
        self.mot_rotate.stop()

    def rotate_cube_blocked_1(self):
        self.rotate_cube_blocked(1,1)

    def rotate_cube_blocked_2(self):
        self.rotate_cube_blocked(1,2)
        
    def rotate_cube_blocked_3(self):
        self.rotate_cube_blocked(-1,1)
        
    def flip(self):
        if (math.fabs(self.mot_push.get_position() - 95) > 5):
            self.mot_push.goto_position(95, 30, 0, 300, regulate=1, brake=1, hold=0)
            time.sleep(0.4)
        self.mot_push.goto_position(180, 50, regulate=1, brake=1, hold=0)
        self.mot_push.wait_for_stop()
        self.mot_push.goto_position(95, 50, 0, 300, regulate=1, brake=1, hold=0)
        time.sleep(0.4)
        transformation = [2, 4, 1, 3, 0, 5]
        self.apply_transformation(transformation)

    # Function to put the cube in a good position, by blocking it with the pusher.
    def bloc_cube(self):
        self.mot_push.goto_position(95, 30, 0, 300, regulate=1, brake=1, hold=0)
        self.mot_push.wait_for_stop()
        self.mot_push.goto_position(5, 35, regulate=1, brake=1, hold=0)
        self.mot_push.wait_for_stop()

    def put_arm_middle(self):
        self.mot_bras.goto_position(-330, 100, regulate=0, brake=1, hold=1)

    def put_arm_corner(self, i):
        diff = 0
        if i >= 3 and i <= 5:
            diff = 20
        self.mot_bras.goto_position(-200 - diff, 100, regulate=1, brake=1, hold=1)

    def put_arm_border(self, i):
        diff = 0
        if i >= 3 and i <= 5:
            diff = 20
        self.mot_bras.goto_position(-260 - diff, 100, regulate=1, brake=1, hold=1)

    def remove_arm(self):
        self.mot_bras.goto_position(0, 100, regulate=1, brake=1, hold=0)

    def get_color(self):
        R, G, B = self.color_sensor.get_rgb()
        sum_RGB = R + G + B
        new_col_n = [255 * R / sum_RGB, 255 * G / sum_RGB, 255 * B / sum_RGB]
        names = ['Orange', 'Vert', 'Mauve', 'Violet', 'Bleu', 'Jaune']
        # Colors only work for a specific rubik's cube. Adapt for any other colors.
        colors_n = [[204, 38, 12], [77, 155, 21], [124, 70, 59], [99, 90, 64], [44, 97, 112], [137, 107, 9]]
        min_diff = 100000000
        min_col = None
        for col_n, i in zip(colors_n, range(6)):
            diff = 0
            diff += (col_n[0] - new_col_n[0]) * (col_n[0] - new_col_n[0]) + (col_n[1] - new_col_n[1]) * (col_n[1] - new_col_n[1]) + (col_n[2] - new_col_n[2]) * (col_n[2] - new_col_n[2])
            if min_diff > diff:
                min_diff = diff
                index_c = i

        print names[index_c]
        return str(index_c + 1)

    def scan_face(self):
        if (self.mot_push.get_position() > 15):
            self.mot_push.goto_position(5, 35, regulate=1, brake=1, hold=0)
            self.mot_push.wait_for_stop()
        self.put_arm_middle()
        self.mot_bras.wait_for_stop()
        self.cube[Rubiks.scan_order[self.k]] = self.get_color()
        self.k += 1
        i = 0
        self.put_arm_corner(i)
        i+=1
        self.mot_rotate.rotate_position(1080, 40, 0, 0, 1, 1, hold=1)
        time.sleep(0.1)
        while math.fabs(self.mot_rotate.get_speed()) > 4:
            if self.mot_rotate.get_position() >= (i * 135) - 5:
                self.cube[Rubiks.scan_order[self.k]] = self.get_color()
                self.k += 1
                i += 1
                if i % 2 and i < 9:
                    self.put_arm_corner(i)
                elif i < 9:
                    self.put_arm_border(i)
            time.sleep(0.01)

        self.remove_arm()
        self.mot_bras.wait_for_stop()
    
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
   
    def scan(self):
        self.bloc_cube()
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
        print self.cube
        self.cube = [ self.cube[i + 1] for i in range(len(self.cube)) ]
        print ''.join(self.cube)
        
    def resolve(self, computer):
        if computer:
            output = Popen(['ssh', 'login@192.168.3.235', 'pass_to_twophase/twophase.py ' + ''.join(self.cube)], stdout=PIPE).communicate()[0]
            output = output.strip()
            actions = output.split(' ')
            print actions
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
            output = Popen(['./cubex_ev3', ''.join(self.cube)], stdout=PIPE).communicate()[0]
            output = output.strip()
            print output
            actions = output.split(', ')
            print actions
            for a in actions:
                if a != "":
                    face_down = list(a)[0]
                    rotation_dir = list(a)[1]
                    self.move(face_down)
                    if rotation_dir == 'R':
                        self.rotate_cube_blocked(-1, 1, blocked=True)
                    else:
                        self.rotate_cube_blocked(1, 1, blocked=True)
        self.cube_done()
    
    def cube_done(self):
        self.mot_push.goto_position(5, 30, 0, 300, regulate=1, brake=1, hold=1)
        self.mot_push.wait_for_stop()
        os.system("beep -f 262 -l 180 -d 20 -r 2 \
            -n -f 392 -l 180 -d 20 -r 2 \
            -n -f 440 -l 180 -d 20 -r 2 \
            -n -f 392 -l 380 -d 20 \
            -n -f 349 -l 180 -d 20 -r 2 \
            -n -f 330 -l 180 -d 20 -r 2 \
            -n -f 294 -l 180 -d 20 -r 2 \
            -n -f 262 -l 400")
        self.rotate_cube(1,8)
        
