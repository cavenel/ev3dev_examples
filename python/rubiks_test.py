#!/usr/bin/env python
# coding: utf-8

from pyev3.rubiks import Rubiks
from time import time as current_time
import logging
import sys

logging.basicConfig(filename='rubiks.log',
                    filemode='w',
                    level=logging.INFO,
                    format='%(asctime)s %(filename)12s %(levelname)8s: %(message)s')
log = logging.getLogger(__name__)
log.info('Begin...')
rub = Rubiks()

try:
    rub.leds.set_all('green')
    rub.wait_for_cube_insert()
    rub.scan()

    if rub.shutdown_flag:
        rub.leds.set_all('green')
        sys.exit(0)

    last_time = current_time()
    rub.resolve()
    rub.leds.set_all('green')

    if rub.shutdown_flag:
        sys.exit(0)

    #total = int(current_time() - last_time)
    #rub.talk(str(total) + " seconds. Ha ha ha.")
    rub.mot_push.wait_for_stop()
    rub.mot_bras.wait_for_stop()
    rub.mot_rotate.wait_for_stop()
    rub.mot_push.stop()
    rub.mot_bras.stop()
    rub.mot_rotate.stop()
except Exception as e:
    rub.leds.set_all('red')
    log.exception(e)
    sys.exit(1)
