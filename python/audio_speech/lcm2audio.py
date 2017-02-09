#!/usr/bin/env python

# If pygst is not available, then we have the wrong version of python-gst
import sys
import os
import re
import argparse
import time

import lcm

import pygtk
pygtk.require('2.0')
import gtk, gobject

import pygst
pygst.require('0.10')
import gst


import gobject

lc = lcm.LCM()

class Lcm2audio(gtk.Object):
    def __init__(self, lcmlogfile=None, lcm_channel=None, wave=None,
                 output=None, spkr=False):
        super(Lcm2audio, self).__init__()
        self.__pipeline = None
        self.__lcm_logfile = lcmlogfile
        self.__lcm_channel = lcm_channel
        self.__wave=None
        if wave:
            self.__wave = re.sub('\.wav', '', wave)+'.wav'
        self.__output = output
        self.__spkr = spkr


    def configure(self):

        lcm_opts = ' channel=%s ' % (self.__lcm_channel)
        if self.__lcm_logfile:
            lcm_opts = lcm_opts + ' provider=file://%s' % (self.__lcm_logfile)
        conf = 'lcmsrc %s ! rtpL16depay ! audioconvert ! audioresample ' % (lcm_opts)
        
        conf = conf + ' name=src ! tee name=tee ' 
       
        if self.__wave:
            conf = conf + ' tee.src1 ! queue ! audioconvert ! audioresample ! audio/x-raw-int,rate=16000,width=16,depth=16,channels=1 ! wavenc ! filesink location=%s' % (self.__wave)

        if self.__output:
            conf = conf + ' tee.src2 ! queue ! audioconvert ! audioresample ! alsasink sync=false max-lateness=10000 device=%s ' % (self.__output)
            
        if self.__spkr:
            conf = conf + ' tee.src3 ! queue !  audioconvert ! audioresample ! alsasink sync=false max-lateness=10000 '

        print conf
        self.__pipeline = gst.parse_launch(conf)

        bus = self.__pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message::eos', self.__on_eos)
        bus.connect('message::error', self.__on_error)
        self.__pipeline.set_state(gst.STATE_READY)

        print "Configured"

    def start(self):
        print "Starting... "
        if self.__lcm_channel:
            print " Listening to LCM Channel: %s" % (self.__lcm_channel)
        if self.__wave:
            print " Outputing to wave: %s" % (self.__wave)
        if self.__output:
            print " Outputing to Alsa dev: %s" % (self.__output)

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
        super(Lcm2audio, self).__del__()

gobject.type_register(Lcm2audio)
    
def main():
    usage = "usage: %prog [options]"
    parser = argparse.ArgumentParser(description=usage)
    parser.set_defaults(spkr=False)
    #parser.set_defaults(out_waves=None)
    #parser.set_defaults(out_devices=None)
    parser.set_defaults(lcmlogfile=None)
    parser.add_argument ('-l', '--logfile',
                         dest="lcmlogfile",
                         default=None,
                         help="Uses <lcm log filename> instead of live messages (resets lcm provider).")
    parser.add_argument("-c", "--channel",
                        action="append",
                        dest="lcm_channels",
                        help="Input LCM channel (Supports multiple channels: -c chan1 -c chan2 ). ")
    parser.add_argument("-w", "--wave",
                        action="append",
                        dest="out_waves",
                        help="Output <name>.wav ",
                        type=str)
    parser.add_argument("-o", "--output",
                        action="append",
                        dest="out_devices",
                        help="Output audio to alsa <device> ")
    parser.add_argument("-S", "--spkr",
                        dest="spkr",
                        help="Output audio to speaker",
                        action="store_true")
    args = parser.parse_args()

    if args.out_waves:
        if len(args.lcm_channels) != len(args.out_waves):
            print "ERROR: number of wave filenames(%d) must match the number of lcm channels(%d)" % (len(args.out_waves),len(args.lcm_channels))
            sys.exit(1)
    if args.out_devices:
        if len(args.out_devices) != len(args.lcm_channels):
            print "ERROR: number of output devices (%d) must match number of lcm channels(%d)" % (len(args.out_devices),len(args.lcm_channels))
            sys.exit(1)

    if args.lcm_channels:
        for i in range(0,len(args.lcm_channels)):
            mylcmchan = device=args.lcm_channels[i]
            mywave=None
            if args.out_waves:
                mywave = device=args.out_waves[i]
            myoutput=None
            if args.out_devices:
                myoutput = device=args.out_devices[i]

            app = Lcm2audio(lcmlogfile=args.lcmlogfile,
                            lcm_channel=mylcmchan,
                            wave=mywave, 
                            output=myoutput, 
                            spkr=args.spkr)
            app.start()

    gtk.main()
       
main()
