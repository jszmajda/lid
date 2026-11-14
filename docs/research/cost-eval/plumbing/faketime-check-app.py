import sqlite3, time, os
from datetime import datetime, timezone
from fastapi import FastAPI
app = FastAPI()
DB = os.environ.get("DATA_DIR", "/data") + "/t.db"
@app.get("/now")
def now():
    con = sqlite3.connect(DB)
    con.execute("create table if not exists hits(at text, py text)")
    py = datetime.now(timezone.utc).isoformat()
    con.execute("insert into hits values (datetime('now'), ?)", (py,)); con.commit()
    rows = con.execute("select at, py from hits").fetchall()
    return {"py_utc": py, "py_local": datetime.now().isoformat(), "time_time": time.time(),
            "sqlite_now": con.execute("select datetime('now')").fetchone()[0], "rows": rows}
