import asyncio
from datetime import date, timedelta
from io import BytesIO

import pytest

import graph


TODAY = date(2026, 9, 19)


def make_records(offsets_to_counts, today=TODAY):
    return {
        today - timedelta(days=offset): count
        for offset, count in offsets_to_counts.items()
    }


def test_create_graph_same_in_thread_and_sync():
    records = make_records({6: 3, 5: 3, 4: 6, 3: 5, 2: 10, 1: 54})

    class FakeLogic:
        def __init__(self, records):
            self._records = records

        def get_records(self, user_id):
            return self._records

    fake = FakeLogic(records)

    # direct call
    sync_result = graph.create_graph(fake, user_id=1, timeline="Monthly", theme="dark", today=TODAY)

    # call via to_thread
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        thread_result = loop.run_until_complete(
            asyncio.to_thread(
                graph.create_graph, fake, 1, "Monthly", "dark", TODAY
            )
        )
    finally:
        loop.close()

    # Both should be identical sentinel or BytesIO contents
    assert (sync_result is None) == (thread_result is None)
    assert (sync_result == "empty_range") == (thread_result == "empty_range")

    if isinstance(sync_result, BytesIO):
        # compare bytes
        sync_result.seek(0)
        thread_result.seek(0)
        assert sync_result.read() == thread_result.read()
