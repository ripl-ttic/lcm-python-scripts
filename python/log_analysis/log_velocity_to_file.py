from time import time
import lcm
from ripl.orc_debug_stat_msg_t import orc_debug_stat_msg_t
from ripl.velocity_msg_t import velocity_msg_t
import threading
from sys import argv

class log_lcm_listener(object):
    def __init__(self, log_name):
        self.lc = lcm.LCM()
        self.base_lcm_msg = None
        self.subscription_base_stat = self.lc.subscribe("BASE_DEBUG_STAT", self.lcm_base_handler)
        self.subscription_robot_vel_cmd = self.lc.subscribe("ROBOT_VELOCITY_CMD", self.lcm_robot_vel_handler)
        self._running = True
        self.file_name = log_name#"vel.log"
        
    def lcm_robot_vel_handler(self, channel, data):
        msg = velocity_msg_t.decode(data)
        print "=====Robot Vel Command : " , msg.tv, msg.rv
        
        
    def lcm_base_handler(self, channel, data):
        msg = orc_debug_stat_msg_t.decode(data)
        print "Pos Status : " , msg.qei_position
        print "Vel Status : " , msg.qei_velocity
        print "Desired Vel (TV, RV) : " , msg.s_desired_vel[0], msg.s_desired_vel[1]
        print "PWM (TV, RV) : " , msg.pwm_value[0], msg.pwm_value[1]

        print "Actual Vel (TV, RV) : " , msg.s_actual[0], msg.s_actual[1]
        print "Commanded Vel (TV, RV) : " , msg.command_velocity[0], msg.command_velocity[1] 
        f = open(self.file_name,'a')
        vel_string = str(float(msg.utime)/1e6)+ "," + str(msg.s_actual[0]) + "," + str(msg.s_actual[1]) + "," + \
            str(msg.s_desired_vel[0]) + "," + str(msg.s_desired_vel[1])+ "\n"
        f.write(vel_string)
        f.close()

    
        

    def run(self):
        print "Started LCM Listener"
        try:
            while self._running:
                self.lc.handle()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    log_name = argv[1]
    background = log_lcm_listener(log_name)
    bg_thread = threading.Thread( target=background.run )
    bg_thread.start()
