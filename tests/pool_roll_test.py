import _context

import icepool
import pytest

def test_pool_roll_eq():
    assert icepool.PoolRoll((1, 2, 3, 4)) == icepool.PoolRoll((1, 2, 3, 4))
    assert icepool.PoolRoll((1, 2, 3, 4)) == {1:1, 2:1, 3:1, 4:1}
    assert icepool.PoolRoll((1, 2, 3, 4)) != icepool.PoolRoll((1, 1, 2, 2, 3, 3, 4, 4))
    assert icepool.PoolRoll((1, 2, 3, 4)) != icepool.d4.pool(1)

def test_pool_roll_sum():
    roll = icepool.PoolRoll((1, 2, 3, 4))
    assert roll.sum() == 10

def test_pool_roll_sum_duplicates():
    roll = icepool.PoolRoll((1, 1, 1, 1, 2, 3, 4))
    assert roll.sum() == 13

def test_pool_roll_sum_negative():
    roll = icepool.PoolRoll({1:-1, 2:-1, 3:-1, 4:-1})
    assert roll.sum() == -10