from typing import TypeVar, ParamSpec, Callable, reveal_type, Concatenate

R_OUTER = TypeVar("R_OUTER")
P_OUTER = ParamSpec("P_OUTER")

R_INNER = TypeVar("R_INNER")
P_INNER = ParamSpec("P_INNER") # This ParamSpec is for the inner callable

# A higher-order function that produces a factory, where the inner factory itself
# returns a callable with a Concatenate in its signature.
def create_conditional_executor_factory(
    condition: bool
) -> Callable[P_OUTER, Callable[Concatenate[str, P_INNER], R_INNER]]:
    """
    Returns a factory function. The factory function (itself determined by P_OUTER)
    then returns an 'executor' callable. This executor callable has `Concatenate[str, P_INNER]`.
    """
    def outer_factory(*args: P_OUTER.args, **kwargs: P_OUTER.kwargs) -> Callable[Concatenate[str, P_INNER], R_INNER]:
        print(f"Outer factory called with args: {args}, kwargs: {kwargs}")
        
        def executor(log_msg: str, *inner_args: P_INNER.args, **inner_kwargs: P_INNER.kwargs) -> R_INNER:
            print(f"Executor received: '{log_msg}' and inner_args: {inner_args}, inner_kwargs: {inner_kwargs}")
            if condition:
                # Example logic: return length of inner_args
                return len(inner_args) # type: ignore[return-value] # R_INNER assumed to be int here
            else:
                # Example logic: return sum of inner_args
                return sum(inner_args) # type: ignore[operator, return-value] # R_INNER assumed to be int
        return executor
    return outer_factory

# --- Usage ---
# P_OUTER will be empty here, as `create_conditional_executor_factory` takes no direct P_OUTER args.
# The returned `inner_factory_true` will then accept P_INNER for its executor.
inner_factory_true = create_conditional_executor_factory(True)() # Calls outer_factory with empty P_OUTER

reveal_type(inner_factory_true) # Expected: Callable[Concatenate[str, P_INNER], R_INNER]

# Call the executor, providing the `str` for Concatenate and then P_INNER args.
# P_INNER is flexible, here we pass ints. R_INNER would be inferred as int.
result_len = inner_factory_true("Count elements", 1, 2, 3)
print(f"Result (condition=True): {result_len}") # Expected: 3
reveal_type(result_len) # Expected: int

inner_factory_false = create_conditional_executor_factory(False)()
result_sum = inner_factory_false("Sum elements", 10, 20, x=30)
print(f"Result (condition=False): {result_sum}") # Expected: 30 (sum of 10, 20 assuming x ignored for sum)
reveal_type(result_sum) # Expected: int

print("\nExample demonstrating nested ParamSpec and Concatenate in return types of higher-order functions.")
print("The primary test is the resolution of `Callable[Concatenate[str, P_INNER], R_INNER]` when it's returned by another callable defined with `P_OUTER`.")