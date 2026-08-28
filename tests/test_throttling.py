from bot.throttling import FixedWindowCounter


def test_hits_are_counted_per_key_and_reset_each_window():
    now = [0.0]
    counter = FixedWindowCounter(window_seconds=60, clock=lambda: now[0])

    assert [counter.hit("a") for _ in range(3)] == [1, 2, 3]
    assert counter.hit("b") == 1

    now[0] = 60.0

    assert counter.hit("a") == 1
