#!/usr/bin/env python3
"""Атомарно переставить символическую ссылку на новый каталог.

os.replace переименовывает поверх существующей ссылки одним системным вызовом — окна, в котором
ссылки нет, не возникает ни на Linux, ни на macOS.

    python3 swap_link.py <куда указывает> <путь ссылки>
"""
import os
import sys


def main() -> int:
    target, link = sys.argv[1:3]
    tmp = "%s.new.%d" % (link, os.getpid())
    if os.path.islink(tmp) or os.path.exists(tmp):
        os.remove(tmp)
    os.symlink(target, tmp)
    os.replace(tmp, link)
    return 0


if __name__ == "__main__":
    sys.exit(main())
