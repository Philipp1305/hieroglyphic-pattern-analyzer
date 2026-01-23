import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "sorted_glyphes.csv"

# Runs in O(n)


def load_sequence() -> List[int]:
    df = pd.read_csv(DATA_PATH)
    return df["gardiner_code"].astype(int).tolist()


# ---- Ukkonen suffix tree implementation for integer sequences ----


@dataclass
class End:
    val: int


@dataclass
class Edge:
    start: int
    end: End
    dest: "Node"

    def length(self, current_pos: int) -> int:
        # Edge length considering open end
        return min(self.end.val, current_pos) - self.start + 1


@dataclass
class Node:
    children: Dict[int, Edge] = field(default_factory=dict)
    suffix_link: Optional["Node"] = None

    def add_edge(self, ch: int, edge: Edge) -> None:
        self.children[ch] = edge

    def get_edge(self, ch: int) -> Optional[Edge]:
        return self.children.get(ch)


class SuffixTree:
    def __init__(self, data: List[int]):
        # Append a unique terminator smaller than any gardiner code
        self.data = data + [-1]
        self.n = len(self.data)
        self.root = Node()
        self.build()

    def build(self) -> None:
        text = self.data
        root = self.root
        root.suffix_link = root

        active_node = root
        active_edge = -1
        active_length = 0
        remaining = 0
        leaf_end = End(-1)
        last_new_node: Optional[Node] = None

        for pos, ch in enumerate(text):
            leaf_end.val = pos
            remaining += 1
            last_new_node = None

            while remaining > 0:
                if active_length == 0:
                    active_edge = pos

                edge = active_node.get_edge(text[active_edge])

                if edge is None:
                    # No edge starting with this char; create leaf
                    leaf = Node()
                    active_node.add_edge(text[active_edge], Edge(pos, leaf_end, leaf))

                    if last_new_node and last_new_node is not root:
                        last_new_node.suffix_link = active_node
                    last_new_node = None

                else:
                    edge_span = edge.length(pos)
                    if active_length >= edge_span:
                        active_edge += edge_span
                        active_length -= edge_span
                        active_node = edge.dest
                        continue

                    if text[edge.start + active_length] == ch:
                        active_length += 1
                        if last_new_node and last_new_node is not root:
                            last_new_node.suffix_link = active_node
                        break

                    # Split edge
                    split_end = End(edge.start + active_length - 1)
                    split = Node()
                    active_node.add_edge(
                        text[active_edge], Edge(edge.start, split_end, split)
                    )

                    edge.start = split_end.val + 1
                    split.add_edge(text[edge.start], edge)

                    leaf = Node()
                    split.add_edge(ch, Edge(pos, leaf_end, leaf))

                    if last_new_node:
                        last_new_node.suffix_link = split
                    last_new_node = split

                remaining -= 1

                if active_node is root and active_length > 0:
                    active_length -= 1
                    active_edge = pos - remaining + 1
                elif active_node is not root:
                    active_node = active_node.suffix_link or root

    def _collect(
        self,
        node: Node,
        path: List[Tuple[int, int]],
        min_length: int,
        results: List[Tuple[int, Tuple[int, ...], int]],
        sentinel_index: int,
    ) -> int:
        # Returns number of leaves under this node
        if not node.children:
            return 1

        leaf_count = 0
        for edge in node.children.values():
            seg_end = min(edge.end.val, sentinel_index - 1)
            seg_len = seg_end - edge.start + 1
            if seg_len <= 0:
                continue

            path.append((edge.start, seg_end))
            child_leaves = self._collect(
                edge.dest, path, min_length, results, sentinel_index
            )
            leaf_count += child_leaves

            path.pop()

        # Evaluate current path (excluding root)
        if path:
            path_len = sum(end - start + 1 for start, end in path)
            if path_len >= min_length and leaf_count >= 2:
                seq = []
                for start, end in path:
                    seq.extend(self.data[start : end + 1])
                results.append((path_len, tuple(seq), leaf_count))

        return leaf_count

    def repeated_substrings(
        self, min_length: int = 1
    ) -> List[Tuple[int, Tuple[int, ...], int]]:
        results: List[Tuple[int, Tuple[int, ...], int]] = []
        sentinel_index = len(self.data)
        self._collect(self.root, [], min_length, results, sentinel_index)

        # Deduplicate by sequence keeping max length and count
        best: Dict[Tuple[int, ...], Tuple[int, int]] = {}
        for length, seq, count in results:
            if (
                seq not in best
                or length > best[seq][0]
                or (length == best[seq][0] and count > best[seq][1])
            ):
                best[seq] = (length, count)

        deduped = [(length, seq, count) for seq, (length, count) in best.items()]
        deduped.sort(key=lambda x: (-x[0], -x[2], x[1]))
        return deduped

    def _count_leaves(self, node: Node) -> int:
        if not node.children:
            return 1
        return sum(self._count_leaves(edge.dest) for edge in node.children.values())

    def search(self, pattern: List[int]) -> int:
        """
        Return the number of occurrences of a pattern (as count of suffix leaves under the match).
        """
        if not pattern:
            return 0

        node = self.root
        idx = 0
        while idx < len(pattern):
            edge = node.get_edge(pattern[idx])
            if edge is None:
                return 0

            edge_len = edge.end.val - edge.start + 1
            to_match = min(edge_len, len(pattern) - idx)
            for j in range(to_match):
                if self.data[edge.start + j] != pattern[idx + j]:
                    return 0

            idx += to_match

            if idx == len(pattern):
                # pattern ended inside this edge or exactly at its end; occurrences = leaves under dest
                return self._count_leaves(edge.dest)

            # otherwise we consumed full edge, move deeper
            node = edge.dest

        return 0


def display_top(results: List[Tuple[int, Tuple[int, ...], int]], limit: int) -> None:
    top = results[:limit]
    if not top:
        print("No repeated sequences found.")
        return

    print(f"\n{'Rank':<6} {'Length':<10} {'Occurrences':<12} Pattern")
    print("-" * 60)
    for idx, (length, seq, count) in enumerate(top, 1):
        print(f"{idx:<6} {length:<10} {count:<12} {list(seq)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Suffix tree LCP finder for Gardiner codes"
    )
    parser.add_argument(
        "--min-length", type=int, default=1, help="Minimum pattern length to report"
    )
    parser.add_argument(
        "--limit", type=int, default=15, help="How many top patterns to show"
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Comma-separated Gardiner codes to search as a pattern",
    )
    args = parser.parse_args()

    seq = load_sequence()
    tree = SuffixTree(seq)
    results = tree.repeated_substrings(min_length=args.min_length)
    display_top(results, limit=args.limit)

    if args.query:
        try:
            pattern = [int(x.strip()) for x in args.query.split(",") if x.strip()]
        except ValueError:
            print(
                "Invalid --query pattern. Use comma-separated integers, e.g. '1,2,3'."
            )
            return

        occ = tree.search(pattern)
        print(f"\nQuery {pattern} occurrences: {occ}")


if __name__ == "__main__":
    main()
