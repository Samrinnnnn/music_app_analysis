-- Create roles
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

GRANT CONNECT ON DATABASE appformusic TO appuser, adminn;
GRANT USAGE ON SCHEMA public TO appuser, adminn;

-- Create table
DROP TABLE IF EXISTS songs;
CREATE TABLE songs (
    id          SERIAL PRIMARY KEY,
    title       VARCHAR(150) NOT NULL,
    artist      VARCHAR(100) NOT NULL,
    genre       VARCHAR(60)  NOT NULL,
    rating      NUMERIC(3,1) CHECK (rating BETWEEN 0 AND 5),
    added_by    TEXT         NOT NULL DEFAULT current_user
);

-- Enable RLS
ALTER TABLE songs ENABLE ROW LEVEL SECURITY;

-- Policies – users see/insert/modify only their own rows
CREATE POLICY own_rows_select ON songs
    FOR SELECT
    USING (added_by = current_user);

CREATE POLICY own_rows_insert ON songs
    FOR INSERT
    WITH CHECK (added_by = current_user);

CREATE POLICY own_rows_update ON songs
    FOR UPDATE
    USING (added_by = current_user);

-- Give privileges
GRANT SELECT, INSERT, UPDATE ON songs TO appuser;
GRANT USAGE, SELECT ON SEQUENCE songs_id_seq TO appuser;

GRANT ALL ON songs TO adminn;
GRANT ALL ON SEQUENCE songs_id_seq TO adminn;

-- Simple PostgreSQL function (average rating per genre for current user)
CREATE OR REPLACE FUNCTION get_avg_rating_per_genre()
RETURNS TABLE (
    genre_name VARCHAR,
    avg_rating NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.genre,
        ROUND(AVG(s.rating), 1)
    FROM songs s
    WHERE s.added_by = current_user
    GROUP BY s.genre
    ORDER BY avg_rating DESC;
END;
$$ LANGUAGE plpgsql;
Delete from songs
    where id=13;
select *from songs;

-- Add is_premium flag to songs (premium content marker)
ALTER TABLE songs 
ADD COLUMN IF NOT EXISTS is_premium BOOLEAN DEFAULT FALSE;

-- Example: mark some songs as premium (you can run this multiple times)
UPDATE songs SET is_premium = TRUE 
WHERE title IN ('Parelima', 'Gajalu', 'la la la', 'Bola Maya', 'Mero Mann Ma','Maya Garnu La');  -- your choice

-- Create listener roles
CREATE ROLE listener_free  WITH LOGIN PASSWORD 'free123' NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE listener_premium WITH LOGIN PASSWORD 'premium456' NOSUPERUSER NOCREATEDB NOCREATEROLE;

-- Grants (only read access – no insert/update)
GRANT CONNECT ON DATABASE appformusic TO listener_free, listener_premium;
GRANT USAGE ON SCHEMA public TO listener_free, listener_premium;
GRANT SELECT ON songs TO listener_free, listener_premium;

-- RLS policy for free listeners – only non-premium songs
CREATE POLICY listener_free_policy ON songs
    FOR SELECT
    USING (
        current_user = 'listener_free'
        AND is_premium = FALSE
    );

-- RLS policy for premium listeners – all songs
CREATE POLICY listener_premium_policy ON songs
    FOR SELECT
    USING (
        current_user = 'listener_premium'
    );

-- Simple function just for listeners (shows count per genre – no averages)
CREATE OR REPLACE FUNCTION listener_genre_counts()
RETURNS TABLE (
    genre_name VARCHAR,
    song_count BIGINT
) LANGUAGE sql SECURITY DEFINER AS $$
    SELECT genre, COUNT(*)
    FROM songs
    WHERE added_by = current_user   -- actually not used, but keeps consistent style
       OR current_user IN ('listener_free', 'listener_premium')
    GROUP BY genre
    ORDER BY song_count DESC;
$$;
select *from songs
