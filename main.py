from machine import PWM, Pin, SPI, Timer
import time
import math
import max7219
import json
import network
import sys
import urequests
import micropython
from dht import DHT22
from config import settings # this is the 'settings' class in the file 'config.py'

class Button:  # *****************************************************************************************************************

    def __init__(self, id, handler):

        self.pin = Pin(id, Pin.IN)
        self.pin.irq(trigger=machine.Pin.IRQ_RISING |
                     machine.Pin.IRQ_FALLING, handler=handler)
        self._id = id
        self._debounce_time_ms = 200
        self._value_before = 0
        self._value = 0
        self._pin_value = 0
        self._pin_value_before = 0
        self._value_changed_time = 0
        self._value_changed_time_first = -1
        self.buttons_enabled = True

    def register_value(self):
        # call this at the beginning of the button callback function to let
        # the button object register state changes and to debounce it
        self._pin_value_before = self._pin_value
        self._pin_value = self.pin.value()

        if self._pin_value != self._pin_value_before:
            self._value_changed_time = time.ticks_ms()
            if self._value_changed_time_first == 0:
                self._value_changed_time_first = self._value_changed_time
                self._value_before = self._value
                self._value = self._pin_value
            elif self._value_changed_time - self._value_changed_time_first > self._debounce_time_ms:
                self._value_before = self._value
                self._value = self._pin_value
                self._value_changed_time_first = 0

    def get_id(self):
        return self._id

    def value_changed(self):
        return self._value_before != self._value

    id = property(get_id)

    def value(self):
        self._value_before = self._value
        return self._value


class AlarmHandler:  # *****************************************************************************************************************

    def __init__(self, rtc):

        self.rtc = rtc

        self._alarm_next_rtcdt = None
        self._enabled = True
        self._alarm_count = 0
        self._snooze_alarm_ticks_ms = 0  # Ticks when the snooze alarm is raised

        self._alarms = settings.alarms

        # rtc format:
        #  0     1      2    3    4     5       6       7
        # (year, month, day, dow, hour, minute, second, ms=0)
        # time format:
        #  0     1      2         3     4       5       6        7
        # (year, month, day,      hour, minute, second, weekday, yearday)

    def snooze_next(self):
        seconds_now = self.rtc.datetime()[6]
        if seconds_now < 30:
            msec_diff = seconds_now * -1000
        else:
            msec_diff = seconds_now * 1000

        self._snooze_alarm_ticks_ms = time.ticks_ms() + settings.snooze_time_m * \
            60000 + msec_diff
        self._alarm_count += 1
        self.set_alarm_next_rtcdt()

    def snooze_first(self):
        self._snooze_alarm_ticks_ms = time.ticks_ms()
        self.set_alarm_next_rtcdt()

    def snooze_stop(self):
        self._snooze_alarm_ticks_ms = 0  # = disabled
        self.set_alarm_next_rtcdt()

    def get_alarm(self):
        # Alarm or snooze time is reached
        return time.ticks_ms() > self._snooze_alarm_ticks_ms > 0

    alarm = property(get_alarm)

    def _get_enabled(self):
        return self._enabled

    def _set_enabled(self, value):
        print("alarm enabled: " + str(self._enabled) + " -> " + str(value))
        self._enabled = value
        if value:
            self.snooze_stop()

    enabled = property(_get_enabled, _set_enabled)

    def alarm_remaining_seconds(self, alarm_rtcdt):
        now_rtcdt = self.rtc.datetime()
        diff_dow = self._diff_dow(now_rtcdt, alarm_rtcdt)

        ret = diff_dow * 86400 + \
            self.midnight_elapsed_seconds(
                alarm_rtcdt) - self.midnight_elapsed_seconds(now_rtcdt)

        return ret

    def alarm_next_remaining_seconds(self):
        if self._enabled:
            ret = self.alarm_remaining_seconds(self._alarm_next_rtcdt)
        else:
            ret = 999999

        print("alarm_next_remaining_seconds=" + str(ret))
        return ret

    def diff_seconds_dt(self, first_dt, second_dt):
        first_mk = time.mktime(first_dt)
        second_mk = time.mktime(second_dt)
        return second_mk-first_mk

    def midnight_elapsed_seconds(self, rtcdt):
        ret = rtcdt[6] + rtcdt[5]*60 + rtcdt[4]*3600
        return ret

    def set_alarm_next_rtcdt(self):
        now_rtcdt = self.rtc.datetime()
        diff_dow_min = 8  # init dummy value
        for alarm in self._alarms:
            alarm_rtcdt = [-1, -1, -1, alarm[0], alarm[1],
                           alarm[2], 0, 0]  # convert to pseudo RTC datetime

            diff_dow = self._diff_dow(now_rtcdt, alarm_rtcdt)
            # if the next alarm is today, then we have to check if it is elapsed already
            if (diff_dow > 0 or (diff_dow == 0 and self.midnight_elapsed_seconds(alarm_rtcdt) > self.midnight_elapsed_seconds(now_rtcdt))) \
                    and diff_dow < diff_dow_min:
                self._alarm_next_rtcdt = alarm_rtcdt
                diff_dow_min = diff_dow

        print("alarm_next_rtcdt=" + str(self._alarm_next_rtcdt))
        return self._alarm_next_rtcdt

    def _diff_dow(self, val1, val2):

        if val1[3] <= val2[3]:
            ret = val2[3]-val1[3]
        else:
            ret = val2[3] + 7-val1[3]

        return ret


class DisplayHandler:  # *****************************************************************************************************************

    def __init__(self):
        spi = SPI(0, sck=Pin(18), mosi=Pin(19))
        cs = Pin(17, Pin.OUT)
        self.disp = max7219.Matrix8x8(spi, cs, 4)
        self.disp.brightness(0)

        if settings.display_inverse:
            self.fg_col = 0
            self.bg_col = 1
        else:
            self.fg_col = 1
            self.bg_col = 0

        self.clear()
        self.show()

        self._row_seconds = 0.01
        self._brightness = 99  # uninitialized

        self._show_colon = False
        self._show_alarm_enabled = False
        self._alarm_enabled = False

        self._show_time_sync_failed = False
        self._time_sync_failed = True

        # characters can be designed with LED matrix editor on
        # https://xantorohara.github.io/led-matrix-editor/#

        # 0 1 2 3 4 5 6 7 8 9 (space) (0-10)
        self._char_matrix_digits = [
            0x1e3333333333331e,
            0x1818181818181e18,
            0x3f03060c1830331e,
            0x1e3330301c30331e,
            0x303030303f333336,
            0x1e3330301f03033f,
            0x1e3333331f03331e,
            0x0c0c0c0c0c18303f,
            0x1e3333331e33331e,
            0x1e3330303e33331e,
            0x0000000000000000]

        self._char_matrix_colon = [
            0x0000000000000000,
            0x0000030300030300,
            0x0000000000000303]

        # D F M S T W (#11-#16)
        self._char_matrix_weekday_0 = [
            0x1f3333333333331f,
            0x030303031f03033f,
            0x333333333f3f3321,
            0x1e3330301e03331e,
            0x0c0c0c0c0c0c0c3f,
            0x21333f3f33333333]

        # a e h i o r u
        self._char_matrix_weekday_1 = [
            0x3e33333e301e0000,
            0x1e33031f331e0000,
            0x333333331f030303,
            0x0606060606000600,
            0x1e3333331e000000,
            0x060606061e000000,
            0x3e33333333000000]

        # You can use uppercase characters if you like (FR instead of Fr)
        # Just exchange _char_matrix_weekday_1 above with the following matrix:
        '''
        # A E H I O R U (#11-16)
        self._char_matrix_weekday_1 = [
              0x333333333f33331e,
              0x3f0303031f03033f,
              0x333333333f333333,
              0x0c0c0c0c0c0c0c0c,
              0x1e3333333333331e,
              0x333333331f33331f,
              0x1e33333333333333]
        '''

        self.wheels = (
            wheel(self, x=0,  width=6, char_matrix=self._char_matrix_digits +
                  self._char_matrix_weekday_0, order=settings.order),
            wheel(self, x=7,  width=6, char_matrix=self._char_matrix_digits +
                  self._char_matrix_weekday_1, order=settings.order),
            wheel(self, x=14, width=2,
                  char_matrix=self._char_matrix_colon, order=settings.order),
            wheel(self, x=17, width=6,
                  char_matrix=self._char_matrix_digits, order=settings.order),
            wheel(self, x=24, width=6,
                  char_matrix=self._char_matrix_digits, order=settings.order)
        )

        self.wheel_count = len(self.wheels)

    def wheels_move_to(self, chars, show_alarm_enabled, show_time_sync_failed):
        self._show_alarm_enabled = show_alarm_enabled
        self._show_time_sync_failed = show_time_sync_failed
        print("wheels_move_to", chars)
        print("wm _show_time_sync_failed", self._show_time_sync_failed)

        # Move digit wheels 0-3:
        for dpos in range(0, self.wheel_count):
            self.wheels[dpos].frame_move_to(chars[dpos])

        self.play()

    def play(self):
        motion = True
        while motion:
            motion = False
            self.clear()
            self.draw_info()
            self.draw_time_sync_failed()

            for dpos in range(0, self.wheel_count):
                motion = self.wheels[dpos].draw_next() or motion

            self.show()
            time.sleep(self._row_seconds)

    def draw_info(self):
        if self.alarm_enabled and self._show_alarm_enabled:
            self.disp.pixel(31, 7, self.fg_col)

    def draw_time_sync_failed(self):
        print("self.time_sync_failed", self.time_sync_failed)
        print("self._show_time_sync_failed", self._show_time_sync_failed)
        if self.time_sync_failed and self._show_time_sync_failed:
            self.disp.vline(31, 0, 3, self.fg_col)
            self.disp.pixel(31, 4, self.fg_col)

    def refresh(self):
        self.clear()
        self.draw_info()
        self.draw_time_sync_failed()
        for dpos in range(0, self.wheel_count):
            self.wheels[dpos].refresh()
        self.show()

    def draw_character(self, chr, x):
        for row in range(0, 8):
            self. draw_character_row(chr, x, row, row, 8)

    def draw_character_row(self, chr, x, y, char_row, width=6):
        if char_row >= 0:
            val_col = (self._char_matrix[chr] >> 8 * char_row) & 0xFF
            for col in range(0, width):
                if 1 << col & val_col:
                    self.disp.pixel(x + col, y, self.fg_col)

    def show(self):
        self.disp.show()

    def _set_brightness(self, value):
        if self._brightness != value:
            self.disp.brightness(value)
            print("brightness: " + str(self._brightness) + " -> " + str(value))
            self._brightness = value

    def _get_brightness(self):
        return self._brightness

    brightness = property(_get_brightness, _set_brightness)

    def set_brightness_from_time(self, rtcdt):
        month = rtcdt[1]
        hour = rtcdt[4]

        sunrise, sunset = settings.sunrisesunset[month-1]

        if sunrise <= hour < sunset:
            self.brightness = settings.brightness_day
        else:
            self.brightness = settings.brightness_night

    def ticker(self, text):
        t = text + "    "
        for x in range(32, len(t)*-8, -1):
            self.clear()
            self.disp.text(t, x, 0, self.fg_col)
            self.disp.show()
            time.sleep(self._row_seconds)

    def clear(self):
        self.disp.fill(self.bg_col)

    def text(self, text, x, y):
        self.disp.text(text, x, y, self.fg_col)

    def _get_show_colon(self):
        return self._show_colon

    show_colon = property(_get_show_colon)

    def _set_alarm_enabled(self, value):
        self._alarm_enabled = value

    def _get_alarm_enabled(self):
        return self._alarm_enabled

    alarm_enabled = property(
        _get_alarm_enabled, _set_alarm_enabled)


    def _set_time_sync_failed(self, value):
        self._time_sync_failed = value

    def _get_time_sync_failed(self):
        return self._time_sync_failed

    time_sync_failed = property(
        _get_time_sync_failed, _set_time_sync_failed)

class wheel:

    def __init__(self, hdisp, x, width, char_matrix, order):
        self._hdisp = hdisp
        self._x = x
        self._pos = 0
        self._width = width
        self._char_matrix = char_matrix
        self._char_count = len(self._char_matrix)
        self._char_height = 9
        self._pos_count = self._char_height * self._char_count  # 99
        self._order = order

        self._start_pattern = (0, 0, 0, 1, 0, 0, 0, 1, 0,
                               0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0)
        self._stop_pattern = (1, 1, 1, 0, 1, 0, 0, 1, 0, -1, 0, 0, -1, 0,
                              0, -1, 0, 0, -1, 0, 0, 0, -1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, -1)

        self.frames_reset()
        self.build()

    def get_dpos(self):
        return self._hdisp.wheels.index(self)

    dpos = property(get_dpos)

    def get_x(self):
        return self._x

    x = property(get_x)

    def get_char(self):
        return self._wheel[self._pos][0]

    char = property(get_char)

    def build(self):
        # creates all positions possible on the wheel as an array self._wheel
        self._wheel = []

        for pos in range(0, self._pos_count):
            char_num = (self._pos_count-1-pos //
                        self._char_height + 1) % self._char_count

            if self._order == 1:
                char_num = (self._char_count - char_num) % self._char_count

            row = pos % self._char_height

            self._wheel.append((char_num, row))

    def frames_reset(self):
        self._frames = []
        self._frame = -1

    def frame_add(self, direction):
        if self._frames == []:
            pos_last = self._pos
        else:
            pos_last = self._frames[-1]

        pos_new = (pos_last + direction) % self._pos_count
        self._frames.append(pos_new)

        return pos_new

    def frame_add_to_char(self, char, direction):

        chr_current, char_row_current = self._wheel[self._pos]

        if not chr_current == char and char_row_current == 0:

            for pos in range(0, (4-self.dpos)*12):  # 4 = 5 Wheels -> 0-based
                self.frame_add(0)

            for sign in self._start_pattern:
                self.frame_add(sign*direction)

            while not (chr_current == char and char_row_current == 0):
                pos_new = self.frame_add(direction)

                chr_current, char_row_current = self._wheel[pos_new]

            for sign in self._stop_pattern:
                self.frame_add(sign*direction)

    def draw_next(self):
        if self._frames != [] and self._frame < len(self._frames)-1:
            self._frame += 1
            self.draw_pos(self._frames[self._frame])
            ret = True
        else:
            self.draw_pos(self._pos)
            self.frames_reset()
            ret = False

        return ret

    def draw_pos(self, pos):
        self._pos = pos % self._pos_count  # 98 -> 98,   99 -> 0,  -1 -> 98

        for y in range(0, 8):
            wp2 = (self._pos + y) % self._pos_count
            chr, char_row = self._wheel[wp2]
            self.draw_character_row(chr, self._x, y, char_row)

    def draw_character_row(self, chr, x, y, char_row):
        if char_row >= 0:
            val_col = (self._char_matrix[chr] >> 8 * char_row) & 0xFF
            for col in range(0, self._width):
                self._hdisp.disp.pixel(
                    x + col, y, self._hdisp.fg_col if 1 << col & val_col else self._hdisp.bg_col)

    def refresh(self):
        self.draw_pos(self._pos)  # Just refresh the wheel's display

    def shortest_direction(self, f, t):

        if f == t:
            direction = 0
        else:
            dist = t - f
            if dist > 0:
                distance_down = dist
                distance_up = self._char_count - dist
            else:
                distance_down = self._char_count + dist
                distance_up = -dist

            if distance_up < distance_down:
                direction = 1
            else:
                direction = -1

        return direction * -self._order

    def frame_move_to(self, char):
        if settings.rotation == 'shortest':
            direction = self.shortest_direction(self.char, char)
        elif settings.rotation == 'up':
            direction = 1
        elif settings.rotation == 'down':
            direction = -1

        if direction != 0:
            self.frame_add_to_char(char, direction)


class MatriClock:  # *****************************************************************************************************************

    def __init__(self):

        self._hdisp = DisplayHandler()
        self._dht22 = DHT22(Pin(14, Pin.IN, Pin.PULL_UP))

        self._settimefrominternet_running = False
        self.rtc = machine.RTC()
        self.rtc.datetime((2022, 1, 1, 6, 12, 0, 0, 0))

        self._rtcdt_last_set = None
        self._time_synced = False

        self.bn0 = 21  # left
        self.bn1 = 22  # middle
        self.bn2 = 27  # right

        self._ids = [self.bn0, self.bn1, self.bn2]

        self._alarm_dt = None

        self.alh = AlarmHandler(self.rtc)
        self.alarm_enabled = True

        self._mode = 'None'
        self._mode_before = 'None'
        self._settimefrominternet_last = None

        self.abuzzer = Pin(28, Pin.OUT)

        buttons = []
        for id in self._ids:
            buttons.append(Button(id, self.bn_hdl))

        self._buttons = tuple(buttons)

        # Adresse welche uns das JSON mit den Zeitdaten liefert
        self.service = 'http://worldtimeapi.org/api/'
        if settings.timezone == 'auto':
            self.url = self.service + 'ip'
        else:
            self.url = self.service + 'timezone/' + settings.timezone

        if settings.language == 'de':
            self._weekday_chars = (
                (13, 15),
                (11, 14),
                (13, 14),
                (11, 15),
                (12, 16),
                (14, 11),
                (14, 15))

        elif settings.language == 'en':
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

    def findJson(self, response):
        txt = 'abbreviation'
        return response[response.find(txt)-2:]

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

            temp_celsius = int(self.my_round(self._dht22.temperature(), 0))
            if settings.temperature_unit == 'C':
                temp = temp_celsius
            elif settings.temperature_unit == 'F':
                temp = temp_celsius * 1.8 + 32
            
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

    def get_time_synced(self):
        return self._time_synced
    
    def set_time_synced(self, value):
        self._time_synced = value
        self._hdisp.time_sync_failed = not value

    time_synced = property(get_time_synced, set_time_synced)

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

            if h1 == 0 and not settings.leading_zero:
                h1 = 10

            self._hdisp.wheels_move_to([h1, h0, 1, m1, m0], show_alarm_enabled=True, show_time_sync_failed=True)

    def wificonnect(self):
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        self.wlan.ifconfig((settings.network_ipaddress,
                           settings.network_subnetmask,
                           settings.network_gateway,
                           settings.network_dnsserver))

        self.wlan.connect(settings.wifi_ssid, settings.wifi_password)

        passes = 0

        cont = True
        while cont:
            passes += 1
            cont = not self.wlan.isconnected() and self.wlan.status() >= 0
            print("WLAN: Waiting to connect, pass " + str(passes) +
                  ": status=" + str(self.wlan.status()))
            time.sleep(1)

        print("WLAN: Connected.")

    def settimefrominternet(self):
        if not self._settimefrominternet_running:
            self._settimefrominternet_running = True
            self.time_synced = False
            print('settimefrominternet()')

            # Reading HTTP Response
            passes = 0
            response_text = ""

            while (response_text == "") and passes < 30:
                response = None
                try:
                    print("requesting time from URL " + self.url + "...")
                    response = urequests.get(self.url)
                    response_text = response.text
                    response.close()

                except ValueError as e:
                    print(e)
                    response_text = ""

                except OSError as e:
                    print(e)
                    response_text = ""

                if response_text == "":
                    time.sleep(1)
                passes += 1

            if len(response_text) > 0:
                jsonData = self.findJson(response_text)
                aDict = json.loads(jsonData)

                day_of_week = aDict['day_of_week']
                dtstring = aDict['datetime']

                # Internet time: Sunday=0, Saturday=6
                # RTC time:      Monday=0, Sunday=6
                if day_of_week == 6:
                    day_of_week = 0
                else:
                    day_of_week -= 1

                # e.g. 2022-10-07T19:03:33.054288 + 02:00
                year = int(dtstring[0:4])
                month = int(dtstring[5:7])
                day = int(dtstring[8:10])
                hours = int(dtstring[11:13])

                # the time format of worldtimeapi.org is 24-hour clock for any country
                if settings.time_convention_hours == 12:
                    hours = hours % 12
                    
                minutes = int(dtstring[14:16])
                seconds = int(dtstring[17:19])
                subseconds = 0

                rtcdt = (year, month, day, day_of_week,
                         hours, minutes, seconds, subseconds)
                self.rtc.datetime(rtcdt)
                self.time_synced = True
                self._settimefrominternet_last = rtcdt
                print("rtcdt, now, last=", rtcdt, self.rtc.datetime(),
                      self._settimefrominternet_last)
                self.alh.set_alarm_next_rtcdt()

            time.sleep(1)
            self._settimefrominternet_running = False

    def beep(self, duration_s):
        self.abuzzer.value(1)
        time.sleep(duration_s)
        self.abuzzer.value(0)

    def beep4x(self):
        for nr in range(0, 4):
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
            if self.alh.alarm:
                self.beep4x()
                time.sleep(0.4)
            else:
                time.sleep(1)

    def minute_loop(self):
        while True:
            rtcdt = self.rtc.datetime()
            print("minute_loop at " +
                  str(rtcdt[4]) + ":" + str(rtcdt[5]) + ":" + str(rtcdt[6]))
            # Sync time if it hasn't been synced before or if it is after 2 a.m. and the last sync is a day ago:
            if self._settimefrominternet_last == None \
               or (rtcdt[4] >= 2 and self._settimefrominternet_last[2] != rtcdt[2]):
                print(self._settimefrominternet_last, rtcdt)
                self.wificonnect()
                self.settimefrominternet()
                
            self.mode_clock()

            if self.alh.alarm_next_remaining_seconds() <= 1:
                self.alh.snooze_first()
                self.mode = 'clock'

            self.sleep_until_second(0)

            if self.mode == 'temp':
                self.mode_temp()  # refresh temperature and humidity display

    def bn_hdl(self, pin):
        if self.buttons_enabled:

            button = self._get_button(pin)
            button.register_value()

            if button.value_changed() and button.value():
                self.beep(0.001)
                print("alarm = " + str(self.alh.alarm), ", button.id = " +
                      str(button.id) + ", mode = " + self.mode)

                if self.alh.alarm and button.id == self.bn1 and self.mode == 'clock':
                    self.action_snooze()
                elif self.alh.alarm and button.id == self.bn1 and self.mode == 'standby':
                    self.action_snooze()
                elif self.alh.alarm and button.id == self.bn2 and self.mode == 'clock':
                    self.action_alarm_off()
                elif self.alh.alarm and button.id == self.bn2 and self.mode == 'standby':
                    self.action_alarm_off()
                elif not self.alh.alarm and button.id == self.bn0 and self.mode == 'clock':
                    self.action_date()
                elif not self.alh.alarm and button.id == self.bn0 and self.mode == 'date':
                    self.action_temp()
                elif not self.alh.alarm and button.id == self.bn0 and self.mode == 'standby':
                    self.action_date()
                elif not self.alh.alarm and button.id == self.bn0 and self.mode == 'temp':
                    self.action_clock()
                elif not self.alh.alarm and button.id == self.bn1 and self.mode == 'clock':
                    self.action_standby()
                elif not self.alh.alarm and button.id == self.bn1 and self.mode == 'date':
                    self.action_standby()
                elif not self.alh.alarm and button.id == self.bn1 and self.mode == 'standby':
                    self.action_clock()
                elif not self.alh.alarm and button.id == self.bn1 and self.mode == 'temp':
                    self.action_standby()
                elif not self.alh.alarm and button.id == self.bn2 and self.mode == 'clock':
                    self.action_alarm_toggle()

    def action_alarm_toggle(self):
        self.alarm_enabled = not self.alarm_enabled
        self._hdisp.refresh()

    def action_snooze(self):
        self.alh.snooze_next()

    def action_alarm_off(self):
        self.alh.snooze_stop()

    def action_clock(self):
        self.mode = 'clock'

    def action_temp(self):
        self.mode = 'temp'

    def action_date(self):
        self.mode = 'date'

    def action_standby(self):
        self.mode = 'standby'


# ---------------- Main program ----------------

macl = MatriClock()
macl.start()
