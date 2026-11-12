import html
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    Update
)

# ================= SOZLAMALAR =================
BOT_TOKEN = "9117090922:AAHBdLtCq7bGsSbcnNoiFT_xCQZCh4xetcc"
ADMIN_IDS = [6258110646, 7645769320]

DOCTOR_NAME = "Doktor Surayyo Vahobjonovna"
CLINIC_ADDRESS = "Toshkent shahri, Doktor Surayyo Vahobjonovna klinikasi"
WORK_HOURS = "09:00 dan 18:00 gacha"
PHONE_NUMBER = "+998952775354"
DOCTOR_TELEGRAM = "https://t.me/Sr7431"
TELEGRAM_CHANNEL = "https://t.me/ginekologplastikx"
YOUTUBE_CHANNEL = "https://youtube.com/@ginekologestetst"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ================= TEZKOR XOTIRA (VERCEL UCHUN) =================
USERS_DB = {}          # user_id -> {"name": str, "warnings": int, "banned": bool}
APPOINTMENTS_DB = []   # list of dicts
RATINGS_DB = []        # list of ints
WEB_REPLIES = defaultdict(list)  # patient_id -> [text, ...]
SCHEDULE_SLOTS = []    # list of str
RATE_LIMIT = defaultdict(list)

def is_rate_limited(key: str) -> bool:
    now = time.time()
    RATE_LIMIT[key] = [t for t in RATE_LIMIT[key] if now - t < 60]
    if len(RATE_LIMIT[key]) >= 12:
        return True
    RATE_LIMIT[key].append(now)
    return False

def clean_text(raw: str) -> str:
    if not raw:
        return ""
    return html.escape(raw.strip()[:800])

def is_banned(user_id: int) -> bool:
    if user_id in ADMIN_IDS:
        return False
    return USERS_DB.get(user_id, {}).get("banned", False)

# ================= XIZMATLAR VA BILIMLAR BAZASI =================
SERVICES = {
    "konsultatsiya": ("🩺 Birlamchi konsultatsiya", "30 daq"),
    "labioplastika": ("✨ Labioplastika (Kichik jinsiy lablar plastikasi)", "30-45 daq"),
    "vaginoplastika": ("✨ Vaginoplastika (Vagina devorlarini toraytirish)", "60-90 daq"),
    "klitoroplastika": ("✨ Klitoroplastika", "30-40 daq"),
    "oqartirish": ("🌸 Intim zona oqartirish", "20-30 daq"),
    "prp": ("💉 Intim yoshartirish va Plazmoterapiya (PRP)", "30 daq"),
    "eroziya": ("🔬 Bachadon bo'yni eroziyasini lazerda davolash", "15-20 daq"),
    "polip": ("🔬 Bachadon bo'yni poliplarini olish", "15-30 daq"),
    "spiral": ("🛡 Spiral (Implantsperal) o'rnatish", "5-10 daq"),
    "sistit": ("⚡ Sistitni lazer SO2 da davolash", "20 daq"),
    "miyoma": ("🏥 Bachadon miyomasini davolash", "30 daq"),
    "razriv": ("🪡 Tug'ruqdan keyingi yirtilishlarni tiklash (Razriv)", "45-60 daq"),
}

KNOWLEDGE_BASE = [
    {"keywords": ["estetik ginekologiya", "lazer so2", "co2", "so2"], "answer": "🌸 <b>Estetik ginekologiya va Lazer SO2:</b>\nIntim zonadagi tug'ma va tug'ruqdan keyingi o'zgarishlarni jarrohlik hamda lazer SO2 yordamida og'riqsiz tiklash muolajasi."},
    {"keywords": ["labioplastika", "labio", "kichik jinsiy lab"], "answer": "✨ <b>Labioplastika:</b>\n• Vaqti: 30–45 daqiqa (mahalliy og'riqsizlantirish).\n• Bitish: 3–4 hafta (shu davrda jinsiy aloqa taqiqlanadi)."},
    {"keywords": ["vaginoplastika", "vagina", "toraytirish"], "answer": "✨ <b>Vaginoplastika:</b>\n• Vaqti: 1–1.5 soat.\n• Tiklanish: 6–8 hafta (2 oy jinsiy aloqa va og'ir yuk taqiqlanadi)."},
    {"keywords": ["klitor", "klitoroplastika"], "answer": "✨ <b>Klitoroplastika:</b>\n• Vaqti: 30–40 daqiqa.\n• Tiklanish: 3 hafta."},
    {"keywords": ["oqartirish", "pigment", "qorayish"], "answer": "🌸 <b>Intim zona oqartirish:</b>\n• Vaqti: 20–30 daqiqa (3–4 seans).\n• Tiklanish: 5–7 kun."},
    {"keywords": ["prp", "plazma", "plazmoterapiya", "yoshartirish", "qurish"], "answer": "💉 <b>Plazmoterapiya (PRP):</b>\n• Vaqti: 30 daqiqa.\n• Tiklanish: 1–2 kun."},
    {"keywords": ["eroziya"], "answer": "🔬 <b>Bachadon bo'yni eroziyasi:</b>\n• Vaqti: 15–20 daqiqa (lazer/radioto'lqin).\n• Bitish: 3–4 hafta."},
    {"keywords": ["polip"], "answer": "🔬 <b>Poliplarni olish:</b>\n• Vaqti: 15–30 daqiqa.\n• Tiklanish: 2 hafta."},
    {"keywords": ["spiral", "implantsperal"], "answer": "🛡 <b>Spiral o'rnatish:</b>\n• Vaqti: 5–10 daqiqa.\n• Moslashish: 1–2 kun."},
    {"keywords": ["sistit", "siydik"], "answer": "⚡ <b>Sistitni lazer SO2 da davolash:</b>\nOg'riqsiz va qonsiz muolaja. Tiklanish: 5–7 kun."},
    {"keywords": ["miyoma"], "answer": "🏥 <b>Bachadon miyomasi:</b>\nDori-darmon yoki kichik invaziv usulda davolanadi. Tiklanish: 3–4 hafta."},
    {"keywords": ["razriv", "yirtilish"], "answer": "🪡 <b>Tug'ruqdan keyingi yirtilishlarni tiklash (Razriv):</b>\n• Vaqti: 45–60 daqiqa.\n• Bitish: 4–6 hafta."},
    {"keywords": ["narx", "qancha", "necha pul", "to'lov"], "answer": f"ℹ️ Muolajalar narxi ko'rik natijasiga qarab belgilanadi.\n📞 {PHONE_NUMBER} | ✉️ @Sr7431"},
]

GREETINGS = ["assalomu alaykum", "assalom", "salom", "qalaysiz", "yaxshimisiz"]

class BookingState(StatesGroup):
    choosing_service = State()
    choosing_type = State()
    choosing_date = State()
    choosing_time = State()
    entering_phone = State()

class AdminReplyState(StatesGroup):
    waiting_for_reply = State()

class ScheduleState(StatesGroup):
    waiting_for_schedule = State()

class BroadcastState(StatesGroup):
    waiting_for_message = State()

# ================= TUGMALAR =================
def patient_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Qabulga yozilish"), KeyboardButton(text="🗓 Qabul kunlari")],
            [KeyboardButton(text="🩺 Tibbiy xizmatlar"), KeyboardButton(text="💬 Surayyo Vahobjonovnaga savol")],
            [KeyboardButton(text="📞 Aloqa va manzil"), KeyboardButton(text="⭐ Xizmatni baholash")]
        ],
        resize_keyboard=True,
        is_persistent=True
    )

def admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Qabul kunlarini kiritish"), KeyboardButton(text="🗑 Qabul kunlarini tozalash")],
            [KeyboardButton(text="📢 Barchaga Push (Broadcast)"), KeyboardButton(text="🧹 Chatni tozalash (Delete)")],
            [KeyboardButton(text="📋 Bugungi qabullar"), KeyboardButton(text="📊 Statistika")]
        ],
        resize_keyboard=True,
        is_persistent=True
    )

def get_menu(user_id: int):
    return admin_menu() if user_id in ADMIN_IDS else patient_menu()

def admin_question_buttons(target_type: str, target_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✍️ Javob qaytarish (Push)", callback_data=f"pushreply_{target_type}_{target_id}"),
            InlineKeyboardButton(text="🗑 Delete", callback_data="del_msg")
        ]
    ])

def consult_action_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Qabulga yozilish", callback_data="start_booking")],
        [InlineKeyboardButton(text="🗓 Qabul kunlarini ko'rish", callback_data="view_schedule_cb")],
        [InlineKeyboardButton(text="👩‍⚕️ Shifokor lichkasi (@Sr7431)", url=DOCTOR_TELEGRAM)]
    ])

def rating_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⭐ 1", callback_data="rate_1"),
        InlineKeyboardButton(text="⭐ 2", callback_data="rate_2"),
        InlineKeyboardButton(text="⭐ 3", callback_data="rate_3"),
        InlineKeyboardButton(text="⭐ 4", callback_data="rate_4"),
        InlineKeyboardButton(text="⭐ 5", callback_data="rate_5"),
    ]])

# ================= 18+ MEDIA FILTRI =================
@dp.message(F.photo | F.video | F.animation | F.document | F.video_note | F.sticker | F.voice | F.audio)
async def block_media(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    if uid in ADMIN_IDS and await state.get_state() == BroadcastState.waiting_for_message.state:
        await send_broadcast(message, state)
        return
    try:
        await message.delete()
    except Exception:
        pass
    user = USERS_DB.setdefault(uid, {"name": clean_text(message.from_user.full_name), "warnings": 0, "banned": False})
    user["warnings"] += 1
    if user["warnings"] >= 3:
        user["banned"] = True
        await message.answer("🚫 Xavfsizlik qoidalarini 3 marta buzganingiz sababli bloklandingiz.")
    else:
        await message.answer(
            f"⚠️ <b>Xavfsizlik qoidasi ({user['warnings']}/3):</b>\nRasm, video yoki ovoz yuborish taqiqlangan! Faqat matn yuboring.",
            reply_markup=get_menu(uid),
            parse_mode="HTML"
        )

# ================= START =================
@dp.message(CommandStart())
@dp.message(Command("menu"))
async def cmd_start(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    if is_banned(uid):
        return
    await state.clear()
    USERS_DB.setdefault(uid, {"name": clean_text(message.from_user.full_name), "warnings": 0, "banned": False})

    await message.answer(
        f"Assalomu alaykum, <b>{clean_text(message.from_user.first_name)}</b>! 🌸\n\n"
        f"Estetik ginekolog vrach <b>Surayyo Vahobjonovna</b>ning rasmiy 24/7 botiga xush kelibsiz.\n\n"
        f"📞 <b>Telefon:</b> {PHONE_NUMBER}\n"
        f"✉️ <b>Telegram lichka:</b> @Sr7431\n\n"
        f"👇 Pastdagi tugmalardan foydalaning:",
        reply_markup=get_menu(uid),
        parse_mode="HTML"
    )
    if uid not in ADMIN_IDS:
        await message.answer("Tezkor amallar:", reply_markup=consult_action_keyboard())

# ================= ADMIN: QABUL KUNLARINI KIRITISH =================
@dp.message(F.text == "📅 Qabul kunlarini kiritish")
async def ask_schedule(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    cancel_kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True)
    await message.answer(
        "📅 <b>Yangi qabul kunlari va vaqtlarini yozing:</b>\n\n"
        "<i>Namuna:</i> <code>Dushanba, Chorshanba, Juma — 10:00 dan 16:00 gacha</code>",
        reply_markup=cancel_kb,
        parse_mode="HTML"
    )
    await state.set_state(ScheduleState.waiting_for_schedule)

@dp.message(ScheduleState.waiting_for_schedule)
async def save_schedule(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Asosiy menyu:", reply_markup=admin_menu())
        return

    slot_text = clean_text(message.text or "")
    if not slot_text:
        return
    SCHEDULE_SLOTS.insert(0, slot_text)

    book_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Qabulga yozilish", callback_data="start_booking")],
        [InlineKeyboardButton(text="👩‍⚕️ Shifokor lichkasi (@Sr7431)", url=DOCTOR_TELEGRAM)]
    ])
    announce_msg = (
        f"🗓 <b>YANGI QABUL KUNLARI E'LON QILINDI!</b>\n\n"
        f"👩‍⚕️ <b>{DOCTOR_NAME}</b>\n"
        f"📅 <b>Qabul kunlari:</b> {slot_text}\n"
        f"📍 <b>Manzil:</b> {CLINIC_ADDRESS}\n"
        f"📞 <b>Telefon:</b> {PHONE_NUMBER}"
    )
    sent = 0
    for uid, udata in USERS_DB.items():
        if uid not in ADMIN_IDS and not udata.get("banned"):
            try:
                await bot.send_message(uid, announce_msg, reply_markup=book_kb, parse_mode="HTML")
                sent += 1
            except Exception:
                pass

    await message.answer(
        f"✅ <b>Qabul kunlari saqlandi!</b>\n🌐 Saytingizda ko'rinadi.\n📲 {sent} ta bemorga yuborildi.",
        reply_markup=admin_menu(),
        parse_mode="HTML"
    )
    await state.clear()

@dp.message(F.text == "🗑 Qabul kunlarini tozalash")
async def clear_schedule(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    SCHEDULE_SLOTS.clear()
    await message.answer("🗑 Qabul kunlari tozalandi.", reply_markup=admin_menu())

# ================= BEMOR BO'LIMLARI =================
@dp.message(F.text == "🗓 Qabul kunlari")
@dp.callback_query(F.data == "view_schedule_cb")
async def view_schedule(event: types.Message | types.CallbackQuery):
    msg = event.message if isinstance(event, types.CallbackQuery) else event
    if isinstance(event, types.CallbackQuery):
        await event.answer()
    if not SCHEDULE_SLOTS:
        text = f"🗓 <b>{DOCTOR_NAME} — Qabul vaqti:</b>\n🕘 {WORK_HOURS}\n📍 {CLINIC_ADDRESS}\n📞 {PHONE_NUMBER}"
    else:
        text = f"🗓 <b>{DOCTOR_NAME} — Ochiq qabul kunlari:</b>\n\n" + "\n".join([f"✅ <b>{s}</b>" for s in SCHEDULE_SLOTS[:5]])
    await msg.answer(text, reply_markup=consult_action_keyboard(), parse_mode="HTML")

@dp.message(F.text == "🩺 Tibbiy xizmatlar")
async def show_services(message: types.Message, state: FSMContext):
    await state.clear()
    text = f"<b>🩺 {DOCTOR_NAME} — Tibbiy xizmatlarimiz:</b>\n\n"
    for name, dur in SERVICES.values():
        text += f"• <b>{name}</b> — {dur}\n"
    await message.answer(text, reply_markup=consult_action_keyboard(), parse_mode="HTML")

@dp.message(F.text == "📞 Aloqa va manzil")
async def show_location(message: types.Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👩‍⚕️ Shifokor Telegram lichkasi (@Sr7431)", url=DOCTOR_TELEGRAM)],
        [
            InlineKeyboardButton(text="✈️ Telegram kanal", url=TELEGRAM_CHANNEL),
            InlineKeyboardButton(text="▶️ YouTube kanal", url=YOUTUBE_CHANNEL)
        ]
    ])
    await message.answer(
        f"🏥 <b>{DOCTOR_NAME}</b>\n📞 {PHONE_NUMBER}\n✉️ @Sr7431\n📍 {CLINIC_ADDRESS}\n🕘 {WORK_HOURS}",
        reply_markup=kb,
        parse_mode="HTML"
    )

@dp.message(F.text == "⭐ Xizmatni baholash")
async def manual_rating(message: types.Message):
    await message.answer(f"<b>{DOCTOR_NAME}</b> xizmatini baholang:", reply_markup=rating_keyboard(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("rate_"))
async def process_rating(callback: types.CallbackQuery):
    await callback.answer()
    stars = int(callback.data.split("_")[1])
    RATINGS_DB.append(stars)
    await callback.message.edit_text(f"⭐ {stars} — Fikringiz uchun katta rahmat! 🙏")

@dp.message(F.text == "💬 Surayyo Vahobjonovnaga savol")
async def ask_doc(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👩‍⚕️ Shaxsiy Telegram (@Sr7431)", url=DOCTOR_TELEGRAM)]])
    await message.answer(f"✍️ Savolingizni matn shaklida yozing — darhol javob olasiz yoki <b>{DOCTOR_NAME}</b>ga yuboriladi.", reply_markup=kb, parse_mode="HTML")

# ================= QABULGA YOZILISH =================
@dp.message(F.text == "📅 Qabulga yozilish")
@dp.callback_query(F.data == "start_booking")
async def start_booking(event: types.Message | types.CallbackQuery, state: FSMContext):
    if is_banned(event.from_user.id):
        return
    await state.clear()
    msg = event.message if isinstance(event, types.CallbackQuery) else event
    if isinstance(event, types.CallbackQuery):
        await event.answer()
    buttons = [[InlineKeyboardButton(text=name, callback_data=f"srv_{k}")] for k, (name, _) in SERVICES.items()]
    await msg.answer("Qaysi xizmat turiga yozilmoqchisiz?", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await state.set_state(BookingState.choosing_service)

@dp.callback_query(F.data.startswith("srv_"))
async def process_srv(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    k = callback.data.split("_", 1)[1]
    srv_name, _ = SERVICES[k]
    await state.update_data(service=srv_name)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💻 Online", callback_data="type_Online"),
        InlineKeyboardButton(text="🏥 Offline", callback_data="type_Offline")
    ]])
    await callback.message.edit_text(f"Xizmat: <b>{srv_name}</b>\nQabul turini tanlang:", reply_markup=kb, parse_mode="HTML")
    await state.set_state(BookingState.choosing_type)

@dp.callback_query(F.data.startswith("type_"))
async def process_type(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    vtype = callback.data.split("_")[1]
    await state.update_data(visit_type=vtype)
    btns = []
    for i, s in enumerate(SCHEDULE_SLOTS[:3]):
        btns.append([InlineKeyboardButton(text=f"🗓 {s[:35]}", callback_data=f"cdate_{i}")])
    tom = (datetime.now() + timedelta(days=1)).strftime("%d.%m.%Y")
    btns.append([InlineKeyboardButton(text=f"Ertaga ({tom})", callback_data=f"date_{tom}")])
    await callback.message.edit_text("Qabul kunini tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    await state.set_state(BookingState.choosing_date)

@dp.callback_query(F.data.startswith("cdate_"))
async def process_cdate(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    idx = int(callback.data.split("_")[1])
    day = SCHEDULE_SLOTS[idx] if idx < len(SCHEDULE_SLOTS) else "Belgilangan kun"
    await state.update_data(visit_date=day)
    times = ["10:00", "11:30", "12:30", "14:00", "15:00", "16:30"]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t, callback_data=f"time_{t}") for t in times[:3]],
        [InlineKeyboardButton(text=t, callback_data=f"time_{t}") for t in times[3:]]
    ])
    await callback.message.edit_text("Soatni tanlang:", reply_markup=kb)
    await state.set_state(BookingState.choosing_time)

@dp.callback_query(F.data.startswith("date_"))
async def process_date(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    day = callback.data.split("_")[1]
    await state.update_data(visit_date=day)
    times = ["10:00", "11:30", "12:30", "14:00", "15:00", "16:30"]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t, callback_data=f"time_{t}") for t in times[:3]],
        [InlineKeyboardButton(text=t, callback_data=f"time_{t}") for t in times[3:]]
    ])
    await callback.message.edit_text("Soatni tanlang:", reply_markup=kb)
    await state.set_state(BookingState.choosing_time)

@dp.callback_query(F.data.startswith("time_"))
async def process_time(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    tm = callback.data.split("_")[1]
    await state.update_data(visit_time=tm)
    pkb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]], resize_keyboard=True, one_time_keyboard=True)
    await callback.message.delete()
    await callback.message.answer("Telefon raqamingizni yuboring:", reply_markup=pkb)
    await state.set_state(BookingState.entering_phone)

@dp.message(BookingState.entering_phone)
async def finish_booking(message: types.Message, state: FSMContext):
    phone = clean_text(message.contact.phone_number if message.contact else (message.text or ""))[:25]
    data = await state.get_data()
    rec = {
        "name": clean_text(message.from_user.full_name),
        "service": data.get("service", "Konsultatsiya"),
        "type": data.get("visit_type", "Offline"),
        "date": data.get("visit_date", "Ertaga"),
        "time": data.get("visit_time", "10:00"),
        "phone": phone
    }
    APPOINTMENTS_DB.insert(0, rec)
    await message.answer(
        f"✅ <b>Qabulga yozildingiz!</b>\n🩺 {rec['service']}\n📅 {rec['date']}, {rec['time']} ({rec['type']})\n📞 {PHONE_NUMBER}",
        reply_markup=get_menu(message.from_user.id),
        parse_mode="HTML"
    )
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(
                aid,
                f"🔔 <b>YANGI QABUL!</b>\n👤 {rec['name']}\n📞 {phone}\n🩺 {rec['service']}\n📅 {rec['date']} | {rec['time']} ({rec['type']})",
                reply_markup=admin_question_buttons("tg", str(message.from_user.id)),
                parse_mode="HTML"
            )
        except Exception:
            pass
    await state.clear()

# ================= ADMIN PUSH JAVOB VA DELETE =================
@dp.callback_query(F.data == "del_msg")
async def del_msg(callback: types.CallbackQuery):
    await callback.answer("O'chirildi 🗑")
    try:
        await callback.message.delete()
    except Exception:
        pass

@dp.callback_query(F.data.startswith("pushreply_"))
async def start_push_reply(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return
    await callback.answer()
    _, t_type, t_id = callback.data.split("_", 2)
    await state.update_data(target_type=t_type, target_id=t_id)
    await state.set_state(AdminReplyState.waiting_for_reply)
    ckb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True)
    await callback.message.answer(f"✍️ <b>({t_id})</b> bemorga javob matnini yozing:", reply_markup=ckb, parse_mode="HTML")

@dp.message(AdminReplyState.waiting_for_reply)
async def send_push_reply(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Asosiy menyu:", reply_markup=admin_menu())
        return
    data = await state.get_data()
    t_type, t_id = data["target_type"], data["target_id"]
    txt = clean_text(message.text or "")
    if t_type == "web":
        WEB_REPLIES[t_id].append(txt)
        await message.answer(f"✅ Javob saytdagi bemorga ({t_id}) Push qilindi!", reply_markup=admin_menu())
    else:
        await bot.send_message(int(t_id), f"👩‍⚕️ <b>{DOCTOR_NAME} javobi:</b>\n\n{txt}", reply_markup=patient_menu(), parse_mode="HTML")
        await message.answer("✅ Javob bemorga yuborildi!", reply_markup=admin_menu())
    await state.clear()

@dp.message(F.text == "🧹 Chatni tozalash (Delete)")
async def clear_chat(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    for mid in range(message.message_id, max(1, message.message_id - 30), -1):
        try:
            await bot.delete_message(message.chat.id, mid)
        except Exception:
            pass
    await bot.send_message(message.chat.id, "🧹 Chat tozalandi.", reply_markup=admin_menu())

@dp.message(F.text == "📊 Statistika")
async def stats(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    avg = f"{sum(RATINGS_DB)/len(RATINGS_DB):.1f}/5.0" if RATINGS_DB else "Yo'q"
    await message.answer(
        f"📊 <b>Statistika:</b>\n👥 Mijozlar: {len(USERS_DB)}\n📅 Qabullar: {len(APPOINTMENTS_DB)}\n⭐ Baho: {avg}",
        parse_mode="HTML"
    )

@dp.message(F.text == "📋 Bugungi qabullar")
async def list_appts(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    if not APPOINTMENTS_DB:
        await message.answer("Hozircha qabullar yo'q.")
        return
    txt = "📋 <b>Oxirgi qabullar:</b>\n\n" + "\n".join([f"• {a['date']} {a['time']} ({a['type']}) — {a['service']} | {a['phone']}" for a in APPOINTMENTS_DB[:15]])
    await message.answer(txt, parse_mode="HTML")

@dp.message(F.text == "📢 Barchaga Push (Broadcast)")
async def bcast_start(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    ckb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True)
    await message.answer("📢 Barcha bemorlarga yuboriladigan xabarni yozing:", reply_markup=ckb)
    await state.set_state(BroadcastState.waiting_for_message)

@dp.message(BroadcastState.waiting_for_message)
async def send_broadcast(message: types.Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Asosiy menyu:", reply_markup=admin_menu())
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Qabulga yozilish", callback_data="start_booking")]])
    sent = 0
    for uid in USERS_DB:
        try:
            await message.copy_to(uid, reply_markup=kb)
            sent += 1
        except Exception:
            pass
    await message.answer(f"✅ {sent} ta bemorga yuborildi!", reply_markup=admin_menu())
    await state.clear()

# ================= UMUMIY SUHBAT VA REPLY =================
@dp.message()
async def all_messages(message: types.Message):
    uid = message.from_user.id
    if is_banned(uid):
        return
    USERS_DB.setdefault(uid, {"name": clean_text(message.from_user.full_name), "warnings": 0, "banned": False})

    if uid in ADMIN_IDS:
        if message.reply_to_message:
            orig = message.reply_to_message.text or ""
            m_web = re.search(r"ID-\d{6}", orig)
            if m_web:
                WEB_REPLIES[m_web.group(0)].append(clean_text(message.text or ""))
                await message.answer(f"✅ Javob saytga ({m_web.group(0)}) yuborildi!", reply_markup=admin_menu())
                return
            m_tg = re.search(r"TG_USER_ID:\s*(\d+)", orig)
            if m_tg:
                await bot.send_message(int(m_tg.group(1)), f"👩‍⚕️ <b>{DOCTOR_NAME} javobi:</b>\n\n{clean_text(message.text or '')}", reply_markup=patient_menu(), parse_mode="HTML")
                await message.answer("✅ Javob bemorga ketdi!", reply_markup=admin_menu())
                return
        await message.answer("👇 Pastdagi tugmalardan foydalaning:", reply_markup=admin_menu())
        return

    if message.text:
        if is_rate_limited(f"tg_{uid}"):
            return
        txt = clean_text(message.text)
        low = txt.lower()
        for item in KNOWLEDGE_BASE:
            if any(k in low for k in item["keywords"]):
                await message.answer(item["answer"], reply_markup=consult_action_keyboard(), parse_mode="HTML")
                return
        if any(g in low for g in GREETINGS) and len(low.split()) <= 5:
            await message.answer(f"Va alaykum assalom, <b>{clean_text(message.from_user.first_name)}</b>! 😊 Quyidagi tugmalardan foydalaning:", reply_markup=patient_menu(), parse_mode="HTML")
            return
        for aid in ADMIN_IDS:
            try:
                await bot.send_message(
                    aid,
                    f"🩺 <b>YANGI SAVOL</b>\n👤 {clean_text(message.from_user.full_name)}\n🆔 TG_USER_ID: {uid}\n💬 {txt}",
                    reply_markup=admin_question_buttons("tg", str(uid)),
                    parse_mode="HTML"
                )
            except Exception:
                pass
        await message.answer(f"✅ Savolingiz <b>{DOCTOR_NAME}</b>ga yuborildi!", reply_markup=patient_menu(), parse_mode="HTML")

# ================= VERCEL WEBHOOK VA SAYT ENDPOINTLARI =================
@app.post("/api/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.model_validate(data, context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"ok": True}

@app.get("/api/set_webhook")
async def set_webhook(request: Request):
    host = request.headers.get("host")
    webhook_url = f"https://{host}/api/webhook"
    await bot.set_webhook(webhook_url, drop_pending_updates=True)
    return {"status": "Webhook muvaffaqiyatli ulandi!", "url": webhook_url}

@app.get("/api/replies")
async def get_replies(patient_id: str = ""):
    if not re.match(r"^ID-\d{6}$", patient_id):
        return {"replies": []}
    msgs = list(WEB_REPLIES[patient_id])
    WEB_REPLIES[patient_id].clear()
    return {"replies": msgs}

@app.get("/api/schedule")
async def get_schedule():
    return {"schedule": [{"text": s} for s in SCHEDULE_SLOTS[:5]]}
