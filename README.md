# web-chat：分布式实时聊天系统

## 项目概述

这是一个基于WebSocket和ZeroMQ的分布式实时聊天系统，支持多服务器部署、文本和语音消息，以及跨容器通信。系统采用双层通信架构，提供高可用性和可扩展性。

## 主要特性

- ✅ 实时文本消息交换
- ✅ 语音消息支持
- ✅ 多服务器分布式部署
- ✅ 用户在线状态同步
- ✅ 消息历史记录
- ✅ 容器化部署支持
- ✅ 资源管理和错误处理

## 技术栈

- **后端**：Python, Flask, Flask-SocketIO, ZeroMQ, Eventlet
- **前端**：HTML5, CSS3, JavaScript, Socket.IO客户端
- **部署**：Docker, Docker Compose

## 系统架构

系统采用双层通信架构：

1. **客户端-服务器通信层**：使用Socket.IO实现WebSocket通信
2. **服务器间通信层**：使用ZeroMQ的PUB-SUB模式实现消息同步

## 安装与部署

### 本地开发环境

1. 克隆仓库
   ```bash
   git clone https://github.com/yourusername/web-chat.git
   cd web-chat
   ```

2. 安装依赖
   ```bash
   pip install requirements.txt
   ```

3. 启动服务器
   ```bash
   python server.py
   ```

4. 访问 http://localhost:5002

### 多实例本地部署

```bash
# 第一个实例
PORT=5002 ZMQ_HOST=localhost python server.py

# 第二个实例
PORT=5003 ZMQ_HOST=localhost python server.py
```

### Docker容器部署

1. 构建Docker镜像
   ```bash
   docker build -t web-chat .
   ```

2. 创建Docker网络
   ```bash
   docker network create chat-network
   ```

3. 启动多个容器
   ```bash
   # 容器A
   docker run -d --name chat-a --network chat-network -p 5001:5002 -e ZMQ_HOST=chat-b,chat-c web-chat

   # 容器B
   docker run -d --name chat-b --network chat-network -p 5003:5002 -e ZMQ_HOST=chat-a,chat-c web-chat

   # 容器C
   docker run -d --name chat-c --network chat-network -p 5004:5002 -e ZMQ_HOST=chat-a,chat-b web-chat
   ```

## 使用指南

1. 打开浏览器访问聊天应用
2. 输入用户名加入聊天室
3. 发送文本消息或录制语音消息
4. 查看在线用户列表和系统状态信息

## 项目结构

```
web-chat/
├── server.py         # 主服务器代码
├── templates/        # HTML模板
│   └── index.html    # 主页面
├── static/           # 静态资源
│   ├── main.js       # 前端JavaScript
│   └── style.css     # CSS样式
├── Dockerfile        # Docker构建文件
└── README.md         # 项目文档
```

## 开发者文档

### 核心模块

- **Flask应用**：提供HTTP服务和API端点
- **Socket.IO**：处理WebSocket实时通信
- **ZeroMQ PUB-SUB**：实现服务器间消息同步
- **Eventlet**：处理异步I/O，避免阻塞

### 消息流处理

1. 客户端发送消息到Socket.IO
2. 服务器处理并保存到本地历史记录
3. 服务器通过ZeroMQ发布消息
4. 其他服务器订阅并接收消息
5. 其他服务器向各自的客户端广播消息

### 添加新功能

添加新消息类型：
1. 扩展前端UI处理新消息类型
2. 在服务器端添加新的Socket.IO事件处理函数
3. 确保ZeroMQ监听器能处理新的消息类型

## 许可证

[MIT License](https://opensource.org/licenses/MIT)

## 联系方式

如有问题或建议，请联系：donghangduan@gmail.com
