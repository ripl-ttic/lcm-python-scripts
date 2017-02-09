import sys
import struct
import math
#import pylab
#import matplotlib
#matplotlib.use('Qt4Agg')
import matplotlib.pyplot as pyplot

#import scipy
import cStringIO as StringIO
import time

from optparse import OptionParser
from lcm import EventLog
from erlcm.trajectory_controller_aux_t import trajectory_controller_aux_t
from erlcm.raw_odometry_msg_t import raw_odometry_msg_t
from erlcm.velocity_msg_t import velocity_msg_t


def plot_control (logfile):
    print "Loading %s..." % logfile
    log = EventLog (logfile, "r")

    start_time = -1

    # controller data
    aux_time = []; ct_err = []; ra_err = []; ct_err_corr = []; ra_err_corr = []
    steer_command = []; tv_command = []; rv_command = [];

    # low-level velocity data
    odometry_time = []; odometry_tv = []; odometry_rv = [];
    velocity_cmd_time = []; velocity_cmd_tv = []; velocity_cmd_rv = [];
    
    for event in log:
        if start_time < 0:
            if hasattr (event.data, 'read'):
                buf = event.data
            else:
                buf = StringIO.StringIO (event.data)
            buf.read (8)
            temp = struct.unpack (">q", buf.read (8))
            start_time = temp[0]
            local_time = time.localtime (start_time*1e-6)
            if local_time.tm_year < 2000:
                start_time = -1
                print "%s has bad utime or does not have utime by definition" % event.channel
            else:
                print "Logging started at %02d:%02d:%02d, %d-%02d-%02d" % (local_time.tm_hour, local_time.tm_min,
                                                                           local_time.tm_sec, local_time.tm_year,
                                                                           local_time.tm_mon, local_time.tm_mday)
        if event.channel == "TRAJECTORY_CONTROLLER_AUX":
            a = trajectory_controller_aux_t.decode (event.data)
            if a.utime > start_time:
                aux_time += [(a.utime - start_time) * 1e-6]
                ct_err += [a.cross_track_error]
                ra_err += [a.relative_angle]
                ct_err_corr += [a.cross_track_error_correction]
                ra_err_corr += [math.degrees(a.relative_angle_correction)]
                steer_command += [math.degrees(a.steer)]
                tv_command += [a.translational_velocity]
                rv_command += [math.degrees(a.rotational_velocity)]

        if event.channel == "ODOMETRY":
            o = raw_odometry_msg_t.decode (event.data)
            if o.utime > start_time:
                odometry_time += [(o.utime - start_time) * 1e-6]
                odometry_tv += [o.tv]
                odometry_rv += [math.degrees(o.rv)]

        if event.channel == "ROBOT_VELOCITY_CMD":
            v = velocity_msg_t.decode (event.data)
# this part is a hack because aux message was not set correctly before
            if v.utime > start_time:
                velocity_cmd_time += [(v.utime - start_time) * 1e-6]
                velocity_cmd_tv += [v.tv]
                velocity_cmd_rv += [math.degrees(v.rv)]
                
    t_max_list = []
    t_max_list.append (max (aux_time))
    t_max_list.append (max (odometry_time))
    t_max_list.append (max (velocity_cmd_time))
    t_max = max (t_max_list)
   
    pyplot.figure ()
    pyplot.plot (aux_time, ct_err)
    pyplot.xlabel ('Time (sec)')
    pyplot.ylabel ('Cross-track Error (m)')
    pyplot.title ('Cross-track Error')
    pyplot.axis ([0, t_max, -0.1, max (ct_err) + 0.1])
    
    
    pyplot.figure ()
    pyplot.plot (aux_time, ra_err)
    pyplot.xlabel ('Time (sec)')
    pyplot.ylabel ('Relative Angle (Error) (degrees)')
    pyplot.title ('Relative Angle (Error)')
    pyplot.axis ([0, t_max, -0.1, max (ra_err) + 0.1])

    pyplot.figure ()
    pyplot.plot (odometry_time, odometry_tv)
    pyplot.plot (velocity_cmd_time, velocity_cmd_tv, color='r')
    pyplot.xlabel ('Time (sec)')
    pyplot.ylabel ('Translational Velocity (m/s)')
    pyplot.title ('Low-level Translational Velocity Control')
    pyplot.axis ([0, t_max, -0.1, max (odometry_tv) + 0.1])
    pyplot.legend (('Actual', 'Requested'), 'upper left')

    pyplot.figure ()
    pyplot.plot (odometry_time, odometry_rv)
    pyplot.plot (velocity_cmd_time, velocity_cmd_rv, color='r')
    pyplot.xlabel ('Time (sec)')
    pyplot.ylabel ('Rotational Velocity (deg/s)')
    pyplot.title ('Low-level Rotational Velocity Control')
    pyplot.axis ([0, t_max, min (odometry_rv) - 5, max (odometry_rv) + 5])
    pyplot.legend (('Actual', 'Requested'), 'upper left')    

    
    pyplot.show ()


usage = "plot_control.py <logfile>"
parser = OptionParser (usage = usage)
(options, args) = parser.parse_args ()

if len (args) < 1:
    print "Usage: %s" % usage
else:
    plot_control (args[0])
