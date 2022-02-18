# ios-colonycontrol

也没啥特别的，利用wda，在atx-ios-provider的基础上，去连接wdaurl，再套用fastapi为后端，进行群控远程管理的demo

接口文档

​			

| 模块                | 接口名    | 请求方式 | 请求参数                                                     | 示例                                                         | 功能介绍                                                     |
| ------------------- | --------- | -------- | ------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ |
| BaseClass           | plat_init | post     | p: str (android or ios) ,device:[{"udid":str, "wdaurl":str}] | params:p=ios, body:{"device":[{"udid":"serial1","wdaurl":"http://localhost:20002"},"udid":"serial2","wdaurl":""]} | 设备初始化，包含设备本身进行群控的准备工作和历史内容清理。   |
|                     | log_state | post     | state:bool                                                   | params:state=True                                            | 初始化后日志即开始记录，在结束使用后停止记录所有设备日志，并使日志文件处于可被获取的状态 |
|                     | tidevice  | post     | func:str, param:{"filepath_or_url":None,"bundle_id":None}    | params: func="app_install", body:{"filepath_or_url":"http://localhost/pags/demo.ipa"} | body为json，本身是动态的，所以传入的参数也会根据对应的方法所需要的进行调整。func为可提供给用户使用的方法（有的不能提供，进行了过滤）：device_date（body:{}）, app_install(body:{"filepath_or_url":str}),app_uninstall(body:{"bundle_id":"com.iggcd.wda.xctrunner"}),app_uninstall{"bundle_id"},app_list(body:{}), app_launch(body:{"bundle_id"}) |
| WDA_Operation_Batch | touch     | post     | pos_x: int, pos_y: int, device: str                          | params: pos_x=74, pos_y=76, device="type"                    | 需要提供基准设备点击的点和设备型号，作为群控操作的坐标转换   |
|                     | swipe     | post     | paramss_pos:                                                 |                                                              |                                                              |
|                     |           |          |                                                              |                                                              |                                                              |
|                     |           |          |                                                              |                                                              |                                                              |
|                     |           |          |                                                              |                                                              |                                                              |
|                     |           |          |                                                              |                                                              |                                                              |
|                     |           |          |                                                              |                                                              |                                                              |
|                     |           |          |                                                              |                                                              |                                                              |
|                     |           |          |                                                              |                                                              |                                                              |
|                     |           |          |                                                              |                                                              |                                                              |
|                     |           |          |                                                              |                                                              |                                                              |

