import time

from config import Settings

class AlarmHandler:  # *****************************************************************************************************************

    def __init__(self, rtc):

        self.rtc = rtc

        self._alarm_next_rtcdt = None
        self._enabled = True
        self._alarm_count = 0
        self._snooze_alarm_ticks_ms = 0  # Ticks when the snooze alarm is raised

        self._alarms = Settings.alarms

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

        self._snooze_alarm_ticks_ms = time.ticks_ms() + Settings.snooze_time_m * \
            60000 + msec_diff
        self._alarm_count += 1
        self.set_alarm_next_rtcdt()

    def snooze_first(self):
        self._snooze_alarm_ticks_ms = time.ticks_ms()
        self.set_alarm_next_rtcdt()

    def snooze_stop(self):
        self._snooze_alarm_ticks_ms = 0  # = disabled
        self.set_alarm_next_rtcdt()

    def get_alarm_reached(self):
        # Returns True if alarm or snooze time is reached
        return time.ticks_ms() > self._snooze_alarm_ticks_ms > 0

    alarm_reached = property(get_alarm_reached)

    def get_alarm_auto_stop_reached(self):
        # Returns True if alarm or snooze time is reached
        return time.ticks_ms() > self._snooze_alarm_ticks_ms + 60000 * Settings.alarm_auto_stop_m > 0

    alarm_auto_stop_reached = property(get_alarm_auto_stop_reached)

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
            # if the next alarm is today, then we have to check whether it is elapsed already
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
