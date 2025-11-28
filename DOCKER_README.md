# Docker Setup for Business Management System

Bu loyihani Docker yordamida ishga tushirish uchun quyidagi ko'rsatmalarga amal qiling.

## Tez ishga tushirish

Agar sizda Docker va Docker Compose o'rnatilgan bo'lsa:

```bash
./docker-run.sh
```

Bu skript sizga interaktiv menyu taqdim etadi.

## Qo'lda ishga tushirish

## Talablar

- Docker
- Docker Compose

## Ishga tushirish

### 1. Environment faylini yaratish

```bash
cp .env.example .env
```

`.env` faylini ochib, kerakli qiymatlarni kiriting:
- `SECRET_KEY` - Flask uchun maxfiy kalit
- `JWT_SECRET_KEY` - JWT tokenlar uchun maxfiy kalit
- Boshqa konfiguratsiya parametrlar

### 2. Docker konteynerlarini ishga tushirish

**Ishlab chiqish rejimi uchun:**
```bash
docker-compose up --build
```

**Fond rejimi uchun:**
```bash
docker-compose up -d --build
```

### 3. Brauzerda ochish

Ilova `http://localhost:5000` manzilida ishlaydi.

## Docker fayllarining tavsifi

- `Dockerfile` - Python ilovasi uchun konteyner konfiguratsiyasi
- `docker-compose.yml` - Asosiy xizmatlar (web, redis)
- `docker-compose.override.yml` - Ishlab chiqish uchun sozlamalar
- `entrypoint.sh` - Konteyner ishga tushish skripti
- `.dockerignore` - Docker build kontekstidan chiqarib tashlanadigan fayllar

## Ma'lumotlar bazasi

- SQLite ma'lumotlar bazasi `data/biznes.db` faylida saqlanadi
- Docker volume yordamida ma'lumotlar saqlanib qolinadi

## Redis

- Sessiyalar va kesh uchun ishlatiladi
- `redis://redis:6379/0` manzilida ishlaydi

## To'xtatish

```bash
docker-compose down
```

## Ma'lumotlarni tozalash

Barcha ma'lumotlarni (ma'lumotlar bazasi, volume) o'chirish uchun:

```bash
docker-compose down -v
```

## Troubleshooting

### Port konflikti
Agar 5000 port band bo'lsa, `docker-compose.override.yml` faylida portni o'zgartiring:

```yaml
ports:
  - "8000:5000"
```

### Ma'lumotlar bazasi xatoliklari
Agar ma'lumotlar bazasi bilan bog'liq xatolik yuz bersa:

```bash
docker-compose down -v
docker-compose up --build
```

### Loglarni ko'rish
```bash
docker-compose logs -f web
```
