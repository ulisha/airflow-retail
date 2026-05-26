CREATE OR REPLACE VIEW dm.v_monthly_kpi AS
SELECT sale_month, SUM(revenue) AS revenue, SUM(profit) AS profit, SUM(quantity) AS quantity, COUNT(*) AS sales_count
FROM dm.dm_sales
GROUP BY sale_month;

CREATE OR REPLACE VIEW dm.v_store_monthly_ranking AS
SELECT sale_month, store_id, SUM(revenue) AS revenue, SUM(profit) AS profit, SUM(quantity) AS quantity
FROM dm.dm_sales
GROUP BY sale_month, store_id;

CREATE OR REPLACE VIEW dm.v_category_monthly_ranking AS
SELECT sale_month, category, SUM(revenue) AS revenue, SUM(profit) AS profit, SUM(quantity) AS quantity
FROM dm.dm_sales
GROUP BY sale_month, category;

CREATE OR REPLACE VIEW dm.v_plan_fact_summary AS
SELECT
    p.plan_month,
    SUM(p.plan_revenue) AS plan_revenue,
    SUM(p.plan_profit) AS plan_profit,
    SUM(p.plan_qty) AS plan_qty,
    COALESCE(SUM(s.revenue), 0) AS fact_revenue,
    COALESCE(SUM(s.profit), 0) AS fact_profit,
    COALESCE(SUM(s.quantity), 0) AS fact_qty,
    ROUND(COALESCE(SUM(s.revenue), 0) / NULLIF(SUM(p.plan_revenue), 0) * 100, 2) AS plan_revenue_pct,
    ROUND(COALESCE(SUM(s.profit), 0) / NULLIF(SUM(p.plan_profit), 0) * 100, 2) AS plan_profit_pct
FROM dm.dm_plan_sales p
LEFT JOIN dm.dm_sales s
  ON s.sale_month = p.plan_month AND s.store_id = p.store_id AND s.category = p.category
GROUP BY p.plan_month;

CREATE OR REPLACE VIEW dm.v_plan_fact_store AS
SELECT
    p.plan_month, p.store_id,
    SUM(p.plan_revenue) AS plan_revenue,
    COALESCE(SUM(s.revenue), 0) AS fact_revenue,
    ROUND(COALESCE(SUM(s.revenue), 0) / NULLIF(SUM(p.plan_revenue), 0) * 100, 2) AS plan_revenue_pct,
    SUM(p.plan_profit) AS plan_profit,
    COALESCE(SUM(s.profit), 0) AS fact_profit,
    ROUND(COALESCE(SUM(s.profit), 0) / NULLIF(SUM(p.plan_profit), 0) * 100, 2) AS plan_profit_pct
FROM dm.dm_plan_sales p
LEFT JOIN dm.dm_sales s
  ON s.sale_month = p.plan_month AND s.store_id = p.store_id AND s.category = p.category
GROUP BY p.plan_month, p.store_id;

CREATE OR REPLACE VIEW dm.v_plan_fact_category AS
SELECT
    p.plan_month, p.category,
    SUM(p.plan_revenue) AS plan_revenue,
    COALESCE(SUM(s.revenue), 0) AS fact_revenue,
    ROUND(COALESCE(SUM(s.revenue), 0) / NULLIF(SUM(p.plan_revenue), 0) * 100, 2) AS plan_revenue_pct,
    SUM(p.plan_profit) AS plan_profit,
    COALESCE(SUM(s.profit), 0) AS fact_profit,
    ROUND(COALESCE(SUM(s.profit), 0) / NULLIF(SUM(p.plan_profit), 0) * 100, 2) AS plan_profit_pct
FROM dm.dm_plan_sales p
LEFT JOIN dm.dm_sales s
  ON s.sale_month = p.plan_month AND s.store_id = p.store_id AND s.category = p.category
GROUP BY p.plan_month, p.category;

CREATE OR REPLACE VIEW dm.v_inventory_summary AS
SELECT inventory_date, SUM(stock_qty) AS total_stock_qty, SUM(stock_value) AS total_stock_value
FROM dm.dm_inventory
GROUP BY inventory_date;

CREATE OR REPLACE VIEW dm.v_inventory_alerts AS
SELECT inventory_date, store_id, product_id, stock_qty, stock_value, reorder_point, days_of_cover, stock_status
FROM dm.dm_inventory;
