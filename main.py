
from machine import PWM, Pin, Timer
import time
import math
import network
import sys
import micropython
from dht import DHT22

#referred files:
from config import Settings
from debounce import Button
from alarmhandler import AlarmHandler
from display import DisplayHandler, Wheel
from timesync import TimeSync

class MatriClock:  # *****************************************************************************************************************

    def __init__(self):

        self._hdisp = DisplayHandler()
        self._dht22 = DHT22(Pin(14, Pin.IN, Pin.PULL_UP))
        self.rtc = machine.RTC()
        self._timesync = TimeSync(self.rtc)
        
        self.rtc.datetime((2022, 1, 1, 6, 12, 0, 0, 0))

        self.bn0 = 21  # left
        self.bn1 = 22  # middle
        self.bn2 = 27  # right

        self._ids = [self.bn0, self.bn1, self.bn2]

        self._alarm_dt = None

        self.alh = AlarmHandler(self.rtc)
        self.alarm_enabled = True

        self._mode = 'None'
        self._mode_before = 'None'

        self.abuzzer = Pin(28, Pin.OUT)

        buttons = []
        for id in self._ids:
            buttons.append(Button(id, self.bn_hdl))

        self._buttons = tuple(buttons)

        if Settings.language == 'de':
            self._weekday_chars = (
                (13, 15),
                (11, 14),
                (13, 14),
                (11, 15),
                (12, 16),
                (14, 11),
                (14, 15))

        elif Settings.language == 'en':
            self._weekday_chars = (
                (13, 15),
                (15, 17),
                (16, 12),
                (15, 13),
                (12, 16),
                (14, 11),
                (14, 17))

    def my_round(self, n, ndigits):
        # Necessary because Python 3 is rounding using round-to-even according to IEE754
        # See https://stackoverflow.com/questions/18473563/python-incorrect-rounding-with-floating-point-numbers
        part = n * 10 ** ndigits
        delta = part - int(part)
        # always round "away from 0"
        if delta >= 0.5 or -0.5 < delta <= 0:
            part = math.ceil(part)
        else:
            part = math.floor(part)
        return part / (10 ** ndigits) if ndigits >= 0 else part * 10 ** abs(ndigits)

    # Extract JSON from HTTP response:

    def _set_mode(self, value):
        if value != self._mode:
            self._mode_before = self._mode
            print('mode:', self._mode, '>>', value)
            self._mode = value
            if value == 'clock':
                self.mode_clock()

            elif value == 'buttontest':
                self.mode_buttontest()

            elif value == 'standby':
                self.mode_standby()

            elif value == 'temp':
                self.mode_temp()

            elif value == 'date':
                self.mode_date()

    def _get_mode(self):
        return self._mode

    mode = property(_get_mode, _set_mode)

    def _set_alarm_enabled(self, value):
        self.alh.enabled = value        
        self._hdisp.alarm_enabled = value
                
    def _get_alarm_enabled(self):
        return self.alh.enabled

    alarm_enabled = property(_get_alarm_enabled, _set_alarm_enabled)

    def mode_temp(self):
        if self.mode == 'temp':
            self._dht22.measure()
            print("temperature=" + str(self._dht22.temperature()))
            print("humidity=" + str(self._dht22.humidity()))

            if Settings.temperature_unit == 'C':
                temp = int(self.my_round(self._dht22.temperature(), 0))
            elif Settings.temperature_unit == 'F':
                temp = int(self.my_round(self._dht22.temperature() * 1.8 + 32, 0))
            
            if temp > 99:
                temp = 99

            t1 = temp // 10
            t0 = temp % 10

            humidity = int(self.my_round(self._dht22.humidity(), 0))
            if humidity > 99:
                humidity = 99

            h1 = humidity // 10
            h0 = humidity % 10

            if t1 == 0:
                t1 = 10

            chars = [t1, t0, 2, h1, h0]
            self._hdisp.wheels_move_to(chars, show_alarm_enabled=False, show_time_sync_failed=False)

    def mode_date(self):
        if self.mode == 'date':
            now_rtcdt = self.rtc.datetime()
            day = now_rtcdt[2]
            weekday = now_rtcdt[3]

            d1 = day // 10
            d0 = day % 10

            wdc = self._weekday_chars[weekday]

            chars = [wdc[0], wdc[1], 0, d1, d0]
            self._hdisp.wheels_move_to(chars, show_alarm_enabled=False, show_time_sync_failed=False)

    def mode_standby(self):
        self._hdisp.wheels_move_to([10, 10, 0, 10, 10], show_alarm_enabled=False, show_time_sync_failed=False)

    def mode_buttontest(self):
        print("mode_buttontest()")
        pos = ((5, 0), (5, 6), (15, 3), (25, 0), (25, 6))

        self._hdisp.disp.fill(0)
        for bnid in range(0, 5):
            if self._buttons[bnid].value():
                self._hdisp.disp.rect(pos[bnid][0], pos[bnid][1], 2, 2, 1)

        self._hdisp.show()

    def mode_clock(self):
        if self.mode == 'clock':

            now_rtcdt = self.rtc.datetime()

            self._hdisp.set_brightness_from_time(now_rtcdt)

            hours = now_rtcdt[4]
            minutes = now_rtcdt[5]

            h1 = hours // 10
            h0 = hours % 10

            m1 = minutes // 10
            m0 = minutes % 10

            if h1 == 0 and not Settings.leading_zero:
                h1 = 10

            self._hdisp.wheels_move_to([h1, h0, 1, m1, m0], show_alarm_enabled=True, show_time_sync_failed=True)

    def wificonnect(self):
        print("wificonnect()...")
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(False)
        self.wlan.active(True)
        
        if not Settings.network_use_dhcp:
            self.wlan.ifconfig((Settings.network_ipaddress,
                Settings.network_subnetmask,
                Settings.network_gateway,
                Settings.network_dnsserver))

        self.wlan.connect(Settings.wifi_ssid, Settings.wifi_password)

        print("ifconfig=", self.wlan.ifconfig())
        
        passes = 0
        cont = True
        while cont:
            passes += 1
            cont = not self.wlan.isconnected() and passes < 30
            print("WLAN: Waiting to connect, pass " + str(passes) +
                  ", status=" + str(self.wlan.status()) + ", isconnected()=" + str(self.wlan.isconnected()))
            time.sleep(0.5)

    def beep(self, duration_s):
        self.abuzzer.value(1)
        time.sleep(duration_s)
        self.abuzzer.value(0)

    def beepnum(self, count):
        for nr in range(0, count):
            self.beep(0.03)
            time.sleep(0.15)

    def selftest(self):
        self._hdisp.disp.fill(1)
        self._hdisp.disp.show()
        self.beep(0.05)
        time.sleep(1)
        self._hdisp.disp.fill(0)
        self._hdisp.disp.show()

    def PinId(self, pin):
        return int(str(pin)[4:6].rstrip(","))

    def _get_button(self, pin):
        for button in self._buttons:
            if button.pin == pin:
                return button
        return None

    def speedtest(self):
        start = time.ticks_ms()
        self._hdisp.wheels_move_to([0, 0, 0, 0, 0], show_alarm_enabled=True, show_time_sync_failed=True)
        self._hdisp.wheels_move_to([5, 5, 0, 5, 5], show_alarm_enabled=True, show_time_sync_failed=True)
        end = time.ticks_ms()
        print("stopwatch", end-start)

    def start(self):
        self.buttons_enabled = False
        self.selftest()
        self.mode = 'clock'
        self.buttons_enabled = True
        self.minute_loop()

    def sleep_until_second(self, second):
        rtcdt = self.rtc.datetime()
        sleep_seconds = second-rtcdt[6]
        if sleep_seconds <= 0:
            sleep_seconds = 60 + sleep_seconds
        print("sleeping for " + str(sleep_seconds) + " seconds...")
        for secs in range(0, sleep_seconds):
            if self.alh.alarm_reached:
                if self.alh.alarm_auto_stop_reached:
                    self.alh.snooze_stop()
                else:
                    self.beepnum(4)
                    time.sleep(0.4)
            else:
                time.sleep(1)

    def minute_loop(self):
        while True:
            rtcdt = self.rtc.datetime()
            print("minute_loop at " +
                  str(rtcdt[4]) + ":" + str(rtcdt[5]) + ":" + str(rtcdt[6]))
            # Sync time if it hasn't been synced before or if it is after 2 a.m. and the last sync is a day ago:
            if self._timesync.necessary:
                print(self._timesync.synced_last_rtcdt, rtcdt)
                self.wificonnect()
                self._timesync.time_sync()
                self._hdisp.time_sync_failed = not self._timesync.synced
                self.alh.set_alarm_next_rtcdt()
                
            self.mode_clock()

            if self.alh.alarm_next_remaining_seconds() <= 1:
                self.alh.snooze_first()
                self.mode = 'clock'

            self.sleep_until_second(0)

            if self.mode == 'temp':
                self.mode_temp()  # refresh temperature and humidity display

    def bn_hdl(self, pin):
        if self.buttons_enabled and not self._hdisp.playing:

            button = self._get_button(pin)
            button.register_value()

            if button.value_changed() and button.value():
                self.beep(0.001)
                print("alarm = " + str(self.alh.alarm_reached), ", button.id = " +
                      str(button.id) + ", mode = " + self.mode)

                if self.alh.alarm_reached:
                    if button.id == self.bn1 and self.mode in ('clock', 'standby', 'date', 'temp'):
                        self.alh.snooze_next()
                    elif button.id == self.bn2 and self.mode in ('clock', 'standby'):
                        self.alh.snooze_stop()
                else:
                    if button.id == self.bn0:
                        if self.mode in ('clock', 'standby'):
                            self.action_date()
                        elif self.mode == 'date' and Settings.use_dht_sensor:
                            self.action_temp()
                        elif self.mode == 'temp' or (self.mode == 'date' and not Settings.use_dht_sensor):
                            self.action_clock()
                    elif button.id == self.bn1:
                        if self.mode == 'standby':
                            self.action_clock()
                        elif self.mode in ('clock', 'date', 'temp'):
                            self.action_standby()
                    elif button.id == self.bn2:
                        if self.mode == 'clock':
                            self.action_alarm_toggle()

    def action_alarm_toggle(self):
        self.alarm_enabled = not self.alarm_enabled
        self._hdisp.refresh()

    def action_clock(self):
        self.mode = 'clock'

    def action_temp(self):
        self.mode = 'temp'

    def action_date(self):
        self.mode = 'date'

    def action_standby(self):
        self.mode = 'standby'


# ---------------- Main program ----------------

MatriClock().start()
