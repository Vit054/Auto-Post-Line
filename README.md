# Auto Post Line — Morning Greeting 🌼

ส่งภาพ **"Good Morning"** ดอกไม้สีตามวัน (ตามความเชื่อสีมงคลไทย) เข้า LINE ทุกเช้า **07:00 น. (เวลาไทย)** อัตโนมัติ
**ภาพไม่ซ้ำกันทุกวัน** (seed ผูกกับวันที่) ส่วนข้อความทักทายภาษาอังกฤษสร้างด้วย DeepSeek (ซ้ำได้)

| วัน | สีมงคล | วัน | สีมงคล |
|-----|--------|-----|--------|
| จันทร์ | เหลือง | ศุกร์ | ฟ้า |
| อังคาร | ชมพู | เสาร์ | ม่วง |
| พุธ | เขียว | อาทิตย์ | แดง |
| พฤหัสบดี | ส้ม | | |

## วิธีทำงาน

```
07:00 ไทย → GitHub Actions (cron)
   ├─ generate.py : DeepSeek → ข้อความ + Pillow วาดภาพดอกไม้ (seed = วันที่ → ไม่ซ้ำ)
   ├─ commit ภาพเข้า repo (ได้ public URL ผ่าน raw.githubusercontent.com)
   └─ send.py     : LINE Messaging API multicast → userId ที่ตั้งไว้
```

- `config.py` — ธีมสีประจำวัน
- `generate.py` — สร้างภาพ + ข้อความ บันทึก `images/<วันที่>.jpg` (ภาพไม่ซ้ำเพราะ seed = วันที่)
- `send.py` — ส่งภาพเข้า LINE
- `.github/workflows/morning.yml` — ตั้งเวลา + ขั้นตอนทั้งหมด

## การตั้งค่า (ทำครั้งเดียว)

### 1) สร้าง LINE Official Account + Messaging API
1. สร้าง OA ที่ <https://manager.line.biz> → ผูกกับ **Messaging API channel** ที่ <https://developers.line.biz>
2. ในช่อง Messaging API → คัดลอก **Channel access token (long-lived)**

### 2) หา userId ของผู้รับ
userId ไม่แสดงใน OA Manager — ต้องดึงจาก **webhook event** ตอนผู้ใช้ทักหา OA
(เปิด Webhook ใน Messaging API แล้ว log ค่า `events[].source.userId`)
ผู้รับทุกคนต้อง **เพิ่ม OA เป็นเพื่อน** ก่อน ถึงจะ multicast ได้

### 3) ตั้ง GitHub Secrets
ไปที่ repo → **Settings → Secrets and variables → Actions → New repository secret** เพิ่ม 3 ตัว:

| Secret | ค่า |
|--------|-----|
| `LINE_CHANNEL_ACCESS_TOKEN` | token จากข้อ 1 |
| `LINE_USER_IDS` | userId ผู้รับ คั่นด้วย `,` เช่น `Uaaa...,Ubbb...` |
| `DEEPSEEK_API_KEY` | key จาก <https://platform.deepseek.com> (ถ้าไม่ใส่ จะใช้ข้อความสำรองในเครื่อง) |

### 4) ทดสอบ
repo → **Actions → Morning LINE Greeting → Run workflow** เพื่อยิงทันทีโดยไม่ต้องรอ 7 โมง

## รันในเครื่อง (ลองดูภาพก่อนส่ง)

```bash
pip install -r requirements.txt
# (ไม่บังคับ) set DEEPSEEK_API_KEY ก่อน
python generate.py        # สร้างภาพไว้ใน images/
```

## หมายเหตุ
- GitHub Actions cron อาจช้ากว่าเวลาที่ตั้งไว้ ~5–15 นาที ในช่วงที่ระบบมีงานเยอะ
- เก็บภาพย้อนหลังไว้ 14 วัน (ลบของเก่าอัตโนมัติ) เพื่อไม่ให้ repo โตเกินไป
- LINE ต้องการ URL รูปแบบ HTTPS — โปรเจกต์นี้ใช้ `raw.githubusercontent.com` ของรูปที่ commit แล้ว
