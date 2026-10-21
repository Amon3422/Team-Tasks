from pathlib import Path
from storage import load_tasks
from task_logic import validate_tasks, tasks_for_team, count_completed, test_original_tasks

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "tasks.json"

def main():
    data = load_tasks(DATA_FILE)
    tasks = validate_tasks(data)

    team_10_task = tasks_for_team(tasks, 10)

    print(f"Total tasks: {len(tasks)}")
    print(f"Team 10 tasks: {len(team_10_task)}")
    print(f"Completed in team 10: {count_completed(team_10_task)}")
    print(data)

if __name__ == "__main__":
    raise SystemExit(main())

