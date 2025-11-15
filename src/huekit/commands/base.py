from pydantic import BaseModel, Field
from typing import Optional

class OnModel(BaseModel):
    is_on: bool

class OnCommand(BaseModel):
    on: OnModel

class DynamicsModel(BaseModel):
    duration_ms: Optional[int] = Field(..., ge=0)
    speed: Optional[float] = Field(..., ge=0.0, le=1.0)

class DimmingModel(BaseModel):
    brightness: float = Field(..., ge=0.0, le=100.0)

class DimmingCommand(BaseModel):
    dimming: DimmingModel
    dynamics: Optional[DynamicsModel] = None

class ColorTemperatureModel(BaseModel):
    mirek: int = Field(..., ge=153, le=500)

class ColorTemperatureCommand(BaseModel):
    color_temperature: ColorTemperatureModel
    dynamics: Optional[DynamicsModel] = None

# Das innerste Objekt
class XYModel(BaseModel):
    x: float = Field(..., ge=0.0, le=1.0)
    y: float = Field(..., ge=0.0, le=1.0)

# Das "mittlere" Objekt
class ColorModel(BaseModel):
    xy: XYModel

# Das "äußere" Päckchen
class ColorCommand(BaseModel):
    color: ColorModel
    dynamics: Optional[DynamicsModel] = None

