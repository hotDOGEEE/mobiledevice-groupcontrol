# ios-colonycontrol

也没啥特别的，利用wda，在atx-ios-provider的基础上，去连接wdaurl，再套用fastapi为后端，进行群控远程管理的demo

接口文档 (目前所有请求均为post)

| 接口名       | 功能介绍                                                     | 请求参数                                                     | 示例                                                         |
| ------------ | ------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ |
| plat_init    | 设备初始化，包含设备本身进行群控的准备工作和历史内容清理。   | p: str (android or ios) ,device:[{"udid":str, "wdaurl":str}] | params:p=ios, body:{"device":[{"udid":"serial1","wdaurl":"http://localhost:20002"},"udid":"serial2","wdaurl":""]} |
| log_state    | 初始化后日志即开始记录，在结束使用后停止记录所有设备日志，并使日志文件处于可被获取的状态 | state:bool                                                   | params:state=True                                            |
| tidevice     | body为json，本身是动态的，所以传入的参数也会根据对应的方法所需要的进行调整。func为可提供给用户使用的方法（有的不能提供，进行了过滤） | func:str, param:{"filepath_or_url":None,"bundle_id":None}    | params: func="app_install", body:{"filepath_or_url":"http://localhost/pags/demo.ipa"} |
| touch        | 需要提供基准设备点击的点和设备型号，作为群控操作的坐标转换   | pos_x: int, pos_y: int, device: str                          | params: pos_x=74, pos_y=76, device="iphone x"                |
| swipe        | 跟touch一样，只是把坐标封了结构体，通过body传输              | device: str,  s_pos, e_pos: {"x": int, "y": int}             | params: device="iphone x", body:{"s_pos": {"x": 200,"y": 220}, "e_pos": {"x": 100, "y": 220}} |
| tap_hold     | 长按事件，多了一个时间参数                                   | device:str, t: float, pos: {"x": int, "y": int}              | params: device="iphone x", t=1.5 body:{"x": 200,"y": 220}    |
| simple_event | 操作事件总体都属于wda的，但有些不需要参数的简单方法，总合到了这个接口下进行实现 | event:str                                                    | params: event="home"                                         |

tidevice具体方法介绍：

device_date（body:{}）, 获取设备时间

app_install(body:{"filepath_or_url":str}),  安装apk or ipa

app_uninstall(body:{"bundle_id":"com.iggcd.wda.xctrunner"}),卸载

app_list(body:{}), 应用列表

app_launch(body:{"bundle_id"}), 启动应用

群控过程中，通过界面来代替对相关接口的操作往往是不现实的。安装时长不以你操作的那个为准，安装完后应用图标出现在对应设备上的位置不一定统一，但是通过统一命令启动可以避免这些麻烦事。



simple_event具体方法介绍:

device_info: 设备基本信息，具体格式去看引用项目本身源码

home:  就是home键

lock: 锁屏

unlock: 解锁

screenshot: 截屏，截屏的文件会保存在对应运行服务器项目下的resource/ios/screenshot下，文件名格式为udid_timestamp.png

