# -*- coding: utf-8 -*-
"""Contains classes and functions related to Algorithms for Enumerating All Perfect,
Maximum and Maximal Matchings in Bipartite Graphs. From Takeaki Uno publication.

The function `enum_perfect_matchings` can be used to enumerate all maximum matchings of a `BipartiteGraph`.
The function `enum_maximum_matchings` can be used to enumerate all maximum matchings of a `BipartiteGraph`.
"""
from typing import cast, Iterator, Any, Dict, List, Optional, Tuple

import copy
import networkx as nx
from networkx.algorithms.bipartite.matching import maximum_matching

from .graphs_utils import (create_directed_matching_graph, find_cycle_with_edge_of_matching,
                           graph_without_edge, graph_without_nodes_of_edge,
                           strongly_connected_components_decomposition, top_nodes, bottom_nodes)

LEFT = 0
RIGHT = 1

__all__ = ['enum_perfect_matchings', 'enum_maximum_matchings']


def enum_perfect_matchings(graph: nx.Graph) -> Iterator[Dict[Any, Any]]:
    if len(list(top_nodes(graph))) != len(list(bottom_nodes(graph))):
        return
    size = len(list(top_nodes(graph)))
    matching = maximum_matching(graph, top_nodes=top_nodes(graph))
    # Express the matching only from a top node to a bottom node
    matching = {k: v for k, v in matching.items() if k in top_nodes(graph)}
    if matching and len(matching) == size:
        yield matching
        directed_match_graph = create_directed_matching_graph(graph, top_nodes(graph), matching)
        trimmed_directed_match_graph = strongly_connected_components_decomposition(
            directed_match_graph)
        graph = trimmed_directed_match_graph.to_undirected()
        assert len(graph.edges) == len(trimmed_directed_match_graph.edges)
        assert len(graph.nodes) == len(trimmed_directed_match_graph.nodes)
        yield from _enum_perfect_matchings_iter(graph=copy.deepcopy(graph), matching=matching)


def _start_cycle_with_left(graph: nx.Graph, raw_cycle: List[Any]) -> Tuple[Any, ...]:
    # Make sure the cycle "starts"" in the the left part
    # If not, start the cycle from the second node, which is in the left part
    if graph.nodes[raw_cycle[0]]['bipartite'] == LEFT:
        return tuple(raw_cycle[:])
    else:
        return tuple(raw_cycle[-1:] + raw_cycle[:-1])

def _enum_perfect_matchings_iter(graph: nx.Graph, matching: Dict[Any, Any]) \
    -> Iterator[Dict[Any, Any]]:
    # Algorithm described in "Algorithms for Enumerating All Perfect, Maximum and Maximal Matchings in Bipartite Graphs"
    # By Takeaki Uno in "Algorithms and Computation: 8th International Symposium, ISAAC '97 Singapore,
    # December 17-19, 1997 Proceedings"
    # See http://dx.doi.org/10.1007/3-540-63890-3_11

    # Step 1
    if len(graph.edges) == 0:
        return

    # Find a cycle in the directed matching graph
    # Note that this cycle alternates between nodes from the left and the right part of the graph

    # TODO: avoid doing a directed graph by implementing missing algorithm steps from paper
    directed_match_graph = create_directed_matching_graph(graph, top_nodes(graph), matching)

    try:
        raw_cycle = find_cycle_with_edge_of_matching(graph=directed_match_graph, matching=matching)
    except nx.NetworkXNoCycle:
        return

    cycle = _start_cycle_with_left(graph, raw_cycle)
    assert directed_match_graph.nodes[cycle[0]]['bipartite'] == LEFT

    # Step 2 - TODO: Properly find right edge? (to get complexity bound)
    edge = cast(Tuple[Any, Any], tuple(cycle[:2]))

    # Step 3
    # already done because we are not really finding the optimal edge

    # Step 4
    # Construct new matching M' by flipping edges along the cycle, i.e. change the direction of all the
    # edges in the cycle
    matching_prime = matching.copy()
    for i in range(0, len(cycle), 2):
        matching_prime[cycle[i]] = cycle[i - 1]
    assert matching_prime != matching
    yield matching_prime

    # Construct G+(e)
    graph_plus = graph_without_nodes_of_edge(graph, edge)

    # Step 5
    # Trim unnecessary edges from G+(e).
    directed_match_graph_plus = create_directed_matching_graph(graph_plus, top_nodes(graph_plus),
                                                               matching)
    trimmed_directed_match_graph_plus = strongly_connected_components_decomposition(
        directed_match_graph_plus)
    graph_plus = trimmed_directed_match_graph_plus.to_undirected()
    assert len(graph_plus.edges) == len(trimmed_directed_match_graph_plus.edges)
    assert len(graph_plus.nodes) == len(trimmed_directed_match_graph_plus.nodes)

    # Step 6
    # Recurse with the old matching M but without the edge e
    yield from _enum_perfect_matchings_iter(graph_plus, matching)

    # Construct G-(e)
    graph_minus = graph_without_edge(graph, edge)

    # Step 7
    # Trim unnecessary edges from G-(e).
    directed_match_graph_minus = create_directed_matching_graph(graph_minus,
                                                                top_nodes(graph_minus),
                                                                matching_prime)
    trimmed_directed_match_graph_minus = strongly_connected_components_decomposition(
        directed_match_graph_minus)
    graph_minus = trimmed_directed_match_graph_minus.to_undirected()
    assert len(graph_minus.edges) == len(trimmed_directed_match_graph_minus.edges)
    assert len(graph_minus.nodes) == len(trimmed_directed_match_graph_minus.nodes)

    # Step 8
    # Recurse with the new matching M' but without the edge e
    yield from _enum_perfect_matchings_iter(graph_minus, matching_prime)


def enum_maximum_matchings(graph: nx.Graph) -> Iterator[Dict[Any, Any]]:
    matching = maximum_matching(graph, top_nodes=top_nodes(graph))
    # Express the matching only from a top node to a bottom node
    matching = {k: v for k, v in matching.items() if k in top_nodes(graph)}
    if matching:
        yield matching
        directed_match_graph = create_directed_matching_graph(graph, top_nodes(graph), matching)
        trimmed_directed_match_graph = strongly_connected_components_decomposition(
            directed_match_graph)
        yield from _enum_maximum_matchings_iter(graph=copy.deepcopy(graph),
                                                matching=matching,
                                                directed_match_graph=trimmed_directed_match_graph)


def _find_feaseable_two_edge_path(graph: nx.Graph, matching: Dict[Any,
                                                                  Any]) -> Optional[List[Any]]:
    # Find feasible path of length 2 in D(graph, matching)
    # This path has the form left1 -> right -> left2
    # left1 must be in the left part of the graph and in matching
    # right must be in the right part of the graph
    # left2 is also in the left part of the graph and but must not be in matching
    left1 = None
    left2 = None
    right = None

    for node1 in graph.nodes:
        if graph.nodes[node1]['bipartite'] == LEFT and node1 in matching.keys():
            left1 = node1
            right = matching[left1]
            if right in graph.nodes:
                for node2 in graph.neighbors(right):
                    if node2 not in matching:
                        left2 = node2
                        break
                if left2 is not None:
                    break

    if left2 is None:
        return None
    else:
        return [left1, right, left2]

def _enum_maximum_matchings_iter(graph: nx.Graph, matching: Dict[Any, Any],
                                          directed_match_graph: nx.DiGraph) \
        -> Iterator[Dict[Any, Any]]:
    # Algorithm described in "Algorithms for Enumerating All Perfect, Maximum and Maximal Matchings in Bipartite Graphs"
    # By Takeaki Uno in "Algorithms and Computation: 8th International Symposium, ISAAC '97 Singapore,
    # December 17-19, 1997 Proceedings"
    # See http://dx.doi.org/10.1007/3-540-63890-3_11

    # Step 1
    if len(graph.edges) == 0:
        return

    # Step 2
    # Find a cycle in the directed matching graph
    # Note that this cycle alternates between nodes from the left and the right part of the graph
    try:
        raw_cycle = find_cycle_with_edge_of_matching(graph=directed_match_graph, matching=matching)
    except nx.NetworkXNoCycle:
        raw_cycle = []

    if raw_cycle:
        cycle = _start_cycle_with_left(graph, raw_cycle)
        assert directed_match_graph.nodes[cycle[0]]['bipartite'] == LEFT

        # Step 3 - TODO: Properly find right edge? (to get complexity bound)
        edge = cast(Tuple[Any, Any], tuple(cycle[:2]))

        # Step 4
        # already done because we are not really finding the optimal edge

        # Step 5
        # Construct new matching M' by flipping edges along the cycle, i.e. change the direction of all the
        # edges in the cycle
        matching_prime = matching.copy()
        for i in range(0, len(cycle), 2):
            matching_prime[cycle[i]] = cycle[i - 1]

        assert matching_prime != matching
        yield matching_prime

        # Step 6
        # Construct G+(e) and D(G+(e), M\e)
        graph_plus = graph_without_nodes_of_edge(graph, edge)
        directed_match_graph_plus = create_directed_matching_graph(graph_plus,
                                                                   top_nodes(graph_plus), matching)
        # Recurse with the old matching M but without the edge e
        yield from _enum_maximum_matchings_iter(graph_plus, matching, directed_match_graph_plus)

        # Step 7
        # Construct G-(e) and D(G-(e), M')
        graph_minus = graph_without_edge(graph, edge)
        directed_match_graph_minus = create_directed_matching_graph(graph_minus,
                                                                    top_nodes(graph_minus),
                                                                    matching_prime)
        # Recurse with the new matching M' but without the edge e
        yield from _enum_maximum_matchings_iter(graph_minus, matching_prime,
                                                directed_match_graph_minus)

    else:
        # Step 8
        # Find feasible path of length 2 in D(graph, matching)
        path = _find_feaseable_two_edge_path(graph=graph, matching=matching)

        if not path:
            return

        # Construct M'
        # Exchange the direction of the path left1 -> right -> left2
        # to left1 <- right <- left2 in the new matching
        matching_prime = matching.copy()
        del matching_prime[path[0]]
        matching_prime[path[2]] = path[1]

        assert matching_prime != matching
        yield matching_prime

        edge = (path[2], path[1])

        # Step 9
        # Construct G+(e) and D(G+(e), M\e)
        graph_plus = graph_without_nodes_of_edge(graph, edge)
        dgm_plus = create_directed_matching_graph(graph_plus, top_nodes(graph_plus),
                                                  matching_prime)
        yield from _enum_maximum_matchings_iter(graph_plus, matching_prime, dgm_plus)

        # Step 10
        # Construct G-(e) and D(G-(e), M')
        graph_minus = graph_without_edge(graph, edge)
        dgm_minus = create_directed_matching_graph(graph_minus, top_nodes(graph_minus), matching)
        yield from _enum_maximum_matchings_iter(graph_minus, matching, dgm_minus)
