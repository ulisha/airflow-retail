from app.services.llm import generate_insight

def ask_llm(prompt: str) -> str:
    return generate_insight(prompt)
