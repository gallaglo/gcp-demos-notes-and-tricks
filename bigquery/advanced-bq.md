# Enhanced Advanced BigQuery Demos

## 1. Wikipedia Pageviews Analysis: Metadata, Time Series & Visualization

### Part 1: Exploring Dataset Metadata with INFORMATION_SCHEMA

```sql
-- Use INFORMATION_SCHEMA and ROLLUP to compute dataset statistics
SELECT
  table_id,
  ROUND(SUM(size_bytes)/POW(10,12),2) AS size_tb,
  ROUND(SUM(row_count)/POW(10,9),2) AS billion_rows,
  COUNT(DISTINCT partition_id) AS partition_count,
  MIN(creation_time) AS oldest_partition_date,
  MAX(creation_time) AS newest_partition_date
FROM
  `bigquery-public-data.wikipedia.__TABLES__`
WHERE 
  table_id LIKE 'pageviews_201%'
GROUP BY 
  ROLLUP(table_id)
ORDER BY 
  table_id;
```

**Key Points to Highlight:**

- INFORMATION_SCHEMA provides metadata about tables without scanning the data itself
- ROLLUP creates multiple levels of aggregation (per table + grand total in final row)
- This query is completely FREE to run (no bytes processed) since it only queries metadata
- Note the size_tb and billion_rows columns showing the massive scale of the dataset

### Part 2: Time Series Analysis with Wildcard Tables

```sql
SELECT
  title,
  EXTRACT(year FROM datehour) AS year,
  EXTRACT(month FROM datehour) AS month,
  ROUND(SUM(views)/1000, 1) AS views_thousands
FROM
  `bigquery-public-data.wikipedia.pageviews_201*`
WHERE
  -- Show how wildcard tables + filtering reduces bytes processed
  _TABLE_SUFFIX BETWEEN "6" AND "8" AND
  -- Show partitioning benefits for time filtering
  datehour BETWEEN TIMESTAMP("2016-01-01") AND TIMESTAMP("2018-12-31")
  AND wiki = "en"
  AND title IN ('BigQuery', 'Hadoop', 'Spark', 'Snowflake')
GROUP BY
  title, year, month
ORDER BY
  year, month, views_thousands DESC;
```

**Interactive Demonstration:**

1. **Before running:** Explain wildcards (_TABLE_SUFFIX) and highlight how they help process only specific tables
2. **After running:** Click "Job Information" to show actual bytes processed vs. total dataset size
3. **Result exploration:**  
   - Show the Chart preview (line chart with year_month as dimension)
   - Discuss patterns: when did BigQuery become more popular than Hadoop?
   - Change to column chart to compare technologies side-by-side

### Part 3: Advanced Time-Based Analytics  

```sql
WITH daily_views AS (
  SELECT
    title,
    EXTRACT(DAYOFWEEK FROM datehour) AS day_of_week,
    EXTRACT(HOUR FROM datehour) AS hour_of_day,
    SUM(views) AS views
  FROM
    `bigquery-public-data.wikipedia.pageviews_2017*`
  WHERE
    wiki = 'en'
    AND title IN ('Machine_learning', 'Artificial_intelligence', 'Data_science', 'Big_data')
  GROUP BY
    title, day_of_week, hour_of_day
),
total_by_title AS (
  SELECT
    title,
    SUM(views) AS total_views
  FROM
    daily_views
  GROUP BY
    title
)
SELECT
  d.title,
  CASE 
    WHEN day_of_week = 1 THEN 'Sunday'
    WHEN day_of_week = 2 THEN 'Monday'
    WHEN day_of_week = 3 THEN 'Tuesday'
    WHEN day_of_week = 4 THEN 'Wednesday'
    WHEN day_of_week = 5 THEN 'Thursday'
    WHEN day_of_week = 6 THEN 'Friday'
    WHEN day_of_week = 7 THEN 'Saturday'
  END AS weekday,
  hour_of_day,
  d.views,
  ROUND(d.views / t.total_views * 100, 2) AS percentage_of_total
FROM
  daily_views d
JOIN
  total_by_title t
ON
  d.title = t.title
ORDER BY
  d.title, day_of_week, hour_of_day;
```

**Discussion Points:**

- Show both table and visualization (heatmap) to identify patterns
- Highlight when ML/AI topics are most frequently viewed (weekdays vs. weekends)
- Point out how BigQuery can handle complex time-based analysis with CTEs and joins

## 2. San Francisco Bikeshare Analysis: Location Intelligence & Pattern Detection

### Part 1: Basic Station Analysis with Window Functions

```sql
WITH station_metrics AS (
  SELECT
    start_station_name,
    COUNT(trip_id) AS num_trips,
    COUNT(DISTINCT subscriber_type) AS rider_types,
    AVG(duration_sec) AS avg_duration_sec
  FROM
    `bigquery-public-data.san_francisco_bikeshare.bikeshare_trips`
  WHERE 
    start_date > '2017-12-31 00:00:00 UTC'
  GROUP BY
    start_station_name
)
SELECT
  start_station_name,
  num_trips,
  avg_duration_sec,
  -- Calculate percentile ranks
  ROUND(PERCENT_RANK() OVER (ORDER BY num_trips), 2) AS trip_volume_percentile,
  ROUND(PERCENT_RANK() OVER (ORDER BY avg_duration_sec), 2) AS duration_percentile
FROM
  station_metrics
ORDER BY
  num_trips DESC
LIMIT 10;
```

**Key Features to Highlight:**

- Window functions (PERCENT_RANK) to analyze rankings without additional queries
- Automatic Chart preview to visualize station popularity
- Ability to quickly identify outliers in the data

### Part 2: Time Pattern Analysis

```sql
SELECT
  EXTRACT(DAYOFWEEK FROM start_date) AS day_of_week,
  EXTRACT(HOUR FROM start_date) AS hour_of_day,
  subscriber_type,
  COUNT(*) AS trip_count,
  AVG(duration_sec) AS avg_duration
FROM
  `bigquery-public-data.san_francisco_bikeshare.bikeshare_trips`
WHERE
  start_date BETWEEN '2018-01-01' AND '2018-12-31'
GROUP BY
  day_of_week, hour_of_day, subscriber_type
ORDER BY
  subscriber_type, day_of_week, hour_of_day;
```

**Visualization Focus:**

- Use Chart preview to create a heatmap (day_of_week vs hour_of_day)
- Identify commute patterns (weekday rush hours)
- Compare trip patterns between subscriber types

### Part 3: Route Analysis with Self-Join and Geographic Functions

```sql
WITH popular_routes AS (
  SELECT
    t.start_station_name,
    t.end_station_name,
    COUNT(*) AS trip_count,
    AVG(t.duration_sec) AS avg_duration_sec,
    -- Calculate distance using station coordinates
    ST_DISTANCE(
      ST_GEOGPOINT(s1.long, s1.lat),
      ST_GEOGPOINT(s2.long, s2.lat)
    ) AS distance_meters
  FROM
    `bigquery-public-data.san_francisco_bikeshare.bikeshare_trips` t
  JOIN
    `bigquery-public-data.san_francisco_bikeshare.bikeshare_stations` s1
  ON
    t.start_station_id = s1.station_id
  JOIN
    `bigquery-public-data.san_francisco_bikeshare.bikeshare_stations` s2
  ON
    t.end_station_id = s2.station_id
  WHERE
    t.start_date > '2017-01-01'
  GROUP BY
    t.start_station_name, t.end_station_name, s1.long, s1.lat, s2.long, s2.lat
  HAVING
    COUNT(*) > 100
)
SELECT
  start_station_name,
  end_station_name,
  trip_count,
  ROUND(distance_meters, 0) AS distance_meters,
  ROUND(avg_duration_sec, 0) AS avg_duration_sec,
  ROUND(avg_duration_sec / (distance_meters/1000), 1) AS seconds_per_km
FROM
  popular_routes
ORDER BY
  trip_count DESC
LIMIT 20;
```

**Key Points to Emphasize:**

- Geospatial functions (ST_GEOGPOINT, ST_DISTANCE) for calculating real-world distances
- Multi-table JOIN operations for enriching trip data with station data
- Derivation of performance metrics (seconds_per_km) for identifying interesting patterns

## 3. Bonus: Performance Optimization Techniques Demo

```sql
-- Run this query first to show performance without optimization
SELECT
  wiki,
  title,
  SUM(views) AS total_views
FROM
  `bigquery-public-data.wikipedia.pageviews_2017*`
WHERE
  datehour BETWEEN TIMESTAMP("2017-01-01") AND TIMESTAMP("2017-01-31")
GROUP BY
  wiki, title
ORDER BY
  total_views DESC
LIMIT 100;

-- Then run this optimized version
SELECT
  wiki,
  title,
  SUM(views) AS total_views
FROM
  `bigquery-public-data.wikipedia.pageviews_2017*`
WHERE
  _TABLE_SUFFIX BETWEEN "01" AND "03"
  AND datehour BETWEEN TIMESTAMP("2017-01-01") AND TIMESTAMP("2017-01-31")
  -- Add filter that uses clustering keys
  AND wiki IN ('en', 'fr', 'de', 'ja', 'es')
GROUP BY
  wiki, title
ORDER BY
  total_views DESC
LIMIT 100;
```

**Interactive Discussion:**

1. Compare execution plans between the two queries
2. Highlight slot usage and processing stage differences
3. Discuss the three key optimization techniques used:
   - Wildcard table filtering with _TABLE_SUFFIX
   - Time-based filtering with datehour
   - Leveraging clustering keys (wiki column)
4. Show cost difference between the two approaches
