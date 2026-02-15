# listenerr.py
# Requirements: pip install psycopg2-binary matplotlib

import psycopg2
import matplotlib.pyplot as plt

# ── Change user here to test different roles ─────────────────────────────
DB_USER = "adminn"   # options: appuser, adminn, listener_free, listener_premium

DB_PASSWORD_MAP = {
    "appuser":        "pass123",
    "adminn":         "admin123",
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
        print("Only appuser / adminn can add songs.")
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

def search_song(conn, search_term):
    if not search_term.strip():
        print("No search term entered.")
        return

    with conn.cursor() as cur:
        cur.execute("""
            SELECT title, artist, genre, rating, is_premium
            FROM songs
            WHERE LOWER(title) LIKE LOWER(%s)
               OR LOWER(artist) LIKE LOWER(%s)
            ORDER BY title
            LIMIT 8
        """, (f"%{search_term}%", f"%{search_term}%"))
        rows = cur.fetchall()

        if not rows:
            print(f"No songs found matching '{search_term}'")
            return

        print(f"\nSearch results for '{search_term}' ({len(rows)} found):")
        for row in rows:
            title, artist, genre, rating, is_premium = row
            premium_tag = " [Premium]" if is_premium else ""

            if DB_USER == "listener_free" and is_premium:
                print(f"  • {title:<35} {artist:<20} → Sorry, this is a premium song. Upgrade to listen.")
            else:
                print(f"  • {title:<35} {artist:<20} {genre:<12} {rating}{premium_tag}")

def show_listener_genre_counts(conn):
    if DB_USER not in ["listener_free", "listener_premium"]:
        return

    with conn.cursor() as cur:
        cur.execute("SELECT * FROM listener_genre_counts()")
        rows = cur.fetchall()

    if not rows:
        print("No genres available in your tier yet.")
        return

    print(f"\nAvailable songs per genre ({DB_USER}):")
    for genre, cnt in rows:
        print(f"  {genre:18} → {cnt} songs")

def show_premium_recommendations(conn):
    if DB_USER != "listener_premium":
        print("Personalized recommendations available only for premium users.")
        return

    with conn.cursor() as cur:
        cur.execute("SELECT * FROM premium_recommendations(8)")
        rows = cur.fetchall()

        if not rows:
            print("No premium recommendations available yet (need more premium songs with ratings).")
            return

        print(f"\nYour Premium Recommendations ({len(rows)} songs):")
        print("   (top-rated premium tracks)")
        for row in rows:
            title, artist, genre, rating, is_premium = row
            print(f"  • {title:<35} {artist:<20} {genre:<12} {rating} [Premium]")

def get_listener_profile(conn):
    if DB_USER not in ["listener_free", "listener_premium"]:
        return None, None

    with conn.cursor() as cur:
        cur.execute("SELECT * FROM get_listener_profile()")
        row = cur.fetchone()
        if row:
            return row[0], row[1]
        return None, None

def update_listener_profile(conn):
    if DB_USER not in ["listener_free", "listener_premium"]:
        print("Profile update only for listeners.")
        return

    full_name = input("Enter your full name: ").strip()
    address = input("Enter your address: ").strip()

    if not full_name or not address:
        print("Name and address required.")
        return

    with conn.cursor() as cur:
        cur.execute("SELECT update_listener_profile(%s, %s)", (full_name, address))
        result = cur.fetchone()[0]
        conn.commit()
        print(result)

def upgrade_to_premium(conn):
    if DB_USER != "listener_free":
        print("Upgrade option only available for free listeners.")
        return

    print("\nUpgrade to Premium for full access? (Price: 99.99) [y/n]")
    choice = input("> ").strip().lower()
    if choice in ['y', 'yes', 'yep']:
        with conn.cursor() as cur:
            cur.execute("SELECT subscribe_to_premium(%s)", (DB_USER,))
            result = cur.fetchone()[0]
            conn.commit()
            print(result)
            print("You are now premium! Restart script with DB_USER = 'listener_premium' to enjoy full access.")
    else:
        print("Upgrade cancelled.")

def main():
    conn = connect()
    try:
        if DB_USER in ["listener_free", "listener_premium"]:
            print("\nListener mode – you can only listen (no dashboard)")

            # Profile check + prompt
            name, address = get_listener_profile(conn)
            if name and address:
                print(f"Welcome, {name} from {address}!")
            else:
                print("No profile found yet. Add your details? (y/n)")
                choice = input("> ").strip().lower()
                if choice in ['y', 'yes', 'yep']:
                    update_listener_profile(conn)
                    name, address = get_listener_profile(conn)
                    if name and address:
                        print(f"Welcome, {name} from {address}!")

            # Upgrade prompt for free listener
            if DB_USER == "listener_free":
                upgrade_to_premium(conn)

            show_songs(conn)
            show_listener_genre_counts(conn)

            # Search loop
            print("\nSearch songs by title or artist (type 'exit' to quit)")
            while True:
                term = input("> ").strip()
                if term.lower() == "exit":
                    break
                if term:
                    search_song(conn, term)

            # Recommendation prompt – only for premium
            if DB_USER == "listener_premium":
                print("\nWould you like personalized recommendations? (y/n)")
                choice = input("> ").strip().lower()
                if choice in ['y', 'yes', 'yep']:
                    show_premium_recommendations(conn)

        else:
            # Original full mode for appuser / adminn
            print("\nAdding example songs...")
            # add_song(conn, "Timi Aajha Bholi", "Sudip Giri", "Pop", 4.0, True)
            # add_song(conn, "Furfuri", "Kuma Sagar", "Pop", 4.5, True)
            # add_song(conn, "K Yo Maya Ho", "Nabin K Bhattarai", "Pop", 3.5, True)

            show_songs(conn)
            avg_data = show_avg_per_genre(conn)
            plot_genre_avg(avg_data)

            # Search for appuser & adminn too
            print("\nSearch songs by title or artist (type 'exit' to quit)")
            while True:
                term = input("> ").strip()
                if term.lower() == "exit":
                    break
                if term:
                    search_song(conn, term)

        print("\nDone. Change DB_USER to test other roles.")

    except Exception as e:
        print("Error:", e)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
