from typing import Protocol, TypeVar, Generic, Optional, Self, Callable, Awaitable, Any

# A TypeVar for the specific type of the concrete class implementing the protocol
_P = TypeVar('_P', bound='ConfigurableComponent') # Retained as originally written, without covariant=True

class ConfigurableComponent(Protocol[_P]):
    """
    A protocol for components that can be configured.
    Includes a method with a default parameter whose type relates to `Self`.
    """
    def get_name(self) -> str: ...

    def configure_self(self, settings: Optional[str] = None) -> _P:
        """
        Configures the component.
        The default value `None` for `settings` means it might be an issue
        if an implementing class tries to provide a non-None default that is not `Optional[str]`.
        The return type `_P` ensures `Self` semantics within the protocol.
        """
        raise NotImplementedError

    def reset_state(self, new_state: Optional[int] = 0) -> _P:
        """Resets the component's internal state."""
        raise NotImplementedError

    def create_nested_component(self, name: str) -> _P:
        """
        Creates and returns a new component of the same type as the current instance.
        This method will be a source of LSP violation in the DatabaseConnector.
        """
        raise NotImplementedError

class BasicService:
    def __init__(self, name: str) -> None:
        self._name = name
        self._config: Optional[str] = None
        self._state: int = 0

    def get_name(self) -> str:
        return self._name

    def configure_self(self, settings: Optional[str] = "DEFAULT_CONFIG") -> Self:
        """
        Implements configure_self with a different default.
        The protocol expects `settings: Optional[str] = None`.
        This implementation has `settings: Optional[str] = "DEFAULT_CONFIG"`.
        (Type checkers generally agree this difference is not an LSP violation).
        """
        self._config = settings
        print(f"{self._name} configured with: {self._config}")
        return self

    def reset_state(self, new_state: Optional[int] = -1) -> Self:
        """
        Protocol expects `Optional[int] = 0`. This implements `Optional[int] = -1`.
        (Type checkers generally agree this difference is not an LSP violation).
        """
        self._state = new_state if new_state is not None else 0
        print(f"{self._name} state reset to: {self._state}")
        return self

    def create_nested_component(self, name: str) -> Self:
        """
        MODIFIED: Now attempts to return a new instance of the *actual* type of `self`.
        For `DatabaseConnector`, this will call `DatabaseConnector(name)`,
        which will cause a runtime `TypeError` because `db_url` is missing from `__init__`.
        Type checkers may diverge on whether this constructor call error
        is caught, and how it relates to the `_P` return type expectation.
        """
        return type(self)(f"{self._name}-{name}")

class DatabaseConnector(BasicService, ConfigurableComponent["DatabaseConnector"]):
    def __init__(self, name: str, db_url: str) -> None:
        super().__init__(name)
        self.db_url = db_url

    def configure_self(self, settings: Optional[str] = "DB_CONFIG") -> Self:
        super().configure_self(settings)
        print(f"  Database specific configuration applied: {self.db_url}")
        return self

    # Does not override reset_state or create_nested_component.
    # The inherited `create_nested_component` from `BasicService` now uses `type(self)`.
    # For `DatabaseConnector`, this means it tries to call `DatabaseConnector(name: str)`.
    # However, `DatabaseConnector.__init__` requires `(name: str, db_url: str)`.
    # This missing argument should be detected by some type checkers (e.g., mypy).
    # The protocol `ConfigurableComponent["DatabaseConnector"]` expects the return type to be `DatabaseConnector`.
    # `type(self)` conceptually returns `DatabaseConnector`, so the LSP return type might appear correct to some,
    # leading to divergence with checkers that focus on the constructor arguments.

if __name__ == "__main__":
    def setup_component(comp: ConfigurableComponent[Any]) -> None:
        print(f"\n--- Setting up {comp.get_name()} ---")
        comp.configure_self()
        comp.reset_state()
        print(f"  Final state: {comp.get_name()} config: {getattr(comp, '_config', 'N/A')}, state: {getattr(comp, '_state', 'N/A')}")
        
        # Test the new method
        nested_comp = comp.create_nested_component("nested")
        print(f"  Nested component created: {nested_comp.get_name()} (Type: {type(nested_comp).__name__})")
        # This line will cause a runtime TypeError for DatabaseConnector if the type checker
        # allows the previous line (creation of nested_comp for DatabaseConnector)
        # due to the missing `db_url` argument in its constructor call.
        nested_comp.configure_self() 

    bs = BasicService("ServiceA")
    setup_component(bs)

    dbc = DatabaseConnector("MyDBConnector", "postgresql://localhost")
    # This call will lead to a runtime TypeError inside create_nested_component for `dbc`
    # due to the mismatch in `DatabaseConnector.__init__` signature.
    # Type checkers are expected to diverge on whether they catch this at type-check time.
    setup_component(dbc) 

    # Directly call with explicit args
    print("\n--- Direct calls with explicit arguments ---")
    bs2 = BasicService("ServiceB")
    bs2.configure_self("EXPLICIT_CONFIG")
    bs2.reset_state(100)
    print(f"{bs2.get_name()} config: {getattr(bs2, '_config')}, state: {getattr(bs2, '_state')}")
    nested_bs2 = bs2.create_nested_component("child")
    print(f"Nested BS2 type: {type(nested_bs2).__name__}")


    dbc2 = DatabaseConnector("MyDBConnector2", "mysql://remote")
    dbc2.configure_self("EXPLICIT_DB_CONFIG")
    dbc2.reset_state(200)
    print(f"{dbc2.get_name()} config: {getattr(dbc2, '_config')}, state: {getattr(dbc2, '_state')}")
    nested_dbc2 = dbc2.create_nested_component("child") # This is the line that triggers the runtime TypeError.
    print(f"Nested DBC2 type: {type(nested_dbc2).__name__}")