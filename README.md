# bots

## DeepSeek harness

A minimal agentic chat harness for the DeepSeek API (OpenAI-compatible). It
supports tool calling (read/write files, list directories, run shell
commands) so the model can act as an agent, not just a chatbot.

### Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then edit .env and set DEEPSEEK_API_KEY
export $(cat .env | xargs)
```

### Usage

Interactive REPL:

```bash
python -m deepseek_harness.main
```

One-shot prompt:

```bash
python -m deepseek_harness.main "list the files in this repo"
```

Use the reasoning model, or disable tool calling:

```bash
python -m deepseek_harness.main --model deepseek-reasoner "..."
python -m deepseek_harness.main --no-tools "..."
```
