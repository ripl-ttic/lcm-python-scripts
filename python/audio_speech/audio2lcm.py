#!/usr/bin/env python

# If pygst is not available, then we have the wrong version of python-gst
import sys
import os
import re
import optparse
import time

sys.path.append('/home/agile/agile/software/python/src')

import lcm

import pygtk
pygtk.require('2.0')
import gtk, gobject

import pygst
pygst.require('0.10')
import gst

import gobject


class Audio2lcm(gtk.Object):
    def __init__(self, device=None, src_file=None, wave=None, lcm_channel=None):
        super(Audio2lcm, self).__init__()
        self.__pipeline = None
        self.__device = device
        self.__src_file = src_file
        self.__wave = None
        if wave:
            self.__wave = re.sub('\.wav', '', wave)+'.wav'
        self.__lcm_channel = lcm_channel

    def configure(self):
        conf= ''
        if self.__device:
            conf = 'pulsesrc name=source ' + 'device=' + self.__device
            #'alsasrc device=%s ' % (self.__device)

        if self.__src_file:
            conf = 'filesrc location=%s ! decodebin ' % (self.__src_file)

        conf = conf + ' ! audioconvert ! audioresample ! audio/x-raw-int,rate=16000,width=16,depth=16,channels=1 ! audioconvert ' 

        if self.__lcm_channel and self.__wave:
            conf = conf + ' name=src ! tee name=tee '
            print "ERROR: Sorry lcm streaming and wave saving doesnt work at the same time (there is a bug in the gst pipeline :( )"
            sys.exit(1);

        if self.__lcm_channel:
            lcm_opts = 'channel=%s' % (self.__lcm_channel)
            conf = conf + ' ! rtpL16pay ! lcmsink %s ' % (lcm_opts)
        if self.__lcm_channel and self.__wave:
            conf = conf + ' tee.src2 '
        if self.__wave:
            conf = conf + '! audioconvert ! wavenc ! filesink location=%s.wav' % (self.__wave)

        print conf
        self.__pipeline = gst.parse_launch(conf)

        bus = self.__pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message::eos', self.__on_eos)
        bus.connect('message::error', self.__on_error)
        self.__pipeline.set_state(gst.STATE_READY)

        print "Configured"

    def start(self):
        print "Start"
        if (self.__device):
            print "Listening to:%s" % (self.__device)
        if (self.__lcm_channel):
            print "Logging to LCM channel:%s" % (self.__lcm_channel)
        if (self.__wave):
            print "Logging to wav file:%s" % (self.__wave)

        if not self.__pipeline:
            self.configure()
        self.__pipeline.set_state(gst.STATE_PLAYING)

    def stop(self):
        print "Stopping"
        src = self.__pipeline.get_by_name('src')
        if src:
            src.set_state(gst.STATE_READY)

    def __on_error(self, bus, message):
        print message

    def __on_eos(self, bus, message):
        print "eos"
        self.__pipeline.set_state(gst.STATE_NULL)

    def __del__(self):
        self.__destroy_pipeline()
        super(Audio2lcm, self).__del__()

gobject.type_register(Audio2lcm)
    
def main():
    usage = "usage: %prog [options]"
    parser = optparse.OptionParser(usage)
    parser.add_option("-i", "--input",
                      action="append",
                      dest="in_devices",
                      help="Input device for now either mic or headset is supported as input).")
    parser.add_option("-f", "--file",
                      action="append",
                      dest="in_files",
                      help="Input files e.g. music.ogg (multiple inputs can be given).")
    parser.add_option("-w", "--wave",
                      action="append",
                      dest="out_waves",
                      help="Wave filename e.g. name[.wav]  (must have same number of waves as inputs).",
                      type=str)
    parser.add_option("-l", "--lcm",
                      dest="lcm_channels",
                      help="Output LCM channel name e.g. AUDIO_DATA (must have same number of channels as inputs).",
                      action="append")
    (options, args) = parser.parse_args()

    num_inputs = 0 
    if options.in_files:
        num_inputs = len(options.in_files)
    if options.in_devices:
        num_inputs = len(options.in_devices)

    if num_inputs==0:
        print "ERROR: no inputs specified: devices=0  files=0"
        sys.exit(1)

    #currently lets use the mapping 
    snd_dev = {'mic':'alsa_input.pci-0000_00_1b.0.analog-stereo', 'headset': 'alsa_input.usb-Logitech_Logitech_G930_Headset-00-Headset.analog-mono'} #'alsa_input.usb-Logitech_Logitech_Wireless_Headset_H760-00-H760.analog-mono'}
        
        
    if options.out_waves:
        if num_inputs != len(options.out_waves):
            print "ERROR: number of inputs(%d) must match number of wave filenames(%d)" % (num_inputs,len(options.out_waves))
            sys.exit(1)
    if options.lcm_channels:
        if num_inputs != len(options.lcm_channels):
            print "ERROR: number of inputs(%d) must match number of lcm channels(%d)" % (len(options.in_devices),len(options.lcm_channels))
            sys.exit(1)
            

    for i in range(0,num_inputs):
        mydevice = None
        mywave=None
        mylcmchan=None
        mysrcfile=None
        if options.in_devices:
            if(snd_dev.has_key(options.in_devices[i])):
                mydevice = snd_dev[options.in_devices[i]]
            else:
                mydevice = options.in_devices[i]
        if options.in_files:
            mysrcfile = options.in_files[i]
        if options.out_waves:
            mywave = device=options.out_waves[i]
        if options.lcm_channels:
            mylcmchan =options.lcm_channels[i]
            
        app = Audio2lcm(device=mydevice, src_file=mysrcfile, wave=mywave, lcm_channel=mylcmchan)
        app.start()
    gtk.main()
        
main()
