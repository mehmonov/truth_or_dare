# Truth or Dare Telegram Bot

Bu Telegram bot ikki kishilik Truth or Dare o'yinini o'ynash uchun yaratilgan.

## O'rnatish

1. Repositoryni clone qiling
2. Kerakli kutubxonalarni o'rnating:
```bash
pip install -r requirements.txt
```
3. `.env.example` faylini `.env` ga nusxalang va Telegram bot tokenini kiriting
4. Botni ishga tushiring:
```bash
python main.py
```

## O'yin qoidalari

1. Birinchi o'yinchi `/create_game` buyrug'ini yuboradi
2. Ikkinchi o'yinchi `/join_game` buyrug'i orqali o'yinga qo'shiladi
3. O'yinchilar navbat bilan Truth yoki Dare tanlashadi
4. O'yinni tugatish uchun `/end_game` buyrug'ini yuboring

## Bot buyruqlari

- `/start` - Botni ishga tushirish
- `/create_game` - Yangi o'yin yaratish
- `/join_game` - Mavjud o'yinga qo'shilish
- `/end_game` - O'yinni tugatish
