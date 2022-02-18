# ios-colonycontrol

也没啥特别的，利用wda，在atx-ios-provider的基础上，去连接wdaurl，再套用fastapi为后端，进行群控远程管理的demo

接口文档

​			

| 接口名    | 功能介绍                                                     | 请求参数                                                     | 示例                                                         |
| --------- | ------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ |
| plat_init | 设备初始化，包含设备本身进行群控的准备工作和历史内容清理。   | p: str (android or ios) ,device:[{"udid":str, "wdaurl":str}] | params:p=ios, body:{"device":[{"udid":"serial1","wdaurl":"http://localhost:20002"},"udid":"serial2","wdaurl":""]} |
| log_state | 初始化后日志即开始记录，在结束使用后停止记录所有设备日志，并使日志文件处于可被获取的状态 | state:bool                                                   | params:state=True                                            |
| tidevice  | body为json，本身是动态的，所以传入的参数也会根据对应的方法所需要的进行调整。func为可提供给用户使用的方法（有的不能提供，进行了过滤）：device_date（body:{}）, app_install(body:{"filepath_or_url":str}),app_uninstall(body:{"bundle_id":"com.iggcd.wda.xctrunner"}),app_uninstall{"bundle_id"},app_list(body:{}), app_launch(body:{"bundle_id"}) | func:str, param:{"filepath_or_url":None,"bundle_id":None}    | params: func="app_install", body:{"filepath_or_url":"http://localhost/pags/demo.ipa"} |
| touch     | 需要提供基准设备点击的点和设备型号，作为群控操作的坐标转换   | pos_x: int, pos_y: int, device: str                          | params: pos_x=74, pos_y=76, device="type"                    |
| swipe     |                                                              | paramss_pos:                                                 |                                                              |
|           |                                                              |                                                              |                                                              |
|           |                                                              |                                                              |                                                              |
|           |                                                              |                                                              |                                                              |
|           |                                                              |                                                              |                                                              |
|           |                                                              |                                                              |                                                              |
|           |                                                              |                                                              |                                                              |
|           |                                                              |                                                              |                                                              |
|           |                                                              |                                                              |                                                              |
|           |                                                              |                                                              |                                                              |

