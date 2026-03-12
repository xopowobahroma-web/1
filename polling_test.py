import telebot

# Токен вашего бота
BOT_TOKEN = '8371508391:AAF2r-M627DkVdkR10uPm4p3Dqvokmyzpxs'
bot = telebot.TeleBot(BOT_TOKEN)

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Я бот, работаю через polling!")

# Обработчик всех текстовых сообщений
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, f"Ты написал: {message.text}")

print("Бот запущен в режиме polling. Нажми Ctrl+C для остановки.")
bot.infinity_polling()