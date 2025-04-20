// Socket.IO客户端连接
const socket = io();
let username = '';
let isRecordingVoiceMsg = false;
let voiceMsgChunks = [];
let voiceMsgRecorder = null;

// 一系列事件监听器和函数，用于处理聊天消息、用户列表、语音消息等功能
// 登录相关功能
document.getElementById('btn-join').addEventListener('click', () => {
    // 获取用户名
    username = document.getElementById('username-input').value.trim();
    // 检查用户名是否为空，如果不为空则加入聊天室
    if (username) {
        // 发送加入聊天室的请求，后端执行join事件
        socket.emit('join', { username });
        document.getElementById('login-screen').classList.add('hidden');
        document.getElementById('chat-screen').classList.remove('hidden');
    } else {
        alert('请输入用户名');
    }
});

// 按Enter键也可以发送消息
document.getElementById('username-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        document.getElementById('btn-join').click();
    }
});

// 语音消息相关功能，如果按下按钮则开始录制语音消息，松开按钮则停止录制，如果鼠标离开按钮也停止录制
document.getElementById('btn-record-voice').addEventListener('mousedown', startRecordingVoiceMsg);
document.getElementById('btn-record-voice').addEventListener('mouseup', stopRecordingVoiceMsg);
document.getElementById('btn-record-voice').addEventListener('mouseleave', stopRecordingVoiceMsg);

// 增加触摸设备支持
document.getElementById('btn-record-voice').addEventListener('touchstart', function(e) {
    // 阻止默认行为，在移动设备上，触摸事件会触发点击事件
    // 这可能会导致录制和发送语音消息的冲突
    // 例如，触摸时开始录制，但在松开时又触发了点击事件，与非触摸设备的行为冲突，导致再次发送语音消息
    e.preventDefault();
    startRecordingVoiceMsg();
});

document.getElementById('btn-record-voice').addEventListener('touchend', function(e) {
    e.preventDefault();
    stopRecordingVoiceMsg();
});

document.getElementById('btn-record-voice').addEventListener('touchcancel', function(e) {
    e.preventDefault();
    stopRecordingVoiceMsg();
});

// 语音消息录制和发送，async函数声明一个异步函数，即使没有返回值也会返回一个fulfilled Promise
// async函数内部可以使用await关键字来等待Promise的结果
async function startRecordingVoiceMsg() {
    // 如果正在录制语音消息，则不再执行
    if (isRecordingVoiceMsg) return;
    
    try {
        // 获取麦克风权限，await会等待Promise完成
        // 如果用户拒绝了麦克风权限，则会抛出异常，运行到catch语句
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        voiceMsgChunks = [];
        
        voiceMsgRecorder = new MediaRecorder(stream);
        
        voiceMsgRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) {
                voiceMsgChunks.push(e.data);
            }
        };
        
        voiceMsgRecorder.onstop = sendVoiceMessage;
        
        voiceMsgRecorder.start();
        isRecordingVoiceMsg = true;
        document.getElementById('recording-indicator').classList.add('active');
        
    } catch (err) {
        console.error('获取麦克风失败:', err);
        alert('无法访问麦克风，请检查权限设置');
    }
}

// 停止录制语音消息
function stopRecordingVoiceMsg() {
    if (!isRecordingVoiceMsg) return;
    
    if (voiceMsgRecorder && voiceMsgRecorder.state === 'recording') {
        voiceMsgRecorder.stop();
        isRecordingVoiceMsg = false;
        document.getElementById('recording-indicator').classList.remove('active');
    }
}

// 发送语音消息
async function sendVoiceMessage() {
    if (voiceMsgChunks.length === 0) return;
    
    try {
        const blob = new Blob(voiceMsgChunks, { type: 'audio/webm' });
        const reader = new FileReader();
        
        reader.onload = function() {
            const base64data = reader.result.split(',')[1];
            socket.emit('voice_message', { audio_data: base64data });
        };
        
        reader.readAsDataURL(blob);
    } catch (err) {
        console.error('发送语音消息失败:', err);
    }
}

// 处理语音消息
socket.on('voice_message', (data) => {
    addVoiceMessage(data);
});

// 添加语音消息到聊天区域
function addVoiceMessage(data) {
    const messagesContainer = document.getElementById('messages');
    const messageElement = document.createElement('div');
    
    let messageClass = 'message';
    if (data.username === username) {
        messageClass += ' sent';
    } else {
        messageClass += ' received';
    }
    
    messageElement.className = messageClass;
    
    const messageHeader = document.createElement('div');
    messageHeader.className = 'message-header';
    messageHeader.innerHTML = `
        <span>${data.username}</span>
        <span>${data.timestamp}</span>
    `;
    messageElement.appendChild(messageHeader);
    
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content voice-message';
    
    const playButton = document.createElement('button');
    playButton.className = 'play-voice-btn';
    playButton.innerHTML = `<span class="btn-icon">▶️</span> 播放语音`;
    
    const voiceIndicator = document.createElement('div');
    voiceIndicator.className = 'voice-message-indicator';
    voiceIndicator.innerHTML = `
        <span class="voice-wave"></span>
        <span>语音消息</span>
    `;
    
    messageContent.appendChild(playButton);
    messageContent.appendChild(voiceIndicator);
    
    // 保存音频数据作为按钮的属性
    playButton.dataset.audioData = data.audio_data;
    
    // 添加点击事件播放音频
    playButton.addEventListener('click', function() {
        playVoiceMessage(this.dataset.audioData);
        
        // 添加视觉反馈
        this.innerHTML = `<span class="btn-icon">🔊</span> 播放中...`;
        setTimeout(() => {
            this.innerHTML = `<span class="btn-icon">▶️</span> 播放语音`;
        }, 2000);
    });
    
    messageElement.appendChild(messageContent);
    messagesContainer.appendChild(messageElement);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// 播放语音消息
function playVoiceMessage(base64Data) {
    try {
        const audio = new Audio(`data:audio/webm;base64,${base64Data}`);
        audio.play();
    } catch (err) {
        console.error('播放语音消息失败:', err);
    }
}

// 文本聊天相关功能
document.getElementById('btn-send').addEventListener('click', sendMessage);

document.getElementById('message-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

// 发送文本消息
function sendMessage() {
    const messageInput = document.getElementById('message-input');
    const message = messageInput.value.trim();
    if (message) {
        socket.emit('chat_message', { message });
        messageInput.value = '';
    }
}

// 添加消息到聊天区域
function addMessage(data) {
    const messagesContainer = document.getElementById('messages');
    const messageElement = document.createElement('div');
    
    let messageClass = 'message';
    if (data.type === 'system') {
        messageClass += ' system';
    } else if (data.username === username) {
        messageClass += ' sent';
    } else {
        messageClass += ' received';
    }
    
    messageElement.className = messageClass;
    
    if (data.type !== 'system') {
        const messageHeader = document.createElement('div');
        messageHeader.className = 'message-header';
        messageHeader.innerHTML = `
            <span>${data.username}</span>
            <span>${data.timestamp}</span>
        `;
        messageElement.appendChild(messageHeader);
    }
    
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    messageContent.textContent = data.message;
    messageElement.appendChild(messageContent);
    
    messagesContainer.appendChild(messageElement);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// 更新用户列表
function updateUserList(users) {
    const userListElement = document.getElementById('user-list');
    userListElement.innerHTML = '';
    
    users.forEach(user => {
        const userElement = document.createElement('div');
        userElement.className = 'user-item';
        userElement.textContent = user;
        userListElement.appendChild(userElement);
    });
    
    // 更新在线用户数量显示
    document.getElementById('online-status').textContent = `在线用户: ${users.length}`;
}

// 处理聊天消息
socket.on('chat_message', (data) => {
    addMessage(data);
});

// 处理聊天历史
socket.on('chat_history', (data) => {
    const messagesContainer = document.getElementById('messages');
    messagesContainer.innerHTML = '';
    
    data.history.forEach(msg => {
        addMessage(msg);
    });
});

// 处理用户列表更新
socket.on('user_list', (data) => {
    updateUserList(data.users);
});

// 错误处理
socket.on('connect_error', (error) => {
    console.error('连接错误:', error);
    alert('连接服务器失败，请检查网络连接');
});

socket.on('error', (error) => {
    console.error('Socket错误:', error);
});