# GrammarForge

[GrammarForge](./grammarforge.py) generates random, valid inputs from a
grammar and prints them one per line. Use it to create test inputs for a
program that expects structured input.

From *The Fuzzing Book*, "Fuzzing with Grammars": inputs built from a grammar
are valid by construction, so they get past a program's input checks instead
of being rejected. This is a small implementation of that basic grammar
fuzzer as a command-line tool.

## Usage

Run the program by giving it a path to a grammar file:

```powershell
python grammarforge.py grammar.txt
python grammarforge.py grammar.txt -n 5 --seed 42
python grammarforge.py grammar.txt -n 100 --max-length 512
```

With no other options, it prints 10 inputs.

| Option | Meaning |
| --- | --- |
| `-n`, `--count` | How many inputs to print (default: `10`) |
| `--seed` | Fix the random seed so a run can be repeated |
| `--max-length` | Maximum length of each generated input (default: `256`) |
| `--max-expansions` | Maximum nonterminal expansions per input (default: `1000`) |

## Output

For a grammar that generates arithmetic expressions, output might look like:

```text
2
(1+0)
((2+1)+0)
(0+(2+2))
```

The same `--seed` produces the same sequence of inputs:

```powershell
python grammarforge.py expression.txt -n 3 --seed 7
```

## Your own grammar

A grammar is a plain-text file. Each rule has a nonterminal, followed by
`::=` or `->`, followed by one or more alternatives separated by `|`.

```text
<expr> ::= <digit> | (<expr> + <digit>)
<digit> ::= 0 | 1 | 2 | 3
```

The first rule is the start rule. Nonterminals are written inside angle
brackets, such as `<expr>`. All referenced nonterminals must have a rule.
Recursive rules, such as `<expr>` referring to itself, allow nested inputs.

Generate inputs from this grammar:

```powershell
python grammarforge.py expression.txt -n 10 --seed 42
```

Lines beginning with `#` are comments, and blank lines are ignored.
Whitespace separates grammar tokens and is not included in generated output.

## Feeding a program

GrammarForge prints one input per line, so its output can be piped into a
program that reads lines from standard input:

```powershell
python grammarforge.py expression.txt -n 100 |
    ForEach-Object { .\my_program.exe $_ }
```

For programs that accept each input as a command-line argument, the generated
lines can be passed to a PowerShell loop as shown above.

## How it works

For each input, GrammarForge:

1. Selects a production for the current nonterminal.
2. Expands any nonterminals in that production.
3. Uses the shortest possible expansion lengths to avoid exceeding
   `--max-length`.
4. Stops if `--max-expansions` is reached.

It does not include coverage feedback, mutation, corpus management, or crash
monitoring. It is intentionally limited to the basic grammar-fuzzing method
from the chapter.
