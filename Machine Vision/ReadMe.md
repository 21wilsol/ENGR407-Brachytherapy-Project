# Machine Vision

This is the ReadMe for the Machine Vision section of the report. The three files contained are:

camcalib2.py 
Pose Est Basic.py
Pose Estimate w arduino.py
dualcamposedetect.py

The three pose detection codes require a camera calibration matrix to accurately identify angles. This is referred to as matrix K in the report. The code used here is copied from https://automaticaddison.com/how-to-perform-pose-estimation-using-an-aruco-marker/. This calibration is done using a chessboard style grid of squares and inputting at least 10 images of varied pose and distance. Ensure that the variables declared at the start match the properties of the chessboard.

Once the .yaml file has been created (only one file per type of camera) the other codes can be run. Pose Est Basic is the most basic code and only supports single cameras. This will work on devices other than the jetson. If no camera is detected, try altering the input to cv2.videocapture() to 1 or 0 to try to find the correct camera.

dualcamposedetect is the code to run dual camera pose detection. This code has some issues with GStreamer and does not function properly currently however the other sections of the code have been tested individually. Ensure that the input parameters to the GStreamer function match the used cameras or it may not function properly. 

Finally, Pose estimate w arduino jetson is the code that integrates the arduino communication. This is done through serial so ensure that the baud rates used match along with ensuring any other common serial issues are not present. The arduino input function can be edited to change what is taken from the serial line, ensuring that the regex statement used is compatable.

Do note that the Jetson is quite tempermental and not all issues with the code will be repeatable or present at the time of writing.
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
