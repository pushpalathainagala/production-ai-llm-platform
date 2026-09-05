import time

from google import genai

from app.config import settings


client = genai.Client(api_key=settings.LLM_API_KEY)


def ask_gemini(question: str) -> str:
    max_retries = 3

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=question,
            )

            if not response.text:
                raise RuntimeError("LLM returned an empty response")

            return response.text

        except Exception as exc:
            if attempt == max_retries - 1:
                raise RuntimeError(
                    f"LLM request failed after {max_retries} attempts"
                ) from exc

            time.sleep(2 ** attempt)