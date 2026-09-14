from pydantic import BaseModel


class IndicatorExplanation(BaseModel):
    source: str
    trigger: str
    limitation: str
