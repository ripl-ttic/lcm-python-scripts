#!/usr/bin/env python

# If pygst is not available, then we have the wrong version of python-gst
import sys
import os
import re
import optparse
import time

import lcm

import pygtk
pygtk.require('2.0')
import gtk, gobject

import pygst
pygst.require('0.10')
import gst


import gobject
#import summit
#from arlcm.robot_status_t import robot_status_t
#from arlcm.robot_state_enum_t import robot_state_enum_t
#from arlcm.robot_state_command_t import robot_state_command_t

lc = lcm.LCM()

class Slicer(gtk.Object):
    def __init__(self, device=None, channel=None, recognizer=None, 
                 output=None, notch=False, silent=False, spkr=False):
        super(Slicer, self).__init__()
        self.__pipeline = None
        self.__device = device
        self.__lcm_channel = channel
        self.__recognizer = recognizer
        self.__output = output
        self.__notch = notch
        self.__silent = silent
        self.__spkr = spkr
        self.__src_name = None

    def configure(self):
        #duration=10000000000l
        duration=3000000000l
        offset=duration/2

        conf = ''
        if self.__device:
            #conf = conf + 'alsasrc device=%s ! audioconvert ! audioresample ! queue' % (self.__device)
            conf = conf + 'pulsesrc name=source ' + 'device=' + self.__device
            self.__src_name = re.sub('hw:', '', self.__device)
        else:
            if self.__lcm_channel:
                chan_str = 'channel=%s' % (self.__lcm_channel)
                conf = conf + 'lcmsrc %s ! rtpL16depay ! audio/x-raw-int,endianness=4321,signed=true,width=16,depth=16,rate=16000,channels=1 ! audioconvert ! audioresample ' % (chan_str)
                self.__src_name = self.__lcm_channel
        
        if self.__notch:
            notch_str = '! audiochebband mode=band-reject poles=4 lower-frequency=1280 upper-frequency=1480 ! audioconvert '
            conf = conf + notch_str

        conf = conf + ' name=src ! tee name=tee ' 
        
        if self.__recognizer:
            conf = conf + ' ! slice slice-duration=%ld ! summitsink name=summit config=%s tee.src1 ! slice slice-duration=%ld slice-offset=%ld ! summitsink name=summit1 config=%s' % (duration, self.__recognizer, duration, offset, self.__recognizer)

        if self.__output:
            conf = conf + ' tee.src2 ! wavenc ! filesink location=%s-%s.wav' % (self.__output, self.__src_name)
            
        if self.__spkr:
            conf = conf + ' tee.src3 ! audioconvert ! audioresample ! alsasink sync=false max-lateness=10000 '

        print conf
        self.__pipeline = gst.parse_launch(conf)

        bus = self.__pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message::eos', self.__on_eos)
        bus.connect('message::application', self.__on_application)
        bus.connect('message::error', self.__on_error)
        self.__pipeline.set_state(gst.STATE_READY)

        print "Configured"

    def start(self):
        print "Starting... "
        if self.__device:
            print " Listening to Sound card: %s" % (self.__device)
        else:
            if self.__lcm_channel:
                print " Listening to LCM Channel: %s" % (self.__lcm_channel)
        if not self.__recognizer:
            print " WARNING: "
            print " WARNING: No recognizer cfg specified"
            print " WARNING: "
            print " WARNING: RECOGNIZER NOT RUNNING"
            print " WARNING: "
            if not self.__spkr and not self.__output:
                print " ERROR: No outputs or recognizer specified"
                print " ERROR: need to specify -r or -o <wav> or -S"
                sys.exit(1)
            
        if self.__silent:
            print " Silent: NOT PUBLISHING FAULTS!"

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

    def clean(self, text):
        text = text.replace('stop', '***STOP***')
        text = re.sub('<[^>]*>', '', text)
        text = re.sub(' +', '', text)
        text = text.strip()
        return text

    def __on_application(self, bus, message):
        nbest = message.structure['items']
        if len(nbest) > 0:
            text = self.clean(nbest[0])
            print "hello:%s: %s" % (self.__src_name, text)
            if "STOP" in text:
                if self.__silent:
                    print "found stop, NOT PUBLISHING FAULT"
                    '''cmd = robot_state_command_t()
                    cmd.utime = 1000 * time.time()
                    cmd.state = robot_state_enum_t.UNDEFINED
                    cmd.faults = robot_status_t.FAULT_NONE
                    cmd.fault_mask = robot_status_t.FAULT_MASK_NO_CHANGE'''
                else:
                    print "found stop"
                    '''cmd = robot_state_command_t()
                    cmd.utime = 1000 * time.time()
                    cmd.state = robot_state_enum_t.ERROR
                    cmd.faults = robot_status_t.FAULT_SHOUT
                    cmd.fault_mask = robot_status_t.FAULT_MASK_NO_CHANGE
                    cmd.sender = "Shout module"
                    cmd.comment = "Shout detected"
                    lc.publish("ROBOT_STATE_COMMAND",cmd.encode())

                    time.sleep(2)

                    cmd = robot_state_command_t()
                    cmd.utime = 1000 * time.time()
                    cmd.state = robot_state_enum_t.ERROR
                    cmd.faults = robot_status_t.FAULT_NONE
                    cmd.fault_mask = robot_status_t.FAULT_SHOUT'''

                '''cmd.sender = "Shout module"
                cmd.comment = "Shout cancelled"
                lc.publish("ROBOT_STATE_COMMAND",cmd.encode())'''

    def __del__(self):
        self.__destroy_pipeline()
        super(Slicer, self).__del__()

gobject.type_register(Slicer)
    
def main():
    usage = "usage: %prog [options]"
    parser = optparse.OptionParser(usage)
    #parser.set_defaults(rec="rec/agile-stop.cfg")
    myrec=os.getenv('SUMMIT_RECOGNIZER_CFG');
    parser.set_defaults(rec=myrec);
    parser.set_defaults(sil=False)
    parser.set_defaults(notch=False)
    parser.set_defaults(spkr=False)
    parser.add_option("-i", "--input",
                      action="append",
                      dest="indevice",
                      help="Input device (Supports multiple sound cards)")
    parser.add_option("-c", "--channel",
                      action="append",
                      dest="inchannel",
                      help="Input LCM channel (Supports multiple channels: -c chan1 -c chan2 ). ")
    parser.add_option("-r", "--recognizer",
                      dest="rec",
                      help="Recognizer configuration file",
                      type=str)
    parser.add_option("-o", "--output",
                      dest="output",
                      help="Output .wav logfile prefix",
                      type=str)
    parser.add_option("-n", "--notch",
                      dest="notch",
                      help="Use Notch filter",
                      action="store_true")
    parser.add_option("-S", "--spkr",
                      dest="spkr",
                      help="Output audio to speaker",
                      action="store_true")
    parser.add_option("-s", "--silent",
                      dest="sil",
                      help="Publish detections but do not spawn faults",
                      action="store_true")
    (options, args) = parser.parse_args()
    myrec = options.rec 
    sil = options.sil
    mynotch = options.notch
    myspkr = options.spkr
    print myrec
    #'alsa_input.usb-Logitech_Logitech_Wireless_Headset_H760-00-H760.analog-mono' 
    # sound cards
    if options.indevice:
        for mydev in options.indevice:
            slicer = Slicer(device=mydev,
                            channel=None,
                            recognizer=myrec, 
                            output=options.output, 
                            notch=mynotch, silent=sil, spkr=myspkr)
            slicer.start()
    # lcm channels
    if options.inchannel:
        for mychan in options.inchannel:
            slicer = Slicer(device=None,
                            channel=mychan,
                            recognizer=myrec, 
                            output=options.output, notch=mynotch, silent=sil, spkr=myspkr)
            slicer.start()

    gtk.main()
        
main()
