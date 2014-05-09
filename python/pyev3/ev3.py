import glob
import time
import sys
import math
from subprocess import *
import os

class Communicate():
    onoff = ['off', 'on']

    def read(self, path):
        pin = open(path, 'r')
        try:
            value = pin.read()
        except:
            value = '0'

        pin.close()
        return value

    def write(self, path, value):
        pout = open(path, 'w')
        pout.write(value)
        pout.close()

    def set_on_off(self, path, value):
        self.write(path, Communicate.onoff[value])


class Sensor(Communicate):

    def __init__(self, type_id = -1):
        self.mode = None
        if type_id != -1:
            self.set_path_from_type_id(type_id)
        else:
            self.path = None

    def set_path_from_type_id(self, type_id):
        self.path = None
        for sensor_p in glob.glob('/sys/class/msensor/sensor*'):
            sensor_type_id = int(self.read(sensor_p + '/type_id'))
            if sensor_type_id == type_id:
                self.path = sensor_p

    def set_mode(self, mode):
        if self.mode != mode:
            self.mode = mode
            self.write(self.path + '/mode', mode)
            time.sleep(0.1)

    def get_values(self, nb_val):
        values = []
        for i in range(nb_val):
            values.append(int(self.read(self.path + '/value' + str(i))))

        return values

    def get_value(self):
        return self.get_values(1)[0]


class Touch_sensor(Sensor):

    def __init__(self):
        Sensor.__init__(self, type_id=16)

    def is_pushed(self):
        return self.get_value()


class Color_sensor(Sensor):
    colors = (None, 'black', 'blue', 'green', 'yellow', 'red', 'white', 'brown')

    def __init__(self):
        Sensor.__init__(self, type_id=29)

    def get_rgb(self):
        self.set_mode('RGB-RAW')
        return self.get_values(3)

    def get_color(self):
        self.set_mode('COL-COLOR')
        return self.get_value()


class Infrared_sensor(Sensor):

    def __init__(self):
        Sensor.__init__(self, type_id=33)

    def get_remote(self):
        self.set_mode('IR-REMOTE')
        return self.get_values(4)

    def get_remote_bin(self):
        self.set_mode('IR-REM-A')
        return self.get_value()

    def get_prox(self):
        self.set_mode('IR-PROX')
        return self.get_value()

    def get_seek(self):
        self.set_mode('IR-SEEK')
        h1, p1, h2, p2, h3, p3, h4, p4 = self.get_values(8)
        seeks = [(1, h1, p1), (2, h2, p2), (3, h3, p3), (4, h4, p4)]
        channels = {}
        for id, h, p in seeks:
            if p != 128:
                if h > 128:
                    h = h - 256
                channels[id] = (h, p)

        return channels


class Motor(Communicate):

    def __init__(self, port = None):
        if port:
            self.path = '/sys/class/tacho-motor/out' + port + ':motor:tacho/'

    def set_run_mode(self, value):
        path = self.path + 'run_mode'
        self.write(path, value)
        while self.get_run_mode() != value:
            time.sleep(0.05)

    def set_brake_mode(self, value):
        path = self.path + 'brake_mode'
        self.set_on_off(path, value)
        while self.get_brake_mode() != Communicate.onoff[value]:
            time.sleep(0.05)

    def set_hold_mode(self, value):
        path = self.path + 'hold_mode'
        self.set_on_off(path, value)
        while self.get_hold_mode() != Communicate.onoff[value]:
            time.sleep(0.05)

    def set_regulation_mode(self, value):
        path = self.path + 'regulation_mode'
        self.set_on_off(path, value)
        while self.get_regulation_mode() != Communicate.onoff[value]:
            time.sleep(0.05)

    def set_position_mode(self, value):
        path = self.path + 'position_mode'
        self.write(path, value)
        while self.get_position_mode() != value:
            time.sleep(0.05)

    def get_run_mode(self):
        return self.read(self.path + 'run_mode').strip()

    def get_brake_mode(self):
        return self.read(self.path + 'brake_mode').strip()

    def get_hold_mode(self):
        return self.read(self.path + 'hold_mode').strip()

    def get_regulation_mode(self):
        return self.read(self.path + 'regulation_mode').strip()

    def get_position_mode(self):
        return self.read(self.path + 'position_mode').strip()

    def set_speed(self, value):
        path = self.path + 'speed_setpoint'
        self.write(path, str(value))

    def set_time(self, value):
        path = self.path + 'time_setpoint'
        self.write(path, str(value))

    def set_position(self, value):
        path = self.path + 'position_setpoint'
        self.write(path, str(value))

    def reset_position(self, value = 0):
        path = self.path + 'position'
        self.write(path, str(value))

    def get_position(self):
        return int(self.read(self.path + 'position'))

    def get_speed(self):
        return int(self.read(self.path + 'speed'))

    def get_power(self):
        return int(self.read(self.path + 'power'))

    def get_state(self):
        return self.read(self.path + 'state')

    def set_ramps(self, up, down):
        path = self.path + 'ramp_up'
        self.write(path, str(up))
        path = self.path + 'ramp_down'
        if down > 10000:
            down = 10000
        self.write(path, str(down))

    def rotate_forever(self, speed, regulate = 0, brake = 1, hold = 0):
        self.set_run_mode('forever')
        self.set_brake_mode(brake)
        self.set_hold_mode(hold)
        self.set_speed(speed)
        self.set_regulation_mode(regulate)
        self.run()

    def rotate_time(self, time, speed, up = 0, down = 0, regulate = 0, brake = 1, hold = 0):
        self.set_run_mode('time')
        self.set_brake_mode(brake)
        self.set_hold_mode(hold)
        self.set_regulation_mode(regulate)
        self.set_ramps(up, down)
        self.set_time(time)
        self.set_speed(speed)
        self.run()

    def rotate_position(self, position, speed, up = 0, down = 0, regulate = 0, brake = 1, hold = 0, reset = 1):
        self.set_run_mode('position')
        if reset:
            self.reset_position()
        self.set_position_mode('relative')
        self.set_brake_mode(brake)
        self.set_hold_mode(hold)
        self.set_regulation_mode(regulate)
        self.set_ramps(up, down)
        self.set_speed(speed)
        self.set_position(position)
        self.run()

    def goto_position(self, position, speed, up = 0, down = 0, regulate = 0, brake = 1, hold = 0):
        self.set_run_mode('position')
        self.set_position_mode('absolute')
        self.set_brake_mode(brake)
        self.set_hold_mode(hold)
        self.set_regulation_mode(regulate)
        self.set_ramps(up, down)
        self.set_speed(speed)
        self.set_position(position)
        self.run()

    def wait_for_stop(self):
        time.sleep(0.1)
        while math.fabs(self.get_speed()) > 3:
            time.sleep(0.05)

    def run(self, value = 1):
        path = self.path + 'run'
        self.write(path, str(value))

    def stop(self, hold = 0):
        self.run(0)
        self.set_hold_mode(hold)


class LCD(Communicate):

    def __init__(self):
        self.LCD_path = '/dev/fb0'

    def clear_screen(self):
        os.system('cat /dev/zero > /dev/fb0')


class Leds(Communicate):

    def __init__(self):
        self.path = '/sys/class/leds/'

    def set_led(self, color, led, value):
        color_text = ['red', 'green']
        led_text = ['left', 'right']
        path = self.path + 'ev3:' + color_text[color] + ':' + led_text[led]
        self.write(path + '/brightness', str(value))

    def set_led_red_left(self, value):
        self.set_led(0, 0, value)

    def set_led_red_right(self, value):
        self.set_led(0, 1, value)

    def set_led_green_left(self, value):
        self.set_led(1, 0, value)

    def set_led_green_right(self, value):
        self.set_led(1, 1, value)

    def get_led(self, color, led):
        color_text = ['red', 'green']
        led_text = ['left', 'right']
        path = self.path + 'ev3:' + color_text[color] + ':' + led_text[led]
        return int(self.read(path + '/brightness'))

    def get_led_red_left(self):
        return self.get_led(0, 0)

    def get_led_red_right(self):
        return self.get_led(0, 1)

    def get_led_green_left(self):
        return self.get_led(1, 0)

    def get_led_green_right(self):
        return self.get_led(1, 1)


class Robot(Communicate):

    def __init__(self):
        self.leds = Leds()
        self.LCD = LCD()

    def talk(self, s):
        self.write('/sys/devices/platform/snd-legoev3/volume', '100')
        os.system('espeak -v en -p 0 -s 120 "' + s + '" --stdout | aplay')

    def show_image(self, path):
        os.system('fbi -d /dev/fb0 -T 1 -noverbose -a ' + path)

