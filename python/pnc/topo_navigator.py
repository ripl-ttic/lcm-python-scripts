from time import time
import lcm
from erlcm.place_node_t import place_node_t
from erlcm.portal_node_t import portal_node_t
from erlcm.point_t import point_t
from erlcm.goal_feasibility_querry_t import goal_feasibility_querry_t
from erlcm.map_request_msg_t import map_request_msg_t
from erlcm.floor_status_msg_t import floor_status_msg_t
from erlcm.floor_change_msg_t import floor_change_msg_t
from erlcm.portal_list_t import portal_list_t
from erlcm.speech_cmd_t import speech_cmd_t
from erlcm.navigator_goal_msg_t import navigator_goal_msg_t
from erlcm.goal_list_t import goal_list_t
from erlcm.goal_t import goal_t
from erlcm.topology_t import topology_t
from erlcm.place_list_t import place_list_t
from erlcm.place_node_t import place_node_t
import threading
import cPickle
import pickle
from sys import argv
from optparse import OptionParser
import math 

class node_listener(object):
    def __init__(self, mode , file_path, door_mode):
        self.lc = lcm.LCM()
        print "Door Mode : ", door_mode
        self.door_mode = door_mode
        self.base_lcm_msg = None
        self.subscription_node_handler = self.lc.subscribe("PLACE_NODE", self.node_handler)
        self.subscription_portal_handler = self.lc.subscribe("PORTAL_NODE", self.portal_handler)
        self.subscription_floor_update_handler = self.lc.subscribe("CURRENT_FLOOR_STATUS", self.floor_status_handler)
        
        self.subscription_floor_change_handler = self.lc.subscribe("FLOOR_CHANGE", self.floor_change_handler)

        self.subscription_goal_result_handler = self.lc.subscribe("GOAL_FEASIBILITY_RESULT", self.goal_result_handler)

        self.subscription_goal_handler = self.lc.subscribe("GOAL_NODE", self.goal_handler)

        self.subscription_goal_name_handler = self.lc.subscribe("GOAL_NODE_NAME", self.goal_name_handler)

        self.subscription_goal_confirm_handler = self.lc.subscribe("GOAL_NODE_CONFIRM", self.goal_confirm_handler)

        self.subscription_nav_status = self.lc.subscribe("WAYPOINT_STATUS", self.waypoint_status_handler)

        self.subscription_door_status_handler = self.lc.subscribe("DOOR_STATUS", self.door_status_handler)

        self.subscription_elevator_status_handler = self.lc.subscribe("ELEVATOR_STATUS", self.elevator_status_handler)

        self.subscription_topology_handler = self.lc.subscribe("MAP_SERVER_TOPOLOGY", self.topology_update_handler)

        self.hack = 1

        self.nodes = []
        self.portals = []
        self.mode = mode
        self.file_path = file_path 
        if(self.mode == 'load'):
            print "Waiting for update message " 
            #if mode load - then load pickledata from file 
            #self.update_from_file()
        self._running = True
        self.current_floor_ind = -1
        self.current_floor_no = -1
        self.request_current_floor()
        self.confirmed_path = {'goal': None, 'path' : None}
        self.last_querry_goal = None

        self.current_path = None
        self.current_waypoint = None

        #self.find_path_to_goal()

    def convert_node_list_to_msg(self):
        p_list_msg = place_list_t()
        p_list = []

        count = 0

        for i in self.nodes: 
            print "Place : " , count , " : " , i
            msg = place_node_t()
            msg.name = i['name']
            msg.type = i['type']
            msg.x = i['xy'][0]
            msg.y = i['xy'][1]
            msg.theta = i['theta']
            msg.std = i['std']
            msg.floor_ind = i['floor_ind']
            msg.floor_no = i['floor_no']
            msg.node_id = count
            msg.create_utime = 0
            count += 1
            p_list.append(msg)

        p_list_msg.place_count = len(p_list)
        p_list_msg.trajectory = p_list

        return p_list_msg

        '''place = {'name':msg.name, 'type': msg.type, 
                 'xy': [msg.x, msg.y] , 'theta': msg.theta, 'std': msg.std, 
                 'floor_ind': msg.floor_ind, 'floor_no':msg.floor_no}'''

    def convert_topology_to_msg(self):
        msg = topology_t()
        msg.utime = int(time() * 1e6)
        msg.portal_list = self.convert_portal_dict_to_msg(msg.utime)
        msg.place_list = self.convert_node_list_to_msg()
        
        return msg
        

    def convert_msg_to_topology(self, msg):
        
        self.convert_node_msg_to_list(msg.place_list)
        self.convert_portal_list_msg_to_list(msg.portal_list)
        print "Converted" 
        
    def publish_topology(self):
        t_msg = self.convert_topology_to_msg()
        print "\n === Publishing topology\n"
        self.lc.publish("TOPOLOGY", t_msg.encode())
        

    def publish_current_waypoint(self):
        if(self.current_waypoint !=None):
            if(self.current_waypoint['type'] == 'elevator_outside_entrance'):
                print "Going to the elevator entrance" 

            elif(self.current_waypoint['type'] == 'elevator_inside_entrance'):
                print "Going in to the elevator" 

            elif(self.current_waypoint['type'] == 'elevator_outside_exit'):
                print "Exiting elevator" 

            elif(self.current_waypoint['type'] == 'door_start'):
                print "Going to the start of the door"         

            msg = navigator_goal_msg_t()
            msg.goal = point_t()
            msg.goal.x = self.current_waypoint['xyt'][0]
            msg.goal.y = self.current_waypoint['xyt'][1]
            msg.goal.yaw =  self.current_waypoint['xyt'][2]
            msg.use_theta = 1;
            msg.utime = int(time()* 1e6)
            msg.nonce = 0
            msg.sender = 0
            self.lc.publish("NAV_GOAL", msg.encode())
        else:
            print "Error : No current Waypoint " 

    def convert_node_msg_to_dict(self, msg):
        place = {'name':msg.name, 'type': msg.type, 
                 'xy': [msg.x, msg.y] , 'theta': msg.theta, 'std': msg.std, 
                 'floor_ind': msg.floor_ind, 'floor_no':msg.floor_no}
        
        return place

    def request_current_floor(self):
        msg = map_request_msg_t()
        msg.utime = time() * 1e6
        msg.requesting_prog = "TOPO_NAV"
        self.lc.publish("FLOOR_STATUS_REQUEST", msg.encode())

    def request_topology(self):
        msg = map_request_msg_t()
        msg.utime = time() * 1e6
        msg.requesting_prog = "TOPO_NAV"
        self.lc.publish("TOPOLOGY_REQUEST", msg.encode())

    def convert_portal_msg_to_dict(self, msg):        
        portal_type = ''
        if(msg.type == 0):
            portal_type = 'door'
        elif(msg.type == 1):
            portal_type = 'elevator'

        portal = {'type':portal_type, 'xy0': [msg.xy0[0], msg.xy0[1]], 
                 'xy1': [msg.xy1[0], msg.xy1[1]], 
                 'floor_ind': msg.floor_ind, 'floor_no':msg.floor_no}
        
        return portal

    def convert_portal_dict_to_msg(self, utime):
        p_list = portal_list_t()
        portal_list = []
        for i in self.portals:
            #print i
            msg = portal_node_t()
            msg.create_utime = utime
            #print "Portal Type : " , i['type'] 
            if(i['type']=='door'):
               msg.type = 0
            if(i['type']=='elevator'):
               msg.type = 1
            msg.xy0 = i['xy0']
            msg.xy1 = i['xy1']

            msg.floor_ind = i['floor_ind']
            msg.floor_no = i['floor_no']

            portal_list.append(msg)
            
        p_list.utime = utime
        p_list.no_of_portals = len(portal_list)
        p_list.portals = portal_list
        return p_list



    def update_to_file(self):
        #instead of writing to file - lets publish these as a message 
        
        self.publish_topology()

        try:
            f = open(self.file_path, 'w')
            #p = cPickle.Pickler(f)
            #p.dump(self.nodes)
            #p.dump(self.portals)

            pickle.dump(self.nodes, f)
            pickle.dump(self.portals, f)
            f.close() 
            print "File closed"
        except IOError:
            print "File Error : Unable to write to file" 

    def print_nodes_and_portals(self):
        print " Nodes : " 
        for i in self.nodes: 
            print "\t " , i
        
        print " Portals : " 
        for i in self.portals: 
            print "\t " , i 
            

    def update_from_file(self):
        try:
            f = open(self.file_path, 'r')
            #print cPickle.load(f)
            #print cPickle.load(f)
            #self.nodes = cPickle.load(f)
            #self.portals = cPickle.load(f)
            self.nodes = pickle.load(f)
            self.portals = pickle.load(f)
            f.close() 
            print "File closed"
            self.print_nodes_and_portals()

        except IOError:
            print "No pre-loaded file found"

    def send_speech_msg( self, cmd, prop, channel):
        msg = speech_cmd_t()
        msg.utime = int(time() * 1000000)
        msg.cmd_type = cmd
        msg.cmd_property = prop
        self.lc.publish(channel, msg.encode())
        print "Speech Msg Sent"

    def get_floor_string(self, floor_no):
        if(floor_no == 0):
            return "ground"
        elif(floor_no == 1):
            return "one"
        elif(floor_no == 2):
            return "two"
        elif(floor_no == 3):
            return "three"
        elif(floor_no == 4):
            return "four"
        elif(floor_no == 5):
            return "five"
        elif(floor_no == 6):
            return "six"
        elif(floor_no == 7):
            return "seven"
        elif(floor_no == 8):
            return "eight"
        elif(floor_no == 9):
            return "nine"
        else:
            return "unknown"

    def goal_handler(self, channel, data):
        msg = place_node_t.decode(data)
        
        print "Place : " , msg.name 

        goal = {'name':msg.name, 'floor_no': msg.floor_no}

        #self.last_querry_goal = goal

        self.find_path_to_goal(goal)

    def floor_change_handler(self, channel, data):
        msg = floor_change_msg_t.decode(data)

        print "Floor Change Heard => New Floor : " , msg.floor_no

        if(self.current_waypoint != None):
            print "Going to location - checking waypoint list " 
            
            if(self.current_waypoint['type'] == 'elevator_inside_exit'):
                if(self.current_waypoint['floor_no'] == msg.floor_no):
                    print "We are on the correct floor - check if the elevator door is open"

                    self.send_speech_msg("AT_EXIT_FLOOR", "", "ELEVATOR_STATUS")

                    #check the next waypoint
                    if(self.current_path[len(self.current_path)-1]['type']== 'elevator_outside_exit' \
                           and self.current_path[len(self.current_path)-1]['floor_no'] == msg.floor_no):
                        print "We are at the correct floor - checking to see if the elevator is open"

                        #send the elevator check message 
                        g_msg = goal_t()
                        
                        g_msg.pos = [self.current_path[len(self.current_path)-1]['xyt'][0],\
                                         self.current_path[len(self.current_path)-1]['xyt'][1]]

                        print "Asking to check position" 

                        #sending closed message for now
                        if(self.door_mode == 'ask'):
                            self.send_speech_msg("ELEVATOR_STATUS", "CLOSED", "ELEVATOR_STATUS")
                        else:
                            self.lc.publish("CHECK_ELEVATOR", g_msg.encode())
                        #we should jump two waypoints 

                        #self.current_waypoint = self.current_path.pop()
                        
                        #print self.current_waypoint
                        #print "This should be elevator End" 
                        #self.publish_current_waypoint()

                elif(self.current_waypoint['type'] == 'elevator_inside_entrance'):
                    print "Error : Floor changed before turning in place"             

                else:
                    print "We are not on the correct floor yet - waiting" 

            else:
                print "Error : Floor change outside of elevator - Time to panic :(" 
        #check if we have outstanding waypoints and if the current waypoint an elevator end 
        #and the new floor is the new elevator floor - move to that node 


    def door_status_handler(self, channel, data):
        msg = speech_cmd_t.decode(data)

        if(self.current_waypoint == None):
            print "No current Waypoint list - ignoring"
            return

        if(self.current_waypoint['type'] == 'door_start' and\
               (msg.cmd_type == "DOOR_STATUS" and\
               msg.cmd_property == "OPEN")):
            
            if(len(self.current_path) >0):
                print "At open Door - poping"
                self.current_waypoint = self.current_path.pop()
                self.print_current_waypoint_list()
                self.publish_current_waypoint()

                print "At Open Door - travelling through door" 

        else:
            print "At closed door - waiting for it to open"

    def topology_update_handler(self, channel, data):
        print "topology update received"
        msg = topology_t.decode(data)
        self.convert_msg_to_topology(msg)

    def elevator_status_handler(self, channel, data):
        msg = speech_cmd_t.decode(data)
        
        print "Elevator status msg received"  , msg

        if(self.current_waypoint == None or self.current_path == None):
            print "No path or current Waypoint - returning"
            return 


        if(self.current_waypoint['type'] == 'elevator_outside_exit' and\
               msg.cmd_type == "AT_EXIT_WITH_PERSON"):

            if(len(self.current_path) >0):
                print "Ouside elevator exit and person tracking - sending goal"                 
                self.current_waypoint = self.current_path.pop()
                self.print_current_waypoint_list()
                self.publish_current_waypoint()
                
            return


        if((self.current_waypoint['type'] == 'elevator_outside_entrance' or \
                self.current_waypoint['type'] == 'elevator_inside_exit') and\
               msg.cmd_type == "OPEN_ELEVATOR"):


            if(self.current_waypoint['type'] == 'elevator_outside_entrance'):
                print "At elevator entrance - and heard open door"
                glist_msg = goal_list_t()
                glist_msg.utime = int(time()* 1e6)
                glist_msg.num_goals = 1
                glist_msg.sender_id = 1
                glist_msg.goals = []
                
                goal_point = goal_t()
                goal_point.pos = [self.current_path[len(self.current_path)-1]['xyt'][0], \
                                      self.current_path[len(self.current_path)-1]['xyt'][1]]
                
                goal_point.size = [0.3, 0.3]
                goal_point.theta = self.current_path[len(self.current_path)-1]['xyt'][2]
                goal_point.use_theta = 1
                goal_point.heading_tol = 0.3
                goal_point.speed = 0 
                goal_point.speed_tol = 0.0
                goal_point.max_speed = 0
                goal_point.min_speed = 0
                goal_point.wait_until_reachable = 0
                goal_point.do_turn_only = 0 
                glist_msg.goals.append(goal_point)

                self.lc.publish("RRTSTAR_ELEVATOR_GOALS", glist_msg.encode())

                self.current_waypoint = self.current_path.pop()
                self.print_current_waypoint_list()

                return


            if(self.current_waypoint['type'] == 'elevator_inside_exit'):
                print "Inside elevator (at exit floor) - and heard open door"

                glist_msg = goal_list_t()
                glist_msg.utime = int(time()* 1e6)
                glist_msg.num_goals = 1
                glist_msg.sender_id = 1
                glist_msg.goals = []
                
                goal_point = goal_t()
                goal_point.pos = [self.current_path[len(self.current_path)-1]['xyt'][0], \
                                      self.current_path[len(self.current_path)-1]['xyt'][1]]
                
                goal_point.size = [0.3, 0.3]
                goal_point.theta = self.current_path[len(self.current_path)-1]['xyt'][2]
                goal_point.use_theta = 1
                goal_point.heading_tol = 0.3
                goal_point.speed = 0 
                goal_point.speed_tol = 0.0
                goal_point.max_speed = 0
                goal_point.min_speed = 0
                goal_point.wait_until_reachable = 0
                goal_point.do_turn_only = 0 
                glist_msg.goals.append(goal_point)

                self.lc.publish("RRTSTAR_ELEVATOR_GOALS", glist_msg.encode())

                self.current_waypoint = self.current_path.pop()
                self.print_current_waypoint_list()
                
                return

            
            if(len(self.current_path) >0):
                print "++++++++++++++++ Sending Elevator Command"                 
                
                print "At open Elevator - poping"
                self.current_waypoint = self.current_path.pop()
                self.print_current_waypoint_list()
                self.publish_current_waypoint()

                print "At Open Elevator - travelling through elevator" 

        else:
            print "At closed elevator - waiting for it to open"

    def waypoint_status_handler(self, channel, data):
        msg = speech_cmd_t.decode(data)

        print "Waypoint Status Received"

        if(self.current_path == None):
            print "No current Path - return"
            return
        
        if(msg.cmd_type == "WAYPOINT_STATUS" and\
               msg.cmd_property == "REACHED"):
            
            print "Current Waypoint reached - considering the next one"
            print "Current Waypoint " , self.current_waypoint

            if(len(self.current_path) ==0 ): 
                print "At the goal - we are done" 
                self.send_speech_msg("PATH_STATUS", "AT_GOAL", "PATH_STATUS")
                print "At the goal"
                return 

            print "Next Waypoint " , self.current_path[len(self.current_path)-1]

            if(self.current_waypoint['type'] == 'door_start'):
                print "At door entrance - checking to see if open" 

                g_msg = goal_t()
                
                g_msg.pos = [self.current_path[len(self.current_path)-1]['xyt'][0],\
                                 self.current_path[len(self.current_path)-1]['xyt'][1]]
                
                #

                print "Asking to check position" 
                if(self.door_mode == 'ask'):
                #Actually - this should send message to check open here 
                    self.send_speech_msg("DOOR_STATUS", "CLOSED", "DOOR_STATUS")
                else:
                    self.lc.publish("CHECK_DOOR", g_msg.encode())
                #this should wait until an open message is received - to move to the next waypoint             
                return


            if(self.current_waypoint['type'] == 'elevator_outside_entrance'):
                print "At elevator start  - signaling at elevator"
                #Actually - this should send message to check open here 
                g_msg = goal_t()
                
                g_msg.pos = [self.current_path[len(self.current_path)-1]['xyt'][0],\
                                 self.current_path[len(self.current_path)-1]['xyt'][1]]
                
                print "Sending At elevator entrance msg" 
                #self.send_speech_msg("AT_ELEVATOR_ENTRANCE", "", "ELEVATOR_STATUS")

                print "Asking to check position" 

                direction = "up"

                if(self.current_path[len(self.current_path)-2]['floor_no'] - self.current_path[len(self.current_path)-1]['floor_no'] > 0):
                    direction = "up"
                    print "We need to go up" 
                elif(self.current_path[len(self.current_path)-2]['floor_no'] - self.current_path[len(self.current_path)-1]['floor_no'] < 0):
                    direction = "down"
                    print "We need to go down" 

                if(self.door_mode == 'ask'):
                    self.send_speech_msg("AT_ELEVATOR_ENTRANCE", direction , "ELEVATOR_STATUS")
                else:
                    print "Checking if the elevator is reachable"
                    self.send_speech_msg("AT_ELEVATOR_ENTRANCE", direction , "ELEVATOR_STATUS")

                    self.lc.publish("CHECK_ELEVATOR", g_msg.encode())
                #this should wait until an open message is received - to move to the next waypoint 
                return
                
            elif(self.current_waypoint['type'] == 'elevator_inside_exit'):
                print "Done Turning around - publish message"

                ask_floor = self.get_floor_string(self.current_waypoint['floor_no'])

                self.send_speech_msg("DONE_TURNING", ask_floor , "ELEVATOR_STATUS")

                print "Waiting for Floor change"                 
                
                return
 
            if(self.current_waypoint['type'] == 'door_end'):
                print "At the end of the door  - signaling passed"
                self.send_speech_msg("DOOR_STATUS", "PASSED", "DOOR_STATUS")

            if(self.current_waypoint['type'] == 'elevator_outside_exit'):
                #check if the next waypoint is the same elevator at a different floor 
                print "Outside the elevator (on Exit floor)"
                self.send_speech_msg("EXITED_ELEVATOR", "", "ELEVATOR_STATUS")

                #this one shuld wait to hear if it has the person - so that the robot can move on 
                
                print "Waiting for DM signal" 

                return

            #### Need to add a check to see when the turn is done also 

            if(self.current_waypoint['type'] == 'elevator_inside_entrance'):

                if(self.current_path[len(self.current_path)-1]['type']== 'elevator_inside_exit'):
                    print "Inside Elevator - sending status and turning in place" 

                    #calculate heading difference 

                    print "Current Heading " ,  self.current_waypoint['xyt'][2]

                    print "Next waypoint heading " , self.current_path[len(self.current_path)-1]['xyt'][2]

                    heading_difference = self.current_waypoint['xyt'][2] - self.current_path[len(self.current_path)-1]['xyt'][2]

                    while (heading_difference < - 2 * math.pi):
                        heading_difference += 2 * math.pi
                    while (heading_difference > 2 * math.pi):
                        heading_difference -= 2 * math.pi

                    if(heading_difference > 10.0 /180.0 * math.pi):

                        ask_floor = self.get_floor_string(self.current_path[len(self.current_path)-1]['floor_no'])

                        print "We need to go to floor : " , ask_floor

                        self.send_speech_msg("INSIDE_ELEVATOR_TURNING", ask_floor , "ELEVATOR_STATUS")

                        print "Inside the elevator - Turning in place" 
                        #turn towards the next waypoint - for now direct command 

                        #ideally direct this through the navigator 
                        glist_msg = goal_list_t()
                        glist_msg.utime = int(time()* 1e6)
                        glist_msg.num_goals = 1
                        glist_msg.sender_id = 1
                        glist_msg.goals = []

                        goal_point = goal_t()
                        goal_point.pos = [self.current_path[len(self.current_path)-1]['xyt'][0], \
                                              self.current_path[len(self.current_path)-1]['xyt'][1]]

                        goal_point.size = [0.3, 0.3]
                        goal_point.theta = self.current_path[len(self.current_path)-1]['xyt'][2]
                        goal_point.use_theta = 1
                        goal_point.heading_tol = 0.3
                        goal_point.speed = 0 
                        goal_point.speed_tol = 0.0
                        goal_point.max_speed = 0
                        goal_point.min_speed = 0
                        goal_point.wait_until_reachable = 0
                        goal_point.do_turn_only = 1 
                        glist_msg.goals.append(goal_point)

                        self.lc.publish("RRTSTAR_ELEVATOR_GOALS", glist_msg.encode())

                        self.current_waypoint = self.current_path.pop()
                        self.print_current_waypoint_list()

                        print "Sent turn in place message" 
                    
                        return 

                    else:
                        print "Already within heading" 
                        ask_floor = self.get_floor_string(self.current_path[len(self.current_path)-1]['floor_no'])

                        print "We need to go to floor : " , ask_floor

                        self.send_speech_msg("INSIDE_ELEVATOR_NOT_TURNING", ask_floor , "ELEVATOR_STATUS")
                        print "Inside the elevator - No need to turn in place" 

                        self.current_waypoint = self.current_path.pop()                        
                        self.print_current_waypoint_list()

                        #we are poping two waypoints 

                        print "Sent turn in place message" 
                    
                        return 

            if(len(self.current_path) >0):
                print "At normal waypoint - poping"
                self.current_waypoint = self.current_path.pop()
                self.print_current_waypoint_list()
                #hmm - this republishes that waypoint 
                self.publish_current_waypoint()
            else:
                print "Do not have a next waypoint - should not be here" 

        elif(msg.cmd_type == "WAYPOINT_STATUS" and\
               msg.cmd_property == "FAILED"):
            print "Goal failed - Error : " 
            self.send_speech_msg("PATH_STATUS", "FAILED", "PATH_STATUS")
            print "At the goal"
            return 
        

    def goal_name_handler(self, channel, data):
        msg = place_node_t.decode(data)
        
        print "Place : " , msg.name 

        goal = {'name':msg.name, 'floor_no': -1}

        #self.last_querry_goal = goal

        self.find_path_to_goal(goal)

    def goal_confirm_handler(self, channel, data):
        msg = place_node_t.decode(data)
        
        if(self.confirmed_path['goal'] !=None):
            print "Confirm Place : " , msg.name , "Feasible Goal : " , self.confirmed_path['goal']

            if(self.confirmed_path['goal']['name'] == msg.name):
                print "Goal Has been confirmed - drive to location" 
                self.drive_to_location(self.confirmed_path['path'])
                #reset the confirmed path
                self.confirmed_path = {'goal': None, 'path' : None}
        
        else: 
            if(self.current_path != None):
                print "Already going to the same goal" 
            else: 
                print "Error - Do not have feasile location" 

    def drive_to_location(self, path):
        print "Driving to Location" 
        print "path to goal " , path 

        self.current_path = self.convert_result_msg_to_list(path)

        #send out the first location 
        print "Sending first waypoint" 
        
        print "At the start of goal list - poping" 
        self.current_waypoint = self.current_path.pop()
        
        self.publish_current_waypoint()
        
        ##Handle sending the navigator the waypoint set 
        
    def node_handler(self, channel, data):
        msg = place_node_t.decode(data)
        
        print "Place : " , msg.name , " Pos : " , msg.x, msg.y, msg.theta
        current_node = self.convert_node_msg_to_dict(msg)
        print "Current Node  : " ,  current_node
        self.nodes.append(current_node)

        print "=====  All Nodes  =====" 
        for i in self.nodes: 
            print "\t : ", i 
        #might querry the costs also 
        self.update_to_file()

    def convert_node_msg_to_list(self, place_list):
        self.nodes = []
        for i in place_list.trajectory:
            place = {'name': i.name, 'type': i.type, \
                         'xy':[i.x, i.y], 'theta':i.theta, \
                         'std': i.std, 'floor_ind': i.floor_ind, \
                         'floor_no': i.floor_no}
            
            self.nodes.append(place)

        print "New Place List"
        for i in self.nodes:
            print i 
        
    def convert_portal_list_msg_to_list(self, portal_list):
        #convert the result to list - including correct orientations 
        self.portals = []
        for i in portal_list.portals: 
            portal_type = 'door'
            if(i.type == 1):
                portal_type = 'elevator'
            
            floor_ind = i.floor_ind
            floor_no = i.floor_no
            
            portal = {'type': portal_type, 'xy0': i.xy0, \
                          'xy1': i.xy1, 'floor_ind': floor_ind, \
                          'floor_no': floor_no}

            self.portals.append(portal)

        print "New Portal List" 
        for i in self.portals:
            print i 

    def convert_result_msg_to_list(self, msg):
        #convert the result to list - including correct orientations 
        waypoint_list = []

        first_elevator = 0

        for i in msg.portal_list.portals: 
            p_type = 'door'
            if(i.type == 1):
                p_type = 'elevator'

            if(first_elevator == 0 and p_type == 'elevator'):
                print "Elevator entrance " 

                if(i.floor_no == 4 and self.hack == 1):
                     print " Entrance elevator is on the 4th floor - adding the hack - adding additional waypoint" 

                     portal = {'type': 'prereq_waypoint', 'xyt' : [ 4.681567, 2.528924 , 3.086094],\
                                   'floor_ind' : i.floor_ind, \
                                   'floor_no' : i.floor_no}
                     
                     waypoint_list.append(portal)
                
                heading = math.atan2(i.xy1[1] - i.xy0[1], i.xy1[0] - i.xy0[0]) 
                portal = {'type': p_type + "_outside_entrance", 'xyt' : [i.xy0[0], i.xy0[1], heading],\
                              'floor_ind' : i.floor_ind, \
                              'floor_no' : i.floor_no}
                
                waypoint_list.append(portal)
                
                portal = {'type': p_type + "_inside_entrance", 'xyt' : [i.xy1[0], i.xy1[1], heading],\
                              'floor_ind' : i.floor_ind, \
                              'floor_no' : i.floor_no}

                first_elevator = 1
               
                    
                waypoint_list.append(portal)
                    

            elif(first_elevator == 1 and p_type == 'elevator'):
                print "Elevator Exit" 
                heading = math.atan2(i.xy1[1] - i.xy0[1], i.xy1[0] - i.xy0[0]) 
                portal = {'type': p_type + "_inside_exit", 'xyt' : [i.xy0[0], i.xy0[1], heading],\
                              'floor_ind' : i.floor_ind, \
                              'floor_no' : i.floor_no}
                
                waypoint_list.append(portal)
                
                portal = {'type': p_type + "_outside_exit", 'xyt' : [i.xy1[0], i.xy1[1], heading],\
                              'floor_ind' : i.floor_ind, \
                              'floor_no' : i.floor_no}
                
                first_elevator = 0
                
                waypoint_list.append(portal)
                
                #add the hack here 

                if(i.floor_no == 4 and self.hack == 1):
                     print " Entrance elevator is on the 4th floor - adding the hack - adding additional waypoint" 

                     portal = {'type': 'prereq_waypoint', 'xyt' : [ 4.681567, 2.528924 , -0.086738],\
                                   'floor_ind' : i.floor_ind, \
                                   'floor_no' : i.floor_no}

                     waypoint_list.append(portal)


        #add the goal at the end 
        goal = {'type':'goal', 'floor_no': msg.goal_floor_no, 'xyt': [msg.goal.x, msg.goal.y, msg.goal.yaw]}
        waypoint_list.append(goal)

        waypoint_list.reverse()

        for i in waypoint_list:
            print i 
            
        
        return waypoint_list



    '''def convert_result_msg_to_list(self, msg):
        #convert the result to list - including correct orientations 
        waypoint_list = []
        for i in msg.portal_list.portals: 
            #print "Portal : " , i.xy0[0],  i.xy0[1], i.xy1[0],  i.xy1[1],i.type, i.floor_ind , i.floor_no

            p_type = 'door'
            if(i.type == 1):
                p_type = 'elevator'
            heading = math.atan2(i.xy1[1] - i.xy0[1], i.xy1[0] - i.xy0[0]) 
            #portal = {'type': p_type, 'xyt0' : [i.xy0[0], i.xy0[1], heading],\
            #              'xyt1': [i.xy1[0], i.xy1[1], heading], 'floor_ind' : i.floor_ind, \
            #              'floor_no' : i.floor_no}
            portal = {'type': p_type + "_start", 'xyt' : [i.xy0[0], i.xy0[1], heading],\
                          'floor_ind' : i.floor_ind, \
                          'floor_no' : i.floor_no}

            waypoint_list.append(portal)

            portal = {'type': p_type + "_end", 'xyt' : [i.xy1[0], i.xy1[1], heading],\
                          'floor_ind' : i.floor_ind, \
                          'floor_no' : i.floor_no}

            #check - elevator exit might be mixed up 
            
            #              'xyt1': [i.xy1[0], i.xy1[1], heading], 'floor_ind' : i.floor_ind, \
            #              'floor_no' : i.floor_no}
            
            waypoint_list.append(portal)
        #add the goal at the end 
        goal = {'type':'goal', 'floor_no': msg.goal_floor_no, 'xyt': [msg.goal.x, msg.goal.y, msg.goal.yaw]}
        waypoint_list.append(goal)

        waypoint_list.reverse()

        for i in waypoint_list:
            print i 
            
        
        return waypoint_list'''

    def print_current_waypoint_list(self):
        print "Current Path Waypoints" 
        for i in self.current_path:
            print i 
        
    def goal_result_handler(self, channel, data):
        msg = goal_feasibility_querry_t.decode(data)

        print "Goal result Msg received"

        ### we have received the result set 
        
        print " Cost to Goal : " , msg.cost_to_goal 

        if(msg.cost_to_goal > 0):
            if(self.current_floor_no != self.last_querry_goal['floor_no']):

                print "Sucess : Path is feasible - different floor"
                self.send_speech_msg("PATH_FEASIBLE_SAME_FLOOR", "FEASIBLE", "FEASIBILITY_STATUS")
            else:
                print "Sucess : Path is feasible - same floor"
                self.send_speech_msg("PATH_FEASIBLE_DIFFERENT_FLOOR", "FEASIBLE", "FEASIBILITY_STATUS")
            self.confirmed_path['goal'] = self.last_querry_goal
            self.confirmed_path['path'] = msg

        else:
            self.send_speech_msg("PATH_FEASIBILITY_STATUS", "INFEASIBLE", "FEASIBILITY_STATUS")

        for i in msg.portal_list.portals:
            print i 

        
        
        #save this and go through them on confirmation 

        #should inform feasibility and upon confirmation - go to the goal - waypoint by waypoint 
        


    def portal_handler(self, channel, data):
        msg = portal_node_t.decode(data)
        
        print "Portal  => Type  " , msg.type , " Pos : " , msg.xy0[0], msg.xy0[1], msg.xy1[0], msg.xy1[1]
        current_portal = self.convert_portal_msg_to_dict(msg)
        print "Current Portal : " , current_portal
        self.portals.append(current_portal)

        self.update_to_file()
        
        print "===== All Portals ====="
        for i in self.portals: 
            print "\t : " , i

    def goal_floor_handler(self, channel, data):
        ## This should check and send back which floor goal is 
        print "Goal Handler Called\n"

        for i in self.nodes: 
            if(i['name'] == goal_name):
                print "Goal found : ", i
                matching_goals.append(i)
                
        if(len(matching_goals) ==1):
            print "One Location found - Checking Feasibility" 
        elif(len(matching_goals) ==0):
            print "No such location found - Report Error"
        elif(len(matching_goals) >1):
            print "More than one location found - ask for clarification" 

    def floor_status_handler(self, channel, data):
        ## This should check and send back which floor goal is 
        print "Floor Handler Called\n"
        msg = floor_status_msg_t.decode(data)
        self.current_floor_ind = msg.floor_ind;
        self.current_floor_no = msg.floor_no;
        print "Current Floor : " , self.current_floor_no 
        

    def check_for_feasibility(self, goal): 
        print "Checking for feasibility - sending querry msg" 

        msg = goal_feasibility_querry_t()
        
        msg.utime = time()* 1e6
        msg.goal_floor_no = goal['floor_no']
        
        msg.portal_list = self.convert_portal_dict_to_msg(msg.utime)

        msg.goal = point_t()

        msg.goal.x = goal['xy'][0]
        msg.goal.y = goal['xy'][1]
        msg.goal.z = 0
        msg.goal.yaw = goal['theta']
        msg.goal.pitch = 0
        msg.goal.roll = 0

        self.lc.publish("GOAL_FEASIBILITY_CHECK", msg.encode())

    def find_path_to_goal(self, querry_goal):
        #assume this message will just provide us the location - assume that the location is unique 
        goal_name = querry_goal['name']
        goal_floor_no = querry_goal['floor_no'] 
        matching_goals = []


        for i in self.nodes: 
            if(i['name'] == goal_name):
                print "Goal found : ", i
                matching_goals.append(i)
        
        if(len(matching_goals) ==1):
            print "One Location found - Checking Feasibility" 

            #we should also send back which floor it is on 

            self.check_for_feasibility(matching_goals[0])
            self.last_querry_goal = matching_goals[0]

        elif(len(matching_goals) ==0):
            print "No such location found - Report Error"
            self.send_speech_msg("PATH_FEASIBILITY_STATUS", "UNKNOWN", "FEASIBILITY_STATUS")
            #send faliure 
        elif(len(matching_goals) >1):
            print "More than one location found - ask for clarification" 
            self.send_speech_msg("PATH_FEASIBILITY_STATUS", "MULTIPLE", "FEASIBILITY_STATUS")
            #send faliure - for now 
        
    def find_path_to_goal_with_floor(self, querry_goal):
        #assume this message will just provide us the location - assume that the location is unique 
        goal_name = querry_goal['name']
        goal_floor_no = querry_goal['floor_no'] 
        matching_goals = []


        for i in self.nodes: 
            if(i['name'] == goal_name and i['floor_no'] == goal_floor_no):
                print "Goal found : ", i
                matching_goals.append(i)
        
        if(len(matching_goals) ==1):
            print "One Location found - Checking Feasibility" 

            self.check_for_feasibility(matching_goals[0])

        elif(len(matching_goals) ==0):
            print "No such location found - Report Error"
        elif(len(matching_goals) >1):
            print "More than one location found - ask for clarification" 
            
    def run(self):
        print "Started LCM Listener"
        try:
            while self._running:
                self.lc.handle()
        except KeyboardInterrupt:
            pass

if __name__ == '__main__':

    parser = OptionParser()
    parser.add_option("-m", "--mode", dest="mode",action="store",
                      help="Mode of Operation - listen or load")

    parser.add_option("-d", "--door_mode", dest="door_mode",action="store",
                      help="Mode of Operation - ask or check")

    parser.add_option("-f", "--filename", dest="filename",action="store",
                      help="Filename")

    (options, args) = parser.parse_args()

    print "Options : " , options 
        
    file_path = 'topo_layout.log'
    mode = 'listen'
    door_mode = 'ask'
    #if(len(argv) >= 2):
    #    
    #    file_path = argv[1]
    if(options.filename != None):
        file_path = options.filename

    if(options.mode != None):
        mode = options.mode

    if(options.door_mode != None):
        door_mode = options.door_mode

    background = node_listener(mode, file_path, door_mode)
    bg_thread = threading.Thread( target=background.run )
    bg_thread.start()

    if(mode == 'load'):
        print "Requesting Topology update" 
        background.request_topology()
    

