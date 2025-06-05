# ─────────────────────────────────────────────────────────────────
# استخدم صورة Python خفيفة مبنيّة على Debian/Ubuntu
FROM python:3.10-slim

# ─────────────────────────────────────────────────────────────────
# خطوة تحديث الحزم وتثبيت الأدوات اللازمة لتشغيل Chromium وChromeDriver
RUN apt-get update && \
    apt-get install -y \
      wget \
      unzip \
      xvfb \
      chromium \
      chromium-driver && \
    rm -rf /var/lib/apt/lists/*

# ─────────────────────────────────────────────────────────────────
# أنشئ مجلّد العمل داخل الحاوية ونسخ ملفات المشروع إليه
WORKDIR /app
COPY . /app

# ─────────────────────────────────────────────────────────────────
# ثبّت متطلبات البايثون من ملف requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# ─────────────────────────────────────────────────────────────────
# عرّف متغيّرات البيئة لمواقع المتصفّح وChromeDriver
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# ─────────────────────────────────────────────────────────────────
# الأمر الافتراضي عند تشغيل الحاوية:
# نفّذ xfvb-run لتشغيل المتصفح في بيئة افتراضية ثم شغّل ملف بوت التليجرام
CMD ["sh", "-c", "xvfb-run --server-args='-screen 0 1024x768x24' python main.py"]
# بدل "main.py" باسم ملف سكربت البوت الخاص بك إن كان مختلفاً.
