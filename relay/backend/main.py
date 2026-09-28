from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import asyncio
from db import create_session, add_step, get_session, get_steps, list_sessions, update_session_owner, update_session_status, delete_session
from agent_runner import AgentRunner

app = FastAPI()

app.mount("/static", StaticFiles(directory="../frontend"), name="static")

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.setdefault(session_id, []).append(websocket)

    def disconnect(self, session_id: str, websocket: WebSocket):
        if session_id in self.active_connections:
            self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def broadcast(self, session_id: str, message: dict):
        dead_connections = []
        for connection in self.active_connections.get(session_id, []):
            try:
                await asyncio.wait_for(connection.send_json(message), timeout=3.0)
            except (asyncio.TimeoutError, Exception):
                dead_connections.append(connection)
        # Clean up any connections that failed or timed out
        for dead in dead_connections:
            self.disconnect(session_id, dead)

manager = ConnectionManager()
active_runners: dict[str, AgentRunner] = {}

@app.get("/")
def serve_index():
    return FileResponse("../frontend/index.html")

@app.get("/session/{session_id}")
def serve_session_page(session_id: str):
    return FileResponse("../frontend/index.html")

@app.get("/history.html")
def serve_history_page():
    return FileResponse("../frontend/history.html")

@app.post("/api/sessions")
async def create_new_session(payload: dict):
    task = payload.get("task", "")
    participant_name = payload.get("participant_name", "Anonymous")
    session = create_session(task, participant_name)
    return {"session_id": session.get("id")}

@app.get("/api/sessions")
def list_all_sessions():
    return list_sessions()

@app.post("/api/sessions/{session_id}/claim")
async def claim_session(session_id: str, payload: dict):
    participant_name = payload.get("participant_name", "Anonymous")
    updated = update_session_owner(session_id, participant_name)
    await manager.broadcast(session_id, {
        "type": "ownership_changed",
        "new_owner": participant_name
    })
    return updated

@app.delete("/api/sessions/{session_id}")
async def delete_session_endpoint(session_id: str):
    delete_session(session_id)
    return {"ok": True}

@app.websocket("/ws/{session_id}")
async def session_websocket(websocket: WebSocket, session_id: str):
    await manager.connect(session_id, websocket)

    existing_steps = get_steps(session_id)
    await websocket.send_json({"type": "backfill", "steps": existing_steps})

    step_counter = [len(existing_steps)]

    async def on_step(step_type: str, content: str):
        step_counter[0] += 1
        row = add_step(session_id, step_counter[0], step_type, content)
        await manager.broadcast(session_id, {
            "type": "step",
            "step_number": step_counter[0],
            "step_type": step_type,
            "content": content
        })

    def cleanup_runner(sid: str):
        if sid in active_runners:
            del active_runners[sid]

    def update_session_status_cb(sid: str, status: str):
        update_session_status(sid, status)

    if session_id not in active_runners:
        session = get_session(session_id)
        task = session.get("task", "") if session else ""
        runner = AgentRunner(session_id, task, on_step, on_cleanup_callback=cleanup_runner, on_status_update_callback=update_session_status_cb)
        active_runners[session_id] = runner
        agent_task = asyncio.create_task(runner.run())
        runner.agent_task = agent_task
    else:
        runner = active_runners[session_id]

    # Send current owner on connect
    session = get_session(session_id)
    if session and session.get("owner_id"):
        await websocket.send_json({"type": "ownership_changed", "new_owner": session["owner_id"]})

    try:
        while True:
            message = await websocket.receive_json()
            if message.get("type") == "steering":
                content = message.get("content", "")
                sender = message.get("sender", "Anonymous")
                await runner.inject_steering_message(content, sender)
    except (WebSocketDisconnect, Exception):
        manager.disconnect(session_id, websocket)