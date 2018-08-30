#!/usr/bin/env python

import time
import sys

from lcm import LCM
from ripl.floor_change_msg_t import floor_change_msg_t



def publish_floor_change (floor_number):
    lcm = LCM()

    msg = floor_change_msg_t()
    msg.utime = int(time.time() * 1e6)
    msg.floor_no = floor_number

    print "Publishing change to floor %d" % floor_number
    lcm.publish("FLOOR_CHANGE", msg.encode())




if len(sys.argv) == 2:
    floor = int(sys.argv[1])
    publish_floor_change (floor)
else:
    print "hr-floor-change FloorNum"
