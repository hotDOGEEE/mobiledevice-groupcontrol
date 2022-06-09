from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, File, UploadFile
from types import FunctionType
from structbody import *
from common import *
from fastapi.responses import JSONResponse
from concurrent.futures import ThreadPoolExecutor as TPE
from tidevice import __main__ as mi
from tidevice._perf import RunningProcess, WaitGroup, iter_cpu_memory, iter_fps, iter_gpu, set_interval, iter_screenshot, iter_network_flow, gen_stimestamp
from tidevice import Device, DataType
import time
import shutil
import os
import pathlib
import sys
import uvicorn
import subprocess

app = FastAPI()
using_device = list()
resource_type = ["logs", "pags", "screenshot"]

uploads = "uploads"
uploads_dir = pathlib.Path(os.getcwd(), uploads)
android_pag_path = "/data/local/tmp/apks"
plat = "ios"
log_save_state = False
perf_state = False
perfs = [DataType.CPU, DataType.MEMORY, DataType.NETWORK, DataType.FPS, DataType.PAGE, DataType.SCREENSHOT, DataType.GPU]


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
    elif plat == "android":
        # 方式为记录设备日志缓存的方式
        pl = [subprocess.Popen(f"adb -s {u.udid} logcat -d > resource/{plat}/logs/{u.udid}.log", shell=True) for u in using_device]
        [p.wait() for p in pl]


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


class SIMP_EVENTS:

    @classmethod
    def home(cls, u):
        u.wda_obj.home()

    @classmethod
    def lock(cls, u):
        u.wda_obj.lock()

    @classmethod
    def unlock(cls, u):
        u.wda_obj.unlock()

    @classmethod
    def screenshot(cls, u):
        device = [ud.udid for ud in using_device if id(ud.wda_obj) == id(u.wda_obj)][0]
        u.wda_obj.screenshot().save(f"resource/screenshot/{device}_{time.time()}.png")

    @classmethod
    def device_info(cls, u):
        return u.wda_obj.device_info()


class TIDEVICE_EVENTS:
    """
    其实直接使用原来的函数也是可以的。getattr(mi, funcname)()就行了
    但是比起用别人的函数名作为自己的参数，不如自己重命令一个，后面安卓和ios可以统一
    也不必随着别人的更新改动改自己的参数内容。
    """
    @classmethod
    def device_date(cls, udid, params):
        mi.cmd_date_udid(udid, params)

    @classmethod
    def app_install(cls, udid, params):
        mi.cmd_install_udid(udid, params)

    @classmethod
    def app_uninstall(cls, udid, params):
        mi.cmd_uninstall_udid(udid, params)

    @classmethod
    def app_list(cls, udid, params):
        return mi.cmd_applist_udid(udid, params)

    @classmethod
    def app_launch(cls, udid, params):
        mi.cmd_launch_udid(udid, params)


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
            rst = pool.map(getattr(SIMP_EVENTS, event), using_device)
        if any(rst):
            return rst
        else:
            return {"message": "run over"}


class BaseClass:
    base_root = "/api"
    @staticmethod
    @app.post(f"{base_root}/plat_init/")
    def initialize(p: str, devices: Item):
        global using_device, plat
        plat = p
        using_device.clear()
        clear_file()
        if plat.lower() == "android":
            for d in devices.devices:
                a = Android_Device_Obj()
                a.udid = d.udid
                a.model = Android_Event.adb_event(a.udid, "shell getprop ro.product.model")[0].decode()
                Android_Event.adb_event(a.udid, "shell input keyevent 3")
                using_device.append(a)
            content = {"message": "android群控设备初始化成功"}
        elif plat.lower() == "ios":
            for d in devices.devices:
                i = IOS_Device_Obj()
                i.udid, i.wdaurl = d.udid, d.wdaurl
                i.wda_obj = wda.Client(d.wdaurl)
                i.wda_obj.home()
                using_device.append(i)
            content = {"message": "IOS群控设备初始化成功"}
        else:
            raise HTTPException(status_code=403, detail="plat not exist")
        syslog_save()
        response = JSONResponse(content=content)
        return response

    @staticmethod
    @app.post(f"{base_root}/adb_event")
    def adb_event(shell: str):
        with TPE(max_workers=len(using_device)) as pool:
            params = [[u.udid, shell] for u in using_device]
            rst = pool.map(lambda args: getattr(Android_Event, "adb_event")(*args), params)
        return rst

    @staticmethod
    @app.post(f"{base_root}/log_state/")
    def log_state(state: bool):
        global log_save_state
        log_save_state = state

    @staticmethod
    @app.post(f"{base_root}/apk_install")
    async def apk_install(file: UploadFile = File(...)):
        def _install(serial):
            Android_Event.adb_event(serial, f"shell rm -rf {android_pag_path}")
            Android_Event.adb_event(serial, f"shell mkdir {android_pag_path}")
            Android_Event.adb_event(serial, f"push {file.filename} {android_pag_path}")
            Android_Event.adb_event(serial, f"shell pm install {android_pag_path}/{file.filename}")
            # 以下是安装结果检查部分，不用原本的succes，用有没有包更严谨一些，不用那个结果。

        def _install_check(serial):
            r = Android_Event.adb_event(serial, "shell pm list packages")
            rst = [i for i in r if pagname in i]
            if any(rst):
                return True
            return False, serial
        res = await file.read()
        with open(file.filename, "wb") as f:
            f.write(res)
        p = subprocess.Popen(f"aapt dump badging {file.filename}", shell=True,
                             stdout=subprocess.PIPE)
        rst = p.stdout.readlines()[0]
        pagname = rst.split(b"'")[1]
        with TPE(max_workers=len(using_device)) as pool:
            params = [u.udid for u in using_device]
            pool.map(_install, params)
            r = pool.map(_install_check, params)
        content = {"pagname": pagname, "install_rst": r}
        response = JSONResponse(content=content)
        return response

    @staticmethod
    @app.post(f"{base_root}/tidevice/")
    def tidevice(fc: str, param: T_Obj):
        params = [[u.udid, param] for u in using_device]
        with TPE(max_workers=len(using_device)) as pool:
            rst = pool.map(lambda args: getattr(TIDEVICE_EVENTS, fc)(*args), params)
        return {"message": [r for r in rst]}

    @staticmethod
    @app.post(f"{base_root}/perf/")
    def perf(bundle_id: str, state: bool):
        global perf_state
        perf_state = state
        if state:
            perf(bundle_id)

    @staticmethod
    @app.websocket(f"{base_root}/scrcpy")
    async def scrcpy(websocket: WebSocket):
        # 会在initialize中输入平台android的时候对所有ws进行初始化
        await websocket.accept()
        base_serial = await websocket.receive_bytes()
        # 第一条消息必须是基准设备的设备号
        base_serial = base_serial.decode()
        s_launch = ScrcpyLauncher(base_serial, using_device)
        try:
            while True:
                b_data = await websocket.receive_bytes()
                s_launch.broadcast(b_data)
        except WebSocketDisconnect:
            s_launch.teardown()

    @staticmethod
    @app.post(f"{base_root}/functest/")
    def functest():
        p = subprocess.Popen("adb devices", shell=True, stdout=subprocess.PIPE)
        rst = p.stdout.readlines()
        return rst


if __name__ == '__main__':
    uvicorn.run(app, host="localhost", port=8534)
