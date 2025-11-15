from pydantic import BaseModel

class LightMetadata(BaseModel):
    name: str
    archetype: str # z.B. "sultans_bulb"

class LightModel(BaseModel):
    id: str
    metadata: LightMetadata
    on: OnModel
    dimming: DimmingModel
    color_temperature: ColorTemperatureModel
    color: ColorModel
