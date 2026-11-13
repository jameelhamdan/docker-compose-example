import os
import time
import uuid

import psycopg2
import redis
from flask import Flask, abort, jsonify, request, send_from_directory

DATA_DIR = os.environ.get("DATA_DIR", "/data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
ALLOWED = {"png", "jpg", "jpeg", "gif", "webp"}

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB per upload
cache = redis.Redis(host=os.environ.get("REDIS_HOST", "redis"), decode_responses=True)
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


def db():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "db"),
        dbname=os.environ.get("DB_NAME", "todos"),
        user=os.environ.get("DB_USER", "todos"),
        password=os.environ.get("DB_PASSWORD", "todos"),
    )


def init():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    for _ in range(30):  # the database may still be starting
        try:
            conn = db()
            break
        except psycopg2.OperationalError:
            time.sleep(1)
    else:
        raise SystemExit("database not reachable")
    with conn, conn.cursor() as cur:
        cur.execute("CREATE TABLE IF NOT EXISTS todo (id SERIAL PRIMARY KEY, title TEXT NOT NULL, done BOOLEAN NOT NULL DEFAULT FALSE)")
        cur.execute("ALTER TABLE todo ADD COLUMN IF NOT EXISTS image TEXT")
        cur.execute("SELECT COUNT(*) FROM todo")
        if cur.fetchone()[0] == 0:
            cur.executemany("INSERT INTO todo (title) VALUES (%s)", [(f"Todo {i}",) for i in range(1, 11)])
    conn.close()


def run(sql, args=(), fetch=False):
    conn = db()
    with conn, conn.cursor() as cur:
        cur.execute(sql, args)
        rows = cur.fetchall() if fetch else None
    conn.close()
    return rows


def save_image(file):
    """Store an uploaded image under /data/uploads and return its file name."""
    ext = os.path.splitext(file.filename or "")[1].lower().lstrip(".")
    if ext not in ALLOWED:
        abort(400, "image must be one of: " + ", ".join(sorted(ALLOWED)))
    name = f"{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(UPLOAD_DIR, name))
    return name


def remove_image(name):
    if name:
        try:
            os.remove(os.path.join(UPLOAD_DIR, name))
        except FileNotFoundError:
            pass


def todo_json(row):
    id, title, done, image = row
    return {"id": id, "title": title, "done": done, "image": f"/uploads/{image}" if image else None}


@app.errorhandler(400)
@app.errorhandler(413)
def error(e):
    return jsonify(error=e.description), e.code


@app.get("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/uploads/<path:name>")
def uploads(name):
    return send_from_directory(UPLOAD_DIR, name)


@app.get("/api/todos")
def list_todos():
    rows = run("SELECT id, title, done, image FROM todo ORDER BY id", fetch=True)
    return jsonify(todos=[todo_json(r) for r in rows], views=cache.incr("views"))


@app.post("/api/todos")
def add():
    title = (request.form.get("title") or "").strip()
    if not title:
        abort(400, "title is required")
    image = save_image(request.files["image"]) if request.files.get("image") else None
    rows = run("INSERT INTO todo (title, image) VALUES (%s, %s) RETURNING id, title, done, image", (title, image), fetch=True)
    return jsonify(todo_json(rows[0])), 201


@app.post("/api/todos/<int:id>/image")
def set_image(id):
    if not request.files.get("image"):
        abort(400, "image file is required")
    old = run("SELECT image FROM todo WHERE id = %s", (id,), fetch=True)
    if not old:
        abort(404)
    name = save_image(request.files["image"])
    rows = run("UPDATE todo SET image = %s WHERE id = %s RETURNING id, title, done, image", (name, id), fetch=True)
    remove_image(old[0][0])
    return jsonify(todo_json(rows[0]))


@app.post("/api/todos/<int:id>/toggle")
def toggle(id):
    rows = run("UPDATE todo SET done = NOT done WHERE id = %s RETURNING id, title, done, image", (id,), fetch=True)
    if not rows:
        abort(404)
    return jsonify(todo_json(rows[0]))


@app.delete("/api/todos/<int:id>")
def delete(id):
    rows = run("DELETE FROM todo WHERE id = %s RETURNING image", (id,), fetch=True)
    if rows:
        remove_image(rows[0][0])
    return "", 204


init()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
