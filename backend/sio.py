
import socketio
import asyncio
from datetime import datetime, timedelta

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

# Track active task rooms for cleanup
_active_rooms = {}  # task_id -> {'created': datetime, 'clients': set()}
ROOM_CLEANUP_DELAY = 300  # 5 minutes after completion

async def cleanup_room(task_id):
    """Clean up a task room after a delay."""
    await asyncio.sleep(ROOM_CLEANUP_DELAY)
    if task_id in _active_rooms:
        room_info = _active_rooms[task_id]
        # Remove all clients from the room
        for sid in list(room_info.get('clients', [])):
            try:
                await sio_server.leave_room(sid, task_id)
            except Exception as e:
                # Client may have already disconnected - this is expected
                print(f"Note: Could not remove {sid} from room {task_id}: {e}")
        del _active_rooms[task_id]
        print(f"Cleaned up task room: {task_id}")

async def mark_room_complete(task_id):
    """Mark a room as complete and schedule cleanup."""
    if task_id in _active_rooms:
        _active_rooms[task_id]['completed'] = datetime.utcnow()
        # Schedule cleanup
        asyncio.create_task(cleanup_room(task_id))
        print(f"Scheduled cleanup for task room: {task_id}")

# Event Handlers
@sio_server.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")
    await sio_server.emit('log_message', {'message': 'Connected to backend live feed.'}, to=sid)

@sio_server.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")
    # Remove client from tracked rooms
    for task_id, room_info in list(_active_rooms.items()):
        if sid in room_info.get('clients', set()):
            room_info['clients'].discard(sid)
            # If room is empty and completed, clean up immediately
            if not room_info['clients'] and room_info.get('completed'):
                if task_id in _active_rooms:
                    del _active_rooms[task_id]
                    print(f"Immediately cleaned up empty completed room: {task_id}")

@sio_server.event
async def join_task(sid, task_id):
    """
    Allow client to join a room specific to a processing task (e.g. video URL or upload).
    """
    print(f"Client {sid} joining task room: {task_id}")
    await sio_server.enter_room(sid, task_id)

    # Track the room
    if task_id not in _active_rooms:
        _active_rooms[task_id] = {'created': datetime.utcnow(), 'clients': set()}
    _active_rooms[task_id]['clients'].add(sid)

    await sio_server.emit('log_message', {'message': f"Joined room for task {task_id}"}, to=sid)

@sio_server.event
async def leave_task(sid, task_id):
    """
    Allow client to leave a task room.
    """
    print(f"Client {sid} leaving task room: {task_id}")
    await sio_server.leave_room(sid, task_id)
    if task_id in _active_rooms:
        _active_rooms[task_id]['clients'].discard(sid)
