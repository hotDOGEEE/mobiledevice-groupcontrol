import wda
from pydantic import BaseModel
from typing import Optional, List

class IOS_Device_Obj:
    udid: str
    wdaurl: str
    wda_obj: wda.Client


class Android_Device_Obj:
    """
    目前安卓只需要udid一个属性，但为了项目格式统一，姑且也把他跟ios设成一个对象类型了
    """
    udid: str
    model: str


class T_Obj(BaseModel):
    udid: str = None
    filepath_or_url: str = None
    bundle_id: str = None


class Device_Image(BaseModel):
    udid: str
    wdaurl: str = None
    model: str = None


class Item(BaseModel):
    devices: Optional[List[Device_Image]] = None


class Pos(BaseModel):
    x: int
    y: int
