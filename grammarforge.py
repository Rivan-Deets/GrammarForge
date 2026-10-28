"""A small grammar-based fuzzer.

This follows the basic grammar-fuzzing approach:

1. Pick a production for the current nonterminal.
2. Replace its nonterminals recursively.
3. Stop when the generated input reaches a size limit.

Grammar format::

    <start> ::= <number> | (<start> + <number>)
    <number> ::= 0 | 1 | 2 | 3

Whitespace separates grammar tokens and is not included in generated output.
"""

from __future__ import annotations

import argparse
import random
import re
from pathlib import Path
from typing import Iterator, Mapping


NONTERMINAL = re.compile(r"<[^<>]+>")
RULE = re.compile(r"^(<[^<>]+>)\s*(?:\:\:\=|->)\s*(.*)$")


def parse_grammar(text: str) -> tuple[dict[str, list[list[str]]], str]:
    """Parse a small BNF grammar and return its rules and start symbol."""
    grammar: dict[str, list[list[str]]] = {}

    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        match = RULE.match(line)
        if match is None:
            raise ValueError(f"invalid rule on line {line_number}")

        name, alternatives = match.groups()
        grammar.setdefault(name, []).extend(
            [
                token.strip()
                for token in re.split(f"({NONTERMINAL.pattern})", alternative)
                if token.strip()
            ]
            for alternative in alternatives.split("|")
        )

    if not grammar:
        raise ValueError("grammar is empty")

    references = {
        token
        for productions in grammar.values()
        for production in productions
        for token in production
        if NONTERMINAL.fullmatch(token)
    }
    missing = references - grammar.keys()
    if missing:
        raise ValueError(f"undefined nonterminal(s): {', '.join(sorted(missing))}")

    return grammar, next(iter(grammar))


class GrammarFuzzer:
    """Generate bounded strings from a context-free grammar."""

    def __init__(
        self,
        grammar: Mapping[str, list[list[str]]],
        start: str,
        *,
        seed: int | None = None,
        max_length: int = 256,
        max_expansions: int = 1_000,
    ) -> None:
        if start not in grammar:
            raise ValueError(f"start symbol {start!r} is not defined")
        if max_length < 0 or max_expansions < 1:
            raise ValueError("limits must be positive, except max_length")

        self.grammar = grammar
        self.start = start
        self.max_length = max_length
        self.max_expansions = max_expansions
        self.random = random.Random(seed)
        self.minimum = self._find_minimum_lengths()

    def _find_minimum_lengths(self) -> dict[str, int]:
        """Precompute the shortest possible output for each nonterminal."""
        minimum = {name: float("inf") for name in self.grammar}

        changed = True
        while changed:
            changed = False
            for name, productions in self.grammar.items():
                for production in productions:
                    if all(
                        token not in self.grammar or minimum[token] != float("inf")
                        for token in production
                    ):
                        length = sum(
                            minimum.get(token, len(token))
                            for token in production
                        )
                        if length < minimum[name]:
                            minimum[name] = length
                            changed = True

        impossible = [name for name, length in minimum.items() if length == float("inf")]
        if impossible:
            raise ValueError(
                f"nonterminal(s) cannot produce output: {', '.join(impossible)}"
            )
        return {name: int(length) for name, length in minimum.items()}

    def generate(self) -> str:
        """Generate one string without exceeding the configured limits."""
        pending = [self.start]
        output: list[str] = []
        expansions = 0

        while pending:
            symbol = pending.pop()
            if symbol not in self.grammar:
                output.append(symbol)
                continue

            expansions += 1
            if expansions > self.max_expansions:
                raise RuntimeError("maximum grammar expansions exceeded")

            current_length = sum(map(len, output))
            pending_length = sum(
                self.minimum.get(item, len(item)) for item in pending
            )
            budget = self.max_length - current_length - pending_length

            choices = [
                production
                for production in self.grammar[symbol]
                if sum(self.minimum.get(item, len(item)) for item in production)
                <= budget
            ]
            if not choices:
                raise RuntimeError(
                    f"no production for {symbol} fits max_length={self.max_length}"
                )

            pending.extend(reversed(self.random.choice(choices)))

        return "".join(output)

    def generate_many(self, count: int) -> Iterator[str]:
        """Yield ``count`` independent fuzz inputs."""
        if count < 0:
            raise ValueError("count must be non-negative")
        for _ in range(count):
            yield self.generate()


def main() -> None:
    parser = argparse.ArgumentParser(prog="grammarforge")
    parser.add_argument("grammar", type=Path)
    parser.add_argument("-n", "--count", type=int, default=10)
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument("--max-expansions", type=int, default=1_000)
    parser.add_argument("--seed", type=int)
    args = parser.parse_args()

    grammar, start = parse_grammar(args.grammar.read_text(encoding="utf-8"))
    fuzzer = GrammarFuzzer(
        grammar,
        start,
        seed=args.seed,
        max_length=args.max_length,
        max_expansions=args.max_expansions,
    )
    for value in fuzzer.generate_many(args.count):
        print(value)


if __name__ == "__main__":
    main()