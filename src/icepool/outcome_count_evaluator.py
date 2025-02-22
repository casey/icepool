__docformat__ = 'google'

import icepool
from icepool.alignment import Alignment

from abc import ABC, abstractmethod
from collections import defaultdict
import enum
from functools import cached_property
import itertools
import math

from typing import Any, Callable, Collection, Hashable, Mapping, MutableMapping, Sequence

PREFERRED_ORDER_COST_FACTOR = 10
"""The preferred order will be favored this times as much."""


class Order(enum.IntEnum):
    """Can be used to define what order outcomes are seen in by OutcomeCountEvaluators."""
    Ascending = 1
    Descending = -1
    Any = 0


class OutcomeCountEvaluator(ABC):
    """An abstract, immutable, callable class for evaulating one or more `OutcomeCountGenerator`s.

    There is one abstract method to implement: `next_state()`.
    This should incrementally calculate the result given one outcome at a time
    along with how many of that outcome were produced.

    An example sequence of calls, as far as `next_state()` is concerned, is:

    1. `state = next_state(state=None, outcome=1, count_of_1s)`
    2. `state = next_state(state, 2, count_of_2s)`
    3. `state = next_state(state, 3, count_of_3s)`
    4. `state = next_state(state, 4, count_of_4s)`
    5. `state = next_state(state, 5, count_of_5s)`
    6. `state = next_state(state, 6, count_of_6s)`
    7. `outcome = final_outcome(state, *generators)`

    A few other methods can optionally be overridden to further customize behavior.

    It is not expected that subclasses of `OutcomeCountEvaluator`
    be able to handle arbitrary types or numbers of generators.
    Indeed, most are expected to handle only a fixed number of generators,
    and often even only generators with a particular type of `Die`.

    Instances cache all intermediate state distributions.
    You should therefore reuse instances when possible.

    Instances should not be modified after construction
    in any way that affects the return values of these methods.
    Otherwise, values in the cache may be incorrect.
    """

    @abstractmethod
    def next_state(self, state: Hashable, outcome, /, *counts) -> Hashable:
        """State transition function.

        This should produce a state given the previous state, an outcome,
        and the number that outcome produced by each generator.

        `evaluate()` will always call this using only positional arguments.
        Furthermore, there is no expectation that a subclass be able to handle
        an arbitrary number of counts. Thus, you are free to rename any of
        the parameters in a subclass, or to replace `*counts` with a fixed set
        of parameters.

        Make sure to handle the base case where `state is None`.

        States must be hashable. At current, they do not have to be orderable.
        However, this may change in the future, and if they are not totally
        orderable, you must override `final_outcome` to create totally orderable
        final outcomes.

        The behavior of returning a `Die` from `next_state` is currently
        undefined.

        Args:
            state: A hashable object indicating the state before rolling the
                current outcome. If this is the first outcome being considered,
                `state` will be `None`.
            outcome: The current outcome.
                `next_state` will see all rolled outcomes in monotonic order;
                either ascending or descending depending on `order()`.
                If there are multiple generators, the set of outcomes is the
                union of the outcomes of the invididual generators. All outcomes
                with nonzero count will be seen. Outcomes with zero count
                may or may not be seen. If you need to enforce that certain
                outcomes are seen even if they have zero count, see
                `alignment()`.
            *counts: One value (usually an `int`) for each generator output
                indicating how many of the current outcome were produced.
                All outcomes with nonzero count are guaranteed to be seen.
                To guarantee that outcomes are seen even if they have zero
                count, override `alignment()`.

        Returns:
            A hashable object indicating the next state.
            The special value `icepool.Reroll` can be used to immediately remove
            the state from consideration, effectively performing a full reroll.
        """

    def final_outcome(self, final_state: Hashable, /,
                      *generators: icepool.OutcomeCountGenerator) -> Any:
        """Optional function to generate a final outcome from a final state.

        Tthere is no expectation that a subclass be able to handle
        an arbitrary number of generators. Thus, you are free to rename any of
        the parameters in a subclass, or to replace `*generators` with a fixed
        set of parameters.

        By default, the final outcome is equal to the final state.
        Note that `None` is not a valid outcome for a `Die`,
        and if there are no outcomes, the final state will be `None`.
        Subclasses that want to handle this case should explicitly define what
        happens.

        Args:
            final_state: A state after all outcomes have been processed.
            *generators: One or more `OutcomeCountGenerator`s being evaluated.
                Most subclasses will expect a fixed number of generators and
                can replace this variadic parameter with a fixed number of named
                parameters.

        Returns:
            A final outcome that will be used as part of constructing the result `Die`.
            As usual for `Die()`, this could itself be a `Die` or `icepool.Reroll`.
        """
        return final_state

    def order(self, *generators: icepool.OutcomeCountGenerator) -> Order:
        """Optional function to determine the order in which `next_state()` will see outcomes.

        There is no expectation that a subclass be able to handle
        an arbitrary number of generators. Thus, you are free to rename any of
        the parameters in a subclass, or to replace `*generators` with a fixed
        set of parameters.

        The default is ascending order. This works well with mixed standard dice,
        and other dice that differ only by right-truncation.

        Args:
            *generators: One or more `OutcomeCountGenerator`s being evaluated.
                Most subclasses will expect a fixed number of generators and
                can replace this variadic parameter with a fixed number of named
                parameters.

        Returns:
            * Order.Ascending (= 1)
                if `next_state()` should always see the outcomes in ascending order.
            * Order.Descending (= -1)
                if `next_state()` should always see the outcomes in descending order.
            * Order.Any (= 0)
                if the result of the evaluation is order-independent.
        """
        return Order.Ascending

    def alignment(self,
                  *generators: icepool.OutcomeCountGenerator) -> Collection:
        """Optional method to specify an collection of outcomes that should always be given to `next_state()` even if they have zero count.

        There is no expectation that a subclass be able to handle
        an arbitrary number of generators. Thus, you are free to rename any of
        the parameters in a subclass, or to replace `*generators` with a fixed
        set of parameters.

        The default implementation returns `()`; this means outcomes with zero
        count may or may not be seen by `next_state`.

        If you want the outcomes seen by `next_state` to be consecutive
        `int`s, you can set `alignment = icepool.OutcomeCountEvaluator.range_alignment`.
        See `range_alignment()` below.
        """
        return ()

    def range_alignment(
            self,
            *generators: icepool.OutcomeCountGenerator) -> Collection[int]:
        """Example implementation of `alignment()` that produces consecutive `int` outcomes.

        There is no expectation that a subclass be able to handle
        an arbitrary number of generators. Thus, you are free to rename any of
        the parameters in a subclass, or to replace `*generators` with a fixed
        set of parameters.

        Set `alignment = icepool.OutcomeCountEvaluator.range_alignment` to use this.

        Returns:
            All `int`s from the min outcome to the max outcome among the generators,
            inclusive.

        Raises:
            TypeError: if any generator has any non-`int` outcome.
        """
        if len(generators) == 0:
            return ()

        if any(
                any(not isinstance(x, int)
                    for x in generator.outcomes())
                for generator in generators):
            raise TypeError(
                "range_alignment cannot be used with outcomes of type other than 'int'."
            )

        min_outcome = min(generator.min_outcome() for generator in generators)
        max_outcome = max(generator.max_outcome() for generator in generators)
        return range(min_outcome, max_outcome + 1)

    def final_kwargs(
            self,
            *generators: icepool.OutcomeCountGenerator) -> Mapping[str, Any]:
        """Optional method to specify any extra keyword arguments to the final die constructor."""
        return {}

    @cached_property
    def _cache(self) -> MutableMapping[Any, Mapping[Any, int]]:
        """A cache of (order, generators) -> weight distribution over states. """
        return {}

    def evaluate(
        self, *generators: icepool.OutcomeCountGenerator | Mapping[Any, int] |
        Sequence
    ) -> 'icepool.Die':
        """Evaluates generator(s).

        You can call the `OutcomeCountEvaluator` object directly for the same effect,
        e.g. `sum_evaluator(generator)` is an alias for `sum_evaluator.evaluate(generator)`.

        Most evaluators will expect a fixed number of generators.
        The union of the outcomes of the generator(s) must be totally orderable.

        Args:
            *generators: Each element may be one of the following:
                * A `OutcomeCountGenerator`.
                * A mappable mapping dice to the number of those dice.
                * A sequence of arguments to create a `Pool`.

        Returns:
            A `Die` representing the distribution of the final score.
        """

        # Convert non-`Pool` arguments to `Pool`.
        converted_generators = tuple(
            generator if isinstance(generator, icepool.OutcomeCountGenerator
                                   ) else icepool.Pool(generator)
            for generator in generators)

        if not all(generator._is_resolvable()
                   for generator in converted_generators):
            return icepool.Die([])

        algorithm, order = self._select_algorithm(*converted_generators)

        # We use a separate class to guarantee all outcomes are visited.
        alignment = Alignment(self.alignment(*converted_generators))

        dist = algorithm(order, alignment, tuple(converted_generators))

        final_outcomes = []
        final_weights = []
        for state, weight in dist.items():
            outcome = self.final_outcome(state, *converted_generators)
            if outcome is None:
                raise TypeError(
                    "None is not a valid final outcome. "
                    "This may have resulted from supplying an empty generator to OutcomeCountEvaluator. "
                    "If so, refrain from using empty generators, or override OutcomeCountEvaluator.final_outcome() to handle this case."
                )
            if outcome is not icepool.Reroll:
                final_outcomes.append(outcome)
                final_weights.append(weight)

        return icepool.Die(final_outcomes, final_weights,
                           **self.final_kwargs(*converted_generators))

    __call__ = evaluate

    def _select_algorithm(
            self, *generators: icepool.OutcomeCountGenerator
    ) -> tuple[Callable, Order]:
        """Selects an algorithm and iteration order.

        Returns:
            * The algorithm to use (`_eval_internal*`).
            * The order in which `next_state()` sees outcomes.
                1 for ascending and -1 for descending.
        """
        eval_order = self.order(*generators)

        pop_min_costs, pop_max_costs = zip(
            *(generator._estimate_order_costs() for generator in generators))

        pop_min_cost = math.prod(pop_min_costs)
        pop_max_cost = math.prod(pop_max_costs)

        # No preferred order case: go directly with cost.
        if eval_order == Order.Any:
            if pop_max_cost <= pop_min_cost:
                return self._eval_internal, Order.Ascending
            else:
                return self._eval_internal, Order.Descending

        # Preferred order case.
        # Go with the preferred order unless there is a "significant"
        # cost factor.

        if PREFERRED_ORDER_COST_FACTOR * pop_max_cost < pop_min_cost:
            cost_order = Order.Ascending
        elif PREFERRED_ORDER_COST_FACTOR * pop_min_cost < pop_max_cost:
            cost_order = Order.Descending
        else:
            cost_order = Order.Any

        if cost_order == Order.Any or eval_order == cost_order:
            # Use the preferred algorithm.
            return self._eval_internal, eval_order
        else:
            # Use the less-preferred algorithm.
            return self._eval_internal_iterative, eval_order

    def _eval_internal(
        self, order: int, alignment: Alignment,
        generators: tuple[icepool.OutcomeCountGenerator,
                          ...]) -> Mapping[Any, int]:
        """Internal algorithm for iterating in the more-preferred order,
        i.e. giving outcomes to `next_state()` from wide to narrow.

        All intermediate return values are cached in the instance.

        Arguments:
            order: The order in which to send outcomes to `next_state()`.
            alignment: As `alignment()`. Elements will be popped off this
                during recursion.
            generators: One or more `OutcomeCountGenerators`s to evaluate. Elements
                will be popped off this during recursion.

        Returns:
            A dict `{ state : weight }` describing the probability distribution
                over states.
        """
        cache_key = (order, alignment, generators)
        if cache_key in self._cache:
            return self._cache[cache_key]

        result: MutableMapping[Any, int] = defaultdict(int)

        if all(not generator.outcomes()
               for generator in generators) and not alignment.outcomes():
            result = {None: 1}
        else:
            outcome, prev_alignment, iterators = OutcomeCountEvaluator._pop_generators(
                order, alignment, generators)
            for p in itertools.product(*iterators):
                prev_generators, counts, weights = zip(*p)
                counts = tuple(itertools.chain.from_iterable(counts))
                prod_weight = math.prod(weights)
                prev = self._eval_internal(order, prev_alignment,
                                           prev_generators)
                for prev_state, prev_weight in prev.items():
                    state = self.next_state(prev_state, outcome, *counts)
                    if state is not icepool.Reroll:
                        result[state] += prev_weight * prod_weight

        self._cache[cache_key] = result
        return result

    def _eval_internal_iterative(
        self, order: int, alignment: Alignment,
        generators: tuple[icepool.OutcomeCountGenerator,
                          ...]) -> Mapping[Any, int]:
        """Internal algorithm for iterating in the less-preferred order,
        i.e. giving outcomes to `next_state()` from narrow to wide.

        This algorithm does not perform persistent memoization.
        """
        if all(not generator.outcomes()
               for generator in generators) and not alignment.outcomes():
            return {None: 1}
        dist: MutableMapping[Any, int] = defaultdict(int)
        dist[None, alignment, generators] = 1
        final_dist: MutableMapping[Any, int] = defaultdict(int)
        while dist:
            next_dist: MutableMapping[Any, int] = defaultdict(int)
            for (prev_state, prev_alignment,
                 prev_generators), weight in dist.items():
                # The order flip here is the only purpose of this algorithm.
                outcome, alignment, iterators = OutcomeCountEvaluator._pop_generators(
                    -order, prev_alignment, prev_generators)
                for p in itertools.product(*iterators):
                    generators, counts, weights = zip(*p)
                    counts = tuple(itertools.chain.from_iterable(counts))
                    prod_weight = math.prod(weights)
                    state = self.next_state(prev_state, outcome, *counts)
                    if state is not icepool.Reroll:
                        if all(not generator.outcomes()
                               for generator in generators):
                            final_dist[state] += weight * prod_weight
                        else:
                            next_dist[state, alignment,
                                      generators] += weight * prod_weight
            dist = next_dist
        return final_dist

    @staticmethod
    def _pop_generators(
        side: int, alignment: Alignment,
        generators: tuple[icepool.OutcomeCountGenerator, ...]
    ) -> tuple[Any, Alignment, tuple['icepool.NextOutcomeCountGenerator', ...]]:
        """Pops a single outcome from the generators.

        Returns:
            * The popped outcome.
            * The remaining alignment.
            * A tuple of iterators over the resulting generators, counts, and weights.
        """
        alignment_and_generators = (alignment,) + generators
        if side >= 0:
            outcome = max(generator.max_outcome()
                          for generator in alignment_and_generators
                          if generator.outcomes())

            next_alignment, _, _ = next(alignment._generate_max(outcome))

            return outcome, next_alignment, tuple(
                generator._generate_max(outcome) for generator in generators)
        else:
            outcome = min(generator.min_outcome()
                          for generator in alignment_and_generators
                          if generator.outcomes())

            next_alignment, _, _ = next(alignment._generate_min(outcome))

            return outcome, next_alignment, tuple(
                generator._generate_min(outcome) for generator in generators)

    def sample(self, *generators: icepool.OutcomeCountGenerator |
               Mapping[Any, int] | Sequence):
        """EXPERIMENTAL: Samples one result from the generator(s) and evaluates the result."""
        # Convert non-`Pool` arguments to `Pool`.
        converted_generators = tuple(
            generator if isinstance(generator, icepool.OutcomeCountGenerator
                                   ) else icepool.Pool(generator)
            for generator in generators)

        result = self.evaluate(*itertools.chain.from_iterable(
            generator.sample() for generator in converted_generators))

        if not result.is_empty():
            return result.outcomes()[0]
        else:
            return result
