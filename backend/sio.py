"""
Socket.IO server configuration and event handlers.

Provides real-time communication for live analysis status updates.
Includes robust room management with automatic cleanup for orphaned rooms.
"""
import socketio
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Set, Optional
import os

# Create a Socket.IO server
# async_mode='asgi' is compatible with FastAPI
sio_server = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*'
)

# Wrapper for ASGI application (FastAPI will mount this at /socket.io)
# socketio_path='' means socket.io listens at the mount root, avoiding path duplication
sio_app = socketio.ASGIApp(
    socketio_server=sio_server,
    socketio_path=''
)

# =============================================================================
# ROOM MANAGEMENT CONFIGURATION
# =============================================================================

# Time in seconds before a completed room is cleaned up
ROOM_CLEANUP_DELAY = int(os.getenv('SIO_ROOM_CLEANUP_DELAY', '300'))  # 5 minutes default

# Maximum age for any room (even active ones) before forced cleanup
ROOM_MAX_AGE_HOURS = int(os.getenv('SIO_ROOM_MAX_AGE_HOURS', '24'))  # 24 hours default

# How often to run the periodic cleanup sweep
CLEANUP_INTERVAL_SECONDS = int(os.getenv('SIO_CLEANUP_INTERVAL', '3600'))  # 1 hour default

# Maximum number of tracked rooms (memory protection)
MAX_TRACKED_ROOMS = int(os.getenv('SIO_MAX_ROOMS', '1000'))


# =============================================================================
# ROOM TRACKING DATA STRUCTURES
# =============================================================================

class RoomInfo:
    """Track information about a task room."""
    __slots__ = ('created', 'clients', 'completed', 'cleanup_task')

    def __init__(self):
        self.created: datetime = datetime.now(timezone.utc)
        self.clients: Set[str] = set()
        self.completed: Optional[datetime] = None
        self.cleanup_task: Optional[asyncio.Task] = None


# Track active task rooms for cleanup
_active_rooms: Dict[str, RoomInfo] = {}

# Lock for thread-safe room operations
_rooms_lock = asyncio.Lock()

# Periodic cleanup task reference
_cleanup_sweep_task: Optional[asyncio.Task] = None


# =============================================================================
# ROOM CLEANUP FUNCTIONS
# =============================================================================

async def cleanup_room(task_id: str, force: bool = False):
    """
    Clean up a task room after a delay (or immediately if force=True).

    Args:
        task_id: The task/room identifier
        force: If True, clean up immediately without delay
    """
    if not force:
        await asyncio.sleep(ROOM_CLEANUP_DELAY)

    async with _rooms_lock:
        if task_id not in _active_rooms:
            return  # Already cleaned up

        room_info = _active_rooms[task_id]

        # Remove all clients from the room
        for sid in list(room_info.clients):
            try:
                await sio_server.leave_room(sid, task_id)
            except Exception as e:
                # Client may have already disconnected - this is expected
                pass

        del _active_rooms[task_id]
        print(f"Cleaned up task room: {task_id}")


async def mark_room_complete(task_id: str):
    """
    Mark a room as complete and schedule cleanup.

    This is called when a processing task finishes.
    """
    async with _rooms_lock:
        if task_id not in _active_rooms:
            return

        room_info = _active_rooms[task_id]
        room_info.completed = datetime.now(timezone.utc)

        # Cancel any existing cleanup task
        if room_info.cleanup_task and not room_info.cleanup_task.done():
            room_info.cleanup_task.cancel()

        # Schedule new cleanup
        room_info.cleanup_task = asyncio.create_task(cleanup_room(task_id))
        print(f"Scheduled cleanup for task room: {task_id}")


async def cleanup_stale_rooms():
    """
    Periodic cleanup of stale rooms.

    This handles edge cases like:
    - Server restart during processing (orphaned rooms)
    - Tasks that never complete
    - Memory leaks from abandoned rooms
    """
    now = datetime.now(timezone.utc)
    max_age = timedelta(hours=ROOM_MAX_AGE_HOURS)
    completed_grace = timedelta(seconds=ROOM_CLEANUP_DELAY * 2)

    async with _rooms_lock:
        rooms_to_clean = []

        for task_id, room_info in _active_rooms.items():
            room_age = now - room_info.created
            should_clean = False
            reason = ""

            # Check if room is too old
            if room_age > max_age:
                should_clean = True
                reason = f"exceeded max age ({ROOM_MAX_AGE_HOURS}h)"

            # Check if completed room wasn't cleaned up
            elif room_info.completed:
                completed_age = now - room_info.completed
                if completed_age > completed_grace:
                    should_clean = True
                    reason = "completed but not cleaned up"

            # Check if room has no clients and is old (likely orphaned)
            elif not room_info.clients and room_age > timedelta(minutes=30):
                should_clean = True
                reason = "no clients for 30+ minutes"

            if should_clean:
                rooms_to_clean.append((task_id, reason))

        # Clean up outside the iteration
        for task_id, reason in rooms_to_clean:
            print(f"Stale room cleanup: {task_id} ({reason})")
            # Force immediate cleanup (don't await delay)
            asyncio.create_task(cleanup_room(task_id, force=True))

    if rooms_to_clean:
        print(f"Cleaned up {len(rooms_to_clean)} stale rooms")


async def periodic_cleanup_sweep():
    """Background task that periodically cleans up stale rooms."""
    while True:
        try:
            await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
            await cleanup_stale_rooms()
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error in cleanup sweep: {e}")
            # Continue running despite errors


def start_cleanup_sweep():
    """Start the periodic cleanup sweep task."""
    global _cleanup_sweep_task
    if _cleanup_sweep_task is None or _cleanup_sweep_task.done():
        _cleanup_sweep_task = asyncio.create_task(periodic_cleanup_sweep())
        print(f"Started periodic room cleanup (interval: {CLEANUP_INTERVAL_SECONDS}s)")


def stop_cleanup_sweep():
    """Stop the periodic cleanup sweep task."""
    global _cleanup_sweep_task
    if _cleanup_sweep_task and not _cleanup_sweep_task.done():
        _cleanup_sweep_task.cancel()
        print("Stopped periodic room cleanup")


# =============================================================================
# ROOM STATISTICS (for monitoring/debugging)
# =============================================================================

def get_room_stats() -> dict:
    """Get statistics about active rooms."""
    now = datetime.now(timezone.utc)
    active_count = 0
    completed_count = 0
    total_clients = 0

    for room_info in _active_rooms.values():
        if room_info.completed:
            completed_count += 1
        else:
            active_count += 1
        total_clients += len(room_info.clients)

    return {
        "total_rooms": len(_active_rooms),
        "active_rooms": active_count,
        "completed_rooms": completed_count,
        "total_clients": total_clients,
        "max_rooms": MAX_TRACKED_ROOMS,
        "cleanup_delay_seconds": ROOM_CLEANUP_DELAY,
    }


# =============================================================================
# SOCKET.IO EVENT HANDLERS
# =============================================================================

@sio_server.event
async def connect(sid, environ):
    """Handle client connection."""
    print(f"Client connected: {sid}")
    # Start cleanup sweep on first connection (lazy initialization)
    start_cleanup_sweep()
    await sio_server.emit('log_message', {'message': 'Connected to backend live feed.'}, to=sid)


@sio_server.event
async def disconnect(sid):
    """Handle client disconnection."""
    print(f"Client disconnected: {sid}")

    async with _rooms_lock:
        # Remove client from all tracked rooms
        rooms_to_check = []
        for task_id, room_info in _active_rooms.items():
            if sid in room_info.clients:
                room_info.clients.discard(sid)
                rooms_to_check.append(task_id)

        # Check if any rooms should be cleaned up immediately
        for task_id in rooms_to_check:
            room_info = _active_rooms.get(task_id)
            if room_info and not room_info.clients and room_info.completed:
                # Room is empty and completed - clean up immediately
                del _active_rooms[task_id]
                print(f"Immediately cleaned up empty completed room: {task_id}")


@sio_server.event
async def join_task(sid, task_id):
    """
    Allow client to join a room specific to a processing task.

    This is used for live analysis updates - clients join a room
    when they start watching a processing task.
    """
    print(f"Client {sid} joining task room: {task_id}")

    async with _rooms_lock:
        # Check room limits
        if task_id not in _active_rooms and len(_active_rooms) >= MAX_TRACKED_ROOMS:
            # Try to clean up old completed rooms first
            await cleanup_stale_rooms()
            if len(_active_rooms) >= MAX_TRACKED_ROOMS:
                await sio_server.emit('error', {
                    'message': 'Server is busy. Please try again later.'
                }, to=sid)
                print(f"Rejected join: room limit reached ({MAX_TRACKED_ROOMS})")
                return

        await sio_server.enter_room(sid, task_id)

        # Track the room
        if task_id not in _active_rooms:
            _active_rooms[task_id] = RoomInfo()
        _active_rooms[task_id].clients.add(sid)

    await sio_server.emit('log_message', {'message': f"Joined room for task {task_id}"}, to=sid)


@sio_server.event
async def leave_task(sid, task_id):
    """Allow client to leave a task room."""
    print(f"Client {sid} leaving task room: {task_id}")
    await sio_server.leave_room(sid, task_id)

    async with _rooms_lock:
        if task_id in _active_rooms:
            _active_rooms[task_id].clients.discard(sid)


@sio_server.event
async def get_stats(sid):
    """Return room statistics (for admin/debugging)."""
    stats = get_room_stats()
    await sio_server.emit('stats', stats, to=sid)
