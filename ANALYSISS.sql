--SONG ANALYSIS
--1.Total songs per tenant
SELECT count(s.id) as total_songs, t.name as tenant_name
FROM songs s
JOIN tenants t ON s.tenant_id=t.tenant_id
GROUP BY tenant_id
ORDER BY total_songs DESC;

SELECT *FROM songs;

--2.Genre popularity per tenant
SELECT count(genre) as genre_popularity, tenant_id
FROM songs
GROUP BY tenant_id
ORDER BY genre_popularity;

--3.Premium vs Free song ratio
SELECT *FROM songs;
SELECT
SUM(CASE WHEN is_premium='true' THEN 1 ELSE 0 END)  AS premium_songs,
SUM(CASE WHEN is_premium='false' THEN 1 ELSE 0 END)  AS free_songs
FROM SONGS;

--4.Average rating per tenants
SELECT avg(rating) as average_rating, tenant_id
FROM songs 
GROUP BY tenant_id;

--5.Top rated songs
SELECT rating, title
FROM SONGS
ORDER BY rating DESC
LIMIT 10;
--LISTENER ANALYSIS
--6.Total listeners per tenant







