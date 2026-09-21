"""Persistent player accounts and atomic coin/shop transactions."""
import hashlib
import hmac
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


class ProgressStore:
    def __init__(self, path=None):
        self.path = Path(path or os.environ.get("TKD_PROGRESS_DB") or
                         Path(__file__).parent / "data" / "players.sqlite3")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS players (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    name_key TEXT NOT NULL UNIQUE,
                    salt BLOB NOT NULL,
                    password_hash BLOB NOT NULL,
                    coins INTEGER NOT NULL DEFAULT 0 CHECK(coins >= 0),
                    owned TEXT NOT NULL DEFAULT '["Classic White"]',
                    dobok TEXT NOT NULL DEFAULT 'Classic White'
                );
                CREATE TABLE IF NOT EXISTS rewards (
                    player_id INTEGER NOT NULL REFERENCES players(id),
                    event TEXT NOT NULL,
                    PRIMARY KEY(player_id, event)
                );
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def password_hash(password, salt):
        return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1)

    def create(self, name, password):
        name = name.strip()
        if not 1 <= len(name) <= 40:
            raise ValueError("Choose a player name between 1 and 40 characters.")
        if not 8 <= len(password) <= 128:
            raise ValueError("Choose a password between 8 and 128 characters.")
        salt = os.urandom(16)
        digest = self.password_hash(password, salt)
        try:
            with self.connect() as db:
                player_id = db.execute(
                    "INSERT INTO players(name, name_key, salt, password_hash) VALUES (?, ?, ?, ?)",
                    (name, name.casefold(), salt, digest)).lastrowid
        except sqlite3.IntegrityError:
            raise ValueError("That player name is already taken. Sign in or choose another name.") from None
        return self.load(player_id)

    def login(self, name, password):
        with self.connect() as db:
            row = db.execute("SELECT * FROM players WHERE name_key=?",
                             (name.strip().casefold(),)).fetchone()
        if len(password) > 128 or row is None or not hmac.compare_digest(
                self.password_hash(password, row["salt"]), row["password_hash"]):
            raise ValueError("Player name or password is incorrect.")
        return self.load(row["id"])

    def load(self, player_id):
        with self.connect() as db:
            row = db.execute("SELECT id, name, coins, owned, dobok FROM players WHERE id=?",
                             (player_id,)).fetchone()
        if row is None:
            raise ValueError("Player profile could not be found. Please sign in again.")
        result = dict(row)
        result["owned"] = json.loads(result["owned"])
        return result

    def reward(self, player_id, event, amount):
        if amount not in (5, 25):
            raise ValueError("Invalid reward.")
        with self.connect() as db:
            added = db.execute("INSERT OR IGNORE INTO rewards VALUES (?, ?)",
                               (player_id, event)).rowcount
            if added:
                db.execute("UPDATE players SET coins=coins+? WHERE id=?", (amount, player_id))
        return self.load(player_id)

    def equip(self, player_id, name, prices):
        if name not in prices:
            raise ValueError("Unknown dobok.")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT coins, owned FROM players WHERE id=?", (player_id,)).fetchone()
            if row is None:
                raise ValueError("Player profile could not be found.")
            owned = json.loads(row["owned"])
            price = 0 if name in owned else prices[name]
            if row["coins"] < price:
                raise ValueError("You do not have enough coins for this dobok yet.")
            if name not in owned:
                owned.append(name)
            db.execute("UPDATE players SET coins=coins-?, owned=?, dobok=? WHERE id=?",
                       (price, json.dumps(owned), name, player_id))
        return self.load(player_id)
