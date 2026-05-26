from datetime import date
import re

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, field_validator
from app.services.analytics import inventory_summary, monthly_summary, plan_fact_summary

app = FastAPI(
    title="Retail LLM Analytics Assistant",
    description="LLM service for retail KPI interpretation over DataLens-ready marts.",
    version="1.0.0",
)

class MonthRequest(BaseModel):
    month: str

    @field_validator("month")
    @classmethod
    def validate_month(cls, value: str) -> str:
        if not re.fullmatch(r"\d{4}-\d{2}", value):
            raise ValueError("Месяц должен быть в формате YYYY-MM")
        return value

class InventoryRequest(BaseModel):
    report_date: str

    @field_validator("report_date")
    @classmethod
    def validate_report_date(cls, value: str) -> str:
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("Дата отчета должна быть в формате YYYY-MM-DD") from exc
        return value

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <!doctype html>
    <html lang="ru">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Retail LLM Analytics Assistant</title>
      <style>
        :root {
          color-scheme: light;
          --bg: #f5f7fb;
          --surface: #ffffff;
          --surface-soft: #f8fafc;
          --ink: #111827;
          --muted: #667085;
          --line: #d9e2ec;
          --brand: #0f766e;
          --brand-dark: #115e59;
          --accent: #2563eb;
          --danger: #b42318;
          --shadow: 0 18px 45px rgba(15, 23, 42, .08);
        }
        * { box-sizing: border-box; }
        body {
          margin: 0;
          min-height: 100vh;
          font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
          background:
            linear-gradient(180deg, #eef6f5 0, rgba(245, 247, 251, 0) 360px),
            var(--bg);
          color: var(--ink);
        }
        button, input, select { font: inherit; }
        button { cursor: pointer; }
        main { max-width: 1180px; margin: 0 auto; padding: 28px 20px 40px; }
        header {
          display: grid;
          grid-template-columns: minmax(0, 1fr) auto;
          gap: 24px;
          align-items: end;
          margin-bottom: 22px;
        }
        .eyebrow {
          margin: 0 0 8px;
          color: var(--brand-dark);
          font-size: 13px;
          font-weight: 800;
          letter-spacing: .04em;
          text-transform: uppercase;
        }
        h1 { margin: 0; font-size: clamp(28px, 4vw, 44px); line-height: 1.05; letter-spacing: 0; }
        p { color: var(--muted); line-height: 1.55; }
        .lead { max-width: 760px; margin: 12px 0 0; font-size: 16px; }
        .status {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 9px 12px;
          border: 1px solid rgba(15, 118, 110, .22);
          border-radius: 999px;
          background: rgba(255, 255, 255, .72);
          color: var(--brand-dark);
          font-size: 13px;
          font-weight: 700;
          white-space: nowrap;
        }
        .status-dot { width: 8px; height: 8px; border-radius: 50%; background: #12b76a; }
        .layout {
          display: grid;
          grid-template-columns: 360px minmax(0, 1fr);
          gap: 18px;
          align-items: start;
        }
        .panel {
          background: rgba(255, 255, 255, .92);
          border: 1px solid var(--line);
          border-radius: 8px;
          box-shadow: var(--shadow);
        }
        .sidebar { padding: 16px; position: sticky; top: 18px; }
        .tabs {
          display: grid;
          gap: 8px;
          margin-bottom: 18px;
        }
        .tab {
          width: 100%;
          display: grid;
          grid-template-columns: 34px minmax(0, 1fr);
          gap: 10px;
          align-items: center;
          min-height: 66px;
          padding: 10px;
          border: 1px solid var(--line);
          border-radius: 8px;
          background: var(--surface);
          color: var(--ink);
          text-align: left;
        }
        .tab[aria-selected="true"] {
          border-color: rgba(15, 118, 110, .45);
          background: #ecfdf8;
        }
        .tab-icon {
          display: grid;
          place-items: center;
          width: 34px;
          height: 34px;
          border-radius: 8px;
          background: #e8f5f3;
          color: var(--brand-dark);
          font-weight: 900;
        }
        .tab-title { display: block; font-size: 14px; font-weight: 800; }
        .tab-subtitle {
          display: block;
          margin-top: 2px;
          color: var(--muted);
          font-size: 12px;
          line-height: 1.35;
        }
        .form-block { border-top: 1px solid var(--line); padding-top: 16px; }
        h2 { margin: 0 0 12px; font-size: 20px; letter-spacing: 0; }
        label { display: block; margin-bottom: 7px; color: #344054; font-size: 13px; font-weight: 700; }
        input {
          width: 100%;
          min-height: 44px;
          border: 1px solid #cbd5e1;
          border-radius: 8px;
          padding: 9px 11px;
          background: white;
          color: var(--ink);
        }
        input:focus {
          outline: 3px solid rgba(37, 99, 235, .16);
          border-color: var(--accent);
        }
        .button-row { display: grid; grid-template-columns: 1fr 44px; gap: 10px; margin-top: 12px; }
        .primary, .icon-button, .ghost-button {
          min-height: 44px;
          border-radius: 8px;
          border: 1px solid transparent;
          font-weight: 800;
        }
        .primary { background: var(--brand); color: white; }
        .primary:hover { background: var(--brand-dark); }
        .primary:disabled { opacity: .66; cursor: wait; }
        .icon-button {
          display: grid;
          place-items: center;
          background: #eef2f7;
          border-color: var(--line);
          color: #344054;
        }
        .ghost-button {
          min-height: 36px;
          padding: 0 10px;
          background: white;
          border-color: var(--line);
          color: #344054;
          font-size: 13px;
        }
        .examples { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
        .main-panel { overflow: hidden; }
        .toolbar {
          display: flex;
          justify-content: space-between;
          gap: 12px;
          align-items: center;
          padding: 16px 18px;
          border-bottom: 1px solid var(--line);
          background: rgba(248, 250, 252, .82);
        }
        .toolbar h2 { margin: 0; }
        .actions { display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-end; }
        .content { padding: 18px; }
        .answer-card {
          min-height: 220px;
          padding: 18px;
          border: 1px solid var(--line);
          border-radius: 8px;
          background: white;
        }
        .answer-meta {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-bottom: 12px;
        }
        .pill {
          display: inline-flex;
          align-items: center;
          min-height: 26px;
          padding: 4px 9px;
          border-radius: 999px;
          background: #eef2f7;
          color: #344054;
          font-size: 12px;
          font-weight: 800;
        }
        .pill.good { background: #ecfdf3; color: #027a48; }
        .pill.warn { background: #fff6ed; color: #b54708; }
        pre {
          white-space: pre-wrap;
          overflow-wrap: anywhere;
          margin: 0;
          font: 15px/1.62 Arial, sans-serif;
          color: var(--ink);
        }
        .kpi-grid {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 10px;
          margin: 16px 0;
        }
        .kpi {
          min-height: 86px;
          padding: 12px;
          border: 1px solid var(--line);
          border-radius: 8px;
          background: var(--surface-soft);
        }
        .kpi span { display: block; color: var(--muted); font-size: 12px; font-weight: 700; }
        .kpi strong {
          display: block;
          margin-top: 8px;
          overflow-wrap: anywhere;
          font-size: 20px;
          line-height: 1.1;
        }
        .data-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 12px;
          margin-top: 16px;
        }
        .data-box {
          border: 1px solid var(--line);
          border-radius: 8px;
          background: white;
          overflow: hidden;
        }
        .data-box h3 {
          margin: 0;
          padding: 11px 12px;
          border-bottom: 1px solid var(--line);
          background: var(--surface-soft);
          font-size: 14px;
        }
        .data-list { list-style: none; margin: 0; padding: 6px 0; }
        .data-list li {
          display: flex;
          justify-content: space-between;
          gap: 10px;
          padding: 8px 12px;
          color: #344054;
          font-size: 13px;
          border-top: 1px solid #eef2f7;
        }
        .data-list li:first-child { border-top: 0; }
        .history { margin-top: 16px; }
        .history h3 { margin: 0 0 10px; font-size: 14px; }
        .history-list { display: grid; gap: 8px; }
        .history-item {
          width: 100%;
          padding: 9px 10px;
          border: 1px solid var(--line);
          border-radius: 8px;
          background: white;
          color: #344054;
          text-align: left;
          font-size: 13px;
        }
        .empty {
          color: var(--muted);
          font-size: 14px;
        }
        .error { color: var(--danger); }
        .hidden { display: none; }
        @media (max-width: 920px) {
          header { grid-template-columns: 1fr; align-items: start; }
          .layout { grid-template-columns: 1fr; }
          .sidebar { position: static; }
        }
        @media (max-width: 640px) {
          main { padding: 20px 14px 28px; }
          .toolbar { align-items: stretch; flex-direction: column; }
          .actions { justify-content: stretch; }
          .actions button { flex: 1 1 auto; }
          .kpi-grid, .data-grid { grid-template-columns: 1fr; }
        }
      </style>
    </head>
    <body>
      <main>
        <header>
          <div>
            <p class="eyebrow">Retail analytics</p>
            <h1>Retail LLM Analytics Assistant</h1>
            <p class="lead">Интерпретация витрин продаж, план/факт и остатков для демонстрации рядом с DataLens. Выберите сценарий, получите управленческий вывод и проверьте цифры, на которых он построен.</p>
          </div>
          <div class="status"><span class="status-dot"></span><span>Сервис готов</span></div>
        </header>

        <section class="layout">
          <aside class="panel sidebar">
            <nav class="tabs" aria-label="Сценарии анализа">
              <button class="tab" type="button" data-scenario="monthly" aria-selected="true">
                <span class="tab-icon">M</span>
                <span><span class="tab-title">Итоги месяца</span><span class="tab-subtitle">Выручка, прибыль, магазины и категории</span></span>
              </button>
              <button class="tab" type="button" data-scenario="plan" aria-selected="false">
                <span class="tab-icon">P</span>
                <span><span class="tab-title">План/факт</span><span class="tab-subtitle">Отклонения, слабые зоны и причины</span></span>
              </button>
              <button class="tab" type="button" data-scenario="inventory" aria-selected="false">
                <span class="tab-icon">S</span>
                <span><span class="tab-title">Остатки</span><span class="tab-subtitle">Дефицит, излишки и риск заморозки</span></span>
              </button>
            </nav>

            <form class="form-block" id="assistant-form">
              <h2 id="form-title">Итоги месяца</h2>
              <label for="period-input" id="period-label">Месяц анализа</label>
              <input id="period-input" name="value" value="2024-12" autocomplete="off" />
              <div class="button-row">
                <button class="primary" id="submit-button" type="submit">Сформировать вывод</button>
                <button class="icon-button" id="reset-button" type="button" title="Вернуть пример">↻</button>
              </div>
              <div class="examples" id="examples"></div>
            </form>

            <div class="history">
              <h3>Последние запросы</h3>
              <div class="history-list" id="history-list"><p class="empty">История появится после первого запроса.</p></div>
            </div>
          </aside>

          <section class="panel main-panel">
            <div class="toolbar">
              <h2>Ответ ассистента</h2>
              <div class="actions">
                <button class="ghost-button" id="copy-button" type="button">Копировать</button>
                <button class="ghost-button" id="link-button" type="button">Ссылка для DataLens</button>
                <button class="ghost-button" id="context-button" type="button">Контекст</button>
              </div>
            </div>
            <div class="content">
              <article class="answer-card">
                <div class="answer-meta" id="answer-meta">
                  <span class="pill">Сценарий: итоги месяца</span>
                  <span class="pill">Период: 2024-12</span>
                </div>
                <pre id="output">Выберите сценарий слева и нажмите "Сформировать вывод".</pre>
              </article>
              <div id="kpi-grid" class="kpi-grid hidden"></div>
              <div id="context-view" class="data-grid hidden"></div>
            </div>
          </section>
        </section>
      </main>
      <script>
        const scenarios = {
          monthly: {
            title: "Итоги месяца",
            label: "Месяц анализа",
            field: "month",
            inputType: "month",
            value: "2024-12",
            examples: ["2024-10", "2024-11", "2024-12"],
            endpoint: "/insight/monthly-summary",
            description: "итоги месяца"
          },
          plan: {
            title: "План/факт",
            label: "Месяц анализа",
            field: "month",
            inputType: "month",
            value: "2024-12",
            examples: ["2024-10", "2024-11", "2024-12"],
            endpoint: "/insight/plan-fact",
            description: "план/факт"
          },
          inventory: {
            title: "Остатки",
            label: "Дата отчета",
            field: "report_date",
            inputType: "date",
            value: "2024-12-31",
            examples: ["2024-12-15", "2024-12-24", "2024-12-31"],
            endpoint: "/insight/inventory",
            description: "остатки"
          }
        };

        let activeScenario = "monthly";
        let lastResponse = null;
        let contextVisible = false;

        const output = document.querySelector("#output");
        const form = document.querySelector("#assistant-form");
        const input = document.querySelector("#period-input");
        const formTitle = document.querySelector("#form-title");
        const periodLabel = document.querySelector("#period-label");
        const submitButton = document.querySelector("#submit-button");
        const examples = document.querySelector("#examples");
        const meta = document.querySelector("#answer-meta");
        const kpiGrid = document.querySelector("#kpi-grid");
        const contextView = document.querySelector("#context-view");
        const historyList = document.querySelector("#history-list");

        function formatMoney(value) {
          const number = Number(value || 0);
          return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(number) + " руб.";
        }

        function formatNumber(value) {
          return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 1 }).format(Number(value || 0));
        }

        function formatPct(value) {
          if (value === null || value === undefined || value === "") return "0%";
          const raw = Number(value || 0);
          const pct = Math.abs(raw) <= 1 ? raw * 100 : raw;
          return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 1 }).format(pct) + "%";
        }

        function readableValue(key, value) {
          if (value === null || value === undefined || value === "") return "нет данных";
          if (key.includes("pct")) return formatPct(value);
          if (key.includes("revenue") || key.includes("profit") || key.includes("value") || key.includes("amount")) return formatMoney(value);
          if (key.includes("qty") || key.includes("quantity") || key.includes("stock")) return formatNumber(value);
          return String(value);
        }

        function pickLabel(row) {
          return row.store_id || row.store_name || row.category || row.product_id || row.product_name || row.stock_status || "Показатель";
        }

        function pickMetric(row) {
          const key = ["revenue", "profit", "plan_revenue_pct", "stock_value", "stock_qty", "quantity"].find((name) => row[name] !== undefined);
          return key ? readableValue(key, row[key]) : "";
        }

        function renderList(title, rows) {
          if (!Array.isArray(rows) || rows.length === 0) return "";
          const items = rows.slice(0, 5).map((row) => `<li><span>${pickLabel(row)}</span><strong>${pickMetric(row)}</strong></li>`).join("");
          return `<section class="data-box"><h3>${title}</h3><ul class="data-list">${items}</ul></section>`;
        }

        function renderKpis(context) {
          const cards = [];
          const kpi = context.kpi || context.summary || {};
          if (kpi.revenue !== undefined || kpi.fact_revenue !== undefined) cards.push(["Выручка", formatMoney(kpi.revenue ?? kpi.fact_revenue)]);
          if (kpi.profit !== undefined || kpi.fact_profit !== undefined) cards.push(["Прибыль", formatMoney(kpi.profit ?? kpi.fact_profit)]);
          if (kpi.quantity !== undefined) cards.push(["Продано", formatNumber(kpi.quantity)]);
          if (kpi.plan_revenue_pct !== undefined || kpi.revenue_plan_completion_pct !== undefined) cards.push(["План по выручке", formatPct(kpi.plan_revenue_pct ?? kpi.revenue_plan_completion_pct)]);
          if (kpi.total_stock_qty !== undefined) cards.push(["Остаток", formatNumber(kpi.total_stock_qty)]);
          if (kpi.total_stock_value !== undefined) cards.push(["Стоимость остатков", formatMoney(kpi.total_stock_value)]);

          kpiGrid.innerHTML = cards.slice(0, 6).map(([label, value]) => `<div class="kpi"><span>${label}</span><strong>${value}</strong></div>`).join("");
          kpiGrid.classList.toggle("hidden", cards.length === 0);
        }

        function renderContext(context) {
          const blocks = [
            renderList("Лидеры", context.top_stores || context.top_categories),
            renderList("Зоны внимания", context.low_stores || context.worst_stores_by_plan || context.low_stock),
            renderList("Категории", context.low_categories || context.worst_categories_by_plan),
            renderList("Излишки", context.overstock)
          ].filter(Boolean);
          contextView.innerHTML = blocks.join("");
          contextView.classList.toggle("hidden", !contextVisible || blocks.length === 0);
        }

        function updateMeta(source) {
          const scenario = scenarios[activeScenario];
          const sourceClass = source === "ollama" || source === "yandex" ? "good" : source === "local_fallback" ? "warn" : "";
          const sourceText = source === "ollama" ? "Ollama" : source === "yandex" ? "YandexGPT" : source === "local_fallback" ? "Локальный fallback" : "Ожидание";
          meta.innerHTML = `
            <span class="pill">Сценарий: ${scenario.description}</span>
            <span class="pill">Период: ${input.value.trim() || scenario.value}</span>
            <span class="pill ${sourceClass}">Источник: ${sourceText}</span>
          `;
        }

        function friendlyError(message) {
          const technicalMarkers = ["psycopg2", "sqlalchemy", "connection to server", "OperationalError"];
          if (technicalMarkers.some((marker) => message.includes(marker))) {
            return "Не удалось получить данные из PostgreSQL. Проверьте, что база retail запущена, пользователь доступен, а views dm созданы через llm_analytics_assistant/sql/llm_views.sql.";
          }
          return message;
        }

        function getHistory() {
          try { return JSON.parse(localStorage.getItem("assistantHistory") || "[]"); }
          catch { return []; }
        }

        function saveHistory(item) {
          const history = getHistory().filter((entry) => entry.scenario !== item.scenario || entry.value !== item.value);
          history.unshift(item);
          localStorage.setItem("assistantHistory", JSON.stringify(history.slice(0, 5)));
          renderHistory();
        }

        function renderHistory() {
          const history = getHistory();
          if (!history.length) {
            historyList.innerHTML = '<p class="empty">История появится после первого запроса.</p>';
            return;
          }
          historyList.innerHTML = history.map((item) => `
            <button class="history-item" type="button" data-scenario="${item.scenario}" data-value="${item.value}">
              ${scenarios[item.scenario].title}: ${item.value}
            </button>
          `).join("");
        }

        function setScenario(name, value) {
          activeScenario = name;
          const scenario = scenarios[name];
          document.querySelectorAll(".tab").forEach((tab) => {
            tab.setAttribute("aria-selected", String(tab.dataset.scenario === name));
          });
          formTitle.textContent = scenario.title;
          periodLabel.textContent = scenario.label;
          input.type = scenario.inputType;
          input.value = value || scenario.value;
          examples.innerHTML = scenario.examples.map((example) => `<button class="ghost-button" type="button" data-example="${example}">${example}</button>`).join("");
          updateMeta(lastResponse?.insight_source);
        }

        async function runRequest() {
          const scenario = scenarios[activeScenario];
          const value = input.value.trim();
          if (!value) {
            output.classList.add("error");
            output.textContent = "Укажите период для анализа.";
            return;
          }
          submitButton.disabled = true;
          output.classList.remove("error");
          output.textContent = "Готовлю аналитический вывод...";
          updateMeta("loading");
          const controller = new AbortController();
          const timeoutId = window.setTimeout(() => controller.abort(), 70000);
          try {
            const response = await fetch(scenario.endpoint, {
              method: "POST",
              headers: {"Content-Type": "application/json"},
              body: JSON.stringify({[scenario.field]: value}),
              signal: controller.signal
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || "Ошибка запроса");
            lastResponse = data;
            output.textContent = data.insight || JSON.stringify(data, null, 2);
            renderKpis(data.context || {});
            renderContext(data.context || {});
            updateMeta(data.insight_source);
            saveHistory({scenario: activeScenario, value});
          } catch (error) {
            output.classList.add("error");
            output.textContent = error.name === "AbortError"
              ? "Запрос выполняется слишком долго. Проверьте, что Ollama запущена, или повторите запрос: локальные данные доступны, но модель не ответила за 70 секунд."
              : friendlyError(error.message);
            kpiGrid.classList.add("hidden");
            contextView.classList.add("hidden");
          } finally {
            window.clearTimeout(timeoutId);
            submitButton.disabled = false;
          }
        }

        form.addEventListener("submit", (event) => {
          event.preventDefault();
          runRequest();
        });

        document.querySelector("#reset-button").addEventListener("click", () => {
          input.value = scenarios[activeScenario].value;
          updateMeta(lastResponse?.insight_source);
        });

        document.querySelector("#copy-button").addEventListener("click", async () => {
          await navigator.clipboard.writeText(output.textContent);
        });

        document.querySelector("#link-button").addEventListener("click", async () => {
          const scenario = scenarios[activeScenario];
          const url = new URL(scenario.endpoint, window.location.origin);
          url.searchParams.set(scenario.field, input.value.trim() || scenario.value);
          await navigator.clipboard.writeText(url.toString());
        });

        document.querySelector("#context-button").addEventListener("click", () => {
          contextVisible = !contextVisible;
          if (lastResponse?.context) renderContext(lastResponse.context);
        });

        document.addEventListener("click", (event) => {
          const tab = event.target.closest(".tab");
          if (tab) setScenario(tab.dataset.scenario);

          const example = event.target.closest("[data-example]");
          if (example) {
            input.value = example.dataset.example;
            updateMeta(lastResponse?.insight_source);
          }

          const historyItem = event.target.closest(".history-item");
          if (historyItem) {
            setScenario(historyItem.dataset.scenario, historyItem.dataset.value);
            runRequest();
          }
        });

        const params = new URLSearchParams(window.location.search);
        if (params.has("report_date")) setScenario("inventory", params.get("report_date"));
        else if (params.has("month")) setScenario("monthly", params.get("month"));
        else setScenario("monthly");
        renderHistory();
      </script>
    </body>
    </html>
    """

@app.post("/insight/monthly-summary")
def get_monthly_summary(payload: MonthRequest):
    try:
        return monthly_summary(payload.month)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/insight/plan-fact")
def get_plan_fact(payload: MonthRequest):
    try:
        return plan_fact_summary(payload.month)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/insight/inventory")
def get_inventory(payload: InventoryRequest):
    try:
        return inventory_summary(payload.report_date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/insight/monthly-summary")
def get_monthly_summary_link(month: str = Query(..., pattern=r"^\d{4}-\d{2}$", examples=["2024-12"])):
    return get_monthly_summary(MonthRequest(month=month))

@app.get("/insight/plan-fact")
def get_plan_fact_link(month: str = Query(..., pattern=r"^\d{4}-\d{2}$", examples=["2024-12"])):
    return get_plan_fact(MonthRequest(month=month))

@app.get("/insight/inventory")
def get_inventory_link(report_date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$", examples=["2024-12-31"])):
    return get_inventory(InventoryRequest(report_date=report_date))
