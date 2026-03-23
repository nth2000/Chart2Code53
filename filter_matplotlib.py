#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os


def parse_args():
    parser = argparse.ArgumentParser(
        description="Check whether a Python file satisfies the original filtering logic."
    )
    parser.add_argument(
        "python_file",
        type=str,
        help="Path to the Python file to check."
    )
    return parser.parse_args()


def matches_original_logic_true(content: str) -> bool:
    if (
        'mpl_tookits' in content.lower()
        or 'matplotlib' in content
        or 'sankey' in content.lower()
        or 'networkx' in content.lower()
        or 'scipy.cluster.hierarchy.dendrogram' in content.lower()
        or 'mplfinance.plot' in content.lower()
    ):
        return False
    else:
        return True


def main():
    args = parse_args()

    if not os.path.isfile(args.python_file):
        raise FileNotFoundError(f"File not found: {args.python_file}")

    with open(args.python_file, "r", encoding="utf-8") as f:
        content = f.read()

    result = matches_original_logic_true(content)
    print(result)


if __name__ == "__main__":
    main()
