import wda
from fastapi import FastAPI
from types import FunctionType
from typing import Optional, List
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from concurrent.futures import ThreadPoolExecutor as TPE
from tidevice import __main__ as mi
from tidevice._perf import RunningProcess, WaitGroup, iter_cpu_memory, iter_fps, iter_gpu, set_interval, iter_screenshot, iter_network_flow, gen_stimestamp
from tidevice import Device, DataType
import time
import shutil
import os
import sys
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
plat = "ios"
log_save_state = False
perf_state = False
perfs = [DataType.CPU, DataType.MEMORY, DataType.NETWORK, DataType.FPS, DataType.PAGE, DataType.SCREENSHOT, DataType.GPU]


class IOS_Device_Obj:
    udid: str
    wdaurl: str
    wda_obj: wda.Client


class T_Obj(BaseModel):
    udid: str = None
    filepath_or_url: str = None
    bundle_id: str = None


class Device_Image(BaseModel):
    udid: str
    wdaurl: str


class Item(BaseModel):
    devices: Optional[List[Device_Image]] = None


def clear_file():
    for i in resource_type:
        shutil.rmtree(f"resource/{plat}/{i}/")
        os.mkdir(f"resource/{plat}/{i}/")


"""
目前没有进行前端方案对接，采用本地记录的方式进行过程保留
如果要实现实时通信会将 syslog和perf两个方法改用websocket进行传输
"""


def syslog_save():

    def _ios(udid: str, state: FunctionType):
        sock = mi.cmd_syslog_sock_orient(udid)
        with open(f"resource/{plat}/logs/{udid}.log") as f:
            try:
                while True:
                    if state():
                        break
                    text = sock.recv().decode("utf-8")
                    f.write(text)
            except (BrokenPipeError, IOError):
                # Python flushes standard streams on exit; redirect remaining output
                # to devnull to avoid another BrokenPipeError at shutdown
                devnull = os.open(os.devnull, os.O_WRONLY)
                os.dup2(devnull, sys.stdout.fileno())
    global log_save_state
    if plat == "ios":
        params = [[u.udid, lambda: log_save_state] for u in using_device]
        TPE(max_workers=len(using_device)).map(lambda args: _ios(*args), params)


def perf(bundle_id: str):

    def _perf_callback(_type: DataType, value: dict):
        print("R:", _type.value, value)

    def _ios_perf_main(udid: str, bundle_id: str, state: FunctionType):
        d = Device(udid=udid)
        rp = RunningProcess(d, bundle_id)
        iters = []
        wgs = []
        if DataType.CPU in perfs or DataType.MEMORY in perfs:
            iters.append(iter_cpu_memory(d, rp))
        if DataType.FPS in perfs:
            iters.append(iter_fps(d))
        if DataType.GPU in perfs:
            iters.append(iter_gpu(d))
        if DataType.SCREENSHOT in perfs:
            iters.append(set_interval(iter_screenshot(d), 1.0))
        if DataType.NETWORK in perfs:
            iters.append(iter_network_flow(d, rp))
        """
        一段尝试失败的代码
            for n in DataType:
            if n is DataType.CPU or n is DataType.MEMORY:
                iters.append(globals()["iter_cpu_memory"](d, rp))
            elif n in perfs:
                iters.append(globals()[f"iter_{n.value}"])
        """
        for it in (iters):
            wg = WaitGroup()
            wg.add(1)
            wgs.append(wg)

            for _type, data in it:
                assert isinstance(data, dict)
                assert isinstance(_type, DataType)
                if isinstance(data, dict) and "time" in data:
                    stimestamp = gen_stimestamp(data.pop("time"))
                    data.update({"timestamp": stimestamp})
                if _type in perfs:
                    _perf_callback(_type, data)
                if not state():
                    break
        for w in wgs:
            w.done()
    global perf_state
    if plat == "ios":
        params = [[u.udid, bundle_id, lambda: perf_state] for u in using_device]
        TPE(max_workers=len(using_device)).map(lambda args: _ios_perf_main(*args), params)


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


class WDA_EVENTS:

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


class TIDEVICE_EVENTS:
    """
    其实直接使用原来的函数也是可以的。getattr(mi, funcname)()就行了
    但是比起用别人的函数名作为自己的参数，不如自己重命令一个，后面安卓和ios可以统一
    也不必随着别人的更新改动改自己的参数内容。
    """
    @staticmethod
    def device_date(udid, params):
        mi.cmd_date_udid(udid, params)

    @staticmethod
    def app_install(udid, params):
        mi.cmd_install_udid(udid, params)

    @staticmethod
    def app_uninstall(udid, params):
        mi.cmd_uninstall_udid(udid, params)

    @staticmethod
    def app_list(udid, params):
        mi.cmd_applist_udid(udid, params)

    @staticmethod
    def app_launch(udid, params):
        mi.cmd_launch_udid(udid, params)


class BaseClass:
    @staticmethod
    @app.post("/items/")
    def initialize(p: str, devices: Item):
        global using_device, plat
        plat = p
        using_device.clear()
        clear_file()
        if plat.lower() == "android":
            print("安卓的待完善")
        elif plat.lower() == "ios":
            syslog_save()
            for d in devices.devices:
                i = IOS_Device_Obj()
                i.udid, i.wdaurl = d.udid, d.wdaurl
                i.wda_obj = wda.Client(d.wdaurl)
                i.wda_obj.home()
                using_device.append(i)
            content = {"message": "IOS群控设备初始化成功"}
            response = JSONResponse(content=content)
            return response

    @staticmethod
    @app.post("/log_state/")
    def log_state(state: bool):
        global log_save_state
        log_save_state = state

    @staticmethod
    @app.post("/tidevice/")
    def tidevice(func: str, param: T_Obj):
        params = [[u.udid, param] for u in using_device]
        with TPE(max_workers=len(using_device)) as pool:
            pool.map(lambda args: getattr(TIDEVICE_EVENTS, func)(*args), params)
        return {"message": "Tidevice事件运行完毕"}

    @staticmethod
    @app.post("/perf/")
    def perf(bundle_id: str, state: bool):
        global perf_state
        perf_state = state
        if state:
            perf(bundle_id)


class WDA_Operation_Batch:

    @staticmethod
    @app.post("/touch/")
    def touch(pos_x: int, pos_y: int, device: str):
        def _touch_event(wda_obj):
            p = pos_trans(pos_x, pos_y, device)
            wda_obj.click(p[0], p[1])
        with TPE(max_workers=len(using_device)) as pool:
            pool.map(_touch_event, [u.wda_obj for u in using_device])
        return {"message": "click over"}

    @staticmethod
    @app.post("/swipe/")
    def swp(s_pos: Pos, e_pos: Pos, device: str):
        def _swipe_event(wda_obj):
            sp = pos_trans(s_pos.x, s_pos.y, device)
            ep = pos_trans(e_pos.x, e_pos.y, device)
            wda_obj.swipe(sp[0], sp[1], ep[0], ep[1])
        with TPE(max_workers=len(using_device)) as pool:
            pool.map(_swipe_event, [u.wda_obj for u in using_device])
        return {"message": "swipe over"}

    @staticmethod
    @app.post("/tap_hold/")
    def tap_hold(pos: Pos, device: str, t: float):
        def _tap_hold_event(wda_obj):
            p = pos_trans(pos.x, pos.y, device)
            wda_obj.tap_hold(p[0], p[1], t)
        with TPE(max_workers=len(using_device)) as pool:
            pool.map(_tap_hold_event, [u.wda_obj for u in using_device])
        return {"message": "tap_hold over"}

    @staticmethod
    @app.post("/simple_event/")
    def simple_event(event: str):
        with TPE(max_workers=len(using_device)) as pool:
            rst = pool.map(getattr(WDA_EVENTS, event), [u.wda_obj for u in using_device])
        if any([r for r in rst]):
            return [r for r in rst]
        else:
            return {"message": "run over"}


if __name__ == '__main__':
    uvicorn.run(app, host="localhost", port=8534)
