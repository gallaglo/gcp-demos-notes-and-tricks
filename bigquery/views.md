# BigQuery Views

This demo showcases two types of BigQuery views:

1. **Logical View**: A virtual table defined by a SQL query (no physical storage)
2. **Materialized View**: Physically stores query results for improved performance

---

## Prerequisites

- Access to a BigQuery project
- Basic understanding of SQL
- Replace `your-project` and `your-dataset` with your actual project and dataset IDs

---

## Logical Views

### What is a Logical View?

A [logical view](https://cloud.google.com/bigquery/docs/views-intro) is a virtual table defined by a SQL query. It doesn't store data physically - the query is executed every time the view is accessed.

### When to Use

- Simple transformations
- Always need fresh data
- Low query frequency
- No storage budget for materialized data

### Example: Trip Statistics View

```sql
CREATE OR REPLACE VIEW `your-project.your-dataset.trip_statistics_view` AS
SELECT
  DATE(starttime) as trip_date,
  start_station_name,
  end_station_name,
  COUNT(*) as trip_count,
  ROUND(AVG(tripduration) / 60, 2) as avg_duration_minutes,
  COUNT(DISTINCT bikeid) as unique_bikes_used
FROM
  `bigquery-public-data.new_york_citibike.citibike_trips`
WHERE
  starttime >= '2017-01-01'
  AND tripduration IS NOT NULL
  AND tripduration > 60  -- Filter out very short trips (< 1 minute)
GROUP BY
  trip_date,
  start_station_name,
  end_station_name;
```

### Querying the Logical View

```sql
SELECT * 
FROM `your-project.your-dataset.trip_statistics_view`
WHERE trip_date = '2017-07-04'
ORDER BY trip_count DESC
LIMIT 10;
```

---

## Materialized Views

### What is a Materialized View?

A [materialized view](https://cloud.google.com/bigquery/docs/materialized-views-intro) physically stores the query results and periodically refreshes them. It provides significantly better query performance for expensive aggregations.

### When to Use

- Complex aggregations
- Frequent queries on the same data
- Acceptable data latency (periodic refresh)
- Query performance is critical

### Important Restrictions

- ❌ No `COUNT(DISTINCT)` - use approximate functions or calculate at query time
- ❌ No scalar transformations in SELECT (`ROUND()`, division, etc.)
- ❌ Must output **raw aggregation results**
- ❌ Cannot reference tables from other projects/organizations

### Setup: Copy Data to Your Project

Since materialized views must be in the same project as source tables, first copy the data:

```sql
-- Step 1: Copy data to your project (one-time setup)
CREATE OR REPLACE TABLE `your-project.your-dataset.citibike_trips` AS
SELECT *
FROM `bigquery-public-data.new_york_citibike.citibike_trips`
WHERE starttime >= '2017-01-01'  -- Limit data for demo purposes
  AND starttime < '2018-01-01';
```

### Example: Daily Station Metrics Materialized View

```sql
-- Step 2: Create the materialized view on YOUR table
CREATE MATERIALIZED VIEW `your-project.your-dataset.daily_station_metrics_mv` AS
SELECT
  DATE(starttime) as trip_date,
  start_station_name,
  start_station_id,
  start_station_latitude,
  start_station_longitude,
  COUNT(*) as total_trips_started,
  AVG(tripduration) as avg_trip_duration_seconds,  -- Store raw seconds
  MIN(tripduration) as min_trip_duration_seconds,
  MAX(tripduration) as max_trip_duration_seconds,
  SUM(CASE WHEN usertype = 'Subscriber' THEN 1 ELSE 0 END) as subscriber_trips,
  SUM(CASE WHEN usertype = 'Customer' THEN 1 ELSE 0 END) as customer_trips
FROM
  `your-project.your-dataset.citibike_trips`  -- Reference YOUR table
WHERE
  starttime IS NOT NULL
  AND tripduration > 0
GROUP BY
  trip_date,
  start_station_name,
  start_station_id,
  start_station_latitude,
  start_station_longitude;
```

### Querying the Materialized View

Apply transformations (like `ROUND()` and unit conversions) at **query time**:

```sql
SELECT
  trip_date,
  start_station_name,
  total_trips_started,
  ROUND(avg_trip_duration_seconds / 60, 2) as avg_trip_duration_minutes,  -- Transform here
  ROUND(subscriber_trips * 100.0 / total_trips_started, 1) as subscriber_percentage
FROM
  `your-project.your-dataset.daily_station_metrics_mv`
WHERE
  trip_date BETWEEN '2017-06-01' AND '2017-06-30'
  AND total_trips_started > 100
ORDER BY
  total_trips_started DESC
LIMIT 20;
```

### Manual Refresh (Optional)

Materialized views auto-refresh, but you can manually trigger a refresh:

```sql
CALL BQ.REFRESH_MATERIALIZED_VIEW('your-project.your-dataset.daily_station_metrics_mv');
```
