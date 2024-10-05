class Settings:

    # You can specify daily alarm times here.
    # Format: (day_of_week, hour, minute)
    # (0, 5, 30) means: Monday at 5:30 a.m.
    # Alarm times have to be entered in 24-hour format, regardless of the timezone.
    # First day of week is Monday=0, last day of week is Sunday=6
    alarms = [
        (0, 5, 0),
        (1, 6, 0),
        (2, 6, 0),
        (3, 5, 0),
        (4, 6, 0)]

    snooze_time_m = 10 # snooze time in minutes
    alarm_auto_stop_m = 1 # alarm will stop when no key is pressed for this time (minutes)

    # This is a list of the approximate sunrise and sunset hour
    # from January to December for setting up the brightness value.
    # It is always an 24-hour clock value, regardless of the timezone.
    # (9, 16) means: sunrise at approx. 9 o'clock, sunset at approx. 16 o'clock
    # Please look up the values for your city on the internet.
    sunrisesunset = (
            (9, 16),
            (8, 17),
            (7, 18),
            (7, 20),
            (6, 21),
            (5, 22),
            (5, 22),
            (6, 21),
            (6, 20),
            (7, 19),
            (7, 17),
            (8, 16))

    brightness_day = 15  # 0 (darkest) to 15 (brightest)
    brightness_night = 0  # 0 to 15

    rotation = 'down'  # 'shortest', 'down' or 'up''
    order = -1  # = -1: "4" is above "3"    1: "4" is below "3"

    leading_zero = False # leading zero for time display, e.g. "04:59" (True) / " 4:59" (False)

    display_inverse = False


    # Your local timezone.
    # 'auto' (timezone is determined by public IP address), or a timezone like 'Europe/Berlin' or 'America/Los_Angeles'
    # You can request a list of valid timezone values from http://worldtimeapi.org/api/timezone
    timezone = 'auto'
    time_convention_hours = 24  # 12 for 12-hour clock, or 24 for 24-hour clock

    language = 'de'  # 'de' or 'en' for displaying the day of week
    
    use_dht_sensor = False  # Set to True to use DHT sensor and show temperature/humidity
    temperature_unit = 'C' # 'C' for degrees Celsius, or 'F' for degrees Fahrenheit

    wifi_ssid = 'MyWiFiSSID'
    wifi_password = 'MyWiFiPassword'

    network_use_dhcp = True
    
    # if network_use_dhcp is set to False, then you have to setup the network manually:
    # network_ipaddress = '192.168.188.34' 
    # network_subnetmask = '255.255.255.0'
    # network_gateway = '192.168.188.1'
    # network_dnsserver = '9.9.9.9'


