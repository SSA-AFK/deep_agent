import pytest

from api.task_manager import TaskManager, TaskState


@pytest.mark.asyncio
async def test_task_transitions_events_and_terminal_state():
    manager = TaskManager()
    await manager.create("test-task", "research")
    await manager.transition("test-task", TaskState.WAITING_CONFIRMATION)
    await manager.transition("test-task", TaskState.RUNNING)
    await manager.transition("test-task", TaskState.SUCCEEDED)

    snapshot = await manager.snapshot("test-task")
    assert [event["sequence"] for event in snapshot["events"]] == [1, 2, 3, 4]
    assert snapshot["state"] == TaskState.SUCCEEDED
    with pytest.raises(ValueError):
        await manager.transition("test-task", TaskState.RUNNING)


@pytest.mark.asyncio
async def test_task_manager_rejects_duplicate_ids():
    manager = TaskManager()
    await manager.create("test-task", "research")
    with pytest.raises(ValueError):
        await manager.create("test-task", "other")


@pytest.mark.asyncio
async def test_task_manager_broadcasts_versioned_events():
    manager = TaskManager()
    delivered = []
    manager.subscribe(lambda event: _capture(delivered, event))
    await manager.create("test-events", "research")
    await __import__("asyncio").sleep(0)
    assert delivered[0]["version"] == 1
    assert delivered[0]["thread_id"] == "test-events"


async def _capture(delivered, event):
    delivered.append(event)
