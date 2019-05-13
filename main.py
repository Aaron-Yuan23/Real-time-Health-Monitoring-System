#Google Drive API
from __future__ import print_function
from apiclient import discovery
from httplib2 import Http
from oauth2client import file as oauth_file, client, tools
import ffmpy
import tensorflow as tf
import numpy as np
import os
from time import sleep
from common import common as cm
import HttpThread
import queue
import threading
import time
import glob
#from keras.models import load_model

UBUNTU = True  # False
USE_ROS = True
if UBUNTU:
    KINECT_RECORDER_PATH = "/mnt/c/workspace/KinectV2/x64/Debug/KinectV2.exe"
    KINECT_RECORDER_PATH_CONTINOUS = "/mnt/c/workspace/KinectV2recorderContinous/x64/Debug/KinectV2.exe"
else:
    KINECT_RECORDER_PATH = "D:\\KinectV2\\x64\\Debug\\KinectV2.exe"
    KINECT_RECORDER_PATH_CONTINOUS = "D:\\KinectV2recorderContinous\\x64\\Debug\\KinectV2.exe"
folderId = "1_PBjPI_2rg_rKc-HGf0WDoOZjsAvwr0U"
CLASSIFICATION_OUTPUT_TO_STR = {0: "STANDING", 1: "SITTING", 2: "LYING DOWN", 3: "BENDING"}
fallNum = 0

posture_send_skip = 0

lowest_y_point = 1000

standing_height = 0

# Threshold of how many meters from the lowest point in the room is acceptable to approve the person is lying down on the ground
M_FROM_FLOOR = 0.35

objects_per_room = {}   

comm = cm()

# Init HTTP Thread
QDataDict = queue.Queue(maxsize=0)
stopHttpThread = threading.Event()
httpThread = HttpThread.HttpThread(QDataDict, stopHttpThread)
httpThread.start()

#Init ROS
pub1 = ""
pub2 = ""
pub3 = ""
r = ""
if(USE_ROS):
    import rospy
    from std_msgs.msg import String
    from sensor_msgs import msg
    pub1 = rospy.Publisher('CAM_POSTURE', String, queue_size=10)
    pub2 = rospy.Publisher('CAM_FALL', String, queue_size=10)
    pub3 = rospy.Publisher('FALL_LINK', String, queue_size=10)
    rospy.init_node('demo_pub_node')
    camConePublisher = rospy.Publisher('Cam_Data',msg.LaserScan,queue_size=10)
    r = rospy.Rate(1)

def sendROSData(posture, fall):
    pub1.publish(posture)
    pub2.publish(str(fall))
    return

def sendHTTPData(posture, fall):
    global posture_send_skip
    if(posture_send_skip == 0 or fall == True):
        dictData = {}
        dictData["posture"] = posture
        dictData["timestamp"] = str(int(time.time()))
        dictData["fall"] = fall
        QDataDict.put(dictData)
    posture_send_skip += 1
    if(posture_send_skip == 5):
        posture_send_skip = 0
    return

def uploadVideoToDrive(fileName):
    SCOPES = 'https://www.googleapis.com/auth/drive'
    store = oauth_file.Storage('storage.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('client_secrets.json', SCOPES)
        creds = tools.run_flow(flow, store)
    DRIVE = discovery.build('drive', 'v2', http=creds.authorize(Http()))
    metadata = {'title': fileName, 'parents':[{
        "kind": "drive#parentReference",
        "id": folderId,
        "parentLink": "https://drive.google.com/drive/folders/1_PBjPI_2rg_rKc-HGf0WDoOZjsAvwr0U?ogsrc=32",
        "isRoot": True
    }], 'shareable':True}
    ff=ffmpy.FFmpeg(
		inputs={fileName: None},
		outputs={'output.avi': ['-y', '-r', '12']}
	)
    ff.run()
    res = DRIVE.files().insert(convert=False, body=metadata, media_body='output.avi', fields='alternateLink,mimeType,exportLinks').execute()
    if res:
        print('Uploaded "%s" (%s)' % (fileName, res['mimeType']))
        return res['alternateLink']
    return ''

def recordSendFallVideo():
    os.system(KINECT_RECORDER_PATH)
    #os.startfile(KINECT_RECORDER_PATH)#does this run the video recorder why is this commented
    sleep(10)
    fileNameList = glob.glob("*.avi")
    while(not fileNameList): #i.e. is empty
        fileNameList = glob.glob("*.avi")
    fileName = fileNameList[0]
    #Send to google drive and get link
	#Video changed to RGB which requires 60 frame recording use ffmpeg script to downscale Frames and possibly convert to phone friendly video codec
    link = uploadVideoToDrive(fileName)
    pub3.publish(link)
    os.remove(fileName)
    return

def importFloorData(roomNumber):
    filepath = "data/floorplans/" + str(roomNumber) + ".txt"
    if (os.path.isfile(filepath)):
        file = open(filepath, 'r')
        objects_per_room[str(roomNumber)] = []  # This room has a list of objects
        objects = file.read().splitlines()
        num_objects = int(len(objects) / 4)  # Each file has 4 coords
        for i in range(num_objects):
            objects_per_room[str(roomNumber)].append(
                objects[(i * 4):(i * 4) + 4])  # Append the object to the list of objects for that particular room
    print("FLOOR OBJECT DATA IMPORTED FOR ROOM #" + str(roomNumber) + "... !")
    return

# deprecated but still usable, isLayingOnTheFloor() is the new implementation
def isWithinGroundRange(x, z, roomNumber):
    objects = objects_per_room[str(roomNumber)]  # Impoted floor data for that room
    for object in objects:
        if (x > float(object[0]) and x < float(object[1]) and z > float(object[2]) and z < float(object[3])):  # If person is on that object
            return False
    return True


def getLSTMClassification(inputVals):
    #if (inputVals[0][0] < 0.3):
    #    return "LYING DOWN"
    classification_output = model.predict(np.array([tuple(inputVals)]).reshape(1,7,1))
    height = inputVals[0][0]
    #print(height)
    #if (height < 0.35):
    #    classification_output *= [0,0,1]
    #elif (height < 1.2 and height > 0.7):
    #    classification_output *= [0.1, 2, 1]  # Can't be LYING DOWN
    #print('classification_output == ' + str(classification_output))
    return CLASSIFICATION_OUTPUT_TO_STR[np.argmax(classification_output,1)[0]]

def isLayingOnTheFloor(footRightPosY, footLeftPosY):
    if ((footRightPosY < (lowest_y_point + M_FROM_FLOOR)) and (footLeftPosY < (lowest_y_point + M_FROM_FLOOR))):
        return True
    return False
def publishCamData(camPosture, footRightPosY, footLeftPosY ):
    rangeData = msg.LaserScan()
    rangeData.header.frame_id = "camFrame"
    rangeData.header.stamp = rospy.Time.now()
    rangeData.range_min= lowest_y_point
    rangeData.scan_time = footRightPosY
    rangeData.angle_min = footLeftPosY
    if camPosture == "STANDING":
        camPostureInt = 0
    elif camPosture == "SITTING":
        camPostureInt = 1
    elif camPosture == "LAYING DOWN":
        camPostureInt = 2
    else:
        camPostureInt = 3

    rangeData.time_increment = camPostureInt
    camConePublisher.publish(rangeData)

if __name__ == "__main__":
    print("Loading model..")
    model = joblib.load('model/posture_model.pkl')

    # LAUNCH TKINTER UI IF USING WINDOWS
    root = ""
    labelText = ""
    if (not UBUNTU):
        from tkinter import Tk, StringVar, Label

        root = Tk()
        root.title("POSTURE DETECTION")
        root.geometry("400x100")
        labelText = StringVar()
        labelText.set('Starting...!')
        button = Label(root, textvariable=labelText, font=("Helvetica", 40))
        button.pack()
        root.update()

    roomNumber = 0  # Room number 0
    importFloorData(roomNumber)

    file = open('real_time_joints_data.txt', 'w+')
    #file = open('/mnt/c/workspace/FallDetection/src/data/real_time_joints_data.txt', 'w+')
    index = 0

    # Initialization step
    # Extract data from sensor and take the lowest point of foot left & right
    while (index < 300):  # 3 sec * 10numbers/frame 10frames/sec
        lines = file.read().splitlines()
        file.seek(0)
        if (len(lines) >= index + 10):  # if there is new data
            index += 10
            inp = lines[index - 10:index]  # get data for next frame
            # Which Y-position is lower?
            if (float(inp[7]) < float(inp[8])):  # Then use inp[5] because it's the smallest Y-point
                if (lowest_y_point > float(inp[7])):
                    lowest_y_point = float(inp[7])
            else:
                if (lowest_y_point > float(inp[8])):
                    lowest_y_point = float(inp[8])

    print("LOWEST_Y_POINT === " + str(lowest_y_point))

    # End of initialization step
    file = open('real_time_joints_data.txt', 'w+')
    #file = open('/mnt/c/workspace/FallDetection/src/data/real_time_joints_data.txt', 'w+')
    index = 0

    # Start system
    while True:
        global posture
        lines = file.read().splitlines()
        file.seek(0)  # move cursor to beggining of file for next loop
        if (len(lines) >= index + 10):  # if there is new data
            index += 10
            inp = lines[index - 10:index]  # get data for next frame
            # index += 20 #10 FPS
            inp = [float(i) for i in inp]
            inputVals = np.random.rand(1, 7)
            inputVals[0] = inp[:7]  # Only the first 7 values. The other two values will be used to check the floor plan
            posture = getLSTMClassification(inputVals)
            if (not UBUNTU):
                labelText.set(posture)
                root.update()
            print(posture)
            if (posture == "LYING DOWN"):
                if (isLayingOnTheFloor(float(inp[7]), float(inp[8]))):
                    # timestamps = []
                    # timestamps.append(inp[9])
                    timestamp = inp[9]
                    fall = True
                    allowed = 6  # at least 95% of the time detected as LYING DOWN.
                    allowed_not_on_floor = 5
                    for i in range(20):  # check LYING DOWN for 2 seconds (10fps*2s = 20 frames)
                        while (len(lines) < index + 10):
                            lines = file.read().splitlines()
                            file.seek(0)  # move cursor to beggining of file for next loop
                        index += 10
                        inp = lines[index - 10:index]  # get data for next frame
                        # index += 20 #10 FPS
                        inp = [float(i) for i in inp]
                        inputVals = np.random.rand(1, 7)
                        inputVals[0] = inp[:7]
                        # timestamps.append(inp[9])
                        posture = getLSTMClassification(inputVals)
                        print(posture)
                        if (not UBUNTU):
                            labelText.set(posture)
                            root.update()
                        if (posture == "LYING DOWN"):  # Is the person LYING DOWN on the floor?
                            print('LYING DOWN')
                            sendHTTPData("LYING DOWN", False)
                            if(USE_ROS):
                                sendROSData(posture, False)
                                publishCamData("Fall", float(inp[7]),float(inp[8]))
                            if (isLayingOnTheFloor(float(inp[7]), float(inp[8])) == False):
                                if (allowed_not_on_floor == 0):
                                    print("PERSON IS NOT LAYING ON THE FLOOR! No fall..!")
                                    fall = False
                                    break
                                else:
                                    allowed_not_on_floor -= 1
                        else:  # 10% allowed to not be LYING DOWN (2/20)
                            if (allowed == 0):
                                print("PERSON HAS NOT BEEN LAYING ON THE FLOOR FOR MORE THAN 2 SECONDS! No fall..!")
                                fall = False
                                break
                            else:
                                allowed -= 1
                    if (fall):
                        # Send Posture to be LYING DOWN and Fall to be True
                        print('Sending data ...!')
                        sendHTTPData("LYING DOWN", True)
                        if(USE_ROS):
                            sendROSData(posture, True)
                            publishCamData(posture, float(inp[7]), float(inp[8]))
                        if (not UBUNTU):
                            labelText.set("FALLEN!")
                            root.update()
                        print("--FALLEN!--")
                        recordSendFallVideo()

                        # You can now reset index=0 and delete the file to restart the While loop from current data.
                        while posture=="LYING DOWN":  # Fallen until detected in another posture
                            while (len(lines) < index + 10):
                                lines = file.read().splitlines()
                                file.seek(0)  # move cursor to beggining of file for next loop
                            index += 10
                            inp = lines[index - 9:index]  # get data for next frame
                            inp = [float(i) for i in inp]
                            inputVals = np.random.rand(1, 7)
                            inputVals[0] = inp[:7]
                            posture = getLSTMClassification(inputVals)
                            print(posture)
                            if posture != "LYING DOWN":
                                if (not UBUNTU):
                                    labelText.set(posture)
                                    root.update()
                                file = open('real_time_joints_data.txt', 'w+')
                                #file = open('/mnt/c/workspace/FallDetection/src/data/real_time_joints_data.txt', 'w+')
                                index = 0
                else:
                    # Send posture to be LYING DOWN and fall status to be False
                    sendHTTPData("LYING DOWN", False)
                    if(USE_ROS):
                        sendROSData("LYING DOWN", False)
                        publishCamData(posture, float(inp[7]), float(inp[8]))
            else:
                # Send posture result and fall status to be False
                sendHTTPData(posture, False)
                if(USE_ROS):
                    sendROSData(posture, False)
                    publishCamData(posture, float(inp[7]), float(inp[8]))
        if (index > 2500):
            # index = 300
            file = open('real_time_joints_data.txt', 'w+')
            #file = open('/mnt/c/workspace/FallDetection/src/data/real_time_joints_data.txt', 'w+')
            index = 0


