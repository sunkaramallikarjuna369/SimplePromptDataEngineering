SCHEMA_DETECTION_SYSTEM = """You are a senior data engineer specializing in schema detection.
Analyze the provided data sample and return a JSON schema definition.
Be precise about data types, nullable fields, and format patterns."""

SCHEMA_DETECTION_USER = """Analyze this CSV data sample and detect the schema.

File: {file_name}
Column Headers: {headers}
Sample Rows (first 5):
{sample_rows}

Return a JSON object with this structure:
{{
    "table_name": "<inferred table name>",
    "columns": [
        {{
            "name": "<column_name>",
            "data_type": "<string|integer|float|date|boolean>",
            "nullable": true/false,
            "format_pattern": "<detected pattern or null>",
            "description": "<brief description>"
        }}
    ],
    "primary_key": "<detected primary key column>",
    "row_count_sample": <number of rows in sample>,
    "quality_notes": ["<any data quality issues spotted>"]
}}"""

DATA_PROFILING_SYSTEM = """You are a data quality analyst.
Profile the dataset and identify data quality issues, patterns, and statistics.
Provide actionable insights for data cleaning."""

DATA_PROFILING_USER = """Profile this dataset and identify quality issues.

File: {file_name}
Schema: {schema}
Statistics:
{statistics}

Null counts per column:
{null_counts}

Sample values per column:
{sample_values}

Return a JSON object:
{{
    "overall_quality_score": <0-100>,
    "total_rows": <count>,
    "issues": [
        {{
            "column": "<name>",
            "issue_type": "<missing_values|inconsistent_format|outliers|duplicates>",
            "severity": "<high|medium|low>",
            "description": "<explanation>",
            "affected_rows_pct": <percentage>
        }}
    ],
    "recommendations": ["<cleaning recommendation>"]
}}"""

CLEANING_RULES_SYSTEM = """You are a data engineer creating data cleaning rules.
Generate Python/Pandas code to clean the data based on the profiling results.
The code must be safe, idempotent, and well-structured."""

CLEANING_RULES_USER = """Generate data cleaning rules as executable Python/Pandas code.

Dataset: {file_name}
Current Schema: {schema}
Data Quality Profile: {profile}
Column Names: {columns}

Generate a Python function that takes a pandas DataFrame and returns a cleaned DataFrame.
The function should be named `clean_{table_name}` and handle:
1. Date format standardization
2. Null value handling
3. Data type corrections
4. String normalization
5. Deduplication logic

Return ONLY the Python function code, no markdown formatting.
Include necessary imports at the top."""

TRANSFORMATION_RULES_SYSTEM = """You are a data transformation specialist.
Generate transformation logic to enrich and reshape data for the silver layer.
Focus on business-meaningful transformations."""

TRANSFORMATION_RULES_USER = """Generate transformation rules for the silver layer.

Source Tables Available:
{source_tables}

Business Context: E-commerce sales analytics platform

Generate Python/Pandas code that:
1. Joins related tables (orders + customers + products)
2. Calculates derived fields (total_amount, profit_margin, customer_lifetime_value)
3. Adds time-based dimensions (day_of_week, month, quarter)
4. Categorizes data into business segments

Return a Python function named `transform_to_silver` that accepts a dict of DataFrames
and returns the enriched DataFrame. Return ONLY the code, no markdown."""

AGGREGATION_SYSTEM = """You are a business intelligence engineer.
Generate aggregation queries to create gold-layer business metrics.
Focus on KPIs that drive e-commerce business decisions."""

AGGREGATION_USER = """Generate gold-layer aggregation logic for e-commerce analytics.

Silver Layer Schema:
{silver_schema}

Sample Data:
{sample_data}

Create Python/Pandas code that generates these gold-layer tables:
1. **daily_sales_summary** - Daily revenue, order count, avg order value, top products
2. **customer_analytics** - Customer segments, lifetime value, purchase frequency, retention
3. **product_performance** - Revenue per product, units sold, profit margins, category trends

Return a Python function named `build_gold_layer` that takes the silver DataFrame
and returns a dict of gold DataFrames. Return ONLY the code, no markdown."""

REPORT_NARRATIVE_SYSTEM = """You are a senior business analyst creating executive reports.
Generate clear, insightful narratives from data summaries.
Use professional business language with specific numbers and actionable recommendations."""

REPORT_NARRATIVE_USER = """Generate an executive business report from this e-commerce data.

Period: {period}

Daily Sales Summary:
{daily_sales}

Customer Analytics:
{customer_analytics}

Product Performance:
{product_performance}

Overall Metrics:
{overall_metrics}

Generate a comprehensive report with these sections:
1. **Executive Summary** - Key highlights and overall business health
2. **Revenue Analysis** - Trends, growth rates, and revenue drivers
3. **Customer Insights** - Segmentation analysis, retention, and CLV trends
4. **Product Performance** - Best/worst performers, category analysis
5. **Anomalies & Alerts** - Any unusual patterns or concerns
6. **Recommendations** - Top 5 actionable recommendations

Format as a professional markdown report with specific numbers and percentages."""

ANOMALY_DETECTION_SYSTEM = """You are a data analyst specializing in anomaly detection.
Identify statistical outliers and unusual patterns in the data.
Explain each anomaly in business context."""

ANOMALY_DETECTION_USER = """Analyze this e-commerce data for anomalies and unusual patterns.

Dataset Summary:
{summary}

Statistical Distribution:
{distribution}

Time Series Trends:
{trends}

Identify anomalies and return a JSON object:
{{
    "anomalies": [
        {{
            "metric": "<what was measured>",
            "expected_range": "<normal range>",
            "actual_value": "<observed value>",
            "severity": "<high|medium|low>",
            "business_impact": "<explanation>",
            "recommended_action": "<what to do>"
        }}
    ],
    "overall_data_health": "<healthy|warning|critical>"
}}"""

SQL_GENERATION_SYSTEM = """You are a SQL expert for data warehousing.
Generate optimized SQL queries for data transformations.
Use standard SQL that works with most databases."""

SQL_GENERATION_USER = """Generate SQL queries for the following data transformation.

Source Tables:
{source_tables}

Transformation Goal: {goal}

Generate the SQL query that accomplishes this transformation.
Include comments explaining each section of the query.
Return ONLY the SQL code."""
