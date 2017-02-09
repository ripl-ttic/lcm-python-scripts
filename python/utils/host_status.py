#!/usr/bin/env python

import time
import sys
import os

from lcm import LCM
from erlcm.host_status_t import host_status_t

lcm = LCM()

if len(sys.argv) > 1:
    hostname = sys.argv[1]
else:
    hostname = os.popen('uname -n').readline().strip()

# determine number of processors
temp = os.popen('cat /proc/cpuinfo | grep processor | wc -l').readline()
num_processors = int(temp[0])

# do we have the cpufrequtils package
temp = os.popen('which cpufreq-info').readline()
have_cpufrequtils = 1
if (len(temp) == 0):
    print "cpufrequtils package required for cpu frequency info"
    have_cpufrequtils = 0

while (True):
    msg = host_status_t()
    msg.utime = int(time.time() * 1e6)
    msg.id = hostname

    # Get cpu status info
    # min/max cpu frequencies
    msg.num_processors = num_processors

    for i in range(num_processors):
        if (have_cpufrequtils == 1):
            cpufreq_info_str = 'cpufreq-info -l -c %d' % i
            cpufreq_info_limits = os.popen(cpufreq_info_str).readline()
            a = cpufreq_info_limits.split()
            if len(a) > 0:
                msg.min_cpu_freq_hz += [int(a[0])*1000]
            #msg.max_cpu_freq_hz += [int(a[1])*1000]

            cpufreq_info_str = 'cat  /sys/devices/system/cpu/cpu%d/cpufreq/scaling_max_freq' % i
            cpufreq_info_limits = os.popen(cpufreq_info_str).readline()
            msg.max_cpu_freq_hz += [int(cpufreq_info_limits)*1000]

        
            cpufreq_info_str = 'cpufreq-info -f -c %d' % i
            cpufreq_info_current = os.popen(cpufreq_info_str).readline()
            msg.cur_cpu_freq_hz += [int(cpufreq_info_current)*1000]
        else:
            msg.min_cpu_freq_hz += [0]
            msg.max_cpu_freq_hz += [0]
            msg.cur_cpu_freq_hz += [0]

    # Get power status info
    info = os.popen('acpi -t').readlines()
    if (len(info) > 0):
        temp_c = float(info[len(info)-1].split()[3])
        msg.temp_C = temp_c

    ac_info = os.popen('acpi -a').readline()
    if (len(ac_info) > 0):
        msg.plugged_in = (ac_info.split()[2] == 'on-line')

    bat_info = os.popen('acpi -b').readlines()
    msg.nbatteries = len(bat_info)
    msg.battery_charge = []
    for i in range(0,len(bat_info)):
        b = bat_info[i].split()
        msg.battery_charge.append(float(b[3].rstrip('%,')) * 0.01)        

    lcm.publish("HOST_STATUS", msg.encode())
    time.sleep(1)
