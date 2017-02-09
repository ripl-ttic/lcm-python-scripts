# todo:
#in wheelchargtk, init this module


import pickle
import os

class get_synth_file:
    def __init__(self, path=None):
   	 # initialize the pickle with all of the audio files already in existence
        #os.chdir('../../wheelchair_speech_synthesizer/src/responses')
        if(path ==None):
            self.pre_path = '../../wheelchair_speech_synthesizer/src/responses/'
        else:
            self.pre_path = path
        
        self.filenames = {}
    
        #for entry in action_list:
    	#    filenames[entry]  =  self.pre_path + entry + ".wav"
        try:
            print "Loading File"
            self.filenames = pickle.load(open(self.pre_path + "/filenames.p"))
        except EOFError:
            print "No file Found"
        #pickle.dump( filenames, open( self.pre_path + "filenames.p", "wb" ) )

    def action_code_to_filename (self, action):
        

        # name the file for the download to be saved to
        filename = action #+ ".wav"

        # if the file name already exists in the cache, 
        # just return the corresponding filename
        if (self.filenames.has_key(action)):
            return self.pre_path + self.filenames[action]['filename']
        else:
            return None

    def dialogue_to_filename (self, dialogue, timeout):
    
        dialogue = dialogue.replace(' ', '_')
        
        result = os.system("wget -O " + self.pre_path + dialogue  + ".wav --timeout=" + str(timeout) + " http://people.csail.mit.edu/cyphers/cgi/zed.cgi?synth_string=" + dialogue + "&voice=Tom")

        print "Result : " , result 
    
        # if sucessful, add the entry to the pickle and return it
        if result == 0:
        #filenames[dialogue] = filename
        #pickle.dump( filenames, open( "filenames.p", "wb" ) )
            return self.pre_path + dialogue + '.wav'

        # otherwise, return an error, unsucessful querry
        else:
            print "Error" 
	    return None

if __name__ == "__main__":
   x = wheelchair_speech_synthesizer_new()
   print x.action_code_to_filename("stop", 2)
   print x.dialogue_to_filename("this is a piece of dialogue", 2)

   
