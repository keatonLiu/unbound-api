from unbound_console import RemoteControl
import sqlite3
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from socket import getfqdn


rc = RemoteControl(host="127.0.0.1", port=8953)
ch_root = rc.send_command("get_option chroot")
log_file = ch_root + rc.send_command("get_option logfile")
anchor_db_path = rc.send_command("get_option anchor-zones-db")
print(f"Log file: {log_file}, anchor db path: {anchor_db_path}")

app = FastAPI()

class AddZonesRequest(BaseModel):
    zones: List[str]

class DeleteZonesRequest(BaseModel):
    zones: List[str]

class ReplaceZonesRequest(BaseModel):
    zones: List[str]

@app.get("/log")
def get_log(limit: int = 10):
    with open(log_file) as f:
        lines = f.readlines()
    total = len(lines)
    log = lines[-limit:]
    return {
        "log": log,
        "size": len(log),
        "total": total
    }

@app.post("/zones/add")
def add_zones(request: AddZonesRequest):
    # Upsert zones into the database
    sql = """
        INSERT INTO zone(name) VALUES (?)
        ON CONFLICT(name) DO UPDATE SET name=excluded.name;
    """
    db = sqlite3.connect(anchor_db_path)
    cursor = db.cursor()
    cursor.executemany(sql, [(getfqdn(zone),) for zone in request.zones])
    db.commit()
    return {"status": "ok"}

@app.get("/zones/list")
def list_zones():
    db = sqlite3.connect(anchor_db_path)
    cursor = db.cursor()
    cursor.execute("SELECT * FROM zone")
    zones = [row[1] for row in cursor.fetchall()]
    return {"zones": zones}

@app.post("/zones/remove")
def remove_zones(request: DeleteZonesRequest):
    sql = "DELETE FROM zone WHERE name = ?"
    db = sqlite3.connect(anchor_db_path)
    cursor = db.cursor()
    cursor.executemany(sql, [(getfqdn(zone),) for zone in request.zones])
    db.commit()
    return {"status": "ok"}

@app.post("/zones/replace")
def replace_zones(request: ReplaceZonesRequest):
    db = sqlite3.connect(anchor_db_path)
    cursor = db.cursor()
    cursor.execute("DELETE FROM zone")
    sql = """
        INSERT INTO zone(name) VALUES (?)
        ON CONFLICT(name) DO UPDATE SET name=excluded.name;
    """
    cursor.executemany(sql, [(getfqdn(zone),) for zone in request.zones])
    db.commit()
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    