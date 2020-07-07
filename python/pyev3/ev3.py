import pyudev
import time
from subprocess import Popen, PIPE
import os
import math
import logging
import array
import fcntl

log = logging.getLogger(__name__)

def median(data):
    data = sorted(data)

    if len(data) < 1:
        return None
    elif len(data) % 2 == 1:
        return data[((len(data)+1)/2)-1]
    else:
        return float(sum(data[(len(data)/2)-1:(len(data)/2)+1]))/2.0

class Communicate(object):

    @staticmethod
    def read(path):
        with open(path, 'r') as pin:
            try:
                return pin.read().strip()
            except IOError as e:
                log.warning("Failed to read %s" % path)
                raise e

    @staticmethod
    def write(path, value):
        with open(path, 'w') as pout:
            try:
                pout.write(value)
            except IOError as e:
                log.warning("Failed to write %s to %s" % (value, path))
                raise e

    @staticmethod
    def min_max(value, mini=-100, maxi=100):
        return max(mini, min(maxi, value))


class Sensor(Communicate):

    def __init__(self, type_id=None, port=None):
        if port and port not in ('1', '2', '3', '4'):
            raise ValueError('Sensor Port is not valid')

        self.mode = None

        sensors = []
        target_port = 'in' + port if port else None

        for sensor in os.listdir('/sys/class/lego-sensor/'):
            sensor_type_id = self.read("/sys/class/lego-sensor/%s/driver_name" % sensor)
            sensor_port = self.read("/sys/class/lego-sensor/%s/address" % sensor)
            sensors.append((sensor_port, sensor_type_id))

            if type_id:
                if type_id == sensor_type_id:
                    self.path = os.path.join('/sys/class/lego-sensor/', sensor)
                    break

            if target_port:
                if target_port == sensor_port:
                    self.path = os.path.join('/sys/class/lego-sensor/', sensor)
                    break

        else:  # I love for-else blocks
            log.info("Available Sensors:\n%s" % '\n'.join(map(str, sensors)))
            raise EnvironmentError("Sensor not found")

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
        Sensor.__init__(self, type_id='lego-ev3-touch')

    def is_pushed(self):
        return self.get_value()


class Color_sensor(Sensor):
    colors = (None, 'black', 'blue', 'green', 'yellow', 'red', 'white', 'brown')

    def __init__(self):
        Sensor.__init__(self, type_id='lego-ev3-color')

    def get_rgb(self):
        self.set_mode('RGB-RAW')
        return self.get_values(3)

    def get_reflect(self):
        self.set_mode('COL-REFLECT')
        return self.get_value()

    def get_ambient(self):
        self.set_mode('COL-AMBIENT')
        return self.get_value()

    def get_color(self):
        self.set_mode('COL-COLOR')
        return colors[self.get_value()]

class Distance_sensor(Sensor):

    def get_prox(self):
        raise NotImplementedError

    def is_in_range(self):
        raise NotImplementedError

class Infrared_sensor(Distance_sensor):

    def __init__(self):
        Sensor.__init__(self, type_id='lego-ev3-ir')

    def get_remote(self):
        self.set_mode('IR-REMOTE')
        return self.get_values(4)

    def get_remote_bin(self):
        self.set_mode('IR-REM-A')
        return self.get_value()

    def get_prox(self):
        self.set_mode('IR-PROX')
        return self.get_value()

    def is_in_range(self):
        dist = self.get_prox()
        if (dist > 10 and dist < 50):
            return True
        else:
            return False

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

class Ultrasonic_sensor(Distance_sensor):

    def __init__(self):
        Sensor.__init__(self, type_id='lego-ev3-us')

    def get_prox(self):
        self.set_mode('US-DIST-CM')
        return self.get_value()

    def is_in_range(self):
        dist = self.get_prox()
        if (dist > 70 and dist < 140):
            return True
        else:
            return False

class Motor(Communicate):

    def __init__(self, port, desc=None):
        if port.upper() not in ('A', 'B', 'C', 'D'):
            raise ValueError('Motor Port is not valid')

        target_port_name = 'ev3-ports:out' + port.upper()
        motors = pyudev.Context().list_devices(subsystem='tacho-motor')

        for device in motors:
            if target_port_name == device.get('LEGO_ADDRESS', ''):
                self.path = device.sys_path + '/'
                self.port = port.upper()
                break
        else:
            log.info("Available Motors:\n%s" % '\n\n'.join(map(str, motors)))
            raise EnvironmentError("Motor not found")

        self.desc = desc
        self.run_commands = self.get_run_commands()
        self.stop_commands = self.get_stop_commands()
        self.stop()
        time.sleep(0.1)
        self.reset()

    def __str__(self):
        if self.desc:
            return self.desc
        return "Motor %s" % self.port

    def _write_file(self, filename, value):
        path = os.path.join(self.path, filename)
        self.write(path, str(value))

    def _read_file(self, filename):
        return self.read(os.path.join(self.path, filename))

    # ___ sp ___

    def set_duty_cycle_sp(self, value):
        return self._read_file('duty_cycle_sp')

    def set_time_sp(self, value):
        path = self.path + 'time_sp'
        self.write(path, str(value))

    def set_position_sp(self, value):
        path = self.path + 'position_sp'
        self.write(path, str(int(value)))

    def get_duty_cycle_sp(self):
        return int(self._read_file('duty_cycle_sp'))

    def get_time_sp(self):
        return int(self.read(self.path + 'time_sp'))

    def get_position(self):
        return int(self._read_file('position'))

    # ___ info ___

    def reset(self):
        self._write_file('command', 'reset')

    def reset_position(self, value=0):
        path = self.path + 'position'
        self.write(path, str(value))

    def get_duty_cycle(self):
        return int(self._read_file('duty_cycle'))

    def get_position(self):
        return int(self.read(self.path + 'position'))

    def get_power(self):
        return int(self.read(self.path + 'power'))

    def get_state(self):
        return self._read_file('state')

    def get_stop_mode(self):
        return self.read(self.path + 'stop_action')

    def get_run_commands(self):
        return self._read_file('commands').split()

    def get_stop_commands(self):
        return self._read_file('stop_actions').split()

    def get_count_per_rotation(self):
        return int(self._read_file('count_per_rot'))

    def get_driver_name(self):
        return self._read_file('driver_name')

    def set_polarity(self, mode):
        assert mode in ('normal', 'inversed'), "%s is not supported" % mode
        self._write_file('polarity', mode)

    def get_polarity(self):
        return self._read_file('polarity')

    def get_port_name(self):
        return self._read_file('address')

    def get_pulses_per_second_sp(self):
        return int(self.read(self.path + 'pulses_per_second_sp'))

    def get_speed(self):
        return int(self._read_file('speed'))

    def get_speed_sp(self):
        return int(self._read_file('speed_sp'))

    def set_speed_sp(self, value):
        self._write_file('speed_sp', value)

    def set_run_mode(self, value):
        assert value in self.run_commands, "%s is not supported, choices are %s" % (value, ','.join(self.run_commands))
        self._write_file('command', value)

    def set_stop_mode(self, value):
        assert value in self.stop_commands, "%s is not supported" % value
        self._write_file('stop_action', value)

    # ___ macros ___

    def set_ramps(self, up, down):
        path = self.path + 'ramp_up_sp'
        self.write(path, str(up))
        path = self.path + 'ramp_down_sp'
        self.write(path, str(down))

    def rotate_forever(self, speed=480, regulate='on', stop_mode='brake'):
        log.debug("%s rotate_forever at speed %d" % (self, speed))
        self.set_stop_mode(stop_mode)
        if regulate == 'on':
            self.set_speed_sp(speed)
        else:
            self.set_duty_cycle_sp(speed)
        self.set_run_mode('run-forever')
        self.wait_for_start()

    def rotate_time(self, time, speed=480, up=0, down=0, regulate='on', stop_mode='brake'):
        log.debug("%s rotate for %dms at speed %d" % (self, time, speed))
        self.set_stop_mode(stop_mode)
        self.set_ramps(up, down)
        if regulate == 'on':
            self.set_speed_sp(speed)
        else:
            self.set_duty_cycle_sp(speed)
        self.set_time_sp(time)
        self.set_run_mode('run-timed')
        self.wait_for_start()

    def rotate_position(self, position, speed=480, up=0, down=0, regulate='on', stop_mode='brake', accuracy_sp=None):
        log.debug("%s rotate for %d at speed %d" % (self, position, speed))
        self.set_stop_mode(stop_mode)
        self.set_ramps(up, down)
        if regulate == 'on':
            self.set_speed_sp(speed)
        else:
            self.set_duty_cycle_sp(speed)
        self.set_position_sp(position)
        self.set_run_mode('run-to-rel-pos')
        self.wait_for_start()

    def goto_exact_position(self, position, regulate='on', accuracy_sp=None):
        if regulate != 'on':
            raise Exception("accuracy_sp only works with regulate=on")

        self.set_speed_sp(accuracy_sp)
        current_pos = self.get_position()
        log.debug("Current pos %d, target pos %d" % (current_pos, position))

        attempt = 0
        while current_pos != position:
            self.set_run_mode('run-to-abs-pos')
            self.wait_for_start()
            self.wait_for_stop()
            current_pos = self.get_position()
            log.debug("Current pos %d, target pos %d" % (current_pos, position))
            attempt += 1

            if attempt >= 10:
                log.warning("We could not get to target pos %d" % position)
                break

    def goto_position(self, position, speed=480, up=0, down=0, regulate='on', stop_mode='brake', wait=0, accuracy_sp=None):
        log.debug("%s rotate to %d at speed %d" % (self, position, speed))
        self.set_stop_mode(stop_mode)
        self.set_ramps(up, down)

        if regulate == 'on':
            self.set_speed_sp(speed)
        else:
            self.set_duty_cycle_sp(speed)

        self.set_position_sp(position)
        sign = math.copysign(1, self.get_position() - position)
        self.set_run_mode('run-to-abs-pos')
        self.wait_for_start()

        if accuracy_sp or wait:
            self.wait_for_stop()

            #if (not stop_mode == "hold"):
            #    self.stop()

        # If accuracy_sp is set we must rotate the motor to the EXACT degree desired
        if accuracy_sp:
            self.goto_exact_position(position, regulate, accuracy_sp)

    def wait_for_start(self):
        prev = None
        attempt = 0
        log.debug("%s waiting for start" % self)

        while True:
            curr = self.get_position()

            if prev is not None and curr != prev:
                log.debug("%s started" % self)
                return
            prev = curr
            attempt += 1

            # If it was a short move for the motor maybe we missed it...don't
            # stay in this loop for forever
            if attempt >= 50:
                log.debug("%s started (max attempts)" % self)
                return

    def wait_for_stop(self):
        prev = None
        no_movement = 0
        log.debug("%s waiting for stop" % self)

        while True:
            curr = self.get_position()

            if prev is not None and abs(curr - prev) < 3:
                no_movement += 1
                if no_movement >= 3:
                    log.debug("%s stopped" % self)
                    break
                else:
                    continue
            no_movement = 0
            prev = curr
            time.sleep(0.05)

    def is_running(self):
        return True if 'running' in self.get_state() else False

    def stop(self, stop_mode='coast'):
        self.set_stop_mode(stop_mode)
        self.set_run_mode('stop')


class LCD(Communicate):

    def __init__(self):
        self.LCD_path = '/dev/fb0'

    def clear_screen(self):
        os.system('cat /dev/zero > /dev/fb0')


class InvalidColor(Exception):
    pass

class Leds(Communicate):

    def __init__(self):
        self.path = '/sys/class/leds/'

    def _get_path(self, color, led):
        """
        The four LEDs are:

        led0:red:brick-status
        led0:green:brick-status
        led1:red:brick-status
        led1:green:brick-status
        """

        if color == 'red':
            color_text = '0:red'
        elif color == 'green':
            color_text = '1:green'
        else:
            raise InvalidColor("%s is not a supported color (red, green)" % color)

        return self.path + 'led' + led + color_text + ':brick-status'

    def set_led(self, color, led, value):
        path = os.path.join(self._get_path(color, led), 'brightness')
        self.write(path, str(value))

    def set_all(self, color, value=255):

        if color == 'red':
            self.set_led('red', '', value)
            self.set_led('red', '', value)
            self.set_led('green', '', 0)
            self.set_led('green', '', 0)

        elif color == 'green':
            self.set_led('red', '', 0)
            self.set_led('red', '', 0)
            self.set_led('green', '', value)
            self.set_led('green', '', value)

        elif color == 'orange':
            self.set_led('red', '', 255)
            self.set_led('red', '', 255)
            self.set_led('green', '', 180)
            self.set_led('green', '', 180)

        elif color == 'yellow':
            self.set_led('red', '', 25)
            self.set_led('red', '', 25)
            self.set_led('green', '', 255)
            self.set_led('green', '', 255)

        elif color == 'off':
            self.set_led('red', '', 0)
            self.set_led('red', '', 0)
            self.set_led('green', '', 0)
            self.set_led('green', '', 0)

        else:
            raise InvalidColor("%s is not a supported color" % color)

    def set_led_red_left(self, value):
        self.set_led('red', 'left', value)

    def set_led_red_right(self, value):
        self.set_led('red', 'right', value)

    def set_led_green_left(self, value):
        self.set_led('green', 'left', value)

    def set_led_green_right(self, value):
        self.set_led('green', 'right', value)

    def get_led(self, color, led):
        path = os.path.join(self._get_path(color, led), 'brightness')
        return int(self.read(path))

    def get_all(self):
        red_left = self.get_led('red', 'left')
        red_right = self.get_led('red', 'right')
        green_left = self.get_led('green', 'left')
        green_right = self.get_led('green', 'right')

        if red_left and red_right and not green_left and not green_right:
            return 'red'

        elif not red_left and not red_right and green_left and green_right:
            return 'green'

        elif red_left == 255 and red_right == 255 and green_left == 180 and green_right == 180:
            return 'orange'

        elif red_left == 25 and red_right == 25 and green_left == 255 and green_right == 255:
            return 'yellow'

        elif not red_left and not red_right and not green_left and not green_right:
            return 'off'

        return (red_left, red_right, green_left, green_right)

    def get_led_red_left(self):
        return self.get_led('red', 'left')

    def get_led_red_right(self):
        return self.get_led('red', 'right')

    def get_led_green_left(self):
        return self.get_led('green', 'left')

    def get_led_green_right(self):
        return self.get_led('green', 'right')


class InvalidButton(Exception):
    pass


class Buttons(Communicate):

    def __init__(self):
        self.valid_buttons = ('UP', 'DOWN', 'LEFT', 'RIGHT', 'ENTER', 'BACKSPACE')
        self.key_codes = {
            'UP' : 103,
            'DOWN' : 108,
            'LEFT' : 105,
            'RIGHT' : 106,
            'ENTER' : 28,
            'BACKSPACE' : 14
        }
        KEY_MAX = 0x2ff
        self.BUF_LEN = (KEY_MAX + 7) / 8

    def get_button(self, button):
        """
        Return True if button is pressed, else return False

        Borrowed from:
        https://github.com/ev3dev/ev3dev/wiki/Using-the-Buttons
        """

        def test_bit(bit, bytes):
            # bit in bytes is 1 when released and 0 when pressed
            return bool(bytes[bit / 8] & (1 << (bit % 8)))

        def EVIOCGKEY(length):
            return 2 << (14+8+8) | length << (8+8) | ord('E') << 8 | 0x18

        button = button.upper()

        if button not in self.valid_buttons:
            raise InvalidButton("%s is not a supported button" % button)

        buf = array.array('B', [0] * self.BUF_LEN)

        with open('/dev/input/by-path/platform-gpio_keys-event', 'r') as fd:
            ret = fcntl.ioctl(fd, EVIOCGKEY(len(buf)), buf)

        if ret < 0:
            raise IOError("Could not read from /dev/input/by-path/platform-gpio_keys-event")

        return test_bit(self.key_codes[button], buf) and True or False


class Robot(Communicate):

    def __init__(self):
        self.leds = Leds()
        self.LCD = LCD()
        self.buttons = Buttons()

    def beep(self):
        self.write('/sys/devices/platform/snd-legoev3/volume', '100')
        os.system('beep')

    def talk(self, s, wait=1):
        self.write('/sys/devices/platform/snd-legoev3/volume', '100')
        if wait:
            os.system('espeak -v en -p 20 -s 120 "' + s + '" --stdout | aplay')
        else:
            espeak = Popen(("espeak", "-v", "en", "-p", "20", "-s", "120", '"' + s + '"', "--stdout"), stdout=PIPE)
            output = check_output(('aplay'), stdin=espeak.stdout)

    def show_image(self, path):
        os.system('fbi -d /dev/fb0 -T 1 -noverbose -a ' + path)
