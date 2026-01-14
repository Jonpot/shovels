"""
Test that all frontend action types are recognized by the backend.
This is a simple static analysis test that doesn't require running the backend.
"""
import re
from pathlib import Path


def get_backend_action_types():
    """Parse main.py to find all recognized action types."""
    main_py = Path(__file__).parent.parent / "shovels_backend" / "main.py"
    content = main_py.read_text()

    # Find all action_type comparisons: action_type == "xyz"
    pattern = r'action_type\s*==\s*["\'](\w+)["\']'
    matches = re.findall(pattern, content)
    return set(matches)


def get_frontend_action_types():
    """Parse GameBoard.jsx to find all action types sent to backend."""
    gameboard_jsx = Path(__file__).parent.parent / "shovels_frontend" / "src" / "views" / "GameBoard.jsx"
    content = gameboard_jsx.read_text()

    # Find all action_type values: action_type: 'xyz' or action_type: "xyz"
    pattern = r'action_type:\s*["\'](\w+)["\']'
    matches = re.findall(pattern, content)
    return set(matches)


def test_all_frontend_actions_are_recognized():
    """
    Ensure every action type sent by the frontend is recognized by the backend.
    This catches issues like 'resolve_gravedig' not being handled.
    """
    backend_types = get_backend_action_types()
    frontend_types = get_frontend_action_types()

    print(f"Backend recognizes: {sorted(backend_types)}")
    print(f"Frontend sends: {sorted(frontend_types)}")

    unrecognized = frontend_types - backend_types
    if unrecognized:
        raise AssertionError(
            f"Frontend sends action types not recognized by backend: {unrecognized}\n"
            f"Add these to the action routing in shovels_backend/main.py"
        )


def test_expected_action_types_are_handled():
    """
    Verify that all expected action types are handled by the backend.
    This is a hardcoded list of what should be supported.
    """
    backend_types = get_backend_action_types()

    expected_types = {
        # Phase 1
        "draw",
        "discard",
        "play",
        # Phase 2
        "perform_action",
        "action",  # alias
        "tap_hero",
        "tap",  # alias
        "face_strike",
        "strike",  # alias
        "buy",
        "refresh",
        "end_turn",
        # Gravedigging
        "gravedig",
        "resolve_gravedig",  # alias
        "select_gravedig_card",
        "finish_gravedig",
    }

    missing = expected_types - backend_types
    if missing:
        raise AssertionError(
            f"Expected action types missing from backend: {missing}\n"
            f"Add these to the action routing in shovels_backend/main.py"
        )


if __name__ == "__main__":
    test_all_frontend_actions_are_recognized()
    test_expected_action_types_are_handled()
    print("All action routing tests passed!")
