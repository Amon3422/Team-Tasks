import pytest
import copy

tasks = [
    {"id": 1, "title": "Read HTTP basics", "team_id": 10, "done": False},
    {"id": 2, "team_id": 20, "done": True},
    {"id": 3, "title": "Build a view", "team_id": 10, "done": True},
]
#list of dicts

def tasks_for_team(tasks, team_id): 
    return [task for task in tasks if task["team_id"] == team_id]


def count_completed(tasks):
    return sum(1 for task in tasks if task["done"])


def validate_title(title):
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Empty string not accepted")
    return True

def test_tasks_for_team():
    assert tasks_for_team(tasks, 10) == [
        {"id": 1, "title": "Read HTTP basics", "team_id": 10, "done": False}, 
        {"id": 3, "title": "Build a view", "team_id": 10, "done": True}
    ], "Team 10 only has task 1 and task 3"

    assert tasks_for_team(tasks, 99) == [], "Should return an empty list for unknown teams"

def test_count_completed():
    assert count_completed(tasks) == 2, "Should be two"

def test_validate_title():
    with pytest.raises(ValueError, match="Empty string not accepted"):
        validate_title("   ")

    assert validate_title("Valid task title") is True

def test_original_tasks():
    original_snapshot = copy.deepcopy(tasks)
    _ = tasks_for_team(tasks, 10)
    assert original_snapshot == tasks

def validate_tasks(data) -> list[dict]:
    validated_tasks = []

    REQUIRED_KEYS = frozenset({"id", "team_id", "title", "done"})

    if not isinstance(data, list):
        raise TypeError(f"Root JSON entity must be a list, received {type(data).__name__}")
    
    for idx, item in enumerate(data):
        if type(item) is not dict:
            raise TypeError(f"Item at index {idx} must be an object/dict")

        if not REQUIRED_KEYS.issubset(item):
            missing_keys = REQUIRED_KEYS - item.keys()
            raise ValueError(f"Task at index {idx} is missing required fields: {', '.join(missing_keys)}")

        task_id = item["id"]
        team_id = item["team_id"]
        title = item["title"]
        done = item["done"]

        if type(task_id) is not int or task_id <= 0:
            raise ValueError(f"Task at index {idx}: 'id' must be a positive integer")
        if type(team_id) is not int or team_id <= 0:
            raise ValueError(f"Task at index {idx}: 'team_id' must be an positive integer")
        if type(title) is not str or not title.strip():
            raise ValueError(f"Task at index {idx}: 'title' must be a non-empty string")
        if type(done) is not bool:
            raise ValueError(f"Task at index {idx}: 'done' must be a boolean (true/false)")

        validated_tasks.append(item)

    return validated_tasks

