# ENGR407-Brachytherapy-Project
This repository includes all code used for an ENGR407 Master's project at Lancaster University for a Brachytherapy robotic system. The project focusses on precise needle placement for insertion into single or multilayer tissue, radiation shielding and simulation, and the use of machine vision to determine needle insertion location for treatment. 
*************************************************************************************************************************************************************
### FILE NAVIGATION
The project is separated into Radiation, Machine Vision and Control System code files.
Please see the README files in the respective folders for the setup and implementation of each category.

### FILES OVERVIEW
RADIATION: Contains all files used for simulating radiation emmission and the effectiveness of different materials for radiation shielding.
           Contains radiation exposure simulations for the complete robotic arm and end effector system.
           All simulations can be run on a PC.

MACHINE VISION: Contains all files used for programming the NVIDIA Jetson PC and using machine vision for image detection using ArUco markers.
                Includes communication with a third party robotic arm (Yaskawa Cobot HC20SDTP). 

CONTROL SYSTEM: Contains all files used to program an Arduino Uno to control a NEMA14 stepper motor for end effector movement. 
                Includes closed-loop feedback from a HX711 load cell amplifier for a 5kg load cell and HC-SR04 ultrasonic sensor to determine 
                insertion force and depth, respectively.

FORWARD KINEMATICS: Contains MATLAB code to determine the position of the end effector of the Yaskawa Cobot HC20SDTP robotic arm.
