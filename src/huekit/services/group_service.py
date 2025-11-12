class GroupService:
    def __init__(self, api: HueApi):
        self.api = api

    def turn_on(self, group_id: str):
        ...

    def turn_off(self, group_id: str):
        ...

    def set_brightness(self, group_id: str, level: int, duration_ms: int = 500):
        ...

    def set_color(self, group_id: str, xy: tuple[float, float], duration_ms: int = 50):
        ...

    def set_color_temp(self, group_id: str, mirek: int):
        ...