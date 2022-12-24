class settings:

    wifi_ssid = 'myWiFiSSID'
    wifi_password = 'myWiFiPassword'

    network_ipaddress = '192.168.1.23'
    network_subnetmask = '255.255.255.0'
    network_gateway = '192.168.1.1'
    network_dnsserver = '192.168.1.1'

    #Day of week, hour, and minute of an alarm time
    #e.g. (2, 5, 40) for wednesday, 5:40 a.m.
    #day of week: 0=Monday to 6=Sunday
    alarms  = [
            (4, 20, 6),
            (0, 5,  0),
            (1, 5,  0),
            (2, 5, 40),
            (3, 5,  0),
            (4, 5, 40)]


    rotation = 'shortest'  # 'shortest', 'down' or 'up''
    timezone = 'auto' # 'auto' (timezone by public IP address) or a timezone like 'Europe/Berlin'
    leading_zero = False #leading zero when displaying the time
    snooze_time_m = 10
    display_inverse = False
    language = 'de' # 'de' or 'en'
    order = -1 # = -1: "4" is above "3".    = 1: "4" is below "3"

