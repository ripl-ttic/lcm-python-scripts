#!/usr/bin/env python

import time

from lcm import LCM
from erlcm.floor_change_t import floor_change_t



def floor_change (floor_number):
    lcm = LCM()

    msg = floor_change_t()
    msg.utime = int(time.time() * 1e6)
    msg.floor_no = floor_number

    print "Publishing change to floor %d" % floor_number
    lcm.publish("FLOOR_CHANGE", msg.encode())




if len(sys.argv) == 2:
    floor = sys.argv[1]
    publish_floor_change (floor)
else:
    print "hr-floor-change FloorNum"
