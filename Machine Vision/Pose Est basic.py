
from __future__ import print_function # Python 2/3 compatibility
import cv2 # Import the OpenCV library
import numpy as np # Import Numpy library
from scipy.spatial.transform import Rotation as R
import math # Math library
import time
# from nanocamera import Camera

#define the aruco marker size and where the yaml file is
aruco_marker_side_length = 0.055
camera_calibration_parameters_filename = 'calibration_chessboard.yaml'
#set up arduino

coords =[0,0,0,0]

#gstreamer def
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
Replaces opencv contribs estimatepose single marker due to that modules conflict with jetson. Outputs are slightly different(1x3 not 3x1 and not np arrays)
    """

    # Create the matrix of marker points to map the measured corners to
    objp = np.array([
        [-marker_length/2,  marker_length/2, 0],
        [ marker_length/2,  marker_length/2, 0],
        [ marker_length/2, -marker_length/2, 0],
        [-marker_length/2, -marker_length/2, 0]
    ], dtype=np.float32)
   

    
    imgp = corners[0].reshape((4, 2)).astype(np.float32)

    success, rvecs, tvecs = cv2.solvePnP(
        objp,
        imgp,
        camera_matrix,
        dist_coeffs,
        flags=cv2.SOLVEPNP_IPPE_SQUARE
    )
    # Raise exception if the solvepnp fails
    if not success:
        raise RuntimeError("solvePnP failed for marker")

       

    return rvecs, tvecs


 
def euler_from_quaternion(x, y, z, w):
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


 
def main():
  """Main loop"""
  global coords
#  Main loop
  # Load the camera parameters from the saved file
  cv_file = cv2.FileStorage(
    camera_calibration_parameters_filename, cv2.FILE_STORAGE_READ) 
  #defines camera matrix from saved calibration file
  mtx = cv_file.getNode('K').mat()
  #defines camera distortion matrix from saved calibration file
  dst = cv_file.getNode('D').mat()
  cv_file.release()
     
  # Only checks one dictionary, wont be an issue for assumed use case
  this_aruco_dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
  this_aruco_parameters = cv2.aruco.DetectorParameters()
  #instantiate detector object, uses set dictionary and parameters as default, we adjust for the provided camera properties later in the code
  detector= cv2.aruco.ArucoDetector(this_aruco_dictionary,this_aruco_parameters)
   
  #Take in video feed, 0 is systsem default camera, use top for csi and bot for webcam
  #video_capture = cv2.VideoCapture(gstreamer_pipeline(flip_method=0), cv2.CAP_GSTREAMER)
  cap = cv2.VideoCapture(0)
   
  while(True): #loops for each frame
  
   #ret is bool for if there is a valid video feed
    ret, frame = cap.read()  
    if ret == False:
      print("Video feed not detected, program will now exit")
      exit(1)
      
      
    # Detect ArUco markers in the video frame
    (corners, marker_ids, rejected) = detector.detectMarkers(
      frame)
    
    # Check that at least one ArUco marker was detected
    if marker_ids is not None:
 
      # Draw a square around detected markers in the video frame
      # Would need to read in the arduino data here
      # Possibly a wait statement to 
      cv2.aruco.drawDetectedMarkers(frame, corners, marker_ids,borderColor=(0,0,255))
       
      # Get the rotation and translation vectors
      rvecs, tvecs = estimatePoseSingleMarker(
        corners,
        aruco_marker_side_length,
        mtx,
        dst)
         
      # Print the pose for the ArUco marker
      # The pose of the marker is with respect to the camera lens frame.
      # Imagine you are looking through the camera viewfinder, 
      # the camera lens frame's:
      # x-axis points to the right
      # y-axis points straight down towards your toes
      # z-axis points straight ahead away from your eye, out of the camera
      for i, marker_id in enumerate(marker_ids):
       
        # Store the translation (i.e. position) information
        transform_translation_x = tvecs[0][0]
        transform_translation_y = tvecs[1][0]
        transform_translation_z = tvecs[2][0]
 
        # Store the rotation information
        rotation_matrix = np.eye(4)
        permarkerrvecs = np.array([rvecs[0][0],rvecs[1][0],rvecs[2][0]])
        rotation_matrix[0:3, 0:3] = cv2.Rodrigues(permarkerrvecs)[0]
        r = R.from_matrix(rotation_matrix[0:3, 0:3])
        quat = r.as_quat()   
         
        # Quaternion format     
        transform_rotation_x = quat[0] 
        transform_rotation_y = quat[1] 
        transform_rotation_z = quat[2] 
        transform_rotation_w = quat[3] 
         
        # Euler angle format in radians
        roll_x, pitch_y, yaw_z = euler_from_quaternion(transform_rotation_x, 
                                                       transform_rotation_y, 
                                                       transform_rotation_z, 
                                                       transform_rotation_w)
        #convert to degrees
        roll_x = math.degrees(roll_x)
        pitch_y = math.degrees(pitch_y)
        yaw_z = math.degrees(yaw_z)
        roll_x = 180 -roll_x
        #print out to the terminal
        #roll is technically backwards but fixing properly would not be worth the effort
        #generate coords
        coords = np.array([roll_x,pitch_y,yaw_z])
      
         
        # Draw the axes on the marker
        cv2.drawFrameAxes(frame, mtx, dst, np.array(rvecs), np.array(tvecs), length=0.1,thickness=2)
        #save the detected marker as a picture for debugging purposes
        # cv2.imwrite('detectmarker.png',frame)
     
    # Display the resulting frame
    cv2.imshow('frame',frame)
    #debug wait statement to make terminal data easier to read
    #time.sleep(0.5)
    
    # press q to exit capture loop
    if cv2.waitKey(1) & 0xFF == ord('q'):
      break
    elif cv2.waitKey(1) & 0xFF == ord('f'):
      #if user holds down f key then program will slow to allow reading of coordinate values
      time.sleep(0.5)
    elif cv2.waitKey(1) & 0xFF == ord('c'):
      cv2.imwrite('saved marker.png',frame)
      #this will only save one set of coords, which is not an issue for use case so has not been altered
      np.savetxt("marker coords.txt",coords, delimiter=',',fmt='%.3f',comments='x,y,z rotations then distance')
      print("Image taken")

  
  # Close down the video stream
  cap.release()
  cv2.destroyAllWindows()
main()
