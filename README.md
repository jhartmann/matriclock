# matriclock

## Overview
matriclock is an alarm clock written in Micropython for Raspberry Pi Pico W.
See video on [Youtube](https://youtu.be/pl6CCcmThhM)


## Features
 - Time synchronization via [worldtimeapi.org](https://worldtimeapi.org)
 - Time display in 12-hour clock or 24-hour clock format
 - Alarm clock with an infinite number of alarm times
 - Alarm on/off
 - Snooze function
 - Displaying day of week and day of month
 - Displaying temperature (°C or °F) and relative humidity
 - Display off / standby mode


## Software prerequisites
 - Download and install recent Micropython firmware from (https://micropython.org/download/rp2-pico-w/)
 - Download MAX7219 driver (max7219.py) from mcauser on github from (https://github.com/mcauser/micropython-max7219)
 - Edit settings in config.py
 - Copy main.py, config.py, and max7219.py to your Raspberry Pi Pico in Bootloader mode


## Remark: Unreliable time 
In my home WLAN network, the connection to wifi is established exactly every second time the clock is started (connected to the power supply). I don't know whether this bevahiour has to do with my network, my hardware, or with the micropython firmware.


## Parts
|Count|Part                                           |
|-----|-----------------------------------------------|
|1    |Raspberry Pi Pico WH Microcontroller           |
|1    |8x32 LED Matrix Display MAX7219                |
|3    |Buttons                                        |
|1    |DHT-22 Sensor                                  |
|4    |Resistors 10k (3 pull-down for the buttons, 1 pull-up for the DHT-22 sensor)|
|1    |Piezo buzzer, active                           |


## Pinout
|Part       |Connection |RPi Pico |Connection|
|-----------|-----------|---------|----------|
|Button bn0 |S0         |27       |GP21      |
|           |S1         |36       |3V3(OUT)  |
|           |10k        |28       |GND       |
|Button bn1 |S0         |29       |GP22      |
|           |S1         |36       |3V3(OUT)  |
|           |10k        |28       |GND       |
|Button bn2 |S0         |32       |GP27      |
|           |S1         |36       |3V3(OUT)  |
|           |10k        |28       |GND       |
|Buzzer     |S          |34       |GP28      |
|           |+          |36       |3V3(OUT)  |
|           |-          |23       |GND       |
|Matrix LED |CLK        |24       |GP18      |
|           |DIN        |25       |GP19      |
|           |CS         |22       |GP17      |
|           |VCC        |40       |VBUS      |
|           |GND        |23       |GND       |
|DHT22      |DATA       |19       |GP14      |
|           |VCC        |36       |3V3(OUT)  |
|           |GND        |23       |GND       |

Buttons: Connect S0 to GPIO, S1 to 3V3, and place 10KΩ pull-down resistors between GND and each GPIO.
DHT22: Place a 10KΩ pull-up resistor between VCC and DATA of DHT22.


