# finL.py
# Updated: Added search option for all roles
# Requirements: pip install psycopg2-binary matplotlib

import psycopg2
import matplotlib.pyplot as plt
from psycopg2 import Error as PsycopgError

# ── CHANGE THESE TO TEST DIFFERENT ROLES / TENANTS ──────────────────────────
DB_USER      = "listener_premium"                         # appuser, adminn, listener_free, listener_premium
DB_TENANT_ID = "244f866c-7a71-460e-a493-2c4a9daf4e7e"     # ← real UUID from your tenants table
# ─────────────────────────────────────────────────────────────────────────────

DB_PASSWORD_MAP = {
    "appuser":        "pass123",
    "adminn":         "admin123",
    "listener_free":  "free123",
    "listener_premium": "premium456"
}

DB_CONFIG = {
    "dbname":   "appformusic",
    "user":     DB_USER,
    "password": DB_PASSWORD_MAP.get(DB_USER, "unknown"),
    "host":     "localhost",
    "port":     5432
}

def connect():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True

        print(f"Connected as {DB_USER}")

        with conn.cursor() as cur:
            cur.execute("SELECT set_app_current_tenant(%s)", (DB_TENANT_ID,))
            cur.execute("SHOW app.current_tenant;")
            print(f"→ Tenant: {cur.fetchone()[0]}")

        return conn
    except PsycopgError as e:
        print(f"Connection / tenant setup failed: {e}")
        raise


def add_song_interactive(conn):
    if DB_USER not in ["appuser", "adminn"]:
        print("Only appuser/adminn can add songs.")
        return
    print("\n=== Add New Song ===")
    title  = input("Song title: ").strip()
    artist = input("Artist: ").strip()
    genre  = input("Genre: ").strip()

    while True:
        try:
            rating = float(input("Rating (0.0–5.0): ").strip())
            if 0 <= rating <= 5:
                break
            print("Rating must be between 0.0 and 5.0")
        except ValueError:
            print("Please enter a valid number")

    premium_input = input("Premium song? [y/n]: ").strip().lower()
    is_premium = premium_input in ('y', 'yes', '1')

    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO songs (title, artist, genre, rating, is_premium, tenant_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (title, artist, genre, rating, is_premium, DB_TENANT_ID))
        print(f"\nSong added: {title} by {artist} ({genre}, {rating}/5, {'Premium' if is_premium else 'Free'})")
    except PsycopgError as e:
        print(f"Failed to add song: {e}")


def show_songs_dashboard(conn):
    if DB_USER not in ["appuser", "adminn"]:
        return
    try:
        with conn.cursor() as cur:
            if DB_USER == "adminn":
                cur.execute("""
                    SELECT title, artist, genre, rating, is_premium, added_by
                    FROM songs
                    ORDER BY id DESC
                    LIMIT 30
                """)
                rows = cur.fetchall()

                if not rows:
                    print("No songs exist in this tenant yet.")
                    return

                print(f"\nAll songs in tenant ({len(rows)}):")
                for r in rows:
                    t, a, g, r_val, p, by = r
                    tag = " [Premium]" if p else ""
                    print(f"  • {t:<35} {a:<20} {g:<12} {r_val}{tag}  (by {by})")

            else:
                cur.execute("""
                    SELECT title, artist, genre, rating, is_premium
                    FROM songs
                    WHERE added_by = current_user
                    ORDER BY id DESC
                    LIMIT 15
                """)
                rows = cur.fetchall()

                if not rows:
                    print("You haven't uploaded any songs yet.")
                    return

                print(f"\nYour uploaded songs ({len(rows)}):")
                for r in rows:
                    t, a, g, r_val, p = r
                    tag = " [Premium]" if p else ""
                    print(f"  • {t:<35} {a:<20} {g:<12} {r_val}{tag}")

    except PsycopgError as e:
        print(f"Error loading songs: {e}")


def show_avg_rating_dashboard(conn):
    if DB_USER not in ["appuser", "adminn"]:
        return None
    prefix = "Tenant-wide" if DB_USER == "adminn" else "Your"
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM get_avg_rating_per_genre()")
            rows = cur.fetchall()

        if not rows:
            print(f"No rated songs yet ({prefix.lower()}).")
            return None

        print(f"\n{prefix} average rating per genre:")
        for g, avg in rows:
            print(f"  {g:18} → {avg:.1f}")

        return rows
    except PsycopgError as e:
        print(f"Error getting averages: {e}")
        return None


def plot_genre_avg(data):
    if not data:
        return
    genres = [row[0] for row in data]
    avgs   = [float(row[1]) for row in data]

    plt.figure(figsize=(9, 5))
    bars = plt.bar(genres, avgs, color='teal', edgecolor='darkgreen')
    plt.bar_label(bars, fmt='%.1f')
    plt.title(f"Average Song Ratings per Genre – {DB_USER}")
    plt.xlabel("Genre")
    plt.ylabel("Average Rating")
    plt.ylim(0, 5.5)
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()

    filename = f"genre_avg_{DB_USER}.png"
    plt.savefig(filename)
    plt.show()
    print(f"Chart saved as: {filename}")


def show_songs_for_listeners(conn):
    try:
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

        print(f"\nSongs visible to {DB_USER} (tenant {DB_TENANT_ID[:8]}…):")
        visible = 0
        for r in rows:
            if DB_USER == "listener_free" and r[4]:
                continue
            visible += 1
            tag = " [Premium]" if r[4] else ""
            print(f"  • {r[0]:<35} {r[1]:<20} {r[2]:<12} {r[3]}{tag}")

        if visible == 0 and DB_USER == "listener_free":
            print("  (Only premium content exists – none visible to free users)")

    except PsycopgError as e:
        print(f"Error: {e}")


def show_genre_counts(conn):
    if DB_USER not in ["listener_free", "listener_premium"]:
        return
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM listener_genre_counts()")
            rows = cur.fetchall()
        if not rows:
            print("No genres yet.")
            return
        print(f"\nAvailable songs per genre:")
        for g, cnt in rows:
            print(f"  {g:18} → {cnt}")
    except PsycopgError as e:
        print(f"Genre counts error: {e}")

def search_song(conn):
    print("\nSearch songs (title or artist) – type 'exit' to stop")
    while True:
        term = input("> ").strip()
        if term.lower() == "exit":
            break
        if not term:
            continue

        try:
            with conn.cursor() as cur:
                if DB_USER in ["appuser", "adminn"]:
                    # For uploaders: filter by ownership (appuser own only, admin all)
                    if DB_USER == "appuser":
                        cur.execute("""
                            SELECT title, artist, genre, rating, is_premium
                            FROM songs
                            WHERE (LOWER(title) LIKE LOWER(%s) OR LOWER(artist) LIKE LOWER(%s))
                              AND added_by = current_user
                            ORDER BY title
                            LIMIT 10
                        """, (f"%{term}%", f"%{term}%"))
                    else:  # adminn sees all
                        cur.execute("""
                            SELECT title, artist, genre, rating, is_premium
                            FROM songs
                            WHERE LOWER(title) LIKE LOWER(%s)
                               OR LOWER(artist) LIKE LOWER(%s)
                            ORDER BY title
                            LIMIT 10
                        """, (f"%{term}%", f"%{term}%"))
                else:
                    # Listeners use broad search (already filtered by RLS)
                    cur.execute("""
                        SELECT title, artist, genre, rating, is_premium
                        FROM songs
                        WHERE LOWER(title) LIKE LOWER(%s)
                           OR LOWER(artist) LIKE LOWER(%s)
                        ORDER BY title
                        LIMIT 10
                    """, (f"%{term}%", f"%{term}%"))

                rows = cur.fetchall()

            if not rows:
                print(f"No results for '{term}'")
                continue

            print(f"\nResults for '{term}' ({len(rows)} found):")
            visible = 0
            for r in rows:
                title, artist, genre, rating, is_premium = r
                if DB_USER == "listener_free" and is_premium:
                    continue
                visible += 1
                tag = " [Premium]" if is_premium else ""
                print(f"  • {title:<35} {artist:<20} {genre:<12} {rating}{tag}")

            if visible == 0:
                print("  No matching songs visible to your role.")

        except PsycopgError as e:
            print(f"Search error: {e}")



def show_premium_recommendations(conn):
    if DB_USER != "listener_premium":
        return
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM premium_recommendations(6)")
            rows = cur.fetchall()

        if not rows:
            print("\nNo premium recommendations available yet.")
            return

        print(f"\nYour Premium Recommendations ({len(rows)} songs):")
        print("   (top-rated premium tracks in your tenant)")
        for row in rows:
            t, a, g, r, p = row
            print(f"  • {t:<35} {a:<20} {g:<12} {r} [Premium]")

    except PsycopgError as e:
        print(f"Recommendations error: {e}")


def get_profile(conn):
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM get_listener_profile()")
            row = cur.fetchone()
            return row if row else (None, None)
    except PsycopgError as e:
        print(f"Profile read error: {e}")
        return None, None


def update_profile(conn):
    if DB_USER not in ["listener_free", "listener_premium"]:
        return
    name = input("Full name: ").strip()
    addr = input("Address: ").strip()
    if not name or not addr:
        print("Required fields missing.")
        return
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT update_listener_profile(%s, %s)", (name, addr))
            print(cur.fetchone()[0])
    except PsycopgError as e:
        print(f"Profile update failed: {e}")


def upgrade_to_premium(conn):
    if DB_USER != "listener_free":
        return
    print("\nUpgrade to Premium? [y/n]")
    if input("> ").strip().lower().startswith('y'):
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT subscribe_to_premium()")
                print(cur.fetchone()[0])
            print("→ Premium activated! Restart with listener_premium.")
        except PsycopgError as e:
            print(f"Upgrade failed: {e}")
    else:
        print("Cancelled.")


def main():
    conn = None
    try:
        conn = connect()

        print(f"\nMode: {DB_USER}")

        if DB_USER in ["appuser", "adminn"]:
            print("=== Dashboard ===")

            show_songs_dashboard(conn)
            avg_data = show_avg_rating_dashboard(conn)
            if avg_data:
                plot_genre_avg(avg_data)

            while True:
                print("\nOptions:")
                print("  [a] Add new song")
                print("  [s] Search songs")
                print("  [r] Refresh dashboard")
                print("  [q] Quit dashboard")
                choice = input("Choose: ").strip().lower()

                if choice == 'q':
                    break
                elif choice == 'a':
                    add_song_interactive(conn)
                    show_songs_dashboard(conn)
                elif choice == 's':
                    search_song(conn)
                elif choice == 'r':
                    show_songs_dashboard(conn)
                else:
                    print("Invalid choice.")

        else:  # listener mode
            name, addr = get_profile(conn)
            if name:
                print(f"Welcome, {name} ({addr})")
            else:
                print("No profile yet. Create one? [y/n]")
                if input("> ").strip().lower().startswith('y'):
                    update_profile(conn)
                    name, addr = get_profile(conn)
                    if name:
                        print(f"Hi {name}!")

            if DB_USER == "listener_free":
                upgrade_to_premium(conn)

            show_songs_for_listeners(conn)
            show_genre_counts(conn)

            # Search option for listeners too
            print("\nSearch songs (title or artist) – type 'exit' to continue")
            search_song(conn)

            if DB_USER == "listener_premium":
                print("\nWould you like personalized premium recommendations? [y/n]")
                if input("> ").strip().lower().startswith('y'):
                    show_premium_recommendations(conn)

        print("\nDone. Change DB_USER to switch roles.")

    except Exception as e:
        print(f"Main error: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
