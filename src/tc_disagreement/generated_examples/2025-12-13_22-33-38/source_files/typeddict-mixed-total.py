# id: typeddict-mixed-total
# EXPECTED:
#   mypy: Error (TypedDict "NetworkConfig" has no key 'port') or (Item "port" might not be present)
#   pyright: No error
#   pyre: No error
#   zuban: No error
# REASON: Mypy is stricter about direct access (`td['key']`) to NotRequired keys in TypedDicts, even when the key is explicitly marked NotRequired. It requires a prior check (`'key' in td`) or use of `.get()`. Pyright, Pyre, and Zuban often infer the type of `td['key']` as `T | None` for NotRequired keys, allowing direct access without an explicit check.

from typing import TypedDict, Union, Any
from typing_extensions import Required, NotRequired

class ConnectionBase(TypedDict, total=True): # All keys required by default
    host: str

class NetworkConfig(ConnectionBase):
    port: NotRequired[int] # Explicitly optional
    protocol: Required[str] # Explicitly required, overriding total=False if it were there

def check_config(td: NetworkConfig) -> None:
    reveal_type(td.get('host'))    # str for all
    reveal_type(td.get('port'))    # int | None for all
    reveal_type(td['protocol'])    # str for all
    
    # This is the point of divergence for direct access to NotRequired keys
    p = td['port'] # Mypy typically errors here. Others infer int | None.
    reveal_type(p)

if __name__ == "__main__":
    config1: NetworkConfig = {'host': 'localhost', 'protocol': 'https'}
    check_config(config1)

    config2: NetworkConfig = {'host': '127.0.0.1', 'port': 8080, 'protocol': 'http'}
    check_config(config2)