#!/usr/bin/env python
# coding: utf-8

from pyev3.rubiks import Rubiks

import time

rub = Rubiks()
rubiks_present = 0

while(True):
    dist = rub.infrared_sensor.get_prox()
    if (dist > 7 and dist < 15):
        rubiks_present += 1
    else:
        rubiks_present = 0
    if rubiks_present > 10:
        break
    time.sleep(0.1)

rub.scan()
last_time = time.time()
rub.resolve(computer = 0)
total = time.time() - last_time
total = int(total)
rub.talk(str(total) + " seconds. Ha ha ha.")

rub.mot_push.wait_for_stop()
rub.mot_bras.wait_for_stop()
rub.mot_rotate.wait_for_stop()
rub.mot_push.stop()
rub.mot_bras.stop()
rub.mot_rotate.stop()
