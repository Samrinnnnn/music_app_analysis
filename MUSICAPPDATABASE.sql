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

select *from songs;
