from machine import SPI, Pin
import max7219
import time

from config import Settings

class DisplayHandler:  # *****************************************************************************************************************

    def __init__(self):
        spi = SPI(0, sck=Pin(18), mosi=Pin(19))
        cs = Pin(17, Pin.OUT)
        self.disp = max7219.Matrix8x8(spi, cs, 4)
        self.disp.brightness(0)

        self._playing = False

        if Settings.display_inverse:
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
            0x303030303f333332,
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
            Wheel(self, x=0,  width=6, char_matrix=self._char_matrix_digits +
                  self._char_matrix_weekday_0, order=Settings.order),
            Wheel(self, x=7,  width=6, char_matrix=self._char_matrix_digits +
                  self._char_matrix_weekday_1, order=Settings.order),
            Wheel(self, x=14, width=2,
                  char_matrix=self._char_matrix_colon, order=Settings.order),
            Wheel(self, x=17, width=6,
                  char_matrix=self._char_matrix_digits, order=Settings.order),
            Wheel(self, x=24, width=6,
                  char_matrix=self._char_matrix_digits, order=Settings.order)
        )

        self.index_count = len(self.wheels)

    def wheels_move_to(self, chars, show_alarm_enabled, show_time_sync_failed):
        self._show_alarm_enabled = show_alarm_enabled
        self._show_time_sync_failed = show_time_sync_failed
        print("wheels_move_to", chars)

        # Create motion frames for digit wheels 0-3:
        for index in range(0, self.index_count):
            self.wheels[index].frame_move_to(chars[index])

        # Play frames, just like a short movie       
        self.frames_play()

    def frames_play(self):
        self._playing = True
        while self._playing:
            self.clear()
            self.draw_info()
            self.draw_time_sync_failed()

            self._playing = False
            for index in range(0, self.index_count):
                self._playing = self.wheels[index].draw_next() or self._playing

            self.show()
            time.sleep(self._row_seconds)

    def draw_info(self):
        if self.alarm_enabled and self._show_alarm_enabled:
            self.disp.pixel(31, 7, self.fg_col)

    def draw_time_sync_failed(self):
        if self.time_sync_failed and self._show_time_sync_failed:
            self.disp.vline(31, 0, 3, self.fg_col)
            self.disp.pixel(31, 4, self.fg_col)

    def refresh(self):
        self.clear()
        self.draw_info()
        self.draw_time_sync_failed()
        for index in range(0, self.index_count):
            self.wheels[index].refresh()
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


    def _get_playing(self):
        return self._playing
    
    playing = property(_get_playing)
    
    def set_brightness_from_time(self, rtcdt):
        month = rtcdt[1]
        hour = rtcdt[4]

        sunrise, sunset = Settings.sunrisesunset[month-1]

        if sunrise <= hour < sunset:
            self.brightness = Settings.brightness_day
        else:
            self.brightness = Settings.brightness_night

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

class Wheel:

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

    def get_index(self):
        return self._hdisp.wheels.index(self)

    index = property(get_index)

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

            for pos in range(0, (4-self.index)*12):  # 4 = 5 Wheels -> 0-based
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
        if Settings.rotation == 'shortest':
            direction = self.shortest_direction(self.char, char)
        elif Settings.rotation == 'up':
            direction = 1
        elif Settings.rotation == 'down':
            direction = -1

        if direction != 0:
            self.frame_add_to_char(char, direction)
