from pydantic import BaseModel
from typing import Optional


class Signal(BaseModel):
    tag: str
    signal_type: str
    safety: bool = False
    # Design Input Review fields
    pid_tag: Optional[str] = None
    signal_origin: Optional[str] = None
    io_redundancy: Optional[str] = None
    is_non_is: Optional[str] = None
    jb_cable_name: Optional[str] = None
    spare_channel_requirement: Optional[str] = None