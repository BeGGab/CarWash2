import asyncio
import logging
from typing import Any, Dict, Optional

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command, Filter
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from backend.app.config import settings


API_BASE = f"{settings.backend_url}/api"
FRONTEND = settings.frontend_url.rstrip("/")

# Состояние «ожидаем ввод»: user_id -> "qr" | "complete" | {"action":"register"|"add_service","step":int,"data":dict,"carwash_id"?:int}
_pending_carwash_action: Dict[int, Any] = {}


class PendingCarwashFilter(Filter):
    """Срабатывает, когда пользователь в состоянии ожидания ввода."""

    async def __call__(self, message: Message) -> bool:
        return bool(message.from_user and message.from_user.id in _pending_carwash_action)


def is_system_admin(telegram_id: int) -> bool:
    return telegram_id in settings.system_admin_telegram_ids


async def get_user_role(telegram_id: int) -> Optional[str]:
    """Возвращает роль пользователя: 'user' | 'carwash_admin' | 'system_admin' или None если не найден."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{API_BASE}/auth/me", params={"telegram_id": telegram_id})
    if resp.status_code != 200:
        return None
    data = resp.json()
    return data.get("role")


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Меню обычного пользователя."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Отправить местоположение", request_location=True)],
            [
                KeyboardButton(
                    text="Открыть мини-приложение",
                    web_app=WebAppInfo(url=FRONTEND),
                )
            ],
            [KeyboardButton(text="Мои брони")],
        ],
        resize_keyboard=True,
    )


def carwash_admin_keyboard(telegram_id: Optional[int] = None) -> ReplyKeyboardMarkup:
    """Меню администратора автомойки: WebApp + пункты в боте."""
    webapp_url = f"{FRONTEND}/admin-carwash.html"
    if telegram_id:
        webapp_url += f"?telegram_id={telegram_id}"
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📱 Кабинет автомойки (WebApp)",
                    web_app=WebAppInfo(url=webapp_url),
                )
            ],
            [KeyboardButton(text="➕ Регистрация точки")],
            [KeyboardButton(text="📋 Добавить услугу")],
            [KeyboardButton(text="🏢 Мои автомойки"), KeyboardButton(text="📋 Брони моих моек")],
            [KeyboardButton(text="🔍 Поиск по QR"), KeyboardButton(text="✅ Завершить мойку")],
            [KeyboardButton(text="👤 Режим клиента")],
        ],
        resize_keyboard=True,
    )


def system_admin_keyboard(telegram_id: Optional[int] = None) -> ReplyKeyboardMarkup:
    """Меню системного администратора: WebApp + пункты в боте."""
    webapp_url = f"{FRONTEND}/system-admin.html"
    if telegram_id:
        webapp_url += f"?telegram_id={telegram_id}"
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📱 Панель системного админа (WebApp)",
                    web_app=WebAppInfo(url=webapp_url),
                )
            ],
            [KeyboardButton(text="📝 Мойки на модерации"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="👤 Режим клиента")],
        ],
        resize_keyboard=True,
    )


async def send_menu_by_role(message: Message, telegram_id: int, role: str) -> None:
    # Системный админ по переменной окружения — показываем его панель даже если в БД role=user
    if telegram_id in settings.system_admin_telegram_ids:
        await message.answer(
            "Вы вошли как <b>системный администратор</b>.\n\n"
            "Выберите действие: откройте панель в WebApp или используйте кнопки ниже.",
            reply_markup=system_admin_keyboard(telegram_id),
        )
        return
    if role == "carwash_admin":
        await message.answer(
            "Вы вошли как <b>администратор автомойки</b>.\n\n"
            "Выберите действие: откройте кабинет в WebApp или используйте кнопки ниже.",
            reply_markup=carwash_admin_keyboard(telegram_id),
        )
    elif role == "system_admin":
        await message.answer(
            "Вы вошли как <b>системный администратор</b>.\n\n"
            "Выберите действие: откройте панель в WebApp или используйте кнопки ниже.",
            reply_markup=system_admin_keyboard(telegram_id),
        )
    else:
        await message.answer(
            "Теперь вы можете искать автомойки, бронировать время и оплачивать предоплату.",
            reply_markup=main_menu_keyboard(),
        )


bot = Bot(
    token=settings.telegram_bot_token,
    default=DefaultBotProperties(parse_mode="HTML"),
)
dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    if not message.from_user:
        return
    telegram_id = message.from_user.id
    role = await get_user_role(telegram_id)
    if role is None:
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Поделиться телефоном", request_contact=True)],
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        await message.answer(
            "Привет! Я агрегатор автомоек города.\n\n"
            "Для начала работы поделитесь, пожалуйста, номером телефона.",
            reply_markup=kb,
        )
        return
    await send_menu_by_role(message, telegram_id, role)


@dp.message(F.contact)
async def handle_contact(message: Message) -> None:
    if not message.contact:
        return

    contact = message.contact
    telegram_id = contact.user_id or (message.from_user.id if message.from_user else None)
    if telegram_id is None:
        await message.answer("Не удалось определить ваш Telegram ID.")
        return

    full_name_parts = [
        contact.first_name or "",
        contact.last_name or "",
    ]
    full_name = " ".join(p for p in full_name_parts if p).strip()
    if not full_name and message.from_user:
        full_name = message.from_user.full_name

    payload: Dict[str, Any] = {
        "telegram_id": telegram_id,
        "phone": contact.phone_number,
        "full_name": full_name,
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(f"{API_BASE}/auth/register", json=payload)
    if resp.status_code != 200:
        await message.answer("Ошибка регистрации. Попробуйте позже.")
        return
    user = resp.json()
    role = user.get("role", "user")
    await message.answer("Спасибо! Телефон сохранён.")
    await send_menu_by_role(message, telegram_id, role)


@dp.message(F.location)
async def handle_location(message: Message) -> None:
    if not message.location:
        return

    lat = message.location.latitude
    lon = message.location.longitude

    params = {"lat": lat, "lon": lon, "radius_km": 10.0}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{API_BASE}/carwashes/nearby", params=params)
    if resp.status_code != 200:
        await message.answer("Ошибка при получении списка моек. Попробуйте позже.")
        return

    data = resp.json()
    if not data:
        await message.answer("Рядом не найдено автомоек в заданном радиусе.")
        return

    text_parts: list[str] = []
    for cw in data:
        slots = cw.get("nearest_slots") or []
        status_text: str
        if not slots:
            status_text = "Ближайшее окно: нет свободных слотов сегодня"
        else:
            first_slot = slots[0]
            status_text = f"Ближайшее окно: {first_slot['start_time']}"

        text_parts.append(
            f"<b>{cw['name']}</b>\n"
            f"{cw['address']}\n"
            f"{status_text}\n"
        )

    await message.answer(
        "Ближайшие автомойки:\n\n" + "\n".join(text_parts),
        reply_markup=main_menu_keyboard(),
    )


@dp.message(F.text == "🏢 Мои автомойки")
async def handle_my_carwashes(message: Message) -> None:
    if not message.from_user:
        return
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{API_BASE}/admin/carwashes/me",
            params={"telegram_id": message.from_user.id},
        )
    if resp.status_code == 403:
        await message.answer("Доступ только для администратора автомойки.")
        return
    if resp.status_code != 200:
        await message.answer("Не удалось загрузить список моек.")
        return
    data = resp.json()
    if not data:
        await message.answer(
            "У вас пока нет зарегистрированных автомоек. Добавьте точку через кабинет (WebApp).",
            reply_markup=carwash_admin_keyboard(message.from_user.id if message.from_user else None),
        )
        return
    lines = [f"• {cw['name']} — {cw['address']} (id: {cw['id']})" for cw in data]
    await message.answer(
        "Ваши автомойки:\n\n" + "\n".join(lines),
        reply_markup=carwash_admin_keyboard(message.from_user.id if message.from_user else None),
    )


@dp.message(F.text == "📋 Брони моих моек")
async def handle_carwash_bookings(message: Message) -> None:
    if not message.from_user:
        return
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{API_BASE}/admin/bookings",
            params={"telegram_id": message.from_user.id},
        )
    if resp.status_code == 403:
        await message.answer("Доступ только для администратора автомойки.")
        return
    if resp.status_code != 200:
        await message.answer("Не удалось загрузить брони.")
        return
    data = resp.json()
    if not data:
        await message.answer("Пока нет броней по вашим мойкам.", reply_markup=carwash_admin_keyboard(message.from_user.id if message.from_user else None))
        return
    lines = [f"#{b['id']} — {b['date']} {b['start_time']} — {b['status']}" for b in data[:15]]
    await message.answer(
        "Брони по вашим мойкам:\n\n" + "\n".join(lines),
        reply_markup=carwash_admin_keyboard(message.from_user.id if message.from_user else None),
    )


@dp.message(F.text == "➕ Регистрация точки")
async def handle_carwash_register_point(message: Message) -> None:
    if not message.from_user:
        return
    _pending_carwash_action[message.from_user.id] = {
        "action": "register",
        "step": 1,
        "data": {},
    }
    await message.answer(
        "Регистрация новой точки.\n\n<b>Шаг 1/6</b> Введите название автомойки:",
        reply_markup=carwash_admin_keyboard(message.from_user.id),
    )


@dp.message(F.text == "📋 Добавить услугу")
async def handle_carwash_add_service(message: Message) -> None:
    if not message.from_user:
        return
    uid = message.from_user.id
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{API_BASE}/admin/carwashes/me",
            params={"telegram_id": uid},
        )
    if resp.status_code != 200:
        await message.answer(
            "Не удалось загрузить список моек.",
            reply_markup=carwash_admin_keyboard(uid),
        )
        return
    carwashes = resp.json()
    if not carwashes:
        await message.answer(
            "Сначала зарегистрируйте автомойку (кнопка «➕ Регистрация точки»).",
            reply_markup=carwash_admin_keyboard(uid),
        )
        return
    if len(carwashes) == 1:
        _pending_carwash_action[uid] = {
            "action": "add_service",
            "step": 1,
            "data": {},
            "carwash_id": carwashes[0]["id"],
        }
        await message.answer(
            f"Добавление услуги для «{carwashes[0]['name']}».\n\n"
            "<b>Шаг 1/3</b> Введите название услуги:",
            reply_markup=carwash_admin_keyboard(uid),
        )
    else:
        lines = [f"{i+1}. {cw['name']}" for i, cw in enumerate(carwashes)]
        _pending_carwash_action[uid] = {
            "action": "add_service",
            "step": 0,
            "data": {},
            "carwashes": carwashes,
        }
        await message.answer(
            "Выберите мойку. Введите номер:\n\n" + "\n".join(lines),
            reply_markup=carwash_admin_keyboard(uid),
        )


@dp.message(F.text == "🔍 Поиск по QR")
async def handle_carwash_search_qr(message: Message) -> None:
    if not message.from_user:
        return
    _pending_carwash_action[message.from_user.id] = "qr"
    await message.answer(
        "Отправьте текст с QR-кода клиента (то, что отсканировано или введено вручную).",
        reply_markup=carwash_admin_keyboard(message.from_user.id if message.from_user else None),
    )


@dp.message(F.text == "✅ Завершить мойку")
async def handle_carwash_complete(message: Message) -> None:
    if not message.from_user:
        return
    _pending_carwash_action[message.from_user.id] = "complete"
    await message.answer(
        "Введите <b>номер брони</b> (число), которую нужно завершить.",
        reply_markup=carwash_admin_keyboard(message.from_user.id if message.from_user else None),
    )


def _kb(uid: int):
    return carwash_admin_keyboard(uid)


@dp.message(PendingCarwashFilter(), F.text)
async def handle_pending_carwash_input(message: Message) -> None:
    if not message.from_user:
        return
    uid = message.from_user.id
    state = _pending_carwash_action.get(uid)
    if not state:
        return
    text = (message.text or "").strip()
    kb = _kb(uid)

    # Простые действия: qr, complete
    if state == "qr":
        _pending_carwash_action.pop(uid, None)
        if not text:
            _pending_carwash_action[uid] = "qr"
            await message.answer("Отправьте текст с QR-кода одним сообщением.", reply_markup=kb)
            return
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{API_BASE}/admin/bookings/by-qr/{text}",
                params={"telegram_id": uid},
            )
        if resp.status_code == 404:
            await message.answer("Бронь с таким QR не найдена.", reply_markup=kb)
            return
        if resp.status_code == 403:
            await message.answer("Эта бронь не по вашей мойке.", reply_markup=kb)
            return
        if resp.status_code != 200:
            await message.answer("Ошибка запроса.", reply_markup=kb)
            return
        b = resp.json()
        await message.answer(
            f"Бронь #{b['id']}\nДата: {b['date']} {b['start_time']}\nСтатус: {b['status']}",
            reply_markup=kb,
        )
        return
    if state == "complete":
        _pending_carwash_action.pop(uid, None)
        try:
            booking_id = int(text)
        except ValueError:
            _pending_carwash_action[uid] = "complete"
            await message.answer("Введите номер брони числом, например: 5", reply_markup=kb)
            return
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{API_BASE}/admin/bookings/{booking_id}/complete",
                params={"telegram_id": uid},
            )
        if resp.status_code == 404:
            await message.answer("Бронь не найдена.", reply_markup=kb)
            return
        if resp.status_code == 403:
            await message.answer("Это не ваша бронь или доступ запрещён.", reply_markup=kb)
            return
        if resp.status_code != 200:
            await message.answer("Не удалось завершить мойку.", reply_markup=kb)
            return
        await message.answer("Мойка отмечена как завершённая.", reply_markup=kb)
        return

    # Диалоги: register, add_service
    if isinstance(state, dict):
        action = state.get("action")
        step = state.get("step", 0)
        data = state.get("data", {})

        if action == "register":
            if step == 1:
                data["name"] = text
                state["step"] = 2
                state["data"] = data
                await message.answer("<b>Шаг 2/6</b> Введите адрес:", reply_markup=kb)
            elif step == 2:
                data["address"] = text
                state["step"] = 3
                state["data"] = data
                await message.answer("<b>Шаг 3/6</b> Введите широту (например 55.75):", reply_markup=kb)
            elif step == 3:
                try:
                    data["lat"] = float(text.replace(",", "."))
                except ValueError:
                    await message.answer("Введите число, например 55.75", reply_markup=kb)
                    return
                state["step"] = 4
                state["data"] = data
                await message.answer("<b>Шаг 4/6</b> Введите долготу (например 37.62):", reply_markup=kb)
            elif step == 4:
                try:
                    data["lon"] = float(text.replace(",", "."))
                except ValueError:
                    await message.answer("Введите число, например 37.62", reply_markup=kb)
                    return
                state["step"] = 5
                state["data"] = data
                await message.answer("<b>Шаг 5/6</b> Время открытия (ЧЧ:ММ, например 09:00):", reply_markup=kb)
            elif step == 5:
                data["open_time"] = text if ":" in text else f"{text}:00"
                state["step"] = 6
                state["data"] = data
                await message.answer("<b>Шаг 6/6</b> Время закрытия (ЧЧ:ММ, например 21:00):", reply_markup=kb)
            elif step == 6:
                data["close_time"] = text if ":" in text else f"{text}:00"
                _pending_carwash_action.pop(uid, None)
                body = {
                    "name": data["name"],
                    "address": data["address"],
                    "lat": data["lat"],
                    "lon": data["lon"],
                    "description": "",
                    "photos": [],
                    "wash_type": "contact",
                    "additional_services": [],
                    "open_time": data["open_time"],
                    "close_time": data["close_time"],
                    "slot_duration_minutes": 30,
                }
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(
                        f"{API_BASE}/admin/carwashes",
                        params={"telegram_id": uid},
                        json=body,
                    )
                if resp.status_code != 200:
                    await message.answer("Ошибка создания. Проверьте данные и попробуйте снова.", reply_markup=kb)
                    return
                cw = resp.json()
                await message.answer(
                    f"Автомойка «{cw['name']}» зарегистрирована. Ожидает модерации.",
                    reply_markup=kb,
                )
            return

        if action == "add_service":
            if step == 0:
                try:
                    idx = int(text)
                    if 1 <= idx <= len(state.get("carwashes", [])):
                        cw = state["carwashes"][idx - 1]
                        state["carwash_id"] = cw["id"]
                        state["step"] = 1
                        state["data"] = {}
                        del state["carwashes"]
                        await message.answer(
                            f"Добавление услуги для «{cw['name']}».\n\n"
                            "<b>Шаг 1/3</b> Введите название услуги:",
                            reply_markup=kb,
                        )
                    else:
                        await message.answer("Введите номер из списка.", reply_markup=kb)
                except ValueError:
                    await message.answer("Введите номер числом.", reply_markup=kb)
                return
            if step == 1:
                data["name"] = text
                state["step"] = 2
                state["data"] = data
                await message.answer("<b>Шаг 2/3</b> Введите цену (₽):", reply_markup=kb)
            elif step == 2:
                try:
                    data["price"] = float(text.replace(",", "."))
                except ValueError:
                    await message.answer("Введите число, например 500", reply_markup=kb)
                    return
                state["step"] = 3
                state["data"] = data
                await message.answer("<b>Шаг 3/3</b> Длительность в минутах (например 60):", reply_markup=kb)
            elif step == 3:
                try:
                    data["duration_minutes"] = int(text)
                except ValueError:
                    await message.answer("Введите число минут.", reply_markup=kb)
                    return
                _pending_carwash_action.pop(uid, None)
                body = {
                    "carwash_id": state["carwash_id"],
                    "name": data["name"],
                    "description": "",
                    "price": data["price"],
                    "duration_minutes": data["duration_minutes"],
                }
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(
                        f"{API_BASE}/admin/services",
                        params={"telegram_id": uid},
                        json=body,
                    )
                if resp.status_code != 200:
                    await message.answer("Ошибка добавления услуги.", reply_markup=kb)
                    return
                await message.answer(f"Услуга «{data['name']}» добавлена.", reply_markup=kb)


@dp.message(F.text == "📝 Мойки на модерации")
async def handle_pending_carwashes(message: Message) -> None:
    if not message.from_user or not is_system_admin(message.from_user.id):
        await message.answer("Доступ только для системного администратора.")
        return
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{API_BASE}/system/carwashes/pending",
            params={"telegram_id": message.from_user.id},
        )
    if resp.status_code != 200:
        await message.answer("Не удалось загрузить список.")
        return
    data = resp.json()
    if not data:
        await message.answer("Нет моек в ожидании модерации.", reply_markup=system_admin_keyboard(message.from_user.id if message.from_user else None))
        return
    lines = [f"#{cw['id']} — {cw['name']}, {cw['address']}" for cw in data]
    await message.answer(
        "Мойки на модерации:\n\n" + "\n".join(lines) + "\n\nПодтверждение: в WebApp или /add_carwash_admin для назначения админов.",
        reply_markup=system_admin_keyboard(message.from_user.id if message.from_user else None),
    )


@dp.message(F.text == "📊 Статистика")
async def handle_statistics(message: Message) -> None:
    if not message.from_user or not is_system_admin(message.from_user.id):
        await message.answer("Доступ только для системного администратора.")
        return
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{API_BASE}/system/statistics/overview",
            params={"telegram_id": message.from_user.id},
        )
    if resp.status_code != 200:
        await message.answer("Не удалось загрузить статистику.")
        return
    s = resp.json()
    text = (
        f"<b>Статистика</b>\n\n"
        f"Всего моек: {s.get('total_carwashes', 0)}\n"
        f"Подтверждённых: {s.get('total_approved_carwashes', 0)}\n"
        f"Всего броней: {s.get('total_bookings', 0)}\n"
        f"Сумма предоплат: {s.get('total_payments_sum', 0):.2f} ₽\n"
        f"Комиссия ({s.get('commission_percent', 0)}%): {s.get('total_commission', 0):.2f} ₽"
    )
    await message.answer(text, reply_markup=system_admin_keyboard(message.from_user.id if message.from_user else None))


@dp.message(F.text == "👤 Режим клиента")
async def handle_switch_to_client(message: Message) -> None:
    await message.answer(
        "Переключено на режим клиента: ищите мойки, бронируйте и смотрите свои брони.",
        reply_markup=main_menu_keyboard(),
    )


@dp.message(Command("add_carwash_admin"))
async def cmd_add_carwash_admin(message: Message) -> None:
    if not message.from_user:
        return
    if not is_system_admin(message.from_user.id):
        await message.answer("Доступ только для системного администратора.")
        return
    text = (message.text or "").strip()
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "Использование: /add_carwash_admin <telegram_id>\n"
            "Пример: /add_carwash_admin 123456789"
        )
        return
    try:
        target_telegram_id = int(parts[1])
    except ValueError:
        await message.answer("Укажите числовой telegram_id пользователя.")
        return
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{API_BASE}/system/users/assign-carwash-admin",
            params={"telegram_id": message.from_user.id},
            json={"telegram_id": target_telegram_id},
        )
    if resp.status_code == 200:
        await message.answer(
            f"Пользователь {target_telegram_id} назначен администратором автомойки. "
            "Он может добавить точку в кабинете админа."
        )
    elif resp.status_code == 404:
        await message.answer(
            "Пользователь с таким telegram_id не найден. "
            "Он должен сначала запустить бота и поделиться телефоном."
        )
    else:
        await message.answer("Ошибка при назначении. Попробуйте позже.")


@dp.message(F.text == "Мои брони")
async def handle_my_bookings(message: Message) -> None:
    if not message.from_user:
        return

    telegram_id = message.from_user.id
    params = {"telegram_id": telegram_id}

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{API_BASE}/bookings/me", params=params)

    if resp.status_code != 200:
        await message.answer("Не удалось загрузить ваши брони.")
        return

    bookings = resp.json()
    if not bookings:
        await message.answer("У вас пока нет броней.", reply_markup=main_menu_keyboard())
        return

    lines: list[str] = []
    for b in bookings[:10]:
        status = b["status"]
        lines.append(
            f"Бронь #{b['id']} на {b['date']} {b['start_time']} — статус: {status}"
        )

    await message.answer(
        "Ваши брони:\n" + "\n".join(lines),
        reply_markup=main_menu_keyboard(),
    )


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    if not settings.system_admin_telegram_ids:
        logging.warning(
            "SYSTEM_ADMIN_TELEGRAM_IDS пуст в .env — системные администраторы не заданы. "
            "Добавьте ID через запятую для доступа к /add_carwash_admin и системному WebApp."
        )
    else:
        logging.info("Системные администраторы: %s", sorted(settings.system_admin_telegram_ids))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

