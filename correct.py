import psycopg2
import matplotlib.pyplot as plt
import sys

# ---------------- DB CONNECTION ----------------
conn = psycopg2.connect(
    dbname="musicapp",
    user="app_user",
    password="samrin1234",
    host="localhost",
    port="5432"
)
cur = conn.cursor()

# ---------------- CONTEXT SETTER (RLS) ----------------
def set_context(role, distributor=None, subscription="free"):
    cur.execute("SELECT set_config('app.user_role', %s, false);", (role,))
    cur.execute(
        "SELECT set_config('app.current_distributor', %s, false);",
        (distributor if distributor else 'admin',)
    )
    cur.execute(
        "SELECT set_config('app.subscription_level', %s, false);",
        (subscription,)
    )
    conn.commit()

# ---------------- INSERT SONG ----------------
def insert_song():
    title = input("Song title: ").strip()
    genre = input("Genre: ").strip().lower()
    premium = input("Premium (yes/no): ").lower() == "yes"
    year = int(input("Release year: "))

    cur.execute(
        "SELECT add_song(%s,%s,%s,%s);",
        (title, genre, premium, year)
    )
    conn.commit()
    print("✅ Song inserted")

# ---------------- GET SONG ID ----------------
def get_song_id(name):
    cur.execute(
        "SELECT song_id FROM songs WHERE song_title ILIKE %s;",
        (name,)
    )
    row = cur.fetchone()
    return row[0] if row else None

# ---------------- REGISTER LISTEN ----------------
def register_listen():
    name = input("Song name: ").strip()
    country = input("Listener country: ").strip()

    song_id = get_song_id(name)
    if not song_id:
        print("❌ Song not found")
        return

    cur.execute(
        "SELECT register_listen(%s,%s);",
        (song_id, country)
    )
    conn.commit()
    print(f"🎧 Listen registered for {country}")

# ---------------- SEARCH ----------------
def search():
    text = input("Search text: ")
    cur.execute("SELECT * FROM search_song_artist(%s);", (text,))
    rows = cur.fetchall()

    if not rows:
        print("❌ Sorry, not available")
        return

    for r in rows:
        print(f"{r[0]} | {r[1]} | {r[2]}")
        #new
        

# ---------------- RECOMMEND ----------------
def recommend():
    genre = input("Genre: ").strip().lower()
    cur.execute("SELECT * FROM recommend_songs(%s);", (genre,))
    rows = cur.fetchall()

    if not rows:
        print("❌ No recommendations")
        return

    for r in rows:
        print(f"{r[0]} - {r[1]}")

# ---------------- DASHBOARD ----------------
def plot(fn, title):
    cur.execute(f"SELECT * FROM {fn}();")
    data = cur.fetchall()

    if not data:
        print("No data")
        return

    labels = [d[0] for d in data]
    values = [int(d[1]) for d in data]

    plt.figure()
    plt.bar(labels, values)
    plt.title(title)
    plt.show()

def dashboard():
    while True:
        print("\n--- ADMIN DASHBOARD ---")
        print("1. Popular Genres")
        print("2. Free vs Premium")
        print("3. Country-wise Listening")
        print("4. Back")

        ch = input("Choose: ")

        if ch == "1":
            plot("popular_genres", "Popular Genres")
        elif ch == "2":
            plot("free_vs_premium", "Free vs Premium")
        elif ch == "3":
            plot("country_listen_stats", "Country-wise Listening")
        elif ch == "4":
            return

# ---------------- MENU ----------------
def menu(role):
    while True:
        print("\n--- MENU ---")
        print("1.Insert 2.Listen 3.Search 4.Recommend 5.Dashboard 6.Exit")
        ch = input("Choose: ")

        if ch == "1" and role in ["admin", "distributor"]:
            insert_song()

        elif ch == "2":
            register_listen()

        elif ch == "3":
            search()

        elif ch == "4":
            recommend()

        elif ch == "5":
            if role == "admin":
                dashboard()
            else:
                print("❌ Dashboard only for admin")

        elif ch == "6":
            print("👋 Exit")
            sys.exit()

        else:
            print("❌ Invalid option")

# ---------------- LOGIN ----------------
role = input("Role (admin/distributor/listener): ").lower()

if role == "admin":
    if input("Admin password: ") != "admin123":
        print("❌ Wrong password")
        sys.exit()
    set_context("admin")

elif role == "distributor":
    dist = input("Distributor (nepal/india/usa/brazil): ").lower()
    set_context("distributor", distributor=dist)

elif role == "listener":
    sub = input("Subscription (free/premium): ").lower()
    set_context("listener", subscription=sub)

else:
    print("❌ Invalid role")
    sys.exit()

menu(role)
