import asyncio
import re
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def parse_natural_language(user_input, tool_map):
    # Normalize input
    text = user_input.lower()

    # Keyword-to-tool mapping
    keywords = {
        "add": "add",
        "plus": "add",
        "subtract": "subtract",
        "minus": "subtract",
        "multiply": "multiply",
        "times": "multiply",
        "divide": "divide",
        "over": "divide",
        "power": "power",
        "to the power of": "power",
        "sqrt": "sqrt",
        "square root": "sqrt",
        "cosine": "cosine",
        "cos": "cosine",
        "sine": "sine",
        "sin": "sine",
        "tangent": "tangent",
        "tan": "tangent",
        "acos": "acos",
        "asin": "asin",
        "recent": "get_recent_calculations",
        "history": "get_recent_calculations",
        "log": "get_recent_calculations",
    }

    # Try matching keywords
    found_tool = None
    for key_phrase, tool_name in keywords.items():
        if key_phrase in text and tool_name in tool_map:
            found_tool = tool_name
            break

    # Fallback: try first word
    if not found_tool:
        first_word = text.split()[0]
        if first_word in tool_map:
            found_tool = first_word

    if not found_tool:
        return None, None

    # Get tool schema
    props = tool_map[found_tool].inputSchema.get("properties", {})
    required = tool_map[found_tool].inputSchema.get("required", [])

    # Extract numbers
    numbers = re.findall(r"[-+]?\d*\.?\d+", text)

    # If tool requires no input
    if not required:
        return found_tool, {}

    # If tool requires inputs but none found
    if len(numbers) < len(required):
        return None, None

    # Parse arguments
    args = {}
    try:
        for i, key in enumerate(required):
            expected_type = props[key]["type"]
            val = numbers[i]
            if expected_type == "integer":
                args[key] = int(float(val))
            elif expected_type == "number":
                args[key] = float(val)
            else:
                args[key] = val
    except (IndexError, ValueError):
        return None, None

    return found_tool, args


server_params = StdioServerParameters(
    command="python",
    args=["server.py"],
    env=None
)


async def ask_qwen_for_tool(prompt: str, tool_map) -> tuple[str, dict] | tuple[None, None]:
    tool_descriptions = []
    for name, tool in tool_map.items():
        desc = tool.description or "No description"
        params = tool.inputSchema.get("properties", {})
        param_str = ", ".join(
            f"{k}: {v.get('type', 'any')}" for k, v in params.items()
        )
        tool_descriptions.append(f"{name}({param_str}) – {desc}")

    tool_description_text = "\n".join(tool_descriptions)

    system_prompt = build_system_prompt(tool_map)

    try:
        import httpx
        timeout = httpx.Timeout(15.0)  # Wait up to 15 seconds for Qwen to respond
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": "qwen3:1.7b",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "stream": False,
                    "format": "json"
                }
            )

            raw = response.json()
            content = raw.get("message", {}).get("content", "")

            if not content.strip():
                print("Warning: Qwen returned empty response.")
                return None, None

            try:
                parsed = json.loads(content)
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON from Qwen output: {e}")
                print(f"Raw content:\n{content}\n")
                return None, None

            tool = parsed.get("tool")
            args = parsed.get("args", {})

            if tool in tool_map:
                return tool, args

    except Exception as e:
        print(f"Failed to call Qwen: {e}")

    return None, None


def build_system_prompt(tool_map):
    tools_info = {
        name: {
            "description": t.description,
            "parameters": t.inputSchema
        }
        for name, t in tool_map.items()
    }

    return (
        "You are an AI assistant that can call tools to help the user.\n"
        "When the user asks something, return a JSON object with:\n"
        "- 'tool': the name of the tool to call\n"
        "- 'args': the dictionary of arguments to pass\n"
        "Only respond with a JSON object, nothing else.\n"
        "Here are the available tools:\n"
        + json.dumps(tools_info, indent=2)
    )


async def run():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            tool_map = {t.name: t for t in tools.tools}

            print("\n=== Available MCP Tools ===")
            for tool in tool_map.values():
                desc = tool.description or "(no description)"
                print(f"- {tool.name}: {desc}")
            print("============================\n")

            print("Type commands like 'add 5 3' or 'recent'. Type 'quit' to exit.\n")

            while True:
                user_input = input("Enter command or natural language math expression (or 'quit'): ").strip()
                if user_input.lower() in ("quit", "exit"):
                    print("Bye!")
                    break

                # Intercept tool listing requests
                if user_input.strip().lower() in ("tools", "list tools", "what tools do you have", "available tools", "list available tools"):
                    print("\n=== Available MCP Tools ===")
                    for tool in tool_map.values():
                        desc = tool.description or "(no description)"
                        print(f"- {tool.name}: {desc}")
                    print("============================\n")
                    continue

                # Special case: detect weather queries and extract location
                if any(k in user_input.lower() for k in ["weather", "forecast", "temperature", "rain", "snow", "sunny"]) and "weather" in tool_map:
                    # Extract location for weather tool input
                    m = re.search(r"weather\s*(?:in|at|for)?\s*([a-zA-Z\s]+)", user_input.lower())
                    if m:
                        location = m.group(1).strip()
                    else:
                        location = "Nashville"  # default location if none found
                    args = {"location": location}
                    tool_name = "weather"
                    print(f"DEBUG: Calling weather tool with args: {args}")
                else:
                    tool_name, args = await ask_qwen_for_tool(user_input, tool_map)
                    if not tool_name or args is None:
                        # fallback to keyword parsing
                        tool_name, args = parse_natural_language(user_input, tool_map)

                if not tool_name or args is None:
                    print("Sorry, I couldn't understand that. Please try again.")
                    continue

                print(f"Calling tool '{tool_name}' with arguments: {args}")
                result = await session.call_tool(tool_name, args)

                print("\n=== Calculation Result ===")
                print(f"{tool_name}({', '.join(f'{k}={v}' for k, v in args.items())}) = {result}")
                print("==========================\n")


if __name__ == "__main__":
    asyncio.run(run())
