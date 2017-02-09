##    * functions
##          o output_as_speech( text )
import threading
import festival
import gst, gobject
import get_synth_file
import time
from optparse import OptionParser
import pygtk
import gtk
import lcm
import functools
from bot_core.pose_t import pose_t
from exlcm.example_t import example_t

class lcm_listener(threading.Thread):
    def __init__(self,callback):
        threading.Thread.__init__(self)
        self.callback = callback
        self.lc = lcm.LCM()
        self.subscription_pose = self.lc.subscribe("POSE", self.pose_handler)
        self.subscription_example = self.lc.subscribe("EXAMPLE", self.example_handler)
        self._running = True        

    def pose_handler(self, channel, data):
        msg = pose_t.decode(data)
        #gobject.idle_add(self.callback, "turn_right")
        t = threading.Thread( target=functools.partial(self.callback , "turn_right"))
        t.start()

    def example_handler(self, channel, data):
        print "Received"
        msg = example_t.decode(data)
        #gobject.idle_add(self.callback, "turn_right")
        t = threading.Thread( target=functools.partial(self.callback , "turn_right"))
        t.start()

    def run(self):
        print "Started LCM Listener"
        try:
            while self._running:
                self.lc.handle()
        except KeyboardInterrupt:
            pass

class speech_synthesizer:
    def __init__( self , location = None, prefetch = True):
        self.synthesizer = festival.Festival()
        self.use_prefetch = prefetch
        self.gst_pipeline = None
        ##This should be used to initialize the get speech file 
        self.file_location = location 
        if(self.use_prefetch):
            self.get_speech_filename = get_synth_file.get_synth_file(location)

        self.ss_active = threading.Condition()
        self.speaking = False

    def output_as_speech( self, pharse ):
        if(self.use_prefetch):
            file_src = self.get_speech_filename.action_code_to_filename(pharse)
        
            print "File Path : " , file_src
            
            while(self.speaking): 
                print "Sleeping " 
                time.sleep(0.5)

            if(file_src != None):
                
                print file_src
                
                gst_parse_str = "filesrc location= " + file_src + " ! wavparse ! alsasink"
                    
                print "Path string : " , gst_parse_str
                
                print "Lock state : " , self.ss_active

                #stop if there is an ealier player 
                if(self.gst_pipeline != None): 
                        #This should be stopping the repeating phrases - not sure why its not stopping
                    print "(((((((Stopping Pipeline)))))))" 
                    self.gst_pipeline.set_state( gst.STATE_NULL)
                    print "Stopped State : " , self.gst_pipeline.get_state()
                self.gst_pipeline = gst.parse_launch(gst_parse_str)

                self.pipeline_bus = self.gst_pipeline.get_bus()
                
                self.speaking = True

                self.gst_pipeline.set_state( gst.STATE_PLAYING )
                
                # start the pipeline
                self.pipeline_bus.add_signal_watch()
                self.pipeline_bus.connect( "message", self.process_message )
                
                print "New Pipeline State : ",  self.gst_pipeline.get_state()

            else:
                print "Sending to Synthesizer" 

                ### This doesnt seem to play nice with the gst-player 
                if(self.gst_pipeline != None): 
                    print "Stopping Pipeline" 
                    self.gst_pipeline.set_state( gst.STATE_NULL)
                self.synthesizer.say(pharse)      
                    
        else:
            self.ss_active.acquire()
            self.synthesizer.say( pharse )
            self.ss_active.notifyAll()
            self.ss_active.release()
                
        print "++++++++++++++++++++++++++++++"
        print pharse

    def process_message( self, bus, message ):
        if(message.type == gst.MESSAGE_EOS):
            print "+++++++++++ Done speaking" 
            self.speaking = False
          
    def interrupt_synthesizer( self ):
        self.synthesizer.close()


if __name__ == "__main__":    
    parser = OptionParser()
    parser.add_option("-p", "--path", dest="path",action="store",
                     help="File Path")
    
    (options, args) = parser.parse_args()
    
    file_path = ""
    
    if(options.path != None):
        file_path = options.path
        x = speech_synthesizer(location=file_path)
    else:
        x = speech_synthesizer(prefetch=False)
    x.output_as_speech("turn_right")
    ##This needs the gtk thread 
    background = lcm_listener(x.output_as_speech)
    background.start()

    #Add simple gui here if you want 

    gtk.gdk.threads_init()
    gtk.main()

    

    
   
