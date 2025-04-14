# BigQuery Demo: Exploring Wikipedia Data at Scale

## Setup

1. Open BigQuery: [https://console.cloud.google.com/bigquery](https://console.cloud.google.com/bigquery)
2. Explore the interface: Note the navigation panel, query editor, and results pane
3. Point out that BigQuery is a serverless data warehouse - no infrastructure to manage!

## 1: Query 10 Billion Rows in Seconds

Let's start with a query that demonstrates BigQuery's raw processing power:

```sql
SELECT
  language,
  title,
  SUM(views) AS views
FROM
  `cloud-training-demos.wikipedia_benchmark.Wiki10B`
WHERE
  title LIKE '%Google%'
GROUP BY
  language,
  title
ORDER BY
  views DESC;
```

- **Data Volume**: Click the validator to show this query will process ~500 GB of data
- **Performance**: Run the query and emphasize it takes only ~10 seconds
- **Scale**: Click the Execution Details to show it processed 10 billion input rows

## 2. Query Caching and Performance

### Cached Query Demonstration

1. Re-run the original query
2. Point out the dramatically faster execution time (~1-2 seconds)
3. Explain: "BigQuery automatically caches query results for 24 hours if the underlying data doesn't change"

### Profiling Query Execution

Click on the Execution Details tab and highlight:

- **Slot usage**: How many parallel processing units were used
- **Stages**: How BigQuery broke down the execution plan
- **Data shuffle**: How data moved between processing stages

## 3. Scaling Up: 100 Billion Rows

Let's push the limits with an even larger dataset:

```sql
SELECT
  language,
  title,
  SUM(views) AS views
FROM
  `cloud-training-demos.wikipedia_benchmark.Wiki100B`
WHERE
  title LIKE '%Google%'
GROUP BY
  language,
  title
ORDER BY
  views DESC;
```

- BigQuery seamlessly scales to handle 10× more data
- Execution time increases less than linearly with data size

## 4. Advanced Analytics with SQL

Let's showcase BigQuery's analytical capabilities:

```sql
WITH PageStats AS (
  SELECT
    language,
    CASE
      WHEN title LIKE '%Google%' THEN 'Google'
      WHEN title LIKE '%Microsoft%' THEN 'Microsoft'
      WHEN title LIKE '%Amazon%' THEN 'Amazon'
      WHEN title LIKE '%Facebook%' OR title LIKE '%Meta%' THEN 'Meta'
      WHEN title LIKE '%Apple%' THEN 'Apple'
      ELSE 'Other Tech'
    END AS company,
    views
  FROM
    `cloud-training-demos.wikipedia_benchmark.Wiki10B`
  WHERE
    title LIKE '%Google%' OR title LIKE '%Microsoft%' OR 
    title LIKE '%Amazon%' OR title LIKE '%Facebook%' OR 
    title LIKE '%Meta%' OR title LIKE '%Apple%'
)
SELECT
  company,
  SUM(views) AS total_views,
  COUNT(DISTINCT language) AS languages,
  ROUND(SUM(views) / (SELECT SUM(views) FROM PageStats) * 100, 2) AS percentage
FROM
  PageStats
GROUP BY
  company
ORDER BY
  total_views DESC;
```

- **Common Table Expressions (CTEs)**: The WITH PageStats AS (...) syntax creates a temporary named result set that can be referenced in the main query, making complex queries more readable and maintainable.
- **CASE expressions**: The query uses a CASE statement to categorize data into different groups based on pattern matching, demonstrating how to transform and categorize data on-the-fly.
- **Pattern matching**: Multiple LIKE operators with wildcards (%) are used to find partial string matches in the title field.
- **Aggregation functions**:
  - SUM(views) to calculate total views for each company
  - COUNT(DISTINCT language) to count unique languages per company
- **Subqueries in SELECT clause**: The percentage calculation uses a subquery (SELECT SUM(views) FROM PageStats) inline within the outer query to compute the denominator for the percentage.
