import zmq                                              # ZeroMQ库：负责消息传递
import eventlet                                         # 异步处理库：负责协程和异步IO
import os                                               # 操作系统库：负责文件和目录的操作
import sys                                              # 系统库：负责python解释器的操作
import json                                             # JSON库：负责数据的序列化和反序列化
from flask import Flask, render_template, request       # Flask库：负责Web框架
from flask_socketio import SocketIO, emit               # Flask-SocketIO库：负责WebSocket通信
from datetime import datetime                           # datetime库：负责时间和日期的处理

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
# 创建一个订阅套接字，用于接收消息
sub_socket = context.socket(zmq.SUB)
# 获取环境变量ZMQ_HOST，如果没有设置，则使用localhost，适用于多个容器之间的通信
zmq_host = os.environ.get('ZMQ_HOST', 'localhost')
# 订阅者连接到发布者的地址
sub_socket.connect(f"tcp://{zmq_host}:5555")
# 设置订阅过滤器，空字符串表示接收所有消息
sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")

# 定义一个ZeroMQ监听器函数
# 该函数会在后台运行，负责接收消息并广播给所有客户端
def zmq_listener():
    while True:
        try:
            # 非阻塞接收信息
            msg = sub_socket.recv(flags=zmq.NOBLOCK)
        # 如果没有消息，则捕获异常
        # zmq.Again异常表示没有消息可读
        # 这里使用了socket.sleep()来让出执行权，使得在sleep期间可以处理其他事件
        except zmq.Again:
            socketio.sleep(0.01)
        # 如果接收到消息，则进行处理
        else:
            # 解析消息并广播给所有客户端
            try:
                message_data = json.loads(msg.decode('utf-8'))
                # 将消息添加到聊天历史中
                socketio.emit('chat_message', message_data)
            except Exception as e:
                print(f"消息处理错误: {e}")

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
    # 获取用户名，默认为'Anonymous'
    username = data.get('username', 'Anonymous')
    # 获取用户ID，使用request.sid作为唯一标识
    # request.sid是Flask-SocketIO为每个连接生成的唯一ID
    user_id = request.sid
    # 将用户添加到在线用户列表中
    # 使用user_id作为键，username作为值
    online_users[user_id] = username
    
    # 创建加入消息
    join_message = {
        'type': 'system',
        'username': 'System',
        'message': f'{username} 加入了聊天室',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    # 将加入消息添加到聊天历史中
    chat_history.append(join_message)
    
    # 发送历史消息给新用户
    # emit参数解释：
    # 'chat_history'：事件名称，客户端通过监听该事件来接收消息
    # {'history': chat_history[-50:]}：要发送的数据，[-50:]采用切片操作，表示只发送最近50条消息
    # 这里不进行broadcast，只将最近50条消息发送给新用户
    emit('chat_history', {'history': chat_history[-50:]})

    # 通知所有用户有新用户加入
    emit('chat_message', join_message, broadcast=True)
    
    # 更新在线用户列表
    emit('user_list', {'users': list(online_users.values())}, broadcast=True)

# 处理用户离开，disconnect无需在客户端触发
# 该事件会在用户关闭浏览器或断开连接时自动触发
@socketio.on('disconnect')
def handle_disconnect():
    user_id = request.sid
    if user_id in online_users:
        username = online_users[user_id]
        leave_message = {
            'type': 'system',
            'username': 'System',
            'message': f'{username} 离开了聊天室',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        chat_history.append(leave_message)
        # 通知所有用户有用户离开
        emit('chat_message', leave_message, broadcast=True)
        
        # 从在线用户中移除
        del online_users[user_id]
        # 更新在线用户列表
        emit('user_list', {'users': list(online_users.values())}, broadcast=True)

# 处理文本消息而非音频
@socketio.on('chat_message')
def handle_message(data):
    username = online_users.get(request.sid, 'Anonymous')
    message_data = {
        'type': 'message',
        'username': username,
        'message': data.get('message', ''),
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # 保存到历史记录
    chat_history.append(message_data)
    
    # 通过ZMQ发布消息
    pub_socket.send(json.dumps(message_data).encode('utf-8'))

# 处理语音消息
@socketio.on('voice_message')
def handle_voice_message(data):
    username = online_users.get(request.sid, 'Anonymous')
    message_data = {
        'type': 'voice',
        'username': username,
        'audio_data': data.get('audio_data', ''),
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # 直接广播到所有客户端
    emit('voice_message', message_data, broadcast=True)

if __name__ == '__main__':
    print("聊天服务器运行在 http://0.0.0.0:5002")
    try:
        # 启动Flask-SocketIO服务器
        socketio.run(app, host='0.0.0.0', port=5002, debug=True, use_reloader=False)
    except OSError as e:
        print(f"启动服务器失败: {e}")
        print("可能端口已被占用，请尝试关闭占用该端口的应用或使用不同端口")
        # 清理资源
        pub_socket.close()
        sub_socket.close()
        context.term()
        sys.exit(1)