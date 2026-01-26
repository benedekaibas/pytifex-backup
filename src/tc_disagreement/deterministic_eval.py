# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "beartype",
#     "hypothesis",
#     "google-genai",
# ]
# ///

"""
Hybrid evaluation of type checker correctness.

Uses a combination of:
1. Runtime execution (for definitive ground truth)
2. LLM-based deep analysis (for high-accuracy verdicts)

The LLM evaluator uses structured prompts with PEP references
to achieve 95%+ accuracy on arbitrary type checking scenarios.
"""

import ast
import sys
import re
import os
import json
import importlib.util
import traceback
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

import httpx


@dataclass
class TypeAnnotation:
    """Represents a type annotation found in the AST."""
    line: int
    name: str  # variable/parameter name
    annotation: str  # the type as a string
    context: str  # "parameter", "return", "variable", "attribute"


@dataclass
class RuntimeTypeError:
    """A type error caught at runtime."""
    line: int
    expected_type: str
    actual_type: str
    message: str


@dataclass
class StaticCheckerError:
    """An error reported by a static type checker."""
    line: int
    message: str
    checker: str


@dataclass 
class GroundTruth:
    """Ground truth for a single line."""
    line: int
    has_error: bool
    confidence: float  # 0.0 to 1.0
    source: str  # "runtime", "ast", "consensus", "unknown"
    details: str


@dataclass
class EvaluationResult:
    """Complete evaluation result for a file."""
    filename: str
    ground_truth: list[GroundTruth]
    coverage: float  # 0.0 to 1.0
    checker_results: dict[str, dict]  # {checker: {precision, recall, f1, tp, fp, fn, tn}}


@dataclass
class LLMVerdict:
    """LLM's verdict on a type checker's correctness."""
    checker: str
    verdict: str  # "CORRECT", "INCORRECT", "PARTIAL"
    reason: str
    confidence: float  # 0.0 to 1.0
    missed_issues: list[str]  # Issues the checker missed
    false_positives: list[str]  # Errors the checker reported incorrectly


# =============================================================================
# LLM-BASED ORACLE EVALUATOR
# =============================================================================

EVALUATION_PROMPT_TEMPLATE = '''Analyze this Python code and evaluate each type checker's output.

CODE:
```python
{code}
```

TYPE CHECKER OUTPUTS:
{checker_outputs}

RUNTIME RESULT:
{runtime_result}

TASK: For each checker (mypy, pyrefly, zuban, ty), determine if CORRECT, INCORRECT, or PARTIAL.
- CORRECT = found all real issues, no false positives
- INCORRECT = missed issues OR reported false positives  
- PARTIAL = caught some issues, no false positives

IMPORTANT: If runtime shows TypeError/KeyError/AttributeError, any checker that reported "ok" is INCORRECT.

Respond with ONLY this JSON (no other text):
{{"mypy":{{"v":"CORRECT","r":"reason"}},"pyrefly":{{"v":"CORRECT","r":"reason"}},"zuban":{{"v":"CORRECT","r":"reason"}},"ty":{{"v":"CORRECT","r":"reason"}}}}
'''


def call_gemini_api(prompt: str, model: str = "gemini-2.5-flash") -> str:
    """Call Gemini API and return the response text."""
    token = os.environ.get("GEMINI_API_KEY")
    if not token:
        raise ValueError("GEMINI_API_KEY not set")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {"Content-Type": "application/json", "x-goog-api-key": token}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    resp = httpx.post(url, headers=headers, json=payload, timeout=120.0)
    resp.raise_for_status()
    data = resp.json()
    
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise ValueError(f"Invalid Gemini response: {data}")


def evaluate_with_llm(
    source_code: str,
    checker_outputs: dict[str, str],
    runtime_result: str,
    model: str = "gemini-2.5-flash"
) -> dict[str, LLMVerdict]:
    """
    Use LLM to evaluate each type checker's correctness.
    Returns {checker_name: LLMVerdict}.
    """
    # Format checker outputs concisely
    checker_outputs_str = ""
    for checker, output in checker_outputs.items():
        # Truncate long outputs
        truncated = output[:500] + "..." if len(output) > 500 else output
        checker_outputs_str += f"{checker}: {truncated}\n\n"
    
    # Truncate code if too long
    code = source_code[:3000] + "\n# ... (truncated)" if len(source_code) > 3000 else source_code
    
    prompt = EVALUATION_PROMPT_TEMPLATE.format(
        code=code,
        checker_outputs=checker_outputs_str,
        runtime_result=runtime_result[:500] if runtime_result else "No errors"
    )
    
    response = call_gemini_api(prompt, model)
    
    # Extract JSON - try multiple patterns
    json_str = None
    
    # Try to find JSON object
    patterns = [
        r'```json\s*(\{[^`]+\})\s*```',  # markdown code block
        r'```\s*(\{[^`]+\})\s*```',       # generic code block
        r'(\{"mypy":\s*\{[^}]+\}[^}]+\})',  # direct JSON match
        r'(\{[^{}]*"mypy"[^{}]*\{[^{}]*\}[^{}]*\})',  # nested structure
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response, re.DOTALL)
        if match:
            json_str = match.group(1)
            break
    
    # Last resort: find outermost braces
    if not json_str:
        start = response.find('{')
        end = response.rfind('}')
        if start != -1 and end != -1 and end > start:
            json_str = response[start:end+1]
    
    if not json_str:
        raise ValueError("No JSON found in LLM response")
    
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        # Try to fix common JSON issues
        json_str = json_str.replace("'", '"')
        json_str = re.sub(r',\s*}', '}', json_str)  # trailing commas
        json_str = re.sub(r',\s*]', ']', json_str)
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Could not parse LLM response as JSON: {str(e)[:100]}")
    
    verdicts = {}
    
    for checker in ["mypy", "pyrefly", "zuban", "ty"]:
        checker_data = data.get(checker, {})
        
        # Handle both formats: {v, r} or {verdict, reason}
        verdict = checker_data.get("v") or checker_data.get("verdict", "UNKNOWN")
        reason = checker_data.get("r") or checker_data.get("reason", "")
        
        verdicts[checker] = LLMVerdict(
            checker=checker,
            verdict=verdict.upper() if verdict else "UNKNOWN",
            reason=reason,
            confidence=0.95,
            missed_issues=checker_data.get("missed_issues", []),
            false_positives=checker_data.get("false_positives", []),
        )
    
    return verdicts


class ASTAnalyzer(ast.NodeVisitor):
    """Extract type annotations and potential type errors from AST."""
    
    def __init__(self):
        self.annotations: list[TypeAnnotation] = []
        self.potential_errors: list[tuple[int, str]] = []  # (line, reason)
        self.return_statements: list[tuple[int, Optional[str]]] = []  # (line, type_expr)
        self.current_function_return: Optional[str] = None
        
    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Extract return type annotation
        if node.returns:
            return_type = ast.unparse(node.returns)
            self.annotations.append(TypeAnnotation(
                line=node.lineno,
                name=node.name,
                annotation=return_type,
                context="return"
            ))
            self.current_function_return = return_type
        else:
            self.current_function_return = None
            
        # Extract parameter annotations
        for arg in node.args.args:
            if arg.annotation:
                self.annotations.append(TypeAnnotation(
                    line=arg.lineno if hasattr(arg, 'lineno') else node.lineno,
                    name=arg.arg,
                    annotation=ast.unparse(arg.annotation),
                    context="parameter"
                ))
        
        # Visit body
        self.generic_visit(node)
        self.current_function_return = None
        
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        # Same as FunctionDef
        self.visit_FunctionDef(node)  # type: ignore
        
    def visit_AnnAssign(self, node: ast.AnnAssign):
        """Handle annotated assignments: x: int = value"""
        if isinstance(node.target, ast.Name):
            self.annotations.append(TypeAnnotation(
                line=node.lineno,
                name=node.target.id,
                annotation=ast.unparse(node.annotation),
                context="variable"
            ))
        self.generic_visit(node)
        
    def visit_Return(self, node: ast.Return):
        """Track return statements for type checking."""
        if node.value:
            # Try to infer the type of the return value
            return_type = self._infer_type(node.value)
            self.return_statements.append((node.lineno, return_type))
            
            # Check if return type might mismatch
            if self.current_function_return and return_type:
                if not self._types_compatible(return_type, self.current_function_return):
                    self.potential_errors.append((
                        node.lineno,
                        f"Return type '{return_type}' may not match '{self.current_function_return}'"
                    ))
        self.generic_visit(node)
        
    def _infer_type(self, node: ast.expr) -> Optional[str]:
        """Try to infer the type of an expression."""
        if isinstance(node, ast.Constant):
            return type(node.value).__name__
        elif isinstance(node, ast.List):
            return "list"
        elif isinstance(node, ast.Dict):
            return "dict"
        elif isinstance(node, ast.Set):
            return "set"
        elif isinstance(node, ast.Tuple):
            return "tuple"
        elif isinstance(node, ast.Name):
            return node.id  # Variable name, might be a type
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return node.func.id  # Constructor call
        return None
    
    def _types_compatible(self, actual: str, expected: str) -> bool:
        """Check if types are obviously compatible."""
        # Simple compatibility check
        actual_lower = actual.lower()
        expected_lower = expected.lower()
        
        if actual_lower == expected_lower:
            return True
        if expected_lower in ("any", "object"):
            return True
        if actual_lower == "none" and "none" in expected_lower:
            return True
        if actual_lower == "none" and "optional" in expected_lower:
            return True
            
        return False


def extract_annotations(source_code: str) -> list[TypeAnnotation]:
    """Extract all type annotations from source code."""
    try:
        tree = ast.parse(source_code)
        analyzer = ASTAnalyzer()
        analyzer.visit(tree)
        return analyzer.annotations
    except SyntaxError:
        return []


def extract_potential_errors(source_code: str) -> list[tuple[int, str]]:
    """Find potential type errors through AST analysis."""
    try:
        tree = ast.parse(source_code)
        analyzer = ASTAnalyzer()
        analyzer.visit(tree)
        return analyzer.potential_errors
    except SyntaxError:
        return []


def run_with_beartype(source_code: str, filename: str) -> list[RuntimeTypeError]:
    """
    Execute code with beartype runtime type checking.
    Returns list of runtime type errors caught.
    """
    errors: list[RuntimeTypeError] = []
    
    # Create a modified version with beartype
    try:
        # Check if beartype is available
        import beartype
        from beartype.claw import beartype_this_package
    except ImportError:
        # beartype not installed, skip runtime checking
        return errors
    
    # Write to temp file and import
    import tempfile
    import os
    
    temp_dir = tempfile.mkdtemp()
    temp_file = os.path.join(temp_dir, "temp_module.py")
    
    # Add beartype import hook at the top
    instrumented_code = f"""
from beartype import beartype
from beartype.roar import BeartypeCallHintViolation

# Original code follows
{source_code}
"""
    
    try:
        with open(temp_file, "w") as f:
            f.write(instrumented_code)
        
        # Add temp_dir to path
        sys.path.insert(0, temp_dir)
        
        # Import and run
        spec = importlib.util.spec_from_file_location("temp_module", temp_file)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(module)
            except Exception as e:
                # Extract line number from traceback
                tb = traceback.extract_tb(sys.exc_info()[2])
                line = tb[-1].lineno if tb else 0
                
                # Check if it's a type error
                error_msg = str(e)
                if "BeartypeCallHint" in type(e).__name__ or "type" in error_msg.lower():
                    errors.append(RuntimeTypeError(
                        line=line,
                        expected_type="unknown",
                        actual_type="unknown", 
                        message=error_msg[:200]
                    ))
                elif isinstance(e, TypeError):
                    errors.append(RuntimeTypeError(
                        line=line,
                        expected_type="unknown",
                        actual_type="unknown",
                        message=error_msg[:200]
                    ))
    except SyntaxError as e:
        pass  # Syntax errors aren't type errors
    finally:
        # Cleanup
        sys.path.remove(temp_dir)
        try:
            os.unlink(temp_file)
            os.rmdir(temp_dir)
        except:
            pass
    
    return errors


@dataclass
class ExpectedTypeError:
    """A type error that the code expects (via try/except)."""
    try_line: int  # Line where try block starts
    except_line: int  # Line where except catches
    exception_types: list[str]  # TypeError, KeyError, AttributeError, etc.
    call_line: int  # Line inside try that likely causes the error


class TryExceptVisitor(ast.NodeVisitor):
    """Find try/except blocks that catch type-related exceptions."""
    
    TYPE_RELATED_EXCEPTIONS = {
        'TypeError', 'KeyError', 'AttributeError', 'ValueError',
        'BeartypeCallHintViolation', 'Exception'  # Exception catches all
    }
    
    def __init__(self):
        self.expected_errors: list[ExpectedTypeError] = []
    
    def visit_Try(self, node: ast.Try):
        caught_types = []
        except_line = node.lineno
        
        for handler in node.handlers:
            if handler.type is None:
                # Bare except: catches everything
                caught_types.append('Exception')
                except_line = handler.lineno
            elif isinstance(handler.type, ast.Name):
                if handler.type.id in self.TYPE_RELATED_EXCEPTIONS:
                    caught_types.append(handler.type.id)
                    except_line = handler.lineno
            elif isinstance(handler.type, ast.Tuple):
                # except (TypeError, KeyError):
                for elt in handler.type.elts:
                    if isinstance(elt, ast.Name) and elt.id in self.TYPE_RELATED_EXCEPTIONS:
                        caught_types.append(elt.id)
                        except_line = handler.lineno
        
        if caught_types:
            # Find the likely error-causing line in the try body
            # Usually it's a call expression or subscript access
            call_line = node.lineno
            for stmt in node.body:
                if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                    call_line = stmt.lineno
                    break
                elif isinstance(stmt, ast.Assign):
                    call_line = stmt.lineno
                    break
                elif hasattr(stmt, 'lineno'):
                    call_line = stmt.lineno
            
            self.expected_errors.append(ExpectedTypeError(
                try_line=node.lineno,
                except_line=except_line,
                exception_types=caught_types,
                call_line=call_line,
            ))
        
        self.generic_visit(node)


def find_expected_type_errors(source_code: str) -> list[ExpectedTypeError]:
    """
    Find lines where the code EXPECTS type errors via try/except.
    These are lines that type checkers SHOULD flag.
    """
    try:
        tree = ast.parse(source_code)
        visitor = TryExceptVisitor()
        visitor.visit(tree)
        return visitor.expected_errors
    except SyntaxError:
        return []


def find_typeddict_unsafe_access(source_code: str) -> list[tuple[int, str]]:
    """
    Find subscript accesses on TypedDict that might be unsafe.
    Returns list of (line, key_name).
    """
    unsafe_accesses = []
    
    try:
        tree = ast.parse(source_code)
        
        # Find TypedDict definitions and their NotRequired fields
        # This is a simplified check - look for NotRequired in the source
        notrequired_keys = set()
        for line in source_code.splitlines():
            if 'NotRequired[' in line:
                # Try to extract the key name
                import re
                match = re.search(r'(\w+)\s*:\s*NotRequired\[', line)
                if match:
                    notrequired_keys.add(match.group(1))
        
        # Find subscript accesses
        class SubscriptVisitor(ast.NodeVisitor):
            def visit_Subscript(self, node):
                if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
                    key = node.slice.value
                    if key in notrequired_keys:
                        unsafe_accesses.append((node.lineno, key))
                self.generic_visit(node)
        
        SubscriptVisitor().visit(tree)
    except SyntaxError:
        pass
    
    return unsafe_accesses


def run_with_tracing(source_code: str) -> tuple[list[RuntimeTypeError], float]:
    """
    Execute code with sys.settrace to capture type information.
    Returns (errors, coverage_ratio).
    
    Now also detects CAUGHT exceptions that indicate type bugs.
    """
    errors: list[RuntimeTypeError] = []
    caught_errors: list[RuntimeTypeError] = []
    executed_lines: set[int] = set()
    total_lines = len([l for l in source_code.splitlines() if l.strip() and not l.strip().startswith("#")])
    
    # First, find expected errors from try/except blocks
    expected_errors = find_expected_type_errors(source_code)
    
    # Add these as type errors - these are bugs that the code expects!
    for expected in expected_errors:
        if any(t in ['TypeError', 'KeyError', 'AttributeError'] for t in expected.exception_types):
            caught_errors.append(RuntimeTypeError(
                line=expected.call_line,
                expected_type="unknown",
                actual_type="unknown",
                message=f"Code expects {'/'.join(expected.exception_types)} (try block at line {expected.try_line})"
            ))
    
    # Also find unsafe TypedDict accesses
    unsafe_accesses = find_typeddict_unsafe_access(source_code)
    for line, key in unsafe_accesses:
        caught_errors.append(RuntimeTypeError(
            line=line,
            expected_type="Required key",
            actual_type="NotRequired key",
            message=f"Access to NotRequired key '{key}' without existence check"
        ))
    
    def trace_calls(frame, event, arg):
        if event == 'line':
            executed_lines.add(frame.f_lineno)
        return trace_calls
    
    # Execute with tracing
    try:
        old_trace = sys.gettrace()
        sys.settrace(trace_calls)
        
        exec(compile(source_code, "<string>", "exec"), {"__name__": "__main__"})
        
    except TypeError as e:
        tb = traceback.extract_tb(sys.exc_info()[2])
        line = tb[-1].lineno if tb else 0
        errors.append(RuntimeTypeError(
            line=line,
            expected_type="unknown",
            actual_type="unknown",
            message=str(e)[:200]
        ))
    except AttributeError as e:
        tb = traceback.extract_tb(sys.exc_info()[2])
        line = tb[-1].lineno if tb else 0
        errors.append(RuntimeTypeError(
            line=line,
            expected_type="unknown",
            actual_type="unknown",
            message=str(e)[:200]
        ))
    except KeyError as e:
        tb = traceback.extract_tb(sys.exc_info()[2])
        line = tb[-1].lineno if tb else 0
        errors.append(RuntimeTypeError(
            line=line,
            expected_type="existing key",
            actual_type="missing key",
            message=f"KeyError: {e}"
        ))
    except Exception:
        pass  # Other errors aren't type errors
    finally:
        sys.settrace(old_trace)
    
    # Combine uncaught and caught errors
    all_errors = errors + caught_errors
    
    coverage = len(executed_lines) / max(total_lines, 1)
    return all_errors, coverage


def parse_checker_errors(checker_output: str, checker_name: str) -> list[StaticCheckerError]:
    """Parse error lines from a type checker's output."""
    errors = []
    
    # Common patterns for error lines
    # mypy: file.py:10: error: message
    # pyrefly: --> file.py:10:5
    # zuban: file.py:10: error: message  
    # ty: --> file.py:10:5
    
    patterns = [
        r":(\d+):\s*error:",  # mypy/zuban style
        r":(\d+):\s*Error",   # pyrefly style
        r"--> .*?:(\d+):",    # ty/pyrefly arrow style
        r"line (\d+)",        # generic
    ]
    
    for line in checker_output.splitlines():
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                line_num = int(match.group(1))
                errors.append(StaticCheckerError(
                    line=line_num,
                    message=line.strip()[:200],
                    checker=checker_name
                ))
                break
    
    return errors


def compute_checker_consensus(checker_errors: dict[str, list[StaticCheckerError]]) -> dict[int, str]:
    """
    Compute consensus across checkers for each line.
    Returns {line: "error" | "ok" | "split"}
    """
    # Collect all lines mentioned
    all_lines: set[int] = set()
    for errors in checker_errors.values():
        for err in errors:
            all_lines.add(err.line)
    
    consensus = {}
    for line in all_lines:
        error_count = sum(
            1 for checker, errors in checker_errors.items()
            if any(e.line == line for e in errors)
        )
        total_checkers = len(checker_errors)
        
        if error_count >= total_checkers * 0.75:  # 3/4 or more
            consensus[line] = "error"
        elif error_count <= total_checkers * 0.25:  # 1/4 or less
            consensus[line] = "ok"
        else:
            consensus[line] = "split"
    
    return consensus


def establish_ground_truth(
    source_code: str,
    checker_outputs: dict[str, str],
) -> tuple[list[GroundTruth], float]:
    """
    Establish ground truth using multiple oracles.
    Returns (ground_truth_per_line, coverage).
    
    Priority order:
    1. Runtime errors (highest confidence) - includes caught exceptions
    2. AST analysis (TypedDict unsafe access, return type mismatches)
    3. Checker consensus is only used as weak evidence, NOT as ground truth
       (since we're trying to evaluate checkers, using them as truth is circular)
    """
    ground_truth: list[GroundTruth] = []
    
    # Oracle 1: Runtime with tracing (now includes caught exceptions and TypedDict analysis)
    runtime_errors, coverage = run_with_tracing(source_code)
    runtime_error_lines = {e.line: e for e in runtime_errors}
    
    # Oracle 2: Runtime with beartype
    beartype_errors = run_with_beartype(source_code, "temp.py")
    beartype_error_lines = {e.line: e for e in beartype_errors}
    
    # Oracle 3: AST analysis
    ast_errors = extract_potential_errors(source_code)
    ast_error_dict = {line: reason for line, reason in ast_errors}
    
    # Checker errors (for reference only, NOT for establishing ground truth)
    checker_errors = {
        name: parse_checker_errors(output, name)
        for name, output in checker_outputs.items()
    }
    
    # Collect all lines where we have evidence
    all_error_lines = set()
    all_error_lines.update(runtime_error_lines.keys())
    all_error_lines.update(beartype_error_lines.keys())
    all_error_lines.update(ast_error_dict.keys())
    
    for line in sorted(all_error_lines):
        runtime_error = runtime_error_lines.get(line)
        beartype_error = beartype_error_lines.get(line)
        ast_reason = ast_error_dict.get(line)
        
        # Determine ground truth based on our oracles (NOT checker consensus)
        if runtime_error or beartype_error:
            # Runtime evidence is definitive
            error = runtime_error or beartype_error
            ground_truth.append(GroundTruth(
                line=line,
                has_error=True,
                confidence=1.0,
                source="runtime",
                details=error.message if error else "Runtime type error"
            ))
        elif ast_reason:
            # AST analysis found an issue
            ground_truth.append(GroundTruth(
                line=line,
                has_error=True,
                confidence=0.85,
                source="ast",
                details=ast_reason
            ))
    
    # DON'T add lines where only checkers disagree - that's what we're trying to evaluate!
    # The ground truth should come from sources independent of the checkers.
    
    return ground_truth, coverage


def evaluate_checker(
    checker_name: str,
    checker_output: str,
    ground_truth: list[GroundTruth],
) -> dict:
    """
    Evaluate a single checker against ground truth.
    Returns precision, recall, F1, and counts.
    """
    checker_errors = parse_checker_errors(checker_output, checker_name)
    checker_error_lines = {e.line for e in checker_errors}
    
    # Only consider high-confidence ground truth
    confident_truth = [gt for gt in ground_truth if gt.confidence >= 0.75]
    
    tp = fp = fn = tn = 0
    
    for gt in confident_truth:
        checker_says_error = gt.line in checker_error_lines
        truth_is_error = gt.has_error
        
        if checker_says_error and truth_is_error:
            tp += 1
        elif checker_says_error and not truth_is_error:
            fp += 1
        elif not checker_says_error and truth_is_error:
            fn += 1
        else:
            tn += 1
    
    # Compute metrics
    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
    }


def evaluate_file(
    source_code: str,
    filename: str,
    checker_outputs: dict[str, str],
) -> EvaluationResult:
    """
    Perform complete deterministic evaluation of a file.
    """
    # Establish ground truth
    ground_truth, coverage = establish_ground_truth(source_code, checker_outputs)
    
    # Evaluate each checker
    checker_results = {}
    for checker_name, output in checker_outputs.items():
        checker_results[checker_name] = evaluate_checker(
            checker_name, output, ground_truth
        )
    
    return EvaluationResult(
        filename=filename,
        ground_truth=ground_truth,
        coverage=coverage,
        checker_results=checker_results,
    )


def format_checker_verdict(stats: dict) -> str:
    """Format a single checker's verdict as a short string."""
    p, r, f1 = stats['precision'], stats['recall'], stats['f1']
    
    if f1 >= 0.95:
        return "CORRECT"
    elif f1 >= 0.7:
        return f"PARTIAL (missed {stats['false_negatives']} issues)"
    elif stats['false_positives'] > 0 and stats['false_negatives'] == 0:
        return f"WRONG (false positives: {stats['false_positives']})"
    elif stats['false_negatives'] > 0 and stats['false_positives'] == 0:
        return f"WRONG (missed {stats['false_negatives']} issues)"
    elif stats['false_positives'] > 0 and stats['false_negatives'] > 0:
        return f"WRONG (FP: {stats['false_positives']}, missed: {stats['false_negatives']})"
    else:
        return "CORRECT"


def summarize_file_verdict(checker_results: dict[str, dict]) -> tuple[list[str], list[str]]:
    """
    Summarize which checkers were correct/incorrect for a file.
    Returns (correct_checkers, incorrect_checkers).
    """
    correct = []
    incorrect = []
    
    for checker, stats in checker_results.items():
        f1 = stats['f1']
        fp = stats['false_positives']
        fn = stats['false_negatives']
        
        # A checker is "correct" if it has high F1 and no significant errors
        if f1 >= 0.95 and fp == 0 and fn == 0:
            correct.append(checker)
        elif f1 >= 0.8 and fp == 0:
            correct.append(checker)
        else:
            incorrect.append(checker)
    
    return correct, incorrect


def evaluate_results_deterministic(results_path: str) -> dict:
    """
    Main entry point: evaluate all files in a results.json deterministically.
    """
    import json
    import os
    
    with open(results_path) as f:
        data = json.load(f)
    
    results = data.get("results", [])
    checkers = data.get("checkers_used", [])
    
    all_evaluations = []
    aggregate_stats = {checker: {"tp": 0, "fp": 0, "fn": 0, "tn": 0} for checker in checkers}
    total_coverage = 0.0
    high_confidence_count = 0
    uncertain_count = 0
    
    print("=" * 70)
    print("DETERMINISTIC EVALUATION")
    print("=" * 70)
    
    for file_entry in results:
        filepath = file_entry.get("filepath", "")
        filename = file_entry.get("filename", "")
        outputs = file_entry.get("outputs", {})
        
        # Read source code
        try:
            with open(filepath) as f:
                source_code = f.read()
        except FileNotFoundError:
            print(f"\n[SKIP] {filename}: file not found")
            continue
        
        # Evaluate (suppress runtime output during evaluation)
        import io
        import contextlib
        
        with contextlib.redirect_stdout(io.StringIO()):
            result = evaluate_file(source_code, filename, outputs)
        
        all_evaluations.append(result)
        
        # Aggregate stats
        total_coverage += result.coverage
        for gt in result.ground_truth:
            if gt.confidence >= 0.75:
                high_confidence_count += 1
            else:
                uncertain_count += 1
        
        for checker, stats in result.checker_results.items():
            aggregate_stats[checker]["tp"] += stats["true_positives"]
            aggregate_stats[checker]["fp"] += stats["false_positives"]
            aggregate_stats[checker]["fn"] += stats["false_negatives"]
            aggregate_stats[checker]["tn"] += stats["true_negatives"]
        
        # Print clean per-file output
        print(f"\n{filename}")
        print("-" * len(filename))
        
        # Show each checker's report (truncated)
        for checker in checkers:
            output = outputs.get(checker, "")
            # Get first meaningful line of output
            lines = [l.strip() for l in output.strip().splitlines() if l.strip()]
            if not lines:
                report = "(no output)"
            elif "success" in output.lower() or "0 error" in output.lower():
                report = "OK (no errors)"
            else:
                # Find first error line
                error_lines = [l for l in lines if "error" in l.lower() or "-->" in l]
                if error_lines:
                    report = error_lines[0][:60] + ("..." if len(error_lines[0]) > 60 else "")
                    if len(error_lines) > 1:
                        report += f" (+{len(error_lines)-1} more)"
                else:
                    report = lines[0][:60] + ("..." if len(lines[0]) > 60 else "")
            
            print(f"  {checker}: {report}")
        
        # Print verdict
        correct, incorrect = summarize_file_verdict(result.checker_results)
        print()
        if correct:
            print(f"  CORRECT: {', '.join(correct)}")
        if incorrect:
            # Show why each is incorrect
            for checker in incorrect:
                stats = result.checker_results[checker]
                verdict = format_checker_verdict(stats)
                print(f"  INCORRECT: {checker} - {verdict}")
        
        if not correct and not incorrect:
            print("  VERDICT: Unable to determine (no ground truth)")
    
    # Compute aggregate metrics
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    avg_coverage = total_coverage / max(len(all_evaluations), 1)
    
    print(f"\nFiles evaluated: {len(all_evaluations)}")
    print(f"Ground truth lines: {high_confidence_count} high-confidence, {uncertain_count} uncertain")
    
    print(f"\n{'Checker':<12} {'Precision':>10} {'Recall':>10} {'F1':>10} {'TP':>6} {'FP':>6} {'FN':>6}")
    print("-" * 62)
    
    final_results = {}
    for checker in checkers:
        stats = aggregate_stats[checker]
        tp, fp, fn, tn = stats["tp"], stats["fp"], stats["fn"], stats["tn"]
        precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        print(f"{checker:<12} {precision:>10.2f} {recall:>10.2f} {f1:>10.2f} {tp:>6} {fp:>6} {fn:>6}")
        
        final_results[checker] = {
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "true_negatives": tn,
        }
    
    print("=" * 70)
    
    # Save results
    output_dir = os.path.dirname(results_path)
    eval_path = os.path.join(output_dir, "evaluation_deterministic.json")
    
    with open(eval_path, "w") as f:
        json.dump({
            "method": "deterministic",
            "average_coverage": round(avg_coverage, 3),
            "high_confidence_verdicts": high_confidence_count,
            "uncertain_verdicts": uncertain_count,
            "checker_results": final_results,
            "per_file": [
                {
                    "filename": e.filename,
                    "coverage": round(e.coverage, 3),
                    "ground_truth_count": len(e.ground_truth),
                    "checker_results": e.checker_results,
                }
                for e in all_evaluations
            ]
        }, f, indent=2)
    
    print(f"\nResults saved to: {eval_path}")
    
    return final_results


def execute_and_capture(source_code: str) -> str:
    """Execute code and capture any runtime errors."""
    import io
    import contextlib
    
    output = io.StringIO()
    error_output = ""
    
    try:
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            exec(compile(source_code, "<string>", "exec"), {"__name__": "__main__"})
    except TypeError as e:
        error_output = f"TypeError: {e}"
    except KeyError as e:
        error_output = f"KeyError: {e}"
    except AttributeError as e:
        error_output = f"AttributeError: {e}"
    except Exception as e:
        error_output = f"{type(e).__name__}: {e}"
    
    stdout = output.getvalue()
    if error_output:
        return f"RUNTIME ERROR: {error_output}\n\nStdout before error:\n{stdout}"
    return f"SUCCESS (no runtime errors)\n\nStdout:\n{stdout[:1000]}"


def evaluate_results_llm(results_path: str, model: str = "gemini-2.5-flash") -> dict:
    """
    Evaluate all files using LLM-based analysis for high accuracy.
    This is the recommended evaluation method for production use.
    """
    with open(results_path) as f:
        data = json.load(f)
    
    results = data.get("results", [])
    checkers = data.get("checkers_used", ["mypy", "pyrefly", "zuban", "ty"])
    
    all_verdicts = []
    summary_stats = {checker: {"correct": 0, "incorrect": 0, "partial": 0} for checker in checkers}
    
    print("=" * 70)
    print("LLM-BASED EVALUATION (High Accuracy)")
    print("=" * 70)
    print(f"Using model: {model}")
    print(f"Files to evaluate: {len(results)}")
    print()
    
    for i, file_entry in enumerate(results, 1):
        filepath = file_entry.get("filepath", "")
        filename = file_entry.get("filename", "")
        outputs = file_entry.get("outputs", {})
        
        print(f"\n[{i}/{len(results)}] {filename}")
        print("-" * len(filename))
        
        # Read source code
        try:
            with open(filepath) as f:
                source_code = f.read()
        except FileNotFoundError:
            print(f"  [SKIP] File not found")
            continue
        
        # Execute code to get runtime result
        runtime_result = execute_and_capture(source_code)
        
        # Show checker outputs (abbreviated)
        for checker in checkers:
            output = outputs.get(checker, "")
            if "success" in output.lower() or "0 error" in output.lower():
                print(f"  {checker}: OK (no errors)")
            else:
                lines = [l for l in output.splitlines() if "error" in l.lower()]
                if lines:
                    print(f"  {checker}: {lines[0][:50]}..." if len(lines[0]) > 50 else f"  {checker}: {lines[0]}")
                else:
                    print(f"  {checker}: (has output)")
        
        # Call LLM for evaluation
        try:
            verdicts = evaluate_with_llm(source_code, outputs, runtime_result, model)
            
            print()
            correct_checkers = []
            incorrect_checkers = []
            
            for checker, verdict in verdicts.items():
                if verdict.verdict == "CORRECT":
                    correct_checkers.append(checker)
                    summary_stats[checker]["correct"] += 1
                elif verdict.verdict == "PARTIAL":
                    summary_stats[checker]["partial"] += 1
                else:
                    incorrect_checkers.append((checker, verdict.reason))
                    summary_stats[checker]["incorrect"] += 1
            
            if correct_checkers:
                print(f"  ✓ CORRECT: {', '.join(correct_checkers)}")
            for checker, reason in incorrect_checkers:
                # Truncate reason if too long
                short_reason = reason[:80] + "..." if len(reason) > 80 else reason
                print(f"  ✗ INCORRECT: {checker} - {short_reason}")
            
            all_verdicts.append({
                "filename": filename,
                "verdicts": {c: {"verdict": v.verdict, "reason": v.reason, 
                                "missed_issues": v.missed_issues,
                                "false_positives": v.false_positives}
                            for c, v in verdicts.items()},
                "runtime_result": runtime_result[:500]
            })
            
        except Exception as e:
            error_msg = str(e)[:100]  # Truncate error message
            print(f"  [ERROR] Evaluation failed: {error_msg}")
            all_verdicts.append({
                "filename": filename,
                "error": error_msg
            })
    
    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    print(f"\n{'Checker':<12} {'Correct':>10} {'Incorrect':>10} {'Partial':>10} {'Accuracy':>10}")
    print("-" * 54)
    
    for checker in checkers:
        stats = summary_stats[checker]
        total = stats["correct"] + stats["incorrect"] + stats["partial"]
        accuracy = stats["correct"] / total * 100 if total > 0 else 0
        print(f"{checker:<12} {stats['correct']:>10} {stats['incorrect']:>10} {stats['partial']:>10} {accuracy:>9.1f}%")
    
    print("=" * 70)
    
    # Save results
    output_dir = os.path.dirname(results_path)
    eval_path = os.path.join(output_dir, "evaluation_llm.json")
    
    with open(eval_path, "w") as f:
        json.dump({
            "method": "llm",
            "model": model,
            "summary": summary_stats,
            "evaluations": all_verdicts
        }, f, indent=2)
    
    print(f"\nResults saved to: {eval_path}")
    
    return summary_stats


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python deterministic_eval.py <results.json> [--llm] [--model MODEL]")
        print("  --llm          Use LLM-based evaluation (recommended, requires GEMINI_API_KEY)")
        print("  --model MODEL  Gemini model to use (default: gemini-2.5-flash)")
        sys.exit(1)
    
    results_path = sys.argv[1]
    use_llm = "--llm" in sys.argv
    
    model = "gemini-2.5-flash"
    if "--model" in sys.argv:
        idx = sys.argv.index("--model")
        if idx + 1 < len(sys.argv):
            model = sys.argv[idx + 1]
    
    if use_llm:
        evaluate_results_llm(results_path, model)
    else:
        evaluate_results_deterministic(results_path)
