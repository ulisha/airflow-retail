CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS stg;
CREATE SCHEMA IF NOT EXISTS dm;

CREATE TABLE IF NOT EXISTS raw.sales_raw (
    sale_id TEXT, invoice_no TEXT, invoice_type TEXT, sale_datetime TEXT, sale_date TEXT,
    sale_month TEXT, store_id TEXT, product_id TEXT, stock_code TEXT, description TEXT,
    category TEXT, quantity TEXT, unit_price TEXT, discount_rate TEXT, revenue TEXT,
    unit_cost TEXT, total_cost TEXT, profit TEXT, customer_id TEXT, country TEXT,
    sales_channel TEXT, load_dttm TIMESTAMP DEFAULT CURRENT_TIMESTAMP, source_file TEXT
);
CREATE TABLE IF NOT EXISTS raw.stores_raw (
    store_id TEXT, store_name TEXT, city TEXT, region TEXT, format TEXT,
    opening_date TEXT, store_area_sqm TEXT, employees_count TEXT, load_dttm TIMESTAMP DEFAULT CURRENT_TIMESTAMP, source_file TEXT
);
CREATE TABLE IF NOT EXISTS raw.products_raw (
    product_id TEXT, stock_code TEXT, product_name TEXT, category TEXT, subcategory TEXT,
    brand TEXT, supplier TEXT, unit_cost TEXT, unit_price TEXT, uom TEXT, is_active TEXT,
    load_dttm TIMESTAMP DEFAULT CURRENT_TIMESTAMP, source_file TEXT
);
CREATE TABLE IF NOT EXISTS raw.inventory_raw (
    inventory_date TEXT, store_id TEXT, product_id TEXT, stock_qty TEXT, stock_value TEXT,
    reorder_point TEXT, days_of_cover TEXT, stock_status TEXT, load_dttm TIMESTAMP DEFAULT CURRENT_TIMESTAMP, source_file TEXT
);
CREATE TABLE IF NOT EXISTS raw.plan_sales_raw (
    plan_month TEXT, store_id TEXT, category TEXT, plan_revenue TEXT, plan_profit TEXT,
    plan_qty TEXT, load_dttm TIMESTAMP DEFAULT CURRENT_TIMESTAMP, source_file TEXT
);
CREATE TABLE IF NOT EXISTS raw.currency_rates_raw (
    rate_date TEXT, currency_code TEXT, currency_name TEXT, nominal TEXT, rate_to_rub TEXT,
    source_url TEXT, load_dttm TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS stg.sales_clean (
    sale_id TEXT PRIMARY KEY, invoice_no TEXT NOT NULL, invoice_type TEXT NOT NULL,
    sale_datetime TIMESTAMP NOT NULL, sale_date DATE NOT NULL, sale_month TEXT NOT NULL,
    store_id TEXT NOT NULL, product_id TEXT NOT NULL, stock_code TEXT, description TEXT, category TEXT NOT NULL,
    quantity INTEGER NOT NULL, unit_price NUMERIC(12,2) NOT NULL, discount_rate NUMERIC(5,2) NOT NULL,
    revenue NUMERIC(14,2) NOT NULL, unit_cost NUMERIC(12,2) NOT NULL, total_cost NUMERIC(14,2) NOT NULL,
    profit NUMERIC(14,2) NOT NULL, customer_id TEXT, country TEXT, sales_channel TEXT,
    load_dttm TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS stg.stores_clean (
    store_id TEXT PRIMARY KEY, store_name TEXT NOT NULL, city TEXT NOT NULL, region TEXT NOT NULL,
    format TEXT NOT NULL, opening_date DATE NOT NULL, store_area_sqm INTEGER NOT NULL,
    employees_count INTEGER NOT NULL, load_dttm TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS stg.products_clean (
    product_id TEXT PRIMARY KEY, stock_code TEXT, product_name TEXT NOT NULL, category TEXT NOT NULL,
    subcategory TEXT, brand TEXT, supplier TEXT, unit_cost NUMERIC(12,2) NOT NULL,
    unit_price NUMERIC(12,2) NOT NULL, uom TEXT, is_active SMALLINT NOT NULL,
    load_dttm TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS stg.inventory_clean (
    inventory_date DATE NOT NULL, store_id TEXT NOT NULL, product_id TEXT NOT NULL,
    stock_qty INTEGER NOT NULL, stock_value NUMERIC(14,2) NOT NULL, reorder_point INTEGER NOT NULL,
    days_of_cover NUMERIC(10,2) NOT NULL, stock_status TEXT NOT NULL,
    load_dttm TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (inventory_date, store_id, product_id)
);
CREATE TABLE IF NOT EXISTS stg.plan_sales_clean (
    plan_month TEXT NOT NULL, store_id TEXT NOT NULL, category TEXT NOT NULL,
    plan_revenue NUMERIC(14,2) NOT NULL, plan_profit NUMERIC(14,2) NOT NULL, plan_qty INTEGER NOT NULL,
    load_dttm TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (plan_month, store_id, category)
);
CREATE TABLE IF NOT EXISTS stg.currency_rates_clean (
    rate_date DATE NOT NULL,
    currency_code TEXT NOT NULL,
    currency_name TEXT NOT NULL,
    nominal INTEGER NOT NULL,
    rate_to_rub NUMERIC(12,4) NOT NULL,
    source_url TEXT,
    load_dttm TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (rate_date, currency_code)
);

CREATE TABLE IF NOT EXISTS dm.dm_sales (
    sale_id TEXT PRIMARY KEY, sale_date DATE NOT NULL, sale_month TEXT NOT NULL, store_id TEXT NOT NULL,
    product_id TEXT NOT NULL, category TEXT NOT NULL, quantity INTEGER NOT NULL,
    revenue NUMERIC(14,2) NOT NULL, total_cost NUMERIC(14,2) NOT NULL, profit NUMERIC(14,2) NOT NULL,
    sales_channel TEXT, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS dm.dm_stores (
    store_id TEXT PRIMARY KEY,
    store_name TEXT NOT NULL,
    city TEXT NOT NULL,
    region TEXT NOT NULL,
    format TEXT NOT NULL,
    opening_date DATE NOT NULL,
    store_area_sqm INTEGER NOT NULL,
    employees_count INTEGER NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS dm.dm_products (
    product_id TEXT PRIMARY KEY,
    stock_code TEXT,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT,
    brand TEXT,
    supplier TEXT,
    unit_cost NUMERIC(12,2) NOT NULL,
    unit_price NUMERIC(12,2) NOT NULL,
    uom TEXT,
    is_active SMALLINT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS dm.dm_inventory (
    inventory_date DATE NOT NULL, store_id TEXT NOT NULL, product_id TEXT NOT NULL,
    stock_qty INTEGER NOT NULL, stock_value NUMERIC(14,2) NOT NULL, reorder_point INTEGER NOT NULL,
    days_of_cover NUMERIC(10,2) NOT NULL, stock_status TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (inventory_date, store_id, product_id)
);
CREATE TABLE IF NOT EXISTS dm.dm_plan_sales (
    plan_month TEXT NOT NULL, store_id TEXT NOT NULL, category TEXT NOT NULL,
    plan_revenue NUMERIC(14,2) NOT NULL, plan_profit NUMERIC(14,2) NOT NULL, plan_qty INTEGER NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (plan_month, store_id, category)
);
CREATE TABLE IF NOT EXISTS dm.dm_currency_rates (
    rate_date DATE NOT NULL,
    currency_code TEXT NOT NULL,
    currency_name TEXT NOT NULL,
    nominal INTEGER NOT NULL,
    rate_to_rub NUMERIC(12,4) NOT NULL,
    source_url TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (rate_date, currency_code)
);
