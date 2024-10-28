import time
import asyncio
import aiohttp
import ssl
import certifi
from typing import Any, Annotated, Optional, List
import openai

class Model:
  """Class for storing any single language model."""

  def __init__(
      self,
      model_name: str,
      temperature: float = 0.5,
      max_tokens: int = 2048,
      show_responses: bool = False,
      show_prompts: bool = False,
  ) -> None:
    """Initializes a model."""
    self.model_name = model_name
    self.temperature = temperature
    self.max_tokens = max_tokens
    self.show_responses = show_responses
    self.show_prompts = show_prompts
    if model_name.lower().startswith('openai:'):
      openai.api_type = "azure"
      openai.api_base = "https://xxx-openai-service.openai.azure.com/"
      openai.api_version = "2023-05-15"
      openai.api_key = ""
      self.engine_name = "gpt-35-turbo-4k-0613"
    # print(self.model)
    elif model_name.lower().startswith('llama'):
      self.model = self.load_llama(model_name)
  

  # Call ChatGPT with the given prompt, asynchronously.
  async def call_chatgpt_async(self, session, prompt: str, temperature, max_tokens, max_attempts, retry_interval):
    payload = {
        'model': self.model_name[7:],
        'messages': [
            {"role": "user", "content": prompt}
        ]
    }
    result, num_attempts = "", 0 
    while not result and num_attempts < max_attempts:
      try:
        async with session.post(
          url=f'{openai.api_base}openai/deployments/{self.engine_name}/chat/completions?api-version={openai.api_version}',
          headers={"Content-Type": "application/json", "api-key": f"{openai.api_key}", "temperature": str(temperature or self.temperature), "max_tokens": str(max_tokens or self.max_tokens)},
          json=payload,
          ssl=ssl.create_default_context(cafile=certifi.where())
        ) as response:
          response = await response.json()
        if "error" in response:
          print(f"OpenAI request failed with error {response['error']}")
        else:
          result = response['choices'][0]['message']['content']
      except Exception as e:
        print("Encounter the following error when calling api: ", e)
        time.sleep(retry_interval)
      num_attempts += 1
    
    return result

  # Call chatGPT for all the given prompts in parallel.
  async def call_chatgpt_bulk(self, prompts, temperature, max_tokens, max_attempts, retry_interval):
    async with aiohttp.ClientSession() as session, asyncio.TaskGroup() as tg:
      responses = [tg.create_task(self.call_chatgpt_async(session, prompt, temperature, max_tokens, max_attempts, retry_interval)) for prompt in prompts]
    return responses

  def generate_batched(
      self,
      prompt_batch: List[str],
      do_debug: bool = False,
      temperature: Optional[float] = None,
      max_tokens: Optional[int] = None,
      max_attempts: int = 1000,
      timeout: int = 60,
      retry_interval: int = 10,
  ) -> List[str]:
    """Generates a response to a prompt."""
    # self.model.max_attempts = 1
    # self.model.retry_interval = 0
    # self.model.timeout = timeout
    # self.model.deployment_name = 'gpt4'
    prompt_batch = [prompt for prompt in prompt_batch]
    gen_temp = temperature or self.temperature
    gen_max_tokens = max_tokens or self.max_tokens
    response, num_attempts = '', 0

    response = asyncio.run(self.call_chatgpt_bulk(prompt_batch, gen_temp, gen_max_tokens, max_attempts, retry_interval))
    response = [tmp.result() for tmp in response]

    return response