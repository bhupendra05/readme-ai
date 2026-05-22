"""Generate README content using an LLM."""
from __future__ import annotations

import os
from abc import ABC, abstractmethod

from readme_ai.analyzer import RepoContext


def _build_prompt(ctx: RepoContext, style: str, improve: bool) -> str:
    parts = [
        f"Repository: {ctx.name}",
        f"Primary language: {ctx.primary_language or 'unknown'}",
    ]
    if ctx.languages:
        parts.append(f"Languages detected: {', '.join(ctx.languages)}")
    if ctx.frameworks:
        parts.append(f"Frameworks/libraries: {', '.join(ctx.frameworks)}")
    if ctx.package_name:
        parts.append(f"Package name: {ctx.package_name}")
    if ctx.package_version:
        parts.append(f"Version: {ctx.package_version}")
    if ctx.description:
        parts.append(f"Package description: {ctx.description}")
    if ctx.entry_points:
        parts.append(f"Entry points: {', '.join(ctx.entry_points)}")
    if ctx.dependencies:
        top_deps = ctx.dependencies[:20]
        parts.append(f"Key dependencies: {', '.join(top_deps)}")
    parts.append(f"Has tests: {ctx.has_tests}")
    parts.append(f"Has Docker: {ctx.has_docker}")
    parts.append(f"Has CI/CD: {ctx.has_ci}")
    if ctx.has_license:
        parts.append(f"License: {ctx.license_type or 'yes'}")
    if ctx.git_remote:
        parts.append(f"Git remote: {ctx.git_remote}")
    if ctx.recent_commits:
        parts.append("Recent commits:\n" + "\n".join(f"  {c}" for c in ctx.recent_commits[:5]))
    if ctx.file_tree:
        parts.append(f"File structure:\n```\n{ctx.file_tree}\n```")
    for fname, content in list(ctx.key_files.items())[:3]:
        parts.append(f"\n--- {fname} (excerpt) ---\n```\n{content[:1500]}\n```")

    context_block = "\n".join(parts)

    style_instructions = {
        "standard": (
            "Write a comprehensive, professional README.md. Include: "
            "project title with badges, one-line description, Features section (bullet list), "
            "Installation, Usage with code examples, Project structure, Contributing, License."
        ),
        "minimal": (
            "Write a clean, minimal README.md. Include: "
            "title, short description (1-2 sentences), quick install command, "
            "one usage example, license badge. Keep it under 60 lines."
        ),
        "detailed": (
            "Write a highly detailed README.md for a developer audience. Include: "
            "title with badges, description, Motivation/Why section, Features, "
            "Architecture overview, Installation (multiple methods), Configuration (env vars table), "
            "Usage with multiple examples, API reference if applicable, "
            "Project structure with explanations, Contributing guide, Roadmap, FAQ, License."
        ),
    }

    if improve and ctx.existing_readme:
        task = (
            f"Improve and rewrite this existing README:\n\n```markdown\n{ctx.existing_readme}\n```\n\n"
            f"Make it more professional, complete, and compelling. "
            f"Use the repository analysis below as additional context."
        )
    else:
        task = (
            f"Generate a README.md for the repository described below. "
            f"{style_instructions.get(style, style_instructions['standard'])}"
        )

    return (
        f"{task}\n\n"
        f"Repository analysis:\n{context_block}\n\n"
        f"Output ONLY the raw Markdown content. No explanations, no code fences around the whole output."
    )


SYSTEM_PROMPT = (
    "You are an expert technical writer who creates compelling, professional GitHub README files. "
    "Your READMEs are clear, well-structured, and help developers quickly understand and use the project. "
    "Always use proper Markdown. Include relevant badge URLs (shields.io). "
    "Be specific — use actual package names, real commands, real file names from the context provided."
)


class LLMGenerator(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        ...


class OpenAIGenerator(LLMGenerator):
    def __init__(self, model: str = "gpt-4o"):
        try:
            import openai
        except ImportError:
            raise ImportError("Run: pip install openai")
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")
        self._client = openai.OpenAI(api_key=api_key)
        self._model = model

    def generate(self, prompt: str) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=4096,
            temperature=0.4,
        )
        return resp.choices[0].message.content


class AnthropicGenerator(LLMGenerator):
    def __init__(self, model: str = "claude-3-5-sonnet-20241022"):
        try:
            import anthropic
        except ImportError:
            raise ImportError("Run: pip install anthropic")
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def generate(self, prompt: str) -> str:
        resp = self._client.messages.create(
            model=self._model,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
        )
        return resp.content[0].text


class OllamaGenerator(LLMGenerator):
    def __init__(self, model: str = "llama3.2"):
        import requests
        self._model = model
        self._base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        self._requests = requests

    def generate(self, prompt: str) -> str:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {"num_predict": 4096, "temperature": 0.4},
        }
        resp = self._requests.post(f"{self._base_url}/api/chat", json=payload, timeout=180)
        resp.raise_for_status()
        return resp.json()["message"]["content"]


def build_generator(backend: str, model: str | None = None) -> LLMGenerator:
    backends = {
        "openai": (OpenAIGenerator, "gpt-4o"),
        "anthropic": (AnthropicGenerator, "claude-3-5-sonnet-20241022"),
        "ollama": (OllamaGenerator, "llama3.2"),
    }
    if backend not in backends:
        raise ValueError(f"Unknown backend: {backend}")
    cls, default = backends[backend]
    return cls(model or default)


def generate_readme(ctx: RepoContext, backend: str, model: str | None, style: str, improve: bool) -> str:
    gen = build_generator(backend, model)
    prompt = _build_prompt(ctx, style, improve)
    return gen.generate(prompt)
