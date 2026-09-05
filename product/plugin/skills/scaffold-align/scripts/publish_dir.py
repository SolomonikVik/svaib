#!/usr/bin/env python3
"""Опубликовать собранный каталог снимка под его окончательным именем.

Имя каталога — отпечаток содержимого, поэтому параллельные выгрузки кладут одно и то же. Гонку
разрешает сам os.rename: он либо переносит каталог целиком, либо отказывает, если имя уже занято
— и тогда снимок уже положил другой вызов. Наивный `mv` в этом случае положил бы каталог ВНУТРЬ
существующего.

    python3 publish_dir.py <собранный каталог> <окончательный путь> <проверяемый файл внутри>
"""
import os
import shutil
import sys


def main() -> int:
    staged, dest, marker = sys.argv[1:4]
    try:
        os.rename(staged, dest)
    except OSError:
        # имя занято: снимок уже опубликован кем-то ещё — свой черновик убираем
        shutil.rmtree(staged, ignore_errors=True)
    return 0 if os.path.isfile(os.path.join(dest, marker)) else 1


if __name__ == "__main__":
    sys.exit(main())
