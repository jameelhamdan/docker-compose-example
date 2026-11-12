import os
import time

import psycopg2
import redis
from flask import Flask, redirect, render_template_string, request

app = Flask(__name__)
cache = redis.Redis(host=os.environ.get("REDIS_HOST", "redis"), decode_responses=True)

PAGE = """<!doctype html>
<title>Todos</title>
<h1>Todos</h1>
<p>Page views: {{ views }}</p>
<form method="post" action="/add"><input name="title" required> <button>Add</button></form>
<ul>
{% for id, title, done in todos %}
  <li>{{ "✔" if done else "○" }} {{ title }}
    <form method="post" action="/toggle/{{ id }}" style="display:inline"><button>toggle</button></form>
    <form method="post" action="/delete/{{ id }}" style="display:inline"><button>delete</button></form>
  </li>
{% endfor %}
</ul>
"""


def db():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "db"),
        dbname=os.environ.get("DB_NAME", "todos"),
        user=os.environ.get("DB_USER", "todos"),
        password=os.environ.get("DB_PASSWORD", "todos"),
    )


def init():
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


@app.get("/")
def index():
    todos = run("SELECT id, title, done FROM todo ORDER BY id", fetch=True)
    return render_template_string(PAGE, todos=todos, views=cache.incr("views"))


@app.post("/add")
def add():
    run("INSERT INTO todo (title) VALUES (%s)", (request.form["title"],))
    return redirect("/")


@app.post("/toggle/<int:id>")
def toggle(id):
    run("UPDATE todo SET done = NOT done WHERE id = %s", (id,))
    return redirect("/")


@app.post("/delete/<int:id>")
def delete(id):
    run("DELETE FROM todo WHERE id = %s", (id,))
    return redirect("/")


init()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
