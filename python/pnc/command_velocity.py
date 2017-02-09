#from time import time
import time
import lcm
from erlcm.orc_debug_stat_msg_t import orc_debug_stat_msg_t
from erlcm.velocity_msg_t import velocity_msg_t
from erlcm.goal_feasibility_querry_t import goal_feasibility_querry_t
import threading
from sys import argv

class log_lcm_sender(object):
    def __init__(self, tv, rv):
        self.lc = lcm.LCM()
        self.base_lcm_msg = None

        self.tv = tv
        self.rv = rv
        self._running = True
        
    def lcm_robot_vel_handler(self, channel, data):
        msg = velocity_msg_t.decode(data)
        print "=====Robot Vel Command : " , msg.tv, msg.rv
        

    def send_const_vel(self):
        msg = velocity_msg_t()
        msg.tv = self.tv
        msg.rv = self.rv
        msg.utime = int(time.time() * 1000000)
        self.lc.publish("ROBOT_VELOCITY_CMD", msg.encode())
        #print "."

    def lcm_base_handler(self, channel, data):
        msg = orc_debug_stat_msg_t.decode(data)
        print "Pos Status : " , msg.qei_position
        print "Vel Status : " , msg.qei_velocity
        print "Desired Vel (TV, RV) : " , msg.s_desired_vel[0], msg.s_desired_vel[1]
        print "Actual Vel (TV, RV) : " , msg.s_actual[0], msg.s_actual[1]
        print "Commanded Vel (TV, RV) : " , msg.command_velocity[0], msg.command_velocity[1]

    def run(self):
        print "Started LCM Sender"
        try:
            count = 0
            #while self._running:
            while count < 400:
                self.send_const_vel()
                time.sleep(0.05)
                count +=1
            self.tv = 0
            self.rv = 0
            self.send_const_vel()
        except KeyboardInterrupt:
            pass

if __name__ == '__main__':
    tv = 1.0
    rv = 0.0

    if(len(argv) >= 2):
        tv =  float(argv[1])
        rv = float(argv[2])
    background = log_lcm_sender(tv,rv)
    bg_thread = threading.Thread( target=background.run )
    bg_thread.start()
