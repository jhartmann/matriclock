import urequests
import json
import time

from config import Settings

class TimeSync:
    
    def __init__(self, rtc):

        self._synced = False
        self._synced_last_rtcdt = None

        self._rtc = rtc

        service = 'http://worldtimeapi.org/api/'
        if Settings.timezone == 'auto':
            self._url = service + 'ip'
        else:
            self._url = service + 'timezone/' + Settings.timezone
        self._time_sync_running = False

    def time_sync(self):
        if not self._time_sync_running:
            self._time_sync_running = True
            self._synced = False
            print('time_sync()')

            # Reading HTTP Response
            passes = 0
            response_text = ""

            repeat = True

            while repeat:
                response = None
                try:
                    print("requesting time from URL " + self._url + "...")
                    response = urequests.get(self._url)
                    response_text = response.text
                    print("response.status_code=", response.status_code)
                except ValueError as e:
                    print("ValueError:", e)
                    response_text = ""

                except OSError as e:
                    print("OSError:", e)
                    response_text = ""

                finally:
                    if response != None:
                        response.close()
                        print("response closed.")

                if response_text == "":
                    time.sleep(1)
                passes += 1

                repeat = (response_text == "" and passes < 30)
                
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
                if Settings.time_convention_hours == 12:
                    hours = hours % 12
                    
                minutes = int(dtstring[14:16])
                seconds = int(dtstring[17:19])
                subseconds = 0

                rtcdt = (year, month, day, day_of_week,
                         hours, minutes, seconds, subseconds)
                self._rtc.datetime(rtcdt)
                self._synced = True
                self._synced_last_rtcdt = rtcdt
                print("rtcdt, now, last=", rtcdt, self._rtc.datetime(),
                      self._synced_last_rtcdt)

            time.sleep(1)
            self._time_sync_running = False

    def findJson(self, response_text):
        txt = 'abbreviation'
        return response_text[response_text.find(txt)-2:]

    def get_synced(self):
        return self._synced
    
    synced = property(get_synced)
    
    def get_synced_last_rtcdt(self):
        return self._synced_last_rtcdt
    
    synced_last_rtcdt = property(get_synced_last_rtcdt)