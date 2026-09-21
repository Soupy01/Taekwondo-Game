# TKD Terminology Quest — Streamlit v6

- Attempt 5, 10, 15, 20, 25, 50, 100, 200, 360, or All available questions.
- All available runs every question matching the current filters.
- Upgraded illustrated Dobok Shop; equipped dobok is displayed in the quiz.
- Question Type is available in both games.
- Question Source is available only in Full Answer Theory Test.

- Select Dobok Shop under Game type in the sidebar; buy and wear doboks without leaving the shop.
- Written answers: type, press Ctrl+Enter (Command+Enter on Mac) or Check answer, then choose Correct & next or Incorrect & next. Marking advances immediately.

## Saved player profiles

Start the game with `python -m streamlit run app.py`.

Choose **Create player**, enter a player name and a password of at least 8 characters,
and confirm the password. On later visits, choose **Sign in** with the same details.
Player names are case-insensitive. Use **Sign out / switch player** before another
person plays on the same browser. Passwords are stored as salted hashes, not plain text.
There is no password recovery flow, so keep your login details safe.

Coins, purchased doboks, and the equipped dobok save immediately. A refresh or app
restart keeps that progress; sign in again to restore it. An unfinished quiz is not
saved, but coins already earned in it are kept. New profiles start with zero coins
and Classic White. Progress lost before this feature was installed cannot be recovered.

The default database is `data/players.sqlite3`, next to `app.py`. It is created
automatically and excluded from version control. To back it up, stop the app and copy
that file somewhere safe. Restore it to the same location while the app is stopped.
Do not delete it when updating the game.

For a different storage location, set `TKD_PROGRESS_DB` to an absolute database file
path before starting Streamlit. For example, in PowerShell:

```powershell
$env:TKD_PROGRESS_DB = 'C:\TKDData\players.sqlite3'
python -m streamlit run app.py
```

This version saves to the computer running Streamlit. Online deployment requires a
persistent writable disk mounted at that path; ephemeral hosting storage will not
keep this database reliably. A deployment across multiple app servers needs a shared
database implementation before use. This change does not provision online storage.

Run the storage and app-flow tests with `python -m unittest -v test_progress`.
Tests use temporary databases and do not change real player progress.
