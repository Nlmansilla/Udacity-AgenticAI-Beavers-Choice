"""Load application settings and construct the configured model."""

import os

from dotenv import load_dotenv
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider


def create_model() -> OpenAIChatModel:
    """Build the OpenAI-compatible model configured for the exercise."""
    load_dotenv()
    return OpenAIChatModel(
        os.getenv("UDACITY_MODEL_NAME"),
        provider=OpenAIProvider(
            base_url="https://openai.vocareum.com/v1",
            api_key=os.getenv("UDACITY_OPENAI_API_KEY"),
        ),
    )
