from domain.tasks import DailyPlan, TaskItem, TaskPriority, TaskStatus


def test_task_item_defaults_to_todo() -> None:
    item = TaskItem(
        title="Plan today's work",
        priority=TaskPriority.HIGH,
        rationale="Start with the most important work.",
        next_action="List the top three tasks.",
    )

    assert item.status == TaskStatus.TODO


def test_daily_plan_keeps_tasks_and_questions() -> None:
    plan = DailyPlan(
        request="Help me plan today.",
        summary="Do high-priority tasks first.",
        tasks=[
            TaskItem(
                title="Write daily report",
                priority=TaskPriority.HIGH,
                rationale="It is due today.",
                next_action="Draft three key points.",
            )
        ],
        follow_up_questions=["Do you have fixed meetings today?"],
    )

    assert plan.request == "Help me plan today."
    assert plan.tasks[0].title == "Write daily report"
    assert plan.follow_up_questions == ["Do you have fixed meetings today?"]
