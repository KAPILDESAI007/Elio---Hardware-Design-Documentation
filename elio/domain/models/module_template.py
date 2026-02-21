from pydantic import BaseModel


class ModuleTemplate(BaseModel):
    name: str
    signal_type: str
    channel_capacity: int
    redundant: bool = False