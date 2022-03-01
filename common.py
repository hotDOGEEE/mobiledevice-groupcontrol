import subprocess
import websocket
import threading
import struct

ios_screen_size = {"iphone 6": [375, 667],
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

k0 = "screen"
k1 = "touch-player"
android_screen_size = {"Pixel 5": {k0: [1080, 2340], k1: [320, 720]},
                       "vivo X20": {k0: [1080, 2160], k1: [352, 720]}}


def pos_trans(pos_x: int, pos_y: int, device=None, size=None):
    if device:
        if device.lower() in list(ios_screen_size.keys()):
            size = ios_screen_size[device]
    elif size:
        size = [size[:3], size[-3:]]
    pos_x = round(pos_x / size[0], 2)
    pos_y = round(pos_y / size[1], 2)
    return pos_x, pos_y


class Android_Event:
    @classmethod
    def device_list(cls):
        dl = []
        p = subprocess.Popen("adb devices", shell=True, stdout=subprocess.PIPE)
        rst = p.stdout.readlines()
        for r in rst[1:-1]:
            if d:= r.split(b"\t")[0].decode():
                dl.append(d)
        return dl

    @classmethod
    def adb_event(cls, serial, shell):
        p = subprocess.Popen(f"adb -s {serial} {shell}", shell=True, stdout=subprocess.PIPE)
        # 其实正常该分一下，有没有用adb shell的命令，shell与终端相关，需要wait一下.不过readlines自带这个过程
        rst = p.stdout.readlines()
        return rst

    @classmethod
    def device_init(cls, serial):
        # 这里要对安卓版本做一个区分
        if int(subprocess.Popen(f"adb -s {serial} shell getprop ro.build.version.release",
                       shell=True, stdout=subprocess.PIPE).stdout.read().decode().split(".")[0]) > 8:
            rst = subprocess.Popen(f"adb -s {serial} shell dumpsys window policy", shell=True, stdout=subprocess.PIPE).stdout.readlines()
            if any([True for r in rst if "screenState=SCREEN_STATE_OFF" in r.decode()]):
                subprocess.Popen(f"adb {serial} shell input keyevent 26")
        else:
            rst = subprocess.Popen(f"adb -s {serial} shell dumpsys power", shell=True, stdout=subprocess.PIPE).stdout.readlines()
            if [True for r in rst if "Display Power: state=OFF" in r.decode()]:
                subprocess.Popen(f"adb {serial} shell input keyevent 26")


class ScrcpyLauncher:
    def __init__(self, base_device, devices):
        def _on_open(wsapp):
            wsapp.sock.send_binary(
                b'e\x00p\x00\x00\x00\x00\x00<\n\x02\xd0\x02\xd0\x00\x00\x00\x00\x00\x00'
                b'\x00\x00\x00\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')

        self.base_device = [d for d in devices if d.udid == base_device][0]
        self.devices = devices
        self.wsapp_list = [websocket.WebSocketApp(f"ws://10.23.27.196:8000/?action=proxy-adb&remote=tcp%3A8886&udid={d}",
                                   on_open=_on_open,) for d in [d.udid for d in self.devices]]
        [threading.Thread(target=w.run_forever).start() for w in self.wsapp_list]
        # 两秒给设备做一个缓冲

    def broadcast(self, message: bytes):
        # 叫他broad是因为他是一种广播的形式，但不是广播的通信。借用一下名字，通过join来确保所有设备的并发过程都已完成
        # 目前使用的是统一的message，但message中一定是对特定设备进行操作的，需要在初始化的时候指定设备型号作为基础设备，再进行算法转换
        # 嗯 至于怎么转换，就是另一个功能了
        # 先把坐标摘出来，读base设备是哪一个，读对应的touch-player size 转换为百分数，×上其他设备的touch-player size
        x_point = struct.unpack(">H", message[12:14])[0]
        y_point = struct.unpack(">H", message[16:18])[0]
        index = android_screen_size[self.base_device.model][k1]
        x_percent, y_percent = x_point / index[0], y_point / index[1]

        def _send_t():
            for i in range(len(self.devices)):
                index = android_screen_size[self.devices[i].model][k1]
                x_point, y_point = x_percent * index[0], y_percent * index[1]
                x, y = struct.pack(">H", x_point[0]), struct.pack(">H", y_point[1]),
                m = message[:12] + x + message[14:16] + y + message[18:]
                yield threading.Thread(target=self.wsapp_list[i].sock.send_binary, args=(m,))
        t_broad = [next(_send_t()) for _ in range(len(self.devices))]
        [t.start() for t in t_broad]
        [t.join() for t in t_broad]

    def teardown(self):
        [w.close() for w in self.wsapp_list]