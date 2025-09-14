from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import json
import asyncio
from typing import Dict

from app.config import settings
from app.database import init_db
from app.routers import transfers, auth, health
from app.logging_config import setup_logging, get_logger


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, transfer_id: str):
        await websocket.accept()
        self.active_connections[transfer_id] = websocket

    def disconnect(self, transfer_id: str):
        if transfer_id in self.active_connections:
            del self.active_connections[transfer_id]

    async def send_progress_update(self, transfer_id: str, data: dict):
        if transfer_id in self.active_connections:
            try:
                await self.active_connections[transfer_id].send_text(json.dumps(data))
            except Exception:
                # Connection closed, remove it
                self.disconnect(transfer_id)


manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    logger = get_logger()
    logger.info("🚀 Starting FTransport backend server")
    init_db()
    logger.info("📊 Database initialized")
    yield
    # Shutdown
    logger.info("🛑 Shutting down FTransport backend server")
    pass


app = FastAPI(
    title="FTransport API",
    description="Data migration platform for NotebookLM Enterprise",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(transfers.router, prefix="/api/transfers", tags=["transfers"])
app.include_router(health.router, prefix="/api", tags=["health"])


@app.websocket("/ws/transfers/{transfer_id}")
async def websocket_endpoint(websocket: WebSocket, transfer_id: str):
    await manager.connect(websocket, transfer_id)
    try:
        while True:
            # Keep connection alive and listen for client messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(transfer_id)


# Make manager available globally
app.state.connection_manager = manager


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)