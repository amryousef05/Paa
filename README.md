# Personal Action Agent — Backend Core (MVP)

## التشغيل
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # املأ المفاتيح، ثم: set -a; source .env; set +a
uvicorn main:app --reload
```

## التجربة
```bash
curl -X POST localhost:8000/chat -H 'content-type: application/json' \
  -d '{"user_id":"u1","text":"عايز ملعب بادل في التجمع الخميس بالليل"}'
# لو رجع pending_actions:
curl -X POST localhost:8000/confirm -H 'content-type: application/json' \
  -d '{"user_id":"u1","action_id":"<id>","approved":true}'
```

## المعمارية
- `agent.py`: حلقة Function Calling يدوية. أدوات القراءة تتنفذ فورًا، وأدوات التنفيذ تتحول لـ `pending_actions` ولا تعمل إلا بعد `/confirm`.
- `tools.py`: Serper + Places شغالين فعليًا. واتساب وVapi جاهزين للربط. الحجز والتقويم والدفع **STUB** عبر n8n webhooks.
- `prompts.py`: شخصية الوكيل بالمصري وقواعد الأمان.

## المتبقي قبل الإطلاق
1. استبدال `SESSIONS` في الذاكرة بـ Redis/Postgres.
2. Google OAuth لكل مستخدم (Calendar).
3. قوالب واتساب معتمدة من Meta (الرسالة الأولى للمكان لازم Template).
4. Vapi assistant بصوت عربي مصري، واختباره على مكالمات حقيقية قبل الاعتماد عليه.
5. مصادقة المستخدمين (JWT) وrate limiting.
6. اتفاقاتك مع الملاعب/المتاجر لعمولات الإحالة ومصدر بيانات التوافر (أكبر عنق زجاجة في المنتج).
