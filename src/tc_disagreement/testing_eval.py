# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "hypothesis",
#     "beartype",
# ]
# ///

"""
Testing-based evaluation of type checker correctness.

Uses property-based testing (Hypothesis) and runtime type enforcement (beartype)
to establish ground truth for evaluating type checker outputs.

Key insight: Runtime behavior is the ultimate ground truth for type correctness.
- If code raises TypeError/KeyError/AttributeError → type bug exists
- If beartype catches a violation → type bug exists
- Type checkers that missed these bugs are INCORRECT
"""

import ast
import sys
import re
import os
import json
import traceback
import io
import contextlib
from dataclasses import dataclass, field
from typing import Any, Optional, Callable
from pathlib import Path

# These are imported at runtime to avoid issues if not installed
# hypothesis and beartype are installed via uv when running


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class TypeBug:
    """A confirmed type-related bug found through testing."""
    line: int
    bug_type: str  # "TypeError", "KeyError", "AttributeError", "BeartypeViolation"
    message: str
    source: str  # "runtime_uncaught", "runtime_caught", "beartype", "hypothesis"
    confidence: float  # 0.0 to 1.0


@dataclass
class FunctionSignature:
    """Extracted function signature with type annotations."""
    name: str
    line: int
    parameters: dict[str, str]  # param_name -> annotation string
    return_type: Optional[str]
    is_method: bool
    is_async: bool


@dataclass
class TestResult:
    """Result of testing a single code example."""
    filename: str
    bugs_found: list[TypeBug]
    functions_tested: list[str]
    execution_success: bool
    stdout: str
    checker_verdicts: dict[str, dict]  # checker -> {verdict, reason, confidence}


# =============================================================================
# AST ANALYSIS: Extract function signatures and expected errors
# =============================================================================

class SignatureExtractor(ast.NodeVisitor):
    """Extract function signatures with type annotations from AST."""
    
    def __init__(self):
        self.signatures: list[FunctionSignature] = []
        self.in_class = False
    
    def visit_ClassDef(self, node: ast.ClassDef):
        old_in_class = self.in_class
        self.in_class = True
        self.generic_visit(node)
        self.in_class = old_in_class
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._extract_function(node, is_async=False)
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._extract_function(node, is_async=True)
        self.generic_visit(node)
    
    def _extract_function(self, node, is_async: bool):
        params = {}
        
        # Extract parameter annotations
        for arg in node.args.args:
            if arg.annotation:
                params[arg.arg] = ast.unparse(arg.annotation)
        
        # Extract return type
        return_type = ast.unparse(node.returns) if node.returns else None
        
        self.signatures.append(FunctionSignature(
            name=node.name,
            line=node.lineno,
            parameters=params,
            return_type=return_type,
            is_method=self.in_class,
            is_async=is_async,
        ))


class TryExceptAnalyzer(ast.NodeVisitor):
    """Find try/except blocks that catch type-related exceptions."""
    
    TYPE_EXCEPTIONS = {'TypeError', 'KeyError', 'AttributeError', 'ValueError'}
    
    def __init__(self):
        self.expected_errors: list[TypeBug] = []
    
    def visit_Try(self, node: ast.Try):
        caught_types = []
        
        for handler in node.handlers:
            if handler.type is None:
                # Bare except catches everything
                caught_types.append('Exception')
            elif isinstance(handler.type, ast.Name):
                if handler.type.id in self.TYPE_EXCEPTIONS:
                    caught_types.append(handler.type.id)
            elif isinstance(handler.type, ast.Tuple):
                for elt in handler.type.elts:
                    if isinstance(elt, ast.Name) and elt.id in self.TYPE_EXCEPTIONS:
                        caught_types.append(elt.id)
        
        if caught_types:
            # Find the first statement in try block as the likely error source
            if node.body:
                error_line = node.body[0].lineno
                for bug_type in caught_types:
                    if bug_type in self.TYPE_EXCEPTIONS:
                        self.expected_errors.append(TypeBug(
                            line=error_line,
                            bug_type=bug_type,
                            message=f"Code expects {bug_type} (try block at line {node.lineno})",
                            source="runtime_caught",
                            confidence=0.9,
                        ))
        
        self.generic_visit(node)


class NotRequiredAccessAnalyzer(ast.NodeVisitor):
    """Find unsafe access to NotRequired TypedDict fields."""
    
    def __init__(self, source_code: str):
        self.source_code = source_code
        self.notrequired_keys: set[str] = set()
        self.unsafe_accesses: list[TypeBug] = []
        self._find_notrequired_keys()
    
    def _find_notrequired_keys(self):
        """Find all NotRequired field names in the source."""
        pattern = r'(\w+)\s*:\s*NotRequired\['
        for match in re.finditer(pattern, self.source_code):
            self.notrequired_keys.add(match.group(1))
    
    def visit_Subscript(self, node: ast.Subscript):
        """Check for dict[key] access where key is NotRequired."""
        if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
            key = node.slice.value
            if key in self.notrequired_keys:
                self.unsafe_accesses.append(TypeBug(
                    line=node.lineno,
                    bug_type="KeyError",
                    message=f"Access to NotRequired key '{key}' without existence check",
                    source="ast_analysis",
                    confidence=0.85,
                ))
        self.generic_visit(node)


def extract_signatures(source_code: str) -> list[FunctionSignature]:
    """Extract all function signatures from source code."""
    try:
        tree = ast.parse(source_code)
        extractor = SignatureExtractor()
        extractor.visit(tree)
        return extractor.signatures
    except SyntaxError:
        return []


def find_expected_errors(source_code: str) -> list[TypeBug]:
    """Find lines where code expects type errors via try/except."""
    try:
        tree = ast.parse(source_code)
        analyzer = TryExceptAnalyzer()
        analyzer.visit(tree)
        return analyzer.expected_errors
    except SyntaxError:
        return []


def find_notrequired_access(source_code: str) -> list[TypeBug]:
    """Find unsafe access to NotRequired TypedDict fields."""
    try:
        tree = ast.parse(source_code)
        analyzer = NotRequiredAccessAnalyzer(source_code)
        analyzer.visit(tree)
        return analyzer.unsafe_accesses
    except SyntaxError:
        return []


# =============================================================================
# DYNAMIC STRATEGY GENERATION
# =============================================================================

def get_hypothesis_strategies():
    """Import hypothesis strategies - done at runtime to handle missing package."""
    try:
        from hypothesis import strategies as st
        return st
    except ImportError:
        return None


def annotation_to_strategy(annotation: str, st):
    """
    Convert a type annotation string to a Hypothesis strategy.
    
    This maps Python type annotations to strategies that generate valid values.
    """
    if st is None:
        return None
    
    # Clean up the annotation
    annotation = annotation.strip()
    
    # Basic type mappings
    basic_mappings = {
        "int": st.integers(),
        "str": st.text(max_size=50),
        "float": st.floats(allow_nan=False, allow_infinity=False),
        "bool": st.booleans(),
        "None": st.none(),
        "bytes": st.binary(max_size=50),
        "object": st.none(),  # Fallback
        "Any": st.one_of(st.integers(), st.text(), st.booleans(), st.none()),
    }
    
    if annotation in basic_mappings:
        return basic_mappings[annotation]
    
    # Optional types: Optional[X] or X | None
    if annotation.startswith("Optional[") and annotation.endswith("]"):
        inner = annotation[9:-1]
        inner_strategy = annotation_to_strategy(inner, st)
        if inner_strategy:
            return st.none() | inner_strategy
    
    # Union with None: X | None
    if " | None" in annotation:
        inner = annotation.replace(" | None", "").strip()
        inner_strategy = annotation_to_strategy(inner, st)
        if inner_strategy:
            return st.none() | inner_strategy
    
    # List types: list[X]
    if annotation.startswith("list[") and annotation.endswith("]"):
        inner = annotation[5:-1]
        inner_strategy = annotation_to_strategy(inner, st)
        if inner_strategy:
            return st.lists(inner_strategy, max_size=5)
    
    # Set types: set[X]
    if annotation.startswith("set[") and annotation.endswith("]"):
        inner = annotation[4:-1]
        inner_strategy = annotation_to_strategy(inner, st)
        if inner_strategy:
            return st.frozensets(inner_strategy, max_size=5)
    
    # Tuple types: tuple[X, Y] or tuple[X, ...]
    if annotation.startswith("tuple[") and annotation.endswith("]"):
        inner = annotation[6:-1]
        if ", ..." in inner:
            elem_type = inner.replace(", ...", "").strip()
            elem_strategy = annotation_to_strategy(elem_type, st)
            if elem_strategy:
                return st.lists(elem_strategy, max_size=5).map(tuple)
        else:
            # Fixed tuple
            parts = [p.strip() for p in inner.split(",")]
            strategies = [annotation_to_strategy(p, st) for p in parts]
            if all(s is not None for s in strategies):
                return st.tuples(*strategies)
    
    # Dict types: dict[K, V]
    if annotation.startswith("dict[") and annotation.endswith("]"):
        inner = annotation[5:-1]
        # Simple split (doesn't handle nested generics well)
        parts = inner.split(",", 1)
        if len(parts) == 2:
            key_strategy = annotation_to_strategy(parts[0].strip(), st)
            val_strategy = annotation_to_strategy(parts[1].strip(), st)
            if key_strategy and val_strategy:
                return st.dictionaries(key_strategy, val_strategy, max_size=3)
    
    # Literal types: Literal["a", "b", "c"]
    if annotation.startswith("Literal[") and annotation.endswith("]"):
        inner = annotation[8:-1]
        # Parse literal values
        values = []
        for part in inner.split(","):
            part = part.strip().strip('"').strip("'")
            if part.isdigit():
                values.append(int(part))
            elif part in ("True", "False"):
                values.append(part == "True")
            else:
                values.append(part)
        if values:
            return st.sampled_from(values)
    
    # Callable - generate a simple lambda
    if annotation.startswith("Callable"):
        return st.just(lambda *args, **kwargs: None)
    
    # Self, TypeVar, etc. - use none as fallback
    if annotation in ("Self", "T", "K", "V", "R", "P"):
        return st.none()
    
    # Unknown type - return None to skip
    return None


def build_strategies_for_function(sig: FunctionSignature, st) -> Optional[dict]:
    """
    Build Hypothesis strategies for all parameters of a function.
    Returns dict mapping param name to strategy, or None if can't build.
    """
    strategies = {}
    
    for param_name, annotation in sig.parameters.items():
        # Skip 'self' and 'cls'
        if param_name in ('self', 'cls'):
            continue
        
        strategy = annotation_to_strategy(annotation, st)
        if strategy is None:
            # Can't generate strategy for this type
            return None
        strategies[param_name] = strategy
    
    return strategies if strategies else None


# =============================================================================
# RUNTIME EXECUTION WITH TRACING
# =============================================================================

def execute_with_tracing(source_code: str) -> tuple[list[TypeBug], bool, str]:
    """
    Execute code and capture type-related exceptions.
    
    Returns:
        (list of bugs found, execution success, stdout)
    """
    bugs: list[TypeBug] = []
    stdout_capture = io.StringIO()
    success = False
    
    try:
        with contextlib.redirect_stdout(stdout_capture), \
             contextlib.redirect_stderr(stdout_capture):
            exec(compile(source_code, "<test>", "exec"), {"__name__": "__main__"})
        success = True
        
    except TypeError as e:
        tb = traceback.extract_tb(sys.exc_info()[2])
        line = tb[-1].lineno if tb else 0
        bugs.append(TypeBug(
            line=line,
            bug_type="TypeError",
            message=str(e)[:200],
            source="runtime_uncaught",
            confidence=1.0,
        ))
    except KeyError as e:
        tb = traceback.extract_tb(sys.exc_info()[2])
        line = tb[-1].lineno if tb else 0
        bugs.append(TypeBug(
            line=line,
            bug_type="KeyError",
            message=f"KeyError: {e}",
            source="runtime_uncaught",
            confidence=1.0,
        ))
    except AttributeError as e:
        tb = traceback.extract_tb(sys.exc_info()[2])
        line = tb[-1].lineno if tb else 0
        bugs.append(TypeBug(
            line=line,
            bug_type="AttributeError",
            message=str(e)[:200],
            source="runtime_uncaught",
            confidence=1.0,
        ))
    except Exception as e:
        # Other exceptions - not type errors but note them
        pass
    
    return bugs, success, stdout_capture.getvalue()


def execute_with_beartype(source_code: str) -> list[TypeBug]:
    """
    Execute code with beartype runtime type checking enabled.
    
    Returns list of type bugs found by beartype.
    """
    bugs: list[TypeBug] = []
    
    try:
        from beartype import beartype
        from beartype.roar import BeartypeCallHintViolation
    except ImportError:
        # beartype not installed
        return bugs
    
    # Instrument code with beartype import
    instrumented = f"""
from beartype import beartype
from beartype.roar import BeartypeCallHintViolation

{source_code}
"""
    
    try:
        with contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()):
            exec(compile(instrumented, "<beartype_test>", "exec"), {"__name__": "__main__"})
    except Exception as e:
        if "BeartypeCallHint" in type(e).__name__ or "beartype" in str(type(e)).lower():
            # Extract line number from traceback
            tb = traceback.extract_tb(sys.exc_info()[2])
            line = tb[-1].lineno if tb else 0
            bugs.append(TypeBug(
                line=line,
                bug_type="BeartypeViolation",
                message=str(e)[:200],
                source="beartype",
                confidence=1.0,
            ))
        elif isinstance(e, TypeError):
            tb = traceback.extract_tb(sys.exc_info()[2])
            line = tb[-1].lineno if tb else 0
            bugs.append(TypeBug(
                line=line,
                bug_type="TypeError",
                message=str(e)[:200],
                source="beartype",
                confidence=1.0,
            ))
    
    return bugs


# =============================================================================
# PROPERTY-BASED TESTING WITH HYPOTHESIS
# =============================================================================

def run_hypothesis_tests(source_code: str, signatures: list[FunctionSignature]) -> list[TypeBug]:
    """
    Run property-based tests on functions using Hypothesis.
    
    For each function with type annotations:
    1. Generate random valid inputs matching the declared types
    2. Call the function
    3. If TypeError/AttributeError occurs → type bug found
    """
    bugs: list[TypeBug] = []
    
    st = get_hypothesis_strategies()
    if st is None:
        return bugs
    
    try:
        from hypothesis import given, settings, Verbosity
        from hypothesis.errors import Unsatisfied
    except ImportError:
        return bugs
    
    # Compile the module to get access to functions
    try:
        module_globals = {"__name__": "__test_module__"}
        exec(compile(source_code, "<hypothesis_test>", "exec"), module_globals)
    except Exception:
        # Can't even compile/run the module
        return bugs
    
    for sig in signatures:
        # Skip methods, async functions, and special functions
        if sig.is_method or sig.is_async or sig.name.startswith("_"):
            continue
        
        # Get the function from the module
        func = module_globals.get(sig.name)
        if not callable(func):
            continue
        
        # Build strategies for parameters
        strategies = build_strategies_for_function(sig, st)
        if not strategies:
            continue
        
        # Create a test function
        def make_test(fn, strats, fn_name, fn_line):
            @settings(max_examples=20, verbosity=Verbosity.quiet, deadline=None)
            @given(**strats)
            def test_fn(**kwargs):
                try:
                    fn(**kwargs)
                except (TypeError, AttributeError, KeyError) as e:
                    # Found a type bug!
                    bugs.append(TypeBug(
                        line=fn_line,
                        bug_type=type(e).__name__,
                        message=f"Hypothesis found: {str(e)[:100]}",
                        source="hypothesis",
                        confidence=1.0,
                    ))
                    raise  # Let hypothesis know this is a failure
                except Exception:
                    # Other exceptions are not type errors
                    pass
            
            return test_fn
        
        test = make_test(func, strategies, sig.name, sig.line)
        
        try:
            test()
        except Exception:
            # Test found a bug (already recorded in bugs list)
            pass
    
    return bugs


# =============================================================================
# MAIN EVALUATION FUNCTION
# =============================================================================

def evaluate_example(
    source_code: str,
    checker_outputs: dict[str, str],
    filename: str = "unknown.py",
) -> TestResult:
    """
    Evaluate a code example using runtime testing to establish ground truth.
    
    Steps:
    1. Execute code and catch uncaught exceptions
    2. Find expected errors (try/except blocks)
    3. Find unsafe TypedDict access
    4. Run beartype for runtime type checking
    5. Run Hypothesis property-based tests
    6. Compare all findings to checker outputs
    """
    all_bugs: list[TypeBug] = []
    functions_tested: list[str] = []
    
    # Step 1: Basic execution with exception tracing
    runtime_bugs, execution_success, stdout = execute_with_tracing(source_code)
    all_bugs.extend(runtime_bugs)
    
    # Step 2: Find expected errors (try/except blocks)
    expected_bugs = find_expected_errors(source_code)
    all_bugs.extend(expected_bugs)
    
    # Step 3: Find unsafe NotRequired access
    notrequired_bugs = find_notrequired_access(source_code)
    all_bugs.extend(notrequired_bugs)
    
    # Step 4: Run with beartype
    beartype_bugs = execute_with_beartype(source_code)
    all_bugs.extend(beartype_bugs)
    
    # Step 5: Extract signatures and run Hypothesis tests
    signatures = extract_signatures(source_code)
    functions_tested = [s.name for s in signatures if not s.is_method]
    
    hypothesis_bugs = run_hypothesis_tests(source_code, signatures)
    all_bugs.extend(hypothesis_bugs)
    
    # Deduplicate bugs by line
    unique_bugs = {}
    for bug in all_bugs:
        key = (bug.line, bug.bug_type)
        if key not in unique_bugs or bug.confidence > unique_bugs[key].confidence:
            unique_bugs[key] = bug
    all_bugs = list(unique_bugs.values())
    
    # Step 6: Evaluate each checker against our findings
    verdicts = evaluate_checkers(all_bugs, checker_outputs)
    
    return TestResult(
        filename=filename,
        bugs_found=all_bugs,
        functions_tested=functions_tested,
        execution_success=execution_success,
        stdout=stdout[:500],
        checker_verdicts=verdicts,
    )


def evaluate_checkers(
    bugs: list[TypeBug],
    checker_outputs: dict[str, str],
) -> dict[str, dict]:
    """
    Evaluate each type checker against discovered bugs.
    
    Logic:
    - If we found proven bugs AND checker said OK → INCORRECT (false negative)
    - If we found proven bugs AND checker reported errors → CORRECT
    - If no proven bugs AND checker said OK → UNCERTAIN (might be correct)
    - If no proven bugs AND checker reported errors → UNCERTAIN (might be false positive)
    """
    verdicts = {}
    
    # Get high-confidence bugs (runtime or beartype)
    proven_bugs = [b for b in bugs if b.confidence >= 0.9]
    has_proven_bugs = len(proven_bugs) > 0
    
    for checker, output in checker_outputs.items():
        # Determine if checker reported any errors
        output_lower = output.lower()
        checker_reported_error = (
            "error" in output_lower and 
            "0 error" not in output_lower and
            "success" not in output_lower
        )
        
        if has_proven_bugs and not checker_reported_error:
            # Checker missed proven bugs - DEFINITELY INCORRECT
            verdicts[checker] = {
                "verdict": "INCORRECT",
                "reason": f"Missed {len(proven_bugs)} proven type bug(s)",
                "confidence": 1.0,
                "missed_bugs": [
                    {"line": b.line, "type": b.bug_type, "message": b.message}
                    for b in proven_bugs
                ],
            }
        elif has_proven_bugs and checker_reported_error:
            # Checker reported errors and we found bugs - likely CORRECT
            verdicts[checker] = {
                "verdict": "CORRECT",
                "reason": "Correctly identified type issues",
                "confidence": 0.9,
            }
        elif not has_proven_bugs and not checker_reported_error:
            # No bugs found, checker agrees - UNCERTAIN but likely correct
            verdicts[checker] = {
                "verdict": "UNCERTAIN",
                "reason": "No type bugs detected, checker agrees",
                "confidence": 0.5,
            }
        else:
            # No proven bugs but checker reported errors - might be false positive
            verdicts[checker] = {
                "verdict": "UNCERTAIN",
                "reason": "Checker reported errors but no runtime proof of bugs",
                "confidence": 0.5,
                "note": "May be false positive or bug not triggered at runtime",
            }
    
    return verdicts


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def evaluate_results_testing(results_path: str) -> dict:
    """
    Evaluate all files in a results.json using testing-based analysis.
    """
    with open(results_path) as f:
        data = json.load(f)
    
    results = data.get("results", [])
    checkers = data.get("checkers_used", ["mypy", "pyrefly", "zuban", "ty"])
    
    all_results: list[TestResult] = []
    summary_stats = {
        checker: {"correct": 0, "incorrect": 0, "uncertain": 0}
        for checker in checkers
    }
    
    print("=" * 70)
    print("TESTING-BASED EVALUATION")
    print("=" * 70)
    print("Methods: Runtime execution, beartype, Hypothesis, AST analysis")
    print(f"Files to evaluate: {len(results)}")
    print()
    
    for i, file_entry in enumerate(results, 1):
        filepath = file_entry.get("filepath", "")
        filename = file_entry.get("filename", "")
        outputs = file_entry.get("outputs", {})
        
        print(f"[{i}/{len(results)}] {filename}")
        print("-" * len(filename))
        
        # Read source code
        try:
            with open(filepath) as f:
                source_code = f.read()
        except FileNotFoundError:
            print("  [SKIP] File not found")
            continue
        
        # Run evaluation
        result = evaluate_example(source_code, outputs, filename)
        all_results.append(result)
        
        # Print checker outputs summary
        for checker in checkers:
            output = outputs.get(checker, "")
            if "success" in output.lower() or "0 error" in output.lower():
                print(f"  {checker}: OK")
            else:
                error_lines = [l for l in output.splitlines() if "error" in l.lower()]
                if error_lines:
                    print(f"  {checker}: ERROR ({len(error_lines)} issue(s))")
                else:
                    print(f"  {checker}: (has output)")
        
        # Print bugs found
        if result.bugs_found:
            print(f"\n  Bugs found: {len(result.bugs_found)}")
            for bug in result.bugs_found[:3]:  # Show first 3
                print(f"    Line {bug.line}: {bug.bug_type} ({bug.source})")
        else:
            print(f"\n  Bugs found: 0")
        
        # Print verdicts
        print()
        for checker, verdict in result.checker_verdicts.items():
            v = verdict["verdict"]
            if v == "CORRECT":
                print(f"  ✓ {checker}: CORRECT")
                summary_stats[checker]["correct"] += 1
            elif v == "INCORRECT":
                reason = verdict.get("reason", "")[:50]
                print(f"  ✗ {checker}: INCORRECT - {reason}")
                summary_stats[checker]["incorrect"] += 1
            else:
                print(f"  ? {checker}: UNCERTAIN")
                summary_stats[checker]["uncertain"] += 1
        
        print()
    
    # Print summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    total_bugs = sum(len(r.bugs_found) for r in all_results)
    proven_bugs = sum(
        len([b for b in r.bugs_found if b.confidence >= 0.9])
        for r in all_results
    )
    
    print(f"\nTotal bugs detected: {total_bugs} ({proven_bugs} high-confidence)")
    print(f"\n{'Checker':<12} {'Correct':>10} {'Incorrect':>10} {'Uncertain':>10}")
    print("-" * 44)
    
    for checker in checkers:
        stats = summary_stats[checker]
        print(f"{checker:<12} {stats['correct']:>10} {stats['incorrect']:>10} {stats['uncertain']:>10}")
    
    print("=" * 70)
    
    # Save results
    output_dir = os.path.dirname(results_path)
    eval_path = os.path.join(output_dir, "evaluation_testing.json")
    
    with open(eval_path, "w") as f:
        json.dump({
            "method": "testing",
            "total_bugs_found": total_bugs,
            "proven_bugs": proven_bugs,
            "summary": summary_stats,
            "results": [
                {
                    "filename": r.filename,
                    "bugs_found": [
                        {
                            "line": b.line,
                            "type": b.bug_type,
                            "message": b.message,
                            "source": b.source,
                            "confidence": b.confidence,
                        }
                        for b in r.bugs_found
                    ],
                    "execution_success": r.execution_success,
                    "verdicts": r.checker_verdicts,
                }
                for r in all_results
            ],
        }, f, indent=2)
    
    print(f"\nResults saved to: {eval_path}")
    
    return summary_stats


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python testing_eval.py <results.json>")
        print()
        print("Evaluates type checker outputs using runtime testing methods:")
        print("  - Exception tracing (catches TypeError, KeyError, AttributeError)")
        print("  - try/except analysis (finds expected errors)")
        print("  - NotRequired TypedDict access detection")
        print("  - beartype runtime type enforcement")
        print("  - Hypothesis property-based testing")
        sys.exit(1)
    
    evaluate_results_testing(sys.argv[1])
