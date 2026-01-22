from typing import NewType, List, Callable, TypeVar, Generic, reveal_type

OrderId = NewType("OrderId", int)
CustomerId = NewType("CustomerId", int)

T = TypeVar("T", bound=int) # Bounded by int, so OrderId/CustomerId should work
# A generic function type for processing an ID
ProcessorFunc = Callable[[T], str]

class IdProcessor(Generic[T]):
    """
    A generic class to process IDs of type T.
    T is used in contravariant positions:
    - as the argument type of the 'processor' callable in __init__
    - as the argument type of the 'process' method
    Therefore, IdProcessor should be contravariant in T.
    """
    def __init__(self, processor: ProcessorFunc[T]):
        self._processor = processor

    def process(self, item_id: T) -> str:
        return self._processor(item_id)

def format_order_id(o_id: OrderId) -> str:
    return f"Order #{o_id:05d}"

def format_customer_id(c_id: CustomerId) -> str:
    return f"Customer ID: {c_id}"

def format_generic_int(val: int) -> str:
    return f"Int: {val}"

def process_id_type(p: IdProcessor[OrderId], oid: OrderId):
    """
    Tests `IdProcessor` instantiated with `OrderId`.
    """
    reveal_type(p.process(oid)) # Expected str

    # Attempt to use a CustomerId with an OrderId processor.
    # This should be a clear type error (CustomerId is not OrderId).
    # Uncommenting this should result in an error on all type checkers.
    # p.process(CustomerId(99))

def process_int_type(p: IdProcessor[int], val: int):
    """
    Tests `IdProcessor` instantiated with `int`.
    """
    reveal_type(p.process(val)) # Expected str

if __name__ == "__main__":
    # Instantiating IdProcessor with a NewType-specific function
    order_processor = IdProcessor(format_order_id)
    reveal_type(order_processor) # Expected IdProcessor[OrderId]

    customer_processor = IdProcessor(format_customer_id)
    reveal_type(customer_processor) # Expected IdProcessor[CustomerId]

    print("--- Processing Orders ---")
    process_id_type(order_processor, OrderId(123))

    print("\n--- Processing Customers ---")
    # This should be a clear type error: `IdProcessor[CustomerId]` is not compatible with `IdProcessor[OrderId]`.
    # Uncommenting this should result in an error on all type checkers.
    # process_id_type(customer_processor, CustomerId(456))

    print("\n--- Processing Generic Ints ---")
    generic_int_processor = IdProcessor(format_generic_int)
    reveal_type(generic_int_processor) # Expected IdProcessor[int]
    process_int_type(generic_int_processor, 789)

    # Can an `IdProcessor[OrderId]` be used where `IdProcessor[int]` is expected?
    # `OrderId` is a subtype of `int`.
    # As `IdProcessor` is contravariant in `T`, then `IdProcessor[int]` is a subtype of `IdProcessor[OrderId]`.
    # Therefore, assigning `IdProcessor[OrderId]` to `IdProcessor[int]` should be a type error.
    # This tests how checkers infer or default to variance for generic classes
    # involving NewTypes. Mypy should error here (treating it as invariant or correctly as contravariant).
    # Other checkers might incorrectly allow this assignment, leading to divergence.
    process_int_type(order_processor, OrderId(100)) # DISAGREEMENT POINT