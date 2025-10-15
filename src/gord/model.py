import os
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel
from typing import Type, List, Optional
from langchain_core.tools import BaseTool
from langchain_core.messages import AIMessage
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from gord.prompts import DEFAULT_SYSTEM_PROMPT
from gord import metrics

llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY"),
    timeout=60,
)

class _MetricsCallback(BaseCallbackHandler):
    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        try:
            out = response.llm_output or {}
            usage = out.get("token_usage") or out.get("usage") or {}
            prompt_tokens = (
                usage.get("prompt_tokens")
                or usage.get("input_tokens")
                or usage.get("promptTokens")
            )
            completion_tokens = (
                usage.get("completion_tokens")
                or usage.get("output_tokens")
                or usage.get("completionTokens")
            )
            total_tokens = usage.get("total_tokens") or usage.get("totalTokens")
            if isinstance(prompt_tokens, int):
                metrics.increment("openai_prompt_tokens", prompt_tokens)
            if isinstance(completion_tokens, int):
                metrics.increment("openai_completion_tokens", completion_tokens)
            if isinstance(total_tokens, int):
                metrics.increment("openai_total_tokens", total_tokens)
            elif isinstance(prompt_tokens, int) and isinstance(completion_tokens, int):
                metrics.increment("openai_total_tokens", prompt_tokens + completion_tokens)
        except Exception:
            # Do not fail the run if usage metadata shape changes
            pass

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

  runnable = llm
  if output_schema:
      runnable = llm.with_structured_output(output_schema)
  elif tools:
      runnable = llm.bind_tools(tools)
  
  chain = prompt_template | runnable
  metrics.increment('openai', 1)
  cb = _MetricsCallback()
  return chain.invoke({"prompt": prompt}, config={"callbacks": [cb]})
