import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from openai import OpenAI
from app.config import settings
from app.prompts import SYSTEM_PROMPT

def get_yandex_client() -> OpenAI:
    if not settings.yandex_api_key:
        raise ValueError("Не задан YANDEX_API_KEY в llm_analytics_assistant/.env")
    if "<folder_id>" in settings.yandex_model:
        raise ValueError("Не задан реальный folder_id в YANDEX_MODEL")
    return OpenAI(
        api_key=settings.yandex_api_key,
        base_url=settings.yandex_base_url,
        timeout=settings.llm_timeout_seconds,
    )

def generate_yandex_insight(user_prompt: str) -> str:
    client = get_yandex_client()
    headers = {"x-data-logging-enabled": "false"} if settings.disable_data_logging else None
    response = client.chat.completions.create(
        model=settings.yandex_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        extra_headers=headers,
        timeout=settings.llm_timeout_seconds,
    )
    return response.choices[0].message.content.strip()

def generate_ollama_insight(user_prompt: str) -> str:
    endpoint = f"{settings.ollama_base_url.rstrip('/')}/api/chat"
    payload = {
        "model": settings.ollama_model,
        "stream": False,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "options": {
            "temperature": 0.1,
            "top_p": 0.8,
            "num_predict": 300,
        },
    }
    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=settings.llm_timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Ollama вернула HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(
            f"Не удалось подключиться к Ollama по адресу {settings.ollama_base_url}. "
            f"Проверьте, что Ollama запущена и модель {settings.ollama_model} скачана."
        ) from exc

    content = (data.get("message") or {}).get("content", "").strip()
    if not content:
        raise RuntimeError("Ollama вернула пустой ответ")
    return content

def generate_insight(user_prompt: str) -> str:
    provider = settings.llm_provider.lower().strip()
    if provider == "ollama":
        return generate_ollama_insight(user_prompt)
    if provider == "yandex":
        return generate_yandex_insight(user_prompt)
    raise ValueError("LLM_PROVIDER должен быть ollama или yandex")
