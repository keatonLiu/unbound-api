from unbound_console import RemoteControl
import sqlite3
from fastapi import FastAPI, status, Query
from pydantic import BaseModel
from typing import List
from fqdn import FQDN

rc = RemoteControl(host="127.0.0.1", port=8953)

app = FastAPI(
    title="Unbound API",
    description="""Unbound API for managing Anchor NS zones, 
    fetching logs, etc
    """,
    summary="Unbound API for managing Anchor NS",
    version="0.0.1",
    terms_of_service="https://github.com/keatonLiu/unbound-api",
    contact={
        "name": "Keaton Liu",
        "url": "https://github.com/keatonLiu/unbound-api",
        "email": "lxtxiaotong@foxmail.com",
    }
)


class AddZonesRequest(BaseModel):
    zones: List[str]


class DeleteZonesRequest(BaseModel):
    zones: List[str]


class ReplaceZonesRequest(BaseModel):
    zones: List[str]
    
class AddZonesResponse(BaseModel):
    status: str

class ListZonesResponse(BaseModel):
    zones: List[str]
    
class LogResponse(BaseModel):
    log: List[str]
    size: int
    total: int

@app.get("/log", response_model=LogResponse, status_code=status.HTTP_200_OK,
         summary="Get unbound runtime log",
         description="Get the last N lines of the log file")
def get_log(limit: int = Query(default=10, description="The last N lines of the log")):
    ch_root = rc.send_command("get_option chroot")
    log_file = ch_root + rc.send_command("get_option logfile")
    with open(log_file) as f:
        lines = f.readlines()
    total = len(lines)
    log = lines[-limit:]
    return {
        "log": log,
        "size": len(log),
        "total": total
    }


@app.post("/zones/add", response_model=AddZonesResponse, status_code=status.HTTP_201_CREATED, 
          summary="Add monitor zones",
          description="Upsert monitor zones into the database, replace if exists")
def add_zones(request: AddZonesRequest):
    anchor_db_path = rc.send_command("get_option anchor-zones-db")
    # Upsert zones into the database
    sql = """
        INSERT INTO zone(name) VALUES (?)
        ON CONFLICT(name) DO UPDATE SET name=excluded.name;
    """
    db = sqlite3.connect(anchor_db_path)
    cursor = db.cursor()
    cursor.executemany(sql, [(FQDN(zone).absolute,) for zone in request.zones])
    db.commit()
    return {"status": "ok"}


@app.get("/zones/list", response_model=ListZonesResponse, status_code=status.HTTP_200_OK, 
         summary="List monitor zones",
         description="List all monitor zones in the database")
def list_zones():
    anchor_db_path = rc.send_command("get_option anchor-zones-db")
    db = sqlite3.connect(anchor_db_path)
    cursor = db.cursor()
    cursor.execute("SELECT * FROM zone")
    zones = [row[1] for row in cursor.fetchall()]
    return {"zones": zones}


@app.post("/zones/remove", response_model=AddZonesResponse, status_code=status.HTTP_200_OK, 
          summary="Remove monitor zones",
          description="Remove monitor zones from the database")
def remove_zones(request: DeleteZonesRequest):
    anchor_db_path = rc.send_command("get_option anchor-zones-db")
    sql = "DELETE FROM zone WHERE name = ?"
    db = sqlite3.connect(anchor_db_path)
    cursor = db.cursor()
    cursor.executemany(sql, [(FQDN(zone).absolute,) for zone in request.zones])
    db.commit()
    return {"status": "ok"}


@app.post("/zones/replace", response_model=AddZonesResponse, status_code=status.HTTP_200_OK, 
          summary="Replace monitor zones",
          description="Replace monitor zones in the database")
def replace_zones(request: ReplaceZonesRequest):
    anchor_db_path = rc.send_command("get_option anchor-zones-db")
    db = sqlite3.connect(anchor_db_path)
    cursor = db.cursor()
    cursor.execute("DELETE FROM zone")
    sql = """
        INSERT INTO zone(name) VALUES (?)
        ON CONFLICT(name) DO UPDATE SET name=excluded.name;
    """
    cursor.executemany(sql, [(FQDN(zone).absolute,) for zone in request.zones])
    db.commit()
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
