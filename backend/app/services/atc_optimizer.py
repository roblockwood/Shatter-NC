"""ATC pot-assignment optimizer for Brother CNC rotary tool changers.

The Brother Speedio ATC carousel is a rotary magazine that always seeks the
shortest direction. Pocket N is physically adjacent to pocket 1.

Given an ordered list of tool calls extracted from an NC program the optimizer
builds a transition cost matrix and assigns tools to pots to minimise:

    Σ transition_count(Ti→Tj) × rotary_distance(pot_i, pot_j, N)
"""

import math
import random
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple


def rotary_distance(p1: int, p2: int, num_pockets: int) -> int:
    """Shortest carousel steps between pocket p1 and p2 on an N-pocket ring."""
    d = abs(p1 - p2)
    return min(d, num_pockets - d)


def _compute_cost(
    assignment: List[int],
    idx_of: Dict[int, int],
    transitions: Dict[Tuple[int, int], int],
    num_pockets: int,
) -> float:
    cost = 0.0
    for (t1, t2), count in transitions.items():
        if t1 in idx_of and t2 in idx_of:
            cost += count * rotary_distance(
                assignment[idx_of[t1]], assignment[idx_of[t2]], num_pockets
            )
    return cost


def _greedy_chain(
    tools: List[int],
    transitions: Dict[Tuple[int, int], int],
    available_pots: Optional[List[int]] = None,
) -> Dict[int, int]:
    """Assign tools to pockets by chaining the most-connected pairs first."""
    K = len(tools)
    if K == 0:
        return {}
    if available_pots is None:
        available_pots = list(range(1, K + 1))

    tool_set = set(tools)
    adj: Dict[int, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
    for (t1, t2), count in transitions.items():
        if t1 in tool_set and t2 in tool_set:
            adj[t1][t2] += count
            adj[t2][t1] += count

    free_transitions = {
        k: v for k, v in transitions.items() if k[0] in tool_set and k[1] in tool_set
    }
    if free_transitions:
        seed_pair = max(free_transitions, key=lambda k: free_transitions[k])
        chain: List[int] = [t for t in seed_pair if t in tool_set]
    else:
        chain = [tools[0]]

    remaining = set(tools) - set(chain)

    while remaining:
        best_tool: Optional[int] = None
        best_weight = -1
        append_right = True

        for tool in remaining:
            w_right = adj[chain[-1]].get(tool, 0)
            w_left = adj[chain[0]].get(tool, 0)
            if w_right >= w_left and w_right > best_weight:
                best_weight, best_tool, append_right = w_right, tool, True
            elif w_left > best_weight:
                best_weight, best_tool, append_right = w_left, tool, False

        if best_tool is None:
            best_tool = next(iter(remaining))
            append_right = True

        if append_right:
            chain.append(best_tool)
        else:
            chain.insert(0, best_tool)

        remaining.remove(best_tool)

    return {tool: available_pots[i] for i, tool in enumerate(chain)}


def _simulated_annealing(
    initial: Dict[int, int],
    tools: List[int],
    transitions: Dict[Tuple[int, int], int],
    num_pockets: int,
    iterations: int,
    rng: random.Random,
    free_tools: Optional[set] = None,
) -> Dict[int, int]:
    idx_of = {t: i for i, t in enumerate(tools)}
    assignment = [initial[t] for t in tools]
    K = len(tools)

    free_indices = [i for i, t in enumerate(tools) if free_tools is None or t in free_tools]
    KF = len(free_indices)
    if KF < 2:
        return {tools[i]: assignment[i] for i in range(K)}

    current_cost = _compute_cost(assignment, idx_of, transitions, num_pockets)
    best_cost = current_cost
    best_assignment = assignment[:]

    total_transitions = max(sum(transitions.values()), 1)
    avg_dist = current_cost / total_transitions if current_cost > 0 else float(num_pockets) / 4
    T = max(avg_dist * 5, 1.0)

    if iterations > 1:
        cooling = math.exp(math.log(0.01 / max(T, 1e-9)) / iterations)
    else:
        cooling = 1.0

    for _ in range(iterations):
        pi, pj = rng.sample(range(KF), 2)
        i, j = free_indices[pi], free_indices[pj]
        assignment[i], assignment[j] = assignment[j], assignment[i]

        new_cost = _compute_cost(assignment, idx_of, transitions, num_pockets)
        delta = new_cost - current_cost

        if delta < 0 or rng.random() < math.exp(-delta / max(T, 1e-10)):
            current_cost = new_cost
            if new_cost < best_cost:
                best_cost = new_cost
                best_assignment = assignment[:]
        else:
            assignment[i], assignment[j] = assignment[j], assignment[i]

        T *= cooling

    return {tools[i]: best_assignment[i] for i in range(K)}


def _two_opt_polish(
    assignment_dict: Dict[int, int],
    tools: List[int],
    transitions: Dict[Tuple[int, int], int],
    num_pockets: int,
    free_tools: Optional[set] = None,
) -> Dict[int, int]:
    idx_of = {t: i for i, t in enumerate(tools)}
    assignment = [assignment_dict[t] for t in tools]
    K = len(tools)

    free_indices = [i for i, t in enumerate(tools) if free_tools is None or t in free_tools]
    KF = len(free_indices)

    improved = True
    while improved:
        improved = False
        current_cost = _compute_cost(assignment, idx_of, transitions, num_pockets)
        for pi in range(KF):
            for pj in range(pi + 1, KF):
                i, j = free_indices[pi], free_indices[pj]
                assignment[i], assignment[j] = assignment[j], assignment[i]
                new_cost = _compute_cost(assignment, idx_of, transitions, num_pockets)
                if new_cost < current_cost - 1e-9:
                    current_cost = new_cost
                    improved = True
                else:
                    assignment[i], assignment[j] = assignment[j], assignment[i]

    return {tools[i]: assignment[i] for i in range(K)}


def _baseline_assignment(tools: List[int], num_pockets: int) -> Dict[int, int]:
    """Conventional 'tool number = pot number' assignment with collision handling."""
    result: Dict[int, int] = {}
    used: set = set()
    for t in tools:
        pot = t if 1 <= t <= num_pockets else ((t - 1) % num_pockets) + 1
        while pot in used:
            pot = (pot % num_pockets) + 1
        result[t] = pot
        used.add(pot)
    return result


def optimize_atc(
    tool_sequence: List[int],
    num_pockets: int = 21,
    sa_iterations: int = 60_000,
    random_seed: Optional[int] = None,
    current_assignment: Optional[Dict[int, int]] = None,
    pinned_tools: Optional[Dict[int, int]] = None,
) -> Dict[str, Any]:
    """Compute optimised tool-to-pot assignments for a Brother ATC carousel."""
    unique_tools: List[int] = sorted(set(tool_sequence))
    K = len(unique_tools)

    tool_changes = sum(1 for a, b in zip(tool_sequence, tool_sequence[1:]) if a != b)

    if K == 0:
        return {
            "tool_sequence": tool_sequence,
            "unique_tools": [],
            "tool_change_count": 0,
            "transition_matrix": {},
            "baseline_assignment": {},
            "optimized_assignment": {},
            "baseline_cost": 0,
            "optimized_cost": 0,
            "improvement_pct": 0.0,
        }

    if K > num_pockets:
        raise ValueError(
            f"NC program references {K} unique tools but the ATC only has {num_pockets} pockets."
        )

    from app.parsers.nc_tool_sequence_parser import build_transition_counts

    transitions = build_transition_counts(tool_sequence)

    if current_assignment:
        baseline: Dict[int, int] = {}
        used_pots: set = set()
        for t in unique_tools:
            pot = current_assignment.get(t)
            if pot is None or not (1 <= pot <= num_pockets):
                pot = t if 1 <= t <= num_pockets else ((t - 1) % num_pockets) + 1
            while pot in used_pots:
                pot = (pot % num_pockets) + 1
            baseline[t] = pot
            used_pots.add(pot)
    else:
        baseline = _baseline_assignment(unique_tools, num_pockets)

    pinned_map: Dict[int, int] = pinned_tools or {}
    pinned_in_prog: Dict[int, int] = {
        t: p for t, p in pinned_map.items() if t in set(unique_tools) and 1 <= p <= num_pockets
    }
    free_tools_set: set = set(unique_tools) - set(pinned_in_prog)
    free_tools_list: List[int] = [t for t in unique_tools if t in free_tools_set]
    pinned_pots: set = set(pinned_in_prog.values())

    free_pots: List[int] = []
    for pot in range(1, num_pockets + 1):
        if pot not in pinned_pots:
            free_pots.append(pot)
        if len(free_pots) == len(free_tools_list):
            break

    if K == 1:
        only_t = unique_tools[0]
        opt_pot = pinned_in_prog.get(only_t, free_pots[0] if free_pots else 1)
        return {
            "tool_sequence": tool_sequence,
            "unique_tools": unique_tools,
            "tool_change_count": tool_changes,
            "transition_matrix": {},
            "baseline_assignment": baseline,
            "optimized_assignment": {only_t: opt_pot},
            "baseline_cost": 0,
            "optimized_cost": 0,
            "improvement_pct": 0.0,
        }

    rng = random.Random(random_seed)

    if free_tools_list:
        initial_free = _greedy_chain(free_tools_list, transitions, free_pots)
        initial_full = {**pinned_in_prog, **initial_free}

        sa_result = _simulated_annealing(
            initial_full,
            unique_tools,
            transitions,
            num_pockets,
            sa_iterations,
            rng,
            free_tools=free_tools_set if pinned_in_prog else None,
        )

        optimized = _two_opt_polish(
            sa_result,
            unique_tools,
            transitions,
            num_pockets,
            free_tools=free_tools_set if pinned_in_prog else None,
        )
    else:
        optimized = dict(pinned_in_prog)

    baseline_cost = _compute_cost(
        [baseline[t] for t in unique_tools],
        {t: i for i, t in enumerate(unique_tools)},
        transitions,
        num_pockets,
    )
    optimized_cost = _compute_cost(
        [optimized[t] for t in unique_tools],
        {t: i for i, t in enumerate(unique_tools)},
        transitions,
        num_pockets,
    )

    improvement_pct = (
        round((baseline_cost - optimized_cost) / baseline_cost * 100, 1)
        if baseline_cost > 0
        else 0.0
    )

    pair_order: Dict[Tuple[int, int], int] = {}
    for a, b in zip(tool_sequence, tool_sequence[1:]):
        if a != b and (a, b) not in pair_order:
            pair_order[(a, b)] = len(pair_order)
    transition_matrix = {
        f"T{t1}→T{t2}": count
        for (t1, t2), count in sorted(transitions.items(), key=lambda kv: pair_order.get(kv[0], 9999))
    }

    return {
        "tool_sequence": tool_sequence,
        "unique_tools": unique_tools,
        "tool_change_count": tool_changes,
        "transition_matrix": transition_matrix,
        "baseline_assignment": {str(t): baseline[t] for t in unique_tools},
        "optimized_assignment": {str(t): optimized[t] for t in unique_tools},
        "baseline_cost": int(baseline_cost),
        "optimized_cost": int(optimized_cost),
        "improvement_pct": improvement_pct,
    }

