import subprocess
import json
import os
from typing import Dict, Any

SOURCE_FILENAME = "only_mypy_correct.py" # For simplicity I have set it to point to `only_mypy_correct.py` file
                                         # but it can be changed to point to the other example which is `disagreement.py` 
OUTPUT_JSON = "type_checkers_output.json"

TYPE_CHECKERS = {
    "mypy": ["mypy"],
    "pyrefly": ["pyrefly", "check"], 
    "zuban": ["zuban", "check"],
    "ty": ["ty", "check"]
}

def run_command(command_args: list, filename: str) -> str:
    """
    Runs a subprocess and returns the combined stdout/stderr.
    """
    try:
        full_command = command_args + [filename]
        
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            check=False
        )
        
        output = result.stdout
        if result.stderr:
            output += "\n[STDERR]\n" + result.stderr
            
        return output.strip()
        
    except FileNotFoundError:
        return f"Error: Command '{command_args[0]}' not found in system PATH."
    except Exception as e:
        return f"Execution Error: {str(e)}"

def main():
    if not os.path.exists(SOURCE_FILENAME):
        print(f"Error: The file '{SOURCE_FILENAME}' was not found.")
        return

    with open(SOURCE_FILENAME, "r", encoding="utf-8") as f:
        code_content = f.read()

    results: Dict[str, Any] = {
        "analyzed_file": SOURCE_FILENAME,
        "source_code": code_content,
        "outputs": {}
    }

    print(f"Analyzing {SOURCE_FILENAME}...")

    for tool_name, command in TYPE_CHECKERS.items():
        print(f"Running {tool_name}...")
        output = run_command(command, SOURCE_FILENAME)
        results["outputs"][tool_name] = output

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)

    print(f"\nSuccess! Results saved to '{OUTPUT_JSON}'")

if __name__ == "__main__":
    main()
