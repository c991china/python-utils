"""极简命令行骨架，演示 argparse 用法。"""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="python-utils 示例命令")
    parser.add_argument("name", help="要打招呼的名字")
    parser.add_argument("-n", "--times", type=int, default=1, help="重复次数")
    args = parser.parse_args()
    for _ in range(args.times):
        print(f"Hello, {args.name}!")


if __name__ == "__main__":
    main()
