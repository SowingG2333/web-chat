from flask import Flask, render_template, request, session
from flask_socketio import SocketIO, emit, join_room, leave_room
import zmq
import threading
import eventlet
import os
import sys
import json
from datetime import datetime

eventlet.monkey_patch()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key_for_session'
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins='*', logger=True, engineio_logger=True)

# 存储聊天消息历史
chat_history = []
# 存储在线用户
online_users = {}

# ZeroMQ PUB/SUB setup
context = zmq.Context()
pub_socket = context.socket(zmq.PUB)
try:
    # 绑定到所有网络接口，在容器中使用
    pub_socket.bind("tcp://*:5555")
except zmq.error.ZMQError as e:
    print(f"ZMQ错误: {e}")
    sys.exit(1)

sub_socket = context.socket(zmq.SUB)
# 在容器中使用localhost或容器主机名
zmq_host = os.environ.get('ZMQ_HOST', 'localhost')
sub_socket.connect(f"tcp://{zmq_host}:5555")
sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")

def zmq_listener():
    while True:
        try:
            # 非阻塞接收
            msg = sub_socket.recv(flags=zmq.NOBLOCK)
        except zmq.Again:
            # 没有消息时让出执行权，避免阻塞
            socketio.sleep(0.01)
        else:
            # 解析消息并广播给所有客户端
            try:
                message_data = json.loads(msg.decode('utf-8'))
                socketio.emit('chat_message', message_data)
            except Exception as e:
                print(f"消息处理错误: {e}")

# Start ZeroMQ listener using eventlet green thread instead of blocking Thread
socketio.start_background_task(zmq_listener)

# Serve main page
@app.route('/')
def index():
    return render_template('index.html')

# 获取聊天历史
@app.route('/history')
def get_history():
    return {'history': chat_history[-50:]}  # 返回最近50条消息

# 处理用户加入
@socketio.on('join')
def handle_join(data):
    username = data.get('username', 'Anonymous')
    user_id = request.sid
    online_users[user_id] = username
    
    # 创建加入消息
    join_message = {
        'type': 'system',
        'username': 'System',
        'message': f'{username} 加入了聊天室',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    chat_history.append(join_message)
    
    # 发送历史消息给新用户
    emit('chat_history', {'history': chat_history[-50:]})
    # 通知所有用户有新用户加入
    emit('chat_message', join_message, broadcast=True)
    
    # 更新在线用户列表
    emit('user_list', {'users': list(online_users.values())}, broadcast=True)

# 处理用户离开
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
        socketio.run(app, host='0.0.0.0', port=5002, debug=True, use_reloader=False)
    except OSError as e:
        print(f"启动服务器失败: {e}")
        print("可能端口已被占用，请尝试关闭占用该端口的应用或使用不同端口")
        # 清理资源
        pub_socket.close()
        sub_socket.close()
        context.term()
        sys.exit(1)