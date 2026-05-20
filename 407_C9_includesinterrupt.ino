// Last edit: 19/05/26
// ENGR407 DESIGN OF A ROBOTIC SYSTEM FOR BRACHYTHERAPY
// MASTER CODE FOR COMBINING ALL SENSOR DATA RETRIEVAL, SAFETY PROTOCOLS AND MOTOR CONTROL 

#include <Arduino.h>
#include <HX711.h> 

/************************ PIN DEFINITIONS **************************************************/
// Load cell pins
const int loadLED = 17;
const int DT1 = 4;
const int loadSCK1 = 3;
const int DT2 = 6;
const int loadSCK2 = 5;

// Insertion depth sensor pins
const int depthLED = 18;
const int trigPin = 10;   
const int echoPin = 11;   

// Motor pins
const int motorLED = 19;
const int stepPin = 8;
const int dirPin = 7;
const int enablePin = 9;
const int microStepPin = 14; // M1 high for 1/4 microstepping

// Switch interrupt & LEDs
const int interruptLED = 16;
const int interruptPin = 2;
const int spareLED = 15;

/************************ GLOBAL VARIABLES *************************************************/
float INSERTION_DEPTH;

// MOTOR PARAMETERS
const int STEPS_PER_REV = 400; // 1/4 Microstepping
const float mm_per_step = 3.75 / STEPS_PER_REV;
const float max_velocity = 28; // mm/s
//const float accel = 0; // mm/s^2

// PROFILE VARIABLES
float target_depth = 0;
float velocity = 0;
float force_avg = 0;

unsigned long start_time;
unsigned long last_step_time = 0;
unsigned long last_update_time = 0;
unsigned long last_print_time = 0; 
float dt = 0;

long total_steps = 0;
long steps_taken = 0;
float remaining_steps = 0;

// Volatile flag for the interrupt routine
volatile bool emergencyStopFlag = false;

// Motion states
enum MotionState {INSERT_ACCEL, INSERT_CRUISE, INSERT_DECEL, WAIT_CONFIRM, RETRACT_ACCEL, RETRACT_CRUISE, RETRACT_DECEL, STOP, EMERGENCY_STOP};
MotionState motionState = STOP;

// Procedure states
enum InputState {askDepth, waitDepth, askConfirm, waitConfirm};
InputState inputState = askDepth;
bool procedureActive = false;

// HX711 CALIBRATION
const int calibration1 = 200;
const int calibration2 = 200;

/************************ OBJECTS *********************************************************/
HX711 loadCell1;
HX711 loadCell2;

/************************ SENSOR FUNCTIONS ********************************************/
float readInsertionDepth()
{
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  const int needleLength = 20; //cm
  float duration = pulseIn(echoPin, HIGH);
  float distance = (duration*0.0343)/2;
  float depth = needleLength - distance;

  if (depth < 0) depth = 0;
  return depth; 
}

float readInsertionForce()
{
  // Read calibrated force values and calculate average in N
  float load1 = loadCell1.get_units(); 
  float load2 = loadCell2.get_units(); 
  float loadAverage = (fabs(load1 + fabs(load2)) / 2*0.00981);
  return loadAverage; 
}

/************************ STEPPER MOTOR MOVE *********************************************/
void stepMotor()
{
  digitalWrite(stepPin, HIGH);
  delayMicroseconds(5); 
  digitalWrite(stepPin, LOW);
}

/************************ INTERRUPT SERVICE ROUTINE **************************************/
void triggerEmergencyStop() 
{
  emergencyStopFlag = true;
}

/************************ INSERTION DEPTH INPUT FUNCTION *********************************/
void getNewTargetDepth() 
{
  inputState = askDepth;
  bool confirmed = false;
  
  while (!confirmed)
  {
    switch (inputState)
    {
      case askDepth:
        Serial.println("\n--- NEW PROCEDURE ---");
        Serial.println("Enter insertion depth in mm: ");
        inputState = waitDepth;
      break;

      case waitDepth:
        if (Serial.available() > 0)
        {
          target_depth = Serial.parseFloat();
          while (Serial.available() > 0) Serial.read(); 
          Serial.print("You entered: ");
          Serial.println(target_depth);
          inputState = askConfirm;
        }
      break;

      case askConfirm:
        Serial.println("Do you want to continue (yes/no)?");
        inputState = waitConfirm;
      break;

      case waitConfirm:
        if (Serial.available() > 0)
        {
          String confirmInput = Serial.readStringUntil('\n');
          confirmInput.trim();

          if (confirmInput.equalsIgnoreCase("yes"))
          {
            Serial.println("Insertion confirmed.");
            confirmed = true;
          }
          else if (confirmInput.equalsIgnoreCase("no"))
          {
            Serial.println("Procedure cancelled.");
            inputState = askDepth;
          }
          else 
          {
            Serial.print("Unrecognised input: ");
            Serial.println(confirmInput);
            inputState = askConfirm;
          }
          while (Serial.available() > 0) Serial.read(); 
        }
      break;
    }
  }

  // Reset variables for the new run
  Serial.println("time_ms,velocity_mms,position_mm,depth_mm,force_N"); 

  total_steps = target_depth / mm_per_step;
  steps_taken = 0;
  velocity = 0;
  
  // Reset emergency flags if carried from a previous state
  emergencyStopFlag = false;
  digitalWrite(interruptLED, LOW);
  
  procedureActive = true;
  motionState = INSERT_ACCEL;
  digitalWrite(enablePin, LOW); // Enable motor
  
  // Reset timers 
  start_time = millis();
  last_update_time = micros();
}

/******************************** SETUP ***********************************************/
void setup() 
{
  Serial.begin(115200); 

  // Setup motor
  pinMode(stepPin, OUTPUT);
  pinMode(dirPin, OUTPUT);
  pinMode(enablePin, OUTPUT);
  pinMode(motorLED, OUTPUT);
  digitalWrite(enablePin, LOW); 
  digitalWrite(motorLED, HIGH); 
  pinMode(microStepPin, OUTPUT);
  digitalWrite(microStepPin, HIGH);

  // Setup LED Pins
  pinMode(loadLED, OUTPUT);
  digitalWrite(loadLED, HIGH); 
  pinMode(depthLED, OUTPUT);
  digitalWrite(depthLED, HIGH); 
  pinMode(spareLED, OUTPUT);
  
  // Setup Interrupt Pin
  pinMode(interruptLED, OUTPUT);
  // INPUT_PULLUP prevents floating states
  pinMode(interruptPin, INPUT_PULLUP); 
  // Triggers when the button is pressed (voltage goes from HIGH to LOW)
  attachInterrupt(digitalPinToInterrupt(interruptPin), triggerEmergencyStop, FALLING); 

  getNewTargetDepth();
}

/******************************** LOOP ****************************************************/
void loop()
{
  // Calculate dt continuously 
  unsigned long now = micros();
  dt = (now - last_update_time) / 1000000.0;
  last_update_time = now;

  // Live sensor readings
  float DEPTH = readInsertionDepth();
  float FORCE = readInsertionForce();

  float remaining_mm = 0;
  float accel = (max_velocity*max_velocity) / (0.5*target_depth); // Acceleration profile

  // Check if interrupt is pressed
  if (emergencyStopFlag && motionState != EMERGENCY_STOP) 
  {
      motionState = EMERGENCY_STOP;
      velocity = 0;                   // Forced motor stop
      digitalWrite(enablePin, HIGH);  // Motor disabled
      digitalWrite(interruptLED, HIGH); 
      Serial.println("\n--- EMERGENCY STOP TRIGGERED ---");
      Serial.println("Motor disabled. Sensors remain active. Type 'reset' to abort procedure.");
  }

  // KINEMATIC CALCULATIONS
  switch (motionState)
  {
    case EMERGENCY_STOP:
      // Motor is disabled and velocity is 0. Steps taken is frozen.
      // State can only be reset manually via serial monitor input
      if (Serial.available() > 0)
      {
        String response = Serial.readStringUntil('\n');
        response.trim();
        response.toLowerCase();

        if (response == "reset")
        {
          Serial.println("System reset.");
          motionState = STOP;
        }
        while (Serial.available() > 0) Serial.read();
      }
      break;

    case INSERT_ACCEL: // Acceleration profile state (insertion)
      digitalWrite(dirPin, HIGH);
      remaining_steps = total_steps - steps_taken;
      remaining_mm = remaining_steps * mm_per_step;

      velocity += accel * dt;

      if (velocity >= max_velocity)
      {
        velocity = max_velocity;
        motionState = INSERT_CRUISE;
      }
      if (remaining_mm <= (velocity * velocity) / (2 * accel))
      {
        motionState = INSERT_DECEL;
      }
      break;

    case INSERT_CRUISE: // Constant velocity cruise state (insertion)
      remaining_steps = total_steps - steps_taken;
      remaining_mm = remaining_steps * mm_per_step;

      if (remaining_mm <= (velocity * velocity) / (2 * accel))
      {
        motionState = INSERT_DECEL;
      }
      break;

    case INSERT_DECEL: // Deceleration profile state (insertion)
      remaining_steps = total_steps - steps_taken;
      remaining_mm = remaining_steps * mm_per_step;

      velocity -= accel * dt;

      if (velocity <= 0 || remaining_steps <= 0)
      {
        velocity = 0;
        digitalWrite(enablePin, HIGH); // Disable motor temporarily
        Serial.println("\nInsertion complete. Type 'retract' or 'cancel'.");
        motionState = WAIT_CONFIRM;
      }
      break;

    case WAIT_CONFIRM: // Manual input typed "retract" needed
      if (Serial.available() > 0)
      {
        String response = Serial.readStringUntil('\n');
        response.trim();
        response.toLowerCase();

        if (response == "retract")
        {
          digitalWrite(enablePin, LOW); // Re-enable motor
          velocity = 0; 
          motionState = RETRACT_ACCEL;
        }
        else if (response == "cancel")
        {
          Serial.println("Procedure cancelled. Needle ready for manual retraction.");
          motionState = STOP;
        }
        while (Serial.available() > 0) Serial.read(); 
      break;
    
    case RETRACT_ACCEL: // Acceleration profile state (retraction)
      digitalWrite(dirPin, LOW);
      remaining_steps = steps_taken;
      remaining_mm = remaining_steps * mm_per_step;

      velocity -= accel * dt; // Negative velocity for retraction

      if (velocity <= -max_velocity)
      {
        velocity = -max_velocity;
        motionState = RETRACT_CRUISE;
      }

      if (remaining_mm <= (velocity * velocity) / (2 * accel)) 
      {
        motionState = RETRACT_DECEL;
      }
      break;

    case RETRACT_CRUISE: // Constant velocity cruise state (retraction)
      remaining_steps = steps_taken;
      remaining_mm = remaining_steps * mm_per_step;

      if (remaining_mm <= (velocity * velocity) / (2*accel))
      {
        motionState = RETRACT_DECEL;
      }
      break;
  
    case RETRACT_DECEL: // Deceleration profile state (retraction)
      remaining_steps = steps_taken; 
      remaining_mm = remaining_steps * mm_per_step;

      velocity += accel * dt; // Return to 0

      if (velocity >= -0.05 || steps_taken <= 0) 
      {
        velocity = 0;
        steps_taken = 0; 
        Serial.println("\nRetraction complete.");
        motionState = STOP;
      }
      break;

    case STOP:
      digitalWrite(enablePin, HIGH); // Disable motor
      procedureActive = false; 
      getNewTargetDepth(); 
      break;
  }

  // STEP GENERATION
  if (velocity != 0 && procedureActive) 
  {
      float safe_velocity = max(fabs(velocity), 0.001f); 
      unsigned long step_interval = (unsigned long)((mm_per_step / safe_velocity) * 1000000.0);

      if (micros() - last_step_time >= step_interval) 
      {
          if ((motionState <= INSERT_DECEL && steps_taken < total_steps) || 
              (motionState >= RETRACT_ACCEL && steps_taken > 0)) 
          {
              stepMotor();
              last_step_time = micros();

              if (motionState <= INSERT_DECEL) {
                  steps_taken++;
              } else {
                  steps_taken--;
              }
          }
      }
  }

  // CSV OUTPUT (Printed at 50Hz)
  if (millis() - last_print_time >= 20 && procedureActive && motionState != WAIT_CONFIRM) 
  {
    Serial.print(millis() - start_time);
    Serial.print(",");
    Serial.print(velocity, 4);           
    Serial.print(",");
    Serial.print(steps_taken * mm_per_step, 4); 
    Serial.print(",");
    
    // Print insertion depth and insertion force readings from sensors
    Serial.print(DEPTH, 4);
    Serial.print(",");
    Serial.println(FORCE, 4);
    
    last_print_time = millis();
  }
}