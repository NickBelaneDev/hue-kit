import warnings

from hue_id_enums import GroupIDEnum

warnings.filterwarnings("ignore", "Unverified HTTPS request")

import requests
import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

BRIDGE_IP = os.getenv("HUE_BRIDGE_IP")
APP_KEY = os.getenv("V2_APP_KEY")

HEADERS = {"hue-application-key": APP_KEY}
BASE    = f"https://{BRIDGE_IP}/clip/v2/resource"

# =====================
# Helper Functions
def srgb_to_xy(r,g,b):
    def lin(u):
        u = u/255
        return pow((u+0.055)/1.055, 2.4) if u > 0.04045 else u/12.92
    R, G, B = lin(r), lin(g), lin(b)
    X = R*0.4124 + G*0.3576 + B*0.1805
    Y = R*0.2126 + G*0.7152 + B*0.0722
    Z = R*0.0193 + G*0.1192 + B*0.9505
    denom = (X+Y+Z) or 1e-9
    return X/denom, Y/denom


# =====================
# Hue Classes
class HuePairingService:
    @staticmethod
    def connect_to_hue_bridge(bridge_ip):
        _url = f"https://{bridge_ip}/api"
        _payload = {
            "devicetype": "mein_request_script#desktop",
            "generate_clientkey": True
        }
        input("Press the connection button on your HUE Bridge and press enter to get a new APP_KEY")
        _response = requests.post(_url, json=_payload, verify=False, timeout=3)
        print(_response.text)
        return _response.text

class HueClient:
    def __init__(self, bridge_ip=None, app_key=None, base_url=None, headers=None):
        self.bridge_ip = bridge_ip or BRIDGE_IP
        self.app_key = app_key or APP_KEY
        self.base_url = base_url or BASE
        self.headers = headers or HEADERS

        self.session = requests.session()

    def get_resource(self, resource: str, verify=False, timeout=5) -> dict:
        try:
            url = f"{self.base_url}/{resource}"
            _r = self.session.get(url, headers=self.headers, verify=verify, timeout=timeout)
            _r.raise_for_status()
            return _r.json()
        except Exception as e:
            return {"Exception": e}

    def put_resource(self, resource: str,payload: dict, verify=False, timeout=5):
        url = f"{self.base_url}/{resource}"
        r = self.session.put(url, json=payload, headers=self.headers, verify=verify, timeout=timeout)

        try:
            r.raise_for_status()
        except requests.HTTPError as e:
            try:
                print("Response JSON:", r.json())
            except Exception:
                print("Response TEXT:", r.text)
            raise
        try:
            js = r.json()
            if "errors" in js and js["errors"]:
                print("Hue errors:", js["errors"])
            else:
                print("OK:", js.get("data", js))
            return js
        except ValueError:
            return None

    def set_base_url(self, url:str):
        self.base_url = url

class HueEntities:
    def __init__(self, client: HueClient):
        self.client = client

    @property
    def groups(self):
        groups = self.client.get_resource("grouped_light")
        return [group for group in groups["data"]]

    @property
    def lights(self):
        lights = self.client.get_resource("light")
        lights_dict = [{"name": light["metadata"]["name"],
                        "id": light["id"],
                        "is_on": light["on"]["on"],
                        "brightness": light["dimming"]["brightness"]}
                       for light in lights["data"]]
        return lights_dict

    @property
    def rooms(self):
        groups = self.client.get_resource("room")
        return [group for group in groups["data"]]

    @property
    def devices(self):
        devices = self.client.get_resource("device")
        return [
            {
                "id": device["id"],
                "metadata": device["metadata"],
                "services": device["services"]
            }
            for device in devices["data"]
        ]

class HueGroup:
    def __init__(self, client: HueClient, group_id: str):
        self.client = client
        self.group_id = group_id
        self.url = f"grouped_light/{group_id}"
        try:
            self.group_dict = self.client.get_resource(self.url)
            self.group_dict = self.group_dict["data"][0]

        except Exception as e:
            raise AttributeError(e)

        self.parent_room = self._get_parent_room()

    def _get_parent_room(self) -> list[dict]:
        # zuerst suchen wir die room_id des Raums, in dem sich die Gruppe befindet
        room_id = self.group_dict["owner"]["rid"] if self.group_dict["owner"]["rtype"] == "room" else None

        if not room_id:
            raise ValueError(f"'room_id' is None!")

        rooms = self.client.get_resource(f"room")

        is_in_rooms = []
        for room in rooms["data"]:
            if room["id"] == room_id:
                is_in_rooms.append(room)

        return is_in_rooms

    def get_lights(self):

        # /group: {'owner': {'rid': <<room_id>>, 'rtype': <<type>>}} -> /room: {'children': ['rid': <<id>>, 'rtype': <<Hier muss 'device' stehen>>]}
        # /device: {'service': {'rid': '078e603a-21c3-4457-ad12-dc135165c123', 'rtype': 'light'}
        # Aus der Group gehen wir also über die room_id zum room, wo wir über die children mit 'rtype': 'device' finden müssen.
        #rooms = self.client.get_resource(f"room/{}")

        # Laden der Device-IDs der einzelnen Lichter in unserem Raum
        device_light_ids = {
            child.get("rid")
            for child in self.parent_room[0]["children"]
            if child.get("rtype") == "device"
        }

        devices = self.client.get_resource("device")["data"]
        lights = self.client.get_resource("light")["data"]

        # Wir erstellen ein Lookup der 'lights' nach deren 'id', um später einfacher auf sie zugreifen zu können
        all_lights_by_id = {
            light.get("id"):{
                k: v for k, v in light.items() if k != "id"
            }
            for light in lights
            if "id" in light
        }

        # Wir suchen in den 'device["services"]' nach dem Typ 'light'. Die dazugehörige ID ist die finale
        # ID vom 'light', mit welcher sie in 'room' zu finden ist.
        real_light_ids = {
            s.get("rid")
            for d in devices
            if d.get("id") in device_light_ids
            for s in d.get("services", [])
            if s.get("rtype") == "light"
        }

        # Finales zusammenstellen des Dictionaries mit
        complete_lights: dict = {
            lid: all_lights_by_id[lid]
            for lid in real_light_ids
            if lid in all_lights_by_id
        }

        return complete_lights

    def set_on(self, verify=False, timeout=5):
        payload = {"on": {"on": True}}
        self.client.put_resource(self.url, payload=payload, verify=verify, timeout=timeout)

    def set_off(self,verify=False, timeout=5):
        payload = {"on": {"on": False}}
        self.client.put_resource(self.url, payload=payload, verify=verify, timeout=timeout)

    def set_brightness(self, level: int, duration_ms=500):
        max_capped_level = min(level, 100)
        level = max(0, max_capped_level)
        payload = {"dimming": {"brightness": level},
                   "dynamics": {"duration": duration_ms}}
        self.client.put_resource(self.url, payload=payload)

    def set_color_temp(self, temp: int):
        _temp = max(50, min(temp, 1000))
        payload = {"color_temperature":{"mirek": _temp}}
        self.client.put_resource(self.url, payload=payload)

    def set_color(self, color: list[float], temp: int=None, duration_ms:int=50):

        for i, c in enumerate(color):
            color[i] = max(0.0, min(c, 1.0))

        x, y = color
        payload = {"color":{"xy":{"x":x,"y":y}}}
        if temp:
            _temp = max(50, min(temp, 1000))
            payload["color_temperature"] =  {"mirek": _temp}

        if duration_ms:
            payload["dynamics"] = {"duration": duration_ms}

        self.client.put_resource(self.url, payload=payload)


if __name__ == "__main__":

    client = HueClient()

    gid = GroupIDEnum.CeilingLights.value
    group = HueGroup(client, gid)
    print(" debug ---------")
    print(group.get_lights())
    print(" ---------------")
    print(" ------------end\n")


    #group.set_off()
   # group.set_on()

    he = HueEntities(client)
    print(" All Entities ----------")
    print(f"/devices: {he.devices}")
    print(f"/rooms: {he.rooms}")
    print(f"/groups: {he.groups}")
    print(f"/lights: {he.lights}")
