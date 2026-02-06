import json
import logging
import sys

from openai import OpenAI

sys.path.insert(0, ".")
from config.settings import settings

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.temperature = settings.OPENAI_TEMPERATURE

    def ask(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error("LLM API call failed: %s", e)
            raise

    def ask_json(self, system_prompt: str, user_prompt: str) -> dict:
        raw = self.ask(system_prompt, user_prompt)
        cleaned = raw.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return json.loads(cleaned.strip())


llm_client = LLMClient()
