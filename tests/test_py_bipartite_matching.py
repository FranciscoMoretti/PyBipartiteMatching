#!/usr/bin/env python
"""Tests for `py_bipartite_matching` package."""
# -*- coding: utf-8 -*-
import itertools
import math

import hypothesis.strategies as st
from hypothesis import given
import pytest

from py_bipartite_matching.py_bipartite_matching import enum_perfect_matchings, enum_maximum_matchings
import py_bipartite_matching.graphs_utils as gu

from networkx.algorithms.bipartite.matching import maximum_matching
import networkx as nx

# Known limitation of pylint to process composites from hypothesis
# pylint: disable=no-value-for-parameter; `draw` provided by `@composite`


def print_debug_info(graph, matchings):
    print("Graph and matchings")
    print(f"Nodes :{graph.nodes}")
    print(f"Edges :{graph.edges}")
    print("Matchings :")
    for number, matching in enumerate(matchings):
        print(f"{number}: {set(matching)}")
    print("-" * 80)


@st.composite
def bipartite_graph(draw):
    m = draw(st.integers(min_value=1, max_value=4))
    n = draw(st.integers(min_value=1, max_value=5))
    top_nodes = list(range(m))
    bottom_nodes = list(range(10, 10 + n))

    graph = nx.Graph()
    graph.add_nodes_from(top_nodes, bipartite=0)
    graph.add_nodes_from(bottom_nodes, bipartite=1)
    for i in top_nodes:
        for j in bottom_nodes:
            if draw(st.booleans()):
                graph.add_edge(i, j)

    return graph


@st.composite
def balanced_bipartite_graph(draw):
    # For a perfect matching to exist the bipartite graph must have the same
    # the same number of vertex on each partition
    n = draw(st.integers(min_value=1, max_value=6))
    top_nodes = list(range(n))
    bottom_nodes = list(range(10, 10 + n))

    graph = nx.Graph()
    graph.add_nodes_from(top_nodes, bipartite=0)
    graph.add_nodes_from(bottom_nodes, bipartite=1)
    for i in top_nodes:
        for j in bottom_nodes:
            if draw(st.booleans()):
                graph.add_edge(i, j)

    return graph


@given(balanced_bipartite_graph())
def test_enum_perfect_matchings_correctness(graph):
    print("Testing enum_perfect_matchings_correctness")
    if len(list(gu.top_nodes(graph))) != len(list(gu.bottom_nodes(graph))):
        pass

    size = len(list(gu.top_nodes(graph)))  # should be equal to graph.right as well
    matchings = set()
    for matching in enum_perfect_matchings(graph):
        assert len(matching) == size, "Matching has a different size than the first one"
        for edge in matching.items():
            assert edge in graph.edges, "Matching contains an edge that was not in the graph"
        frozen_matching = frozenset(matching.items())
        assert frozen_matching not in matchings, "Matching was duplicate"
        matchings.add(frozen_matching)
    print_debug_info(graph=graph, matchings=matchings)


@given(bipartite_graph())
def test_enum_maximum_matchings_correctness(graph):
    print("Testing enum_maximum_matchings_correctness")
    size = None
    matchings = set()
    for matching in enum_maximum_matchings(graph):
        if size is None:
            size = len(matching)
        assert len(matching) == size, "Matching has a different size than the first one"
        for edge in matching.items():
            assert graph.has_edge(*edge), "Matching contains an edge that was not in the graph"
        frozen_matching = frozenset(matching.items())
        assert frozen_matching not in matchings, "Matching was duplicate"
        matchings.add(frozen_matching)
    print_debug_info(graph=graph, matchings=matchings)


@pytest.mark.parametrize('n', range(1, 6))
def test_perfect_matchings_completeness(n):
    print("Testing perfect_matchings_completeness")
    # Create a complete bipartite graph
    graph = nx.complete_bipartite_graph(n1=n, n2=n, create_using=nx.Graph)
    # Create a set of matchings to be sure there are no repetitions
    matchings = {frozenset(matching.items()) for matching in \
        enum_perfect_matchings(graph)}
    # The matchings count should be equal to n!
    assert len(matchings) == int(math.factorial(n))
    print_debug_info(graph=graph, matchings=matchings)


@pytest.mark.parametrize('n, m',
                         filter(lambda x: x[0] >= x[1],
                                itertools.product(range(1, 6), range(0, 4))))
def test_maximum_matchings_completeness(n, m):
    print("Testing maximum_matchings_completeness")
    # Create a complete bipartite graph
    graph = nx.complete_bipartite_graph(n1=n, n2=m, create_using=nx.Graph)
    # Create a set of matchings to be sure there are no repetitions
    matchings = {frozenset(matching.items()) for matching in \
        enum_maximum_matchings(graph)}
    # The matchings count should be equal to n!/(n-m)! if m > 0, 0 otherwise
    expected_count = m > 0 and int(math.factorial(n) / math.factorial(n - m)) or 0
    assert len(matchings) == expected_count
    print_debug_info(graph=graph, matchings=matchings)


@given(bipartite_graph())
def test_create_directed_matching_graph(graph):
    matching = maximum_matching(G=graph, top_nodes=gu.top_nodes(graph))
    digraph = gu.create_directed_matching_graph(graph=graph,
                                                top_nodes=gu.top_nodes(graph),
                                                matching=matching)
    assert graph.nodes == digraph.nodes
    assert len(graph.edges) == len(digraph.edges)