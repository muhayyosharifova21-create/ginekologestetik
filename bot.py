import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

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

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")

# ================= MA'LUMOTLAR BAZASI =================
conn = sqlite3.connect("surayyo_clinic.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    full_name TEXT,
    username TEXT,
    phone TEXT,
    warnings INTEGER DEFAULT 0,
    is_banned INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    service TEXT,
    visit_type TEXT,
    visit_date TEXT,
    visit_time TEXT,
    phone TEXT,
    status TEXT DEFAULT 'active'
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    stars INTEGER,
    created_at TEXT
)
""")
conn.commit()

# ================= XIZMATLAR RO'YXATI (NARXLARSIZ) =================
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

# ================= AVTOMATIK KONSULTANT BILIMLAR BAZASI =================
KNOWLEDGE_BASE = [
    {
        "keywords": ["estetik ginekologiya", "lazer so2", "co2", "so2"],
        "answer": (
            "🌸 <b>Estetik ginekologiya va Lazer SO2:</b>\n\n"
            "Ayollarning intim zonasidagi tug'ma o'zgarishlar, tug'ruqdan keyingi jarohatlar va yosh bilan bog'liq o'zgarishlarni jarrohlik hamda zamonaviy lazer SO2 yordamida og'riqsiz va qonsiz tiklash yo'nalishidir. Ayollarda o'ziga bo'lgan ishonchni va intim salomatlikni tiklaydi."
        )
    },
    {
        "keywords": ["labioplastika", "labio", "kichik jinsiy lab", "lablar plastikasi"],
        "answer": (
            "✨ <b>Labioplastika (Kichik jinsiy lablar plastikasi):</b>\n\n"
            "• <b>Nima uchun:</b> Tug'ma gipertrofiya, assimetriya yoki tug'ruqdan keyingi o'zgarishlarni bartaraf etish uchun.\n"
            "• <b>Muolaja vaqti:</b> 30–45 daqiqa (mahalliy og'riqsizlantirish ostida).\n"
            "• <b>Tiklanish davri:</b> To'liq bitish 3–4 hafta.\n"
            "• <b>Cheklovlar:</b> 3–4 hafta davomida jinsiy aloqa va og'ir jismoniy mashqlar taqiqlanadi."
        )
    },
    {
        "keywords": ["vaginoplastika", "vagina", "toraytirish", "kengayish"],
        "answer": (
            "✨ <b>Vaginoplastika (Vagina devorlarini toraytirish):</b>\n\n"
            "• <b>Nima uchun:</b> Tug'ruqdan keyingi jinsiy yo'llar kengayishini bartaraf etish, mushaklar tonusini va sezgirlikni tiklash.\n"
            "• <b>Muolaja vaqti:</b> 1 – 1.5 soat (umumiy yoki spinal og'riqsizlantirish ostida).\n"
            "• <b>Tiklanish davri:</b> 6–8 hafta.\n"
            "• <b>Cheklovlar:</b> 2 oy (8 hafta) davomida jinsiy hayot va og'ir yuk ko'tarish taqiqlanadi."
        )
    },
    {
        "keywords": ["klitor", "klitoroplastika", "kilitra"],
        "answer": (
            "✨ <b>Klitoroplastika:</b>\n\n"
            "• <b>Nima uchun:</b> Klitor atrofidagi ortiqcha to'qimalarni olib tashlash, sezgirlikni oshirish va estetik ko'rinishni yaxshilash.\n"
            "• <b>Muolaja vaqti:</b> 30–40 daqiqa (mahalliy og'riqsizlantirish ostida).\n"
            "• <b>Tiklanish davri:</b> 3 hafta ichida to'liq tuzaladi."
        )
    },
    {
        "keywords": ["oqartirish", "pigment", "qorayish"],
        "answer": (
            "🌸 <b>Intim zona pigmentatsiyasini yo'qotish (Oqartirish):</b>\n\n"
            "• <b>Muolaja vaqti:</b> 20–30 daqiqa (kursi 3–4 ta muolajadan iborat).\n"
            "• <b>Tiklanish davri:</b> Terining yangilanishi 5–7 kun davom etadi.\n"
            "• <b>Cheklovlar:</b> 3–5 kun jinsiy aloqadan saqlanish tavsiya etiladi."
        )
    },
    {
        "keywords": ["prp", "plazma", "plazmoterapiya", "yoshartirish", "qurish", "qichishish"],
        "answer": (
            "💉 <b>Intim yoshartirish va Plazmoterapiya (PRP):</b>\n\n"
            "• <b>Nima uchun:</b> To'qimalarni yoshartirish, qurish va qichishishni yo'qotish, sezgirlik hamda tabiiy namlikni qaytarish.\n"
            "• <b>Muolaja vaqti:</b> 30 daqiqa (bemorning o'z qonidan plazma tayyorlanadi).\n"
            "• <b>Tiklanish:</b> 1–2 kunda tiklanadi, 2–3 kun jinsiy aloqadan saqlanish kifoya."
        )
    },
    {
        "keywords": ["eroziya", "bachadon bo'yni"],
        "answer": (
            "🔬 <b>Bachadon bo'yni eroziyasini davolash:</b>\n\n"
            "• <b>Usul:</b> Lazer yoki radioto'lqin usulida og'riqsiz davolanadi.\n"
            "• <b>Muolaja vaqti:</b> 15–20 daqiqa.\n"
            "• <b>Tiklanish davri:</b> To'liq bitish vaqti 3–4 hafta (shu davrda jinsiy aloqa taqiqlanadi)."
        )
    },
    {
        "keywords": ["polip"],
        "answer": (
            "🔬 <b>Bachadon bo'yni va devori poliplarini olish:</b>\n\n"
            "• <b>Muolaja vaqti:</b> 15–30 daqiqa.\n"
            "• <b>Tiklanish davri:</b> 2 hafta ichida tiklanadi (2–3 hafta jinsiy aloqada bo'lmaslik tavsiya etiladi)."
        )
    },
    {
        "keywords": ["spiral", "implantsperal", "homiladorlik"],
        "answer": (
            "🛡 <b>Spiral (Implantsperal) o'rnatish:</b>\n\n"
            "• <b>Muolaja vaqti:</b> 5–10 daqiqa.\n"
            "• <b>Tiklanish:</b> 1–2 kunda organizm moslashadi. 7–10 kun og'ir yuk ko'tarish va issiq vannaga tushish taqiqlanadi."
        )
    },
    {
        "keywords": ["sistit", "siydik"],
        "answer": (
            "⚡ <b>Sistitni lazer SO2 da davolash:</b>\n\n"
            "Zamonaviy lazer SO2 aparati yordamida og'riqsiz va qonsiz tarzda sistit muammosidan xalos bo'lasiz. Tiklanish vaqti 5–7 kun."
        )
    },
    {
        "keywords": ["miyoma"],
        "answer": (
            "🏥 <b>Bachadon miyomasi va uni davolash:</b>\n\n"
            "Zamonaviy dori-darmonlar yoki kichik invaziv jarrohlik yo'li bilan davolanadi. Tiklanish davri 3–4 haftani tashkil qiladi."
        )
    },
    {
        "keywords": ["razriv", "yirtilish", "chandiq"],
        "answer": (
            "🪡 <b>Tug'ruqdan keyingi yirtilishlarni tiklash (Razriv):</b>\n\n"
            "• <b>Muolaja vaqti:</b> 45–60 daqiqa.\n"
            "• <b>Tiklanish davri:</b> To'liq bitish 4–6 hafta."
        )
    },
    {
        "keywords": ["ajralma", "videlina", "qon", "hayz"],
        "answer": (
            "🩺 <b>Ajralmalar va hayz o'zgarishlari:</b>\n\n"
            "Mikroflorani normallashtirish va gormonal holatni aniq tekshirish uchun shifokor ko'rigidan o'tish zarur. Qabulga yozilish uchun pastdagi tugmani bosing."
        )
    },
    {
        "keywords": ["narx", "qancha", "necha pul", "to'lov", "summa"],
        "answer": (
            f"ℹ️ Muolajalar narxi bemorning individual holati va ko'rik natijasiga qarab belgilanadi.\n\n"
            f"Aniq ma'lumot olish uchun qabulga yozilishingiz yoki shaxsan <b>{DOCTOR_NAME}</b>ga murojaat qilishingiz mumkin:\n"
            f"📞 Telefon: {PHONE_NUMBER}\n✉️ Telegram: @Sr7431"
        )
    },
    {
        "keywords": ["manzil", "qayerda", "lokatsiya", "telefon", "nomer", "raqam", "lichka"],
        "answer": (
            f"🏥 <b>{DOCTOR_NAME} klinikasi:</b>\n\n"
            f"📍 <b>Manzil:</b> {CLINIC_ADDRESS}\n"
            f"🕘 <b>Ish vaqti:</b> {WORK_HOURS}\n"
            f"📞 <b>Telefon:</b> {PHONE_NUMBER}\n"
            f"✉️ <b>Telegram lichka:</b> @Sr7431"
        )
    }
]

GREETINGS = ["assalomu alaykum", "assalom", "salom", "qalaysiz", "yaxshimisiz", "murojaat", "savolim bor"]

# ================= HOLATLAR (FSM) =================
class BookingState(StatesGroup):
    choosing_service = State()
    choosing_type = State()
    choosing_date = State()
    choosing_time = State()
    entering_phone = State()

class BroadcastState(StatesGroup):
    waiting_for_message = State()

# ================= TUGMALAR =================
def main_menu(user_id: int):
    buttons = [
        [KeyboardButton(text="📅 Qabulga yozilish"), KeyboardButton(text="🩺 Tibbiy xizmatlar")],
        [KeyboardButton(text="💬 Surayyo Vahobjonovnaga savol"), KeyboardButton(text="📞 Aloqa va manzil")],
        [KeyboardButton(text="⭐ Xizmatni baholash")]
    ]
    if user_id in ADMIN_IDS:
        buttons.append([KeyboardButton(text="📊 Statistika"), KeyboardButton(text="📋 Bugungi qabullar")])
        buttons.append([KeyboardButton(text="📢 Barchaga Broadcast yuborish"), KeyboardButton(text="💡 Yordam & Qo'llanma")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def consult_action_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Qabulga yozilish", callback_data="start_booking")],
        [InlineKeyboardButton(text="👩‍⚕️ Shifokor lichkasi (@Sr7431)", url=DOCTOR_TELEGRAM)]
    ])

def rating_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⭐ 1", callback_data="rate_1"),
            InlineKeyboardButton(text="⭐ 2", callback_data="rate_2"),
            InlineKeyboardButton(text="⭐ 3", callback_data="rate_3"),
            InlineKeyboardButton(text="⭐ 4", callback_data="rate_4"),
            InlineKeyboardButton(text="⭐ 5", callback_data="rate_5"),
        ]
    ])

def is_user_banned(user_id: int) -> bool:
    cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return bool(row and row[0] == 1)

# ================= 🛡️ XAVFSIZLIK FILTRI (18+ RASM / VIDEO BLOKLASH) =================
@dp.message(
    F.from_user.id.not_in(ADMIN_IDS),
    (F.photo | F.video | F.animation | F.document | F.video_note | F.sticker)
)
async def block_media_messages(message: types.Message):
    user_id = message.from_user.id
    # Yuborilgan rasm/videoni darhol o'chirish
    try:
        await message.delete()
    except Exception:
        pass

    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, full_name, username) VALUES (?, ?, ?)",
        (user_id, message.from_user.full_name, message.from_user.username)
    )
    cursor.execute("UPDATE users SET warnings = warnings + 1 WHERE user_id = ?", (user_id,))
    conn.commit()

    cursor.execute("SELECT warnings FROM users WHERE user_id = ?", (user_id,))
    warnings = cursor.fetchone()[0]

    if warnings >= 3:
        cursor.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        await message.answer("🚫 Xavfsizlik qoidalarini 3 marta buzganingiz sababli botdan foydalanish huquqingiz cheklandi.")
    else:
        await message.answer(
            f"⚠️ <b>Xavfsizlik qoidasi ({warnings}/3):</b>\n\n"
            f"Botga rasm, video yoki fayl yuborish <b>qat'iyan taqiqlangan!</b>\n"
            f"Iltimos, faqat <b>matnli savol</b> yuboring (3-ogohlantirishda bloklanasiz).",
            parse_mode="HTML"
        )

# ================= START BUYRUQ =================
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    if is_user_banned(message.from_user.id):
        return
    await state.clear()
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, full_name, username) VALUES (?, ?, ?)",
        (message.from_user.id, message.from_user.full_name, message.from_user.username)
    )
    conn.commit()

    welcome_text = (
        f"Assalomu alaykum, <b>{message.from_user.first_name}</b>! 🌸\n\n"
        f"Estetik ginekolog vrach <b>Surayyo Vahobjonovna</b>ning rasmiy 24/7 konsultant botiga xush kelibsiz.\n\n"
        f"<i>“Shifokor — bu kasb emas, bu chaqiriq. Insonlarga yaxshilik qilish – eng katta baxt.”</i>\n\n"
        f"📞 <b>Telefon:</b> {PHONE_NUMBER}\n"
        f"✉️ <b>Shaxsiy Telegram:</b> @Sr7431\n\n"
        f"⚠️ <i>Eslatma: Xavfsizlik qoidasiga ko'ra botda faqat matnli xabarlar qabul qilinadi (rasm/video taqiqlangan).</i>"
    )
    await message.answer(welcome_text, reply_markup=main_menu(message.from_user.id), parse_mode="HTML")
    await message.answer("Bevosita shifokor bilan bog'lanish:", reply_markup=consult_action_keyboard())

# ================= XIZMATLAR RO'YXATI =================
@dp.message(F.text.in_(["🩺 Tibbiy xizmatlar", "Xizmatlar", "Qanday xizmatlar bor?"]))
async def show_services(message: types.Message):
    if is_user_banned(message.from_user.id):
        return
    text = f"<b>🩺 {DOCTOR_NAME} — Tibbiy xizmatlarimiz:</b>\n\n"
    for name, duration in SERVICES.values():
        text += f"• <b>{name}</b> — {duration}\n"
    text += f"\n📍 <b>Manzil:</b> {CLINIC_ADDRESS}\n🕘 <b>Ish vaqti:</b> {WORK_HOURS}\n📞 <b>Telefon:</b> {PHONE_NUMBER}"

    await message.answer(text, reply_markup=consult_action_keyboard(), parse_mode="HTML")

# ================= MANZIL VA BOG'LANISH =================
@dp.message(F.text == "📞 Aloqa va manzil")
async def show_location(message: types.Message):
    if is_user_banned(message.from_user.id):
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👩‍⚕️ Shifokor Telegram lichkasi (@Sr7431)", url=DOCTOR_TELEGRAM)],
        [
            InlineKeyboardButton(text="✈️ Telegram kanal", url=TELEGRAM_CHANNEL),
            InlineKeyboardButton(text="▶️ YouTube kanal", url=YOUTUBE_CHANNEL)
        ]
    ])
    await message.answer(
        f"🏥 <b>{DOCTOR_NAME}</b>\n\n"
        f"📞 <b>Telefon raqam:</b> {PHONE_NUMBER}\n"
        f"✉️ <b>Telegram lichka:</b> @Sr7431\n"
        f"📍 <b>Manzil:</b> {CLINIC_ADDRESS}\n"
        f"🕘 <b>Ish vaqti:</b> {WORK_HOURS}",
        reply_markup=kb,
        parse_mode="HTML"
    )

# ================= QABULGA YOZILISH JARAYONI =================
@dp.message(F.text.in_(["📅 Qabulga yozilish", "Yozilmoqchiman", "Assalomu alaykum, ertaga qabul bormi?", "Qabul bormi", "Yozilish"]))
@dp.callback_query(F.data == "start_booking")
async def start_booking(event: types.Message | types.CallbackQuery, state: FSMContext):
    if is_user_banned(event.from_user.id):
        return
    msg = event.message if isinstance(event, types.CallbackQuery) else event
    if isinstance(event, types.CallbackQuery):
        await event.answer()

    buttons = []
    for key, (name, _) in SERVICES.items():
        buttons.append([InlineKeyboardButton(text=name, callback_data=f"srv_{key}")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await msg.answer(
        f"Assalomu alaykum! 😊 <b>{DOCTOR_NAME}</b> qabuliga bo'sh vaqtlar bor.\n\nQaysi xizmat turiga yozilmoqchisiz?",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await state.set_state(BookingState.choosing_service)

@dp.callback_query(BookingState.choosing_service, F.data.startswith("srv_"))
async def process_service(callback: types.CallbackQuery, state: FSMContext):
    srv_key = callback.data.split("_", 1)[1]
    srv_name, _ = SERVICES[srv_key]
    await state.update_data(service=srv_name)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💻 Online", callback_data="type_Online"),
            InlineKeyboardButton(text="🏥 Offline", callback_data="type_Offline")
        ]
    ])
    await callback.message.edit_text(
        f"Tanlangan xizmat: <b>{srv_name}</b>\n\nQabul turini tanlang:",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await state.set_state(BookingState.choosing_type)

@dp.callback_query(BookingState.choosing_type, F.data.startswith("type_"))
async def process_type(callback: types.CallbackQuery, state: FSMContext):
    visit_type = callback.data.split("_")[1]
    await state.update_data(visit_type=visit_type)

    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    day_after = today + timedelta(days=2)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Ertaga ({tomorrow.strftime('%d.%m.%Y')})", callback_data=f"date_{tomorrow.strftime('%Y-%m-%d')}")],
        [InlineKeyboardButton(text=f"Indinga ({day_after.strftime('%d.%m.%Y')})", callback_data=f"date_{day_after.strftime('%Y-%m-%d')}")]
    ])
    await callback.message.edit_text("Qabul kunini tanlang:", reply_markup=kb)
    await state.set_state(BookingState.choosing_date)

@dp.callback_query(BookingState.choosing_date, F.data.startswith("date_"))
async def process_date(callback: types.CallbackQuery, state: FSMContext):
    visit_date = callback.data.split("_")[1]
    await state.update_data(visit_date=visit_date)

    times = ["10:00", "11:30", "12:30", "14:00", "15:00", "16:30"]
    row1 = [InlineKeyboardButton(text=t, callback_data=f"time_{t}") for t in times[:3]]
    row2 = [InlineKeyboardButton(text=t, callback_data=f"time_{t}") for t in times[3:]]
    kb = InlineKeyboardMarkup(inline_keyboard=[row1, row2])

    await callback.message.edit_text("Vaqtni tanlang:", reply_markup=kb)
    await state.set_state(BookingState.choosing_time)

@dp.callback_query(BookingState.choosing_time, F.data.startswith("time_"))
async def process_time(callback: types.CallbackQuery, state: FSMContext):
    visit_time = callback.data.split("_")[1]
    await state.update_data(visit_time=visit_time)

    phone_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await callback.message.delete()
    await callback.message.answer(
        "Tasdiqlash uchun telefon raqamingizni yuboring (pastdagi tugmani bosing yoki raqamni yozing):",
        reply_markup=phone_kb
    )
    await state.set_state(BookingState.entering_phone)

@dp.message(BookingState.entering_phone)
async def finish_booking(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
    data = await state.get_data()

    cursor.execute(
        "INSERT INTO appointments (user_id, service, visit_type, visit_date, visit_time, phone) VALUES (?, ?, ?, ?, ?, ?)",
        (message.from_user.id, data["service"], data["visit_type"], data["visit_date"], data["visit_time"], phone)
    )
    conn.commit()

    try:
        appt_dt = datetime.strptime(f"{data['visit_date']} {data['visit_time']}", "%Y-%m-%d %H:%M")
        reminder_dt = appt_dt - timedelta(hours=1)
        rating_dt = appt_dt + timedelta(hours=2)

        if reminder_dt > datetime.now():
            scheduler.add_job(
                send_reminder,
                "date",
                run_date=reminder_dt,
                args=[message.from_user.id, data["visit_time"]]
            )
        if rating_dt > datetime.now():
            scheduler.add_job(
                ask_rating,
                "date",
                run_date=rating_dt,
                args=[message.from_user.id]
            )
    except Exception as e:
        logging.error(f"Vaqt rejalashtirishda xato: {e}")

    direct_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👩‍⚕️ Shifokor lichkasiga yozish (@Sr7431)", url=DOCTOR_TELEGRAM)]
    ])

    confirm_text = (
        f"✅ <b>Qabulga yozildingiz!</b>\n\n"
        f"👩‍⚕️ Shifokor: <b>{DOCTOR_NAME}</b>\n"
        f"🩺 Xizmat: {data['service']}\n"
        f"📅 Sana: {data['visit_date']}, {data['visit_time']}\n"
        f"📍 Tur: {data['visit_type']} qabul\n"
        f"📞 Aloqa: {PHONE_NUMBER}\n\n"
        f"<i>Qabuldan 1 soat oldin sizga eslatma yuboramiz.</i>"
    )
    await message.answer(confirm_text, reply_markup=direct_kb, parse_mode="HTML")
    await message.answer("Asosiy menyu:", reply_markup=main_menu(message.from_user.id))

    admin_msg = (
        f"🔔 <b>YANGI QABULGA YOZILISH!</b>\n\n"
        f"👤 Bemor: {message.from_user.full_name}\n"
        f"📞 Telefon: {phone}\n"
        f"🩺 Xizmat: {data['service']}\n"
        f"📅 Vaqt: {data['visit_date']} | {data['visit_time']}\n"
        f"📍 Turi: {data['visit_type']}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_msg, parse_mode="HTML")
        except Exception:
            pass

    await state.clear()

async def send_reminder(user_id: int, visit_time: str):
    try:
        await bot.send_message(
            user_id,
            f"⏰ <b>Eslatma!</b>\n\nBir soatdan keyin, soat <b>{visit_time}</b> da <b>{DOCTOR_NAME}</b> qabuliga yozilgansiz.\n📍 {CLINIC_ADDRESS}\n📞 {PHONE_NUMBER}",
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Eslatma yuborishda xato: {e}")

# ================= XIZMATNI BAHOLASH (1-5 YULDUZ) =================
async def ask_rating(user_id: int):
    try:
        await bot.send_message(
            user_id,
            f"<b>{DOCTOR_NAME}</b> xizmatini baholang:",
            reply_markup=rating_keyboard(),
            parse_mode="HTML"
        )
    except Exception:
        pass

@dp.message(F.text == "⭐ Xizmatni baholash")
async def manual_rating(message: types.Message):
    if is_user_banned(message.from_user.id):
        return
    await message.answer(
        f"<b>{DOCTOR_NAME}</b> xizmatini baholang:",
        reply_markup=rating_keyboard(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("rate_"))
async def process_rating(callback: types.CallbackQuery):
    stars = int(callback.data.split("_")[1])
    cursor.execute(
        "INSERT INTO ratings (user_id, stars, created_at) VALUES (?, ?, ?)",
        (callback.from_user.id, stars, datetime.now().strftime("%Y-%m-%d %H:%M"))
    )
    conn.commit()

    await callback.message.edit_text(
        f"⭐ {stars} — Fikringiz uchun katta rahmat! 🙏"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"⭐ <b>Yangi baho:</b> {stars}/5\n👤 Bemor: {callback.from_user.full_name}",
                parse_mode="HTML"
            )
        except Exception:
            pass

# ================= SHIFOKORGA SAVOL BERISH =================
@dp.message(F.text == "💬 Surayyo Vahobjonovnaga savol")
async def ask_doctor_prompt(message: types.Message):
    if is_user_banned(message.from_user.id):
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👩‍⚕️ Shaxsiy Telegram (@Sr7431)", url=DOCTOR_TELEGRAM)]
    ])
    await message.answer(
        f"✍️ Savolingizni faqat matn shaklida yozib yuboring — botimiz darhol ma'lumot beradi yoki savolingizni <b>{DOCTOR_NAME}</b>ga yetkazadi.\n\n"
        f"Yoki bevosita shaxsiy Telegram orqali murojaat qilishingiz mumkin:\n"
        f"📞 Telefon: {PHONE_NUMBER}",
        reply_markup=kb,
        parse_mode="HTML"
    )

# ================= ADMIN FUNKSIYALARI =================
@dp.message(F.text == "📊 Statistika", F.from_user.id.in_(ADMIN_IDS))
async def show_stats(message: types.Message):
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM appointments")
    total_appts = cursor.fetchone()[0]

    cursor.execute("SELECT AVG(stars) FROM ratings")
    avg_rating = cursor.fetchone()[0]
    rating_str = f"{avg_rating:.1f} / 5.0" if avg_rating else "Hali baholanmagan"

    await message.answer(
        f"📊 <b>{DOCTOR_NAME} boti statistikasi:</b>\n\n"
        f"👥 <b>{total_users}</b> ta mijoz bazada saqlangan\n"
        f"📅 <b>{total_appts}</b> ta jami qabulga yozilishlar\n"
        f"⭐ O'rtacha baho: <b>{rating_str}</b>",
        parse_mode="HTML"
    )

@dp.message(F.text == "📋 Bugungi qabullar", F.from_user.id.in_(ADMIN_IDS))
async def today_appointments(message: types.Message):
    cursor.execute("SELECT service, visit_date, visit_time, visit_type, phone FROM appointments ORDER BY id DESC LIMIT 15")
    rows = cursor.fetchall()
    if not rows:
        await message.answer("Hozircha qabulga yozilganlar yo'q.")
        return
    text = "📋 <b>So'nggi yozilgan bemorlar:</b>\n\n"
    for r in rows:
        text += f"• {r[1]} <b>{r[2]}</b> ({r[3]}) — {r[0]} | 📞 {r[4]}\n"
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("elon"), F.from_user.id.in_(ADMIN_IDS))
async def quick_announcement(message: types.Message):
    raw_text = message.text.replace("/elon barchaga", "").replace("/elon", "").strip()
    if not raw_text:
        await message.answer(
            "Namuna:\n<code>/elon barchaga 🔥 Yangilik! Qabulga yozilish uchun pastdagi tugmani bosing.</code>",
            parse_mode="HTML"
        )
        return

    book_btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Qabulga yozilish", callback_data="start_booking")]
    ])

    cursor.execute("SELECT user_id FROM users WHERE is_banned = 0")
    users = cursor.fetchall()
    sent = 0
    for (uid,) in users:
        try:
            await bot.send_message(uid, raw_text, reply_markup=book_btn)
            sent += 1
        except Exception:
            pass
    await message.answer(f"✅ E'lon {sent} ta mijozga «Qabulga yozilish» tugmasi bilan yuborildi!")

@dp.message(F.text == "📢 Barchaga Broadcast yuborish", F.from_user.id.in_(ADMIN_IDS))
async def start_broadcast(message: types.Message, state: FSMContext):
    await message.answer("📢 Barcha foydalanuvchilarga yuboriladigan xabar matnini (yoki rasm/video) yuboring:")
    await state.set_state(BroadcastState.waiting_for_message)

@dp.message(BroadcastState.waiting_for_message, F.from_user.id.in_(ADMIN_IDS))
async def send_broadcast(message: types.Message, state: FSMContext):
    book_btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Qabulga yozilish", callback_data="start_booking")]
    ])
    cursor.execute("SELECT user_id FROM users WHERE is_banned = 0")
    users = cursor.fetchall()
    sent = 0
    for (uid,) in users:
        try:
            await message.copy_to(uid, reply_markup=book_btn)
            sent += 1
        except Exception:
            pass
    await message.answer(f"✅ Xabar {sent} ta foydalanuvchiga muvaffaqiyatli yuborildi!")
    await state.clear()

@dp.message(F.text == "💡 Yordam & Qo'llanma", F.from_user.id.in_(ADMIN_IDS))
async def admin_help(message: types.Message):
    await message.answer(
        f"💡 <b>{DOCTOR_NAME} — Admin qo'llanmasi:</b>\n\n"
        "1. <b>📊 Statistika:</b> Bazadagi mijozlar soni va o'rtacha bahoni ko'rsatadi.\n"
        "2. <b>/elon barchaga Matn:</b> Barcha mijozlarga tagida «Qabulga yozilish» tugmasi bor xabar yuboradi.\n"
        "3. <b>Reply:</b> Bemor savoliga javob berish uchun uning xabariga Reply qiling.\n"
        "4. <b>Xavfsizlik:</b> Foydalanuvchilar rasm/video yuborsa avtomatik o'chiriladi va 3-marta bloklanadi.",
        parse_mode="HTML"
    )

# ================= AVTOMATIK SUHBAT VA SAVOL-JAVOB =================
@dp.message()
async def handle_messages(message: types.Message):
    if is_user_banned(message.from_user.id):
        return

    # 1. Admin bemor xabariga Reply qilsa
    if message.from_user.id in ADMIN_IDS and message.reply_to_message:
        orig_text = message.reply_to_message.text or ""
        if "TG_USER_ID:" in orig_text:
            try:
                target_id = int(orig_text.split("TG_USER_ID:")[1].split()[0])
                await bot.send_message(
                    target_id,
                    f"👩‍⚕️ <b>{DOCTOR_NAME} javobi:</b>\n\n{message.text}",
                    parse_mode="HTML"
                )
                await message.answer("✅ Javobingiz bemorga yetkazildi!")
            except Exception as e:
                await message.answer(f"❌ Xatolik: {e}")
        return

    if message.from_user.id not in ADMIN_IDS and message.text:
        user_text = message.text.lower().strip()

        # 2. Avtomatik bilimlar bazasidan javob qidirish
        for item in KNOWLEDGE_BASE:
            if any(kw in user_text for kw in item["keywords"]):
                await message.answer(
                    f"{item['answer']}\n\n👇 Qabulga yozilish yoki shifokor bilan bog'lanish uchun tugmani bosing:",
                    reply_markup=consult_action_keyboard(),
                    parse_mode="HTML"
                )
                return

        # 3. Salomlashish va umumiy suhbatga avtomatik javob
        if any(gr in user_text for gr in GREETINGS) and len(user_text.split()) <= 5:
            await message.answer(
                f"Va alaykum assalom, <b>{message.from_user.first_name}</b>! 😊\n\n"
                f"<b>{DOCTOR_NAME}</b>ning virtual yordamchisiman. Sizga qanday yordam bera olaman? "
                f"Muolaja nomini yozishingiz (masalan: <i>labioplastika, vaginoplastika, eroziya, sistit, PRP</i>) yoki qabulga yozilishingiz mumkin:",
                reply_markup=consult_action_keyboard(),
                parse_mode="HTML"
            )
            return

        # 4. Individual tibbiy savol bo'lsa
        forward_text = (
            f"🩺 <b>YANGI SAVOL ({DOCTOR_NAME})</b>\n\n"
            f"👤 Bemor: {message.from_user.full_name}\n"
            f"🆔 TG_USER_ID: {message.from_user.id}\n"
            f"💬 Savol: {message.text}\n\n"
            f"👇 <i>Javob berish uchun shu xabarga Reply qiling.</i>"
        )
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, forward_text, parse_mode="HTML")
            except Exception:
                pass

        await message.answer(
            f"✅ Savolingiz qabul qilindi va shaxsan <b>{DOCTOR_NAME}</b>ga yuborildi. Shifokor ko'rib chiqib, shu yerda javob beradilar.\n\n"
            f"Shoshilinch bo'lsa, to'g'ridan-to'g'ri shifokor lichkasiga yozishingiz yoki qo'ng'iroq qilishingiz mumkin:\n"
            f"📞 Telefon: {PHONE_NUMBER}",
            reply_markup=consult_action_keyboard(),
            parse_mode="HTML"
        )

# ================= ISHGA TUSHIRISH =================
async def main():
    scheduler.start()
    await bot.delete_webhook(drop_pending_updates=True)
    print(f"{DOCTOR_NAME} himoyalangan konsultant boti 24/7 rejimda ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
