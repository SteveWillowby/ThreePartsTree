import networkx as nx
from networkx import utils
from rule_miner_base import *
from rule import *
from rule_lib import *
from sets import Set
from itertools import combinations
from itertools import chain
import random
# from collections import OrderedDict

class ApproximateRuleMiner(RuleMinerBase):
    """Used to find and compress grammar rules in a graph"""

    def __init__(self, G):
        self._G = G

        self.in_sets = {}
        self.out_sets = {}
        self.both_sets = {}
        for node in list(self._G.nodes()):
            in_set = Set([edge[0] for edge in self._G.in_edges(node)])
            out_set = Set([edge[1] for edge in self._G.out_edges(node)])
            both_set = in_set | out_set
            in_only_set = in_set - both_set
            out_only_set = out_set - both_set
            self.in_sets[node] = in_only_set# OrderedDict(sorted(in_only_set))
            self.out_sets[node] = out_only_set# OrderedDict(sorted(out_only_set))
            self.both_sets[node] = both_set # OrderedDict(sorted(both_set))

    def determine_best_rule(self):
        nodes = list(self._G.nodes())
        rule_lib = RuleLib()
        rule_occurrences = {}
        for i in range(2, len(nodes) + 1):
            indices = [j for j in range(0, i)]
            done = False
            while not done:
                t = [nodes[idx] for idx in indices]
                if self.is_tuple_valid(t):
                    rule = Rule(t, self._G, rule_lib)
                    if rule.id() not in rule_occurrences:
                        rule_occurrences[rule.id()] = [{node: 1 for node in t}, rule, t]
                    else:
                        all_new_nodes = True
                        for node in t:
                            if node in rule_occurrences[rule.id()][0]:
                                all_new_nodes = False
                                break
                        if all_new_nodes:
                            for node in t:
                                rule_occurrences[rule.id()][0][node] = 1
                            rule_occurrences[rule.id()].append(t)
                indices_idx = i - 1
                indices[indices_idx] += 1
                while indices[indices_idx] == len(nodes) - (i - indices_idx) + 1:
                    indices[indices_idx] = -1 # Note that the loop finished.
                    if indices_idx == 0:
                        done = True
                        break
                    indices_idx -= 1
                    indices[indices_idx] += 1
                if not done:
                    while indices_idx < i:
                        if indices[indices_idx] == -1:
                            indices[indices_idx] = indices[indices_idx - 1] + 1
                        indices_idx += 1
            if len(rule_occurrences) > 0:
                break
            else:
                print(f"Going to size {i + 1}")
        max_len = 0
        best_rule = []
        for rule, occurrences in rule_occurrences.items():
            if len(occurrences) > max_len:
                max_len = len(occurrences)
                best_rule = occurrences
        return best_rule[1:len(best_rule)]

    def is_tuple_valid(self, t):
        ins = {}
        outs = {}
        counters = {}
        for n in t:
            counters[n] = 0
        max_in_len = 0
        max_out_len = 0
        for n in t:
            ins[n] = [edge[0] for edge in self._G.in_edges(n) if edge[0] not in counters]
            ins[n].sort()
            if len(ins[n]) > 0 and len(ins[n]) != max_in_len:
                if max_in_len != 0:
                    return False
                max_in_len = len(ins[n])
            outs[n] = [edge[1] for edge in self._G.out_edges(n) if edge[1] not in counters]
            outs[n].sort()
            if len(outs[n]) > 0 and len(outs[n]) != max_out_len:
                if max_out_len != 0:
                    return False
                max_out_len = len(outs[n])
        done_count = 0
        while done_count < len(t):
            done_count = 0
            first_iter = True
            for n in t:
                if len(ins[n]) == 0:
                    done_count += 1
                    continue
                if counters[n] >= len(ins[n]):
                    done_count += 1
                    curr_finished = True
                else:
                    curr_finished = False
                    curr_node = ins[n][counters[n]]
                if not first_iter:
                    if curr_finished != prev_finished or curr_node != prev_node:
                        return False
                first_iter = False
                prev_finished = curr_finished
                prev_node = curr_node

                counters[n] += 1

        for n in t:
            counters[n] = 0
        done_count = 0
        while done_count < len(t):
            done_count = 0
            first_iter = True
            for n in t:
                if len(outs[n]) == 0:
                    done_count += 1
                    continue
                if counters[n] >= len(outs[n]):
                    done_count += 1
                    curr_finished = True
                else:
                    curr_finished = False
                    curr_node = outs[n][counters[n]]
                if not first_iter:
                    if curr_finished != prev_finished or curr_node != prev_node:
                        return False
                first_iter = False
                prev_finished = curr_finished
                prev_node = curr_node
                counters[n] += 1
        return True

    # Thanks to Mark Rushakoff on Stack Overflow for the basis of this function. Although I might not use it.
    def powerset(self, iterable):
        "powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)"
        s = list(iterable)
        return chain.from_iterable(combinations(s, r) for r in range(len(s)+1))

    # Returns all valid, cheapest ways to edit the pair.
    # Or, if the pair is already valid, returns an empty array.
    def best_options_for_pair(self, a, b):
        just_a = Set([a])
        just_b = Set([b])

        in_comp = [self.in_sets[a] - just_b, self.in_sets[b] - just_a]
        in_comp.append(in_comp[0] & in_comp[1])
        out_comp = [self.out_sets[a] - just_b, self.out_sets[b] - just_a]
        out_comp.append(out_comp[0] & out_comp[1])

        three_in_values = [len(in_comp[0]), len(in_comp[1]), len(in_comp[0]) + len(in_comp[1]) - 2 * len(in_comp[2])]
        three_out_values = [len(out_comp[0]), len(out_comp[1]), len(out_comp[0]) + len(out_comp[1]) - 2 * len(out_comp[2])]

        in_min = min(three_in_values)
        out_min = min(three_out_values)

        if in_min == 0 and out_min == 0:
            # Already valid! No modifications needed. TODO: Add return value
            return

        a_in_add = Set()
        a_in_del = Set()
        b_in_add = Set()
        b_in_del = Set()

        a_out_add = Set()
        a_out_del = Set()
        b_out_add = Set()
        b_out_del = Set()
        single_return_value = [a_in_add, a_in_del, b_in_add, b_in_del, a_out_add, a_out_del, b_out_add, b_out_del]

        # Distinct possible best edit options:
        if three_in_values[0] == in_min:
            if three_out_values[0] == out_min:
                # Delete a_in and delete a_out
                a_in_del = in_comp[0]
                a_out_del = out_comp[0]
            if three_out_values[1] == out_min:
                # Delete a_in and delete b_out
                pass
            if three_out_values[2] == out_min:
                # Delete a_in and move outs to intersection
                # There are actually 2^(out_comp[2]) ways to do this!

                pass
        if three_in_values[1] == in_min:
            if three_out_values[0] == out_min:
                # Delete b_in and delete a_out
                pass
            if three_out_values[1] == out_min:
                # Delete b_in and delete b_out
                pass
            if three_out_values[2] == out_min:
                # Delete b_in and move outs to intersection
                # There are actually 2^(out_comp[2]) ways to do this!
                pass
        if three_in_values[2] == in_min:
            if three_out_values[0] == out_min:
                # Move ins to intersection and delete a_out
                # There are actually 2^(in_comp[2]) ways to do this!
                pass
            if three_out_values[1] == out_min:
                # Move ins to intersection and delete b_out
                # There are actually 2^(in_comp[2]) ways to do this!
                pass
            if three_out_values[2] == out_min:
                # Move both ins and outs to their respective intersections
                # There are actually 2^(in_comp[2] + out_comp[2]) ways to do this!
                pass


    def contract_valid_tuples(self, rule_with_occurrences):
        for i in range(1, len(rule_with_occurrences)):
            tuple = rule_with_occurrences[i]
            nodes = {n: 1 for n in tuple}
            in_edges = {}
            out_edges = {}
            all_internal_in = True
            all_internal_out = True
            for j in range(0, len(tuple)):
                if all_internal_in:
                    ie = self._G.in_edges(tuple[j])
                    for edge in ie:
                        if edge[0] not in nodes:
                            all_internal_in = False
                            in_edges[edge[0]] = 1
                if all_internal_out:
                    oe = self._G.out_edges(tuple[j])
                    for edge in oe:
                        if edge[1] not in nodes:
                            all_internal_out = False
                            out_edges[edge[1]] = 1
                if not all_internal_in and not all_internal_out:
                    break
            self._G.remove_nodes_from(tuple[1:len(tuple)])
            for source, ignored in in_edges.items():
                self._G.add_edge(source, tuple[0])
            for dest, ignored in out_edges.items():
                self._G.add_edge(tuple[0], dest)