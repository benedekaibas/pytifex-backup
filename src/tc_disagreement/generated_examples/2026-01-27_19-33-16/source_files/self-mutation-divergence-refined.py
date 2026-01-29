from typing import TypeVar, Generic, Self, List, Any, Callable

T = TypeVar('T')

class ChainableProcessor(Generic[T]):
    def __init__(self, data: T):
        self._data: T = data
        self._history: List[str] = [f"Initial data: {data}"]

    def add_step(self, step_name: str) -> Self:
        self._history.append(f"Step '{step_name}' applied.")
        return self

    # This method is modified to actually apply the transformation.
    # It takes a function that accepts T but can return Any,
    # and mutates `self._data` in place.
    # The return type `Self` implies the generic type `T` of the instance
    # is maintained. However, the assignment `self._data = func(self._data)`
    # attempts to assign a value of type `Any` to a variable of type `T`.
    # This is a common source of type checker divergence, especially in strict modes,
    # and when combined with the `Self` return type.
    def transform(self, func: Callable[[T], Any]) -> Self:
        # The value `func(self._data)` is of type `Any`.
        # `self._data` is of type `T` (e.g., int, str).
        # Assigning `Any` to `T` is an incompatible assignment for strict type checkers.
        self._data = func(self._data)
        self._history.append(f"Transformation '{func.__name__}' applied. New data type: {type(self._data).__name__}")
        return self

    def get_final_data(self) -> T:
        return self._data

    def get_history(self) -> List[str]:
        return self._history

def process_workflow(initial_data: int) -> List[str]:
    processor_instance = ChainableProcessor(initial_data) # T is bound to `int` for this instance

    # Multi-line chained calls with `Self` return types.
    # The `type: ignore` here is now intended to suppress the potential
    # "incompatible assignment" error that occurs *inside* `transform`.
    # Divergence may occur if checkers handle the scope of `type: ignore`
    # on a chained call differently, or their strictness regarding `Any` to `T` assignments.
    final_processor = processor_instance.add_step("preprocessing").transform(
        lambda x: str(x * 2) # type: ignore[assignment] 
        # This lambda returns a string, while T is int. The internal assignment will be `int = str`.
    ).add_step("postprocessing")

    # This line should ideally trigger a type error: `final_processor` is `ChainableProcessor[int]`,
    # so `get_final_data()` should return `int`. But due to the mutation, it returns `str`.
    # Some checkers might catch this, especially if the internal assignment error was suppressed.
    result_int: int = final_processor.get_final_data()
    print(f"Workflow final data (declared as int, runtime {type(result_int)}): {result_int}")

    return final_processor.get_history()

if __name__ == "__main__":
    history = process_workflow(10)
    print("Workflow History:")
    for entry in history:
        print(f"- {entry}")

    # Another example of a tricky multi-line chain
    my_obj = ChainableProcessor("initial_string") # T is bound to `str` for this instance
    processed = my_obj.add_step("step1")\
                      .add_step("step2")\
                      .transform(lambda s: len(s)) # type: ignore[assignment] 
                      # This lambda returns an int, while T is str. The internal assignment will be `str = int`.

    # Similar to above, this should be a type error as `processed` is `ChainableProcessor[str]`,
    # but `get_final_data()` now returns `int` at runtime.
    result_str: str = processed.get_final_data()
    print(f"Processed data (declared as str, runtime {type(result_str)}): {result_str}")
    print(f"Processed history: {processed.get_history()}")