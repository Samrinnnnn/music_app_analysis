# listenerr.py
# Requirements: pip install psycopg2-binary matplotlib

import psycopg2
import matplotlib.pyplot as plt

# ── Change these two lines to switch users ───────────────────────────────
DB_USER = "listener_premium"             # or "distributer" or "listener_free" or "listener_premium"
DB_PASSWORD_MAP = {
    "appuser":        "pass123",
    "adminn":    "admin123",
    "listener_free":  "free123",
    "listener_premium": "premium456"
}
# ──────────────────────────────────────────────────────────────────────────

DB_CONFIG = {
    "dbname":   "appformusic",
    "user":     DB_USER,
    "password": DB_PASSWORD_MAP.get(DB_USER, "unknown_user"),
    "host":     "localhost",
    "port":     5432
}

def connect():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print(f"Connected successfully as: {DB_USER}")
        return conn
    except Exception as e:
        print(f"Connection failed: {e}")
        raise

def add_song(conn, title, artist, genre, rating, is_premium=False):
    if DB_USER not in ["appuser", "adminn"]:
        print("Only appuser / distributer can add songs.")
        return
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO songs (title, artist, genre, rating, is_premium)
            VALUES (%s, %s, %s, %s, %s)
        """, (title, artist, genre, rating, is_premium))
    conn.commit()
    print(f"Added → {title} ({genre}) {rating}/5  premium={is_premium}")

def show_songs(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT title, artist, genre, rating, is_premium
            FROM songs
            ORDER BY id DESC
            LIMIT 12
        """)
        rows = cur.fetchall()

    if not rows:
        print("No songs visible.")
        return

    print(f"\nShowing songs visible to {DB_USER} ({len(rows)} rows):")
    for r in rows:
        premium_tag = " [Premium]" if r[4] else ""
        print(f"  • {r[0]:<30} {r[1]:<20} {r[2]:<12} {r[3]}{premium_tag}")

def show_avg_per_genre(conn):
    if DB_USER not in ["appuser", "adminn"]:
        print("Averages & dashboard only available to appuser / distributer")
        return None

    with conn.cursor() as cur:
        cur.execute("SELECT * FROM get_avg_rating_per_genre()")
        rows = cur.fetchall()

    if not rows:
        print("No data yet.")
        return None

    print(f"\nAverage rating per genre (function result):")
    for genre, avg in rows:
        print(f"  {genre:18} → {avg:.1f}")

    return rows

def show_listener_genre_counts(conn):
    if DB_USER not in ["listener_free", "listener_premium"]:
        return

    with conn.cursor() as cur:
        cur.execute("SELECT * FROM listener_genre_counts()")
        rows = cur.fetchall()

    if not rows:
        print("No songs available in your tier.")
        return

    print(f"\nAvailable songs per genre ({DB_USER}):")
    for genre, cnt in rows:
        print(f"  {genre:18} → {cnt} songs")

def plot_genre_avg(data):
    if not data or DB_USER not in ["appuser", "adminn"]:
        return

    genres = [row[0] for row in data]
    avgs   = [float(row[1]) for row in data]

    plt.figure(figsize=(8, 5))
    bars = plt.bar(genres, avgs, color='cornflowerblue', edgecolor='navy')
    plt.bar_label(bars, fmt='%.1f')

    plt.title(f"Your Average Song Rating per Genre – {DB_USER}")
    plt.xlabel("Genre")
    plt.ylabel("Average Rating")
    plt.ylim(0, 5.5)
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()

    filename = f"genre_avg_{DB_USER}.png"
    plt.savefig(filename)
    plt.show()
    print(f"Chart saved as: {filename}")

def main():
    conn = connect()
    try:
        if DB_USER in ["listener_free", "listener_premium"]:
            print("\nListener mode – you can only listen (no dashboard)")
            show_songs(conn)
            show_listener_genre_counts(conn)
        else:
            # Original behavior preserved
            print("\nAdding example songs (only appuser/adminn)...")
            add_song(conn, "Lover", "Taylor Swift", "Pop", 4.5, False)
            add_song(conn, "APT", "ROSE & Bruno Mars", "K-Pop", 4.0, True)
            # ... add more if you want

            show_songs(conn)
            avg_data = show_avg_per_genre(conn)
            plot_genre_avg(avg_data)

        print("\nDone.")

    except Exception as e:
        print("Error:", e)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
