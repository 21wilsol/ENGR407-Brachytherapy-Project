# Closed-loop-motor-control 
This code is used to control a stepper motor along a trapezoidal motion profile for needle insertion to a specified insertion depth from manual input
to the serial monitor. The system also provides the option for retraction depending on manual input options. 
The stepper motor does not include an encoder, hence load cells and an ultrasonic sensor are used to generate closed-loop feedback during insertion. 
Two switches operate for manual override with one stopping all motion as an interrupt switch whilst power is still supplied to the motor, the second switch shuts
off power to the motor and is the primary on/off switch for activation of the device.

NOTE: This code was not used to program needle insertion for real-life insertion into human or simulated tissue. It was used for simulating insertive action 
of a telescopic end effector with a metal straw in place of the needle.

### ARDUINO SETUP
Code is written in Arduino IDE to program the Arduino Uno using C++
1. Download Arduino IDE or use the online version available
2. Ensure "Arduino Uno" board is downloaded
3. Include libraries for: HX711 load cell amplifier, and HC-SR04 (is usually included already)

### HARDWARE SETUP
Motor used is the NEMA14 stepper motor with the DRV8825 stepper driver but other NEMA steppers would work with the same code
1. Connect M1 pin of the DRV8825 driver to the 5V output of the Arduino Uno (this activates the 1/4 microstepping specified in the code, see DRV8825 datasheet
   for alternative microstepping configurations https://www.ti.com/lit/ds/symlink/drv8825.pdf)
2. Connect sensor outputs and motor pins to those specified in the code
3. Connect 12V battery input to the stepper driver inputs
4. Adjust the driver potentiometer depending on the maximum current rating of the motor (see motor datasheet)

### DEBUGGING
If testing on hardware for yourself, the potentiometer may need to be adjusted greater than the maximum motor ratings due to additional circuit impedance.
The code prints to serial monitor, however increasing print times will increase lag and hence the outputs will not generate smooth graphing.
