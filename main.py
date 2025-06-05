# -*- coding: utf-8 -*-
import logging
import time
from typing import Dict

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# 1) إعداد السجلّات (logging)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 2) ضع توكن بوت التلجرام هنا:
TELEGRAM_TOKEN = '6653730137:AAGmEno_OEnvw1oC39jB69is9hO22pczhdE'

# 3) مسار Chromedriver إذا لم يكن في PATH:
CHROMEDRIVER_PATH = '/path/to/chromedriver'  # عدّل هذا المسار حسب مكان chromedriver عندك

# 4) دالة لإنشاء ChromeDriver مع بعض الإعدادات (Headless اختياري)
def create_chrome_driver(headless: bool = True) -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--window-size=1200x800')
    # (يمكن إضافة أو تعديل الـ user-agent إن لزمّ)
    options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) ' +
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36'
    )
    service = ChromeService(executable_path=CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# 5) دالة مساعدة لتسجيل الخطأ والرد على المستخدم
async def send_error(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    logger.error(text)
    await update.message.reply_text(f"❌ خطأ: {text}")

# 6) الأمر /start لبدء المحادثة
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "مرحباً! أرسل لي رابط التسجيل الذي وصلك على بريدك الإلكتروني.\n"
        "سأستخدم Selenium لفتح الرابط والضغط على الزر الأزرق تلقائيًا، ثم أرسلك رسالة تطلب منك \"رمز الأمان\"."
    )

# 7) عند استقبال الرابط (أي رسالة نصية تبدأ بـ http أو https)
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text.strip()
    if not (url.startswith('http://') or url.startswith('https://')):
        await send_error(update, context, "الرابط غير صالح. تأكد أنه يبدأ بـ http أو https.")
        return

    await update.message.reply_text("🔄 جارٍ فتح الرابط بالمتصفح (Selenium) والضغط على الزر الأزرق...")

    try:
        # 7.1) إنشاء WebDriver جديد
        driver = create_chrome_driver(headless=True)

        # 7.2) ننتقل إلى الرابط
        driver.get(url)

        # 7.3) ننتظر حتى يظهر الزر الأزرق الخاص بـ “إرسال رمز الأمان”
        #      عادةً زر “أرسل الرمز إلى البريد الإلكتروني” في هذه المرحلة يكون input أو button بعلامات معينة.
        #      في هذه الأمثلة سنبحث عن زر به نص عربي “إرسال رمز الأمان” أو نستخدم CSS/XPATH التقريبي.
        #
        #      مثال عام: زر الزر الأزرق قد يكون مكتوب فيه كلمة “إرسال” أو “Next” أو قد يكون زرًا بدون نص لكن بلون أزرق.
        #      نستخدم انتظار حتى يظهر عنصر button أو input من النوع submit ضمن حقل معين.
        #
        wait = WebDriverWait(driver, 20)

        # 7.4) مثال: نبحث زر button فيه نص عربي يحتوي “إرسال” ضمن الصفحة:
        try:
            button_send = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(), 'إرسال') or contains(text(), 'Send')]")
                )
            )
        except:
            # إذا لم نجده في النص العربي/الإنجليزي، نجرب البحث بحسب class أو attribute شائع
            button_send = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button[type='submit']")
                )
            )

        # 7.5) ننقر الزر الأزرق
        button_send.click()
        logger.info("Clicked the blue button (أرسل رمز الأمان).")

        # 7.6) نحفظ الـ driver في user_data حتى نستخدمه عندما يصل الرمز
        context.user_data['selenium_driver'] = driver
        context.user_data['stage'] = 'awaiting_code'

        # 7.7) نُعلِم المستخدم بأننا ننتظر منه إرسال الرمز
        await update.message.reply_text(
            "✅ لقد نقرت زر إرسال الرمز أليًا.\n"
            "🕐 الآن تأكَّد من بريدك، وانسخ \"رمز الأمان\" الذي وصلك.\n"
            "ثم أرسله إليّ هنا في رسالة منفصلة."
        )

    except Exception as e:
        # إذا فشل أي شيء، نعطي رسالة خطأ للمستخدم، ونتأكد من إغلاق الـ driver إن وُجد
        await send_error(update, context, f"لم أتمكن من فتح الرابط أو النقر على الزر: {e}")
        if 'selenium_driver' in context.user_data:
            try:
                context.user_data['selenium_driver'].quit()
            except:
                pass
        context.user_data.clear()

# 8) عند استقبال الرمز (any text بعد الحلقة الأولى)
async def handle_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()

    # نتأكد أن المرحلة الصحيحة “awaiting_code” ما زالت مستمرة
    if context.user_data.get('stage') != 'awaiting_code' or 'selenium_driver' not in context.user_data:
        # لم نكن في مرحلة انتظار الرمز، نتجاهل الرسالة
        return

    driver: webdriver.Chrome = context.user_data['selenium_driver']
    code = text  # نص الرسالة هو رمز الأمان الذي أدخله المستخدم

    await update.message.reply_text("🔄 جارٍ إدخال رمز الأمان في الصفحة...")

    try:
        # 8.1) نبحث حقل إدخال الكود (عادةً input من النوع text أو tel)
        wait = WebDriverWait(driver, 20)

        # مثال: غالبًا الحقل يكون input[name="security_code"] أو ما شابه
        # يعتمد على شكل صفحة إنستاجرام الحالية. سنجرب XPath يحتوي على كلمة “code”:
        input_code = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//input[contains(@name, 'code') or contains(@aria-label, 'security code')]")
            )
        )

        # 8.2) ندخل الرمز
        input_code.clear()
        input_code.send_keys(code)

        # 8.3) نضغط زر التأكيد (button أو input[type=submit] الذي يلي الحقل)
        try:
            btn_confirm = driver.find_element(By.XPATH, "//button[contains(text(), 'التالي') or contains(text(), 'Confirm') or contains(text(), 'Continue')]")
        except:
            btn_confirm = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")

        btn_confirm.click()
        logger.info("Clicked Confirm after entering code.")

        # 8.4) ننتظر حتى يتم التحميل والإنتقال إلى صفحة الحساب أو حتى ظهور خطأ
        #       على سبيل المثال، ننتظر ظهور عنصر يدل على أن العملية نجحت مثل وجود input لإدخال كلمة المرور الجديدة 
        #       أو إعادة توجيه إلى الصفحة الرئيسية.
        time.sleep(5)  # ننتظر لبضع ثوانٍ للتأكّد من استجابة السيرفر

        # 8.5) جلب الكوكيز من الـ driver (sessionid و csrftoken)
        cookies = driver.get_cookies()  # قائمة dict فيها كل الكوكيز
        cookie_dict: Dict[str, str] = {}
        for ck in cookies:
            cookie_dict[ck['name']] = ck['value']

        # 8.6) نتأكّد أن الكوكيز المطلوبة موجودة
        needed = {}
        for key in ('csrftoken', 'sessionid'):
            if key in cookie_dict:
                needed[key] = cookie_dict[key]

        if not needed:
            # إذا لم نجد الكوكيز المطلوبة
            await update.message.reply_text(
                "❌ لم أتمكن من العثور على csrftoken أو sessionid بعد إدخال الكود.\n"
                "ربما فشل التحقق، تأكد من الرمز وحاول مجددًا."
            )
            # لا نغلق الـ driver كي يتيح للمستخدم إعادة إرسال الرمز الصحيح.
            return

        # 8.7) إذا وجدنا الكوكيز:
        result_lines = [f"{k} = {v}" for k, v in needed.items()]
        await update.message.reply_text(
            "✅ تم التحقق بنجاح! إليك قيم الكوكيز:\n\n" + "\n".join(result_lines)
        )

        # 8.8) نُغلق الـ driver وننظف بيانات المستخدم
        driver.quit()
        context.user_data.clear()

    except Exception as e:
        await send_error(update, context, f"حدث خطأ أثناء إدخال الرمز أو جلب الكوكيز: {e}")
        try:
            driver.quit()
        except:
            pass
        context.user_data.clear()

# 9) الدالة الرئيسية لبدء البوت
def main() -> None:
    # 9.1) بناء تطبيق تلجرام
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # 9.2) إضافة الهاندلرات
    app.add_handler(CommandHandler("start", start))

    # عندما يرسل المستخدم رابط (http/https) بمعزل عن أمر:
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & (filters.Regex(r"^https?://")),
            handle_link
        )
    )

    # عندما يرسل المستخدم أي نص آخر (قد يكون رمز الأمان):
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & ~filters.Regex(r"^https?://"),
            handle_code
        )
    )

    # 9.3) تشغيل البوت
    app.run_polling()
    logger.info("Bot started. Listening for messages...")

if __name__ == '__main__':
    main()
