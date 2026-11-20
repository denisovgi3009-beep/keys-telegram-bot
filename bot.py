# -*- coding: utf-8 -*-
"""Telegram-бот продажи ключей подписки.
Поток: /start -> выбор срока -> счёт на оплату -> 'Я оплатил' ->
уведомление админу -> админ подтверждает -> бот выдаёт ключ из склада.
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message)

import db
from config import ADMIN_IDS, BOT_TOKEN, DISCLAIMER, PAYMENT_TEXT, eur

log = logging.getLogger("bot")
router = Router()

def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS

# ---------- Клавиатуры ----------
def catalog_kb(counts) -> InlineKeyboardMarkup:
    rows = []
    for r in counts:
        label = f"{r['duration']} — {eur(r['price'])}"
        if r["free"] == 0:
            label += "  ⛔"
        else:
            label += f"  ({r['free']})"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"buy:{r['id']}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def pay_kb(oid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"paid:{oid}")
    ]])

def admin_order_kb(oid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✔️ Подтвердить", callback_data=f"ok:{oid}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"no:{oid}"),
    ]])

# ---------- Пользователь ----------
@router.message(CommandStart())
async def cmd_start(m: Message):
    kb = catalog_kb(db.stock_counts())
    await m.answer(
        "🛒 <b>Магазин ключей</b>\n\nВыберите срок подписки:\n\n" + DISCLAIMER,
        reply_markup=kb,
    )

@router.message(Command("catalog"))
async def cmd_catalog(m: Message):
    await cmd_start(m)

@router.callback_query(F.data == "catalog")
async def cb_catalog(cb: CallbackQuery):
    kb = catalog_kb(db.stock_counts())
    await cb.message.edit_text("🛒 <b>Магазин ключей</b>\n\nВыберите срок:", reply_markup=kb)
    await cb.answer()

@router.callback_query(F.data.startswith("buy:"))
async def cb_buy(cb: CallbackQuery):
    pid = cb.data.split(":", 1)[1]
    p = db.product(pid)
    if not p:
        return await cb.answer("Товар не найден", show_alert=True)
    # проверка наличия на складе
    free = next((r["free"] for r in db.stock_counts() if r["id"] == pid), 0)
    if free <= 0:
        return await cb.answer("Нет в наличии 😔", show_alert=True)
    oid = db.create_order(cb.from_user.id, cb.from_user.username, pid)
    await cb.message.edit_text(
        f"🧾 <b>Заказ #{oid}</b>\n"
        f"{p['title']} · {p['duration']}\n"
        f"Сумма: <b>{eur(p['price'])}</b>\n\n"
        f"{PAYMENT_TEXT}",
        reply_markup=pay_kb(oid),
    )
    await cb.answer()

@router.callback_query(F.data.startswith("paid:"))
async def cb_paid(cb: CallbackQuery):
    oid = int(cb.data.split(":", 1)[1])
    o = db.get_order(oid)
    if not o:
        return await cb.answer("Заказ не найден", show_alert=True)
    db.mark_paid(oid)
    p = db.product(o["product_id"])
    note = (f"💰 <b>Клиент сообщил об оплате</b>\n"
            f"Заказ #{oid} · {p['duration']} · {eur(o['amount'])}\n"
            f"От: @{cb.from_user.username or cb.from_user.id}")
    kb = admin_order_kb(oid)
    for a in ADMIN_IDS:
        try:
            await cb.bot.send_message(a, note, reply_markup=kb, parse_mode=ParseMode.HTML)
        except Exception as e:
            log.warning("notify admin %s failed: %s", a, e)
    await cb.message.edit_text(
        cb.message.text + "\n\n⏳ <b>Оплата проверяется.</b> Ключ придёт сразу после подтверждения.",
        reply_markup=None,
    )
    await cb.answer("Уведомили продавца 👍")

# ---------- Админ ----------
@router.callback_query(F.data.startswith("ok:"))
async def cb_ok(cb: CallbackQuery, bot: Bot):
    if not is_admin(cb.from_user.id):
        return await cb.answer("Только для админа", show_alert=True)
    oid = int(cb.data.split(":", 1)[1])
    key = db.deliver(oid)
    if not key:
        return await cb.answer("На складе нет свободных ключей!", show_alert=True)
    o = db.get_order(oid)
    try:
        await bot.send_message(
            o["chat_id"],
            f"✅ <b>Оплата получена — заказ #{oid}</b>\n\n"
            f"🔑 Ваш ключ:\n<code>{key}</code>\n\n"
            f"Активируйте его в панели Neverlose.",
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        log.warning("deliver to user failed: %s", e)
    await cb.message.edit_text(cb.message.text + "\n\n✅ <b>Подтверждено. Ключ выдан.</b>",
                               reply_markup=None, parse_mode=ParseMode.HTML)
    await cb.answer("Готово")

@router.callback_query(F.data.startswith("no:"))
async def cb_no(cb: CallbackQuery, bot: Bot):
    if not is_admin(cb.from_user.id):
        return await cb.answer("Только для админа", show_alert=True)
    oid = int(cb.data.split(":", 1)[1])
    db.reject(oid)
    o = db.get_order(oid)
    try:
        await bot.send_message(o["chat_id"], f"❌ Заказ #{oid} отклонён.")
    except Exception:
        pass
    await cb.message.edit_text(cb.message.text + "\n\n❌ <b>Отклонено.</b>",
                               reply_markup=None, parse_mode=ParseMode.HTML)
    await cb.answer()

@router.message(Command("addkeys"))
async def cmd_addkeys(m: Message):
    """Добавить ключи: /addkeys 30d KEY1 KEY2 ..."""
    if not is_admin(m.from_user.id):
        return
    parts = (m.text or "").split(maxsplit=2)
    if len(parts) < 3:
        return await m.answer("Формат: /addkeys <product_id> <ключ1 ключ2 ...>")
    pid, raw = parts[1], parts[2]
    if not db.product(pid):
        return await m.answer(f"Нет товара '{pid}'. /stock покажет id.")
    added, skipped = db.add_keys(pid, raw.replace(",", " ").split())
    await m.answer(f"➕ Добавлено {added}, пропущено дублей {skipped} (товар {pid}).")

@router.message(Command("stock"))
async def cmd_stock(m: Message):
    if not is_admin(m.from_user.id):
        return
    lines = [f"<b>Склад</b>"]
    for r in db.stock_counts():
        lines.append(f"• <code>{r['id']}</code> {r['duration']} — {eur(r['price'])}: "
                     f"<b>{r['free']}</b> св.")
    lines.append("\nДобавление: <code>/addkeys 30d NLE-.... NLE-....</code>")
    await m.answer("\n".join(lines), parse_mode=ParseMode.HTML)

@router.message(Command("orders"))
async def cmd_orders(m: Message):
    if not is_admin(m.from_user.id):
        return
    ps = db.pending_orders()
    if not ps:
        return await m.answer("Нет ожидающих заказов.")
    txt = ["<b>Заказы в ожидании</b>"]
    for o in ps:
        p = db.product(o["product_id"])
        txt.append(f"#{o['id']} · {p['duration']} · {eur(o['amount'])} · "
                   f"@{o['username'] or o['chat_id']} · {o['status']}")
    await m.answer("\n".join(txt), parse_mode=ParseMode.HTML)

@router.message(Command("help"))
async def cmd_help(m: Message):
    if not is_admin(m.from_user.id):
        return await m.answer("Магазин ключей. Начните с /start")
    await m.answer(
        "<b>Админ-команды</b>\n"
        "/stock — склад и id товаров\n"
        "/addkeys <id> KEY1 KEY2 — закинуть ключи\n"
        "/orders — ожидающие оплаты\n"
        "Кнопки ✔️/❌ в уведомлении — подтвердить/отклонить оплату.",
        parse_mode=ParseMode.HTML,
    )

# ---------- Запуск ----------
async def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not BOT_TOKEN:
        raise SystemExit("Не задан BOT_TOKEN. Скопируйте .env.example в .env и впишите токен.")
    if not ADMIN_IDS:
        log.warning("ADMIN_IDS пуст — подтверждения оплаты некому слать!")
    db.init()
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)

    # --- само-проверка связи с Telegram (не фатально: polling сам переподключится) ---
    try:
        me = await asyncio.wait_for(bot.get_me(), timeout=20)
        log.info("Связь с Telegram OK. Бот: @%s (id %s). Товаров: %d",
                 me.username, me.id, len(db.list_products()))
    except Exception as e:
        log.warning("Пока не достучался до api.telegram.org (%s). Пробую подключиться через polling — "
                    "убедись, что хостинг даёт доступ к Telegram.", type(e).__name__)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
