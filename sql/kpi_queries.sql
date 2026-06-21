/* ============================================================
   AI SALES ANALYTICS — FINAL FULL KPI SQL SUITE
   ------------------------------------------------------------
   Database    : ai_sales_analytics
   Main Table  : sales_orders
   Purpose     : Executive-level business intelligence,
                 KPI automation, dashboard metrics,
                 portfolio-grade analytics
   ============================================================ */

USE ai_sales_analytics;
SELECT date, STR_TO_DATE(date, '%m-%d-%y') AS parsed FROM sales_orders LIMIT 5;

/* ============================================================
   1. TOTAL REVENUE
   ============================================================ */
SELECT
    ROUND(SUM(amount), 2) AS total_revenue
FROM sales_orders;


/* ============================================================
   2. MONTHLY REVENUE TREND
   ============================================================ */
SELECT
    DATE_FORMAT(date, '%Y-%m') AS order_month,
    ROUND(SUM(amount), 2) AS monthly_revenue
FROM sales_orders
GROUP BY DATE_FORMAT(date, '%Y-%m')
ORDER BY order_month ASC;
	

/* ============================================================
   3. REVENUE BY PRODUCT CATEGORY
   ============================================================ */
SELECT
    category,
    COUNT(DISTINCT order_id) AS total_orders,
    SUM(qty) AS units_sold,
    ROUND(SUM(amount), 2) AS total_revenue,
    ROUND(
        SUM(amount) * 100.0 /
        SUM(SUM(amount)) OVER (),
        2
    ) AS revenue_share_pct
FROM sales_orders
GROUP BY category
ORDER BY total_revenue DESC;


/* ============================================================
   4. TOP 10 PRODUCTS BY REVENUE
   ============================================================ */
SELECT
    sku,
    SUM(qty) AS units_sold,
    ROUND(SUM(amount), 2) AS total_revenue,
    ROUND(
        SUM(amount) / NULLIF(SUM(qty), 0),
        2
    ) AS avg_unit_price
FROM sales_orders
GROUP BY sku
ORDER BY total_revenue DESC
LIMIT 10;


/* ============================================================
   5. REVENUE BY STATE
   ============================================================ */
SELECT
    shipstate AS state,
    COUNT(DISTINCT order_id) AS total_orders,
    ROUND(SUM(amount), 2) AS total_revenue,
    ROUND(AVG(amount), 2) AS avg_order_value,
    ROUND(
        SUM(amount) * 100.0 /
        SUM(SUM(amount)) OVER (),
        2
    ) AS revenue_share_pct
FROM sales_orders
GROUP BY shipstate
ORDER BY total_revenue DESC;


/* ============================================================
   6. TOP 10 CITIES BY REVENUE
   ============================================================ */
SELECT
    shipcity AS city,
    COUNT(DISTINCT order_id) AS total_orders,
    ROUND(SUM(amount), 2) AS total_revenue
FROM sales_orders
GROUP BY shipcity
ORDER BY total_revenue DESC
LIMIT 10;


/* ============================================================
   7. FULFILMENT PERFORMANCE
   ============================================================ */
SELECT
    fulfilment AS fulfillment_channel,
    COUNT(DISTINCT order_id) AS total_orders,
    ROUND(SUM(amount), 2) AS total_revenue,
    ROUND(AVG(amount), 2) AS avg_order_value,
    ROUND(
        COUNT(*) * 100.0 /
        SUM(COUNT(*)) OVER (),
        2
    ) AS order_share_pct
FROM sales_orders
GROUP BY fulfilment
ORDER BY total_orders DESC;


/* ============================================================
   8. SALES CHANNEL PERFORMANCE
   ============================================================ */
SELECT
    sales_channel,
    COUNT(DISTINCT order_id) AS total_orders,
    ROUND(SUM(amount), 2) AS total_revenue,
    ROUND(AVG(amount), 2) AS avg_order_value
FROM sales_orders
GROUP BY sales_channel
ORDER BY total_revenue DESC;


/* ============================================================
   9. ORDER STATUS / CANCELLATION ANALYSIS
   ============================================================ */
SELECT
    status,
    COUNT(*) AS total_orders,
    ROUND(SUM(amount), 2) AS revenue,
    ROUND(
        COUNT(*) * 100.0 /
        SUM(COUNT(*)) OVER (),
        2
    ) AS order_share_pct
FROM sales_orders
GROUP BY status
ORDER BY total_orders DESC;


/* ============================================================
   10. COURIER PERFORMANCE
   ============================================================ */
SELECT
    courier_status,
    COUNT(*) AS total_orders,
    ROUND(SUM(amount), 2) AS total_revenue
FROM sales_orders
GROUP BY courier_status
ORDER BY total_orders DESC;


/* ============================================================
   11. B2B vs B2C CUSTOMER SEGMENT ANALYSIS
   ============================================================ */
SELECT
    CASE
        WHEN b2b = 1 THEN 'B2B (Business)'
        ELSE 'B2C (Consumer)'
    END AS customer_segment,
    COUNT(DISTINCT order_id) AS total_orders,
    ROUND(SUM(amount), 2) AS total_revenue,
    ROUND(AVG(amount), 2) AS avg_order_value,
    ROUND(
        SUM(amount) * 100.0 /
        SUM(SUM(amount)) OVER (),
        2
    ) AS revenue_share_pct
FROM sales_orders
GROUP BY b2b
ORDER BY total_revenue DESC;


/* ============================================================
   12. AVERAGE DAILY REVENUE
   ============================================================ */
SELECT
    ROUND(AVG(daily_revenue), 2) AS avg_daily_revenue
FROM (
    SELECT
        STR_TO_DATE(date, '%m-%d-%y') AS order_date,
        SUM(amount) AS daily_revenue
    FROM sales_orders
    GROUP BY order_date
) daily_sales;


/* ============================================================
   13. INVENTORY DEMAND BY CATEGORY & SIZE
   ============================================================ */
SELECT
    category,
    size,
    SUM(qty) AS total_units_sold,
    ROUND(SUM(amount), 2) AS total_revenue
FROM sales_orders
GROUP BY category, size
ORDER BY total_units_sold DESC;


/* ============================================================
   14. PROFITABILITY PROXY (AVG REVENUE PER ORDER)
   ============================================================ */
SELECT
    ROUND(
        SUM(amount) / COUNT(DISTINCT order_id),
        2
    ) AS avg_revenue_per_order
FROM sales_orders;


/* ============================================================
   15. SHIP SERVICE LEVEL PERFORMANCE
   ============================================================ */
SELECT
    shipservicelevel,
    COUNT(DISTINCT order_id) AS total_orders,
    ROUND(SUM(amount), 2) AS total_revenue,
    ROUND(AVG(amount), 2) AS avg_order_value
FROM sales_orders
GROUP BY shipservicelevel
ORDER BY total_orders DESC;


/* ============================================================
   16. CATEGORY + STATE PERFORMANCE
   ============================================================ */
SELECT
    shipstate,
    category,
    COUNT(DISTINCT order_id) AS total_orders,
    SUM(qty) AS units_sold,
    ROUND(SUM(amount), 2) AS total_revenue
FROM sales_orders
GROUP BY shipstate, category
ORDER BY total_revenue DESC;


/* ============================================================
   17. TOP STATES BY ORDER CANCELLATION
   ============================================================ */
SELECT
    shipstate,
    COUNT(*) AS cancelled_orders
FROM sales_orders
WHERE LOWER(status) LIKE '%cancel%'
GROUP BY shipstate
ORDER BY cancelled_orders DESC;


/* ============================================================
   18. EXECUTIVE SUMMARY KPI DASHBOARD
   ============================================================ */
SELECT
    COUNT(DISTINCT order_id) AS total_orders,
    SUM(qty) AS total_units_sold,
    ROUND(SUM(amount), 2) AS total_revenue,
    ROUND(AVG(amount), 2) AS avg_order_value,
    COUNT(DISTINCT shipstate) AS active_states,
    COUNT(DISTINCT shipcity) AS active_cities,
    COUNT(DISTINCT category) AS product_categories,
    COUNT(DISTINCT sku) AS unique_products
FROM sales_orders;

-- Return / Refund Analysis
SELECT
    status,
    COUNT(*) AS returned_orders,
    ROUND(SUM(amount), 2) AS affected_revenue
FROM sales_orders
WHERE LOWER(status) LIKE '%return%'
   OR LOWER(status) LIKE '%refund%'
GROUP BY status;

-- Revenue Seasonality
SELECT
    MONTH(STR_TO_DATE(date, '%m-%d-%y')) AS month_num,
    ROUND(SUM(amount), 2) AS revenue
FROM sales_orders
GROUP BY month_num
ORDER BY month_num;

-- Customer Concentration Risk
SELECT
    shipstate,
    ROUND(SUM(amount), 2) AS revenue,
    ROUND(
        SUM(amount) * 100.0 /
        SUM(SUM(amount)) OVER (),
        2
    ) AS revenue_share_pct
FROM sales_orders
GROUP BY shipstate
ORDER BY revenue DESC;