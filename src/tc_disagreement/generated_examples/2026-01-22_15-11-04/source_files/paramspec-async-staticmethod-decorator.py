import asyncio
from typing import TypeVar, ParamSpec, Callable, Concatenate, Any, Awaitable

R = TypeVar("R")
P = ParamSpec("P")

def async_static_timer(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        print(f"Async static method '{func.__name__}' started...")
        start_time = asyncio.get_event_loop().time()
        result = await func(*args, **kwargs)
        end_time = asyncio.get_event_loop().time()
        print(f"Async static method '{func.__name__}' finished in {end_time - start_time:.4f}s")
        return result
    return wrapper

class AsyncOperations:
    @staticmethod
    @async_static_timer
    async def fetch_data(url: str, timeout: int = 5) -> str:
        await asyncio.sleep(0.1) # Simulate async I/O
        print(f"  Fetching data from {url} with timeout {timeout}s")
        return f"Data from {url} (size: {len(url) + timeout})"

    @staticmethod
    @async_static_timer
    async def calculate_sum(a: int, b: int) -> int:
        await asyncio.sleep(0.05) # Simulate async computation
        print(f"  Calculating {a} + {b}")
        return a + b

    # A normal instance method to ensure type checking doesn't bleed
    async def instance_method(self) -> str:
        return "instance result"


async def main() -> None:
    # Test fetch_data
    result1 = await AsyncOperations.fetch_data("https://example.com/api/data", timeout=10)
    print(f"Fetch result: {result1}")

    result2 = await AsyncOperations.fetch_data("https://another.com") # Using default timeout
    print(f"Fetch result (default timeout): {result2}")

    # Test calculate_sum
    sum_result = await AsyncOperations.calculate_sum(10, 20)
    print(f"Sum result: {sum_result}")

    # Test type checking on arguments
    # await AsyncOperations.fetch_data(123) # This should be a type error
    # await AsyncOperations.calculate_sum("a", "b") # This should be a type error

    # Ensure decorator works with correct arguments and returns
    _ = AsyncOperations().instance_method() # should not be decorated
    # Awaitable[str] is fine
    # print(await AsyncOperations().instance_method())


if __name__ == "__main__":
    asyncio.run(main())