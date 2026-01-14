from typing import NewType, TypeVar, Generic, List, reveal_type, Protocol

EntityId = NewType("EntityId", int)
RecordId = NewType("RecordId", int)

# Covariant TypeVar for demonstrating NewType behavior in generics
Co = TypeVar("Co", bound=int, covariant=True)

class DataLoader(Generic[Co]):
    def __init__(self, ids: List[Co]):
        self._ids = ids

    def get_first_id(self) -> Co:
        return self._ids[0]

    def add_id(self, new_id: Co) -> None:
        self._ids.append(new_id)

    def get_all_ids(self) -> List[Co]:
        return self._ids

def process_entity_loader(loader: DataLoader[EntityId]):
    """
    Function to process a `DataLoader` specifically for `EntityId`.
    """
    first_id = loader.get_first_id()
    reveal_type(first_id) # Expected EntityId

    # This should be a type error if RecordId is not compatible with EntityId.
    # loader.add_id(RecordId(99)) # DISAGREEMENT POINT: NewType is not compatible with other NewType based on same primitive.

def process_int_loader(loader: DataLoader[int]):
    """
    Function to process a `DataLoader` for general `int`s.
    """
    first_id = loader.get_first_id()
    reveal_type(first_id) # Expected int

    loader.add_id(100) # Should be fine
    loader.add_id(EntityId(200)) # Should be fine (NewType is subtype of base)
    loader.add_id(RecordId(300)) # Should be fine

if __name__ == "__main__":
    entity_ids: List[EntityId] = [EntityId(1), EntityId(2)]
    entity_loader = DataLoader(entity_ids)
    reveal_type(entity_loader) # Expected DataLoader[EntityId]
    print(f"Entity loader first ID: {entity_loader.get_first_id()}")
    process_entity_loader(entity_loader)

    record_ids: List[RecordId] = [RecordId(101), RecordId(102)]
    record_loader = DataLoader(record_ids)
    reveal_type(record_loader) # Expected DataLoader[RecordId]

    # DISAGREEMENT POINT: Can a `DataLoader[EntityId]` be assigned to `DataLoader[int]`
    # due to `covariant=True` and `EntityId` being a subtype of `int`? Yes, it should.
    process_int_loader(entity_loader)
    print(f"Entity loader processed as int loader: {entity_loader.get_all_ids()}")

    # DISAGREEMENT POINT: Can `DataLoader[RecordId]` be assigned to `DataLoader[EntityId]`? No.
    # process_entity_loader(record_loader) # This should be an error.