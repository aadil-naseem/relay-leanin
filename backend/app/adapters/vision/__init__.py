"""Vision provider chain (cache -> gemini -> ollama), order from settings (section 3.4)."""

from app.adapters.vision import cache, gemini, ollama

__all__ = ["cache", "gemini", "ollama"]
