from typing import Annotated

from pydantic import BaseModel, Field


class MorganStanleySettings(BaseModel):
    enabled: bool = False
    timeout_seconds: Annotated[float, Field(ge=5, le=60)] = 40
    cache_seconds: Annotated[int, Field(ge=30, le=3600)] = 60
