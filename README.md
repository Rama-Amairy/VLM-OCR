# VLM-OCR

نظام OCR (استخراج النص من الصور والمستندات) مبني على نموذج رؤية ولغة (VLM) هو **GLM-OCR**، ويعمل محلياً عبر **Ollama**.
يستقبل النظام ملف PDF أو صورة (PNG / JPEG) ويُرجع النص المستخرج بصيغة Markdown.

يحتوي المشروع أيضاً على تجارب لقياس كفاءة النظام قبل الضبط (Tuning) وبعده.

---

## هيكل المشروع

```text
VLM-OCR/
├── src/                      # كود الـ API
│   ├── main.py               # نقطة تشغيل FastAPI
│   ├── config.py             # الإعدادات (تُقرأ من .env)
│   ├── apis/ocr_api.py       # الـ endpoints
│   ├── controllers/          # التحقق من الملف وتحويل PDF إلى صور وتشغيل الـ OCR
│   ├── services/ocr_model.py # الاتصال بنموذج GLM-OCR عبر Ollama
│   ├── preprocessing/        # معالجة الصور قبل الـ OCR (قص الهوامش، تصحيح الميلان، التباين)
│   ├── schemas/              # شكل الاستجابة
│   └── utils/                # أدوات مساعدة (السجل، إعدادات الخطوط، تنظيف Markdown)
├── experiments/
│   ├── configs/              # إعدادات خطوط التجربة line1 / line2 / line3
│   ├── get_dataset.py        # تنزيل بيانات الاختبار
│   ├── run_experiment.py     # تشغيل التجارب
│   └── metrics.py            # حساب CER و WER والعناوين
├── dataset/                  # بيانات الاختبار (تُنشأ تلقائياً، غير مرفوعة على git)
├── .env.example
└── requirements.txt
```

---

## المتطلبات

- Python 3.10 أو أحدث
- [Ollama](https://ollama.com) مثبت ويعمل
- يُفضّل وجود كرت شاشة NVIDIA (GPU) لتسريع النموذج

---

## طريقة التشغيل

### 1. تثبيت المكتبات

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. تنزيل النموذج

```bash
ollama pull glm-ocr
```

### 3. تجهيز ملف الإعدادات

```bash
cp .env.example .env
```

أهم الإعدادات في `.env`:

| الإعداد | المعنى |
| --- | --- |
| `OLLAMA_URL` | عنوان Ollama (الافتراضي `http://localhost:11434`) |
| `OLLAMA_MODEL` | اسم النموذج (`glm-ocr`) |
| `OCR_PROMPT` | الأمر المُرسل للنموذج |
| `OLLAMA_NUM_CTX` | حجم السياق (اختياري) |
| `PDF_DPI` | دقة تحويل صفحات PDF إلى صور |
| `MAX_IMAGE_SIDE` | أكبر طول لضلع الصورة قبل إرسالها للنموذج |
| `MAX_FILE_SIZE_MB` / `MAX_PAGES` | الحد الأقصى لحجم الملف وعدد الصفحات |

### 4. تشغيل الخادم

```bash
uvicorn src.main:app
```

بعد التشغيل يمكن فتح صفحة التجربة التفاعلية على:
`http://localhost:8000/docs`

### 5. التأكد من أن النموذج يعمل على الـ GPU

```bash
ollama ps
```

يجب أن يظهر `100% GPU`.

---

## الـ API

| الطلب | الوظيفة |
| --- | --- |
| `GET /api/health` | يتأكد أن Ollama والنموذج متاحان |
| `GET /api/lines` | يعرض خطوط التجربة المتاحة وخطوات المعالجة المسبقة |
| `POST /api/ocr` | يرفع ملف ويُرجع النص |

ملفات PDF تُحوَّل أولاً إلى صور صفحات، أما الصور فتُستخدم كما هي.

### أمثلة

استخراج النص بالإعدادات الافتراضية:

```bash
curl -X POST http://localhost:8000/api/ocr -F "file=@page.png"
```

استخدام إعدادات خط تجربة معيّن:

```bash
curl -X POST http://localhost:8000/api/ocr -F "file=@doc.pdf" -F "line=line2_best"
```

تغيير إعدادات محددة أو إضافة معالجة مسبقة للصورة:

```bash
curl -X POST http://localhost:8000/api/ocr \
  -F "file=@page.jpg" \
  -F "max_image_side=1800" \
  -F "preprocessing=deskew,contrast"
```

ترتيب الأولوية: القيم المُرسلة في الطلب ← ثم إعدادات الخط (`line`) ← ثم القيم الافتراضية في `.env`.

الحقول المتاحة: `line`، `prompt`، `pdf_dpi`، `max_image_side`، `num_ctx`، `preprocessing`.

---

## التجارب

الهدف قياس كفاءة النظام قبل الضبط وبعده، عبر ثلاثة خطوط:

| الخط | الوصف |
| --- | --- |
| **line1** | الإعداد الابتدائي: prompt طويل، بدون معالجة مسبقة |
| **line2** | تجربة كل عامل لوحده فوق line1 (`max_image_side`، `num_ctx`، `prompt`)، ثم دمج أفضل القيم في `line2_best` |
| **line3** | `line2_best` + معالجة مسبقة للصورة (`crop_margins`، `deskew`، `contrast`): كل خطوة لوحدها، ثم دمج الخطوات المفيدة في `line3_best` |

الإعدادات موجودة في [experiments/configs/](experiments/configs/)، والملفان `line2_best.json` و `line3_best.json` يُنشآن تلقائياً بعد تشغيل line2 و line3.

### البيانات

التجارب تعمل على **صور فقط**، من مجموعة بيانات [OmniDocBench](https://huggingface.co/datasets/opendatalab/OmniDocBench) (صفحات إنجليزية، نصها المرجعي مُراجَع يدوياً).
يتم أخذ 20 صفحة: 14 للتدريب (train) و 6 للاختبار (test).

النظام يدعم PDF أيضاً، لكن مجموعة البيانات لا تحتوي ملفات PDF، لذلك مسار PDF غير داخل في القياس، وإعداد `pdf_dpi` لا يُضبط في line2 (فقط `max_image_side`).

### خطوات تشغيل التجارب

```bash
# 1. تنزيل البيانات إلى مجلد dataset/
python -m experiments.get_dataset

# 2. الضبط على صفحات التدريب (ينتج line2_best)
python -m experiments.run_experiment --line line2

# 3. المعالجة المسبقة فوق line2_best (ينتج line3_best)
python -m experiments.run_experiment --line line3

# 4. المقارنة النهائية على صفحات الاختبار
python -m experiments.run_experiment --line line1      --split test
python -m experiments.run_experiment --line line2_best --split test
python -m experiments.run_experiment --line line3_best --split test
```

النتائج تُحفظ في `experiments/results/<الخط>/<split>/`:

- `summary.csv`: ملخص كل تشغيل
- `details.csv`: نتيجة كل صفحة
- ملفات `.md`: النص الذي أخرجه النموذج لكل صفحة

### طريقة التقييم

- تُرسل صورة الصفحة كاملة للنموذج ويُطلب منه نص عادي (plain text).
- يُقارن الناتج بالنص المرجعي باستخدام:
  - **CER**: نسبة الخطأ على مستوى الحروف
  - **WER**: نسبة الخطأ على مستوى الكلمات
- أعمدة إضافية: نسبة العناوين الرئيسية التي وُجدت في الناتج (`headings_found`)، والوقت.

هذا التقييم يقيس جودة الـ OCR (مع تأثير بسيط لترتيب القراءة)، ولا يقيّم تنسيق Markdown أو الجداول.
النص المرجعي لا يحتوي على الترويسة والتذييل وأرقام الصفحات، لذلك تظهر هذه كخطأ إضافي بسيط في CER.
