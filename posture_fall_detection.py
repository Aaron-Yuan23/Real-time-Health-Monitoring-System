import tensorflow as tf
import numpy as np
import os
from time import sleep
from common import common as cm
#from builtins import True
from sklearn.externals import joblib

USE_TESTING_DATA = False
USE_ROS = False
UBUNTU = True
CLASSIFICATION_OUTPUT_TO_STR = {0:"STANDING", 1:"SITTING", 2:"LAYING DOWN", 3:"BENDING"}
fallNum = 0

lowest_y_point = 1000

#Threshold of how many m from the lowest point in the room is acceptable to approve the person is laying down on the ground?
M_FROM_FLOOR = 0.25


# X_START_NONFLOOR = 0.0
# X_END_NONFLOOR = 0.0
# Z_START_NONFLOOR = 0.0
# Z_END_NONFLOOR = 0.0
objects_per_room = {}

comm= cm()

def getClassification(inputVals):
    #print('inputVals = ' + str(inputVals))
    classification_output = loaded_model.predict(inputVals)
    print('prediction == ' + str(CLASSIFICATION_OUTPUT_TO_STR[classification_output[0]]))
    # if(inputVals[0][0] < 0.3):
    #     return "LAYING DOWN"
    #Gets the argmax value of the output of the neural network
    # if(inputVals[0][0] < 0.45):
    #     classification_output *= [0,1,2,1] #Can't be standing
    # elif(inputVals[0][0] >= 0.75):
    #     classification_output *= [1,1,0,1] #Can't be laying down
    #classification_output = tf.argmax(classification_output,1).eval()
    #print("INPUT == " + str(inputVals))
    return CLASSIFICATION_OUTPUT_TO_STR[classification_output[0]]

def importFloorData(roomNumber):
    filepath = "data/floorplans/" + str(roomNumber) + ".txt"
    if(os.path.isfile(filepath)):
        file = open(filepath, 'r')
        objects_per_room[str(roomNumber)] = [] #This room has a list of objects
        objects = file.read().splitlines()
        num_objects = int(len(objects)/4) #Each file has 4 coords
        for i in range(num_objects):
            objects_per_room[str(roomNumber)].append(objects[(i*4):(i*4)+4]) #Append the object to the list of objects for that particular room
    print("FLOOR OBJECT DATA IMPORTED FOR ROOM #" + str(roomNumber) + "... !")
    return

#deprecated but still usable, isLayingOnTheFloor() is the new implementation
def isWithinGroundRange(x, z, roomNumber):
    objects = objects_per_room[str(roomNumber)] #Impoted floor data for that room
    for object in objects:
        if(x > float(object[0]) and x < float(object[1]) and z > float(object[2]) and z < float(object[3])): #If person is on that object
            return False
    return True


def isLayingOnTheFloor(footRightPosY, footLeftPosY):
    if((footRightPosY < (lowest_y_point + M_FROM_FLOOR)) and (footLeftPosY < (lowest_y_point + M_FROM_FLOOR))):
        #print("PERSON LS LAYING ON THE FLOOR!")
        return True
    #print("PERSON not laying on the floor ..")
    
    return False

if __name__ == "__main__":
    loaded_model = joblib.load('model/posture_model.pkl')

    if(USE_TESTING_DATA):
        inputs, labels = comm.getTestingData()
        testNetwork(inputs, labels)
    else:
        #LAUNCH TKINTER UI IF USING WINDOWS   
        root = ""
        labelText = ""
        if(not UBUNTU):
            from tkinter import Tk, StringVar, Label
            root = Tk()
            root.title("POSTURE DETECTION")
            root.geometry("400x100")
            labelText = StringVar()
            labelText.set('Starting...!')
            button = Label(root, textvariable=labelText, font=("Helvetica", 40))
            button.pack()
            root.update()
        
        
        roomNumber = 0 #Room number 0
        importFloorData(roomNumber)
        
        file = open('real_time_joints_data.txt','w+')
        index = 0
        
        #Initialization step
        #Extract data from sensor and take the lowest point of foot left & right
        # while(index < 300): # 3 sec * 10numbers/frame 10frames/sec
        #     lines = file.read().splitlines()
        #     file.seek(0)
        #     if(len(lines) >= index+10): #if there is new data
        #         index += 10
        #         inp = lines[index-10:index] #get data for next frame
        #         #Which Y-position is lower?
        #         if(float(inp[7]) < float(inp[8])): #Then use inp[5] because it's the smallest Y-point
        #             if(lowest_y_point > float(inp[7])):
        #                 lowest_y_point = float(inp[7])
        #         else:
        #             if(lowest_y_point > float(inp[8])):
        #                 lowest_y_point = float(inp[8])
        lowest_y_point = 0
                    
        print("LOWEST_Y_POINT === " + str(lowest_y_point))
        
        #End of initialization step
        file = open('real_time_joints_data.txt','w+')
        index = 0
        
        #SETUP ROS PUBLISHERS IF USING UBUNTU
        pub1 = ""
        pub2 = ""
        r = ""
    
            
        #Start system
        print('Starting..')
        while True:#not rospy.is_shutdown(): #while True (windows) | not rospy.is_shutdown()
            file = open('real_time_joints_data.txt','r')
            lines = file.read().splitlines()
            file.seek(0) #move cursor to beggining of file for next loop
            if(len(lines) >= index+10): #if there is new data
                print('Classyfing ..')
                if(index > 2000):
                    index = 0
                    file = open('real_time_joints_data.txt','w+')
                index += 10
                inp = lines[index-10:index] #get data for next frame
                #index += 20 #10 FPS
                inp = [float(i) for i in inp]
                inputVals = np.random.rand(1,7)
                inputVals[0] = inp[:7] #Only the first 7 values. The other two values will be used to check the floor plan
                posture = getClassification(inputVals)
                
                if(not UBUNTU):
                    labelText.set(posture)
                    root.update()
                print(posture)
                

                # detect fall if person is lying on the foor for more than 2 seconds 
                if(posture == "LAYING DOWN"):
                    if(isLayingOnTheFloor(float(inp[7]),float(inp[8]))):
                        #timestamps = []
                        #timestamps.append(inp[9])
                        timestamp = inp[9]
                        fall = True
                        allowed = 2 #at least 95% of the time detected as laying down.
                        allowed_not_on_floor = 5
                        #MODIFIED 
                        for i in range(20): #check laying down for 2 seconds (10fps*2s = 20 frames)
                            while ((len(lines) < index+10)):
                                lines = file.read().splitlines()
                                file.seek(0) #move cursor to beginning of file for next loop
                            index += 10
                            inp = lines[index-10:index] #get data for next frame
                            #index += 20 #10 FPS
                            inp = [float(i) for i in inp]
                            inputVals = np.random.rand(1,7)
                            inputVals[0] = inp[:7]
                            #timestamps.append(inp[9])
                            posture = getClassification(inputVals)
                            print(posture)
                          
                            if(posture == "LAYING DOWN"): #Is the person laying down on the floor?
                                if(isLayingOnTheFloor(float(inp[7]),float(inp[8])) == False):
                                    if(allowed_not_on_floor == 0):
                                        print("PERSON IS NOT LAYING ON THE FLOOR! No fall..!")
                                        fall = False
                                        break
                                    else:
                                        allowed_not_on_floor -= 1
                                else: 
                                    print('Person is lying on the floor')
                            else: #10% allowed to not be laying down (2/20)
                                if(allowed == 0):
                                    print("PERSON HAS NOT BEEN LAYING ON THE FLOOR FOR MORE THAN 2 SECONDS! No fall..!")
                                    fall = False
                                    break
                                else:
                                    allowed -= 1
                                    print('Fall Detected!')

            if()    
# detect fall if person is lying below a certain threshold 
