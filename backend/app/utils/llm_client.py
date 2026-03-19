"""
LLM Client
Provides OpenAI-format API calls.
"""

import json
import re
from typing import Optional, Dict, Any, List

from..config import Config
from.retry import retry_with_backoff


def get_available_validators() -> List[Dict[str, Any]]:
    """Return metadata about all configured validators (without API keys).

    Always includes the primary model (index 1). Validators 2 and 3 are
    included only when their API key, base URL, and model are all set.
    """
    validators = [{
        "index": 1,
        "model": Config.LLM_MODEL_NAME or "gpt-4o-mini",
        "label": "Primary (Report Writer)",
        "configured": bool(Config.LLM_API_KEY),
    }]
    labels = {2: "Validator 2", 3: "Validator 3"}
    for idx in [2, 3]:
        key = getattr(Config, f'LLM_VALIDATOR_{idx}_API_KEY', '') or ''
        url = getattr(Config, f'LLM_VALIDATOR_{idx}_BASE_URL', '') or ''
        model = getattr(Config, f'LLM_VALIDATOR_{idx}_MODEL_NAME', '') or ''
        configured = bool(key.strip() and url.strip() and model.strip())
        validators.append({
            "index": idx,
            "model": model.strip() if configured else "",
            "label": labels[idx],
            "configured": configured,
        })
    return validators


def get_validator_clients(validator_indices: Optional[List[int]] = None) -> List["LLMClient"]:
    """Return list of configured validator LLM clients.

    Args:
        validator_indices: Which validators to include (1=primary, 2, 3).
            If None, includes all configured validators (legacy behaviour).
    """
    all_configs = {
        1: lambda: LLMClient(),
    }
    for idx in [2, 3]:
        key = getattr(Config, f'LLM_VALIDATOR_{idx}_API_KEY', '') or ''
        url = getattr(Config, f'LLM_VALIDATOR_{idx}_BASE_URL', '') or ''
        model = getattr(Config, f'LLM_VALIDATOR_{idx}_MODEL_NAME', '') or ''
        if key.strip() and url.strip() and model.strip():
            # Capture variables in closure
            all_configs[idx] = (lambda k, u, m: lambda: LLMClient(api_key=k, base_url=u, model=m))(key, url, model)

    if validator_indices is not None:
        indices = [i for i in validator_indices if i in all_configs]
    else:
        indices = sorted(all_configs.keys())

    clients = []
    for idx in indices:
        try:
            clients.append(all_configs[idx]())
        except Exception:
            pass  # Skip misconfigured validators silently
    return clients


class LLMClient:
    """LLM client for OpenAI-compatible APIs."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model = model or Config.LLM_MODEL_NAME
        
        if not self.api_key:
            raise ValueError("LLM_API_KEY not yet configured")
        
        from openai import OpenAI
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None
    ) -> str:
        """
        Send a chat completion request.
        
        Args:
            messages: Message list
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            response_format: Response format (e.g. JSON mode)
            
        Returns:
            Response text
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if response_format:
            kwargs["response_format"] = response_format
        
        response = self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        # Some models (e.g. MiniMax M2.5) include <think> content in response; remove it
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        return content
    
    @retry_with_backoff(max_retries=3, initial_delay=1.0)
    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        Send a chat request and return parsed JSON.
        
        Args:
            messages: Message list
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            
        Returns:
            Parsed JSON object
        """
        response = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"}
        )
        # Strip markdown code fences if present
        cleaned_response = response.strip()
        cleaned_response = re.sub(r'^```(?:json)?\s*\n?', '', cleaned_response, flags=re.IGNORECASE)
        cleaned_response = re.sub(r'\n?```\s*$', '', cleaned_response)
        cleaned_response = cleaned_response.strip()

        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            raise ValueError(f"LLM response is not valid JSON format: {cleaned_response}")

