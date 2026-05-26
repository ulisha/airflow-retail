CREATE SCHEMA IF NOT EXISTS dm;

DROP VIEW IF EXISTS
    dm.v_fx_risk_metrics,
    dm.v_sales_fx_monthly,
    dm.v_currency_rates_monthly,
    dm.v_dashboard_summary,
    dm.v_product_inventory_turnover,
    dm.v_abc_xyz_analysis,
    dm.v_store_monthly_heatmap,
    dm.v_retail_kpi_mart,
    dm.v_inventory_risks,
    dm.v_plan_fact_dashboard,
    dm.v_category_plan_fact_mart,
    dm.v_category_performance,
    dm.v_store_performance,
    dm.v_monthly_sales_kpi,
    dm.v_sales_enriched,
    dm.v_stores_dim,
    dm.v_products_dim;

DROP VIEW IF EXISTS dm.v_stores_dim;
DROP VIEW IF EXISTS dm.v_products_dim;

CREATE OR REPLACE VIEW dm.v_sales_enriched AS
SELECT
    s.sale_id,
    s.sale_date,
    s.sale_month,
    EXTRACT(YEAR FROM s.sale_date)::INTEGER AS sale_year,
    EXTRACT(QUARTER FROM s.sale_date)::INTEGER AS sale_quarter,
    EXTRACT(MONTH FROM s.sale_date)::INTEGER AS sale_month_num,
    EXTRACT(WEEK FROM s.sale_date)::INTEGER AS sale_week,
    EXTRACT(DOW FROM s.sale_date)::INTEGER AS day_of_week_num,
    CASE WHEN EXTRACT(DOW FROM s.sale_date)::INTEGER IN (0, 6) THEN 1 ELSE 0 END AS is_weekend,
    s.store_id,
    st.store_name,
    st.city,
    st.region,
    st.format AS store_format,
    st.store_area_sqm,
    st.employees_count,
    s.product_id,
    p.product_name,
    p.stock_code,
    s.category,
    p.subcategory,
    p.brand,
    p.supplier,
    p.uom,
    s.sales_channel,
    s.quantity,
    s.revenue,
    s.total_cost,
    s.profit,
    ROUND(s.profit / NULLIF(s.revenue, 0) * 100, 2) AS margin_pct,
    ROUND(s.revenue / NULLIF(s.quantity, 0), 2) AS avg_unit_revenue,
    ROUND(s.profit / NULLIF(s.quantity, 0), 2) AS profit_per_unit,
    ROUND(s.revenue / NULLIF(st.employees_count, 0), 2) AS revenue_per_employee,
    ROUND(s.revenue / NULLIF(st.store_area_sqm, 0), 2) AS revenue_per_sqm,
    s.updated_at
FROM dm.dm_sales s
LEFT JOIN dm.dm_stores st
    ON st.store_id = s.store_id
LEFT JOIN dm.dm_products p
    ON p.product_id = s.product_id;

CREATE OR REPLACE VIEW dm.v_monthly_sales_kpi AS
SELECT
    sale_month,
    sale_year,
    sale_month_num,
    SUM(revenue) AS revenue,
    SUM(total_cost) AS total_cost,
    SUM(profit) AS profit,
    SUM(quantity) AS quantity,
    COUNT(*) AS sales_rows,
    COUNT(DISTINCT store_id) AS active_stores,
    COUNT(DISTINCT product_id) AS active_products,
    ROUND(SUM(profit) / NULLIF(SUM(revenue), 0) * 100, 2) AS margin_pct,
    ROUND(SUM(revenue) / NULLIF(COUNT(*), 0), 2) AS avg_sale_row_revenue
FROM dm.v_sales_enriched
GROUP BY sale_month, sale_year, sale_month_num;

CREATE OR REPLACE VIEW dm.v_currency_rates_monthly AS
WITH monthly_rates AS (
    SELECT
        TO_CHAR(rate_date, 'YYYY-MM') AS report_month,
        currency_code,
        currency_name,
        AVG(rate_to_rub) AS avg_rate_to_rub,
        MIN(rate_to_rub) AS min_rate_to_rub,
        MAX(rate_to_rub) AS max_rate_to_rub,
        (ARRAY_AGG(rate_to_rub ORDER BY rate_date ASC))[1] AS first_rate_to_rub,
        (ARRAY_AGG(rate_to_rub ORDER BY rate_date DESC))[1] AS last_rate_to_rub,
        COUNT(*) AS observations
    FROM dm.dm_currency_rates
    GROUP BY TO_CHAR(rate_date, 'YYYY-MM'), currency_code, currency_name
)
SELECT
    report_month,
    currency_code,
    currency_name,
    ROUND(avg_rate_to_rub, 4) AS avg_rate_to_rub,
    min_rate_to_rub,
    max_rate_to_rub,
    first_rate_to_rub,
    last_rate_to_rub,
    ROUND((last_rate_to_rub - first_rate_to_rub) / NULLIF(first_rate_to_rub, 0) * 100, 2) AS monthly_change_pct,
    ROUND((max_rate_to_rub - min_rate_to_rub) / NULLIF(avg_rate_to_rub, 0) * 100, 2) AS monthly_volatility_pct,
    observations
FROM monthly_rates;

CREATE OR REPLACE VIEW dm.v_sales_fx_monthly AS
WITH sales AS (
    SELECT
        sale_month AS report_month,
        SUM(revenue) AS revenue_rub,
        SUM(total_cost) AS total_cost_rub,
        SUM(profit) AS profit_rub,
        SUM(quantity) AS quantity,
        ROUND(SUM(profit) / NULLIF(SUM(revenue), 0) * 100, 2) AS margin_pct
    FROM dm.dm_sales
    GROUP BY sale_month
),
joined AS (
    SELECT
        s.report_month,
        r.currency_code,
        r.currency_name,
        s.revenue_rub,
        s.total_cost_rub,
        s.profit_rub,
        s.quantity,
        s.margin_pct,
        r.avg_rate_to_rub,
        r.monthly_change_pct,
        r.monthly_volatility_pct
    FROM sales s
    JOIN dm.v_currency_rates_monthly r
        ON r.report_month = s.report_month
)
SELECT
    report_month,
    currency_code,
    currency_name,
    revenue_rub,
    total_cost_rub,
    profit_rub,
    quantity,
    margin_pct,
    avg_rate_to_rub,
    monthly_change_pct,
    monthly_volatility_pct,
    ROUND(revenue_rub / NULLIF(avg_rate_to_rub, 0), 2) AS revenue_in_currency,
    ROUND(total_cost_rub / NULLIF(avg_rate_to_rub, 0), 2) AS total_cost_in_currency,
    ROUND(profit_rub / NULLIF(avg_rate_to_rub, 0), 2) AS profit_in_currency,
    ROUND(
        (avg_rate_to_rub - LAG(avg_rate_to_rub) OVER (PARTITION BY currency_code ORDER BY report_month))
        / NULLIF(LAG(avg_rate_to_rub) OVER (PARTITION BY currency_code ORDER BY report_month), 0) * 100,
        2
    ) AS avg_rate_mom_pct,
    ROUND(
        (revenue_rub - LAG(revenue_rub) OVER (PARTITION BY currency_code ORDER BY report_month))
        / NULLIF(LAG(revenue_rub) OVER (PARTITION BY currency_code ORDER BY report_month), 0) * 100,
        2
    ) AS revenue_rub_mom_pct
FROM joined;

CREATE OR REPLACE VIEW dm.v_fx_risk_metrics AS
SELECT
    report_month,
    currency_code,
    currency_name,
    revenue_rub,
    total_cost_rub,
    profit_rub,
    margin_pct,
    avg_rate_to_rub,
    avg_rate_mom_pct,
    ROUND(total_cost_rub * COALESCE(avg_rate_mom_pct, 0) / 100, 2) AS estimated_cost_pressure_rub,
    ROUND(
        (profit_rub - total_cost_rub * COALESCE(avg_rate_mom_pct, 0) / 100)
        / NULLIF(revenue_rub, 0) * 100,
        2
    ) AS margin_after_fx_pressure_pct,
    CASE
        WHEN avg_rate_mom_pct >= 5 THEN 'Высокий валютный риск'
        WHEN avg_rate_mom_pct >= 2 THEN 'Умеренный валютный риск'
        WHEN avg_rate_mom_pct <= -2 THEN 'Снижение валютного давления'
        ELSE 'Стабильный курс'
    END AS fx_risk_status
FROM dm.v_sales_fx_monthly;

CREATE OR REPLACE VIEW dm.v_store_performance AS
SELECT
    sale_month,
    store_id,
    store_name,
    city,
    region,
    store_format,
    store_area_sqm,
    employees_count,
    SUM(revenue) AS revenue,
    SUM(total_cost) AS total_cost,
    SUM(profit) AS profit,
    SUM(quantity) AS quantity,
    COUNT(*) AS sales_rows,
    COUNT(DISTINCT product_id) AS active_products,
    ROUND(SUM(profit) / NULLIF(SUM(revenue), 0) * 100, 2) AS margin_pct,
    ROUND(SUM(revenue) / NULLIF(employees_count, 0), 2) AS revenue_per_employee,
    ROUND(SUM(revenue) / NULLIF(store_area_sqm, 0), 2) AS revenue_per_sqm
FROM dm.v_sales_enriched
GROUP BY
    sale_month,
    store_id,
    store_name,
    city,
    region,
    store_format,
    store_area_sqm,
    employees_count;

CREATE OR REPLACE VIEW dm.v_category_performance AS
SELECT
    sale_month,
    category,
    subcategory,
    brand,
    supplier,
    SUM(revenue) AS revenue,
    SUM(total_cost) AS total_cost,
    SUM(profit) AS profit,
    SUM(quantity) AS quantity,
    COUNT(*) AS sales_rows,
    COUNT(DISTINCT store_id) AS active_stores,
    ROUND(SUM(profit) / NULLIF(SUM(revenue), 0) * 100, 2) AS margin_pct,
    ROUND(SUM(revenue) / NULLIF(SUM(SUM(revenue)) OVER (PARTITION BY sale_month), 0) * 100, 2) AS revenue_share_pct
FROM dm.v_sales_enriched
GROUP BY sale_month, category, subcategory, brand, supplier;

CREATE OR REPLACE VIEW dm.v_category_plan_fact_mart AS
WITH plan_by_category AS (
    SELECT
        plan_month,
        category,
        SUM(plan_revenue) AS plan_revenue,
        SUM(plan_profit) AS plan_profit,
        SUM(plan_qty) AS plan_qty
    FROM dm.dm_plan_sales
    GROUP BY plan_month, category
),
sales_by_category AS (
    SELECT
        sale_month,
        category,
        SUM(revenue) AS fact_revenue,
        SUM(profit) AS fact_profit,
        SUM(quantity) AS fact_qty
    FROM dm.dm_sales
    GROUP BY sale_month, category
)
SELECT
    p.plan_month AS report_month,
    p.category,
    p.plan_revenue,
    p.plan_profit,
    p.plan_qty,
    COALESCE(s.fact_revenue, 0) AS fact_revenue,
    COALESCE(s.fact_profit, 0) AS fact_profit,
    COALESCE(s.fact_qty, 0) AS fact_qty,
    COALESCE(s.fact_revenue, 0) - p.plan_revenue AS revenue_variance,
    COALESCE(s.fact_profit, 0) - p.plan_profit AS profit_variance,
    ROUND(COALESCE(s.fact_revenue, 0) / NULLIF(p.plan_revenue, 0) * 100, 2) AS revenue_plan_completion_pct,
    ROUND(COALESCE(s.fact_profit, 0) / NULLIF(p.plan_profit, 0) * 100, 2) AS profit_plan_completion_pct
FROM plan_by_category p
LEFT JOIN sales_by_category s
    ON s.sale_month = p.plan_month
    AND s.category = p.category
;

CREATE OR REPLACE VIEW dm.v_plan_fact_dashboard AS
SELECT
    p.plan_month,
    p.store_id,
    st.store_name,
    st.city,
    st.region,
    st.format AS store_format,
    p.category,
    SUM(p.plan_revenue) AS plan_revenue,
    SUM(p.plan_profit) AS plan_profit,
    SUM(p.plan_qty) AS plan_qty,
    COALESCE(SUM(s.revenue), 0) AS fact_revenue,
    COALESCE(SUM(s.profit), 0) AS fact_profit,
    COALESCE(SUM(s.quantity), 0) AS fact_qty,
    COALESCE(SUM(s.revenue), 0) - SUM(p.plan_revenue) AS revenue_variance,
    COALESCE(SUM(s.profit), 0) - SUM(p.plan_profit) AS profit_variance,
    ROUND(COALESCE(SUM(s.revenue), 0) / NULLIF(SUM(p.plan_revenue), 0) * 100, 2) AS revenue_plan_completion_pct,
    ROUND(COALESCE(SUM(s.profit), 0) / NULLIF(SUM(p.plan_profit), 0) * 100, 2) AS profit_plan_completion_pct
FROM dm.dm_plan_sales p
LEFT JOIN dm.dm_sales s
    ON s.sale_month = p.plan_month
    AND s.store_id = p.store_id
    AND s.category = p.category
LEFT JOIN dm.dm_stores st
    ON st.store_id = p.store_id
GROUP BY
    p.plan_month,
    p.store_id,
    st.store_name,
    st.city,
    st.region,
    st.format,
    p.category;

CREATE OR REPLACE VIEW dm.v_inventory_risks AS
SELECT
    i.inventory_date,
    i.store_id,
    st.store_name,
    st.city,
    st.region,
    st.format AS store_format,
    i.product_id,
    p.product_name,
    p.category,
    p.subcategory,
    p.brand,
    p.supplier,
    i.stock_qty,
    i.stock_value,
    i.reorder_point,
    i.days_of_cover,
    i.stock_status,
    CASE WHEN i.stock_status = 'LOW' THEN 1 ELSE 0 END AS is_low_stock,
    CASE WHEN i.stock_status = 'OVERSTOCK' THEN 1 ELSE 0 END AS is_overstock,
    i.stock_qty - i.reorder_point AS stock_vs_reorder_qty
FROM dm.dm_inventory i
LEFT JOIN dm.dm_stores st
    ON st.store_id = i.store_id
LEFT JOIN dm.dm_products p
    ON p.product_id = i.product_id;

CREATE OR REPLACE VIEW dm.v_dashboard_summary AS
SELECT
    k.sale_month,
    k.revenue,
    k.profit,
    k.quantity,
    k.margin_pct,
    pf.plan_revenue,
    pf.fact_revenue,
    pf.revenue_plan_completion_pct,
    inv.inventory_date AS latest_inventory_date,
    inv.total_stock_qty,
    inv.total_stock_value,
    inv.low_stock_positions,
    inv.overstock_positions
FROM dm.v_monthly_sales_kpi k
LEFT JOIN (
    SELECT
        plan_month,
        SUM(plan_revenue) AS plan_revenue,
        SUM(fact_revenue) AS fact_revenue,
        ROUND(SUM(fact_revenue) / NULLIF(SUM(plan_revenue), 0) * 100, 2) AS revenue_plan_completion_pct
    FROM dm.v_plan_fact_dashboard
    GROUP BY plan_month
) pf
    ON pf.plan_month = k.sale_month
LEFT JOIN (
    SELECT
        inventory_date,
        SUM(stock_qty) AS total_stock_qty,
        SUM(stock_value) AS total_stock_value,
        SUM(is_low_stock) AS low_stock_positions,
        SUM(is_overstock) AS overstock_positions
    FROM dm.v_inventory_risks
    GROUP BY inventory_date
) inv
    ON TO_CHAR(inv.inventory_date, 'YYYY-MM') = k.sale_month;

CREATE OR REPLACE VIEW dm.v_monthly_plan_fact_trend AS
WITH plan_by_month AS (
    SELECT
        plan_month AS trend_month,
        SUM(plan_revenue) AS plan_revenue,
        SUM(plan_profit) AS plan_profit,
        SUM(plan_qty) AS plan_qty
    FROM dm.dm_plan_sales
    GROUP BY plan_month
),
sales_by_month AS (
    SELECT
        sale_month AS trend_month,
        SUM(revenue) AS fact_revenue,
        SUM(profit) AS fact_profit,
        SUM(quantity) AS fact_qty
    FROM dm.dm_sales
    GROUP BY sale_month
)
SELECT
    COALESCE(p.trend_month, s.trend_month) AS trend_month,
    COALESCE(p.plan_revenue, 0) AS plan_revenue,
    COALESCE(p.plan_profit, 0) AS plan_profit,
    COALESCE(p.plan_qty, 0) AS plan_qty,
    COALESCE(s.fact_revenue, 0) AS fact_revenue,
    COALESCE(s.fact_profit, 0) AS fact_profit,
    COALESCE(s.fact_qty, 0) AS fact_qty,
    COALESCE(s.fact_revenue, 0) - COALESCE(p.plan_revenue, 0) AS revenue_variance,
    ROUND(COALESCE(s.fact_revenue, 0) / NULLIF(p.plan_revenue, 0) * 100, 2) AS revenue_plan_completion_pct
FROM plan_by_month p
FULL OUTER JOIN sales_by_month s
    ON s.trend_month = p.trend_month;

DROP VIEW IF EXISTS dm.v_product_inventory_turnover;
DROP VIEW IF EXISTS dm.v_abc_xyz_analysis;
DROP VIEW IF EXISTS dm.v_store_monthly_heatmap;
DROP VIEW IF EXISTS dm.v_retail_kpi_mart;

CREATE OR REPLACE VIEW dm.v_retail_kpi_mart AS
WITH sales AS (
    SELECT
        sale_month,
        store_id,
        store_name,
        city,
        region,
        store_format,
        category,
        SUM(revenue) AS fact_revenue,
        SUM(total_cost) AS fact_cost,
        SUM(profit) AS fact_profit,
        SUM(quantity) AS fact_qty,
        COUNT(*) AS sales_rows,
        COUNT(DISTINCT product_id) AS sold_products,
        ROUND(SUM(profit) / NULLIF(SUM(revenue), 0) * 100, 2) AS margin_pct,
        ROUND(SUM(revenue) / NULLIF(SUM(quantity), 0), 2) AS avg_unit_revenue
    FROM dm.v_sales_enriched
    GROUP BY
        sale_month,
        store_id,
        store_name,
        city,
        region,
        store_format,
        category
),
plan AS (
    SELECT
        plan_month,
        store_id,
        category,
        SUM(plan_revenue) AS plan_revenue,
        SUM(plan_profit) AS plan_profit,
        SUM(plan_qty) AS plan_qty
    FROM dm.dm_plan_sales
    GROUP BY plan_month, store_id, category
),
inventory AS (
    SELECT
        TO_CHAR(i.inventory_date, 'YYYY-MM') AS inventory_month,
        i.store_id,
        p.category,
        SUM(i.stock_qty) AS stock_qty,
        SUM(i.stock_value) AS stock_value,
        AVG(i.days_of_cover) AS avg_days_of_cover,
        SUM(CASE WHEN i.stock_status = 'LOW' THEN 1 ELSE 0 END) AS low_stock_positions,
        SUM(CASE WHEN i.stock_status = 'OVERSTOCK' THEN 1 ELSE 0 END) AS overstock_positions,
        SUM(CASE WHEN i.stock_status = 'OK' THEN 1 ELSE 0 END) AS ok_stock_positions,
        COUNT(*) AS inventory_positions
    FROM dm.dm_inventory i
    LEFT JOIN dm.dm_products p
        ON p.product_id = i.product_id
    GROUP BY TO_CHAR(i.inventory_date, 'YYYY-MM'), i.store_id, p.category
)
SELECT
    COALESCE(s.sale_month, p.plan_month, i.inventory_month) AS report_month,
    COALESCE(s.store_id, p.store_id, i.store_id) AS store_id,
    COALESCE(s.store_name, st.store_name) AS store_name,
    COALESCE(s.city, st.city) AS city,
    COALESCE(s.region, st.region) AS region,
    COALESCE(s.store_format, st.format) AS store_format,
    COALESCE(s.category, p.category, i.category) AS category,
    COALESCE(s.fact_revenue, 0) AS fact_revenue,
    COALESCE(s.fact_cost, 0) AS fact_cost,
    COALESCE(s.fact_profit, 0) AS fact_profit,
    COALESCE(s.fact_qty, 0) AS fact_qty,
    COALESCE(s.sales_rows, 0) AS sales_rows,
    COALESCE(s.sold_products, 0) AS sold_products,
    COALESCE(s.margin_pct, 0) AS margin_pct,
    COALESCE(s.avg_unit_revenue, 0) AS avg_unit_revenue,
    COALESCE(p.plan_revenue, 0) AS plan_revenue,
    COALESCE(p.plan_profit, 0) AS plan_profit,
    COALESCE(p.plan_qty, 0) AS plan_qty,
    COALESCE(s.fact_revenue, 0) - COALESCE(p.plan_revenue, 0) AS revenue_variance,
    COALESCE(s.fact_profit, 0) - COALESCE(p.plan_profit, 0) AS profit_variance,
    ROUND(COALESCE(s.fact_revenue, 0) / NULLIF(p.plan_revenue, 0) * 100, 2) AS revenue_plan_completion_pct,
    ROUND(COALESCE(s.fact_profit, 0) / NULLIF(p.plan_profit, 0) * 100, 2) AS profit_plan_completion_pct,
    COALESCE(i.stock_qty, 0) AS stock_qty,
    COALESCE(i.stock_value, 0) AS stock_value,
    ROUND(COALESCE(i.avg_days_of_cover, 0), 2) AS avg_days_of_cover,
    COALESCE(i.low_stock_positions, 0) AS low_stock_positions,
    COALESCE(i.overstock_positions, 0) AS overstock_positions,
    COALESCE(i.ok_stock_positions, 0) AS ok_stock_positions,
    COALESCE(i.inventory_positions, 0) AS inventory_positions,
    ROUND(COALESCE(s.fact_revenue, 0) / NULLIF(i.stock_value, 0), 4) AS stock_turnover_revenue_ratio,
    CASE
        WHEN COALESCE(i.low_stock_positions, 0) > 0 AND COALESCE(s.fact_revenue, 0) > 0 THEN 'Риск упущенной выручки'
        WHEN COALESCE(i.overstock_positions, 0) > 0 THEN 'Избыточные запасы'
        WHEN COALESCE(s.fact_revenue, 0) < COALESCE(p.plan_revenue, 0) THEN 'Невыполнение плана'
        ELSE 'Норма'
    END AS management_status
FROM sales s
FULL OUTER JOIN plan p
    ON p.plan_month = s.sale_month
    AND p.store_id = s.store_id
    AND p.category = s.category
FULL OUTER JOIN inventory i
    ON i.inventory_month = COALESCE(s.sale_month, p.plan_month)
    AND i.store_id = COALESCE(s.store_id, p.store_id)
    AND i.category = COALESCE(s.category, p.category)
LEFT JOIN dm.dm_stores st
    ON st.store_id = COALESCE(s.store_id, p.store_id, i.store_id);

CREATE OR REPLACE VIEW dm.v_store_monthly_heatmap AS
SELECT
    report_month,
    store_id,
    store_name,
    city,
    region,
    store_format,
    SUM(fact_revenue) AS fact_revenue,
    SUM(fact_profit) AS fact_profit,
    SUM(plan_revenue) AS plan_revenue,
    SUM(revenue_variance) AS revenue_variance,
    ROUND(SUM(fact_revenue) / NULLIF(SUM(plan_revenue), 0) * 100, 2) AS revenue_plan_completion_pct,
    ROUND(SUM(fact_profit) / NULLIF(SUM(fact_revenue), 0) * 100, 2) AS margin_pct,
    SUM(stock_value) AS stock_value,
    SUM(low_stock_positions) AS low_stock_positions,
    SUM(overstock_positions) AS overstock_positions,
    ROUND(AVG(NULLIF(avg_days_of_cover, 0)), 2) AS avg_days_of_cover,
    RANK() OVER (PARTITION BY report_month ORDER BY SUM(fact_revenue) DESC) AS revenue_rank,
    RANK() OVER (PARTITION BY report_month ORDER BY SUM(fact_profit) DESC) AS profit_rank,
    RANK() OVER (PARTITION BY report_month ORDER BY SUM(revenue_variance) ASC) AS underplan_rank
FROM dm.v_retail_kpi_mart
GROUP BY report_month, store_id, store_name, city, region, store_format;

CREATE OR REPLACE VIEW dm.v_abc_xyz_analysis AS
WITH product_month AS (
    SELECT
        sale_month,
        product_id,
        product_name,
        category,
        subcategory,
        brand,
        supplier,
        SUM(revenue) AS revenue,
        SUM(profit) AS profit,
        SUM(quantity) AS quantity
    FROM dm.v_sales_enriched
    GROUP BY sale_month, product_id, product_name, category, subcategory, brand, supplier
),
product_total AS (
    SELECT
        product_id,
        product_name,
        category,
        subcategory,
        brand,
        supplier,
        SUM(revenue) AS revenue,
        SUM(profit) AS profit,
        SUM(quantity) AS quantity,
        AVG(quantity) AS avg_monthly_qty,
        STDDEV_POP(quantity) AS stddev_monthly_qty,
        COUNT(*) AS active_months
    FROM product_month
    GROUP BY product_id, product_name, category, subcategory, brand, supplier
),
abc AS (
    SELECT
        *,
        ROUND(revenue / NULLIF(SUM(revenue) OVER (), 0) * 100, 4) AS revenue_share_pct,
        ROUND(SUM(revenue) OVER (ORDER BY revenue DESC ROWS UNBOUNDED PRECEDING) / NULLIF(SUM(revenue) OVER (), 0) * 100, 4) AS cumulative_revenue_share_pct
    FROM product_total
)
SELECT
    product_id,
    product_name,
    category,
    subcategory,
    brand,
    supplier,
    revenue,
    profit,
    quantity,
    active_months,
    ROUND(profit / NULLIF(revenue, 0) * 100, 2) AS margin_pct,
    revenue_share_pct,
    cumulative_revenue_share_pct,
    CASE
        WHEN cumulative_revenue_share_pct <= 80 THEN 'A'
        WHEN cumulative_revenue_share_pct <= 95 THEN 'B'
        ELSE 'C'
    END AS abc_class,
    ROUND(stddev_monthly_qty / NULLIF(avg_monthly_qty, 0) * 100, 2) AS demand_cv_pct,
    CASE
        WHEN stddev_monthly_qty / NULLIF(avg_monthly_qty, 0) <= 0.10 THEN 'X'
        WHEN stddev_monthly_qty / NULLIF(avg_monthly_qty, 0) <= 0.25 THEN 'Y'
        ELSE 'Z'
    END AS xyz_class,
    CASE
        WHEN cumulative_revenue_share_pct <= 80 THEN 'A'
        WHEN cumulative_revenue_share_pct <= 95 THEN 'B'
        ELSE 'C'
    END ||
    CASE
        WHEN stddev_monthly_qty / NULLIF(avg_monthly_qty, 0) <= 0.10 THEN 'X'
        WHEN stddev_monthly_qty / NULLIF(avg_monthly_qty, 0) <= 0.25 THEN 'Y'
        ELSE 'Z'
    END AS abc_xyz_class
FROM abc;

CREATE OR REPLACE VIEW dm.v_product_inventory_turnover AS
WITH sales_month AS (
    SELECT
        sale_month,
        store_id,
        store_name,
        region,
        product_id,
        product_name,
        category,
        brand,
        SUM(quantity) AS sold_qty,
        SUM(revenue) AS revenue,
        SUM(profit) AS profit
    FROM dm.v_sales_enriched
    GROUP BY sale_month, store_id, store_name, region, product_id, product_name, category, brand
),
inventory_month AS (
    SELECT
        TO_CHAR(i.inventory_date, 'YYYY-MM') AS inventory_month,
        i.store_id,
        st.store_name,
        st.region,
        i.product_id,
        p.product_name,
        p.category,
        p.brand,
        SUM(i.stock_qty) AS stock_qty,
        SUM(i.stock_value) AS stock_value,
        AVG(i.days_of_cover) AS avg_days_of_cover,
        MAX(i.stock_status) AS stock_status
    FROM dm.dm_inventory i
    LEFT JOIN dm.dm_stores st
        ON st.store_id = i.store_id
    LEFT JOIN dm.dm_products p
        ON p.product_id = i.product_id
    GROUP BY TO_CHAR(i.inventory_date, 'YYYY-MM'), i.store_id, st.store_name, st.region, i.product_id, p.product_name, p.category, p.brand
)
SELECT
    COALESCE(s.sale_month, i.inventory_month) AS report_month,
    COALESCE(s.store_id, i.store_id) AS store_id,
    COALESCE(s.store_name, i.store_name) AS store_name,
    COALESCE(s.region, i.region) AS region,
    COALESCE(s.product_id, i.product_id) AS product_id,
    COALESCE(s.product_name, i.product_name) AS product_name,
    COALESCE(s.category, i.category) AS category,
    COALESCE(s.brand, i.brand) AS brand,
    COALESCE(s.sold_qty, 0) AS sold_qty,
    COALESCE(s.revenue, 0) AS revenue,
    COALESCE(s.profit, 0) AS profit,
    COALESCE(i.stock_qty, 0) AS stock_qty,
    COALESCE(i.stock_value, 0) AS stock_value,
    ROUND(COALESCE(i.avg_days_of_cover, 0), 2) AS avg_days_of_cover,
    i.stock_status,
    ROUND(COALESCE(s.sold_qty, 0) / NULLIF(i.stock_qty, 0), 4) AS qty_turnover_ratio,
    ROUND(COALESCE(s.revenue, 0) / NULLIF(i.stock_value, 0), 4) AS value_turnover_ratio,
    CASE
        WHEN COALESCE(s.sold_qty, 0) = 0 AND COALESCE(i.stock_qty, 0) > 0 THEN 'Нет продаж при наличии остатка'
        WHEN COALESCE(i.stock_qty, 0) = 0 AND COALESCE(s.sold_qty, 0) > 0 THEN 'Продажи без остатка на конец месяца'
        WHEN COALESCE(i.avg_days_of_cover, 0) < 7 THEN 'Риск дефицита'
        WHEN COALESCE(i.avg_days_of_cover, 0) > 45 THEN 'Риск излишка'
        ELSE 'Норма'
    END AS turnover_status
FROM sales_month s
FULL OUTER JOIN inventory_month i
    ON i.inventory_month = s.sale_month
    AND i.store_id = s.store_id
    AND i.product_id = s.product_id;
