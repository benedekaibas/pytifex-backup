import json
import os
import asyncio
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider


JSON_INPUT_FILE = "type_checkers_output.json"
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("Please set the GEMINI_API_KEY environment variable.")

provider = GoogleProvider(api_key=API_KEY)
judge_model = GoogleModel('gemini-2.5-pro', provider=provider)

judge_agent = Agent(
    judge_model,
    system_prompt=(
        "You are an expert Python Type System Judge (PEP 484). "
        "Your goal is to determine if a specific Type Checker behaved correctly given a piece of source code.\n\n"
        
        "PROTOCOL:\n"
        "1. ANALYZE THE CODE: Look for 'Overload Overlap'. If `Literal['x']` and `str` are both defined as inputs "
        "   in `@overload` signatures, they overlap because 'x' is also a str. If they return different types, "
        "   this is UNSAFE and AMBIGUOUS.\n"
        "2. JUDGE THE TOOL:\n"
        "   - If the code has this Unsafe Overlap, the tool MUST report an ERROR to be 'CORRECT'.\n"
        "   - If the code has Unsafe Overlap and the tool says 'Success' (or 0 errors), it is 'INCORRECT'.\n"
        "   - If the code is perfectly safe, then 'Success' is 'CORRECT'.\n\n"
        
        "OUTPUT FORMAT:\n"
        "Start your response with exactly 'CORRECT' or 'INCORRECT', followed by a vertical bar '|', "
        "and then a short explanation."
        "Example: CORRECT | Mypy correctly flagged the unsafe overload overlap."
    )
)

def remove_comments(source_code: str) -> str:
    """Removes comments to force the agent to analyze the code logic, not the 'EXPECTED' comments."""
    lines = [line for line in source_code.splitlines() if not line.strip().startswith("#")]
    return "\n".join(lines)

async def evaluate_single_tool(tool_name: str, output: str, clean_code: str) -> dict:
    """Evaluates a single tool and returns the structured result."""
    prompt = (
        f"### Source Code (No Comments):\n```python\n{clean_code}\n```\n\n"
        f"### Tool Name: {tool_name}\n"
        f"### Tool Output:\n{output}\n\n"
        f"### Task:\n"
        f"Does the tool output correctly reflect the safety of the code? "
        f"(Hint: Check for unsafe overload overlap between Literal and str)."
    )

    try:
        response = await judge_agent.run(prompt)
        raw_text = response.output.strip()
        
        parts = raw_text.split('|', 1)
        if len(parts) == 2:
            verdict_str = parts[0].strip().upper()
            reason = parts[1].strip()
        else:
            verdict_str = raw_text.split(' ')[0].strip().upper()
            reason = raw_text
            
        is_correct = "CORRECT" in verdict_str and "INCORRECT" not in verdict_str
        
        return {
            "tool": tool_name,
            "passed": is_correct,
            "reason": reason
        }
    except Exception as e:
        return {
            "tool": tool_name,
            "passed": False,
            "reason": f"Agent Error: {str(e)}"
        }

async def main():
    if not os.path.exists(JSON_INPUT_FILE):
        print(f"Error: {JSON_INPUT_FILE} not found.")
        return

    with open(JSON_INPUT_FILE, "r") as f:
        data = json.load(f)

    source_code = data.get("source_code", "")
    clean_code = remove_comments(source_code)
    outputs = data.get("outputs", {})
    analyzed_file = data.get("analyzed_file", "Unknown File")

    print(f"--- AI Judge: Evaluating {len(outputs)} Type Checkers ---")
    print(f"File: {analyzed_file}")
    print("Analyizing code safety...\n")

    tasks = [
        evaluate_single_tool(name, output, clean_code) 
        for name, output in outputs.items()
    ]
    results = await asyncio.gather(*tasks)

    print("="*90)
    print(f"FINAL EVALUATION REPORT: {analyzed_file}")
    print("="*90)
    print(f"{'Tool':<10} | {'Verdict':<8} | {'Reasoning'}")
    print("-" * 90)

    total_passed = 0
    for res in results:
        status = "✅ PASS" if res['passed'] else "❌ FAIL"
        if res['passed']:
            total_passed += 1
            
        reason = res['reason']
        if len(reason) > 65:
            reason = reason[:62] + "..."
            
        print(f"{res['tool']:<10} | {status:<8} | {reason}")

    print("-" * 90)
    final_score = total_passed / len(results) if results else 0.0
    print(f"Overall Accuracy of the type checkers: {final_score:.0%}")
    print("="*90)

if __name__ == "__main__":
    asyncio.run(main())
