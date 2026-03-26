import time
from fastapi import WebSocket, WebSocketDisconnect
import json
from pathlib import Path
from uuid import uuid4
from pydantic import BaseModel
from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from Augment_chess_main import Board

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

rooms = {}
connections = {}

class AugmentSelectRequest(BaseModel):
    player_id: str
    augment_id: str

def create_room_data():
    return {
        "board": Board(),
        "players": {"W": None, "B": None},
        "time": {
    "W": 600,
    "B": 600,
    "last_update": time.time(),
    "running": None,
    "ended": False,
    "winner": None,
},
        "rematch": {
            "votes": {"W": False, "B": False},
            "count": 0,
        },
        "augment": {
            "active": False,
            "tier": "gold",
            "choices": {
                "W": [],
                "B": []
            },
            "selected": {
                "W": None,
                "B": None
            }
        }
    }


def build_state(room):
    data = room["board"].to_dict()
    data["clock"] = room["time"]
    data["rematch"] = room["rematch"]
    data["players"] = room["players"]
    data["augment"] = room["augment"]
    return data


def update_clock(room):
    clock = room["time"]

    if room["players"]["W"] is None or room["players"]["B"] is None:
        clock["last_update"] = time.time()
        return

    if clock["ended"]:
        return

    if clock["running"] is None:
        clock["last_update"] = time.time()
        return

    now = time.time()
    elapsed = now - clock["last_update"]
    current = clock["running"]
    clock[current] -= elapsed
    clock["last_update"] = now

    if clock[current] <= 0:
        clock[current] = 0
        clock["ended"] = True
        clock["winner"] = "B" if current == "W" else "W"


def get_player_color(room, player_id):
    if room["players"]["W"] == player_id:
        return "W"
    if room["players"]["B"] == player_id:
        return "B"
    return None


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    pieces_dir = STATIC_DIR / "pieces"
    if pieces_dir.exists():
        app.mount("/pieces", StaticFiles(directory=pieces_dir), name="pieces")


@app.post("/create_room")
def create_room():
    room_id = uuid4().hex[:6].upper()
    rooms[room_id] = create_room_data()
    return {"room_id": room_id}


@app.post("/rooms/{room_id}/join")
async def join_room(room_id: str, data: dict = Body(...)):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="room not found")

    player_id = data.get("player_id")
    if not player_id:
        raise HTTPException(status_code=400, detail="player_id required")

    room = rooms[room_id]
    players = room["players"]

    if players["W"] == player_id:
        return {"color": "W"}
    if players["B"] == player_id:
        return {"color": "B"}

    if players["W"] is None:
        players["W"] = player_id
        return {"color": "W"}

    if players["B"] is None:
        players["B"] = player_id

        # 증강 선택 전이니까 시간 멈춤
        room["time"]["last_update"] = time.time()
        room["time"]["running"] = None
        room["augment"]["active"] = True

        room["augment"]["choices"]["W"] = [
            {"id": "a1", "tier": "gold", "title": "캐슬링 금지", "description": "..."},
            {"id": "a2", "tier": "gold", "title": "언더 프로모션!!", "description": "..."},
            {"id": "a3", "tier": "gold", "title": "폰 둔화", "description": "..."}
        ]

        room["augment"]["choices"]["B"] = [
            {"id": "b1", "tier": "gold", "title": "룩 약화", "description": "..."},
            {"id": "b2", "tier": "gold", "title": "비숍 약화", "description": "..."},
            {"id": "b3", "tier": "gold", "title": "전장의 안개", "description": "..."}
        ]

        await broadcast(room_id, {
            "type": "update",
            "state": build_state(room)
        })

        return {"color": "B"}

    return {"color": "S"}


@app.get("/rooms/{room_id}/state")
def get_state(room_id: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="room not found")
    room = rooms[room_id]
    update_clock(room)
    return build_state(room)

@app.post("/rooms/{room_id}/move")
async def move(room_id: str, data: dict = Body(...)):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="room not found")

    room = rooms[room_id]
    board = room["board"]
    update_clock(room)

    if room["time"]["ended"]:
        return {
            "result": {"success": False, "message": "시간 종료"},
            "state": build_state(room),
        }

    player_id = data.get("player_id")
    if not player_id:
        raise HTTPException(status_code=400, detail="player_id required")

    if room["players"]["W"] == player_id:
        player_color = "W"
    elif room["players"]["B"] == player_id:
        player_color = "B"
    else:
        return {
            "result": {"success": False, "message": "관전자는 움직일 수 없음"},
            "state": build_state(room),
        }

    game_state = board.get_game_state()
    if game_state["checkmate"] or game_state["draw"]:
        return {
            "result": {"success": False, "message": "이미 끝난 게임임"},
            "state": build_state(room),
        }

    if board.turn != player_color:
        return {
            "result": {"success": False, "message": "지금 네 턴이 아님"},
            "state": build_state(room),
        }

    x1, y1, x2, y2 = data["x1"], data["y1"], data["x2"], data["y2"]
    promotion = data.get("promotion", "Q")
    piece = board.grid[y1][x1]
    if piece is None:
        return {
            "result": {"success": False, "message": "거기에 기물이 없음"},
            "state": build_state(room),
        }

    if piece.color != player_color:
        return {
            "result": {"success": False, "message": "네 기물만 움직일 수 있음"},
            "state": build_state(room),
        }

    result = board.move_piece_web(x1, y1, x2, y2, promotion)
    if result["success"]:
        room["time"]["running"] = board.turn
        room["time"]["last_update"] = time.time()

        await broadcast(room_id, {
            "type": "update",
            "state": build_state(room)
        })

    return {"result": result, "state": build_state(room)}


@app.post("/rooms/{room_id}/reset")
def reset_room(room_id: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="room not found")

    old_players = rooms[room_id]["players"]
    rooms[room_id] = create_room_data()
    rooms[room_id]["players"] = old_players

    if old_players["W"] is not None and old_players["B"] is not None:
        rooms[room_id]["time"]["last_update"] = time.time()
        rooms[room_id]["time"]["running"] = None

    return {"success": True}

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await websocket.accept()

    if room_id not in connections:
        connections[room_id] = []

    connections[room_id].append(websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connections[room_id].remove(websocket)

async def broadcast(room_id: str, message: dict):
    if room_id not in connections:
        return

    dead = []
    for ws in connections[room_id]:
        try:
            await ws.send_text(json.dumps(message))
        except:
            dead.append(ws)

    for ws in dead:
        connections[room_id].remove(ws)

def reset_room_with_swap(room_id: str):
    old_room = rooms[room_id]
    old_players = old_room["players"]

    new_room = create_room_data()
    new_room["players"] = {
        "W": old_players["B"],
        "B": old_players["W"],
    }

    if new_room["players"]["W"] is not None and new_room["players"]["B"] is not None:
        new_room["time"]["last_update"] = time.time()
        new_room["time"]["running"] = None

    rooms[room_id] = new_room


@app.post("/rooms/{room_id}/rematch")
async def rematch_room(room_id: str, data: dict = Body(...)):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="room not found")

    player_id = data.get("player_id")
    if not player_id:
        raise HTTPException(status_code=400, detail="player_id required")

    room = rooms[room_id]
    players = room["players"]

    if players["W"] == player_id:
        player_color = "W"
    elif players["B"] == player_id:
        player_color = "B"
    else:
        raise HTTPException(status_code=403, detail="only players can request rematch")

    rematch = room["rematch"]

    if not rematch["votes"][player_color]:
        rematch["votes"][player_color] = True
        rematch["count"] += 1

    await broadcast(room_id, {
        "type": "rematch_vote",
        "state": build_state(room)
    })

    if rematch["count"] >= 2:
        reset_room_with_swap(room_id)
        await broadcast(room_id, {
            "type": "update",
            "state": build_state(rooms[room_id])
        })
        return {"success": True, "started": True, "state": build_state(rooms[room_id])}

    return {"success": True, "started": False, "state": build_state(room)}

@app.post("/rooms/{room_id}/augment/select")
async def select_augment(room_id: str, req: AugmentSelectRequest):
    room = rooms.get(room_id)
    if not room:
        raise HTTPException(status_code=404)

    color = get_player_color(room, req.player_id)

    if room["augment"]["selected"][color] is not None:
        raise HTTPException(status_code=400)

    room["augment"]["selected"][color] = req.augment_id

    await broadcast(room_id, {
        "type": "update",
        "state": build_state(room)
    })

    both_done = (
        room["augment"]["selected"]["W"] is not None and
        room["augment"]["selected"]["B"] is not None
    )

    if both_done:
        room["augment"]["active"] = False
        room["time"]["last_update"] = time.time()
        room["time"]["running"] = room["board"].turn

        await broadcast(room_id, {
            "type": "update",
            "state": build_state(room)
        })

    return {
        "both_done": both_done,
        "state": build_state(room)
    }