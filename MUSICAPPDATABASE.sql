-- =============================================================================
-- musicdatabase.sql – Complete Music App Database Setup
-- All roles, tables, RLS policies, functions and grants in one file
-- Run as superuser (postgres) on database 'appformusic'
-- Last updated: February 2026
-- =============================================================================

-- 1. Create all roles if they don't exist
DO $$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'appuser') THEN
        CREATE ROLE appuser WITH LOGIN PASSWORD 'pass123';
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'adminn') THEN
        CREATE ROLE adminn WITH LOGIN PASSWORD 'admin123' BYPASSRLS;
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'listener_free') THEN
        CREATE ROLE listener_free WITH LOGIN PASSWORD 'free123' NOSUPERUSER NOCREATEDB NOCREATEROLE;
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'listener_premium') THEN
        CREATE ROLE listener_premium WITH LOGIN PASSWORD 'premium456' NOSUPERUSER NOCREATEDB NOCREATEROLE;
    END IF;
END $$;

-- 2. Basic database & schema permissions for all roles
GRANT CONNECT ON DATABASE appformusic TO appuser, adminn, listener_free, listener_premium;
GRANT USAGE ON SCHEMA public TO appuser, adminn, listener_free, listener_premium;

-- 3. Songs table – core content
DROP TABLE IF EXISTS songs CASCADE;
CREATE TABLE songs (
    id          SERIAL PRIMARY KEY,
    title       VARCHAR(150) NOT NULL,
    artist      VARCHAR(100) NOT NULL,
    genre       VARCHAR(60)  NOT NULL,
    rating      NUMERIC(3,1) CHECK (rating BETWEEN 0 AND 5),
    is_premium  BOOLEAN DEFAULT FALSE,
    added_by    TEXT NOT NULL DEFAULT current_user
);

-- Enable RLS on songs
ALTER TABLE songs ENABLE ROW LEVEL SECURITY;

-- Policies for song owners (appuser/adminn)
CREATE POLICY own_rows_select ON songs FOR SELECT USING (added_by = current_user);
CREATE POLICY own_rows_insert ON songs FOR INSERT WITH CHECK (added_by = current_user);
CREATE POLICY own_rows_update ON songs FOR UPDATE USING (added_by = current_user);

-- Listener policies (free sees non-premium, premium sees all)
CREATE POLICY listener_free_policy ON songs
    FOR SELECT
    USING (current_user = 'listener_free' AND is_premium = FALSE);

CREATE POLICY listener_premium_policy ON songs
    FOR SELECT
    USING (current_user = 'listener_premium');

-- Privileges on songs
GRANT SELECT, INSERT, UPDATE ON songs TO appuser;
GRANT USAGE, SELECT ON SEQUENCE songs_id_seq TO appuser;

GRANT ALL PRIVILEGES ON songs TO adminn;
GRANT ALL PRIVILEGES ON SEQUENCE songs_id_seq TO adminn;

GRANT SELECT ON songs TO listener_free, listener_premium;

-- 4. Listener Profiles (name + address per role)
CREATE TABLE IF NOT EXISTS listener_profiles (
    user_name    TEXT PRIMARY KEY,
    full_name    VARCHAR(100) NOT NULL,
    address      TEXT NOT NULL,
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE listener_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY own_profile ON listener_profiles
    FOR ALL
    USING (user_name = current_user)
    WITH CHECK (user_name = current_user);

GRANT SELECT, INSERT, UPDATE ON listener_profiles TO listener_free, listener_premium;
GRANT USAGE, SELECT, UPDATE ON SEQUENCE listener_profiles_id_seq TO listener_free, listener_premium;

-- 5. Premium Subscriptions (upgrade simulation)
CREATE TABLE IF NOT EXISTS premium_subscriptions (
    user_name        TEXT PRIMARY KEY REFERENCES listener_profiles(user_name),
    amount           NUMERIC(10,2) DEFAULT 99.99,
    payment_status   TEXT DEFAULT 'completed',
    subscribed_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at       TIMESTAMP,
    added_by         TEXT DEFAULT current_user
);

ALTER TABLE premium_subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY own_subscription ON premium_subscriptions
    FOR ALL
    USING (user_name = current_user)
    WITH CHECK (user_name = current_user);

GRANT SELECT, INSERT, UPDATE ON premium_subscriptions TO listener_free, listener_premium;
GRANT USAGE, SELECT, UPDATE ON SEQUENCE premium_subscriptions_id_seq TO listener_free, listener_premium;

-- 6. Functions

-- Average rating per genre (for appuser/adminn)
CREATE OR REPLACE FUNCTION get_avg_rating_per_genre()
RETURNS TABLE (
    genre_name VARCHAR,
    avg_rating NUMERIC
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT genre, ROUND(AVG(rating), 1)
    FROM songs
    WHERE added_by = current_user
    GROUP BY genre
    ORDER BY avg_rating DESC;
END;
$$;

-- Genre counts for listeners
CREATE OR REPLACE FUNCTION listener_genre_counts()
RETURNS TABLE (
    genre_name VARCHAR,
    song_count BIGINT
)
LANGUAGE sql
SECURITY DEFINER
AS $$
    SELECT genre, COUNT(*)
    FROM songs
    GROUP BY genre
    HAVING COUNT(*) > 0
    ORDER BY COUNT(*) DESC;
$$;

-- Premium recommendations
CREATE OR REPLACE FUNCTION premium_recommendations(limit_count INT DEFAULT 6)
RETURNS TABLE (
    title      VARCHAR,
    artist     VARCHAR,
    genre      VARCHAR,
    rating     NUMERIC,
    is_premium BOOLEAN
)
LANGUAGE sql
SECURITY DEFINER
AS $$
    SELECT title, artist, genre, rating, is_premium
    FROM songs
    WHERE is_premium = TRUE
      AND rating IS NOT NULL
    ORDER BY rating DESC, RANDOM()
    LIMIT limit_count;
$$;

-- Get current user's profile
CREATE OR REPLACE FUNCTION get_listener_profile()
RETURNS TABLE (
    full_name VARCHAR(100),
    address   TEXT
)
LANGUAGE sql
AS $$
    SELECT full_name, address
    FROM listener_profiles
    WHERE user_name = current_user;
$$;

-- Update/create profile
CREATE OR REPLACE FUNCTION update_listener_profile(
    p_full_name VARCHAR(100),
    p_address   TEXT
)
RETURNS TEXT
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO listener_profiles (user_name, full_name, address)
    VALUES (current_user, p_full_name, p_address)
    ON CONFLICT (user_name) DO UPDATE SET
        full_name  = EXCLUDED.full_name,
        address    = EXCLUDED.address,
        updated_at = CURRENT_TIMESTAMP;

    RETURN 'Profile updated successfully.';
EXCEPTION WHEN OTHERS THEN
    RETURN 'Error: ' || SQLERRM;
END;
$$;

-- Simulate premium upgrade
CREATE OR REPLACE FUNCTION subscribe_to_premium()
RETURNS TEXT
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO premium_subscriptions (user_name)
    VALUES (current_user)
    ON CONFLICT (user_name) DO UPDATE SET
        subscribed_at   = CURRENT_TIMESTAMP,
        payment_status  = 'completed';

    RETURN 'Premium subscription successful! (simulated payment of 99.99)';
EXCEPTION WHEN OTHERS THEN
    RETURN 'Error: ' || SQLERRM;
END;
$$;

-- Grant function execution rights
GRANT EXECUTE ON FUNCTION get_avg_rating_per_genre()          TO appuser, adminn;
GRANT EXECUTE ON FUNCTION listener_genre_counts()             TO listener_free, listener_premium;
GRANT EXECUTE ON FUNCTION premium_recommendations(INT)        TO listener_premium;
GRANT EXECUTE ON FUNCTION get_listener_profile()              TO listener_free, listener_premium;
GRANT EXECUTE ON FUNCTION update_listener_profile(VARCHAR, TEXT) TO listener_free, listener_premium;
GRANT EXECUTE ON FUNCTION subscribe_to_premium()              TO listener_free, listener_premium;

-- =============================================================================
-- End of file – all roles and features created
-- Run this file once as superuser to set up everything
-- =============================================================================
