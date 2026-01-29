from typing import NewType, Literal, TypedDict, Dict, Union

# Simulate a NewType that *could* be a variable name
UserId = NewType('UserId', str)

# A Literal that is also a valid variable name
# This pattern caused zuban#121 where 'a' was flagged as undefined.
# What if it's a value for a NewType-based TypedDict key?
UserStatus = Literal['active', 'inactive'] 

class UserInfo(TypedDict):
    id: UserId
    status: UserStatus
    name: str

class AccountSettings(TypedDict, total=False):
    theme: Literal["dark", "light"]
    language: Literal["en", "es"]
    default_status: UserStatus # Using the Literal alias directly

def process_user_data(data: Dict[UserId, UserInfo]) -> None:
    for user_id, info in data.items():
        if info['status'] == 'active':
            print(f"User {user_id} is active.")
        else:
            print(f"User {user_id} is inactive.")

if __name__ == "__main__":
    user_data: Dict[UserId, UserInfo] = {
        UserId("user123"): UserInfo(id=UserId("user123"), status='active', name="Alice"),
        UserId("user456"): UserInfo(id=UserId("user456"), status='inactive', name="Bob")
    }
    process_user_data(user_data)

    settings: AccountSettings = {
        'theme': 'dark',
        'default_status': 'active', # This is fine
        # Removed 'extra_setting': 'value' to fix the original error
    }
    print(f"Settings: {settings}")

    # THIS IS THE MODIFICATION: An assignment of a plain str variable to a Literal type.
    # Mypy is typically strict about this, flagging an error because 'str' is not
    # precisely 'Literal["active", "inactive"]', even if the runtime value matches.
    # Other type checkers might be more lenient, allowing the assignment if the
    # runtime value could potentially match one of the literal options.
    dynamic_status_str: str = "active" 
    literal_test: UserStatus = dynamic_status_str # <--- POTENTIAL DIVERGENCE POINT
    print(f"Literal test from str variable: {literal_test}")