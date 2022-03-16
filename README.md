# mobiledevice-groupcontrol

也没啥特别的，利用wda，在atx-ios-provider的基础上，去连接wdaurl，再套用fastapi为后端，进行群控远程管理的demo
总体架构
![](https://s3.bmp.ovh/imgs/2022/02/5a98049be291c4b6.png)

接口文档 (目前所有请求均为post)
![](https://s3.bmp.ovh/imgs/2022/02/56ec6c216bf82c7b.png)

tidevice具体方法介绍：

- device_date（body:{}）, 获取设备时间
- app_install(body:{"filepath_or_url":str}),  安装apk or ipa
- app_uninstall(body:{"bundle_id":"com.iggcd.wda.xctrunner"}),卸载
- app_list(body:{}), 应用列表
- app_launch(body:{"bundle_id"}), 启动应用

群控过程中，通过界面来代替对相关接口的操作往往是不现实的。安装时长不以你操作的那个为准，安装完后应用图标出现在对应设备上的位置不一定统一，但是通过统一命令启动可以避免这些麻烦事。



simple_event具体方法介绍:

- device_info: 设备基本信息，具体格式去看引用项目本身源码
- home:  就是home键
- lock: 锁屏
- unlock: 解锁
- screenshot: 截屏，截屏的文件会保存在对应运行服务器项目下的resource/ios/screenshot下，文件名格式为udid_timestamp.png


tidevice部分就是通过命令行自己简单的复写了一遍直接传参的方法。方便接口调用而已

## 环境

python3.7+

pip install -r requirements.txt

需要手动安装的部分

pip install uvicorn[standard]

pip install -U "tidevice[openssl]"




