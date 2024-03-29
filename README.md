# matriclock
![matriclock (01)](matriclock_01.jpg)

## Overview
matriclock is an alarm clock written in Micropython for Raspberry Pi Pico W.  
See video on [Youtube](https://youtu.be/ngEsFX9NxQA).

## Features
 - Time synchronization via [worldtimeapi.org](https://worldtimeapi.org)
 - Time display in 12-hour clock or 24-hour clock format
 - Alarm clock with an infinite number of alarm times
 - Alarm on/off
 - Snooze function
 - Displaying day of week and day of month
 - Displaying temperature (°C or °F) and relative humidity (optional)
 - Display off / standby mode


## Software prerequisites and installation
 - Download and install recent Micropython firmware from [micropython.org](https://micropython.org/download/rp2-pico-w/)
 - Download `max7219.py` from mcauser on [github](https://github.com/mcauser/micropython-max7219)
 - Customise `config.py` to your needs
 - Set your Raspberry Pi Pico W to Bootloader mode
 - Copy all Python files of this project and `max7219.py` to it


## Parts
|Count|Part                                           |
|-----|-----------------------------------------------|
|1    |Raspberry Pi Pico WH Microcontroller           |
|1    |8x32 LED Matrix Display MAX7219                |
|3    |Buttons                                        |
|1    |DHT-22 Sensor (optional)                       |
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
|           |10kΩ       |28       |GND       |
|Button bn2 |S0         |32       |GP27      |
|           |S1         |36       |3V3(OUT)  |
|           |10kΩ       |28       |GND       |
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

Buttons: Connect S0 to GPIO, S1 to 3V3, and place 10kΩ pull-down resistors between GND and the corresponding GPIO pin.  
DHT22: Place a 10kΩ pull-up resistor between VCC and DATA of DHT22.  

You can leave out the DHT22 sensor if you don't need the temperature/humidity display. Please also set `use_dht_sensor = False` in this case.

## Operation

Press bn1 to toggle between time display and standby mode.  
Press bn0 to toggle between time display, date display, and temperature/humidity display.  
Press bn2 to toggle alarm on/off during time display.  
Alarm: Press bn1 for snooze mode, or press bn2 to stop the alarm.  
