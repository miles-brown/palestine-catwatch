
import socketio

# Create a Socket.IO server
# async_mode='asgi' is compatible with FastAPI
sio_server = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*'
)

# Wrapper for ASGI application (FastAPI will mount this)
sio_app = socketio.ASGIApp(
    socketio_server=sio_server,
    socketio_path='socket.io'
)

# Event Handlers
@sio_server.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")
    await sio_server.emit('log_message', {'message': 'Connected to backend live feed.'}, to=sid)

@sio_server.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")

@sio_server.event
async def join_task(sid, task_id):
    """
    Allow client to join a room specific to a processing task (e.g. video URL or upload).
    """
    print(f"Client {sid} joining task room: {task_id}")
    sio_server.enter_room(sid, task_id)
    await sio_server.emit('log_message', {'message': f"Joined room for task {task_id}"}, to=sid)
