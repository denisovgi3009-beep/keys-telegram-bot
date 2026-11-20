# -*- coding: utf-8 -*-
"""Настройки бота. Всё, что можно менять, — здесь или в .env."""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Доступ ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
# Telegram user id владельца(ов). Получить: написать @userinfobot
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").replace(",", " ").split() if x.strip()}

# --- Товары: (id, название, срок, цена в ЕВРОЦЕНТАХ) ---
PRODUCTS = [
    ("30d", "Neverlose CS2", "30 days", 2900),
    ("90d", "Neverlose CS2", "90 days", 7900),
    ("180d", "Neverlose CS2", "180 days", 14900),
    ("1y", "Neverlose CS2", "1 year", 26900),
]
PRODUCT_MAP = {p[0]: p for p in PRODUCTS}

# --- Реквизиты для оплаты. ЗАМЕНИТЕ на свои ---
PAYMENT_TEXT = (
    "💳 <b>Как оплатить</b>\n"
    "Переведите точную сумму на один из способов:\n\n"
    "• Карта: <code>0000 0000 0000 0000</code>\n"
    "• USDT (TRC20): <code>T...ваш адрес...</code>\n"
    "• BTC: <code>bc1...ваш адрес...</code>\n\n"
    "После оплаты нажмите «Я оплатил» — продавец проверит и выдаст ключ."
)

# --- Тексты ---
DISCLAIMER = (
    "⚠️ Продавец не связан с официальным Neverlose. "
    "Это независимый магазин ключей. Оплата — по вашему согласию."
)

def eur(cents: int) -> str:
    """2900 -> '29 €', 14950 -> '149,50 €'."""
    if cents % 100 == 0:
        return f"{cents // 100} €"
    return f"{cents // 100},{cents % 100:02d} €"
