#!/usr/bin/env python
# coding: utf-8

from pyev3.rubiks import Rubiks

import logging
import time

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)5s: %(message)s')
log = logging.getLogger(__name__)

rub = Rubiks()
rubiks_present = 0
rubiks_present_target = 10

while True:
    dist = rub.infrared_sensor.get_prox()
    if (dist > 10 and dist < 50):
        rubiks_present += 1
        log.info("wait for cube...proximity %d, present for %d/%d" % (dist, rubiks_present, rubiks_present_target))
    else:
        if rubiks_present:
            log.info('wait for cube...cube removed')
        rubiks_present = 0

    if rubiks_present >= rubiks_present_target:
        log.info('wait for cube...cube found and stable')
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
