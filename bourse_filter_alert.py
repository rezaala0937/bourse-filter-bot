"""
ربات هشدار فیلتر بورس -> تلگرام
-----------------------------------
این اسکریپت هر N دقیقه اطلاعات بازار (دیده‌بان) رو از TSETMC می‌گیره،
فیلتر ترکیبی رو روی هر نماد چک می‌کنه و اگه match شد، از طریق ربات
تلگرام برای chat_id مشخص‌شده پیام می‌فرسته.

قبل از اجرا:
1) یک ربات تلگرام با @BotFather بسازید و TOKEN رو بگیرید.
2) کاربر مقصد (شماره 09374143100) باید یک بار به ربات شما /start بزنه.
3) با فراخوانی https://api.telegram.org/bot<TOKEN>/getUpdates
   مقدار chat_id همون کاربر رو پیدا کنید و پایین جایگزین کنید.
4) این اسکریپت را روی کامپیوتر/سروری که همیشه روشنه اجرا کنید
   (یا با cron هر 5 دقیقه یک‌بار صدا بزنید).

نکته: ساختار API عمومی TSETMC ممکنه توسط خود سایت تغییر کنه.
اگه درخواست‌ها جواب ندادن، باید هدرها/آدرس را طبق تغییرات سایت
به‌روزرسانی کنید (بخش fetch_market_watch را ببینید).
"""

import os
import sys
import traceback

print("=== شروع اسکریپت ===", flush=True)

try:
    import requests
    print("requests وارد شد", flush=True)
except Exception as e:
    print(f"[خطا در import requests] {e}", flush=True)
    sys.exit(1)

try:
    from tsetmc_api.market_watch import MarketWatch
    print("tsetmc_api وارد شد", flush=True)
except Exception as e:
    print(f"[خطا در import tsetmc_api] {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)

# ====== تنظیمات ======
# این دو مقدار دیگه داخل کد نوشته نمیشن (امن نیست)، بلکه از "Secrets"
# گیت‌هاب خونده میشن که در مرحله بعد تنظیم می‌کنیم.
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
print("توکن و chat_id خونده شدن", flush=True)

# در حالت تشخیصی، به‌جای اجرای فیلتر واقعی، فقط اسم ستون‌های واقعی
# داده‌ها رو برای شما نشون می‌ده تا نگاشت فیلدها رو تأیید/تصحیح کنیم.
DIAGNOSTIC_MODE = os.environ.get("DIAGNOSTIC_MODE", "true").lower() == "true"


def send_telegram_message(text: str) -> None:
    """ارسال پیام به تلگرام از طریق ربات."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    try:
        r = requests.post(url, data=payload, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print(f"[خطا در ارسال تلگرام] {e}")


def fetch_raw_dataframes():
    """
    دریافت داده‌های خام از کتابخانه‌ی tsetmc-api (چهار جدول جدا).
    خروجی: (price_df, stats_df, traders_df, history_df)
    هرکدوم یک pandas.DataFrame هست که ایندکسش کد نماد (InsCode) هست.
    """
    market_watch = MarketWatch()
    price_df = market_watch.get_price_data()
    stats_df = market_watch.get_stats_data()
    traders_df = market_watch.get_traders_type_data()
    history_df = market_watch.get_daily_history_data()
    return price_df, stats_df, traders_df, history_df


def print_diagnostics():
    """
    حالت تشخیصی: فقط اسم ستون‌های واقعی هر جدول رو چاپ می‌کنه تا
    مطمئن بشیم قبل از فعال کردن فیلتر واقعی، نگاشت درستی داریم.
    خروجی این تابع رو (از لاگ GitHub Actions) کپی کن و برای من بفرست.
    """
    print("=== شروع حالت تشخیصی ===", flush=True)
    try:
        print("در حال ساخت MarketWatch...", flush=True)
        market_watch = MarketWatch()
        print("MarketWatch ساخته شد، در حال گرفتن price_data...", flush=True)
        price_df = market_watch.get_price_data()
        print("=== ستون‌های price_data ===", flush=True)
        print(list(price_df.columns), flush=True)

        print("در حال گرفتن stats_data...", flush=True)
        stats_df = market_watch.get_stats_data()
        print("=== ستون‌های stats_data ===", flush=True)
        print(list(stats_df.columns), flush=True)

        print("در حال گرفتن traders_type_data...", flush=True)
        traders_df = market_watch.get_traders_type_data()
        print("=== ستون‌های traders_type_data ===", flush=True)
        print(list(traders_df.columns), flush=True)

        print("در حال گرفتن daily_history_data...", flush=True)
        history_df = market_watch.get_daily_history_data()
        print("=== ستون‌های daily_history_data ===", flush=True)
        print(list(history_df.columns), flush=True)

        print("=== پایان موفق حالت تشخیصی ===", flush=True)
    except Exception as e:
        print(f"[خطا در حالت تشخیصی] {type(e).__name__}: {e}", flush=True)
        traceback.print_exc()


def fetch_market_watch():
    """
    ترکیب چهار جدول خام در یک لیست از دیکشنری با فیلدهایی که
    check_filter انتظار داره.

    ⚠️ نام دقیق ستون‌ها هنوز با یک اجرای تشخیصی (DIAGNOSTIC_MODE)
    تأیید نشده؛ ممکنه بعد از اولین اجرا نیاز به اصلاح این تابع باشه.
    """
    try:
        price_df, stats_df, traders_df, history_df = fetch_raw_dataframes()
        merged = price_df.join(stats_df, how="left", rsuffix="_stats")
        merged = merged.join(traders_df, how="left", rsuffix="_traders")

        symbols = []
        for ins_code, row in merged.iterrows():
            try:
                price_5_days_ago = history_df.loc[ins_code].iloc[4]["pl"]
            except Exception:
                price_5_days_ago = None

            symbols.append({
                "name": row.get("name") or row.get("l18") or str(ins_code),
                "pc": row.get("pc"),
                "py": row.get("py"),
                "pl": row.get("pl"),
                "tvol": row.get("tvol"),
                "bvol": row.get("bvol"),
                "tno": row.get("tno"),
                "buy_i_volume": row.get("Buy_I_Volume"),
                "sell_i_volume": row.get("Sell_I_Volume"),
                "buy_count_i": row.get("Buy_CountI"),
                "sell_count_i": row.get("Sell_CountI"),
                "sell_n_volume": row.get("Sell_N_Volume"),
                "price_5_days_ago": price_5_days_ago,
            })
        return symbols
    except Exception as e:
        print(f"[خطا در دریافت اطلاعات بازار] {e}")
        return []


def check_filter(symbol: dict) -> bool:
    """
    منطق فیلتر ترکیبی که قبلاً نوشتیم، به پایتون ترجمه شده:
    - رشد ۵ روزه زیر ۱۰٪
    - حجم بالای ۱.۵ برابر حجم مبنا
    - قدرت خریدار حقیقی بالای ۱.۵
    - خالص خرید حقیقی بالای ۲۰٪ حجم کل
    - فروش حقوقی بالای ۲۰٪ حجم کل (کد به کد)
    - پایانی بیشتر از دیروز
    - آخرین قیمت >= پایانی
    - تعداد معاملات بالای ۵۰

    ورودی symbol باید کلیدهای زیر رو داشته باشه (باید متناسب با
    داده واقعی که از fetch_market_watch میاد، نگاشت/map بشه):
    pc, py, tvol, bvol, tno, pl,
    buy_i_volume, sell_i_volume, buy_count_i, sell_count_i,
    sell_n_volume, price_5_days_ago
    """
    try:
        growth_5d = (symbol["pc"] - symbol["price_5_days_ago"]) / symbol["price_5_days_ago"] * 100
        if not growth_5d < 10:
            return False

        if not symbol["tvol"] > 1.5 * symbol["bvol"]:
            return False

        buyer_power = (symbol["buy_i_volume"] / symbol["buy_count_i"]) / \
                      (symbol["sell_i_volume"] / symbol["sell_count_i"])
        if not buyer_power > 1.5:
            return False

        net_buy_pct = (symbol["buy_i_volume"] - symbol["sell_i_volume"]) / symbol["tvol"] * 100
        if not net_buy_pct > 20:
            return False

        code_to_code_pct = symbol["sell_n_volume"] / symbol["tvol"] * 100
        if not code_to_code_pct > 20:
            return False

        if not symbol["pc"] > symbol["py"]:
            return False

        if not symbol["pl"] >= symbol["pc"]:
            return False

        if not symbol["tno"] > 50:
            return False

        return True
    except (KeyError, ZeroDivisionError):
        return False


def run_once():
    symbols = fetch_market_watch()
    matched = [s for s in symbols if check_filter(s)]

    if matched:
        names = "\n".join(f"• {s.get('name', 'نامشخص')}" for s in matched)
        message = f"🔔 نمادهای واجد شرایط فیلتر:\n\n{names}"
        send_telegram_message(message)
        print(f"{len(matched)} نماد پیدا شد و پیام ارسال شد.")
    else:
        print("هیچ نمادی این دفعه match نشد.")


if __name__ == "__main__":
    try:
        if DIAGNOSTIC_MODE:
            # اولین بار حتماً با همین حالت اجرا کن تا اسم واقعی ستون‌ها رو ببینیم.
            print_diagnostics()
        else:
            # توجه: اینجا دیگه حلقه‌ی بی‌نهایت نداریم. GitHub Actions خودش
            # طبق زمان‌بندی (cron) این فایل رو هر چند دقیقه یک‌بار اجرا می‌کنه.
            run_once()
    except Exception as e:
        print(f"[خطای کلی و غیرمنتظره] {type(e).__name__}: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)
    finally:
        print("=== پایان اسکریپت ===", flush=True)
   
