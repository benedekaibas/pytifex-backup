from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Self

T = TypeVar('T')

class BaseRepository(Generic[T], ABC):
    @abstractmethod
    def get_by_id(self, id: str) -> Self:
        pass

    @abstractmethod
    def save(self, entity: T) -> Self:
        pass

class User:
    def __init__(self, uid: str, name: str):
        self.uid = uid
        self.name = name

    def __repr__(self) -> str:
        return f"User(uid='{self.uid}', name='{self.name}')"

class UserRepository(BaseRepository[User]):
    def __init__(self):
        self._users: dict[str, User] = {}

    def get_by_id(self, id: str) -> Self:
        user = self._users.get(id)
        if user is None:
            raise ValueError(f"User with id {id} not found.")
        return self # Returning Self here

    def save(self, user: User) -> Self:
        self._users[user.uid] = user
        return self # Returning Self here

def initialize_repository(repo: UserRepository) -> None:
    # zuban#180 flagged `_ = ...` for needing annotation.
    # Here, `_` receives a `Self` return type from a generic context.
    # Type checkers might disagree on whether `_` needs explicit annotation
    # when the value comes from a `Self` return type in a generic class.
    _ = repo.save(User("u1", "Alice")) 
    _ = repo.save(User("u2", "Bob"))
    
    # Try to fetch and assign to `_`
    try:
        _ = repo.get_by_id("u1") # This could also be flagged for `_` annotation
        print(f"Retrieved user U1 via dummy var: {_}")
    except ValueError as e:
        print(e)


if __name__ == "__main__":
    user_repo = UserRepository()
    initialize_repository(user_repo)

    # Another assignment to `_` directly from a method returning `Self`
    _ = user_repo.save(User("u3", "Charlie")).save(User("u4", "David"))
    print(f"Chained saves, last user (via _): {_._users['u4']}")
