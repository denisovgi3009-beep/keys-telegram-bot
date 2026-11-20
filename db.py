# -*- coding: utf-8 -*-
"""Слой данных: товары, склад ключей, заказы. SQLite, потокобезопасно."""
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from config import PRODUCTS

# Путь к базе можно задать переменной окружения DB_PATH (для Docker/тома).
DB_PATH = Path(os.getenv("DB_PATH") or Path(__file__).with_name("store.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
_lock = threading.Lock()

def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c

def init():
    with _lock, conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS products(
              id TEXT PRIMARY KEY, title TEXT, duration TEXT, price INTEGER);
            CREATE TABLE IF NOT EXISTS keys(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              product_id TEXT REFERENCES products(id),
              key TEXT UNIQUE NOT NULL,
              sold INTEGER NOT NULL DEFAULT 0,
              order_id INTEGER,
              added_at TEXT);
            CREATE TABLE IF NOT EXISTS orders(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              chat_id INTEGER NOT NULL,
              username TEXT,
              product_id TEXT REFERENCES products(id),
              amount INTEGER NOT NULL,
              status TEXT NOT NULL DEFAULT 'pending', -- pending|paid|delivered|rejected
              key_id INTEGER,
              created_at TEXT, updated_at TEXT);
            """
        )
        # засеваем товары, если их нет
        have = {r["id"] for r in c.execute("SELECT id FROM products")}
        for pid, title, dur, price in PRODUCTS:
            if pid not in have:
                c.execute(
                    "INSERT INTO products(id,title,duration,price) VALUES(?,?,?,?)",
                    (pid, title, dur, price),
                )

def list_products():
    with conn() as c:
        return list(c.execute("SELECT * FROM products ORDER BY price"))

def product(pid):
    with conn() as c:
        return c.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()

def add_keys(pid, keys):
    """Возвращает (добавлено, пропущено-дублей)."""
    added = skipped = 0
    with _lock, conn() as c:
        for k in keys:
            k = k.strip()
            if not k:
                continue
            try:
                c.execute(
                    "INSERT INTO keys(product_id,key,added_at) VALUES(?,?,?)",
                    (pid, k, _now()),
                )
                added += 1
            except sqlite3.IntegrityError:
                skipped += 1
    return added, skipped

def stock_counts():
    with conn() as c:
        rows = c.execute(
            """SELECT p.id, p.title, p.duration, p.price,
                      COUNT(k.id) AS free
               FROM products p LEFT JOIN keys k
                 ON k.product_id=p.id AND k.sold=0
               GROUP BY p.id ORDER BY p.price"""
        ).fetchall()
    return rows

def _take_free_key(c, pid):
    return c.execute(
        "SELECT id,key FROM keys WHERE product_id=? AND sold=0 "
        "ORDER BY id LIMIT 1", (pid,)
    ).fetchone()

def create_order(chat_id, username, pid):
    p = product(pid)
    if not p:
        return None
    with _lock, conn() as c:
        cur = c.execute(
            "INSERT INTO orders(chat_id,username,product_id,amount,status,created_at,updated_at)"
            " VALUES(?,?,?,?, 'pending', ?, ?)",
            (chat_id, username, pid, p["price"], _now(), _now()),
        )
        return cur.lastrowid

def get_order(oid):
    with conn() as c:
        return c.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()

def pending_orders():
    with conn() as c:
        return list(c.execute(
            "SELECT * FROM orders WHERE status='pending' ORDER BY id DESC LIMIT 25"))

def mark_paid(oid):
    with _lock, conn() as c:
        c.execute("UPDATE orders SET status='paid', updated_at=? WHERE id=?", (_now(), oid))

def deliver(oid):
    """Атомарно: забрать ключ, пометить sold, заказ -> delivered. Возвращает ключ или None."""
    with _lock, conn() as c:
        o = c.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
        if not o:
            return None
        if o["status"] == "delivered" and o["key_id"]:
            k = c.execute("SELECT key FROM keys WHERE id=?", (o["key_id"],)).fetchone()
            return k["key"] if k else None
        fk = _take_free_key(c, o["product_id"])
        if not fk:
            return None
        c.execute("UPDATE keys SET sold=1, order_id=? WHERE id=?", (oid, fk["id"]))
        c.execute("UPDATE orders SET status='delivered', key_id=?, updated_at=? WHERE id=?",
                  (fk["id"], _now(), oid))
        return fk["key"]

def reject(oid):
    with _lock, conn() as c:
        c.execute("UPDATE orders SET status='rejected', updated_at=? WHERE id=?", (_now(), oid))
