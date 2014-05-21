from ev3 import *
import colorsys

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
        self.mot_bras.goto_position(-370, 100, regulate=0, brake=1, hold=1)

    def put_arm_corner(self, i):
        diff = 0
        if (i == 2):
            diff = 20
        if i == 6:
            diff = -20
        self.mot_bras.goto_position(-200 - diff, 100, regulate=1, brake=1, hold=1)

    def put_arm_edge(self, i):
        diff = 0
        if i >= 2 and i <= 4:
            diff = 20
        self.mot_bras.goto_position(-260 - diff, 100, regulate=1, brake=1, hold=1)

    def remove_arm(self):
        self.mot_bras.goto_position(0, 100, regulate=1, brake=1, hold=0)

    def get_color_distance (self, c1, c2):
        (_,(h1,s1,l1)) = c1
        (_,(h2,s2,l2)) = c2
        return math.sqrt((h1-h2)*(h1-h2) + (s1-s2)*(s1-s2))

    def connect(self, i1,i2):
        cl1, cl2 = self.clusters[i1], self.clusters[i2]
        if (self.clusters.count(cl1) + self.clusters.count(cl2) > 9):
            return None
        else:
            for i in [i_ for i_, cl in enumerate(self.clusters) if cl == cl2]:
                self.clusters[i] = cl1
        
    def cluster_colors (self):
        distances = []
        self.clusters = [i for i, _ in enumerate(self.colors)]

        for i1 in range(len(self.colors)):
            for i2 in range(i1+1,len(self.colors)):
                distances.append((i1, i2, self.get_color_distance(self.colors[i1], self.colors[i2])))
        distances.sort(key=lambda (_, __, d): d)


        for (i1,i2,d) in distances:
            self.connect(i1,i2)

        for index, c in enumerate(set(self.clusters)):
            for i in [i_ for i_, cl in enumerate(self.clusters) if cl == c]:
                self.clusters[i] = index
        for i,c in enumerate(self.clusters):
            k,_ = self.colors[i]
            self.cube[k] = str(c+1)

    def get_hsl_colors(self):
        R, G, B = self.color_sensor.get_rgb()
        val_max = 255.#float(max(255,R,G,B))
        h,l,s = colorsys.rgb_to_hls(R / val_max, G / val_max, B / val_max)
        return h,s,l
        
    def scan_face(self):
        if (self.mot_push.get_position() > 15):
            self.mot_push.goto_position(5, 35, regulate=1, brake=1, hold=0)
            self.mot_push.wait_for_stop()
        self.put_arm_middle()
        self.mot_bras.wait_for_stop()
        self.colors.append((Rubiks.scan_order[self.k],self.get_hsl_colors()))
        self.k += 1
        i = 0
        self.put_arm_corner(i)
        i+=1
        self.mot_rotate.rotate_position(1080, 40, 0, 0, 1, 1, hold=1)
        time.sleep(0.1)
        while math.fabs(self.mot_rotate.get_speed()) > 4:
            if self.mot_rotate.get_position() >= (i * 135) - 5:
                i += 1
                if i%2:
                    self.colors.append((Rubiks.scan_order[self.k],self.get_hsl_colors()))
                else:
                    self.colors.append((Rubiks.scan_order[self.k],self.get_hsl_colors()))
                self.k += 1
                if i % 2 and i < 9:
                    self.put_arm_corner(i)
                elif i < 9:
                    self.put_arm_edge(i)
            time.sleep(0.05)

        self.remove_arm()
        self.mot_bras.wait_for_stop()
    
    def scan(self):
        self.colors = []
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
        self.cluster_colors ()
        print self.cube
        self.cube = [ self.cube[i + 1] for i in range(len(self.cube)) ]
        print ''.join(self.cube)
        
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
   
    def resolve(self, computer):
        if computer:
            output = Popen(['ssh', 'login@192.168.3.235', 'twophase.py ' + ''.join(self.cube)], stdout=PIPE).communicate()[0]
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
                        self.rotate_cube_blocked_3()
                    else:
                        self.rotate_cube_blocked_1()
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
        
