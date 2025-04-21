
# README

## 项目介绍

web-chat是一个基于Python Flask部署的Web聊天室应用，支持文字聊天和语音聊天功能。用户可以使用自定义的用户名加入聊天室，所有消息实时显示，同时能查看当前在线用户列表。

## 主要功能

- **多用户聊天**：支持多个用户同时在线聊天
- **用户名自定义**：用户可自由设置个性化的显示名称
- **实时消息**：文字消息和语音消息即时传输和显示
- **语音聊天支持**：可通过麦克风录制并发送语音消息
- **在线状态显示**：实时更新并展示当前在线用户列表

## 项目特点

- 基于Web技术构建，无需安装客户端
- Docker技术支持跨平台使用（Windows, macOS, Linux, 移动设备）
- 使用Socket.IO实现低延迟实时通信
- 采用ZeroMQ增强消息传递的可靠性和效率


## 技术栈

- 前端：HTML5, CSS3, JavaScript, Socket.IO
- 后端：Flask, Python, SocketIO
- 实时通信：Socket.IO, ZeroMQ
- 异步处理：eventlet

## 项目结构

```
.
├── static/               # 静态文件目录
│   └── main.js           # 前端核心交互逻辑
├── templates/            # 模板文件目录
│   └── index.html        # 网页界面
├── server.py             # Flask后端服务
├── requirements.txt      # 项目依赖
├── Dockerfile            # Docker构建文件
└── README.md
```

## 运行环境要求

- Python 3.6+
- 现代浏览器（Chrome, Firefox, Safari等）

## 安装与运行

### 基础运行（非Docker）

1. 克隆项目仓库

```
git clone https://github.com/SowingG2333/web-chat
cd web-chat
```

2. 创建并激活虚拟环境（推荐）  

3. 安装依赖

```
pip install -r requirements.txt
```

4. 启动服务

```
flask run --host localhost --port 5002
```

5. 打开浏览器访问

```
http://localhost:5002
```

### Docker部署

1. 确保已安装Docker和Docker Compose

2. 构建镜像

```
docker build -t web-chatroom .
```

3. 启动容器

```
docker run -p 5002:5002 web-chatroom
```

4. 访问应用

```
http://localhost:5002
```

## 使用说明

1. 打开网页后，输入用户名并点击"进入聊天室"
2. 文字聊天：
   - 在输入框中输入文本内容
   - 点击"发送"按钮或按Enter键发送消息
3. 语音聊天：
   - 点击并按住"按住录制语音"按钮
   - 松开按钮或鼠标离开按钮时自动发送语音消息
   - 点击消息中的播放按钮可收听语音内容
4. 查看在线用户列表：聊天界面右侧边栏显示当前所有在线用户

## 项目依赖

- Flask==2.0.1
- flask-socketio==5.1.1
- python-socketio==5.4.0
- eventlet==0.30.2
- pyzmq==22.3.0
- python-engineio==4.3.0
- dnspython==1.16.0

