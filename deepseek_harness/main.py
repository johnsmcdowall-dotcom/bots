"""Minimal agentic chat harness for the DeepSeek API (OpenAI-compatible)."""

import argparse
import json
import os
import sys

from openai import OpenAI

from deepseek_harness.tools import TOOL_SCHEMAS, call_tool

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
SYSTEM_PROMPT = (
    "You are a helpful coding assistant with access to tools for reading/writing "
    "files, listing directories, and running shell commands. Use them when needed."
)


def build_client() -> OpenAI:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        sys.exit("DEEPSEEK_API_KEY is not set (see .env.example).")
    return OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)


def run_turn(client: OpenAI, model: str, messages: list, use_tools: bool) -> str:
    """Send messages to the model, resolving any tool calls, and return the final reply."""
    while True:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_SCHEMAS if use_tools else None,
        )
        message = response.choices[0].message
        messages.append(message.model_dump(exclude_none=True))

        if not message.tool_calls:
            return message.content or ""

        for tool_call in message.tool_calls:
            args = json.loads(tool_call.function.arguments or "{}")
            result = call_tool(tool_call.function.name, args)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                }
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="DeepSeek chat/agent harness")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="deepseek-chat or deepseek-reasoner")
    parser.add_argument("--no-tools", action="store_true", help="Disable tool calling")
    parser.add_argument("prompt", nargs="*", help="One-shot prompt; omit for an interactive REPL")
    args = parser.parse_args()

    client = build_client()
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    use_tools = not args.no_tools

    if args.prompt:
        messages.append({"role": "user", "content": " ".join(args.prompt)})
        print(run_turn(client, args.model, messages, use_tools))
        return

    print(f"DeepSeek harness ({args.model}). Ctrl+C or 'exit' to quit.")
    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if user_input in ("exit", "quit"):
            break
        if not user_input:
            continue
        messages.append({"role": "user", "content": user_input})
        reply = run_turn(client, args.model, messages, use_tools)
        print(reply)


if __name__ == "__main__":
    main()
