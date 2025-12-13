# id: double-bound-typevar-generics
# EXPECTED:
#   mypy: Error (Argument type "Notifier[User]" incompatible with TypeVar "T_Notifier" bound "Notifier[Event]")
#   pyright: No error
#   pyre: No error
#   zuban: No error
# REASON: Mypy can be overly strict when checking compatibility of a generic instance against a `TypeVar` that is bound to another generic type, especially if the inner generic also has a bound. It might not correctly infer that `Notifier[User]` is compatible with `T_Notifier` which is bound to `Notifier[Event]`, despite `User` being a subtype of `Event`. This is because `Notifier` is invariant by default. Pyright, Pyre, and Zuban generally handle this specific subtyping relationship correctly, inferring compatibility.

from typing import TypeVar, Generic, Any

class Event: ...
class User(Event): ...
class SystemLog(Event): ...

T = TypeVar('T', bound=Event)

class Notifier(Generic[T]): # Invariant by default
    def notify(self, item: T) -> None:
        print(f"Notifying about: {type(item).__name__}")

# T_Notifier is bound to a generic type that itself uses a TypeVar
T_Notifier = TypeVar('T_Notifier', bound="Notifier[Event]") # Use string for forward ref of Notifier[Event] if in global scope

def dispatch_event_notification(notifier: T_Notifier, event: Event) -> None:
    """Dispatches an event using a generic notifier."""
    notifier.notify(event)

if __name__ == "__main__":
    user_notifier: Notifier[User] = Notifier()
    user = User()
    user_notifier.notify(user) # OK

    # Divergence point: passing Notifier[User] where T_Notifier bound to Notifier[Event] is expected
    # Mypy often complains here, as it upholds invariance strictly.
    dispatch_event_notification(user_notifier, user) # Checkers disagree here
    reveal_type(user_notifier)

    system_notifier: Notifier[SystemLog] = Notifier()
    system_log = SystemLog()
    dispatch_event_notification(system_notifier, system_log)