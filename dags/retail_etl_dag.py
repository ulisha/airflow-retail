from datetime import datetime
from airflow import DAG
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.providers.standard.operators.python import PythonOperator
from retail_etl_pipeline import (
    load_currency_rates_to_raw,
    load_to_raw,
    transform_currency_rates_to_stg,
    transform_to_stg,
    upsert_dm_currency_rates,
    upsert_dm_inventory,
    upsert_dm_plan_sales,
    upsert_dm_products,
    upsert_dm_sales,
    upsert_dm_stores,
)

with DAG(
    dag_id="retail_etl_pipeline",
    description="Retail ETL pipeline",
    start_date=datetime(2026, 3, 31),
    schedule="0 6,12,18 * * *",
    catchup=False,
    tags=["retail", "etl"],
) as dag:

    truncate_stg = SQLExecuteQueryOperator(
        task_id="truncate_stg",
        conn_id="retail_postgres",
        sql="""
        TRUNCATE TABLE
            stg.sales_clean,
            stg.stores_clean,
            stg.products_clean,
            stg.inventory_clean,
            stg.plan_sales_clean,
            stg.currency_rates_clean
        RESTART IDENTITY CASCADE;
        """,
    )

    task_load_to_raw = PythonOperator(task_id="load_to_raw", python_callable=load_to_raw)
    task_load_currency_rates_to_raw = PythonOperator(
        task_id="load_currency_rates_to_raw",
        python_callable=load_currency_rates_to_raw,
    )
    task_transform_to_stg = PythonOperator(task_id="transform_to_stg", python_callable=transform_to_stg)
    task_transform_currency_rates_to_stg = PythonOperator(
        task_id="transform_currency_rates_to_stg",
        python_callable=transform_currency_rates_to_stg,
    )
    task_upsert_dm_stores = PythonOperator(task_id="upsert_dm_stores", python_callable=upsert_dm_stores)
    task_upsert_dm_products = PythonOperator(task_id="upsert_dm_products", python_callable=upsert_dm_products)
    task_upsert_dm_sales = PythonOperator(task_id="upsert_dm_sales", python_callable=upsert_dm_sales)
    task_upsert_dm_inventory = PythonOperator(task_id="upsert_dm_inventory", python_callable=upsert_dm_inventory)
    task_upsert_dm_plan_sales = PythonOperator(task_id="upsert_dm_plan_sales", python_callable=upsert_dm_plan_sales)
    task_upsert_dm_currency_rates = PythonOperator(
        task_id="upsert_dm_currency_rates",
        python_callable=upsert_dm_currency_rates,
    )

    truncate_stg >> task_load_to_raw >> task_transform_to_stg
    truncate_stg >> task_load_currency_rates_to_raw >> task_transform_currency_rates_to_stg >> task_upsert_dm_currency_rates
    task_transform_to_stg >> [task_upsert_dm_stores, task_upsert_dm_products]
    task_upsert_dm_stores >> [task_upsert_dm_sales, task_upsert_dm_inventory, task_upsert_dm_plan_sales]
    task_upsert_dm_products >> [task_upsert_dm_sales, task_upsert_dm_inventory, task_upsert_dm_plan_sales]
