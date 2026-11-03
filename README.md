# USB Qalqon — Web boshqaruv tizimi

USB Qalqon desktop dasturining markazlashgan web qismi. Tizim qurilmalar bazasini,
tashkiliy tuzilmadagi foydalanuvchilarni va qora ro'yxat hodisalarini saqlaydi.

- **Backend:** FastAPI + SQLAlchemy 2 + SQLite (PostgreSQL'ga ham oson o'tkaziladi)
- **Frontend:** React 18 + Vite + React Router + Axios
- **Auth:** JWT (`/api/auth/login`), parollar PBKDF2-SHA256 bilan xeshlanadi
- **Hujjat:** Swagger — `http://localhost:8000/docs`, ReDoc — `/redoc`

---

## 1. Papka tuzilishi

```
.
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI ilovasi, routerlar, CORS
│   │   ├── config.py          # .env sozlamalari
│   │   ├── database.py        # SQLite engine va sessiya
│   │   ├── models.py          # User, Device, BlacklistEntry
│   │   ├── security.py        # JWT, parol xeshi, agent token
│   │   ├── hierarchy.py       # ierarxiya ruxsatlari
│   │   ├── deps.py            # auth dependency'lar
│   │   ├── seed.py            # admin va demo ma'lumotlar
│   │   ├── routers/           # auth, users, devices, blacklist, agent, software, stats
│   │   └── services/          # Devices.txt parseri
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .env.example
│   └── data/usbqalqon.db      # ishga tushganda avtomatik yaratiladi
├── frontend/
│   ├── src/
│   │   ├── pages/             # Dashboard, Blacklist, Users, Software, Login
│   │   ├── components/        # Layout, Modal, Icon, jadvallar
│   │   ├── context/           # Auth, Toast
│   │   ├── api.js             # axios + JWT interceptor
│   │   └── styles.css
│   ├── package.json
│   ├── Dockerfile
│   ├── nginx.conf
│   └── vite.config.js         # /api -> localhost:8000 proxy
└── README.md
```

---

## 2. Tez ishga tushirish

### Backend

```bash
cd backend

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cp .env.example .env        # ixtiyoriy, lekin tavsiya etiladi
# .env ichida SECRET_KEY va ADMIN_PASSWORD ni albatta o'zgartiring

PYTHONPATH=. .venv/bin/uvicorn app.main:app --reload --port 8000
```

Birinchi ishga tushishda:

- `data/usbqalqon.db` SQLite bazasi yaratiladi;
- `.env` dagi `ADMIN_USERNAME` / `ADMIN_PASSWORD` bo'yicha administrator yaratiladi
  (standart: **admin / admin123**).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Brauzer: **http://localhost:5173** — Vite `/api` so'rovlarini
`http://localhost:8000` ga proksi qiladi.

### Demo ierarxiya (ixtiyoriy)

```bash
cd backend
PYTHONPATH=. .venv/bin/python -m app.seed --demo
```

Yaratiladi:

```
admin (admin123)
└── rahbar (rahbar123)
    └── xodim (xodim123)
```

Demo rejimda 3 ta qurilma va 1 ta qora ro'yxat yozuvi ham qo'shiladi.
`--demo` faqat bitta foydalanuvchi mavjud bo'lganda ishlaydi.

---

## 3. Rollar va ko'rinish chegarasi

| Rol | Huquqlar |
|-----|----------|
| **Administrator** (`is_superuser=true`) | Butun tizim, barcha foydalanuvchilar va ma'lumotlar |
| **Rahbar / Xodim** | O'zining va barcha quyi bo'limlarning ma'lumotlari |

- Har bir foydalanuvchi faqat o'ziga ko'rinadigan qurilmalar/qora ro'yxat
  yozuvlarini ko'radi.
- Yuqori bo'lim foydalanuvchisi o'zining **va butun quyi tuzilmaning**
  ma'lumotlarini ko'radi.
- Oddiy foydalanuvchi faqat o'ziga biriktirilgan quyi bo'limlarda yangi
  foydalanuvchi yaratadi.
- Ildiz (yuqori bo'limsiz) foydalanuvchini faqat administrator yaratadi.
- Siklni oldini olish: foydalanuvchini o'z quyi tuzilmasiga yuqori bo'lim qilib
  qo'yib bo'lmaydi.

---

## 4. Devices.txt import

**Bosh sahifa → Import** tugmasi orqali desktop dasturning `Devices.txt` fayli
yuklanadi. Fayl UTF-8 yoki CP1251 kodlashida bo'lishi mumkin (10 MB gacha).

Kutilayotgan format (bitta qatorda yoki ko'p qatorda):

```
Seriya raqami: E0D55E6C382BE820D9430146; Ishlab chiqaruvchi: KINGSTON; Model: DATATRAVELER_3.0; Grif: Nomaxfiy
```

Xususiyatlar:

- `Grif` ko'rsatilmasa — `Nomaxfiy` qo'yiladi.
- `Qurilma turi` ko'rsatilmasa, vendor/modeldan taxmin qilinadi
  (Fleshka, Hard disk, Android smartfon, Iphone smartphone).
- Bir bo'lim ichida takrorlangan seriya raqamlari o'tkazib yuboriladi.
- Import natijasi: jami yozuv, qo'shilgan, o'tkazilgan va xatolar ro'yxati.
- **Export** tugmasi bazadagi qurilmalarni yana `Devices.txt` formatida beradi.

---

## 5. Desktop agent

**Dasturiy ta'minot** sahifasida administrator yagona agent `.exe` faylini
yuklaydi. Barcha tizimga kirgan foydalanuvchilar shu faylni yuklab oladi.

| Amal | Kim uchun | Tavsif |
|------|-----------|--------|
| Yuklash | Administrator | Windows PE (MZ) formatida, hajmi sozlamalar bilan cheklangan |
| Yuklab olish | Barcha foydalanuvchilar | Fayl nomi va SHA-256 nazorat summasi bilan |
| O'chirish | Administrator | Joriy paket bazadan va diskdan o'chiriladi |

Agent mantiqi:

1. Har 10 soniyada USB qurilmalarni tekshiradi.
2. `GET /api/agent/check/{serial}` orqali ruxsat etilganlar bazasida bor-yo'qligini so'raydi.
3. Bazada yo'q qurilmalarni `POST /api/agent/blacklist` ga yuboradi.
4. Bir qurilma 30 daqiqada bir marta qayd etiladi; takroriy signalda
   `event_count` oshadi.
5. Barcha agent so'rovlari `X-Agent-Token` sarlavhasi bilan autentifikatsiya qilinadi.

Har bir foydalanuvchining shaxsiy agent tokeni `GET /api/software/info` orqali
olinadi. Token `POST /api/software/token/rotate` bilan yangilanadi (eskisi
bekor qilinadi va agentni qayta sozlash kerak bo'ladi).

---

## 6. API va Swagger

Swagger UI: **http://localhost:8000/docs**

### Asosiy endpointlar

| Metod | Endpoint | Tavsif |
|-------|----------|--------|
| POST | `/api/auth/login` | JWT token (form-data: username, password) |
| GET | `/api/auth/me` | Joriy foydalanuvchi |
| POST | `/api/auth/change-password` | Parolni almashtirish |
| GET/POST | `/api/users` | Foydalanuvchilar ro'yxati / yaratish |
| GET | `/api/users/tree` | Tashkiliy tuzilma |
| GET/PUT/DELETE | `/api/users/{id}` | Bitta foydalanuvchi CRUD |
| GET/POST | `/api/devices` | Qurilmalar ro'yxati (qidiruv, filtr, sahifa) / yaratish |
| POST | `/api/devices/import` | `Devices.txt` import (multipart) |
| GET | `/api/devices/export` | `Devices.txt` eksport |
| GET/PUT/DELETE | `/api/devices/{id}` | Qurilma CRUD |
| GET/POST | `/api/blacklist` | Qora ro'yxat (qidiruv, status, sahifa) / yaratish |
| GET/DELETE | `/api/blacklist/{id}` | Yozuvni ko'rish / o'chirish (tahrirlash yo'q) |
| POST | `/api/blacklist/{id}/review` | Hodisani "Ko'rib chiqildi" deb belgilash |
| GET | `/api/agent/check/{serial}` | Agent: ruxsat tekshiruvi |
| POST | `/api/agent/blacklist` | Agent: ruxsatsiz qurilma signali |
| POST | `/api/agent/heartbeat` | Agent: aloqa tekshiruvi |
| GET | `/api/software/info` | Agent sozlamalari va shaxsiy token |
| GET | `/api/software/package` | Joriy agent paketi haqida ma'lumot |
| POST/DELETE | `/api/software/package` | Agent `.exe` yuklash / o'chirish (faqat administrator) |
| GET | `/api/software/package/download` | Agent `.exe` faylini yuklab olish |
| POST | `/api/software/token/rotate` | Agent tokenini yangilash |
| GET | `/api/stats` | Bosh sahifa statistikasi |
| GET | `/api/health` | Health check |

Qidiruv barcha asosiy matn maydonlari bo'yicha ishlaydi: seriya raqami,
ishlab chiqaruvchi, model, grif, qurilma turi, sabab, agent nomi, egasi
(login/F.I.Sh).

Swagger'da avtorizatsiya qilish: **Authorize** → `Bearer <access_token>`.
Agent endpointlarida `X-Agent-Token` sarlavhasi ishlatiladi.

---

## 7. Sozlamalar (`.env`)

```ini
APP_NAME=USB Qalqon API
SECRET_KEY=juda-uzun-tasodifiy-kalit
ACCESS_TOKEN_EXPIRE_MINUTES=720
DATABASE_URL=sqlite:///./data/usbqalqon.db
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
ADMIN_FULL_NAME=Tizim administratori
SERVER_URL=http://localhost:8000
```

- `SECRET_KEY` — JWT imzosi uchun; production'da albatta almashtiring.
- `SERVER_URL` — agent paketlariga yoziladigan manzil. Bo'sh bo'lsa so'rov
  manzili olinadi. Tashqi tarmoqda ishlatilsa, masalan
  `http://192.168.1.10:8000` yoki domen yozing.
- `DATABASE_URL` — PostgreSQL uchun:
  `postgresql+psycopg://user:parol@host:5432/usbqalqon`
  (qo'shimcha `psycopg` paketi kerak).

---

## 8. Production uchun

```bash
cd frontend
npm run build          # dist/ hosil bo'ladi
```

Variantlar:

1. **Nginx** orqali: `dist/` ni statik sifatida bering, `/api` ni
   `uvicorn`ga proksi qiling.
2. **Bitta server:** `dist/` ni FastAPI orqali `StaticFiles` bilan bering
   (kerak bo'lsa `app.mount(...)` qo'shiladi).

Backendni production rejimida:

```bash
cd backend
PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Muhim:

- `SECRET_KEY` va `ADMIN_PASSWORD` ni o'zgartiring.
- `CORS_ORIGINS` ga haqiqiy frontend domenini yozing.
- HTTPS ishlatsangiz, `SERVER_URL` ni `https://...` qilib yangilang.
- `data/usbqalqon.db` faylini muntazam zaxiralang.

---

## 9. Foydali buyruqlar

```bash
# Backend loglari bilan ishga tushirish
cd backend
PYTHONPATH=. .venv/bin/uvicorn app.main:app --reload --port 8000

# Demo ma'lumotlar
PYTHONPATH=. .venv/bin/python -m app.seed --demo

# Frontend dev server
cd frontend && npm run dev

# Frontend production build
cd frontend && npm run build
```
