from ev3 import *


class Everstorm(Robot):

    def __init__(self):
        Robot.__init__(self)
        self.mot_right = Motor('C')
        self.mot_left = Motor('D')
        self.mot_front = Motor('A')

    def turn_forever(self, speed, regulate=0):
        self.mot_left.rotate_forever(speed)
        self.mot_right.rotate_forever(-speed)

    def straight_forever(self, speed, regulate=0):
        self.mot_left.rotate_forever(speed, regulate=0, brake=1, hold=0)
        self.mot_right.rotate_forever(speed, regulate=0, brake=1, hold=0)

    def straight(self, speed, dist):
        step_position = 350
        position = dist * 4.8
        self.mot_right.rotate_position(position, speed, up=200, down=200)
        self.mot_left.rotate_position(position, speed, up=200, down=200)
        self.mot_right.wait_for_stop()
        self.mot_left.wait_for_stop()

    def turn_right(self, speed, angle):
        sleep_step = 50.0 / speed
        step_position = 350
        position = angle * 4.6
        self.mot_left.rotate_position(step_position / 2.0, speed, up=200, down=200)
        time.sleep(sleep_step / 2.0)
        self.mot_right.rotate_position(-position, speed, up=0, down=200)
        self.mot_left.rotate_position(position, speed, up=0, down=200)
        self.mot_right.wait_for_stop()
        self.mot_right.rotate_position(step_position / 2.0, speed, up=200, down=200)
        time.sleep(sleep_step / 2.0)

    def turn_left(self, speed, angle):
        sleep_step = 50.0 / speed
        step_position = 350
        position = angle * 4.9
        self.mot_right.rotate_position(step_position / 2.0, speed, up=200, down=200)
        time.sleep(sleep_step / 2.0)
        self.mot_right.rotate_position(position, speed, up=0, down=200)
        self.mot_left.rotate_position(-position, speed, up=0, down=200)
        self.mot_left.wait_for_stop()
        self.mot_left.rotate_position(step_position / 2.0, speed, up=200, down=200)
        time.sleep(sleep_step / 2.0)

    def stop(self):
        self.mot_left.stop()
        self.mot_right.stop()
        self.mot_front.stop()

    def walk(self, speed, steps, direction=1):
        step_position = 350 * direction
        sleep_step = 50.0 / speed
        self.mot_left.rotate_position(step_position / 2.0, speed, up=0, down=200)
        time.sleep(sleep_step / 2.0)
        for i in range(steps):
            self.mot_right.rotate_position(step_position, speed, up=0, down=200)
            time.sleep(sleep_step)
            self.mot_left.rotate_position(step_position, speed, up=0, down=200)
            time.sleep(sleep_step)

        self.mot_right.rotate_position(step_position / 2.0, speed, up=0, down=200)
        self.mot_right.wait_for_stop()
