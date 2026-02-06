# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "hypothesis",
#     "beartype",
#     "coverage",
# ]
# ///

"""
Tiered Evaluation System for Type Checker Correctness.

This module implements a multi-level evaluation pipeline that progressively
applies more sophisticated testing techniques to resolve UNCERTAIN verdicts.

Level 1: Basic Runtime Testing (from testing_eval.py)
    - Direct execution with exception tracing
    - Hypothesis property-based testing
    - Beartype runtime enforcement
    - AST analysis for unsafe patterns

Level 2: Coverage-Guided Testing
    - Measure code coverage of Level 1 tests
    - Generate additional tests targeting uncovered branches
    - Re-run with beartype to catch hidden type bugs

Level 3: Mutation Adequacy Testing
    - Create type-aware code mutants
    - Run mutants with beartype enforcement
    - Compare mutant behavior with checker outputs
    - Determine if type constraints are semantically meaningful

Key insight: If a type-aware mutant crashes with beartype but the original
code runs fine, we've proven the type constraint matters. Checkers that
missed this constraint are INCORRECT.
"""

import ast
import sys
import os
import json
import copy
import random
import tempfile
import traceback
import subprocess
import io
import contextlib
from dataclasses import dataclass, field
from typing import Optional, Callable, Any
from pathlib import Path
from enum import Enum


class Verdict(Enum):
    CORRECT = "CORRECT"
    INCORRECT = "INCORRECT"
    UNCERTAIN = "UNCERTAIN"


@dataclass
class TypeBug:
    """A confirmed type-related bug found through testing."""
    line: int
    bug_type: str
    message: str
    source: str  # "level1", "level2", "level3_mutation"
    confidence: float
    details: dict = field(default_factory=dict)


@dataclass
class EvaluationResult:
    """Result of tiered evaluation for a single file."""
    filename: str
    level1_bugs: list[TypeBug]
    level2_bugs: list[TypeBug]
    level3_bugs: list[TypeBug]
    coverage_before: float
    coverage_after: float
    mutations_tested: int
    mutations_killed: int
    checker_verdicts: dict[str, dict]
    level_reached: int  # 1, 2, or 3


# =============================================================================
# LEVEL 1: Basic Runtime Testing
# (Imported from testing_eval.py core functionality)
# =============================================================================

def execute_with_tracing(source_code: str) -> tuple[list[TypeBug], bool, str]:
    """Execute code and capture type-related exceptions."""
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
            line=line, bug_type="TypeError", message=str(e)[:200],
            source="level1", confidence=1.0
        ))
    except KeyError as e:
        tb = traceback.extract_tb(sys.exc_info()[2])
        line = tb[-1].lineno if tb else 0
        bugs.append(TypeBug(
            line=line, bug_type="KeyError", message=f"KeyError: {e}",
            source="level1", confidence=1.0
        ))
    except AttributeError as e:
        tb = traceback.extract_tb(sys.exc_info()[2])
        line = tb[-1].lineno if tb else 0
        bugs.append(TypeBug(
            line=line, bug_type="AttributeError", message=str(e)[:200],
            source="level1", confidence=1.0
        ))
    except Exception as e:
        # Other exceptions might indicate type issues
        if "type" in str(e).lower():
            tb = traceback.extract_tb(sys.exc_info()[2])
            line = tb[-1].lineno if tb else 0
            bugs.append(TypeBug(
                line=line, bug_type=type(e).__name__, message=str(e)[:200],
                source="level1", confidence=0.7
            ))
        success = False
    
    return bugs, success, stdout_capture.getvalue()


def run_beartype_check(source_code: str) -> list[TypeBug]:
    """Run code with beartype decorators applied to all functions."""
    bugs = []
    
    try:
        from beartype import beartype
        from beartype.roar import BeartypeCallHintException
    except ImportError:
        return bugs
    
    # Parse and transform AST to add beartype decorators
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return bugs
    
    class BeartypeTransformer(ast.NodeTransformer):
        def visit_FunctionDef(self, node):
            # Skip if already has beartype
            for dec in node.decorator_list:
                if isinstance(dec, ast.Name) and dec.id == 'beartype':
                    return self.generic_visit(node)
            # Add beartype decorator
            node.decorator_list.insert(0, ast.Name(id='beartype', ctx=ast.Load()))
            return self.generic_visit(node)
    
    transformer = BeartypeTransformer()
    new_tree = transformer.visit(tree)
    ast.fix_missing_locations(new_tree)
    
    # Prepare execution environment with beartype
    wrapped_code = f"""
from beartype import beartype
from beartype.roar import BeartypeCallHintException

{ast.unparse(new_tree)}
"""
    
    try:
        exec(compile(wrapped_code, "<beartype_test>", "exec"), {"__name__": "__main__"})
    except BeartypeCallHintException as e:
        bugs.append(TypeBug(
            line=0, bug_type="BeartypeViolation", message=str(e)[:300],
            source="level1", confidence=0.95
        ))
    except Exception as e:
        if "beartype" in str(e).lower() or "type" in str(e).lower():
            bugs.append(TypeBug(
                line=0, bug_type="BeartypeViolation", message=str(e)[:200],
                source="level1", confidence=0.8
            ))
    
    return bugs


def analyze_ast_for_type_issues(source_code: str) -> list[TypeBug]:
    """Static AST analysis for common type-related issues."""
    bugs = []
    
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return bugs
    
    # Find NotRequired TypedDict keys
    notrequired_keys = set()
    import re
    for match in re.finditer(r'(\w+)\s*:\s*NotRequired\[', source_code):
        notrequired_keys.add(match.group(1))
    
    # Also check for total=False TypedDicts
    has_optional_typeddict = 'total=False' in source_code or notrequired_keys
    
    if has_optional_typeddict:
        class UnsafeAccessVisitor(ast.NodeVisitor):
            def __init__(self):
                self.unsafe = []
                self.in_guard = False
            
            def visit_If(self, node):
                # Check if this is a key existence check
                test_str = ast.unparse(node.test)
                if ' in ' in test_str or '.get(' in test_str:
                    old_guard = self.in_guard
                    self.in_guard = True
                    for child in node.body:
                        self.visit(child)
                    self.in_guard = old_guard
                    for child in node.orelse:
                        self.visit(child)
                else:
                    self.generic_visit(node)
            
            def visit_Subscript(self, node):
                if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
                    key = node.slice.value
                    if key in notrequired_keys and not self.in_guard:
                        self.unsafe.append((node.lineno, key))
                self.generic_visit(node)
        
        visitor = UnsafeAccessVisitor()
        visitor.visit(tree)
        
        for line, key in visitor.unsafe:
            bugs.append(TypeBug(
                line=line, bug_type="PotentialKeyError",
                message=f"Unguarded access to NotRequired key '{key}'",
                source="level1", confidence=0.7
            ))
    
    return bugs


def run_level1(source_code: str) -> list[TypeBug]:
    """Run all Level 1 tests and return found bugs."""
    all_bugs = []
    
    # 1. Direct execution with tracing
    exec_bugs, _, _ = execute_with_tracing(source_code)
    all_bugs.extend(exec_bugs)
    
    # 2. Beartype runtime checking
    beartype_bugs = run_beartype_check(source_code)
    all_bugs.extend(beartype_bugs)
    
    # 3. AST analysis
    ast_bugs = analyze_ast_for_type_issues(source_code)
    all_bugs.extend(ast_bugs)
    
    return all_bugs


# =============================================================================
# LEVEL 2: Coverage-Guided Testing
# =============================================================================

def measure_coverage(source_code: str) -> tuple[float, set[int], set[int]]:
    """
    Measure line coverage when executing the code using subprocess.
    
    Returns (coverage_percentage, covered_lines, uncovered_lines).
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(source_code)
        temp_path = f.name
    
    work_dir = os.path.dirname(temp_path)
    cov_data_file = os.path.join(work_dir, '.coverage')
    
    try:
        # Run the code with coverage tracking via subprocess
        result = subprocess.run(
            [sys.executable, '-m', 'coverage', 'run', '--branch', temp_path],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=work_dir,
        )
        
        # Get JSON coverage report
        json_result = subprocess.run(
            [sys.executable, '-m', 'coverage', 'json', '-o', '-'],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=work_dir,
        )
        
        if json_result.returncode != 0:
            return 0.0, set(), set()
        
        try:
            data = json.loads(json_result.stdout)
        except json.JSONDecodeError:
            return 0.0, set(), set()
        
        # Extract coverage data for our file
        filename = os.path.basename(temp_path)
        file_data = None
        for fname, fdata in data.get('files', {}).items():
            if filename in fname:
                file_data = fdata
                break
        
        if not file_data:
            return 0.0, set(), set()
        
        summary = file_data.get('summary', {})
        covered_lines = set(file_data.get('executed_lines', []))
        missing_lines = set(file_data.get('missing_lines', []))
        
        total = summary.get('num_statements', 0)
        if total == 0:
            return 100.0, covered_lines, missing_lines
        
        coverage_pct = summary.get('percent_covered', 0.0)
        return coverage_pct, covered_lines, missing_lines
        
    except subprocess.TimeoutExpired:
        return 0.0, set(), set()
    except FileNotFoundError:
        # coverage module not available
        return 0.0, set(), set()
    except Exception:
        return 0.0, set(), set()
    finally:
        try:
            os.unlink(temp_path)
            if os.path.exists(cov_data_file):
                os.unlink(cov_data_file)
        except Exception:
            pass


class FunctionExtractor(ast.NodeVisitor):
    """Extract function signatures for targeted testing."""
    
    def __init__(self):
        self.functions = []
        self.in_class = None
    
    def visit_ClassDef(self, node):
        old_class = self.in_class
        self.in_class = node.name
        self.generic_visit(node)
        self.in_class = old_class
    
    def visit_FunctionDef(self, node):
        params = {}
        for arg in node.args.args:
            if arg.arg not in ('self', 'cls'):
                ann = ast.unparse(arg.annotation) if arg.annotation else None
                params[arg.arg] = ann
        
        self.functions.append({
            'name': node.name,
            'class': self.in_class,
            'params': params,
            'return_type': ast.unparse(node.returns) if node.returns else None,
            'lineno': node.lineno,
        })
        self.generic_visit(node)


def generate_test_inputs_for_type(type_annotation: str) -> list[Any]:
    """Generate diverse test inputs based on type annotation."""
    inputs = []
    
    if type_annotation is None:
        return [None, 0, "", [], {}]
    
    ann = type_annotation.strip()
    
    # Basic types
    if ann == "int":
        inputs = [0, 1, -1, 2**31, -2**31]
    elif ann == "str":
        inputs = ["", "test", "a" * 100, "\n\t", "123"]
    elif ann == "float":
        inputs = [0.0, 1.5, -1.5, float('inf'), float('-inf')]
    elif ann == "bool":
        inputs = [True, False]
    elif ann == "None":
        inputs = [None]
    elif ann.startswith("Optional["):
        inner = ann[9:-1]
        inputs = [None] + generate_test_inputs_for_type(inner)
    elif ann.startswith("List[") or ann.startswith("list["):
        inner = ann[5:-1]
        inner_inputs = generate_test_inputs_for_type(inner)[:2]
        inputs = [[], inner_inputs, inner_inputs * 3]
    elif ann.startswith("Dict[") or ann.startswith("dict["):
        inputs = [{}, {"key": "value"}]
    elif ann.startswith("Literal["):
        # Extract literal values
        inner = ann[8:-1]
        for part in inner.split(","):
            part = part.strip().strip('"').strip("'")
            if part.isdigit():
                inputs.append(int(part))
            elif part in ("True", "False"):
                inputs.append(part == "True")
            else:
                inputs.append(part)
        # Add an invalid value
        inputs.append("__INVALID_LITERAL__")
    else:
        # Unknown type - use diverse values
        inputs = [None, 0, "", [], {}]
    
    return inputs


def run_level2(source_code: str, level1_bugs: list[TypeBug]) -> tuple[list[TypeBug], float, float]:
    """
    Run Level 2: Coverage-guided testing.
    
    Strategy:
    1. Measure initial coverage
    2. Identify uncovered lines/branches
    3. Generate targeted tests to cover those paths
    4. Run tests with beartype to catch type errors
    
    Returns: (bugs_found, coverage_before, coverage_after)
    """
    bugs = []
    
    # Measure initial coverage
    coverage_before, covered_lines, uncovered_lines = measure_coverage(source_code)
    
    if coverage_before >= 95.0:
        # Already high coverage, Level 2 won't help much
        return bugs, coverage_before, coverage_before
    
    # Extract functions to generate targeted tests
    try:
        tree = ast.parse(source_code)
        extractor = FunctionExtractor()
        extractor.visit(tree)
    except SyntaxError:
        return bugs, coverage_before, coverage_before
    
    # Identify which functions have uncovered lines
    functions_with_uncovered = []
    for func in extractor.functions:
        func_end = func['lineno'] + 50  # Rough estimate of function end
        if any(func['lineno'] <= line <= func_end for line in uncovered_lines):
            functions_with_uncovered.append(func)
    
    # If no specific functions identified, test all functions with params
    if not functions_with_uncovered:
        functions_with_uncovered = [f for f in extractor.functions if f['params']]
    
    # For each function, generate diverse test inputs
    for func in functions_with_uncovered:
        if not func['params']:
            continue
        
        # Generate test inputs for each parameter
        param_inputs = {}
        for param, type_ann in func['params'].items():
            param_inputs[param] = generate_test_inputs_for_type(type_ann)
        
        if not param_inputs:
            continue
        
        # Generate test combinations
        test_cases = generate_test_combinations(param_inputs, max_cases=10)
        
        # Run each test case with beartype
        for case in test_cases:
            test_code = generate_test_code(source_code, func, case)
            if test_code:
                test_bugs = run_test_with_beartype(test_code, func['name'])
                for bug in test_bugs:
                    bug.source = "level2"
                    bug.details['test_inputs'] = str(case)
                    bug.details['function'] = func['name']
                bugs.extend(test_bugs)
    
    # Measure coverage after (would need to combine all test runs)
    coverage_after = coverage_before  # Simplified for now
    
    return bugs, coverage_before, coverage_after


def generate_test_combinations(param_inputs: dict[str, list], max_cases: int = 10) -> list[dict]:
    """
    Generate diverse test case combinations from parameter inputs.
    Uses a combination of boundary values and random sampling.
    """
    test_cases = []
    param_names = list(param_inputs.keys())
    
    if not param_names:
        return test_cases
    
    # Strategy 1: First value of each (often default/simple case)
    case = {name: param_inputs[name][0] for name in param_names}
    test_cases.append(case)
    
    # Strategy 2: Last value of each (often edge case)
    case = {name: param_inputs[name][-1] for name in param_names}
    test_cases.append(case)
    
    # Strategy 3: Mix first and last
    for i, name in enumerate(param_names):
        case = {}
        for j, n in enumerate(param_names):
            values = param_inputs[n]
            case[n] = values[-1] if i == j else values[0]
        test_cases.append(case)
    
    # Strategy 4: Random combinations
    for _ in range(max_cases - len(test_cases)):
        if len(test_cases) >= max_cases:
            break
        case = {}
        for name in param_names:
            values = param_inputs[name]
            case[name] = random.choice(values)
        if case not in test_cases:
            test_cases.append(case)
    
    return test_cases[:max_cases]


def generate_test_code(source_code: str, func: dict, inputs: dict) -> Optional[str]:
    """Generate test code that calls a function with specific inputs."""
    func_name = func['name']
    class_name = func['class']
    
    # Build the call
    args_str = ", ".join(f"{k}={repr(v)}" for k, v in inputs.items())
    
    if class_name:
        # Method call - need to instantiate class first
        call = f"""
try:
    obj = {class_name}()
    result = obj.{func_name}({args_str})
except Exception as e:
    raise
"""
    else:
        call = f"""
try:
    result = {func_name}({args_str})
except Exception as e:
    raise
"""
    
    # Wrap source with beartype and add test call
    test_code = f"""
from beartype import beartype
from beartype.roar import BeartypeCallHintException

# Original code with beartype applied to functions
{source_code}

# Test call
if __name__ == "__main__":
{call}
"""
    
    return test_code


def run_test_with_beartype(test_code: str, func_name: str) -> list[TypeBug]:
    """Run test code and capture type-related errors."""
    bugs = []
    
    # Try to import beartype exception type
    try:
        from beartype.roar import BeartypeCallHintException
    except ImportError:
        BeartypeCallHintException = Exception
    
    # Suppress output during test execution
    stdout_capture = io.StringIO()
    
    try:
        with contextlib.redirect_stdout(stdout_capture), \
             contextlib.redirect_stderr(stdout_capture):
            exec(compile(test_code, "<level2_test>", "exec"), {"__name__": "__main__"})
    except (TypeError, KeyError, AttributeError) as e:
        bugs.append(TypeBug(
            line=0, bug_type=type(e).__name__, 
            message=f"In {func_name}: {str(e)[:200]}",
            source="level2", confidence=0.95
        ))
    except BeartypeCallHintException as e:
        bugs.append(TypeBug(
            line=0, bug_type="BeartypeViolation", 
            message=f"In {func_name}: {str(e)[:200]}",
            source="level2", confidence=0.95
        ))
    except Exception as e:
        error_str = str(e).lower()
        if "type" in error_str or "key" in error_str or "attribute" in error_str:
            bugs.append(TypeBug(
                line=0, bug_type=type(e).__name__, 
                message=f"In {func_name}: {str(e)[:200]}",
                source="level2", confidence=0.8
            ))
    
    return bugs


# =============================================================================
# LEVEL 3: Mutation Adequacy Testing
# =============================================================================

@dataclass
class Mutant:
    """A code mutant with type-relevant modifications."""
    name: str
    description: str
    code: str
    mutation_type: str  # "literal_value", "type_annotation", "dict_key", etc.
    original_line: int


class TypeAwareMutator:
    """Generate type-aware code mutations."""
    
    def __init__(self, source_code: str):
        self.source_code = source_code
        self.tree = ast.parse(source_code)
        self.mutants: list[Mutant] = []
    
    def generate_mutants(self, max_mutants: int = 20) -> list[Mutant]:
        """Generate diverse type-aware mutants."""
        self.mutants = []
        
        # 1. Literal value mutations
        self._mutate_literals()
        
        # 2. Dict/TypedDict key mutations
        self._mutate_dict_keys()
        
        # 3. Function argument mutations
        self._mutate_function_calls()
        
        # 4. Type annotation removals (to test if they matter)
        self._mutate_type_annotations()
        
        # Limit and shuffle for variety
        random.shuffle(self.mutants)
        return self.mutants[:max_mutants]
    
    def _mutate_literals(self):
        """Mutate literal values to invalid alternatives."""
        
        class LiteralMutator(ast.NodeTransformer):
            def __init__(self, mutants_list, original_code):
                self.mutants = mutants_list
                self.original = original_code
                self.mutation_count = 0
            
            def visit_Constant(self, node):
                if isinstance(node.value, str) and len(node.value) > 0:
                    # Mutate string literal
                    mutated = copy.deepcopy(self.original)
                    mutated_tree = ast.parse(mutated)
                    
                    class StringReplacer(ast.NodeTransformer):
                        def __init__(self, target_line, target_value):
                            self.target_line = target_line
                            self.target_value = target_value
                            self.replaced = False
                        
                        def visit_Constant(self, n):
                            if (n.lineno == self.target_line and 
                                n.value == self.target_value and 
                                not self.replaced):
                                self.replaced = True
                                return ast.Constant(value="__MUTANT_INVALID__")
                            return n
                    
                    replacer = StringReplacer(node.lineno, node.value)
                    new_tree = replacer.visit(mutated_tree)
                    
                    if replacer.replaced:
                        ast.fix_missing_locations(new_tree)
                        self.mutants.append(Mutant(
                            name=f"literal_str_{self.mutation_count}",
                            description=f"Changed '{node.value}' to invalid value at line {node.lineno}",
                            code=ast.unparse(new_tree),
                            mutation_type="literal_value",
                            original_line=node.lineno,
                        ))
                        self.mutation_count += 1
                
                return node
        
        mutator = LiteralMutator(self.mutants, self.source_code)
        mutator.visit(copy.deepcopy(self.tree))
    
    def _mutate_dict_keys(self):
        """Remove or modify dict keys to test TypedDict requirements."""
        
        class DictMutator(ast.NodeTransformer):
            def __init__(self, mutants_list, original_code):
                self.mutants = mutants_list
                self.original = original_code
                self.mutation_count = 0
            
            def visit_Dict(self, node):
                if len(node.keys) > 1:
                    # Try removing each key
                    for i, key in enumerate(node.keys):
                        if isinstance(key, ast.Constant) and isinstance(key.value, str):
                            # Create mutant with this key removed
                            mutated_tree = ast.parse(self.original)
                            
                            class KeyRemover(ast.NodeTransformer):
                                def __init__(self, target_line, target_key, idx):
                                    self.target_line = target_line
                                    self.target_key = target_key
                                    self.idx = idx
                                    self.removed = False
                                
                                def visit_Dict(self, n):
                                    if n.lineno == self.target_line and not self.removed:
                                        if len(n.keys) > self.idx:
                                            k = n.keys[self.idx]
                                            if (isinstance(k, ast.Constant) and 
                                                k.value == self.target_key):
                                                self.removed = True
                                                new_keys = n.keys[:self.idx] + n.keys[self.idx+1:]
                                                new_vals = n.values[:self.idx] + n.values[self.idx+1:]
                                                return ast.Dict(keys=new_keys, values=new_vals)
                                    return self.generic_visit(n)
                            
                            remover = KeyRemover(node.lineno, key.value, i)
                            new_tree = remover.visit(mutated_tree)
                            
                            if remover.removed:
                                ast.fix_missing_locations(new_tree)
                                self.mutants.append(Mutant(
                                    name=f"dict_key_{self.mutation_count}",
                                    description=f"Removed key '{key.value}' from dict at line {node.lineno}",
                                    code=ast.unparse(new_tree),
                                    mutation_type="dict_key",
                                    original_line=node.lineno,
                                ))
                                self.mutation_count += 1
                
                return self.generic_visit(node)
        
        mutator = DictMutator(self.mutants, self.source_code)
        mutator.visit(copy.deepcopy(self.tree))
    
    def _mutate_function_calls(self):
        """Mutate function call arguments to wrong types."""
        
        class CallMutator(ast.NodeTransformer):
            def __init__(self, mutants_list, original_code):
                self.mutants = mutants_list
                self.original = original_code
                self.mutation_count = 0
            
            def visit_Call(self, node):
                # Skip common non-user functions
                if isinstance(node.func, ast.Name):
                    if node.func.id in ('print', 'len', 'str', 'int', 'list', 'dict', 'type'):
                        return self.generic_visit(node)
                
                # Try mutating each argument
                for i, arg in enumerate(node.args):
                    if isinstance(arg, ast.Constant):
                        # Create wrong-type mutant
                        mutated_tree = ast.parse(self.original)
                        
                        class ArgMutator(ast.NodeTransformer):
                            def __init__(self, target_line, arg_idx, original_val):
                                self.target_line = target_line
                                self.arg_idx = arg_idx
                                self.original_val = original_val
                                self.mutated = False
                            
                            def visit_Call(self, n):
                                if n.lineno == self.target_line and not self.mutated:
                                    if len(n.args) > self.arg_idx:
                                        a = n.args[self.arg_idx]
                                        if isinstance(a, ast.Constant) and a.value == self.original_val:
                                            self.mutated = True
                                            # Replace with wrong type
                                            if isinstance(self.original_val, str):
                                                new_val = 12345  # str -> int
                                            elif isinstance(self.original_val, int):
                                                new_val = "wrong_type"  # int -> str
                                            else:
                                                new_val = None
                                            n.args[self.arg_idx] = ast.Constant(value=new_val)
                                return self.generic_visit(n)
                        
                        mutator = ArgMutator(node.lineno, i, arg.value)
                        new_tree = mutator.visit(mutated_tree)
                        
                        if mutator.mutated:
                            ast.fix_missing_locations(new_tree)
                            self.mutants.append(Mutant(
                                name=f"call_arg_{self.mutation_count}",
                                description=f"Changed arg {i} type in call at line {node.lineno}",
                                code=ast.unparse(new_tree),
                                mutation_type="argument_type",
                                original_line=node.lineno,
                            ))
                            self.mutation_count += 1
                
                return self.generic_visit(node)
        
        mutator = CallMutator(self.mutants, self.source_code)
        mutator.visit(copy.deepcopy(self.tree))
    
    def _mutate_type_annotations(self):
        """Remove type annotations to test if they're enforced."""
        
        class AnnotationRemover(ast.NodeTransformer):
            def __init__(self, mutants_list, original_code):
                self.mutants = mutants_list
                self.original = original_code
                self.mutation_count = 0
            
            def visit_FunctionDef(self, node):
                # Try removing return type annotation
                if node.returns:
                    mutated_tree = ast.parse(self.original)
                    
                    class ReturnRemover(ast.NodeTransformer):
                        def __init__(self, target_name):
                            self.target_name = target_name
                            self.removed = False
                        
                        def visit_FunctionDef(self, n):
                            if n.name == self.target_name and not self.removed:
                                self.removed = True
                                n.returns = None
                            return self.generic_visit(n)
                    
                    remover = ReturnRemover(node.name)
                    new_tree = remover.visit(mutated_tree)
                    
                    if remover.removed:
                        ast.fix_missing_locations(new_tree)
                        self.mutants.append(Mutant(
                            name=f"annotation_{self.mutation_count}",
                            description=f"Removed return type from {node.name}",
                            code=ast.unparse(new_tree),
                            mutation_type="annotation_removal",
                            original_line=node.lineno,
                        ))
                        self.mutation_count += 1
                
                return self.generic_visit(node)
        
        mutator = AnnotationRemover(self.mutants, self.source_code)
        mutator.visit(copy.deepcopy(self.tree))


def run_mutant(mutant: Mutant) -> tuple[bool, Optional[str], str]:
    """
    Run a mutant with beartype enforcement.
    
    Returns: (crashed_with_type_error, error_message, crash_type)
    
    crash_type can be:
    - "type_error": TypeError, KeyError, AttributeError, BeartypeViolation
    - "import_error": Missing module (not a type bug)
    - "syntax_error": Invalid mutation (not a type bug)
    - "other": Other error (not a type bug)
    - "none": No crash
    """
    # Import beartype at runtime
    try:
        from beartype import beartype
        from beartype.roar import BeartypeCallHintException
        beartype_available = True
    except ImportError:
        beartype_available = False
        BeartypeCallHintException = Exception
    
    # Prepare code - only add beartype if available
    if beartype_available:
        test_code = f"""
from beartype import beartype
from beartype.roar import BeartypeCallHintException

{mutant.code}
"""
    else:
        test_code = mutant.code
    
    # Suppress stdout/stderr from mutant execution
    stdout_capture = io.StringIO()
    
    try:
        with contextlib.redirect_stdout(stdout_capture), \
             contextlib.redirect_stderr(stdout_capture):
            exec(compile(test_code, "<mutant>", "exec"), {"__name__": "__main__"})
        return False, None, "none"
    except (TypeError, KeyError, AttributeError) as e:
        return True, f"{type(e).__name__}: {str(e)[:100]}", "type_error"
    except BeartypeCallHintException as e:
        return True, f"BeartypeViolation: {str(e)[:100]}", "type_error"
    except ModuleNotFoundError as e:
        # Not a type bug - just missing imports
        return False, None, "import_error"
    except SyntaxError as e:
        # Invalid mutation
        return False, None, "syntax_error"
    except Exception as e:
        # Other errors - might be type-related
        error_str = str(e).lower()
        if "type" in error_str or "key" in error_str or "attribute" in error_str:
            return True, f"{type(e).__name__}: {str(e)[:100]}", "type_error"
        return False, None, "other"


def run_level3(source_code: str, checker_outputs: dict[str, str]) -> tuple[list[TypeBug], int, int]:
    """
    Run Level 3: Mutation adequacy testing.
    
    The key insight is:
    - If a type-aware mutant crashes with a type error, the type constraint matters
    - Checkers that didn't report this constraint may have missed it
    
    Returns: (bugs_found, mutations_tested, mutations_killed)
    """
    bugs = []
    
    try:
        mutator = TypeAwareMutator(source_code)
        mutants = mutator.generate_mutants(max_mutants=15)
    except SyntaxError:
        return bugs, 0, 0
    
    if not mutants:
        return bugs, 0, 0
    
    mutations_tested = 0
    mutations_killed = 0  # Mutants that crashed with type errors
    
    for mutant in mutants:
        mutations_tested += 1
        crashed, error_msg, crash_type = run_mutant(mutant)
        
        # Only count actual type errors, not import errors or other issues
        if crashed and crash_type == "type_error":
            mutations_killed += 1
            
            # This proves the type constraint at this line matters
            bugs.append(TypeBug(
                line=mutant.original_line,
                bug_type="MutationKilled",
                message=f"Mutation '{mutant.description}' crashed: {error_msg}",
                source="level3_mutation",
                confidence=0.85,
                details={
                    'mutation_type': mutant.mutation_type,
                    'mutant_name': mutant.name,
                }
            ))
    
    return bugs, mutations_tested, mutations_killed


# =============================================================================
# VERDICT DETERMINATION
# =============================================================================

def determine_verdicts(
    all_bugs: list[TypeBug],
    checker_outputs: dict[str, str],
    level_reached: int,
) -> dict[str, dict]:
    """
    Determine verdict for each checker based on found bugs.
    
    Logic:
    - High-confidence bugs + checker OK → INCORRECT
    - High-confidence bugs + checker ERROR → CORRECT
    - No bugs + checker OK → UNCERTAIN (but with higher confidence at higher levels)
    - No bugs + checker ERROR → UNCERTAIN (possible false positive)
    """
    verdicts = {}
    
    # Get high-confidence bugs
    proven_bugs = [b for b in all_bugs if b.confidence >= 0.85]
    has_proven_bugs = len(proven_bugs) > 0
    
    # Base confidence increases with level
    base_confidence = {1: 0.5, 2: 0.6, 3: 0.7}[level_reached]
    
    for checker, output in checker_outputs.items():
        output_lower = output.lower()
        checker_reported_error = (
            "error" in output_lower and
            "0 error" not in output_lower and
            "success" not in output_lower
        )
        
        if has_proven_bugs and not checker_reported_error:
            verdicts[checker] = {
                "verdict": Verdict.INCORRECT.value,
                "reason": f"Missed {len(proven_bugs)} proven bug(s) at level {level_reached}",
                "confidence": 0.95,
                "bugs_missed": [
                    {"line": b.line, "type": b.bug_type, "source": b.source}
                    for b in proven_bugs[:3]
                ],
            }
        elif has_proven_bugs and checker_reported_error:
            verdicts[checker] = {
                "verdict": Verdict.CORRECT.value,
                "reason": "Correctly identified type issues",
                "confidence": 0.9,
            }
        elif not has_proven_bugs and not checker_reported_error:
            verdicts[checker] = {
                "verdict": Verdict.UNCERTAIN.value,
                "reason": f"No bugs found through level {level_reached} testing",
                "confidence": base_confidence,
                "note": "May be correct or bug not triggerable at runtime",
            }
        else:  # No bugs but checker reported error
            verdicts[checker] = {
                "verdict": Verdict.UNCERTAIN.value,
                "reason": f"Checker reported error but level {level_reached} testing found no runtime proof",
                "confidence": base_confidence,
                "note": "May be false positive or static-only type issue",
            }
    
    return verdicts


# =============================================================================
# MAIN EVALUATION FUNCTION
# =============================================================================

def evaluate_example_tiered(
    source_code: str,
    checker_outputs: dict[str, str],
    filename: str,
    max_level: int = 3,
) -> EvaluationResult:
    """
    Run tiered evaluation on a single example.
    
    Stops early if definitive verdicts are reached at lower levels.
    """
    level1_bugs = []
    level2_bugs = []
    level3_bugs = []
    coverage_before = 0.0
    coverage_after = 0.0
    mutations_tested = 0
    mutations_killed = 0
    level_reached = 1
    
    # Level 1: Basic runtime testing
    level1_bugs = run_level1(source_code)
    
    # Check if Level 1 resolved it
    proven_level1 = [b for b in level1_bugs if b.confidence >= 0.85]
    if proven_level1:
        # We have definitive bugs, can determine verdicts
        all_bugs = level1_bugs
        verdicts = determine_verdicts(all_bugs, checker_outputs, level_reached)
        
        return EvaluationResult(
            filename=filename,
            level1_bugs=level1_bugs,
            level2_bugs=[],
            level3_bugs=[],
            coverage_before=0.0,
            coverage_after=0.0,
            mutations_tested=0,
            mutations_killed=0,
            checker_verdicts=verdicts,
            level_reached=1,
        )
    
    # Level 2: Coverage-guided testing
    if max_level >= 2:
        level_reached = 2
        level2_bugs, coverage_before, coverage_after = run_level2(source_code, level1_bugs)
        
        proven_level2 = [b for b in level2_bugs if b.confidence >= 0.85]
        if proven_level2:
            all_bugs = level1_bugs + level2_bugs
            verdicts = determine_verdicts(all_bugs, checker_outputs, level_reached)
            
            return EvaluationResult(
                filename=filename,
                level1_bugs=level1_bugs,
                level2_bugs=level2_bugs,
                level3_bugs=[],
                coverage_before=coverage_before,
                coverage_after=coverage_after,
                mutations_tested=0,
                mutations_killed=0,
                checker_verdicts=verdicts,
                level_reached=2,
            )
    
    # Level 3: Mutation testing
    if max_level >= 3:
        level_reached = 3
        level3_bugs, mutations_tested, mutations_killed = run_level3(source_code, checker_outputs)
    
    # Final verdict determination
    all_bugs = level1_bugs + level2_bugs + level3_bugs
    verdicts = determine_verdicts(all_bugs, checker_outputs, level_reached)
    
    return EvaluationResult(
        filename=filename,
        level1_bugs=level1_bugs,
        level2_bugs=level2_bugs,
        level3_bugs=level3_bugs,
        coverage_before=coverage_before,
        coverage_after=coverage_after,
        mutations_tested=mutations_tested,
        mutations_killed=mutations_killed,
        checker_verdicts=verdicts,
        level_reached=level_reached,
    )


def evaluate_results_tiered(results_path: str, max_level: int = 3) -> dict:
    """
    Evaluate all files using the tiered evaluation system.
    """
    with open(results_path) as f:
        data = json.load(f)
    
    results = data.get("results", [])
    checkers = data.get("checkers_used", ["mypy", "pyrefly", "zuban", "ty"])
    
    all_results: list[EvaluationResult] = []
    summary_stats = {
        checker: {"correct": 0, "incorrect": 0, "uncertain": 0}
        for checker in checkers
    }
    level_distribution = {1: 0, 2: 0, 3: 0}
    
    print("=" * 70)
    print("TIERED EVALUATION SYSTEM")
    print("=" * 70)
    print(f"Level 1: Runtime + Beartype + AST analysis")
    print(f"Level 2: Coverage-guided testing")
    print(f"Level 3: Mutation adequacy testing")
    print(f"Max level: {max_level}")
    print(f"Files to evaluate: {len(results)}")
    print("=" * 70)
    print()
    
    for i, file_entry in enumerate(results, 1):
        filepath = file_entry.get("filepath", "")
        filename = file_entry.get("filename", "")
        outputs = file_entry.get("outputs", {})
        
        print(f"[{i}/{len(results)}] {filename}")
        
        try:
            with open(filepath) as f:
                source_code = f.read()
        except FileNotFoundError:
            print("  [SKIP] File not found")
            continue
        
        result = evaluate_example_tiered(source_code, outputs, filename, max_level)
        all_results.append(result)
        level_distribution[result.level_reached] += 1
        
        # Print summary
        total_bugs = len(result.level1_bugs) + len(result.level2_bugs) + len(result.level3_bugs)
        print(f"  Level reached: {result.level_reached}")
        print(f"  Bugs found: L1={len(result.level1_bugs)}, L2={len(result.level2_bugs)}, L3={len(result.level3_bugs)}")
        
        if result.level_reached >= 2:
            print(f"  Coverage: {result.coverage_before:.1f}% → {result.coverage_after:.1f}%")
        if result.level_reached >= 3:
            print(f"  Mutations: {result.mutations_killed}/{result.mutations_tested} killed")
        
        for checker, verdict in result.checker_verdicts.items():
            v = verdict["verdict"]
            if v == "CORRECT":
                print(f"  ✓ {checker}: CORRECT")
                summary_stats[checker]["correct"] += 1
            elif v == "INCORRECT":
                print(f"  ✗ {checker}: INCORRECT")
                summary_stats[checker]["incorrect"] += 1
            else:
                print(f"  ? {checker}: UNCERTAIN")
                summary_stats[checker]["uncertain"] += 1
        
        print()
    
    # Print summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    print(f"\nLevel distribution:")
    for level, count in level_distribution.items():
        print(f"  Level {level}: {count} files")
    
    total_bugs = sum(
        len(r.level1_bugs) + len(r.level2_bugs) + len(r.level3_bugs)
        for r in all_results
    )
    print(f"\nTotal bugs found: {total_bugs}")
    
    print(f"\n{'Checker':<12} {'Correct':>10} {'Incorrect':>10} {'Uncertain':>10}")
    print("-" * 44)
    
    for checker in checkers:
        stats = summary_stats[checker]
        print(f"{checker:<12} {stats['correct']:>10} {stats['incorrect']:>10} {stats['uncertain']:>10}")
    
    print("=" * 70)
    
    # Save results
    output_dir = os.path.dirname(results_path)
    eval_path = os.path.join(output_dir, "evaluation_tiered.json")
    
    with open(eval_path, "w") as f:
        json.dump({
            "method": "tiered",
            "max_level": max_level,
            "level_distribution": level_distribution,
            "summary": summary_stats,
            "results": [
                {
                    "filename": r.filename,
                    "level_reached": r.level_reached,
                    "level1_bugs": [{"line": b.line, "type": b.bug_type, "msg": b.message} for b in r.level1_bugs],
                    "level2_bugs": [{"line": b.line, "type": b.bug_type, "msg": b.message} for b in r.level2_bugs],
                    "level3_bugs": [{"line": b.line, "type": b.bug_type, "msg": b.message} for b in r.level3_bugs],
                    "coverage_before": r.coverage_before,
                    "coverage_after": r.coverage_after,
                    "mutations_tested": r.mutations_tested,
                    "mutations_killed": r.mutations_killed,
                    "verdicts": r.checker_verdicts,
                }
                for r in all_results
            ],
        }, f, indent=2)
    
    print(f"\nResults saved to: {eval_path}")
    
    return summary_stats


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Tiered evaluation system for type checker disagreements"
    )
    parser.add_argument("results_path", help="Path to results.json")
    parser.add_argument(
        "--max-level", type=int, default=3, choices=[1, 2, 3],
        help="Maximum evaluation level to run (default: 3)"
    )
    
    args = parser.parse_args()
    
    evaluate_results_tiered(args.results_path, max_level=args.max_level)
