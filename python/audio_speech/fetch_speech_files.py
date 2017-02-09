import os
import pickle
from optparse import OptionParser

dialogue_dict = {
    "go_forward":"please go forward", 
    "turn_left":"turn left", 
    "turn_right":"turn right", 
    "go_back":"go back"
}

def get_audio_files(action, phrase):
    #print "wget -O " + action +".wav \'http://people.csail.mit.edu/cyphers/cgi/zed.cgi?synth_string=" + phrase + "&voice=Tom\'"
    voice = '' #'Tom' #can be Samantha , Jill

    os.system("wget -O " + action +".wav \'http://people.csail.mit.edu/cyphers/cgi/zed.cgi?synth_string=" + phrase + "&voice=" + voice + "\'")
    dict_audio = {'filename': action+'.wav' , 'phrase': phrase}
    
    return dict_audio
    #save to pickle file 

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-p", "--path", dest="path",action="store",
                     help="File Path")
    (options, args) = parser.parse_args()
    
    file_path = ""
    
    if(options.path != None):
        file_path = options.path
    os.chdir(file_path)
    key_dict = {}
    
    for action in dialogue_dict.keys():
        dialogue = dialogue_dict[action]
        curr_key = get_audio_files(action, dialogue.replace(" ", "_"))
        key_dict[action] = curr_key

    f = open('filenames.p', 'w')
    pickle.dump(key_dict, f)
    f.close()
