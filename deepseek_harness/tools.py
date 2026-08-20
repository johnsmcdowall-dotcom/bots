"""Tool definitions the agent can call, plus the dispatcher that executes them."""

import subprocess
from pathlib import Path

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a text file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to read."}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write text content to a file, overwriting it if it exists.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to write."},
                    "content": {"type": "string", "description": "Text content to write."},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List the entries in a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path.", "default": "."}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Run a shell command and return its stdout/stderr/exit code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to run."}
                },
                "required": ["command"],
            },
        },
    },
]


def read_file(path: str) -> str:
    return Path(path).read_text()


def write_file(path: str, content: str) -> str:
    Path(path).write_text(content)
    return f"wrote {len(content)} bytes to {path}"


def list_dir(path: str = ".") -> str:
    entries = sorted(p.name + ("/" if p.is_dir() else "") for p in Path(path).iterdir())
    return "\n".join(entries)


def run_shell(command: str) -> str:
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, timeout=60
    )
    return (
        f"exit_code: {result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


DISPATCH = {
    "read_file": read_file,
    "write_file": write_file,
    "list_dir": list_dir,
    "run_shell": run_shell,
}


def call_tool(name: str, arguments: dict) -> str:
    if name not in DISPATCH:
        return f"error: unknown tool {name!r}"
    try:
        return str(DISPATCH[name](**arguments))
    except Exception as exc:  # noqa: BLE001 - surface any tool failure back to the model
        return f"error: {exc}"
