import sqlite3
from datetime import datetime, timedelta
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import ReplyKeyboardRemove

# الاتصال بقاعدة البيانات وإنشاء جدول
conn = sqlite3.connect('subjects.db', check_same_thread=False)
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS subjects (
    user_id TEXT,
    subject_name TEXT,
    reminder_date TEXT
)
''')
conn.commit()

# قائمة بتوكنات البوتات
tokens = [
    "7831639949:AAGAdo5LdTvjNcxie8ihTdl8YXh4Rr-plL4",
    "توكن_بوت_2",
    "توكن_بوت_3",
    "توكن_بوت_4",
    "توكن_بوت_5",
    "توكن_بوت_6",
    "توكن_بوت_7",
    "توكن_بوت_8",
    "توكن_بوت_9",
    "توكن_بوت_10"
]

# إضافة مادة جديدة وحفظها في قاعدة البيانات تلقائيًا
def add_subject_to_db(user_id, subject_name, reminder_dates):
    for reminder_date in reminder_dates:
        c.execute("INSERT INTO subjects (user_id, subject_name, reminder_date) VALUES (?, ?, ?)",
                  (user_id, subject_name, reminder_date.strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()

# إضافة مادة جديدة مع الفترات الافتراضية
def add_subject(name, user_id, job_queue):
    today = datetime.now()

    def set_reminder_time(day_offset):
        reminder_date = today + timedelta(days=day_offset)
        return reminder_date.replace(hour=4, minute=0, second=0, microsecond=0)

    reminders = [set_reminder_time(i) for i in [1, 4, 11, 25, 55, 85, 115, 145, 175, 205, 235, 265, 295, 325, 355]]

    add_subject_to_db(user_id, name, reminders)

    for reminder_time in reminders:
        job_queue.run_once(remind_user, reminder_time, context={'user_id': user_id, 'subject_name': name})

# تذكير المستخدم بمراجعة المادة
def remind_user(context):
    job_data = context.job.context
    user_id = job_data['user_id']
    subject_name = job_data['subject_name']
    context.bot.send_message(chat_id=user_id, text=f"حان الوقت لمراجعة: {subject_name}")

# إضافة مادة باستخدام الأمر A
def add_subject_command(update, context):
    user_id = str(update.effective_chat.id)
    text = update.message.text.split()

    if len(text) < 2:
        update.message.reply_text("يرجى إدخال اسم المادة. مثال: A الرياضيات", reply_markup=ReplyKeyboardRemove())
        return

    subject_name = ' '.join(text[1:])
    add_subject(subject_name, user_id, context.job_queue)
    update.message.reply_text(f"تم إضافة المادة {subject_name} بنظام التكرار المتباعد.", reply_markup=ReplyKeyboardRemove())

# إضافة مادة بفترات مخصصة باستخدام الأمر L
def add_subject_custom_command(update, context):
    user_id = str(update.effective_chat.id)
    text = update.message.text

    # التحقق من وجود الأقواس والفترات بداخلها
    if '(' not in text or ')' not in text:
        update.message.reply_text("يرجى إدخال الفترات داخل قوسين. مثال: L الرياضيات (2 7 14 30)", reply_markup=ReplyKeyboardRemove())
        return

    # تقسيم النص للحصول على اسم المادة والفترات داخل القوس
    try:
        subject_name = text.split(' ')[1]
        periods_str = text[text.index('(')+1:text.index(')')].strip()
        custom_periods = list(map(int, periods_str.split()))
    except:
        update.message.reply_text("حدث خطأ في معالجة الفترات. يرجى التأكد من إدخال الأرقام بشكل صحيح داخل الأقواس.", reply_markup=ReplyKeyboardRemove())
        return

    add_subject_with_custom_periods(subject_name, user_id, context.job_queue, custom_periods)
    update.message.reply_text(f"تم إضافة المادة {subject_name} بفترات مخصصة: {', '.join(map(str, custom_periods))} أيام.", reply_markup=ReplyKeyboardRemove())

# عرض قائمة المواد والمراجعات باستخدام الأمر M
def reviews(update, context):
    user_id = str(update.effective_chat.id)
    today = datetime.now().strftime('%Y-%m-%d')
    c.execute("SELECT subject_name, reminder_date FROM subjects WHERE user_id=? ORDER BY reminder_date ASC", (user_id,))
    subjects = c.fetchall()

    if not subjects:
        update.message.reply_text("لا توجد مواد مضافة.", reply_markup=ReplyKeyboardRemove())
        return

    response = "قائمة المواد والمراجعات القادمة:\n"
    for subject_name, reminder_date in subjects:
        reminder_day = reminder_date.split(' ')[0]

        if reminder_day == today:
            response += f"✅ المادة: {subject_name} - المراجعة اليوم: {reminder_date}\n"
        else:
            response += f"المادة: {subject_name} - المراجعة القادمة في: {reminder_date}\n"

    update.message.reply_text(response, reply_markup=ReplyKeyboardRemove())

# عرض قائمة مراجعات اليوم فقط باستخدام الأمر E
def today_reviews_command(update, context):
    user_id = str(update.effective_chat.id)
    today = datetime.now().strftime('%Y-%m-%d')
    c.execute("SELECT subject_name, reminder_date FROM subjects WHERE user_id=? AND reminder_date LIKE ? ORDER BY reminder_date ASC", (user_id, f'{today}%'))
    subjects = c.fetchall()

    if not subjects:
        update.message.reply_text("لا توجد مراجعات لليوم.", reply_markup=ReplyKeyboardRemove())
        return

    response = "قائمة مراجعات اليوم:\n"
    for subject_name, reminder_date in subjects:
        response += f"✅ المادة: {subject_name} - المراجعة في: {reminder_date}\n"

    update.message.reply_text(response, reply_markup=ReplyKeyboardRemove())

# حذف مادة باستخدام الأمر D
def delete_subject_command(update, context):
    user_id = str(update.effective_chat.id)
    text = update.message.text.split()

    if len(text) < 2:
        update.message.reply_text("يرجى إدخال اسم المادة. مثال: D الرياضيات", reply_markup=ReplyKeyboardRemove())
        return

    subject_name = ' '.join(text[1:])
    
    # حذف المادة من قاعدة البيانات والتحقق من النجاح
    rows_deleted = c.execute("DELETE FROM subjects WHERE user_id = ? AND subject_name = ?", (user_id, subject_name)).rowcount
    conn.commit()

    if rows_deleted > 0:
        update.message.reply_text(f"تم حذف المادة {subject_name}.", reply_markup=ReplyKeyboardRemove())
    else:
        update.message.reply_text(f"لم يتم العثور على المادة {subject_name}.", reply_markup=ReplyKeyboardRemove())

# إضافة الردود التوضيحية عند الخطأ
def incorrect_a(update, context):
    update.message.reply_text("A [أسم المادة]")

def incorrect_d(update, context):
    update.message.reply_text("D [أسم المادة]")

# بدء البوت باستخدام الأمر Start مع رسالة الترحيب المعدلة
def start_command(update, context):
    welcome_message = (
        "مرحباً بك في REPETI التَجريبي!\n\n"
        "• قبل استخدام البوت يجب عليك أن تشاهد فيديو شرح استخدامه.\n\n"
        "أوامر البوت:\n\n"
        "• لإنشاء مراجعة بنظام التكرار المتباعد: A\n\n"
        "• لعرض قائمة مراجعاتي: M\n\n"
        "• لعرض قائمة مراجعات اليوم: E\n\n"
        "• لحذف مراجعة: D\n\n"
        "- إذا واجهتك أيّ مشكلة تواصل مع [@REPETIHELPEBOT]"
    )
    update.message.reply_text(welcome_message, reply_markup=ReplyKeyboardRemove())

# إعداد البوتات باستخدام Updater
for token in tokens:
    updater = Updater(token, use_context=True)
    dispatcher = updater.dispatcher

    # معالجة الأوامر
    dispatcher.add_handler(CommandHandler("start", start_command))  # معالجة الأمر /start
    dispatcher.add_handler(MessageHandler(Filters.text & Filters.regex('^A$'), incorrect_a))
    dispatcher.add_handler(MessageHandler(Filters.text & Filters.regex('^A '), add_subject_command))
    dispatcher.add_handler(MessageHandler(Filters.text & Filters.regex('^D$'), incorrect_d))
    dispatcher.add_handler(MessageHandler(Filters.text & Filters.regex('^D '), delete_subject_command))
    dispatcher.add_handler(MessageHandler(Filters.text & Filters.regex('^M$'), reviews))  # إضافة معالجة لأمر M
    dispatcher.add_handler(MessageHandler(Filters.text & Filters.regex('^E$'), today_reviews_command))  # إضافة معالجة لأمر E

    updater.start_polling()

updater.idle()