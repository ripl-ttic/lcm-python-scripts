import subprocess
import os
import time
import signal

if __name__ == '__main__':   
    
    os.chdir("/home/sachih/software/envoy/data/speech/language_models/envoy_new")
    retcode = subprocess.call(["ls", "-l"])
    #retcode = subprocess.call(["asr_server -xmlrpc -port 3000", ""])
    asr_process = subprocess.Popen("asr_server -xmlrpc -port 3000", shell=True,preexec_fn = os.setsid)

    while 1:
        try:
            # Join all threads using a timeout so it doesn't block
            # Filter out threads which have been joined or are None
            #
            time.sleep(10)
            print "."
        except KeyboardInterrupt:
            print "Key break"
            break

    print "Process Killed" 
    asr_process.send_signal(signal.SIGINT)
    #asr_process.terminate()
