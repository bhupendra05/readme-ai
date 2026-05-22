# readme-ai

> Point it at any repo — it analyzes the code, detects the stack, reads your commits, and generates a polished GitHub README in seconds.

![Python](https://img.shields.io/badge/python-3.10+-blue) ![License](https://img.shields.io/badge/license-MIT-green)

## How It Works

1. **Analyze** — Scans your repo: file tree, languages, frameworks, dependencies, entry points, git history
2. **Prompt** — Builds a rich context prompt with real data extracted from your code
3. **Generate** — Sends to your chosen LLM (GPT-4o, Claude 3.5, or local Ollama)
4. **Output** — Renders a Markdown preview or writes directly to `README.md`

## Features

- **Smart repo analysis** — detects Python, TypeScript, Rust, Go, Solidity, Dart, and 10+ other languages
- **Framework recognition** — identifies FastAPI, React, Next.js, Anchor, PyTorch, Hardhat, and more
- **Three styles** — `standard`, `minimal`, `detailed`
- **Improve mode** — rewrites and improves your existing README instead of starting fresh
- **Rich terminal preview** — see rendered Markdown before writing the file
- **Multiple LLM backends** — OpenAI GPT-4o, Anthropic Claude, local Ollama
- **Dry-run analyze** — inspect what context gets extracted, no LLM call needed

## Installation

```bash
git clone https://github.com/bhupendra05/readme-ai.git
cd readme-ai
pip install -e ".[all]"   # installs openai + anthropic SDKs
# or
pip install -e ".[openai]"
```

## Configuration

```bash
cp .env.example .env
# Add your API key
```

```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

## Usage

### Generate a README for the current directory

```bash
readme-ai generate .
```

### Write directly to README.md

```bash
readme-ai generate . --output README.md
```

### Different styles

```bash
# Minimal (60 lines, quick install + one example)
readme-ai generate . --style minimal --output README.md

# Detailed (full docs, API reference, FAQ, roadmap)
readme-ai generate . --style detailed --output README.md
```

### Use Claude instead of GPT-4o

```bash
readme-ai generate . --backend anthropic
readme-ai generate . --backend anthropic --model claude-3-5-sonnet-20241022
```

### Use local Ollama (no API key)

```bash
readme-ai generate . --backend ollama --model llama3.2
```

### Improve an existing README

```bash
readme-ai generate . --improve --output README.md
```

### Preview in terminal before writing

```bash
readme-ai generate . --preview --output README.md
```

### Inspect extracted context (no LLM)

```bash
readme-ai analyze .
readme-ai analyze ~/my-other-project
```

## Example Output

```
 Repository Analysis
──────────────────────────────────────────
 Name              my-project
 Primary Language  Python
 Frameworks        FastAPI, PyTorch
 Dependencies      47
 Tests             ✓
 Docker            ✓
 CI/CD             ✓
 License           MIT
 Existing README   no

Generating README (standard style) via openai…
README written to: README.md
142 lines, 4,821 characters
```

## Screenshots

![readme-ai demo](docs/demo.png)

## Supported Languages & Frameworks

**Languages:** Python, TypeScript, JavaScript, Rust, Go, Java, Kotlin, Dart, Solidity, C/C++, Ruby, Swift

**Frameworks auto-detected:** FastAPI, Flask, Django, React, Next.js, Vue, Express, NestJS, Hardhat, Anchor, PyTorch, TensorFlow, Transformers, Solana web3, Flutter, Actix, Axum, Tokio

## Project Structure

```
readme-ai/
├── readme_ai/
│   ├── cli.py        # Click CLI (generate / analyze)
│   ├── analyzer.py   # Repo analysis (language, framework, deps, git)
│   └── generator.py  # LLM prompt builder + OpenAI/Anthropic/Ollama backends
├── requirements.txt
├── setup.py
└── .env.example
```

## License

MIT © bhupendra05
