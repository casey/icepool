import hdroller
import hdroller.math

from scipy.special import comb
import numpy

"""
These deal with all sorted tuples of tuple_length whose elements are between 0 and num_values-1 inclusive.
Tuples are indexed in lexicographic order.
"""
def num_sorted_tuples(tuple_length, num_values):
    return comb(num_values, tuple_length, exact=True, repetition=True)

def iter_sorted_tuples(tuple_length, num_values, start_value=0):
    """
    Iterates through all sorted tuples.
    """
    if tuple_length == 0:
        yield ()
        return
    
    for head_value in range(start_value, num_values):
        for tail in iter_sorted_tuples(tuple_length - 1, num_values, head_value):
            yield (head_value,) + tail

def ravel_sorted_tuple(tuple, num_values, start_value=0):
    """
    Given a sorted tuple, returns the index of that tuple.
    """
    if len(tuple) == 0:
        return 0
    elif len(tuple) == 1:
        return tuple[0] - start_value
    result = 0
    for head_value in range(start_value, tuple[0]):
        result += num_sorted_tuples(len(tuple) - 1, num_values - head_value)
    return result + ravel_sorted_tuple(tuple[1:], num_values, tuple[0])

def keep_transition(tuple_length, num_values, transition_slice):
    """
    [new_value, sorted_tuple_index] -> next_sorted_tuple_index
    """
    num_tuples = num_sorted_tuples(tuple_length, num_values)
    result = numpy.zeros((num_values, num_tuples), dtype=int)
    for value in range(num_values):
        for sorted_tuple_index, sorted_tuple in enumerate(iter_sorted_tuples(tuple_length, num_values)):
            next_sorted_tuple = sorted((value,) + sorted_tuple)[transition_slice]
            next_sorted_tuple_index = ravel_sorted_tuple(next_sorted_tuple, num_values)
            result[value, sorted_tuple_index] = next_sorted_tuple_index
    return result
    
def keep(num_keep, *dice, transition_slice):
    dice = hdroller.Die._union_outcomes(*dice)
    
    num_values = len(dice[0])
    sorted_pmf_length = num_sorted_tuples(num_keep, num_values)
    sorted_pmf = numpy.zeros((sorted_pmf_length,))
    
    # Initial state.
    unsorted_shape = (num_values,) * num_keep
    for faces in numpy.ndindex(unsorted_shape):
        mass = numpy.product([die.pmf()[face] for die, face in zip(dice[:num_keep], faces)])
        faces = tuple(sorted(faces))
        index = ravel_sorted_tuple(faces, num_values)
        sorted_pmf[index] += mass
    
    print(sorted_pmf)
    # Step through the remaining dice.
    transition = keep_transition(num_keep, num_values, transition_slice)
    print(transition)
    for die in dice[num_keep:]:
        next_sorted_pmf = numpy.zeros_like(sorted_pmf)
        for face in range(num_values):
            indices = transition[face, :]
            masses = die.pmf()[face] * sorted_pmf
            numpy.add.at(next_sorted_pmf, indices, masses)
        sorted_pmf = next_sorted_pmf
    
    # Sum the faces.
    sum_pmf_length = num_keep * (num_values - 1) + 1
    sum_pmf = numpy.zeros((sum_pmf_length,))
    sum_min_outcome = num_keep * dice[0].min_outcome()
    
    for faces, mass in zip(iter_sorted_tuples(num_keep, num_values), sorted_pmf):
        sum_pmf[sum(faces)] += mass
    
    print(sum_pmf)
    return hdroller.Die(sum_pmf, sum_min_outcome)._trim()

def keep_highest(num_keep, *dice):
    return keep(num_keep, *dice, transition_slice=slice(1, None))
    
def keep_lowest(num_keep, *dice):
    return keep(num_keep, *dice, transition_slice=slice(None, -1))