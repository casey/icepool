import icepool
import pytest
"""
Tests the mix functionality of icepool.Die() and its derivatives.
"""


def test_mix_d6_faces():
    result = icepool.Die([1, 2, 3, 4, 5, 6])
    expected = icepool.d6
    assert result.equals(expected)


def test_mix_identical():
    assert icepool.Die([icepool.d6, icepool.d6, icepool.d6,
                        icepool.d6]).probabilities() == pytest.approx(
                            icepool.d6.probabilities())


def test_mix_mixed():
    die = icepool.Die([icepool.d4, icepool.d6])
    assert die.probabilities() == icepool.Die(range(1, 7),
                                              times=[5, 5, 5, 5, 2,
                                                     2]).probabilities()


def test_mix_lists():
    result = icepool.Die([[1, 2, 3, 4], [1, 2, 3, 4, 5, 6]])
    expected = icepool.Die([icepool.d4, icepool.d6])
    assert result == expected


def test_mix_reroll():
    result = icepool.Die([1, 2, 3, 4, icepool.Reroll, icepool.Reroll])
    expected = icepool.d4
    assert result.equals(expected)


def test_mix_dict_reroll():
    data = {1: 1, 2: 1, 3: 1, 4: 1, icepool.Reroll: 10}
    result = icepool.Die([data, data]).simplify()
    expected = icepool.d4
    assert result.equals(expected)


def test_if_else():
    assert (icepool.d6 >= 4).if_else(icepool.d6,
                                     icepool.d6 + 6).equals(icepool.d12,
                                                            simplify=True)
    assert (icepool.d6 - 3).if_else(True, False).equals(icepool.d6 != 6,
                                                        simplify=True)
