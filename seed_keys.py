# -*- coding: utf-8 -*-
"""Наполнить склад ключами.

Реальные ключи из файла:  python seed_keys.py --file keys.txt --product 30d
Тестовые сгенерированные:  python seed_keys.py --gen 20 --product 30d
"""
import argparse
import random

import db

ALPHA = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

def gen_key():
    g = lambda: "".join(random.choice(ALPHA) for _ in range(4))
    return f"NLE-{g()}-{g()}-{g()}-{g()}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--product", required=True, help="id товара (см. /stock)")
    ap.add_argument("--file", help="файл, где ключ по одному в строке")
    ap.add_argument("--gen", type=int, help="сгенерировать N тестовых ключей")
    a = ap.parse_args()
    db.init()
    if not db.product(a.product):
        raise SystemExit(f"Нет товара '{a.product}'")
    if a.file:
        keys = open(a.file, encoding="utf-8").read().split()
    elif a.gen:
        keys = [gen_key() for _ in range(a.gen)]
    else:
        raise SystemExit("Нужно --file или --gen")
    added, skipped = db.add_keys(a.product, keys)
    print(f"Товар {a.product}: добавлено {added}, дублей пропущено {skipped}.")

if __name__ == "__main__":
    main()
