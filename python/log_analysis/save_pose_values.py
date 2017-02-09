from sys import argv
from time import time
import lcm
from erlcm.pose_value_t import pose_value_t
import threading

class save_pose_values(object):
    def __init__(self, log_name):
        self.lc = lcm.LCM()
        self.base_lcm_msg = None
        self.subscription_pose_value = self.lc.subscribe("POSE_VALUE", self.lcm_pose_value_handler)
        self._running = True
        self.file_name = log_name
        
            
    def lcm_pose_value_handler(self, channel, data):
        msg = pose_value_t.decode(data)
        print "Pos Status : " , msg.x , msg.y, msg.theta, msg.score 
        f = open(self.file_name,'a')
        val_string = str(msg.x) + "," + str(msg.y) + "," + str(msg.theta) + "," + str(msg.score) + "\n"
        f.write(val_string)
        f.close()

    def run(self):
        print "Started LCM Listener"
        try:
            while self._running:
                self.lc.handle()
        except KeyboardInterrupt:
            pass

if __name__ == '__main__':
    print len(argv)
    
    if(len(argv) < 2):
        print "Log path not given" 
        exit(0)

    log_name = argv[1]

    background = save_pose_values(log_name)
    bg_thread = threading.Thread( target=background.run )
    bg_thread.start()
