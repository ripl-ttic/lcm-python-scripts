#!/usr/bin/python
import sys, os
import pygtk, gtk, gobject
pygtk.require('2.0')
if gtk.pygtk_version < (2,3,90):
   print "PyGtk 2.3.90 or later required for this example"
   raise SystemExit

import pygst
pygst.require("0.10")
import gst
import string
import platform
from time import *
import pango
from sys import argv
from optparse import OptionParser

sys.path.append( '../../build/lib/python2.6/site-packages/' )

import threading, thread

class GTK_Main:
	
	def __init__(self, src, log_path="", log_name=""):

                #----------System info
		release = platform.release()

                self.player_made = 0

                self.source = 'alsa_input.pci-0000_00_1b.0.analog-stereo'
                self.log_path = log_path
                self.log_name = log_name

                if(src == 'mic'):
                   self.source = 'alsa_input.pci-0000_00_1b.0.analog-stereo'
                elif(src == 'headset'):
                   self.source = 'alsa_input.usb-Logitech_Logitech_Wireless_Headset_H760-00-H760.analog-mono'
                
                #----Logging Parameters
                self.logging_mode = 1

                self.listening = 0

		#Audio Logs
		if self.logging_mode == 1:		
                   self.last_log_name = 'logs/last_file.log'	
                   try: 
		      #file exists so we start from the next position
                      a = open(self.last_log_name,'r')
                      self.sink_count = int(a.read()) + 1
                      a.close()
                      
                   except IOError, e:
		      #No previous logs - so start the logs at 0
                      self.sink_count = 0

		else: 
                   print "== Not Logging Audio ==" 

		self.mode = 'recording' #Listener State 

		#Main window 
		self.width = 700
		self.height = 500

		window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		window.set_title("Wheelchair DM")
		window.set_default_size(self.width, self.height) 
		window.connect("destroy", self.destroy, "WM destroy")

		#Notebook - for tabs		
		self.notebook = gtk.Notebook()
		self.notebook.set_tab_pos(gtk.POS_TOP)
		self.notebook.show()
		self.show_tabs = True
		self.show_border = True

		window.add(self.notebook)

		#####################################################################
		#Main tab
		
		results_vbox =  gtk.VBox()		
		results_label = gtk.Label("Dialog Manager")
		
		#add dialog manager tab 
		self.notebook.append_page(results_vbox, results_label)

		#Main Section 
		
		main_hbox = gtk.HBox()
		results_vbox.pack_start(main_hbox)

		#Speech Command buttons
		
		cmd_frame = gtk.Frame("Dialog Manager")
		cmd_vbox =  gtk.VBox()
		cmd_frame.add(cmd_vbox)

		main_hbox.pack_start(cmd_frame)                

		#Current Status Button - Listening/Sleep/Not Listening
		self.buttonLabelSize = pango.FontDescription('Sans 20')
		self.btnStartStop = gtk.Button()
		self.start_label = gtk.Label()
		self.start_label.set_markup('Not Listening')
		self.start_label.modify_font(self.buttonLabelSize)
		self.btnStartStop.add(self.start_label)
		self.btnStartStop.connect("clicked", self.start_stop)
		self.btnStartStop.set_size_request(self.width/2,40)
		
                button_hbox = gtk.HBox()
                cmd_vbox.pack_start(button_hbox)
                dm_button_vbox = gtk.VBox()

                button_hbox.pack_start(dm_button_vbox)
		dm_button_vbox.pack_start(self.btnStartStop)
                
                #Mode Display - Displays the Current DM - Tourguide/Navigation
                buttonLabelSize = pango.FontDescription('Sans 24')
		self.btnModeDisp = gtk.Button()
		self.mode_label = gtk.Label()
		self.mode_label.modify_font(buttonLabelSize)
		self.btnModeDisp.add(self.mode_label)
                #self.btnModeDisp.connect("clicked",self.change_mode_handler)
		self.btnModeDisp.set_size_request(self.width/2,40)
		dm_button_vbox.pack_start(self.btnModeDisp)
                
		window.show_all()
                
		self.get_colors(window)
		self.set_color('offline')

                #starting listening
                #self.change_DM_mode(mode)
                self.start_listening()
                
		return

        #=================================================================================#
        #======================Helper Functions===========================================#

        #--------GUI Element Handlers------------
        def get_colors(self,window):		
		self.gc = window.get_style().fg_gc[gtk.STATE_NORMAL]
		self.colormap = self.gc.get_colormap()
		self.white = self.colormap.alloc_color('white')
		self.black = self.colormap.alloc_color('black')
		self.magenta = self.colormap.alloc_color('magenta')
		self.green = self.colormap.alloc_color('green')
		self.gray = self.colormap.alloc_color('gray')
		self.red = self.colormap.alloc_color('red')
		self.lightgray = self.colormap.alloc_color(60000,60000,60000)
		self.pink = self.colormap.alloc_color('pink')
		self.blue = self.colormap.alloc_color('blue')
		self.orange = self.colormap.alloc_color('orange')
		self.yellow = self.colormap.alloc_color('yellow') 

        #### Status Updates on the GUI ####
        

        #Changing the listening State

        def set_color(self, state):

		if state == 'offline':
			self.btnStartStop.modify_bg(gtk.STATE_NORMAL,self.white)
			self.btnStartStop.modify_bg(gtk.STATE_PRELIGHT,self.white)
			self.btnStartStop.modify_bg(gtk.STATE_ACTIVE,self.white)
			self.start_label.set_text("Not Listening")

                elif state == 'sleep':
			self.btnStartStop.modify_bg(gtk.STATE_NORMAL,self.gray)
			self.btnStartStop.modify_bg(gtk.STATE_PRELIGHT,self.gray)
			self.btnStartStop.modify_bg(gtk.STATE_ACTIVE,self.gray)
			self.start_label.set_text("Sleeping")

		elif state == 'listening':

			self.btnStartStop.modify_bg(gtk.STATE_NORMAL,self.green)
			self.btnStartStop.modify_bg(gtk.STATE_PRELIGHT,self.green)
			self.btnStartStop.modify_bg(gtk.STATE_ACTIVE,self.green)
			self.start_label.set_text("Listening")			

		elif state == 'heard':
			
			self.btnStartStop.modify_bg(gtk.STATE_NORMAL,self.orange)
			self.btnStartStop.modify_bg(gtk.STATE_PRELIGHT,self.orange)
			self.btnStartStop.modify_bg(gtk.STATE_ACTIVE,self.orange)
			self.start_label.set_text("Heard")

                elif state == 'processing':
			
			self.btnStartStop.modify_bg(gtk.STATE_NORMAL,self.red)
			self.btnStartStop.modify_bg(gtk.STATE_PRELIGHT,self.red)
			self.btnStartStop.modify_bg(gtk.STATE_ACTIVE,self.red)
			self.start_label.set_text("Processing")

		print "Changed Color " 

        #Start/Stop Button for Listener           
	def start_stop(self, w):
                if self.listening==0:
                        self.start_listening()
		else:
                        self.stop_listening()			

           
	def destroy(self, widget, data=None):
                self.stop_listening()
		print "Exiting"
		gtk.main_quit()


         #------------------ GST Functions --------------------------#
	def make_recorder(self):
		# Define the GStreamer Source Element -- will need to be alter to fit hardware
		print "Making Recorder"

                self.player_made = 0
                
                file_name = self.log_path + "./log_" + self.log_name + "_" + str(self.sink_count) + ".raw"

                        #we will make use of pulssrc
			#self.recorder = gst.parse_launch('alsasrc name=source ! queue ! audioconvert'
                self.recorder = gst.parse_launch('pulsesrc name=source '
                                                 #+ 'device=alsa_input.usb-Logitech_Logitech_Wireless_Headset_H760-00-H760.analog-mono '
                                                 + 'device=' + self.source
                                                 + ' ! queue ! audioconvert'
                                                 + '! audioresample ! ' 
                                                 + 'audio/x-raw-int, rate = 16000, channels=1, width=16, depth=16 ! ' 
                                                 #+ ' SAD name =sad !'
                                                 + 'wavenc ! filesink name=filesink location='
                                                 + file_name)
                
                #bus = self.recorder.get_bus()
		#bus.add_signal_watch()
		#bus.connect("message", self.on_message)

        #Starts and stops listener
        def start_listening(self):
           if self.listening ==0:
              self.listening = 1
              self.make_recorder()	
              self.state = 'active'
              self.start_label.set_text("Listening")				
              self.recorder.set_state(gst.STATE_PLAYING)
              print "Started Listening"
              self.set_color('listening')
              
        def stop_listening(self):
           if self.listening ==1:  # we are currently listening
              
              self.recorder.get_by_name("source").set_state(gst.STATE_READY)
              self.listening =0
              self.sink_count +=1
           else:
              self.recorder.set_state(gst.STATE_NULL)
              self.sink_count +=1
              self.listening =0
           print "Set to ready"
           self.set_color('offline')
           self.state = "inactive"
                 


#====================================================================================================#

if __name__ == "__main__":
   parser = OptionParser()
   parser.add_option("-s", "--src", dest="src",action="store",
                     help="Input src : mic or headset")
   
   parser.add_option("-p", "--path", dest="path",action="store",
                     help="Path to save logs")
   
   parser.add_option("-n", "--filename", dest="name",action="store",
                     help="File name ")

   (options, args) = parser.parse_args()
   
   file_path = ""
   file_name = ""
   src = "headset"
   
   if(options.src != None):
      src = options.src
      
   if(options.path != None):
      file_path = options.path

   if(options.name != None):
      file_name = options.name
       
   GTK_Main(src, log_path=file_path, log_name=file_name)

   gtk.gdk.threads_init()
   gtk.main()

