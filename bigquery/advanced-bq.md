# Advanced BigQuery Demo

Wikipedia Pageviews demo that shows off INFORMATION_SCHEMA, ROLLUP, and the new Chart preview.

```sql
-- Use INFORMATION_SCHEMA and ROLLUP to compute total rows and bytes
-- in wikipedia_pageviews tables
SELECT
  table_id,
  -- Convert bytes to GB.
  sum(ROUND(size_bytes/pow(10,12),2)) as size_tb,
  sum(ROUND(row_count/pow(10,9),2)) as billion_rows
FROM
  -- Replace baseball with a different dataset:
  `bigquery-public-data.wikipedia.__TABLES__`
WHERE table_id LIKE 'pageviews_201%'
GROUP BY ROLLUP(table_id)
ORDER BY table_id;
-- This query is free because it's against bigquery-public-data
SELECT
  title,
  extract(year from datehour) as year_viewed,
  SUM(views) AS sumViews
FROM
  `bigquery-public-data.wikipedia.pageviews_201*`
WHERE
  -- Change the number to show impact on amount ingested
  _TABLE_SUFFIX >= "5" AND
  -- Change date to show impact of partitioning
  TIMESTAMP_TRUNC(datehour, DAY) >= TIMESTAMP("2010-01-01")
  AND wiki = "en"
  AND title = 'BigQuery'
GROUP BY
  wiki,
  title,
  year_viewed
ORDER BY
  sumViews DESC
LIMIT
  10
-- After running the query:
-- Go to Job Information to show actual bytes processed due to clustering (only 257 GB)
-- Show the results using the new Chart (Preview). Change the dimension dropdown to year_viewed.
```
