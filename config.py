class settings:

    # You can specify daily alarm times here.
    # Format: (day_of_week, hour, minute)
    # (0, 5, 30) means: Monday at 5:30 a.m.
    # Alarm times have to be entered in 24-hour format, regardless of the timezone.
    # First day of week is Monday=0, last day of week is Sunday=6
    alarms = [
        (0, 5,  0),
        (1, 5,  0),
        (2, 5, 40),
        (3, 5,  0),
        (4, 5, 40),
        (5, 7,  0),
        (6, 7,  0)]

    rotation = 'shortest'  # 'shortest', 'down' or 'up''

    wifi_ssid = 'MyWiFiSSID'
    wifi_password = 'MyWiFiPassword'

    # Please customize these values for your local network
    network_ipaddress = '192.168.188.34' 
    network_subnetmask = '255.255.255.0'
    network_gateway = '192.168.188.1'
    network_dnsserver = '192.168.188.1'

    # Your local timezone.
    # 'auto' (timezone is determined by public IP address), or a timezone like 'Europe/Berlin' or 'America/Los_Angeles'
    # You can request a list of valid timezone values from http://worldtimeapi.org/api/timezone
    timezone = 'Europe/Berlin'
    
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

    brightness_day = 2  # 0 (darkest) to 15 (brightest)
    brightness_night = 0  # 0 to 15

    leading_zero = False # leading zero for time display

    snooze_time_m = 10 # snooze time in minutes

    display_inverse = False

    language = 'de'  # 'de' or 'en' for displaying the day of week

    order = -1  # = -1: "4" is above "3"    1: "4" is below "3"
    
    time_convention_hours = 24 # 12 for 12-hour clock, or 24 for 24-hour clock
    
    temperature_unit = 'C' # 'C' for degrees Celsius, or 'F' for degrees Fahrenheit

