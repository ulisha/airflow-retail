from __future__ import annotations
import os
from pathlib import Path
from datetime import date, datetime
from urllib.request import urlopen
from urllib.parse import urlencode
import xml.etree.ElementTree as ET
import pandas as pd
from sqlalchemy import create_engine, text

def get_engine():
    return create_engine(
        f"postgresql+psycopg2://{os.getenv('RETAIL_DB_USER','airflow')}:{os.getenv('RETAIL_DB_PASSWORD','airflow')}"
        f"@{os.getenv('RETAIL_DB_HOST','postgres')}:{os.getenv('RETAIL_DB_PORT','5432')}/{os.getenv('RETAIL_DB_NAME','retail')}"
    )

DATA_DIR = Path(os.getenv("RETAIL_DATA_DIR", "/opt/airflow/data"))
CBR_DAILY_URL = os.getenv("CBR_DAILY_URL", "https://www.cbr.ru/scripts/XML_daily.asp")
CBR_DYNAMIC_URL = os.getenv("CBR_DYNAMIC_URL", "https://www.cbr.ru/scripts/XML_dynamic.asp")
CURRENCY_CODES = tuple(
    code.strip().upper()
    for code in os.getenv("CURRENCY_CODES", "USD,EUR,CNY").split(",")
    if code.strip()
)
CURRENCY_HISTORY_START = os.getenv("CURRENCY_HISTORY_START", "2024-01-01")
CURRENCY_HISTORY_END = os.getenv("CURRENCY_HISTORY_END")

def read_csv(name: str) -> pd.DataFrame:
    path = DATA_DIR / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)

def load_raw_table(engine, df, table, source_file):
    df = df.copy()
    df["source_file"] = source_file
    df.to_sql(table, engine, schema="raw", if_exists="append", index=False, method="multi", chunksize=5000)

def write_clean(engine, df, table):
    df.to_sql(table, engine, schema="stg", if_exists="append", index=False, method="multi", chunksize=5000)

def fetch_currency_rates(report_date: date | None = None) -> pd.DataFrame:
    report_date = report_date or date.today()
    date_req = report_date.strftime("%d/%m/%Y")
    source_url = f"{CBR_DAILY_URL}?date_req={date_req}"

    with urlopen(source_url, timeout=30) as response:
        payload = response.read()

    root = ET.fromstring(payload)
    rate_date = datetime.strptime(root.attrib["Date"], "%d.%m.%Y").date()
    rows = []

    for item in root.findall("Valute"):
        code = item.findtext("CharCode", "").upper()
        if code not in CURRENCY_CODES:
            continue

        nominal = int(item.findtext("Nominal", "1"))
        value = float(item.findtext("Value", "0").replace(",", "."))
        rows.append(
            {
                "rate_date": rate_date.isoformat(),
                "currency_code": code,
                "currency_name": item.findtext("Name", ""),
                "nominal": str(nominal),
                "rate_to_rub": round(value / nominal, 4),
                "source_url": source_url,
            }
        )

    if not rows:
        raise ValueError(f"No requested currencies found in CBR response: {CURRENCY_CODES}")

    return pd.DataFrame(rows)

def get_currency_metadata(report_date: date | None = None) -> dict[str, dict[str, str]]:
    report_date = report_date or date.today()
    date_req = report_date.strftime("%d/%m/%Y")
    source_url = f"{CBR_DAILY_URL}?date_req={date_req}"

    with urlopen(source_url, timeout=30) as response:
        payload = response.read()

    root = ET.fromstring(payload)
    metadata = {}
    for item in root.findall("Valute"):
        code = item.findtext("CharCode", "").upper()
        if code in CURRENCY_CODES:
            metadata[code] = {
                "id": item.attrib["ID"],
                "name": item.findtext("Name", ""),
            }
    return metadata

def fetch_currency_rates_history(
    start_date: date | None = None,
    end_date: date | None = None,
) -> pd.DataFrame:
    start_date = start_date or datetime.strptime(CURRENCY_HISTORY_START, "%Y-%m-%d").date()
    end_date = end_date or (
        datetime.strptime(CURRENCY_HISTORY_END, "%Y-%m-%d").date()
        if CURRENCY_HISTORY_END
        else date.today()
    )
    metadata = get_currency_metadata(end_date)
    rows = []

    for code in CURRENCY_CODES:
        currency = metadata.get(code)
        if not currency:
            continue

        query = urlencode(
            {
                "date_req1": start_date.strftime("%d/%m/%Y"),
                "date_req2": end_date.strftime("%d/%m/%Y"),
                "VAL_NM_RQ": currency["id"],
            }
        )
        source_url = f"{CBR_DYNAMIC_URL}?{query}"
        with urlopen(source_url, timeout=30) as response:
            payload = response.read()

        root = ET.fromstring(payload)
        for item in root.findall("Record"):
            nominal = int(item.findtext("Nominal", "1"))
            value = float(item.findtext("Value", "0").replace(",", "."))
            vunit_rate = item.findtext("VunitRate")
            rate_to_rub = float(vunit_rate.replace(",", ".")) if vunit_rate else value / nominal
            rows.append(
                {
                    "rate_date": datetime.strptime(item.attrib["Date"], "%d.%m.%Y").date().isoformat(),
                    "currency_code": code,
                    "currency_name": currency["name"],
                    "nominal": str(nominal),
                    "rate_to_rub": round(rate_to_rub, 4),
                    "source_url": source_url,
                }
            )

    if not rows:
        raise ValueError(f"No CBR history loaded for currencies: {CURRENCY_CODES}")

    return pd.DataFrame(rows)

def transform_stores(df):
    df = df.drop_duplicates(subset=["store_id"]).copy()
    df["opening_date"] = pd.to_datetime(df["opening_date"], errors="coerce").dt.date
    for c in ["store_area_sqm", "employees_count"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    return df.dropna(subset=["store_id", "store_name", "city", "region", "format", "opening_date"])

def transform_products(df):
    df = df.drop_duplicates(subset=["product_id"]).copy()
    for c in ["unit_cost", "unit_price", "is_active"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["unit_cost"] = df["unit_cost"].fillna(0).round(2)
    df["unit_price"] = df["unit_price"].fillna(0).round(2)
    df["is_active"] = df["is_active"].fillna(1).astype(int)
    return df.dropna(subset=["product_id", "product_name", "category"])

def transform_sales(df):
    df = df.drop_duplicates(subset=["sale_id"]).copy()
    df["sale_datetime"] = pd.to_datetime(df["sale_datetime"], errors="coerce")
    df["sale_date"] = pd.to_datetime(df["sale_date"], errors="coerce").dt.date
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    for c in ["unit_price", "discount_rate", "revenue", "unit_cost", "total_cost", "profit"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").round(2)
    df = df.dropna(subset=["sale_id", "invoice_no", "sale_datetime", "sale_date", "store_id", "product_id", "category"])
    df = df[(df["quantity"] > 0) & (df["unit_price"] >= 0) & (df["revenue"] >= 0)]
    df["quantity"] = df["quantity"].astype(int)
    df["discount_rate"] = df["discount_rate"].fillna(0)
    return df

def transform_inventory(df):
    df = df.drop_duplicates(subset=["inventory_date", "store_id", "product_id"]).copy()
    df["inventory_date"] = pd.to_datetime(df["inventory_date"], errors="coerce").dt.date
    for c in ["stock_qty", "reorder_point"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    for c in ["stock_value", "days_of_cover"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).round(2)
    return df.dropna(subset=["inventory_date", "store_id", "product_id", "stock_status"])

def transform_plan_sales(df):
    df = df.drop_duplicates(subset=["plan_month", "store_id", "category"]).copy()
    df["plan_qty"] = pd.to_numeric(df["plan_qty"], errors="coerce").fillna(0).astype(int)
    df["plan_revenue"] = pd.to_numeric(df["plan_revenue"], errors="coerce").fillna(0).round(2)
    df["plan_profit"] = pd.to_numeric(df["plan_profit"], errors="coerce").fillna(0).round(2)
    return df.dropna(subset=["plan_month", "store_id", "category"])

def transform_currency_rates(df):
    df = df.drop_duplicates(subset=["rate_date", "currency_code"], keep="last").copy()
    df["rate_date"] = pd.to_datetime(df["rate_date"], errors="coerce").dt.date
    df["nominal"] = pd.to_numeric(df["nominal"], errors="coerce").fillna(1).astype(int)
    df["rate_to_rub"] = pd.to_numeric(df["rate_to_rub"], errors="coerce").round(4)
    return df.dropna(subset=["rate_date", "currency_code", "currency_name", "rate_to_rub"])

def load_to_raw():
    engine = get_engine()
    for name in ["stores", "products", "sales", "inventory", "plan_sales"]:
        load_raw_table(engine, read_csv(name), f"{name}_raw", f"{name}.csv")

def load_currency_rates_to_raw():
    engine = get_engine()
    fetch_currency_rates_history().to_sql(
        "currency_rates_raw",
        engine,
        schema="raw",
        if_exists="append",
        index=False,
        method="multi",
    )

def transform_to_stg():
    engine = get_engine()
    stores = transform_stores(read_csv("stores"))
    products = transform_products(read_csv("products"))
    sales = transform_sales(read_csv("sales"))
    inventory = transform_inventory(read_csv("inventory"))
    plan_sales = transform_plan_sales(read_csv("plan_sales"))

    sales = sales[sales["store_id"].isin(stores["store_id"]) & sales["product_id"].isin(products["product_id"])].copy()
    inventory = inventory[inventory["store_id"].isin(stores["store_id"]) & inventory["product_id"].isin(products["product_id"])].copy()
    plan_sales = plan_sales[plan_sales["store_id"].isin(stores["store_id"])].copy()

    write_clean(engine, stores, "stores_clean")
    write_clean(engine, products, "products_clean")
    write_clean(engine, sales, "sales_clean")
    write_clean(engine, inventory, "inventory_clean")
    write_clean(engine, plan_sales, "plan_sales_clean")

def transform_currency_rates_to_stg():
    engine = get_engine()
    query = """
        SELECT rate_date, currency_code, currency_name, nominal, rate_to_rub, source_url
        FROM raw.currency_rates_raw
    """
    currency_rates = transform_currency_rates(pd.read_sql(query, engine))
    write_clean(engine, currency_rates, "currency_rates_clean")

def upsert_dm_sales():
    with get_engine().begin() as conn:
        conn.execute(text("""
            INSERT INTO dm.dm_sales (
                sale_id, sale_date, sale_month, store_id, product_id, category, quantity,
                revenue, total_cost, profit, sales_channel, updated_at
            )
            SELECT sale_id, sale_date, sale_month, store_id, product_id, category, quantity,
                   revenue, total_cost, profit, sales_channel, CURRENT_TIMESTAMP
            FROM stg.sales_clean
            ON CONFLICT (sale_id) DO UPDATE SET
                sale_date = EXCLUDED.sale_date,
                sale_month = EXCLUDED.sale_month,
                store_id = EXCLUDED.store_id,
                product_id = EXCLUDED.product_id,
                category = EXCLUDED.category,
                quantity = EXCLUDED.quantity,
                revenue = EXCLUDED.revenue,
                total_cost = EXCLUDED.total_cost,
                profit = EXCLUDED.profit,
                sales_channel = EXCLUDED.sales_channel,
                updated_at = CURRENT_TIMESTAMP;
        """))

def upsert_dm_stores():
    with get_engine().begin() as conn:
        conn.execute(text("""
            INSERT INTO dm.dm_stores (
                store_id, store_name, city, region, format, opening_date,
                store_area_sqm, employees_count, updated_at
            )
            SELECT
                store_id, store_name, city, region, format, opening_date,
                store_area_sqm, employees_count, CURRENT_TIMESTAMP
            FROM stg.stores_clean
            ON CONFLICT (store_id) DO UPDATE SET
                store_name = EXCLUDED.store_name,
                city = EXCLUDED.city,
                region = EXCLUDED.region,
                format = EXCLUDED.format,
                opening_date = EXCLUDED.opening_date,
                store_area_sqm = EXCLUDED.store_area_sqm,
                employees_count = EXCLUDED.employees_count,
                updated_at = CURRENT_TIMESTAMP;
        """))

def upsert_dm_products():
    with get_engine().begin() as conn:
        conn.execute(text("""
            INSERT INTO dm.dm_products (
                product_id, stock_code, product_name, category, subcategory,
                brand, supplier, unit_cost, unit_price, uom, is_active, updated_at
            )
            SELECT
                product_id, stock_code, product_name, category, subcategory,
                brand, supplier, unit_cost, unit_price, uom, is_active, CURRENT_TIMESTAMP
            FROM stg.products_clean
            ON CONFLICT (product_id) DO UPDATE SET
                stock_code = EXCLUDED.stock_code,
                product_name = EXCLUDED.product_name,
                category = EXCLUDED.category,
                subcategory = EXCLUDED.subcategory,
                brand = EXCLUDED.brand,
                supplier = EXCLUDED.supplier,
                unit_cost = EXCLUDED.unit_cost,
                unit_price = EXCLUDED.unit_price,
                uom = EXCLUDED.uom,
                is_active = EXCLUDED.is_active,
                updated_at = CURRENT_TIMESTAMP;
        """))

def upsert_dm_inventory():
    with get_engine().begin() as conn:
        conn.execute(text("""
            INSERT INTO dm.dm_inventory (
                inventory_date, store_id, product_id, stock_qty, stock_value,
                reorder_point, days_of_cover, stock_status, updated_at
            )
            SELECT inventory_date, store_id, product_id, stock_qty, stock_value,
                   reorder_point, days_of_cover, stock_status, CURRENT_TIMESTAMP
            FROM stg.inventory_clean
            ON CONFLICT (inventory_date, store_id, product_id) DO UPDATE SET
                stock_qty = EXCLUDED.stock_qty,
                stock_value = EXCLUDED.stock_value,
                reorder_point = EXCLUDED.reorder_point,
                days_of_cover = EXCLUDED.days_of_cover,
                stock_status = EXCLUDED.stock_status,
                updated_at = CURRENT_TIMESTAMP;
        """))

def upsert_dm_plan_sales():
    with get_engine().begin() as conn:
        conn.execute(text("""
            INSERT INTO dm.dm_plan_sales (
                plan_month, store_id, category, plan_revenue, plan_profit, plan_qty, updated_at
            )
            SELECT plan_month, store_id, category, plan_revenue, plan_profit, plan_qty, CURRENT_TIMESTAMP
            FROM stg.plan_sales_clean
            ON CONFLICT (plan_month, store_id, category) DO UPDATE SET
                plan_revenue = EXCLUDED.plan_revenue,
                plan_profit = EXCLUDED.plan_profit,
                plan_qty = EXCLUDED.plan_qty,
                updated_at = CURRENT_TIMESTAMP;
        """))

def upsert_dm_currency_rates():
    with get_engine().begin() as conn:
        conn.execute(text("""
            INSERT INTO dm.dm_currency_rates (
                rate_date, currency_code, currency_name, nominal, rate_to_rub, source_url, updated_at
            )
            SELECT
                rate_date, currency_code, currency_name, nominal, rate_to_rub, source_url, CURRENT_TIMESTAMP
            FROM stg.currency_rates_clean
            ON CONFLICT (rate_date, currency_code) DO UPDATE SET
                currency_name = EXCLUDED.currency_name,
                nominal = EXCLUDED.nominal,
                rate_to_rub = EXCLUDED.rate_to_rub,
                source_url = EXCLUDED.source_url,
                updated_at = CURRENT_TIMESTAMP;
        """))
