from typing import TypeGuard, Dict, Any, Union, TypeVar, reveal_type

K = TypeVar("K")
V = TypeVar("V")

class DataRecord:
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name

    def get_id(self) -> int:
        return self.id

    def get_name(self) -> str:
        return self.name

class ValidatedDataRecord(DataRecord):
    def is_valid(self) -> bool:
        return True # Assume some validation logic

def is_dict_of_data_records(d: Dict[K, Any]) -> TypeGuard[Dict[K, DataRecord]]:
    """
    TypeGuard to narrow a dictionary's value types to DataRecord.
    The key type K should be preserved.
    """
    return all(isinstance(v, DataRecord) for v in d.values())

def is_dict_of_validated_records(d: Dict[K, DataRecord]) -> TypeGuard[Dict[K, ValidatedDataRecord]]:
    """
    TypeGuard to further narrow DataRecord values to ValidatedDataRecord.
    """
    return all(isinstance(v, ValidatedDataRecord) for v in d.values())

def process_data_dicts(data: Dict[str, Any]):
    """
    Function demonstrating nested TypeGuard usage for dictionary values.
    """
    if is_dict_of_data_records(data):
        reveal_type(data) # Expected Dict[str, DataRecord]
        # Accessing `DataRecord`-specific methods.
        print(f"Data records names: {[v.get_name() for v in data.values()]}")

        if is_dict_of_validated_records(data):
            reveal_type(data) # Expected Dict[str, ValidatedDataRecord]
            # Accessing `ValidatedDataRecord`-specific methods.
            # DISAGREEMENT POINT: Can checkers correctly chain TypeGuards for generic dicts?
            print(f"Validated records: {[v.is_valid() for v in data.values()]}")
        else:
            print("Not all records are validated.")
    else:
        print("Not a dictionary of data records.")

if __name__ == "__main__":
    print("--- Case 1: All DataRecords ---")
    dict1: Dict[str, Any] = {
        "rec1": DataRecord(1, "Alpha"),
        "rec2": DataRecord(2, "Beta")
    }
    process_data_dicts(dict1)

    print("\n--- Case 2: Mixed DataRecords and ValidatedDataRecords ---")
    dict2: Dict[str, Any] = {
        "recA": DataRecord(3, "Gamma"),
        "recB": ValidatedDataRecord(4, "Delta")
    }
    process_data_dicts(dict2) # Should enter first if, but not second.

    print("\n--- Case 3: All ValidatedDataRecords ---")
    dict3: Dict[str, Any] = {
        "val_rec1": ValidatedDataRecord(5, "Epsilon"),
        "val_rec2": ValidatedDataRecord(6, "Zeta")
    }
    process_data_dicts(dict3) # Should enter both ifs.

    print("\n--- Case 4: Non-DataRecord ---")
    dict4: Dict[str, Any] = {
        "recX": DataRecord(7, "Eta"),
        "recY": "not a record"
    }
    process_data_dicts(dict4) # Should not enter any if.