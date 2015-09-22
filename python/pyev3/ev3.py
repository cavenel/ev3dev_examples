import pyudev
import time
from subprocess import Popen, PIPE
import os
import math
import logging

log = logging.getLogger(__name__)

class Communicate(object):
    @staticmethod
    def read(path):
        with open(path, 'r') as pin:
            return pin.read().strip()

    @staticmethod
    def write(path, value):
        with open(path, 'w') as pout:
            pout.write(value)

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
            sensor_port = self.read("/sys/class/lego-sensor/%s/port_name" % sensor)
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


class Infrared_sensor(Sensor):
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
    def __init__(self, port, desc=None):
        if port.upper() not in ('A', 'B', 'C', 'D'):
            raise ValueError('Motor Port is not valid')

        target_port_name = 'out' + port.upper()
        motors = pyudev.Context().list_devices(subsystem='tacho-motor')

        for device in motors:
            if target_port_name == device.get('LEGO_PORT_NAME', ''):
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
        #log.info("%s set_position_sp %s" % (self, value))
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

    def reset_position(self, value = 0):
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
        return self.read(self.path + 'stop_command')

    def get_regulation_mode(self):
        return self.read(self.path + 'speed_regulation')

    def get_run_commands(self):
        return self._read_file('commands').split()

    def get_stop_commands(self):
        return self._read_file('stop_commands').split()

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
        return self._read_file('port_name')

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
        self._write_file('stop_command', value)

    def set_regulation_mode(self, value):
        assert value in ('on', 'off'), "%s is not supported" % value
        self._write_file('speed_regulation', value)


    # ___ macros ___

    def set_ramps(self, up, down):
        path = self.path + 'ramp_up_sp'
        self.write(path, str(up))
        path = self.path + 'ramp_down_sp'
        self.write(path, str(down))

    def rotate_forever(self, speed=480, regulate='on', stop_mode='brake'):
        log.info("%s rotate_forever at speed %d" % (self, speed))
        self.set_stop_mode(stop_mode)
        if regulate=='on':
            self.set_speed_sp(speed)
        else:
            self.set_duty_cycle_sp(speed)
        self.set_regulation_mode(regulate)
        self.set_run_mode('run-forever')

    def rotate_time(self, time, speed=480, up=0, down=0, regulate='on', stop_mode='brake'):
        log.info("%s rotate for %dms at speed %d" % (self, time, speed))
        self.set_stop_mode(stop_mode)
        self.set_regulation_mode(regulate)
        self.set_ramps(up, down)
        if regulate=='on':
            self.set_speed_sp(speed)
        else:
            self.set_duty_cycle_sp(speed)
        self.set_time_sp(time)
        self.set_run_mode('run-timed')

    def rotate_position(self, position, speed=480, up=0, down=0, regulate='on', stop_mode='brake'):
        log.info("%s rotate for %d at speed %d" % (self, position, speed))
        self.set_stop_mode(stop_mode)
        self.set_regulation_mode(regulate)
        self.set_ramps(up, down)
        if regulate=='on':
            self.set_speed_sp(speed)
        else:
            self.set_duty_cycle_sp(speed)
        self.set_position_sp(position)
        self.set_run_mode('run-to-rel-pos')

    def goto_position(self, position, speed=480, up=0, down=0, regulate='on', stop_mode='brake', wait=0):
        log.info("%s rotate to %d at speed %d" % (self, position, speed))
        self.set_stop_mode(stop_mode)
        self.set_regulation_mode(regulate)
        self.set_ramps(up, down)

        if regulate=='on':
            self.set_speed_sp(speed)
        else:
            self.set_duty_cycle_sp(speed)

        self.set_position_sp(position)
        sign = math.copysign(1, self.get_position() - position)
        self.set_run_mode('run-to-abs-pos')

        if (wait):
            self.wait_for_stop()

            if (not stop_mode == "hold"):
                self.stop()

    def wait_for_stop(self):
        prev = None
        no_movement = 0

        while True:
            curr = self.get_position()
            #log.info("%s wait_for_stop prev %s, curr %s" % (self, prev, curr))

            if prev is not None and abs(curr - prev) < 3:
                no_movement += 1
                if no_movement >= 5:
                    break
                else:
                    continue
            no_movement = 0
            prev = curr
            time.sleep(0.05)

    def is_running(self):
        return True if 'running' in self.get_state() else False

    def stop(self, stop_mode='coast'):
        log.info("%s stop to %s" % (self, stop_mode))
        self.set_stop_mode(stop_mode)
        self.set_run_mode('stop')


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

    def beep(self):
        self.write('/sys/devices/platform/snd-legoev3/volume', '100')
        os.system('beep')

    def talk(self, s, wait=1):
        self.write('/sys/devices/platform/snd-legoev3/volume', '100')
        if wait:
            os.system('espeak -v en -p 20 -s 120 "' + s + '" --stdout | aplay')
        else:
            espeak = Popen(("espeak","-v","en","-p","20","-s","120",'"' + s + '"',"--stdout"), stdout=PIPE)
            output = check_output(('aplay'), stdin=espeak.stdout)

    def show_image(self, path):
        os.system('fbi -d /dev/fb0 -T 1 -noverbose -a ' + path)

