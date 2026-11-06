"""
Test that GMB extraction runs cleanly even under WindowsSelectorEventLoopPolicy
(which is what Uvicorn forces on Windows with --reload).
"""
import asyncio
import sys
import threading
from app import GMBExtractionTask, run_gmb_task

# Force WindowsSelectorEventLoopPolicy to simulate Uvicorn with --reload
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def main():
    print(f"Active event loop policy: {type(asyncio.get_event_loop_policy())}")
    print(f"Active running loop: {type(asyncio.get_running_loop())}")

    # Create task for a small query with max 2 results
    task = GMBExtractionTask(
        task_id="test_fix",
        niche="Bakery",
        location="Austin, TX",
        max_results=2,
        exhaustive=False,
        enrich_emails=False
    )

    events_received = []

    async def event_collector():
        while True:
            try:
                ev = await asyncio.wait_for(task.event_queue.get(), timeout=15.0)
                events_received.append(ev)
                print(f"[EVENT] {ev.get('type')}: {ev.get('message', ev.get('profile', {}).get('business_name', ''))}")
                if ev.get("type") in ["task_completed", "task_error"]:
                    break
            except asyncio.TimeoutError:
                break

    collector_coro = asyncio.create_task(event_collector())
    task_coro = asyncio.create_task(run_gmb_task(task))

    await asyncio.gather(collector_coro, task_coro, return_exceptions=True)

    print("\nTotal events received:", len(events_received))
    print("Task status:", task.status)
    print("Total profiles extracted:", len(task.results))

    assert task.status == "Completed", f"Task failed with status: {task.status}"
    assert len(task.results) > 0, "Expected at least 1 profile to be extracted"
    print("VERIFICATION SUCCEEDED: NO NotImplementedError!")


if __name__ == "__main__":
    asyncio.run(main())

