"""
llm_client.py
-------------
Unified BYOK (Bring Your Own Key) Multi-Provider AI Engine for CodeAuditAI.

Supported Providers:
1. Google AI Studio (Free Tier, Default) - gemini-2.5-flash, gemini-3.1-flash-lite, gemini-1.5-pro
2. Anthropic Claude - claude-3-7-sonnet-latest, claude-3-5-sonnet-latest, claude-3-5-haiku-latest
3. OpenAI / Codex - gpt-4o, gpt-4o-mini, o3-mini, o1
4. DeepSeek - deepseek-chat, deepseek-coder, deepseek-reasoner
5. GitHub Copilot / Custom OpenAI-Compatible / Local - Azure AI, Ollama, OpenRouter, vLLM
"""

import os
import re
import time
import asyncio
from typing import Any, List, Dict, Optional
import httpx
from dotenv import load_dotenv

load_dotenv()

# Preconfigured Provider Presets
PROVIDER_PRESETS = {
    "aistudio": {
        "name": "Google AI Studio (Free Tier)",
        "default_model": "gemini-3.5-flash-lite",
        "models": ["gemini-3.5-flash-lite", "gemini-flash-lite-latest", "gemini-3-flash-preview", "gemini-2.5-flash"],
        "docs_url": "https://aistudio.google.com",
        "is_free": True
    },
    "claude": {
        "name": "Anthropic Claude",
        "default_model": "claude-3-7-sonnet-latest",
        "models": ["claude-3-7-sonnet-latest", "claude-3-5-sonnet-latest", "claude-3-5-haiku-latest", "claude-3-opus-latest"],
        "docs_url": "https://console.anthropic.com",
        "is_free": False
    },
    "openai": {
        "name": "OpenAI / Codex",
        "default_model": "gpt-4o",
        "models": ["gpt-4o", "gpt-4o-mini", "o3-mini", "o1", "chatgpt-4o-latest"],
        "docs_url": "https://platform.openai.com",
        "is_free": False
    },
    "deepseek": {
        "name": "DeepSeek",
        "default_model": "deepseek-coder",
        "models": ["deepseek-coder", "deepseek-chat", "deepseek-reasoner"],
        "base_url": "https://api.deepseek.com",
        "docs_url": "https://platform.deepseek.com",
        "is_free": False
    },
    "copilot": {
        "name": "GitHub Copilot / Custom Endpoint",
        "default_model": "gpt-4o",
        "models": ["gpt-4o", "claude-3.5-sonnet", "deepseek-r1", "custom"],
        "base_url": "https://models.inference.ai.azure.com",
        "docs_url": "https://github.com/marketplace/models",
        "is_free": False
    }
}


class BYOKClientManager:
    """Manages multi-provider BYOK configurations and dispatches prompts."""

    def __init__(self):
        # Determine active provider
        self.active_provider = os.getenv("ACTIVE_PROVIDER", "aistudio").lower()
        if self.active_provider not in PROVIDER_PRESETS:
            self.active_provider = "aistudio"

        # Keys per provider
        self.keys = {
            "aistudio": os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "",
            "claude": os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY") or "",
            "openai": os.getenv("OPENAI_API_KEY") or "",
            "deepseek": os.getenv("DEEPSEEK_API_KEY") or "",
            "copilot": os.getenv("COPILOT_API_KEY") or os.getenv("CUSTOM_API_KEY") or ""
        }

        # Active models per provider
        self.models = {
            "aistudio": os.getenv("GEMINI_MODEL") or PROVIDER_PRESETS["aistudio"]["default_model"],
            "claude": os.getenv("CLAUDE_MODEL") or PROVIDER_PRESETS["claude"]["default_model"],
            "openai": os.getenv("OPENAI_MODEL") or PROVIDER_PRESETS["openai"]["default_model"],
            "deepseek": os.getenv("DEEPSEEK_MODEL") or PROVIDER_PRESETS["deepseek"]["default_model"],
            "copilot": os.getenv("COPILOT_MODEL") or PROVIDER_PRESETS["copilot"]["default_model"]
        }

        # Custom Base URLs
        self.custom_urls = {
            "deepseek": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            "copilot": os.getenv("COPILOT_BASE_URL", "https://models.inference.ai.azure.com")
        }

        # Google rate limit throttle (Free tier has ~15-30 RPM)
        self._min_gap_seconds = 2.0
        self._last_google_request = 0.0
        self._google_lock = asyncio.Lock()

    def set_provider(self, provider: str):
        p = provider.lower().strip()
        if p in PROVIDER_PRESETS:
            self.active_provider = p
            os.environ["ACTIVE_PROVIDER"] = p

    def update_key(self, provider: str, key: str):
        p = provider.lower().strip()
        if p in self.keys:
            self.keys[p] = key.strip()
            if p == "aistudio":
                os.environ["GOOGLE_API_KEY"] = key.strip()
                os.environ["GEMINI_API_KEY"] = key.strip()
            elif p == "claude":
                os.environ["ANTHROPIC_API_KEY"] = key.strip()
            elif p == "openai":
                os.environ["OPENAI_API_KEY"] = key.strip()
            elif p == "deepseek":
                os.environ["DEEPSEEK_API_KEY"] = key.strip()
            elif p == "copilot":
                os.environ["COPILOT_API_KEY"] = key.strip()

    def update_model(self, provider: str, model: str):
        p = provider.lower().strip()
        if p in self.models:
            self.models[p] = model.strip()

    def update_base_url(self, provider: str, url: str):
        p = provider.lower().strip()
        if p in self.custom_urls:
            self.custom_urls[p] = url.strip()

    def get_config_summary(self) -> Dict[str, Any]:
        """Returns non-sensitive status of all BYOK providers."""
        providers_status = {}
        for p, preset in PROVIDER_PRESETS.items():
            key = self.keys.get(p, "")
            has_key = bool(key and len(key) > 5)
            masked = f"{key[:6]}...{key[-4:]}" if has_key else "Not Configured"
            providers_status[p] = {
                "name": preset["name"],
                "has_key": has_key,
                "masked_key": masked,
                "current_model": self.models.get(p, preset["default_model"]),
                "supported_models": preset["models"],
                "docs_url": preset["docs_url"],
                "is_free": preset["is_free"],
                "is_active": p == self.active_provider
            }

        return {
            "active_provider": self.active_provider,
            "active_model": self.models.get(self.active_provider, ""),
            "providers": providers_status
        }

    # -------------------------------------------------------------------------
    # Provider Invocation Dispatchers
    # -------------------------------------------------------------------------

    async def _invoke_google_aistudio(self, prompt: str, max_retries: int = 3) -> str:
        """Invokes Google AI Studio Gemini API with rate-limit handling and free model fallbacks."""
        key = self.keys["aistudio"]
        if not key:
            raise RuntimeError(
                "No Google AI Studio key configured. Get a free key at https://aistudio.google.com "
                "and paste it in the BYOK Settings modal."
            )

        from langchain_google_genai import ChatGoogleGenerativeAI
        models_to_try = [self.models["aistudio"]] + [m for m in PROVIDER_PRESETS["aistudio"]["models"] if m != self.models["aistudio"]]

        last_error = None
        for model in models_to_try:
            client = ChatGoogleGenerativeAI(model=model, temperature=0.2, google_api_key=key, max_retries=0)

            for attempt in range(1, max_retries + 1):
                # Rate limit throttle for free tier
                async with self._google_lock:
                    now = time.monotonic()
                    wait = self._min_gap_seconds - (now - self._last_google_request)
                    if wait > 0:
                        await asyncio.sleep(wait)
                    self._last_google_request = time.monotonic()

                try:
                    resp = await client.ainvoke(prompt)
                    text = _extract_content(resp.content)
                    if model != self.models["aistudio"]:
                        self.models["aistudio"] = model
                    return text
                except Exception as e:
                    err = str(e)
                    last_error = err
                    if "429" in err or "RESOURCE_EXHAUSTED" in err:
                        retry_match = re.search(r"retry\s*(?:in|delay['\"]?\s*:\s*['\"]?)(\d+)", err, re.IGNORECASE)
                        wait_sec = int(retry_match.group(1)) if retry_match else 4 * attempt
                        if wait_sec > 15:
                            print(f"⚠️ [Google AI Studio] {model} daily limit reached (retry delay: {wait_sec}s). Falling back immediately to next free model...")
                            break
                        print(f"⏳ [Google AI Studio] 429 on {model}. Retrying in {wait_sec}s...")
                        await asyncio.sleep(wait_sec)
                        continue
                    elif any(k in err for k in ["404", "NOT_FOUND", "503", "UNAVAILABLE", "no longer available"]):
                        print(f"⚠️ [Google AI Studio] {model} temporarily unavailable. Falling back...")
                        break
                    else:
                        raise

        raise RuntimeError(f"Google AI Studio invocation failed: {last_error}")

    async def _invoke_anthropic_claude(self, prompt: str) -> str:
        """Invokes Anthropic Claude API via direct async HTTPS."""
        key = self.keys["claude"]
        if not key:
            raise RuntimeError("No Anthropic Claude API key configured. Provide key in BYOK Settings.")

        model = self.models["claude"]
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": model,
            "max_tokens": 4096,
            "temperature": 0.2,
            "messages": [{"role": "user", "content": prompt}]
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("content", [])
                return "".join(c.get("text", "") for c in content if c.get("type") == "text")
            else:
                raise RuntimeError(f"Anthropic Claude API returned HTTP {resp.status_code}: {resp.text}")

    async def _invoke_openai_compatible(self, base_url: str, key: str, model: str, prompt: str, provider_name: str) -> str:
        """Generic OpenAI-compatible chat completion dispatcher (OpenAI, DeepSeek, Copilot)."""
        if not key:
            raise RuntimeError(f"No API key configured for {provider_name}. Enter key in BYOK Settings.")

        clean_url = base_url.rstrip("/")
        if not clean_url.endswith("/chat/completions"):
            if not clean_url.endswith("/v1"):
                clean_url = f"{clean_url}/v1/chat/completions"
            else:
                clean_url = f"{clean_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "temperature": 0.2,
            "messages": [{"role": "user", "content": prompt}]
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(clean_url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "")
                return ""
            else:
                raise RuntimeError(f"{provider_name} API returned HTTP {resp.status_code}: {resp.text}")

    async def safe_invoke(self, prompt: str, max_retries: int = 3) -> str:
        """Routes prompt to the actively configured BYOK provider."""
        provider = self.active_provider

        if provider == "aistudio":
            return await self._invoke_google_aistudio(prompt, max_retries=max_retries)
        elif provider == "claude":
            return await self._invoke_anthropic_claude(prompt)
        elif provider == "openai":
            return await self._invoke_openai_compatible(
                base_url="https://api.openai.com/v1",
                key=self.keys["openai"],
                model=self.models["openai"],
                prompt=prompt,
                provider_name="OpenAI"
            )
        elif provider == "deepseek":
            return await self._invoke_openai_compatible(
                base_url=self.custom_urls.get("deepseek", "https://api.deepseek.com"),
                key=self.keys["deepseek"],
                model=self.models["deepseek"],
                prompt=prompt,
                provider_name="DeepSeek"
            )
        elif provider == "copilot":
            return await self._invoke_openai_compatible(
                base_url=self.custom_urls.get("copilot", "https://models.inference.ai.azure.com"),
                key=self.keys["copilot"],
                model=self.models["copilot"],
                prompt=prompt,
                provider_name="GitHub Copilot / Custom"
            )
        else:
            # Default fallback to Google AI Studio
            return await self._invoke_google_aistudio(prompt, max_retries=max_retries)

    async def test_provider(self, provider: str, key: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
        """Tests provider connectivity and key validity with a lightweight ping."""
        p = provider.lower().strip()
        test_key = key.strip() if key else self.keys.get(p, "")
        test_model = model.strip() if model else self.models.get(p, PROVIDER_PRESETS[p]["default_model"])

        if not test_key:
            return {"status": "error", "message": f"Please provide an API key for {PROVIDER_PRESETS.get(p, {}).get('name', p)}"}

        start = time.monotonic()
        try:
            if p == "aistudio":
                from langchain_google_genai import ChatGoogleGenerativeAI
                llm = ChatGoogleGenerativeAI(model=test_model, google_api_key=test_key, temperature=0.1)
                res = await llm.ainvoke("Ping test. Reply with 'OK'.")
                reply = _extract_content(res.content).strip()
            elif p == "claude":
                url = "https://api.anthropic.com/v1/messages"
                headers = {"x-api-key": test_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
                payload = {"model": test_model, "max_tokens": 10, "messages": [{"role": "user", "content": "Ping"}]}
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    if resp.status_code != 200:
                        return {"status": "error", "message": f"Anthropic error {resp.status_code}: {resp.text}"}
                    reply = "OK"
            elif p in {"openai", "deepseek", "copilot"}:
                base = "https://api.openai.com/v1" if p == "openai" else self.custom_urls.get(p, "https://api.deepseek.com")
                reply = await self._invoke_openai_compatible(base, test_key, test_model, "Ping", p)

            latency = round((time.monotonic() - start) * 1000, 1)
            return {
                "status": "success",
                "provider": p,
                "model": test_model,
                "latency_ms": latency,
                "message": f"Connection verified successfully! ({latency}ms)"
            }
        except Exception as e:
            return {
                "status": "error",
                "provider": p,
                "message": str(e)
            }


def _extract_content(content: Any) -> str:
    """Defensively extracts text from LLM response representations."""
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                parts.append(part["text"])
        return "".join(parts)
    if isinstance(content, str):
        return content
    return str(content)


# Global singleton instance
byok_manager = BYOKClientManager()

# Backward compatible module-level functions
async def safe_invoke(prompt: str, max_retries: int = 3) -> str:
    return await byok_manager.safe_invoke(prompt, max_retries=max_retries)

def get_message_text(content: Any) -> str:
    return _extract_content(content)
