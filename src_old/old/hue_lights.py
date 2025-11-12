import os
import time

import phue
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

APP_KEY = os.getenv("APP_KEY")
HUE_BRIDGE_IP = os.getenv("HUE_BRIDGE_IP")

hue_bridge = phue.Bridge(HUE_BRIDGE_IP, APP_KEY)

hue_bridge.connect()
lights = hue_bridge.get_light_objects('list')

groups = hue_bridge.groups

print(groups)
class PcHueLights:
    left_light: phue.Light = hue_bridge.lights[0]
    right_light: phue.Light = hue_bridge.lights[1]
    group: phue.Group = groups[4]

    @classmethod
    def turn_on(cls):
        cls.left_light.on = True
        cls.right_light.on = True

    @classmethod
    def turn_off(cls):
        cls.left_light.on = False
        cls.right_light.on = False

    @classmethod
    def set_on(cls, is_on:bool):
        cls.left_light.on = is_on
        cls.right_light.on = is_on

    @classmethod
    def set_transition_time(cls, transition_time):
        if transition_time < 0.1:
            raise ValueError(f"'transition_time' is smaller than 0!\n{transition_time=}")
        cls.right_light.transitiontime = transition_time
        cls.left_light.transitiontime = transition_time

    @classmethod
    def set_brightness(cls, brightness_level):
        if brightness_level not in [i for i in range(0, 255)]:
            raise ValueError(f"'brightness_level' out of range!\n{brightness_level=}")

        cls.right_light.brightness = brightness_level
        cls.left_light.brightness = brightness_level

    @classmethod
    def blink_lights(cls, frequency, repetitions, color=None):
        current_state_is_on = True

        cls.turn_on()
        cls.set_transition_time(0.5)
        cls.set_brightness(254)

        for i in range(0, repetitions):
            current_state_is_on = not current_state_is_on

            cls.set_on(current_state_is_on)

            time.sleep(frequency)
        cls.turn_on()

ceiling_light: phue.Light = hue_bridge.lights[2]
color_range = (0, 65535)

PcHueLights.blink_lights(0.5, 5)
