#!/usr/bin/env python3

import sys

def process_markdown(file_path, prompt):
    blocks = []
    block = []

    with open(file_path, 'r') as file:
        for line in file:
            if line.lstrip().startswith(prompt):
                line = line.strip()
                pos = line.find('>')
                if pos == -1 or pos == len(line) - 1:
                    continue

                line = line[pos + 2:]
                block.append(line)
            elif block:
                blocks.append(block.copy())
                block = []

    return blocks

def main():
    if len(sys.argv) != 2:
        print("Usage: md-to-cli.py MARKDOWN-FILE")
        sys.exit(1)

    file_path = sys.argv[1]
    blocks = process_markdown(file_path, "admin@example:")

    for block in blocks:
        print(f"")
        for line in block:
            line = line.replace("eth0", "x2")
            line = line.replace("eth1", "x3")
            print(line)

if __name__ == "__main__":
    main()

