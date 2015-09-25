#!/usr/bin/env python
# coding: utf-8

from pyev3.rubiks import Rubiks
from time import time as current_time
import logging
import sys

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(filename)12s %(levelname)8s: %(message)s')
log = logging.getLogger(__name__)
log.info('import complete')

rub = Rubiks()

while True:
    rub.wait_for_cube_insert()
    rub.scan()

    last_time = current_time()
    rub.resolve(computer=0)
    total = int(current_time() - last_time)
    rub.talk(str(total) + " seconds. Ha ha ha.")

    rub.mot_push.wait_for_stop()
    rub.mot_bras.wait_for_stop()
    rub.mot_rotate.wait_for_stop()
    rub.mot_push.stop()
    rub.mot_bras.stop()
    rub.mot_rotate.stop()
    rub.wait_for_cube_removal()
