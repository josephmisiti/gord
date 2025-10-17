import os
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel
from typing import Type, List, Optional
from langchain_core.tools import BaseTool
from langchain_core.messages import AIMessage
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

# Optional providers
try:
    from langchain_anthropic import ChatAnthropic  # type: ignore
except Exception:  # pragma: no cover
    ChatAnthropic = None  # type: ignore

try:
    from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore
except Exception:  # pragma: no cover
    ChatGoogleGenerativeAI = None  # type: ignore

from gord.prompts import DEFAULT_SYSTEM_PROMPT
from gord import metrics
from gord import settings

class _MetricsCallback(BaseCallbackHandler):
    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        try:
            out = response.llm_output or {}
            usage = out.get("token_usage") or out.get("usage") or out.get("usage_metadata") or {}
            prompt_tokens = (
                usage.get("prompt_tokens")
                or usage.get("input_tokens")
                or usage.get("promptTokens")
                or usage.get("prompt_token_count")
                or usage.get("promptTokenCount")
            )
            completion_tokens = (
                usage.get("completion_tokens")
                or usage.get("output_tokens")
                or usage.get("completionTokens")
                or usage.get("candidates_token_count")
                or usage.get("outputTokenCount")
            )
            total_tokens = usage.get("total_tokens") or usage.get("totalTokens")
            # Generic counters
            if isinstance(prompt_tokens, int):
                metrics.increment("llm_prompt_tokens", prompt_tokens)
            if isinstance(completion_tokens, int):
                metrics.increment("llm_completion_tokens", completion_tokens)
            if isinstance(total_tokens, int):
                metrics.increment("llm_total_tokens", total_tokens)
            elif isinstance(prompt_tokens, int) and isinstance(completion_tokens, int):
                metrics.increment("llm_total_tokens", prompt_tokens + completion_tokens)

            # Provider-specific mirrors
            provider = settings.LLM_PROVIDER
            if isinstance(prompt_tokens, int):
                metrics.increment(f"{provider}_prompt_tokens", prompt_tokens)
            if isinstance(completion_tokens, int):
                metrics.increment(f"{provider}_completion_tokens", completion_tokens)
            if isinstance(total_tokens, int):
                metrics.increment(f"{provider}_total_tokens", total_tokens)
            elif isinstance(prompt_tokens, int) and isinstance(completion_tokens, int):
                metrics.increment(f"{provider}_total_tokens", prompt_tokens + completion_tokens)
        except Exception:
            # Do not fail the run if usage metadata shape changes
            pass


def _build_llm():
    provider = settings.LLM_PROVIDER
    temperature = 0
    timeout = 60
    if provider == 'openai':
        return ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=temperature,
            api_key=settings.OPENAI_API_KEY,
            timeout=timeout,
        )
    if provider == 'grok':
        # Use OpenAI-compatible interface with custom base_url
        return ChatOpenAI(
            model=settings.GROK_MODEL,
            temperature=temperature,
            api_key=settings.XAI_API_KEY,
            base_url=settings.XAI_BASE_URL,
            timeout=timeout,
        )
    if provider == 'anthropic':
        if ChatAnthropic is None:
            raise RuntimeError("langchain-anthropic is not installed.")
        # Ensure env is set as some libs read from environment
        if settings.ANTHROPIC_API_KEY:
            os.environ.setdefault('ANTHROPIC_API_KEY', settings.ANTHROPIC_API_KEY)
        return ChatAnthropic(
            model=settings.ANTHROPIC_MODEL,
            temperature=temperature,
            timeout=timeout,
        )
    if provider == 'gemini':
        if ChatGoogleGenerativeAI is None:
            raise RuntimeError("langchain-google-genai is not installed.")
        if not settings.GOOGLE_API_KEY:
            raise RuntimeError("GOOGLE_API_KEY is not set for Gemini.")
        return ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            temperature=temperature,
            google_api_key=settings.GOOGLE_API_KEY,
            timeout=timeout,
        )
    # Fallback
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=temperature,
        api_key=settings.OPENAI_API_KEY,
        timeout=timeout,
    )

def call_llm(
    prompt: str,
    system_prompt: Optional[str] = None,
    output_schema: Optional[Type[BaseModel]] = None,
    tools: Optional[List[BaseTool]] = None,
) -> AIMessage:
    final_system_prompt = system_prompt if system_prompt else DEFAULT_SYSTEM_PROMPT

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", final_system_prompt),
        ("user", "{prompt}")
    ])

    llm = _build_llm()

    runnable = llm
    if output_schema:
        try:
            runnable = llm.with_structured_output(output_schema)
        except Exception:
            # Fall back to plain text if provider doesn't support structured output
            runnable = llm
    elif tools:
        try:
            runnable = llm.bind_tools(tools)
        except Exception:
            runnable = llm

    chain = prompt_template | runnable
    # Count provider-specific call
    provider = settings.LLM_PROVIDER
    metrics.increment(provider, 1)
    cb = _MetricsCallback()
    return chain.invoke({"prompt": prompt}, config={"callbacks": [cb]})
