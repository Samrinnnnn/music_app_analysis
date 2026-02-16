# music_app_multi_tenant.py
# Multi-tenant music app demo
# - Free users see only non-premium songs
# - appuser sees own uploads + personal stats
# - adminn sees ALL songs in tenant + who uploaded them + stats
# Requirements: pip install psycopg2-binary matplotlib

import psycopg2
import matplotlib.pyplot as plt
from psycopg2 import Error as PsycopgError

# ── CHANGE THESE TO TEST DIFFERENT ROLES / TENANTS ──────────────────────────
DB_USER      = "appuser"                                   # appuser, adminn, listener_free, listener_premium
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


def add_song(conn, title, artist, genre, rating, is_premium=False):
    if DB_USER not in ["appuser", "adminn"]:
        print("Only appuser/adminn can add songs.")
        return
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO songs (title, artist, genre, rating, is_premium, tenant_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (title, artist, genre, rating, is_premium, DB_TENANT_ID))
        print(f"Added → {title} ({genre}) {rating}/5  premium={is_premium}")
    except PsycopgError as e:
        print(f"Add song failed: {e}")


def show_songs_dashboard(conn):
    if DB_USER not in ["appuser", "adminn"]:
        return

    try:
        with conn.cursor() as cur:
            if DB_USER == "adminn":
                # Admin sees ALL songs in the tenant + uploader info
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
                    title, artist, genre, rating, is_premium, added_by = r
                    tag = " [Premium]" if is_premium else ""
                    print(f"  • {title:<35} {artist:<20} {genre:<12} {rating}{tag}  (by {added_by})")

            else:
                # appuser sees only their own songs
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
                    title, artist, genre, rating, is_premium = r
                    tag = " [Premium]" if is_premium else ""
                    print(f"  • {title:<35} {artist:<20} {genre:<12} {rating}{tag}")

    except PsycopgError as e:
        print(f"Error loading songs dashboard: {e}")


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
        for genre, avg in rows:
            print(f"  {genre:18} → {avg:.1f}")

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

        print("\nDone.")

    except Exception as e:
        print(f"Main error: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
