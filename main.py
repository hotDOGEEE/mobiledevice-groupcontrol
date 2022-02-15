import wda
from fastapi import FastAPI
from typing import Optional, List
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from concurrent.futures import ThreadPoolExecutor
from tidevice import __main__ as mi
import time
import shutil
import os
import uvicorn


app = FastAPI()
using_device = list()
resource_type = ["logs", "pags", "screenshot"]
form_size = {"iphone 6": [375, 667],
             "iphone 6 plus": [414, 736],
             "iphone 6s": [375, 667],
             "iphone 6s plus": [414, 736],
             "iphone 7": [375, 667],
             "iphone 7 plus": [414, 736],
             "iphone 8": [375, 667],
             "iphone 8 plus": [414, 736],
             "iphone x": [375, 812],
             "iphone xs": [375, 812],
             "iphone xs max": [414, 896],
             "iphone xr": [414, 896],
             "iphone 11": [414, 896],
             "iphone 11 pro": [375, 812],
             "iphone 11 pro max": [414, 896],
             "iphone 12 mini": [360, 780],
             "iphone 12": [390, 844],
             "iphone 12 pro": [390, 844],
             "iphone 12 pro max": [428, 926],
             "iphone 13 mini": [360, 780],
             "iphone 13 pro": [390, 844],
             "iphone 13 pro max": [428, 926]}


class IOS_Device_Obj:
    udid: str
    wdaurl: str
    wda_obj: wda.Client


class Device_Image(BaseModel):
    udid: str
    wdaurl: str


class Item(BaseModel):
    devices: Optional[List[Device_Image]] = None


def clear_file(plat: str):
    for i in resource_type:
        shutil.rmtree(f"resource/{plat}/{i}/")
        os.mkdir(f"resource/{plat}/{i}/")


class BaseClass:
    @app.post("/items/")
    def create_item(plat: str, devices: Item):
        global using_device
        using_device.clear()
        if plat.lower() == "android":
            print("安卓的待完善")
            clear_file("android")
        elif plat.lower() == "ios":
            for d in devices.devices:
                i = IOS_Device_Obj()
                i.udid, i.wdaurl = d.udid, d.wdaurl
                i.wda_obj = wda.Client(d.wdaurl)
                i.wda_obj.home()
                using_device.append(i)
            content = {"message": "IOS群控设备初始化成功"}
            response = JSONResponse(content=content)
            clear_file("ios")
            return response


class Pos(BaseModel):
    x: int
    y: int


def pos_trans(pos_x: int, pos_y: int, device=None, size=None):
    if device:
        if device.lower() in list(form_size.keys()):
            size = form_size[device]
    elif size:
        size = [size[:3], size[-3:]]
    pos_x = round(pos_x / size[0], 2)
    pos_y = round(pos_y / size[1], 2)
    return pos_x, pos_y


class EVENTS:

    @staticmethod
    def home(obj):
        obj.home()

    @staticmethod
    def lock(obj):
        obj.lock()

    @staticmethod
    def unlock(obj):
        obj.unlock()

    @staticmethod
    def screenshot(obj):
        device = [u.udid for u in using_device if id(u.wda_obj) == id(obj)][0]
        obj.screenshot().save(f"resource/screenshot/{device}_{time.time()}.png")

    @staticmethod
    def device_info(obj):
        return obj.device_info()


class WDA_Operation_Batch:

    @staticmethod
    @app.post("/touch/")
    def touch(pos_x: int, pos_y: int, device: str):
        def _touch_event(wda_obj):
            p = pos_trans(pos_x, pos_y, device)
            wda_obj.click(p[0], p[1])
        with ThreadPoolExecutor(max_workers=len(using_device)) as pool:
            pool.map(_touch_event, [u.wda_obj for u in using_device])
        return {"message": "click over"}

    @staticmethod
    @app.post("/swipe/")
    def swp(s_pos: Pos, e_pos: Pos, device: str):
        def _swipe_event(wda_obj):
            sp = pos_trans(s_pos.x, s_pos.y, device)
            ep = pos_trans(e_pos.x, e_pos.y, device)
            wda_obj.swipe(sp[0], sp[1], ep[0], ep[1])
        with ThreadPoolExecutor(max_workers=len(using_device)) as pool:
            pool.map(_swipe_event, [u.wda_obj for u in using_device])
        return {"message": "swipe over"}

    @staticmethod
    @app.post("/tap_hold/")
    def tap_hold(pos: Pos, device: str, t: float):
        def _tap_hold_event(wda_obj):
            p = pos_trans(pos.x, pos.y, device)
            wda_obj.tap_hold(p[0], p[1], t)
        with ThreadPoolExecutor(max_workers=len(using_device)) as pool:
            pool.map(_tap_hold_event, [u.wda_obj for u in using_device])
        return {"message": "tap_hold over"}

    @staticmethod
    @app.post("/simple_event/")
    def simple_event(event: str):
        with ThreadPoolExecutor(max_workers=len(using_device)) as pool:
            rst = pool.map(getattr(EVENTS, event), [u.wda_obj for u in using_device])
        if any([r for r in rst]):
            return [r for r in rst]
        else:
            return {"message": "run over"}


if __name__ == '__main__':
    uvicorn.run(app, host="localhost", port=8534)
