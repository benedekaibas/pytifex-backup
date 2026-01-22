# id: protocol-default-args-mismatch
# EXPECTED:
#   mypy: No error
#   pyright: Error (Default arguments must match)
#   pyre: No error
#   zuban: Error (Default arguments must match)
# REASON: Mypy and Pyre treat default argument differences in protocol implementations as compatible as long as the signature is otherwise assignable. Pyright and Zuban enforce stricter compatibility, requiring default argument values to match.

from typing import Protocol

class EventHandler(Protocol):
    def handle(self, event_name: str, priority: int = 0) -> bool: ...

class LowPriorityHandler:
    def handle(self, event_name: str, priority: int = 1) -> bool: # Different default
        print(f"Handling '{event_name}' with priority {priority}")
        return True

def process_event(handler: EventHandler, name: str) -> None:
    handler.handle(name)

if __name__ == "__main__":
    low_handler = LowPriorityHandler()
    process_event(low_handler, "user_login") # Type checkers disagree on default arg compatibility