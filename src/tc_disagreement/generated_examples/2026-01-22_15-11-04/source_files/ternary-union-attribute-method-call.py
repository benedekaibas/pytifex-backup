from typing import Union, Optional, List, reveal_type, Callable

class Validator:
    def is_valid(self) -> bool:
        return True
    def get_message(self) -> str:
        return "Validator is valid."

class ErrorReporter:
    def report_error(self, code: int) -> str:
        return f"Error {code} reported."
    def has_errors(self) -> bool:
        return True # Simplified for example

class NoOp:
    def no_op_action(self) -> None:
        print("No operation performed.")

def process_entity(entity: Union[Validator, ErrorReporter, None]) -> None:
    # Ternary expression involving method calls on Union types
    # The crucial part is type narrowing for the `entity` variable inside the lambda.
    # Checkers should confirm that `entity` is appropriately narrowed
    # for `entity.is_valid()` and `entity.report_error()`.
    action_callable: Callable[[], str] = (
        (lambda: entity.get_message() if entity.is_valid() else "Validator not valid")
        if isinstance(entity, Validator) else
        (lambda: entity.report_error(400) if isinstance(entity, ErrorReporter) and entity.has_errors() else "No error/No reporter")
    )
    reveal_type(action_callable) # N: Revealed type is "def () -> str"

    print(f"Action result: {action_callable()}")

    # More complex ternary, potentially involving multiple methods and `Optional` return
    status_info: Callable[[], Optional[str]] = (
        (lambda: entity.get_message() if entity and entity.is_valid() else None)
        if isinstance(entity, Validator) else
        (lambda: entity.report_error(500) if isinstance(entity, ErrorReporter) else None)
    )
    reveal_type(status_info) # N: Revealed type is "def () -> Union[str, None]"

    print(f"Status info: {status_info()}")

    # A ternary with an `else` branch that involves a different kind of object (NoOp)
    final_task: Callable[[], None] = (
        (lambda: print(f"Processing: {entity.get_message()}"))
        if isinstance(entity, Validator) else
        (lambda: NoOp().no_op_action())
    )
    reveal_type(final_task) # N: Revealed type is "def ()"
    final_task()


if __name__ == "__main__":
    v = Validator()
    er = ErrorReporter()
    n = None

    print("--- Processing Validator ---")
    process_entity(v)

    print("\n--- Processing ErrorReporter ---")
    process_entity(er)

    print("\n--- Processing None ---")
    process_entity(n)

    # Test cases where narrowing is false
    class InvalidValidator(Validator):
        def is_valid(self) -> bool: return False
    iv = InvalidValidator()
    print("\n--- Processing InvalidValidator ---")
    process_entity(iv)

    class NoErrorsReporter(ErrorReporter):
        def has_errors(self) -> bool: return False
    ner = NoErrorsReporter()
    print("\n--- Processing NoErrorsReporter ---")
    process_entity(ner)