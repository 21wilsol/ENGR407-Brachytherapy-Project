#Adapted from https://automaticaddison.com/how-to-perform-pose-estimation-using-an-aruco-marker/  Only thing still used is the euler from quat function
from __future__ import print_function
from charset_normalizer import detect
import cv2 #Import opencv, Do not need to import through pip if using Jetpack
from matplotlib.mathtext import MathTextParser
import numpy as np # Import Numpy library
from scipy.spatial.transform import Rotation as R # Maths module for handling rotation vectors
import math # Main Library for maths functionality
import time # Time Module
import threading # Need threading to access both cameras at the same time

#define the aruco marker size and where the yaml file is
aruco_marker_side_length = 0.055 #metres
camera_calibration_parameters_filename = 'calibration_chessboard.yaml' #relative path, make sure it is root directory of folder being used
#set up arduino
#Add arduino interface code when ready
coords =[0,0,0,0] #declare coords as empty vector to prevent memory issues
window_title = "dual cam aruco detector"
cv2.namedWindow(window_title,cv2.WINDOW_AUTOSIZE) #Define Window

class CSI_Camera:
    """CSI Camera Class to to initialise each camera"""

    def __init__(self):
        """Initialise camera by instantiating variables and threading"""
        # Initialize instance variables
        # OpenCV video capture element
        self.video_capture = None
        # The last captured image from the camera
        self.frame = None
        self.grabbed = False
        # The thread where the video capture runs
        self.read_thread = None
        self.read_lock = threading.Lock()
        self.running = False

    def open(self, gstreamer_pipeline_string):
        """Open camera function"""
        try:
            self.video_capture = cv2.VideoCapture(
                gstreamer_pipeline_string, cv2.CAP_GSTREAMER
            )
            # Grab the first frame to start the video capturing
            self.grabbed, self.frame = self.video_capture.read()

        except RuntimeError:
            self.video_capture = None
            print("Unable to open camera")
            print("Pipeline: " + gstreamer_pipeline_string)


    def start(self):
        if self.running:
            print('Video capturing is already running')
            return None
        # create a thread to read the camera image
        if self.video_capture != None:
            self.running = True
            self.read_thread = threading.Thread(target=self.updateCamera)
            self.read_thread.start()
        return self

    def stop(self):
        self.running = False
        # Kill the thread
        self.read_thread.join() # type: ignore
        self.read_thread = None

    def updateCamera(self):
        # This is the thread to read images from the camera
        while self.running:
            try:
                grabbed, frame = self.video_capture.read() # type: ignore
                with self.read_lock:
                    self.grabbed = grabbed
                    self.frame = frame
            except RuntimeError:
                print("Could not read image from camera")
        # FIX ME - stop and cleanup thread
        # Something bad happened

    def read(self):
        with self.read_lock:
            frame = self.frame.copy() # type: ignore
            grabbed = self.grabbed
        return grabbed, frame

    def release(self):
        if self.video_capture != None:
            self.video_capture.release()
            self.video_capture = None
        # Now kill the thread
        if self.read_thread != None:
            self.read_thread.join()


def gstreamer_pipeline(
    sensor_id=0,
    capture_width=1920,
    capture_height=1080,
    display_width=960,
    display_height=540,
    framerate=30,
    flip_method=0,
):
    """
gstreamer function to sort out gstreamer pipeline, source: https://github.com/JetsonHacksNano/CSI-Camera/blob/master/simple_camera.py
    """
    return (
        "nvarguscamerasrc sensor-id=%d ! "
        "video/x-raw(memory:NVMM), width=(int)%d, height=(int)%d, framerate=(fraction)%d/1 ! "
        "nvvidconv flip-method=%d ! "
        "video/x-raw, width=(int)%d, height=(int)%d, format=(string)BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=(string)BGR ! appsink"
        % (
            sensor_id,
            capture_width,
            capture_height,
            framerate,
            flip_method,
            display_width,
            display_height,
        )
    )



def estimatePoseSingleMarker(corners, marker_length, camera_matrix, dist_coeffs):
    """
Estimates pose of a single marker, given image coordinates and the camera coefficients.
    """
    # 3D points of marker corners in marker coordinate system
    objp = np.array([
        [-marker_length/2,  marker_length/2, 0],
        [ marker_length/2,  marker_length/2, 0],
        [ marker_length/2, -marker_length/2, 0],
        [-marker_length/2, -marker_length/2, 0]
    ], dtype=np.float32)

    # Ensure correct shape
    imgp = corners.reshape((4, 2)).astype(np.float32)

    success, rvecs, tvecs = cv2.solvePnP(
        objp,
        imgp,
        camera_matrix,
        dist_coeffs,
        flags=cv2.SOLVEPNP_IPPE_SQUARE
    )
    if not success:
        raise RuntimeError("solvePnP failed for marker")

    return rvecs, tvecs


 
def eulerFromQuaternion(x, y, z, w):
  """
  Convert a quaternion into euler angles (roll, pitch, yaw)
  roll is rotation around x in radians (counterclockwise)
  pitch is rotation around y in radians (counterclockwise)
  yaw is rotation around z in radians (counterclockwise)
  """
  t0 = +2.0 * (w * x + y * z)
  t1 = +1.0 - 2.0 * (x * x + y * y)
  roll_x = math.atan2(t0, t1)
      
  t2 = +2.0 * (w * y - z * x)
  t2 = +1.0 if t2 > +1.0 else t2
  t2 = -1.0 if t2 < -1.0 else t2
  pitch_y = math.asin(t2)
      
  t3 = +2.0 * (w * z + x * y)
  t4 = +1.0 - 2.0 * (y * y + z * z)
  yaw_z = math.atan2(t3, t4)
      
  return roll_x, pitch_y, yaw_z # in radians


def detectAndMarkMarkers(frame,corners,marker_ids,mtx,dst):
   """Function that takes in the image & detector and generates the coordinates and outputs the drawn image"""
   global coords
   
   #Set Single marker pose, only one marker in use case so no need to run this twice per call
   rvecs, tvecs = estimatePoseSingleMarker(corners,aruco_marker_side_length,mtx,dst)
   for i, marker_id in enumerate(marker_ids):
       
        
        # Store the rotation information
        rotation_matrix = np.eye(4)
        permarkerrvecs = np.array([rvecs[i][0][0],rvecs[i][1][0],rvecs[i][2][0]])
        rotation_matrix[0:3, 0:3] = cv2.Rodrigues(permarkerrvecs[i][0])[0]
        r = R.from_matrix(rotation_matrix[0:3, 0:3])
        quat = r.as_quat()   
        # Quaternion format     
        transform_rotation_x = quat[0]
        transform_rotation_y = quat[1] 
        transform_rotation_z = quat[2] 
        transform_rotation_w = quat[3] 
         
        # Euler angle format in radians
        roll_x, pitch_y, yaw_z = eulerFromQuaternion(transform_rotation_x, 
                                                       transform_rotation_y, 
                                                       transform_rotation_z, 
                                                       transform_rotation_w)
        #convert to degrees
        roll_x = math.degrees(roll_x)
        pitch_y = math.degrees(pitch_y)
        yaw_z = math.degrees(yaw_z)
        roll_x = 180 -roll_x
        
        #generate coords
        coords = np.array([roll_x,pitch_y,yaw_z])
        frame = cv2.drawFrameAxes(frame, mtx, dst, np.array(rvecs[i]), np.array(tvecs[i]), length=0.1,thickness=2)
   return(coords,frame)

def coordinatecalcs(leftcoords,rightcoords):
    """This function attempts to combine the 2 sets of coords from both cameras and find a more accurate value"""
    #Seperated as a function to make it easier to change the combination method in future
    combinedcoords = np.average(rightcoords,leftcoords)

    return(combinedcoords)
 
def main():
  """Main loop"""
  global coords
  global detector
  # Load the camera parameters from the saved file
  cv_file = cv2.FileStorage(
    camera_calibration_parameters_filename, cv2.FILE_STORAGE_READ) 
  #defines camera matrix from saved calibration file
  mtx = cv_file.getNode('K').mat()
  #defines camera distortion matrix from saved calibration file
  dst = cv_file.getNode('D').mat()
  #release file
  cv_file.release()
     
  # Only checks one dictionary, wont be an issue in chosen use case as only one dictionary will be used
  this_aruco_dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
  this_aruco_parameters = cv2.aruco.DetectorParameters()
  #instantiate global detector object, uses set dictionary and default parameters, we adjust for the provided camera properties in pose estimation function
  detector = cv2.aruco.ArucoDetector(this_aruco_dictionary,this_aruco_parameters)

  # Take in video feeds Calling gstreamer function and class twice with sensor id = 0 & 1, flip if misassigned

  Left_video_capture = CSI_Camera()
  Left_video_capture.open(
        gstreamer_pipeline(
            sensor_id=0,
            capture_width=1920,
            capture_height=1080,
            flip_method=0,
            display_width=960,
            display_height=540,
        )
    )
  Left_video_capture.start()

  Right_video_capture = CSI_Camera()
  Right_video_capture.open(
        gstreamer_pipeline(
            sensor_id=1,
            capture_width=1920,
            capture_height=1080,
            flip_method=0,
            display_width=960,
            display_height=540,
        )
    )
  Right_video_capture.start()
  
  while(True): #loops for each frame
  
   #ret is bool for if there is a valid video feed

    # read in both camera frames
    leftret,leftframe    = Left_video_capture.read()
    rightret, rightframe = Right_video_capture.read()


    if leftret and rightret == False:
      #if both cams are not loaded, exit program and output state of both feeds
      print("No video feeds detected, program will now exit LCam: {}, RCam: {}".format(str(leftret),str(rightret)))
      exit(1)
      
    # Detect In left then right feeds
    (corners, marker_ids, rejected) = detector.detectMarkers(leftframe)
    leftcoords,leftframe= detectAndMarkMarkers(leftframe,corners,marker_ids,mtx,dst)
    (corners, marker_ids, rejected) = detector.detectMarkers(rightframe)
    rightcoords,rightframe = detectAndMarkMarkers(rightframe,corners,marker_ids,mtx,dst)

    # Display the resulting combined frame
    combined_image = np.hstack((leftframe,rightframe))
    cv2.imshow(window_title,combined_image)
    
    #debug wait statement to make terminal data easier to read
    #time.sleep(0.5)
    
    # coordinate calculations

    combinedcoords = coordinatecalcs(leftcoords,rightcoords)
          
    # press q to exit capture loop
    if cv2.waitKey(1) & 0xFF == ord('q'):
      break
    elif cv2.waitKey(1) & 0xFF == ord('f'):
      #if user holds down f key then program will slow to allow reading of coordinate values
      time.sleep(0.5)
    elif cv2.waitKey(1) & 0xFF == ord('c'):
      cv2.imwrite('saved marker.png',combined_image)
      #this will only save one set of coords, which is not an issue for use case so has not been altered
      np.savetxt("marker coords.txt",combinedcoords, delimiter=',',fmt='%.3f',comments='x,y,z rotations then distance')
      print("Image taken")

  
    # Close down the video streams
    Left_video_capture.stop()
    Left_video_capture.release()
    Right_video_capture.stop()
    Right_video_capture.release()
  cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
