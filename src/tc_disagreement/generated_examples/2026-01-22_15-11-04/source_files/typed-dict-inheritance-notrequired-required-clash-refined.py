from typing import TypedDict, NotRequired, Required, Union, Literal, List, Optional

class BaseResource(TypedDict, total=False):
    """Base for resources, all fields are optional by default."""
    name: NotRequired[str]
    id: Required[str] # id is always required
    tags: NotRequired[List[str]]

class NetworkResource(BaseResource, total=False):
    """Network-related fields, also optional."""
    ip_address: NotRequired[str]
    port: NotRequired[int]

class ComputeResource(NetworkResource, total=True):
    """Compute resources are total. New fields are Required.
    Inherited NotRequired fields from parents, like 'name', 'ip_address', 'port',
    should theoretically remain NotRequired according to PEP 655
    ("explicit mark takes precedence over the total setting").
    However, some type checkers might interpret 'total=True' more broadly,
    making all inherited fields implicitly Required regardless of parent's NotRequired mark.
    This creates the potential for divergence.
    """
    cpu_cores: int
    memory_gb: int
    # Removed explicit overrides for 'name' and 'ip_address'.
    # Their status (Required/NotRequired) is now solely determined
    # by inheritance rules and the 'total=True' setting.

class StorageResource(BaseResource, total=False):
    capacity_gb: NotRequired[int]
    resource_type: Literal["SSD", "HDD"]

# Added BaseResource to the Union to allow processing of base1,
# resolving an unrelated type error from the original code.
def create_resource(data: Union[BaseResource, NetworkResource, ComputeResource, StorageResource]) -> None:
    print(f"Processing resource with ID: {data['id']}")
    if "name" in data:
        print(f"  Name: {data['name']}")
    if isinstance(data, ComputeResource):
        print(f"  Compute: {data['cpu_cores']} cores, {data['memory_gb']}GB RAM")
        # For ComputeResource (total=True), 'cpu_cores' and 'memory_gb' are always present.
        # 'name', 'ip_address', 'port', 'tags' are inherited as NotRequired from parents.
        # If checkers follow PEP 655 strictly, these inherited fields remain NotRequired,
        # so 'in data' checks are valid. If not, they are redundant.
        if "ip_address" in data:
            print(f"  IP: {data['ip_address']}")
        else:
            print("  IP address not specified (ambiguous: optional or required?)")
        if "port" in data:
            print(f"  Port: {data['port']}")
        else:
            print("  Port not specified (ambiguous: optional or required?)")
    elif isinstance(data, StorageResource):
        print(f"  Storage: {data['resource_type']}")
        if "capacity_gb" in data:
            print(f"  Capacity: {data['capacity_gb']}GB")


if __name__ == "__main__":
    # Valid BaseResource
    base1: BaseResource = {"id": "res-001", "name": "Base Item"}
    # Valid NetworkResource (total=False)
    net1: NetworkResource = {"id": "net-001", "ip_address": "192.168.1.1"}
    net2: NetworkResource = {"id": "net-002"}

    # ComputeResource (total=True)
    # 'cpu_cores' and 'memory_gb' are new fields and are Required.
    # 'id' is Required from BaseResource.
    # 'name', 'ip_address', 'port', 'tags' are inherited as NotRequired.

    # comp1: All fields present, should be valid for all interpretations.
    comp1: ComputeResource = {
        "id": "comp-001",
        "name": "Server Alpha",
        "cpu_cores": 8,
        "memory_gb": 32,
        "ip_address": "10.0.0.1",
        "port": 8080
    }

    # comp2: Missing 'ip_address' and 'port'.
    # If inherited NotRequired fields remain NotRequired (PEP 655 compliant), this is VALID.
    # If 'total=True' makes ALL inherited fields Required, this is an ERROR.
    comp2: ComputeResource = {
        "id": "comp-002",
        "name": "Server Beta",
        "cpu_cores": 4,
        "memory_gb": 16,
        # Missing 'ip_address', 'port'
    }

    # comp3: Missing 'name'.
    # If inherited NotRequired fields remain NotRequired (PEP 655 compliant), this is VALID.
    # If 'total=True' makes ALL inherited fields Required, this is an ERROR.
    comp3: ComputeResource = {
        "id": "comp-003",
        "cpu_cores": 16,
        "memory_gb": 64,
        "ip_address": "10.0.0.3",
        "port": 22
        # Missing 'name'
    }

    # Valid StorageResource
    store1: StorageResource = {"id": "store-001", "resource_type": "SSD", "capacity_gb": 500}
    store2: StorageResource = {"id": "store-002", "resource_type": "HDD"}

    create_resource(base1)
    create_resource(net1)
    create_resource(net2)
    create_resource(comp1)
    create_resource(store1)
    create_resource(store2)

    # These two calls are designed to expose type checker divergence.
    # Some checkers (following PEP 655 strictly) will allow them.
    # Others (interpreting total=True as making all fields required) will produce type errors.
    create_resource(comp2)
    create_resource(comp3)