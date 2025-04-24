import zmq                                              # ZeroMQ库：负责消息传递
import eventlet                                         # 异步处理库：负责协程和异步IO
import os                                               # 操作系统库：负责文件和目录的操作
import sys                                              # 系统库：负责python解释器的操作
import json                                             # JSON库：负责数据的序列化和反序列化
from flask import Flask, render_template, request       # Flask库：负责Web框架
from flask_socketio import SocketIO, emit               # Flask-SocketIO库：负责WebSocket通信
from datetime import datetime                           # datetime库：负责时间和日期的处理
import signal                                           # 信号处理库：负责处理系统信号

# 使用eventlet进行异步处理 解决Flask-SocketIO与ZeroMQ的阻塞问题
eventlet.monkey_patch()

# 实例化Flask应用
app = Flask(__name__)
# 设置Flask的session密钥（实际应用中应使用更复杂的密钥）
app.config['SECRET_KEY'] = 'secret_key_for_session'
# 设置socketIO的异步模式为eventlet
# 参数解释：
# async_mode='eventlet'：使用eventlet作为异步模式
# cors_allowed_origins='*'：允许所有跨域请求
# logger=True：启用日志记录
# engineio_logger=True：启用engineio的日志记录，用于调试
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins='*', logger=True, engineio_logger=True)

# 存储聊天消息历史
chat_history = []
# 存储在线用户
online_users = {}

# ZeroMQ配置
# 创建一个ZeroMQ上下文，用于统一管理套接字
# 这里使用了zmq.PUB和zmq.SUB模式，分别用于发布和订阅消息
context = zmq.Context()
# 创建一个发布套接字，用于发送消息
pub_socket = context.socket(zmq.PUB)
try:
    # 绑定到所有网络接口，在容器中使用
    # 容器中可能会有多个网络接口，使用*表示绑定到所有接口
    pub_socket.bind("tcp://*:5555")
# 如果绑定失败，可能是端口已被占用
except zmq.error.ZMQError as e:
    print(f"ZMQ错误: {e}")
    sys.exit(1)

# 支持多个ZMQ_HOST
zmq_hosts = os.environ.get('ZMQ_HOST', 'localhost').split(',')
sub_sockets = []
print(f"ZMQ主机列表: {zmq_hosts}")

# 为每个主机创建一个订阅socket
def connect_to_zmq_hosts():
    global sub_sockets
    # 清空现有socket列表
    for sock in sub_sockets:
        sock.close()
    sub_sockets = []
    
    # 为每个主机创建新的socket连接
    for host in zmq_hosts:
        if host.strip():
            retry_count = 0
            max_retries = 5
            connected = False
            
            while not connected and retry_count < max_retries:
                try:
                    sub_socket = context.socket(zmq.SUB)
                    print(f"尝试连接到ZMQ主机: {host.strip()} (尝试 {retry_count+1}/{max_retries})")
                    sub_socket.connect(f"tcp://{host.strip()}:5555")
                    sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
                    sub_sockets.append(sub_socket)
                    connected = True
                    print(f"成功连接到ZMQ主机: {host.strip()}")
                except zmq.error.ZMQError as e:
                    retry_count += 1
                    print(f"连接到 {host.strip()} 失败: {e}，将在5秒后重试")
                    socketio.sleep(5)  # 使用socketio.sleep而不是time.sleep保持异步
            
            if not connected:
                print(f"无法连接到ZMQ主机: {host.strip()}，已达到最大重试次数")

# 启动一个后台任务来处理ZMQ连接
socketio.start_background_task(connect_to_zmq_hosts)

def zmq_listener():
    while True:
        for sock in sub_sockets:
            try:
                msg = sock.recv(flags=zmq.NOBLOCK)
                message_data = json.loads(msg.decode('utf-8'))
                
                # 根据消息类型处理
                if message_data.get('type') == 'system':
                    # 处理系统消息
                    if 'online_users' in message_data:
                        remote_users = message_data['online_users']
                        socketio.emit('user_list', {'users': remote_users})
                    
                    socketio.emit('chat_message', message_data)
                    
                elif message_data.get('type') == 'voice':
                    # 处理语音消息
                    socketio.emit('voice_message', message_data)
                else:
                    # 处理文本消息
                    socketio.emit('chat_message', message_data)
                    
            except zmq.Again:
                pass
            except Exception as e:
                print(f"消息处理错误: {e}")
                
        socketio.sleep(0.01)

# 启动ZeroMQ监听器
# 使用socketio.start_background_task()来启动一个后台任务
socketio.start_background_task(zmq_listener)

# 定义Flask路由
# 当用户访问根目录时，返回index.html模板
@app.route('/')
def index():
    return render_template('index.html')

# 当用户访问/history时，返回聊天历史记录
# 这里使用了一个API接口，返回最近50条消息
@app.route('/history')
def get_history():
    return {'history': chat_history[-50:]}  # 返回最近50条消息

# 处理用户加入聊天室，join事件来自客户端
@socketio.on('join')
def handle_join(data):
    username = data.get('username', 'Anonymous')
    user_id = request.sid
    online_users[user_id] = username
    
    # 包含完整的用户列表
    join_message = {
        'type': 'system',
        'event': 'join',
        'username': 'System',
        'user_joined': username,
        'message': f'{username} 加入了聊天室',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'online_users': list(online_users.values())  # 包含用户列表
    }
    chat_history.append(join_message)
    
    # 发送历史消息只给当前用户
    emit('chat_history', {'history': chat_history[-50:]})
    
    # 本地广播用户列表更新
    emit('user_list', {'users': list(online_users.values())}, broadcast=True)
    
    # 通过ZeroMQ广播加入消息
    pub_socket.send(json.dumps(join_message).encode('utf-8'))

# 处理用户离开，disconnect无需在客户端触发
# 该事件会在用户关闭浏览器或断开连接时自动触发
@socketio.on('disconnect')
def handle_disconnect():
    user_id = request.sid
    if user_id in online_users:
        username = online_users[user_id]
        leave_message = {
            'type': 'system',
            'event': 'leave',  # 添加事件类型
            'username': 'System',
            'user_left': username,  # 记录谁离开了
            'message': f'{username} 离开了聊天室',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        chat_history.append(leave_message)
        
        # 通过ZeroMQ广播离开消息
        pub_socket.send(json.dumps(leave_message).encode('utf-8'))
        
        # 本地处理
        del online_users[user_id]
        emit('user_list', {'users': list(online_users.values())}, broadcast=True)

# 修改handle_message函数，添加消息ID
@socketio.on('chat_message')
def handle_message(data):
    username = online_users.get(request.sid, 'Anonymous')
    # 生成唯一消息ID (使用时间戳和用户ID)
    message_id = f"{request.sid}-{datetime.now().timestamp()}"
    message_data = {
        'type': 'message',
        'username': username,
        'message': data.get('message', ''),
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'message_id': message_id  # 添加消息ID
    }
    
    # 保存到历史记录
    chat_history.append(message_data)
    
    # 先直接在本地广播，确保发送者能看到自己的消息
    emit('chat_message', message_data, broadcast=True)
    
    # 然后通过ZMQ发布消息给其他服务器
    pub_socket.send(json.dumps(message_data).encode('utf-8'))

# 处理语音消息
@socketio.on('voice_message')
def handle_voice_message(data):
    username = online_users.get(request.sid, 'Anonymous')
    # 生成唯一消息ID
    message_id = f"{request.sid}-voice-{datetime.now().timestamp()}"
    message_data = {
        'type': 'voice',
        'username': username,
        'audio_data': data.get('audio_data', ''),
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'message_id': message_id
    }
    
    # 直接广播到所有客户端
    emit('voice_message', message_data, broadcast=True)
    
    # 通过ZeroMQ发布给其他服务器
    pub_socket.send(json.dumps(message_data).encode('utf-8'))

if __name__ == '__main__':
    # 从环境变量获取端口，默认5002
    port = int(os.environ.get('PORT', 5002))
    
    # 定义信号处理函数，确保容器优雅关闭
    def signal_handler(sig, frame):
        print("正在关闭服务器...")
        pub_socket.close()
        for sock in sub_sockets:
            sock.close()
        context.term()
        sys.exit(0)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print(f"聊天服务器运行在 0.0.0.0:{port}")
    try:
        # 启动Flask-SocketIO服务器
        socketio.run(app, host='localhost', port=port, debug=True, use_reloader=False)
    except OSError as e:
        print(f"启动服务器失败: {e}")
        print("可能端口已被占用，请尝试关闭占用该端口的应用或使用不同端口")
        # 清理资源
        pub_socket.close()
        for sock in sub_sockets:
            sock.close()
        context.term()
        sys.exit(1)