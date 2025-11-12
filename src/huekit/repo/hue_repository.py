class HueRepository:
    def __init__(self, api: HueApi):
        self.api = api

    def resolve_group_room(self, group_id: str) -> Room:
        ...

    def get_group_lights(self, group_id: str) -> dict[str, Light]:
        ...

    def get_room_devices(self, room_id: str) -> list[Device]:
        ...