"""Run (mission/job) data model.

Merged from the old standalone ``run_tracker.py``. Runs used to carry a
``character_file`` / ``character_name`` pointing at a character JSON file on
disk, and completing a run rewrote that file directly. Now that runs live
inside the character's own save file, that indirection is gone -- a run
always belongs to whichever character it's stored on.
"""


class ShadowrunRun:
    STATUSES = ["Active", "Completed", "Abandoned"]

    def __init__(self, name="", description="", reward=0):
        self.name = name
        self.description = description
        self.reward = reward
        self.status = "Active"
        # Each task: {"description": str, "mandatory": bool, "completed": bool}
        self.tasks = []

    @property
    def total_tasks(self):
        return len(self.tasks)

    @property
    def completed_tasks(self):
        return sum(1 for t in self.tasks if t.get("completed"))

    @property
    def progress_percent(self):
        if not self.tasks:
            return 0
        return int(self.completed_tasks / self.total_tasks * 100)

    def mandatory_complete(self):
        """True if every mandatory task is completed (or there are none)."""
        return all(t.get("completed") for t in self.tasks if t.get("mandatory"))

    def payout(self):
        """Nuyen actually earned, scaled by task completion percentage."""
        if not self.tasks:
            return self.reward
        return int(self.reward * self.completed_tasks / self.total_tasks)

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "reward": self.reward,
            "status": self.status,
            "tasks": self.tasks,
        }

    @classmethod
    def from_dict(cls, data):
        run = cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            reward=data.get("reward", 0),
        )
        run.status = data.get("status", "Active")
        if run.status not in cls.STATUSES:
            run.status = "Active"
        run.tasks = [dict(t) for t in data.get("tasks", [])]
        return run
