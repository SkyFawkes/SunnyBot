

"""Line following script with ds4 controller as supervisor
DS4  controller axis maps:
Axis0: Left stick l-r (-1 left, 1 right)
Axis1: Left stick u-d (-1 up, 1 down)
Axis2: Left trigger (-1 unpressed, 1 completely pressed)
Axis3: Right stick l-r (-1 left, 1 right)
Axis4: Right stick u-d (-1 up, 1 down)
Axis5: Right trigger (-1 unpressed, 1 completely pressed)
"""

"""Wall sensors connected to MCP3008 channels 1, 4 and 7
wall sensors connected to MCP3008 channels 1, 4 and 7
Channel 1 -> Right hand view
Channel 4 -> Forward view
Channel 7 -> Left hand view
"""

import pygame
import wiringpi
import spidev
from time import sleep
import sys
import numpy as np

#initialise DS4 controller
screen = pygame.display.set_mode([10,10]) #make a 10x10 window
pygame.joystick.init() #find the joysticks
joy = pygame.joystick.Joystick(0)
joy.init()
if(joy.get_name()=='Sony Entertainment Wireless Controller'):
    print("DS4 connected")
else:
    print("Not a DS4")
    print(joy.get_name())

"""SPI pins for MCP3008:
SCLK->CLK gpio 23
MISO->DOUT gpio 21
MOSI->DIN gpio 19
CE0->CS gpio 24
"""

Motor1PWM  = 1 # gpio pin 12 = wiringpi no. 1 (BCM 18)
Motor1AIN1 = 4 # gpio pin 16 = wiringpi no. 4 (BCM 23)
Motor1AIN2 = 5 # gpio pin 18 = wiringpi no. 5 (BCM 24)
MotorStandby = 6 # gpio pin 22 = wiringpi no. 6 (BCM 25)
Motor2PWM = 23 # gpio pin 33 = wiringpi no. 23 (BCM 13)
Motor2BIN1 = 21 # gpio pin 29 = wiringpi no. 21 (BCM 5)
Motor2BIN2 = 22 # gpio pin 31 = wiringpi no. 22 (BCM 6)

# Initialize PWM output
wiringpi.wiringPiSetup()
wiringpi.pinMode(Motor1PWM, 2)     # PWM mode
wiringpi.pinMode(Motor1AIN1, 1) #Digital out mode
wiringpi.pinMode(Motor1AIN2, 1) #Digital out mode
wiringpi.pinMode(MotorStandby, 1) #Ditial out mode

wiringpi.pinMode(Motor2PWM, 2)     # PWM mode
wiringpi.pinMode(Motor2BIN1, 1)    #Digital out mode
wiringpi.pinMode(Motor2BIN2, 1)    #Digital out mode


wiringpi.pwmWrite(Motor1PWM, 0)    # OFF
wiringpi.pwmWrite(Motor2PWM, 0)    # OFF
wiringpi.digitalWrite(Motor1AIN1, 1) #forward mode
wiringpi.digitalWrite(Motor1AIN2, 0) #forward mode
wiringpi.digitalWrite(Motor2BIN1, 1)
wiringpi.digitalWrite(Motor2BIN2, 0)
wiringpi.digitalWrite(MotorStandby, 1) #enabled

# Initialise SPI stuff
spi = spidev.SpiDev()
spi.open(0, 0) #SPI bus 0, device 0
spi.max_speed_hz = 1000000 #max speed of 1MHz

# Set Motor Speed
def motorspeed(speed1, speed2):
    if speed1 < 0:
        wiringpi.digitalWrite(Motor1AIN1, 0) #reverse mode
        wiringpi.digitalWrite(Motor1AIN2, 1)
    else:
        wiringpi.digitalWrite(Motor1AIN1, 1) #forward mode
        wiringpi.digitalWrite(Motor1AIN2, 0)

    wiringpi.pwmWrite(Motor1PWM, int(abs(speed1)*1024)) #motorspeed from 0 to 1024

    if speed2 < 0:
        wiringpi.digitalWrite(Motor2BIN1, 0) #reverse mode
        wiringpi.digitalWrite(Motor2BIN2, 1)
    else:
        wiringpi.digitalWrite(Motor2BIN1, 1) #forward mode
        wiringpi.digitalWrite(Motor2BIN2, 0)

    wiringpi.pwmWrite(Motor2PWM, int(abs(speed2)*1024)) 

# read SPI data from MCP3008 chip, 8 possible adc's (0 thru 7)
def readadc(adcnum):
        if ((adcnum > 7) or (adcnum < 0)):
                return -1
        r = spi.xfer2([1,(8+adcnum)<<4,0])
        adcout = ((r[1]&3) << 8) + r[2]
        return adcout

motorspeed(0,0) #start with zero motor speed
base_speed = 0.9 #set base speed
Kp = 0.01
#Ki = 0.0
#integral = 0.0
reference = 20.0
calibrated = 0


while True:
    motorspeed(0,0) #turn the motors off!
    pygame.event.get()   #get pygame values for reading in ds4 buttons
    triangle = joy.get_button(3)
    cross = joy.get_button(0)
    if(cross == 1):
        start = 1
    else:
        start = 0
    calibrated = 0

    while(start == 1):
#        print('Cross pressed')
        left_sensor = (readadc(7)/1024.0)*3.3 + 0.01
        right_sensor = (readadc(1)/1024.0)*3.3 + 0.01
        forward_sensor = (readadc(4)/1024)*3.3 + 0.01
        left_distance = 12.5/left_sensor - 0.42
        right_distance = 12.5/right_sensor - 0.42
        forward_distance = 12.5/forward_sensor - 0.42
#        print('Left: '+ str(left_distance)+', Right: '+str(right_distance)+', Forward: '+str(forward_distance))
        if(calibrated ==0): #follow the right wall at the distance it started at
            reference = right_distance
            calibrated = 1
            print('Calibrated at: ' + str(reference))
        if(right_distance <=30): #limits of sensor
            error = reference - right_distance
        else:
            error = left_distance - reference
#        integral = integral + error
#        if(Ki*integral > 0.1):
#            integral = 0.1/Ki
#        elif(Ki*integral < -0.1):
#            integral = -0.1/Ki
 #       print(error)
        m1_speed = base_speed - Kp*error #- Ki*integral
        m2_speed = base_speed + Kp*error #+ Ki*integral
        if(m1_speed >= 1.0):
           # m1_overshoot = m1_speed - 1.0
            m1_speed = 1.0
        elif (m1_speed <= 0.0):
           # m1_overshoot = m1_speed + 1.0
            m1_speed = 0.0
        #else
          #  m1_overshoot = 0
        if(m2_speed >= 1.0):
           # m2_overshoot = m2_speed - 1.0
            m2_speed = 1.0
        elif (m2_speed <= 0.0):
           # m2_overshoot = m2_speed + 1.0
            m2_speed = 0.0
       # else:
          #  m2_overshoot = 0
        if(forward_distance <= 30):
            motorspeed(0,0) #stop if you see a wall!
        else:
            motorspeed(m1_speed, m2_speed)
 #       print('Motor1 speed: ' + str(m1_speed) + ' Motor2 speed: ' + str(m2_speed))
        pygame.event.get()   #get pygame values for reading in ds4 buttons
        cross = joy.get_button(0)
        triangle = joy.get_button(3)
        if(triangle == 1):
            start = 0
        sleep(0.01) #limit refresh to 100Hz
