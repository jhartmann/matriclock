from machine import Pin
import time

class Button:  # *****************************************************************************************************************

    def __init__(self, id, handler):

        self.pin = Pin(id, Pin.IN, Pin.PULL_DOWN)
        self.pin.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=handler)
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
