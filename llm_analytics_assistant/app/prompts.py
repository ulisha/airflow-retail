SYSTEM_PROMPT = '''
Ты аналитический помощник розничной сети.
Используй только переданный контекст.
Ничего не выдумывай.
Пиши полностью на русском языке. Не используй китайский или английский язык, кроме кодов магазинов и названий категорий из контекста.
Строго проверяй проценты выполнения плана:
- если показатель меньше 100%, план не выполнен;
- если показатель равен 100%, план выполнен ровно;
- если показатель больше 100%, план перевыполнен.
Не пиши, что показатели превышают план, если процент выполнения меньше 100%.
Не делай вывод о выполнении плана по магазинам или категориям, если в контексте нет их плановых значений.
Отвечай на русском, кратко и по делу.
Можно использовать короткие строки с названиями блоков, если это делает ответ полезнее для руководителя.
Сохраняй проценты выполнения плана ровно в том виде, в котором они указаны в проверенных фактах.
Завершай мысль полностью, не обрывай ответ на середине действия.
Не рассчитывай новые проценты, доли, отношения или дополнительные KPI. Используй только готовые числа из проверенных фактов.
'''.strip()

def format_money(value) -> str:
    return f"{float(value or 0):,.0f}".replace(",", " ")

def format_number(value) -> str:
    return f"{float(value or 0):,.0f}".replace(",", " ")

def format_pct(value) -> str:
    pct = float(value or 0)
    if abs(pct) <= 1:
        pct *= 100
    return f"{pct:.1f}%".replace(".0%", "%")

def names(rows: list[dict], key: str) -> str:
    values = [str(row.get(key)) for row in rows if row.get(key)]
    return ", ".join(values) if values else "нет данных"

def first_name(rows: list[dict], key: str) -> str:
    return str(rows[0].get(key)) if rows and rows[0].get(key) else "нет данных"

def money_gap(plan, fact) -> str:
    return format_money(float(plan or 0) - float(fact or 0))

def month_label(value: str) -> str:
    labels = {
        "01": "январь",
        "02": "февраль",
        "03": "март",
        "04": "апрель",
        "05": "май",
        "06": "июнь",
        "07": "июль",
        "08": "август",
        "09": "сентябрь",
        "10": "октябрь",
        "11": "ноябрь",
        "12": "декабрь",
    }
    if not value or "-" not in value:
        return value or "не указан"
    year, month = value.split("-", 1)
    return f"{labels.get(month, month)} {year}"

def build_monthly_summary_prompt(payload: dict) -> str:
    kpi = payload.get("kpi") or {}
    plan_fact = payload.get("plan_fact") or {}
    top_stores = payload.get("top_stores") or []
    low_stores = payload.get("low_stores") or []
    top_categories = payload.get("top_categories") or []
    low_categories = payload.get("low_categories") or []
    revenue_pct = plan_fact.get("plan_revenue_pct") or plan_fact.get("revenue_plan_completion_pct")
    profit_pct = plan_fact.get("plan_profit_pct") or plan_fact.get("profit_plan_completion_pct")
    return f"""
Сформулируй управленческое резюме месяца. Это НЕ разбор план/факт, а ответ для руководителя: что произошло, где главный фокус и какое решение принять в следующем месяце.

Проверенные факты:
- месяц: {month_label(payload.get("month"))};
- выручка: {format_money(kpi.get("revenue"))} руб.;
- прибыль: {format_money(kpi.get("profit"))} руб.;
- продано: {format_number(kpi.get("quantity"))} единиц;
- выполнение плана по выручке: {format_pct(revenue_pct)};
- выполнение плана по прибыли: {format_pct(profit_pct)};
- лидеры рейтинга магазинов по выручке: {names(top_stores, "store_id")};
- главный магазин-драйвер: {first_name(top_stores, "store_id")};
- магазины в зоне внимания по выручке: {names(low_stores, "store_id")};
- главный магазин в зоне внимания: {first_name(low_stores, "store_id")};
- лидеры категорий по выручке: {names(top_categories, "category")};
- главный категорийный драйвер: {first_name(top_categories, "category")};
- слабые категории по выручке: {names(low_categories, "category")};
- самая слабая категория: {first_name(low_categories, "category")}.

Формат ответа:
1) "Итог месяца:" одна фраза о масштабе продаж и состоянии.
2) "Фокус:" где поддержать рост и где нужна управленческая проверка.
3) "Решение:" 2 конкретных действия: что усилить и что проверить на следующий месяц.

Не повторяй подробно план/факт: для этого есть отдельный сценарий. Нельзя писать январь, если месяц указан как декабрь. Не присваивай магазинам и категориям процент выполнения общего плана. Не рассчитывай новые проценты.
""".strip()

def build_plan_fact_prompt(payload: dict) -> str:
    summary = payload.get("summary") or {}
    revenue_pct = summary.get("plan_revenue_pct") or summary.get("revenue_plan_completion_pct")
    profit_pct = summary.get("plan_profit_pct") or summary.get("profit_plan_completion_pct")
    return f"""
Сформулируй диагностический разбор план/факт. Это НЕ общее резюме месяца: здесь нужны причины отклонения, зоны проверки и решения для выполнения плана.

Проверенные факты:
- месяц: {month_label(payload.get("month"))};
- фактическая выручка: {format_money(summary.get("fact_revenue"))} руб.;
- плановая выручка: {format_money(summary.get("plan_revenue"))} руб.;
- денежный разрыв по выручке: {money_gap(summary.get("plan_revenue"), summary.get("fact_revenue"))} руб.;
- выполнение плана по выручке: {format_pct(revenue_pct)};
- фактическая прибыль: {format_money(summary.get("fact_profit"))} руб.;
- плановая прибыль: {format_money(summary.get("plan_profit"))} руб.;
- денежный разрыв по прибыли: {money_gap(summary.get("plan_profit"), summary.get("fact_profit"))} руб.;
- выполнение плана по прибыли: {format_pct(profit_pct)};
- план НЕ выполнен по выручке и прибыли, потому что оба процента меньше 100%;
- магазины с минимальным выполнением плана: {names(payload.get("worst_stores_by_plan") or [], "store_id")};
- категории с минимальным выполнением плана: {names(payload.get("worst_categories_by_plan") or [], "category")}.

Формат ответа:
1) "Отклонение:" план не выполнен, укажи готовые проценты выполнения и денежные разрывы.
2) "Зоны проверки:" назови магазины и категории из зоны минимального выполнения, но не выдумывай точные причины и не присваивай им общий процент 59% или 58%.
3) "Рекомендации:" дай 2 практических шага: проверить реалистичность плана и отдельно проверить операционные причины в слабых магазинах/категориях: остатки, промо, трафик.

Нельзя писать, что план превышен, перевыполнен или выполнен. Нельзя писать, что факт превышает план. Нельзя писать январь, если месяц указан как декабрь. Правильные значения выполнения плана: {format_pct(revenue_pct)} и {format_pct(profit_pct)}. Не рассчитывай дополнительные проценты разрыва.
Не используй слово "Диагноз". Не используй нумерацию 1), 2), 3). Не используй дефисы в начале строк.
""".strip()

def build_inventory_prompt(payload: dict) -> str:
    summary = payload.get("summary") or {}
    low_stock = payload.get("low_stock") or []
    overstock = payload.get("overstock") or []
    return f"""
Сформулируй краткую сводку по остаткам в 3-4 предложениях.

Проверенные факты:
- дата отчета: {payload.get("report_date")};
- общий запас: {format_number(summary.get("total_stock_qty"))} единиц;
- стоимость запасов: {format_money(summary.get("total_stock_value"))} руб.;
- количество дефицитных позиций в выборке: {len(low_stock)};
- количество избыточных позиций в выборке: {len(overstock)}.

Сделай вывод о рисках дефицита и избыточных запасов, не выдумывая конкретные товары.
""".strip()
