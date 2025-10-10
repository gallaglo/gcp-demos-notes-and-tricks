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

---

## Authorized Views

### What is an Authorized View?

An [authorized view](https://cloud.google.com/bigquery/docs/authorized-views) allows you to share query results with users or service accounts without giving them access to the underlying tables. The view is "authorized" to access source data on behalf of users who only have access to the view.

### When to Use

- Restrict access to sensitive columns or rows
- Share aggregated data without exposing raw data
- Implement row-level security

### Step 1: Create Datasets

```sql
-- Dataset for source data (restrictive permissions)
CREATE SCHEMA IF NOT EXISTS `restricted_data`
OPTIONS(
  description="Contains sensitive raw data"
);

-- Dataset for authorized views (permissive for service accounts)
CREATE SCHEMA IF NOT EXISTS `shared_views`
OPTIONS(
  description="Contains views authorized to access restricted data"
);
```

### Step 2: Copy Source Data

```sql
-- Copy data to the restricted dataset
CREATE OR REPLACE TABLE `restricted_data.citibike_trips` AS
SELECT *
FROM `bigquery-public-data.new_york_citibike.citibike_trips`
WHERE starttime >= '2017-01-01'
  AND starttime < '2018-01-01';
```

### Step 3: Create the Authorized View

```sql
-- Create a view that filters and aggregates data
CREATE OR REPLACE VIEW `shared_views.station_summary_view`
OPTIONS(
  description="Aggregated station metrics - accessible to authorized service accounts",
  labels=[("team", "analytics"), ("data_level", "aggregated")],
  expiration_timestamp=TIMESTAMP_ADD(CURRENT_TIMESTAMP(), INTERVAL 180 DAY)
)
AS
SELECT
  start_station_name,
  start_station_id,
  COUNT(*) as total_trips,
  ROUND(AVG(tripduration) / 60, 2) as avg_duration_minutes,
  ROUND(SUM(CASE WHEN usertype = 'Subscriber' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as subscriber_percentage
FROM
  `restricted_data.citibike_trips`
WHERE
  tripduration > 60  -- Filter out trips under 1 minute
GROUP BY
  start_station_name,
  start_station_id;
```

### Step 4: Authorize the View

In the BigQuery Console or using the `bq` command:

```bash
# Authorize the view to access the source dataset
bq update --source_dataset=your-project:restricted_data \
  --view $(gcloud config get-value project):shared_views.station_summary_view
```

Or use the Console:
1. Go to the **restricted_data** dataset
2. Click **SHARING** → **Authorized Views**
3. Click **ADD AUTHORIZED VIEW**
4. Select `your-project.shared_views.station_summary_view`

### Step 5: Grant Service Account Access

```bash
# Get your project's default compute service account
# Format: PROJECT_NUMBER-compute@developer.gserviceaccount.com
# You can find the project number in the console or with:
gcloud projects describe your-project --format="value(projectNumber)"

# Grant the service account access to the shared_views dataset ONLY
# (NOT the restricted_data dataset)
bq add-iam-policy-binding \
  --member="serviceAccount:$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")-compute@developer.gserviceaccount.com" \
  --role="roles/bigquery.dataViewer" \
  $(gcloud config get-value project):shared_views
```

### Step 6: Test from a Compute Engine VM

SSH into a VM that uses the default compute service account:

```bash
# SSH into your VM
gcloud compute ssh your-vm-name --zone=your-zone

# Test querying the authorized view (should work)
bq query --use_legacy_sql=false \
'SELECT * 
FROM `your-project.shared_views.station_summary_view`
WHERE total_trips > 1000
ORDER BY total_trips DESC
LIMIT 10'

# Try querying the source table (should fail with permission denied)
bq query --use_legacy_sql=false \
'SELECT COUNT(*) 
FROM `your-project.restricted_data.citibike_trips`'
```

### Expected Results

- ✅ **View query succeeds**: The service account can access aggregated data through the view
- ❌ **Table query fails**: The service account cannot access the underlying restricted table
- 🔒 **Security achieved**: Raw data remains protected while allowing controlled access

### Additional Options

**Row-Level Security Example:**

```sql
-- Filter data based on a specific condition
CREATE OR REPLACE VIEW `shared_views.recent_trips_view` AS
SELECT
  DATE(starttime) as trip_date,
  start_station_name,
  end_station_name,
  tripduration
FROM
  `restricted_data.citibike_trips`
WHERE
  starttime >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY);  -- Last 7 days only
```

**Column-Level Security Example:**

```sql
-- Exclude sensitive columns (e.g., precise location data)
CREATE OR REPLACE VIEW `shared_views.trips_no_location_view` AS
SELECT
  starttime,
  stoptime,
  tripduration,
  start_station_name,  -- Keep names
  end_station_name,
  -- Exclude: start_station_latitude, start_station_longitude, etc.
  usertype,
  birth_year,
  gender
FROM
  `restricted_data.citibike_trips`;
```
