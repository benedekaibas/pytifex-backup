# id: self-generic-abstract-inference
# category: self-generic
# expected: mypy: ok, pyrefly: error, zuban: error, ty: error

from typing import TypeVar, Generic, Self, Any
from abc import ABC, abstractmethod

T = TypeVar('T')

class BaseRepository(Generic[T], ABC):
    """
    An abstract generic base class for repositories.
    It uses `Self` in its abstract class method return type.
    """
    @classmethod
    @abstractmethod
    def create_default(cls, value: T) -> Self:
        """
        Creates a default instance of `Self`, parameterized by `T`.
        `Self` should resolve to the concrete class with its specific `T` type argument.
        """
        pass

class UserRepository(BaseRepository[str]):
    """
    A concrete implementation of BaseRepository for strings.
    `T` is fixed to `str` here.
    """
    @classmethod
    def create_default(cls, value: str) -> Self:
        print(f"Creating default UserRepository with value: {value}")
        # In a real impl, might initialize an instance using 'value'.
        return cls()

def process_repository[R: BaseRepository[Any]](repo_type: type[R], initial_value: Any) -> R:
    """
    Takes a repository *type* (e.g., UserRepository) and calls its class method.
    The return type `R` relies on `Self` being correctly inferred with its
    generic type parameters from the actual `repo_type`.
    """
    return repo_type.create_default(initial_value)

if __name__ == "__main__":
    # DIVERGENCE POINT:
    # Mypy correctly infers that `UserRepository.create_default` returns `UserRepository[str]`
    # because `Self` resolves to the specific class `UserRepository` and preserves its `str` type argument.
    # Therefore, the assignment to `processed_repo` as `UserRepository[str]` is valid.
    # Other type checkers might struggle to preserve the `str` type parameter
    # through `Self` when `create_default` is called via the generic function `process_repository`.
    # They might infer `BaseRepository[Any]` or `BaseRepository[str]` for `processed_repo`,
    # leading to an assignment error (as `BaseRepository[str]` is not `UserRepository[str]`).
    processed_repo: UserRepository[str] = process_repository(UserRepository, "default_user_name")
    print(f"Created repository of type: {type(processed_repo)} for value: '{processed_repo}'")

    # Example of using the created instance (should be fine if type inference succeeded).
    # If `processed_repo` lost its specific generic type, this might lead to further errors.
    # reveal_type(processed_repo) # Should show UserRepository[str]