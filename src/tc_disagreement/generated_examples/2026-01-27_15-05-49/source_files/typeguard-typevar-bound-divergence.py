from typing import TypeGuard, List, Union, TypeVar, reveal_type, Any

T = TypeVar("T")

class Vehicle:
    def drive(self) -> str:
        return "Vroom!"

class Car(Vehicle):
    def honk(self) -> str:
        return "Honk honk!"
    def drive(self) -> str:
        return "Driving a car."

class Bike(Vehicle):
    def pedal(self) -> str:
        return "Pedaling..."

# --- MODIFICATION START ---
# The original code showed a divergence where `ty` allowed the call to
# `process_vehicles(mixed_fleet)` but mypy/pyrefly/zuban reported an error due
# to mutable list covariance rules or type inference.
#
# To create a new, more subtle divergence specifically within the TypeGuard's
# narrowing behavior, we first make the call sites explicitly typed to resolve
# the initial disagreement.
#
# The core change introduces a TypeVar `V` that is *bound* to `Vehicle`.
# The TypeGuard's return type is `TypeGuard[List[V]]`, implying a list of
# general `Vehicle`s. However, the *internal logic* of the TypeGuard
# explicitly checks for `Car` instances.
#
# Type checkers might diverge on how they resolve `V` within the `if` block:
# 1. Some might infer `V` as `Car` (the more specific type from the `isinstance` check),
#    making methods like `.honk()` directly accessible.
# 2. Others might adhere strictly to `V`'s bound (`Vehicle`), treating `vehicles`
#    as `List[Vehicle]`, which would make `.honk()` (a `Car`-specific method) an error.
# 3. Some might leave `V` unresolved, also leading to an error on `.honk()`.

V = TypeVar("V", bound=Vehicle) # A TypeVar bound to Vehicle

def all_are_specific_vehicles(items: List[Union[T, Vehicle]]) -> TypeGuard[List[V]]:
    """
    A TypeGuard designed to narrow a list potentially containing T or Vehicle to List[V],
    where V is a TypeVar bound to Vehicle.
    The internal logic, however, checks explicitly for Car instances.
    This setup creates an ambiguity: should `V` be resolved to `Car` (due to the runtime
    check) or `Vehicle` (due to its bound)?
    """
    return all(isinstance(item, Car) for item in items)

def process_vehicles(vehicles: List[Union[str, Vehicle]]) -> List[str]:
    results: List[str] = []
    if all_are_specific_vehicles(vehicles):
        # This is the key divergence point.
        # How is `V` resolved by the type checker for `vehicles`?
        reveal_type(vehicles) # Expected: List[Car] by some, List[Vehicle] by others.
        for item_in_list in vehicles:
            # If `vehicles` is narrowed to `List[Car]`, this call is valid.
            # If `vehicles` is narrowed to `List[Vehicle]` (or `List[V]` where `V` is generic),
            # then `honk()` is not a method on `Vehicle`, so this should be an error.
            results.append(item_in_list.honk())
    else:
        # Here, `vehicles` could still contain `str` or `Bike`
        for item in vehicles:
            if isinstance(item, Vehicle):
                results.append(item.drive())
            else:
                results.append(f"Non-vehicle: {item}")
    return results

if __name__ == "__main__":
    # Explicitly typing these lists to prevent initial call-site errors
    # (which was a point of divergence in the original code, but not the
    # intended one for this task). This ensures the focus is on the TypeGuard's behavior.
    mixed_fleet: List[Union[str, Vehicle]] = ["truck", Car(), Bike(), Car()]
    all_cars_fleet: List[Union[str, Vehicle]] = [Car(), Car()]
    empty_fleet: List[Union[str, Vehicle]] = []

    print(f"Processing mixed fleet: {process_vehicles(mixed_fleet)}")
    # Expected: ['Non-vehicle: truck', 'Driving a car.', 'Vroom!', 'Driving a car.']
    # The `mixed_fleet` should not pass the `all_are_specific_vehicles` guard due to `str` and `Bike`.

    print(f"Processing all cars fleet: {process_vehicles(all_cars_fleet)}")
    # Expected output: ['Honk honk!', 'Honk honk!'] IF `V` is correctly inferred as `Car`.
    # Expected type error: If `V` is inferred as `Vehicle` (its bound) or remains generic,
    # `item_in_list.honk()` will be reported as an error.

    print(f"Processing empty fleet: {process_vehicles(empty_fleet)}")
    # Expected: []

    print("\nDemonstrating TypeGuard's interaction with a bound TypeVar and explicit runtime checks.")
    print("This setup tests if type checkers infer `V` as the specific `Car` type based on the `isinstance` check,")
    print("or adhere more strictly to `V`'s `Vehicle` bound or its generic nature, leading to a divergence.")
# --- MODIFICATION END ---