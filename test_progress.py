import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from progress import ProgressStore
from streamlit.testing.v1 import AppTest


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "players.sqlite3"
        self.store = ProgressStore(self.path)
        self.player = self.store.create("Player One", "test-password")

    def tearDown(self):
        self.temp.cleanup()

    def test_login_and_separate_profiles(self):
        self.assertEqual(self.store.login(" player ONE ", "test-password")["id"], self.player["id"])
        with self.assertRaises(ValueError):
            self.store.login("Player One", "wrong-password")
        with self.assertRaises(ValueError):
            self.store.create("PLAYER ONE", "test-password")
        other = self.store.create("Player Two", "another-password")
        self.store.reward(self.player["id"], "q1", 5)
        self.assertEqual(self.store.load(other["id"])["coins"], 0)

    def test_persistence_idempotency_and_shop(self):
        pid = self.player["id"]
        for i in range(12):
            self.store.reward(pid, f"question-{i}", 5)
        self.store.reward(pid, "question-0", 5)
        prices = {"Classic White": 0, "Ocean Blue": 60, "Forest Green": 90}
        profile = self.store.equip(pid, "Ocean Blue", prices)
        self.assertEqual(profile["coins"], 0)
        self.store.equip(pid, "Ocean Blue", prices)
        with self.assertRaises(ValueError):
            self.store.equip(pid, "Forest Green", prices)
        restored = ProgressStore(self.path).login("Player One", "test-password")
        self.assertEqual(restored["coins"], 0)
        self.assertEqual(restored["dobok"], "Ocean Blue")
        self.assertEqual(restored["owned"], ["Classic White", "Ocean Blue"])

    def test_concurrent_rewards_and_purchase(self):
        pid = self.player["id"]
        with ThreadPoolExecutor(max_workers=4) as workers:
            list(workers.map(lambda i: self.store.reward(pid, f"q-{i % 12}", 5), range(24)))
            list(workers.map(lambda _: self.store.equip(pid, "Ocean Blue", {"Ocean Blue": 60}), range(4)))
        profile = self.store.load(pid)
        self.assertEqual(profile["coins"], 0)
        self.assertEqual(profile["owned"].count("Ocean Blue"), 1)

    def test_app_refresh_signout_rewards_and_shop(self):
        with patch.dict(os.environ, {"TKD_PROGRESS_DB": str(self.path)}):
            app_path = str(Path(__file__).with_name("app.py"))
            at = AppTest.from_file(app_path).run()

            def click(label):
                next(b for b in at.button if b.label == label).click().run()
                self.assertFalse(at.exception)

            def login():
                at.text_input[0].input("Player One")
                at.text_input[1].input("test-password")
                click("Sign in")

            login()
            at.sidebar.radio[0].set_value("Full Answer Theory Test").run()
            click("Start new game")
            # A one-question round exercises both answer and completion rewards.
            at.session_state.game = at.session_state.game[:1]
            at.text_area[0].input("My answer")
            click("Check answer")
            click("Correct & finish")
            self.assertEqual(self.store.load(self.player["id"])["coins"], 30)
            at.run()
            self.assertEqual(self.store.load(self.player["id"])["coins"], 30)
            click("Play another round")
            at.session_state.game = at.session_state.game[:1]
            at.text_area[0].input("Another answer")
            click("Check answer")
            click("Correct & finish")
            at.sidebar.radio[0].set_value("Dobok Shop").run()
            at.button(key="buy-Ocean Blue").click().run()
            self.assertFalse(at.exception)
            self.assertEqual(at.session_state.coins, 0)
            # A new app instance has no session state, like a refreshed browser.
            at = AppTest.from_file(app_path).run()
            login()
            self.assertEqual(at.session_state.dobok, "Ocean Blue")
            self.assertIn("Ocean Blue", at.session_state.owned)
            self.assertIsNone(at.session_state.game)
            click("Sign out / switch player")
            self.assertNotIn("player_id", at.session_state)
            at.radio[0].set_value("Create player").run()
            at.text_input[0].input("New Player")
            at.text_input[1].input("new-password")
            at.text_input[2].input("new-password")
            click("Create player")
            self.assertEqual(at.session_state.coins, 0)
            self.assertEqual(at.session_state.dobok, "Classic White")
            at.sidebar.radio[0].set_value("Multiple Choice Game").run()
            click("Start new game")
            at.radio[0].set_value(at.session_state.game[0]["correct"]).run()
            click("Check answer")
            self.assertEqual(self.store.login("New Player", "new-password")["coins"], 5)
            click("Next question")
            self.assertEqual(at.session_state.index, 1)


if __name__ == "__main__":
    unittest.main()
