from time import time
from lcm import EventLog
from bot_core.planar_lidar_t import planar_lidar_t
from bot_core.image_t import image_t
from xsens.ins_t import ins_t
import sys

fname_in = sys.argv[1]
log = EventLog(fname_in, "r")

print >> sys.stderr, "opened %s" % fname_in

imu_utime = -1;

for e in log:

    if e.channel == "IMU":
        imu = ins_t.decode(e.data)

        imu_utime = imu.utime

    if (e.channel == "SKIRT_FRONT" or e.channel == "SKIRT_REAR"):
        lidar = planar_lidar_t.decode(e.data)

        delta = (lidar.utime - imu_utime) * 1E-6
        if (abs(delta) > 0.2):
            print "%s: Difference from IMU is %.4f" % (e.channel, delta)

    if e.channel == "DRAGONFLY_IMAGE":
        image = image_t.decode(e.data)

        delta = (image.utime - imu_utime) * 1E-6
        if (abs(delta) > 0.2):
            print "%s: Difference from IMU is %.4f" % (e.channel, delta)
