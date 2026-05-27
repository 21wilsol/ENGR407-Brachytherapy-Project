This is the ReadMe for the Machine Vision section of the report. The three files contained are:

camcalib2.py 
Pose Est Basic
Pose Estimate w arduino 
dualcamposedetect.py

The three pose detection codes require a camera calibration matrix to accurately identify angles. This is referred to as matrix K in the report. The code used here is copied from https://automaticaddison.com/how-to-perform-pose-estimation-using-an-aruco-marker/. This calibration is done using a chessboard style grid of squares and inputting at least 10 images of varied pose and distance. Ensure that the variables declared at the start match the properties of the chessboard.

Once the .yaml file has been created (only one file per type of camera) the other codes can be run. Pose Est Basic is the most basic code and only supports single cameras. This will work on devices other than the jetson. If no camera is detected, try altering the input to cv2.videocapture() to 1 or 0 to try to find the correct camera.


Libraries required:

Numpy
OpenCV2
glob
matplotlib
scipy
math
time
threading
charset_normalizer

DO NOT INSTALL OPENCV onto the Jetson device, it is already installed and reinstalling will interfere with some Jetson specific configurations that will cause GStreamer to malfunction.
