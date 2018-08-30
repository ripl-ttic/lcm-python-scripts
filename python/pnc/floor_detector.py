import lcm
from math import *
import pickle
#from ripl.pressure_msg_t import pressure_msg_t
from senlcm.pressure_msg_t import pressure_msg_t
from ripl.speech_cmd_t import speech_cmd_t
from ripl.floor_change_msg_t import floor_change_msg_t
from bot_core.pose_t import pose_t
from ripl.tagged_node_t import tagged_node_t
from ripl.single_floor_pressure_t import single_floor_pressure_t
from ripl.floor_pressure_msg_t import floor_pressure_msg_t
from ripl.map_request_msg_t import map_request_msg_t
from ripl.floor_status_msg_t import floor_status_msg_t
from sys import argv
from time import time
import cPickle
from optparse import OptionParser
import threading
import signal
import sys
pose_list = []


class lcm_listener():#threading.Thread):
    def __init__(self, mode, log_filename, pressure_stat, current_floor=-1):
        #threading.Thread.__init__(self)
        self._running = True
        if(mode == 'learn'):
            self.file_path = log_filename
        else:
            self.file_path = None
        self.lc = lcm.LCM()
        self.subscription_floor_update_handler = self.lc.subscribe("CURRENT_FLOOR_STATUS", self.floor_status_handler)
        self.pressure_sub = self.lc.subscribe("PRESSURE_STAT", self.pressure_handler)
        self.floor_sub = self.lc.subscribe("FLOOR_STATUS", self.floor_handler)
        self.pose_sub = self.lc.subscribe("POSE", self.pose_handler)
        self.mode_sub = self.lc.subscribe("WHEELCHAIR_MODE", self.mode_handler)
        self.readings = []
        self.last_known_floor = -1
        self.last_known_floor_readings = []
        self.last_known_reading_size = 30 #might just keep the average
        self.last_known_floor_stat = {}
        self.last_report_time = 0
        self.last_suggested_time = 0
        self.current_floor = current_floor#3#'3'#'-1'
        print "Current Floor : " , current_floor
        self.at_start = True #flag to request floor status
        self.floor_change_detected = 0
        self.time_since_floor_change_det = 0
        self.floor_stat = {}
        self.final_floor_stat = {}
        self.running_avg = 0
        self.running_sdev = 0 
        self.window_size = 5
        self.last_pose_msg = None
        self.pose_on_floor_change = None 
        self.verbose = False #True
        if(mode == 'learn'):
            self.tourguide_mode = 1
        else:
            self.tourguide_mode = 0
        self.pressure_change_thresh = 10#8#10
        self.short_term_pressure_readings = []
        self.short_term_pressure_size = 3
        self.pressure_change_thresh = 15
        
        self.same_floor_predict_count = 0
        self.unknown_floor_count = 0
        self.deviated_count = 0
        self.last_predict_floor = '-1'

        #self.publish_count = 0

        if(pressure_stat !=None):
            print "Preloaded Pressure Stats"
            self.tourguide_mode = 0
            self.floor_stat = pressure_stat
            self.convert_to_final_stat()

        #In the tourguide mode we should collect the pressure stats and suggest/querry floor information from the user
        #In the navigation mode - we assume that we have visited all the floors in the building - and then swithc floors
        #automatically based on the current floor and the collected pressure difference stats

    def run(self):
        print "Started LCM Listener"
        
        while self._running:
            if self.at_start:
                self.request_current_floor()
                self.at_start = False
            try:
                self.lc.handle()
            except KeyboardInterrupt:
                print "\n============== Interrupt =================\n" 
                self._running = False
                pass

    def request_current_floor(self):
        msg = map_request_msg_t()
        msg.utime = time() * 1e6
        msg.requesting_prog = "FLOOR_PREDICTOR"
        self.lc.publish("FLOOR_STATUS_REQUEST", msg.encode())
        
    def prob_normal(self,x, mean, sdev):        
        prob = 1/sqrt((2*pi*pow(sdev,2)))*exp(-pow(x-mean,2)/(2*pow(sdev,2)))
        return prob


    def floor_handler(self,channel, data):
        print "Floor Message"
        msg = floor_change_msg_t.decode(data)
        print msg.utime, " : " , msg.floor_no
        self.current_floor = msg.floor_no        
        self.floor_change_detected = 0
        self.unknown_floor_count = 0
        self.deviated_count = 0

    def floor_status_handler(self,channel, data):
        print "Floor Handler Called\n"
        msg = floor_status_msg_t.decode(data)
        print msg.utime, " : " , msg.floor_no
        self.current_floor = msg.floor_no        
        self.floor_change_detected = 0
        self.unknown_floor_count = 0
        self.deviated_count = 0
        self.lc.unsubscribe(self.subscription_floor_update_handler)
        

    def convert_to_final_stat(self):
        for i in self.floor_stat.keys():
            temp_fl_stat = self.floor_stat.get(i)
            f_count = temp_fl_stat['count']
            f_avg  = temp_fl_stat['mean']
            f_std = temp_fl_stat['sdev']
            
            floor_info = {}
            for j in self.floor_stat.keys():
                if(i==j):
                    continue
                new_fl_stat = self.floor_stat.get(j)
                nf_count = new_fl_stat['count']
                nf_avg  = new_fl_stat['mean']
                nf_std = new_fl_stat['sdev']
                floor_info[j] = {'m_dif':nf_avg - f_avg, 'sdev':nf_std,'count':nf_count}
                self.final_floor_stat[i] = {'sdev': f_std, 'count':f_count, 'rel_floor': floor_info}

    def publish_stat_and_save(self):
        print self.floor_stat.keys()
        
        print " +++++++ Publishing " 
        msg = floor_pressure_msg_t()#single_floor_pressure_t()
        msg.no_floors = 0
        pressure = []
        for i in self.floor_stat.keys():
            temp_fl_stat = self.floor_stat.get(i)
            f_count = temp_fl_stat['count']
            f_avg  = temp_fl_stat['mean']
            f_std = temp_fl_stat['sdev']

            t_p = single_floor_pressure_t()
            t_p.floor_no = i
            t_p.count = f_count
            t_p.mean = f_avg
            t_p.sdev = f_std
            pressure.append(t_p)
            msg.no_floors +=1

            floor_info = {}
            for j in self.floor_stat.keys():
                if(i==j):
                    continue
                new_fl_stat = self.floor_stat.get(j)
                nf_count = new_fl_stat['count']
                nf_avg  = new_fl_stat['mean']
                nf_std = new_fl_stat['sdev']
                floor_info[j] = {'m_dif':nf_avg - f_avg, 'sdev':nf_std,'count':nf_count}
            self.final_floor_stat[i] = {'sdev': f_std, 'count':f_count, 'rel_floor': floor_info}
            
        print "No of Floors : " , msg.no_floors
        print pressure
        msg.pressure = pressure
        self.lc.publish("FINAL_FLOOR_STAT", msg.encode())

        #self.publish_count +=1

        #if(self.publish_count == 5):           
        #    self.publish_count = 0
        try:
            pressure_log = open(self.file_path,'w')
            cPickle.dump(self.floor_stat, pressure_log)
            pressure_log.close()
            print "Saved File"

        except IOError, e:
            print "Unable to save to file "
            

    def mode_handler(self,channel, data):
        print "msg received"
        msg = tagged_node_t.decode(data)
        print "MODE handler ", msg
        if(msg.type == 'mode'):
            if(msg.label == 'tourguide'):
                print "We were in navigation Mode - does not support changing back"
                #self.tourguide_mode = 1
                #print "=========== In tour guide mode  =============="

            elif(msg.label == 'navigation'):
                if(self.tourguide_mode):
                    print "We were in a tour - Converting the collected stats for Navigation"
                    msg = floor_pressure_msg_t()#single_floor_pressure_t()
                    msg.no_floors = 0
                    pressure = []
                    for i in self.floor_stat.keys():
                        temp_fl_stat = self.floor_stat.get(i)
                        f_count = temp_fl_stat['count']
                        f_avg  = temp_fl_stat['mean']
                        f_std = temp_fl_stat['sdev']

                        t_p = single_floor_pressure_t()
                        t_p.floor_no = i
                        t_p.count = f_count
                        t_p.mean = f_avg
                        t_p.sdev = f_std
                        pressure.append(t_p)
                        msg.no_floors +=1
                        
                        floor_info = {}
                        for j in self.floor_stat.keys():
                            if(i==j):
                                continue
                            new_fl_stat = self.floor_stat.get(j)
                            nf_count = new_fl_stat['count']
                            nf_avg  = new_fl_stat['mean']
                            nf_std = new_fl_stat['sdev']
                            floor_info[j] = {'m_dif':nf_avg - f_avg, 'sdev':nf_std,'count':nf_count}
                        self.final_floor_stat[i] = {'sdev': f_std, 'count':f_count, 'rel_floor': floor_info}

                    msg.pressure = pressure
                    self.lc.publish("FINAL_FLOOR_STAT", msg.encode())

                    try:
			pressure_log = open(self.file_path,'w')
			cPickle.dump(self.floor_stat, pressure_log)
			pressure_log.close()
			print "Saved File"
			
                    except IOError, e:
                        print "Unable to save to file "

                    for k in  self.final_floor_stat.keys():
                        fl_stat = self.final_floor_stat.get(k)
                        print fl_stat
                            
                self.tourguide_mode = 0
                print "=========== In navigation mode  =============="
        
    def pose_handler(self,channel, data):
       msg = pose_t.decode(data)
       #we are ignoring the pose for the moment - not sure if we would ever need to keep that
       self.last_pose_msg = {'x':msg.pos[0], 'y': msg.pos[1]}
        
    
    def pressure_handler(self,channel, data):
        msg = pressure_msg_t.decode(data)
        print msg.utime, " : " , msg.pressure

        p_change = 0

        if(len(self.readings)):
            last_reading = self.readings[len(self.readings)-1]
            #print last_reading
            p_change = abs(last_reading['pressure'] - float(msg.pressure))
            print "Pressure Change : ", p_change 

        if(self.tourguide_mode ==1):
            print "TG Mode " 
            print "Current Floor " , self.current_floor
        #if we have a current floor 
            if(self.current_floor !=-1):
                curr_floor_stat = self.floor_stat.get(self.current_floor)
                if(curr_floor_stat == None):
                    print "Adding First Stat"
                    curr_floor_stat = {'count':1,'sum':float(msg.pressure), 's_sum':pow(float(msg.pressure),2), 'mean':float(msg.pressure), 'sdev':0.0}
                    self.floor_stat[self.current_floor] = curr_floor_stat
                    print self.floor_stat
                else:
                    
                    #check if this is an abnormal reading 
                    #actually this should check which floor has the highest prob of causing this observation                
                    #prob = self.prob_normal(msg.pressure,curr_floor_stat['mean'], curr_floor_stat['sdev'])

                    z_score = 1000
                    #(curr_floor_stat['count'] > 1) and 
                    if (curr_floor_stat['count'] < 100):
                        z_score = (msg.pressure - curr_floor_stat['mean'])/ 6.0  #otherwise sdev seems too small  
                        print "Z_score :", z_score
                    else:
                        z_score = (msg.pressure - curr_floor_stat['mean'])/ curr_floor_stat['sdev']
                        print "Z_score :", z_score

                    #if(diff < 20.0):
                    #if(curr_floor_stat['count'] < 10) or 
                    #if we are within the current floor and there is no uncleared floor change 
                    if((abs(z_score) < 3) or p_change < self.pressure_change_thresh) and (self.floor_change_detected==0): 
                        print "====== On the same floor - Adding Stat"
                        curr_floor_stat['count'] += 1
                        curr_floor_stat['sum'] += float(msg.pressure)
                        curr_floor_stat['s_sum'] += pow(float(msg.pressure),2)
                        curr_floor_stat['mean'] = curr_floor_stat['sum'] / curr_floor_stat['count']
                        curr_floor_stat['sdev'] = sqrt(curr_floor_stat['s_sum'] / curr_floor_stat['count'] - pow(curr_floor_stat['mean'],2))
                    elif (abs(z_score) < 3 and self.floor_change_detected==1):
                        self.deviated_count = 0
                        self.floor_change_detected = 0
                        print "Abberent Reading - Ignoring"
                    else:
                        self.deviated_count +=1
                        print "====== Floor Change Seems to have occured" 
                        self.time_since_floor_change_det = float(msg.utime) / 1e6
                        take_action = 0 #set this flag to take action - action is either asking for the floor or suggesting floor

                        #add floor change flag 
                        if(self.floor_change_detected ==0):
                            self.floor_change_detected = 1
                            #should send floor change evento for the SLAM module 
                        if(self.deviated_count == 5):
                            print "Sending Floor Change Event - to ISAM" 
                            floor_msg = floor_change_msg_t()
                            floor_msg.utime = int(msg.utime)
                            floor_msg.floor_no = -100
                            self.lc.publish("FLOOR_CHANGE",floor_msg.encode())

                            self.pose_on_floor_change = self.last_pose_msg
                        elif(self.deviated_count >=5): 
                            if(self.last_pose_msg !=None and self.pose_on_floor_change !=None): #we have valid poses for when the floor change occure and now
                                dist_moved = sqrt(pow(self.pose_on_floor_change['x'] - self.last_pose_msg['x'],2) + \
                                                      pow(self.pose_on_floor_change['y'] - self.last_pose_msg['y'],2))
                                print "Distance traveled from the detection of the floor change : ", dist_moved 
                                if(dist_moved >= 0.5):
                                        take_action = 1

                        #do this checks when the readings have stabilized                    
                        #if(p_change < 10): #ignoring the pressure change -assume stability since we are moving out of the elevator
                        if(take_action==1):
                            if(len(self.floor_stat)==1):
                                print "We have not visited more than one floor - Asking for floor"
                                time_since_last = float(msg.utime)/1e6 -self.last_report_time
                                print "Time since last" , time_since_last
                                if(time_since_last > 30.0):
                                    print "++++++++++++ Sent speech querry : Which Floor "
                                    self.last_report_time = float(msg.utime)/1e6
                                    speech_msg = speech_cmd_t()
                                    speech_msg.utime = int(time() * 1000000)
                                    speech_msg.cmd_type = "FLOOR_CHANGE"
                                    speech_msg.cmd_property = "CHANGE"
                                    self.lc.publish("PERSON_TRACKER", speech_msg.encode())

                            else: 
                                #there is more than one floor - checking to see if we have a match 
                                predicted_floor = '-1'
                                min_pressure_dif = 20
                                #search through the known floors
                                for i in self.floor_stat.keys():
                                    if (self.current_floor == i): #same floor
                                        continue
                                    temp_fl_stat = self.floor_stat.get(i)
                                    f_count = temp_fl_stat['count']
                                    f_avg  = temp_fl_stat['mean']
                                    f_std = temp_fl_stat['sdev']
                                    pressure_thresh = 18.0

                                    #if(f_count >= 100):
                                    #    pressure_thresh = f_std * 3

                                    temp_presure_diff = fabs(msg.pressure - f_avg)
                                    print "Checked floor : " , i , " Difference :" , temp_presure_diff

                                    if(temp_presure_diff < pressure_thresh):
                                        #possibly within this floor 
                                        min_pressure_dif = temp_presure_diff
                                        predicted_floor = i

                                if(min_pressure_dif < 20.0): #not sure which value to use 
                                    print "Predicted Floor :" , predicted_floor
                                    #send a floor suggestion 
                                    print "Time since last suggestion :" , (float(msg.utime)/1e6 - self.last_suggested_time > 30.0)
                                    self.unknown_floor_count = 0 #reset the unknown floor counts
                                    if(float(msg.utime)/1e6 - self.last_suggested_time > 30.0):
                                        print "++++++++++++ Sent speech querry : Floor Suggestion"
                                        speech_msg = speech_cmd_t()
                                        speech_msg.utime = int(time() * 1000000)
                                        speech_msg.cmd_type = "FLOOR_REVISIT"
                                        speech_msg.cmd_property = str(predicted_floor)
                                        self.lc.publish("PERSON_TRACKER", speech_msg.encode())
                                        self.last_suggested_time = float(msg.utime)/1e6

                                else: #we are exiting the elevator and we do not have a matching floor - most likely unvisited floor 
                                    print "Could not find a matching floor"
                                    time_since_last = float(msg.utime)/1e6 -self.last_report_time
                                    print "Time since last" , time_since_last
                                    self.unknown_floor_count +=1
                                    if(time_since_last > 30.0 and self.unknown_floor_count > 4):
                                        self.unknown_floor_count = 0
                                        print "++++++++++++ Sent speech querry : Which Floor "
                                        self.last_report_time = float(msg.utime)/1e6
                                        speech_msg = speech_cmd_t()
                                        speech_msg.utime = int(time() * 1000000)
                                        speech_msg.cmd_type = "FLOOR_CHANGE"
                                        speech_msg.cmd_property = "CHANGE"
                                        self.lc.publish("PERSON_TRACKER", speech_msg.encode())


                        else:
                            print "We have not moved out of the elevator" 


            self.publish_stat_and_save()
        

        elif(len(self.last_known_floor_readings) > 10):

            print "In Prediction Mode " 
            
            short_change = 0

            print self.short_term_pressure_readings

            if(len(self.short_term_pressure_readings)>0):                
                short_change = abs(self.short_term_pressure_readings[0] - float(msg.pressure))
                
            print "Short Change : " , short_change

            print "Current Floor : " , self.current_floor
            #use the last_known floor pressure stats and the gap between the visited floor pressure to predict the floor 
            print "No of readings on the current Floor :" , len(self.last_known_floor_readings) 
            
            z_score = 1000            

            if(len(self.last_known_floor_readings) < self.last_known_reading_size):
                z_score = (msg.pressure - self.last_known_floor_stat['mean'])/ 8.0
            else:
                z_score = (msg.pressure - self.last_known_floor_stat['mean'])/ 6.0 
                #\ self.last_known_floor_stat['sdev']
            print "Navigation : Z-score : ", z_score
    
            #if((abs(z_score) > 3) and p_change > self.pressure_change_thresh):
            #instead of checking if this is a significant dev from the current floor 
            #check if there is another floor that is closer than this one 
            #if(p_change > self.pressure_change_thresh): 
            if(((abs(z_score) > 3) and p_change > self.pressure_change_thresh) or short_change > self.pressure_change_thresh) :
                if(short_change > self.pressure_change_thresh):
                    print "Short Change Exceeded Limit : " , short_change , self.pressure_change_thresh
                self.floor_change_detected = 1 
                self.last_predict_floor = -1
                self.same_floor_predict_count = 0

            if(self.floor_change_detected==1):
                print "Uncleared Floor Change" 
                print "Current FLoor : " , self.current_floor
                if(p_change >self.pressure_change_thresh):
                    print "Readings not settled" 
                elif(self.current_floor !='-1'):
                    print "Readings have settled - Looking for matching floor"
                    predicted_floor = '-1'
                   
                    mean_pressure_on_pred_floor = 0
                    min_pressure_dif = 20

                    print "Checking on the current floor " 
                    if(abs(z_score) <3) and (fabs(min_pressure_dif > msg.pressure - self.last_known_floor_stat['mean'])):
                        predicted_floor = self.current_floor
                        min_pressure_dif = msg.pressure - self.last_known_floor_stat['mean']
                        print "Difference from the current floor : " , msg.pressure - self.last_known_floor_stat['mean']
                        
                    print "Checking on other floors"

                    fl_stat = self.final_floor_stat.get(self.current_floor)
                    print fl_stat['rel_floor']

                    for l in fl_stat['rel_floor'].keys(): #cycle through 
                        rel_fl_stat = fl_stat['rel_floor'].get(l)
                        print "Rel floor Stat : " , rel_fl_stat
                        print "Last Floor mean : ",  self.last_known_floor_stat['mean']
                        mean = rel_fl_stat['m_dif'] + self.last_known_floor_stat['mean']
                        s_dev = rel_fl_stat['sdev']

                        f_count = rel_fl_stat['count']

                        pressure_thresh = 18.0

                        #if(f_count >= 100):
                        #    pressure_thresh = s_dev * 3

                        temp_presure_diff = fabs(msg.pressure - mean)
                        print "Checked floor : " , l , " Difference :" , temp_presure_diff

                        if(temp_presure_diff < pressure_thresh):
                            #possibly within this floor 
                            print "Found possible prediction : " , l
                            min_pressure_dif = temp_presure_diff
                            predicted_floor = l
                            mean_pressure_on_pred_floor = mean

                    if(min_pressure_dif < 20.0):
                        print "Floor Prediction " , predicted_floor
                        print "Mean pressure on predicted floor" , mean_pressure_on_pred_floor

                        if(self.last_predict_floor == predicted_floor):
                            self.same_floor_predict_count += 1
                            print "Same as the last prediction" 
                        else:
                            self.last_predict_floor = predicted_floor
                            print "Different Prediction"
                        #should wait for 4 predictions to make a decisio n

                        #this might still be an issue if we stop at a floor - we would get only a small no of readings on the new floor before we switch over 
                        #so might need to keep a last_stable floor readings as well 
                        if(self.same_floor_predict_count > 4): 
                            print "*****Updating the floor : Old floor : ", self.current_floor, \
                                " => New Floor " , predicted_floor
                            self.current_floor = predicted_floor
                            #should send an lcm floor change message as well 
                            self.floor_change_detected = 0 #reseting the floor change detection 

                            floor_msg = floor_change_msg_t()
                            floor_msg.utime = int(time() * 1000000)
                            floor_msg.floor_no = self.current_floor
                            self.lc.publish("FLOOR_CHANGE",floor_msg.encode())
                            
                            
                            
                            #sending speech message
                            speech_msg = speech_cmd_t()
                            speech_msg.utime = int(time() * 1000000)
                            speech_msg.cmd_type = "FLOOR_AUTO_CHANGE"
                            speech_msg.cmd_property = str(predicted_floor)
                            self.lc.publish("PERSON_TRACKER", speech_msg.encode())
                            self.last_suggested_time = float(msg.utime)/1e6

                    else: 
                        print "No valid Floor candidate found"

                else:
                    print "Did not know the current Floor - so can not predict"

        #add the short term buffer 

        self.short_term_pressure_readings.append(msg.pressure) #{'time':msg.utime, "pressure":msg.pressure})
        if(len(self.short_term_pressure_readings) > self.short_term_pressure_size):
                self.short_term_pressure_readings.pop(0)

        if(self.current_floor != -1 and self.floor_change_detected ==0): #we are on a known floor with no elevator change detected
            if(self.last_known_floor != self.current_floor): # a floor change had occured - our old data is invalid 
                self.last_known_floor_readings = []
                print "On a new known floor : Flushing old data"
                self.last_known_floor = self.current_floor
                self.short_term_pressure_readings = []
            else:
                print "On the same floor as before => Floor " , self.current_floor

            self.last_known_floor_readings.append({'time':msg.utime, "pressure":msg.pressure})
            
            
            if(len(self.last_known_floor_readings) > self.last_known_reading_size):
                self.last_known_floor_readings.pop(0)

            

            lf_count = 0
            lf_n_sum = 0
            lf_s_sum = 0
            for i in self.last_known_floor_readings:
                lf_count = lf_count + 1
                lf_n_sum = lf_n_sum + float(i['pressure'])
                lf_s_sum = lf_s_sum + pow(float(i['pressure']),2)

            if(lf_count >0):
                self.last_known_floor_stat['mean'] = lf_n_sum/lf_count
                self.last_known_floor_stat['sdev'] = sqrt(lf_s_sum/lf_count - pow(self.last_known_floor_stat['mean'],2))

            #print "Last Known Floor Reading " , self.last_known_floor_readings
            print "========Last Known Floor Stats========" 
            print "\t\t Mean : " , self.last_known_floor_stat['mean']
            print "\t\t SDev : " , self.last_known_floor_stat['sdev']

        #keeps the last X readings in mempry   
        self.readings.append({'time':msg.utime, "pressure":msg.pressure})
        if(len(self.readings) > self.window_size):
            self.readings.pop(0)

        #calculate the statistics 
        count = 0
        n_sum = 0
        s_sum = 0
        for i in self.readings:
            count = count + 1
            n_sum = n_sum + float(i['pressure'])
            s_sum = s_sum + pow(float(i['pressure']),2)

        if(count > 0):
            self.running_avg = n_sum / count 
            self.running_sdev = sqrt(s_sum/count - pow((n_sum / count),2))
            print "----- Current Reading    -----"
            print "\t\t Current Pressure " , float(i['pressure'])
            print "----- History Statistics -----"
            print "\t\t Mean : " , self.running_avg
            print "\t\t SDev : " , self.running_sdev

        ####Printing statistics 
        if(self.verbose):
            print "----- Floor Statistics   -----"
            for i in self.floor_stat.keys():
                curr_fl_stat = self.floor_stat.get(i)
                print "\t\t [", i , "] => Count : " , curr_fl_stat['count'] , " Mean : ", curr_fl_stat['mean'] , " Std Dev :", curr_fl_stat['sdev']

if __name__ == "__main__":

    parser = OptionParser()
    parser.add_option("-m", "--mode", dest="mode",action="store",
                      help="Mode of Operation - learn or predict")

    parser.add_option("-f", "--filename", dest="filename",action="store",
                      help="Filename")

    parser.add_option("-c", "--current_floor", dest="current_floor",action="store",
                      help="Current Floor")

    (options, args) = parser.parse_args()

    print "Options : " , options 

    file_path = 'test.log'
    current_floor = -1;

    if(options.filename != None):
        file_path = options.filename

    if(options.mode != None):
        mode = options.mode
        
    if(options.current_floor != None):
        current_floor = int(options.current_floor)

    pressure_stat = None

    if(mode == 'predict'):
        print " Prediction Mode " 
        pressure_log = open(file_path,'r')
        pressure_stat = cPickle.load(pressure_log)
        pressure_log.close()
        print pressure_stat
        
    #pressure_handler = lcm_listener("",pressure_stat)
    #print "Floor Detector - Initialized"
    #signal.signal(signal.SIGINT, signal_handler)
    
    background = lcm_listener(mode, file_path ,pressure_stat, current_floor)
    bg_thread = threading.Thread( target=background.run )
    bg_thread.start()
    '''background.start()

    threads = [background] 
    
    while len(threads) > 0:
        try:
            # Join all threads using a timeout so it doesn't block
            # Filter out threads which have been joined or are None
            print "---"
            threads = [t.join(1) for t in threads if t is not None and t.isAlive()]
        except KeyboardInterrupt:
            print "Ctrl-c received! Sending kill to threads..."
            for t in threads:
                t._running = False'''
   
