import asyncio
import os
import json  # Для работы с файлами JSON
from twitchio.ext import commands

# Настройки (берём из Secrets)
CHANNEL_NAME = os.getenv("CHANNEL_NAME")  # Имя канала стримера
BOT_NICK = os.getenv("BOT_NICK")  # Имя аккаунта бота
OAUTH_TOKEN = os.getenv("OAUTH_TOKEN")  # Ваш OAuth-токен
CLIENT_ID = os.getenv("CLIENT_ID")  # Client ID из Twitch Developer Portal
API_OAUTH_TOKEN = os.getenv("API_OAUTH_TOKEN")  # Access Token для Twitch API

# Ключевые слова и их веса
HIGH_IMPACT_KEYWORDS = [
    "тильт", "тильтит", "тильтить", "тильтанул", "нытик", "ноет", "ныть",
    "нюня", "клоун", "сгорел", "пригорел", "бедный", "бедолага", "бедняга",
    "зажрался", ":clown_face:", "терпи", "плачет", "нытик2к", "заебал", "таблетки", "тютя", "ТЮТЯ МАТЮТЯ", "крыса", "крыса2к"
]
OTHER_KEYWORDS = [
    "еблан", "лох", "хуесос", "долбоеб", "нахуя",
    "нахуй", "пиздец", "лошара", "додик", "далбаеб", "долбоёб", "долбоеб",
    "долбоёб", "ебанат", "ебанутый", "идиот", "алкаш",
    "ебаный", "уебан", "мудак", "огр", "огр2к", "шрек", "чудовище", "чудик",
    "ублюдок", "придурок", "дурак", "дурачок", "тварь", "пиздабол",
    "сосешь", "хуйлан", "хуйло", "спермоглот", "лузер",
    "придурок", "нах", "бомж", "бомжара", "бомж2к",
    "идиотина", "быдло", "быдло2к", "пес", "ПЬЯНЬ", "CoolStoryBob"
]

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=OAUTH_TOKEN,
            client_id=CLIENT_ID,
            nick=BOT_NICK,
            prefix="!",
            initial_channels=[CHANNEL_NAME]
        )
        self.load_state()  # Загружаем состояние из файла
        self.total_messages = 0  # Общий счётчик всех сообщений
        self.last_critical_warning_time = 0  # Время последнего критического предупреждения
        self.time_until_auto_message = 300  # Время до автоматического сообщения (в секундах, теперь 5 минут)
        self.last_tilter_command_time = 0  # Время последнего использования команды !тильт

    def load_state(self):
        """Загружает уровень тильта из файла."""
        try:
            with open("state.json", "r") as file:
                content = file.read()
                if content.strip():  # Проверяем, что файл не пустой
                    data = json.loads(content)
                    self.internal_tilt_chance = data.get("tilt_chance", 0)  # Загружаем tilt_chance или 0
                else:
                    self.internal_tilt_chance = 0  # Если файл пустой, начинаем с 0
        except FileNotFoundError:
            self.internal_tilt_chance = 0  # Если файл не найден, начинаем с 0

    def save_state(self):
        """Сохраняет уровень тильта в файл."""
        with open("state.json", "w") as file:
            json.dump({"tilt_chance": self.internal_tilt_chance}, file)

    async def event_ready(self):
        print(f"Бот {self.nick} подключен к чату {CHANNEL_NAME}")
        # Запускаем задачу для автоматических уведомлений
        asyncio.create_task(self.auto_tilt_message())
        # Запускаем задачу для проверки статуса стрима
        asyncio.create_task(self.check_stream_status())
        # Запускаем задачу для отчета времени до автоматического сообщения
        asyncio.create_task(self.report_time_until_auto_message())

    async def event_message(self, message):
        # Игнорируем сообщения от самого бота
        if message.echo:
            return
        # Игнорируем команды (сообщения, начинающиеся с "!")
        if message.content.startswith("!"):
            await self.handle_commands(message)
            return
        # Увеличиваем общий счётчик сообщений
        self.total_messages += 1
        # Проверяем, содержит ли сообщение ключевые слова
        content = message.content.lower()
        if any(keyword in content for keyword in HIGH_IMPACT_KEYWORDS):
            self.internal_tilt_chance += 2  # Увеличиваем внутренний уровень тильта на 2%
        elif any(keyword in content for keyword in OTHER_KEYWORDS):
            self.internal_tilt_chance += 1  # Увеличиваем внутренний уровень тильта на 1%
        # Если прошло 100 сообщений без ключевых слов, уменьшаем уровень тильта на 1%
        if self.total_messages % 100 == 0:
            self.internal_tilt_chance = max(0, self.internal_tilt_chance - 1)  # Уменьшаем уровень тильта, но не ниже 0%
        # Сохраняем состояние после каждого изменения
        self.save_state()
        # Выводим текущий внутренний уровень тильта в консоль
        print(f"Текущий внутренний уровень тильта: {int(self.internal_tilt_chance)}%")
        # Проверяем критический уровень
        if self.internal_tilt_chance >= 99:
            await self.send_critical_warning()

    @commands.command(name="тильт")
    async def tilter_command(self, ctx):
        current_time = asyncio.get_event_loop().time()
        cooldown = 10  # Интервал между использованием команды (в секундах)
        # Проверяем, прошло ли достаточно времени с момента последнего использования
        if current_time - self.last_tilter_command_time < cooldown:
            remaining_time = int(cooldown - (current_time - self.last_tilter_command_time))
            await ctx.send(f"@{ctx.author.name}, команда доступна через {remaining_time} сек.")
            return
        # Обновляем время последнего использования команды
        self.last_tilter_command_time = current_time
        # Выводим текущий внутренний уровень тильта в консоль
        print(f"Текущий внутренний уровень тильта: {int(self.internal_tilt_chance)}%")
        # Отправляем ответ в чат с упоминанием пользователя
        response = f"@{ctx.author.name}, {self.format_tilt_message(self.internal_tilt_chance)}"
        await ctx.send(response)

    async def auto_tilt_message(self):
        """Автоматически отправляет сообщение раз в 5 минут."""
        while True:
            # Ждем 5 минут (300 секунд)
            for i in range(300, 0, -1):
                self.time_until_auto_message = i
                await asyncio.sleep(1)
            # Формируем сообщение с командой !тильт в конце
            channel = self.get_channel(CHANNEL_NAME)
            await channel.send(
                f"{self.format_tilt_message(self.internal_tilt_chance)} !тильт")

    def format_tilt_message(self, tilt_chance):
        """Форматирует сообщение об уровне тильта (выводит максимум 100%)."""
        displayed_chance = min(tilt_chance, 100)  # В чате показываем максимум 100%
        if displayed_chance <= 30:
            return f"😇 Уровень тильта низкий: ({int(displayed_chance)}%) 😇"
        elif displayed_chance <= 70:
            return f"😐 Уровень тильта средний: ({int(displayed_chance)}%) 😐"
        elif displayed_chance <= 90:
            return f"😡 Уровень тильта высокий: ({int(displayed_chance)}%) 😡"
        else:
            return f"🔥 Уровень тильта критический: ({int(displayed_chance)}%) 🔥"

    async def send_critical_warning(self):
        """Отправляет критическое предупреждение не чаще чем раз в 10 минут."""
        current_time = asyncio.get_event_loop().time()
        if current_time - self.last_critical_warning_time >= 600:  # 10 минут
            self.last_critical_warning_time = current_time
            channel = self.get_channel(CHANNEL_NAME)
            await channel.send("🔥 ВНИМАНИЕ! Уровень тильта КРИТИЧЕСКИЙ! 🔥 (!тильт)")
            print("Критическое предупреждение отправлено!")

    async def check_stream_status(self):
        """Проверяет статус стрима каждые 5 минут."""
        while True:
            try:
                headers = {
                    "Authorization": f"Bearer {API_OAUTH_TOKEN}",
                    "Client-ID": CLIENT_ID
                }
                response = requests.get(
                    f"https://api.twitch.tv/helix/streams?user_login={CHANNEL_NAME}",
                    headers=headers)
                data = response.json()
                # Проверяем, идет ли стрим
                if data["data"]:
                    print("Стрим начался! Статус: ВКЛЮЧЕН")
                else:
                    print("Стрим закончился! Статус: ВЫКЛЮЧЕН")
            except Exception as e:
                print("Ошибка при проверке статуса стрима:", e)
            await asyncio.sleep(300)  # Ждем 5 минут (300 секунд)

    async def report_time_until_auto_message(self):
        """Выводит в консоль время до автоматического сообщения."""
        while True:
            print(
                f"Время до автоматического сообщения: {self.time_until_auto_message} сек."
            )
            await asyncio.sleep(1)

    async def event_command_error(self, ctx, error):
        """Обрабатывает ошибки команд."""
        if isinstance(error, commands.CommandNotFound):
            return  # Игнорируем ошибку, если команда не найдена
        raise error  # Повторно вызываем другие ошибки

# Запуск бота
if __name__ == "__main__":
    bot = Bot()
    bot.run()
