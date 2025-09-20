"""Simple LLM integration utilities.

This module provides a tiny adapter to call an LLM for review/help tasks.
It prefers the Hugging Face Inference API when `HF_TOKEN` is available in env
and `settings.huggingface_model` is set. The implementation is intentionally
minimal — it's a place to expand later with OpenAI/Anthropic/Gemini adapters.
"""
from __future__ import annotations

import os
import json
from typing import Optional
import requests

from ..core.config import settings


def call_llm(prompt: str, model: Optional[str] = None, max_tokens: int = 512) -> str:
    """Call an LLM and return the text response.

    Current behavior:
    - If HF_TOKEN env var is present and model resolves, call HF Inference API
      using `requests` (synchronous). Returns the textual output if available.
    - Otherwise raise NotImplementedError to indicate no model configured.
    """
    model = model or settings.huggingface_model
    hf_token = os.getenv('HF_TOKEN')
    if not model:
        raise NotImplementedError('No model configured in settings.huggingface_model')

    if hf_token:
        url = f'https://api-inference.huggingface.co/models/{model}'
        headers = {
            'Authorization': f'Bearer {hf_token}',
            'Accept': 'application/json',
        }
        payload = {
            'inputs': prompt,
            'parameters': {'max_new_tokens': max_tokens},
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f'HF inference failed: {resp.status_code} {resp.text}')
        # Hugging Face can return a list of dicts or a dict depending on model
        data = resp.json()
        # Try common shapes
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return data[0].get('generated_text', str(data))
        if isinstance(data, dict):
            # some models return {'generated_text': '...'} or {'text': '...'}
            return data.get('generated_text') or data.get('text') or json.dumps(data)
        return str(data)

    raise NotImplementedError('No HF_TOKEN found and no other LLM adapter implemented')


def summarize_mapping_for_review(mapping: dict) -> str:
    """Create a short prompt summarizing mapping for LLM review.

    This is a helper to prepare a concise prompt; it's intentionally simple.
    """
    lines = [f"{k}: {v}" for k, v in mapping.items()]
    txt = "\n".join(lines[:200])
    prompt = f"Please review the following anonymization mapping and indicate potential false positives or entries requiring human review:\n\n{txt}\n\nProvide a short JSON list of tokens that look suspicious."
    return prompt
