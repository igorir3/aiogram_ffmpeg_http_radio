from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import BaseFilter
from aiogram import F
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import os
import subprocess
from multiprocessing import Process, Queue
import asyncio
import random
import hashlib
from mutagen.id3 import ID3
import queue
import textwrap

MEDIA_FOLDER = "media"
CURRENT_PROCESS = None
AUTH_USERNAME = "admin"
AUTH_PASSWORD = "1234"
KEY = hashlib.sha256(f"{AUTH_USERNAME}:{AUTH_PASSWORD}".encode("utf-8")).hexdigest()

AIOGRAM_TOKEN = "TOKEN"
CHAT_ID = 0 # Set your telegram chat ID

FONT_BOLD = "calibrib.ttf"  # Bold
FONT_REGULAR = "calibri.ttf"    # Normal
FONT_ITALIC = "calibrii.ttf"  # Italic

playlist = []
router = Router()
def wrap_text(text, font, max_width, draw):
    """Перенос строки для текста."""
    lines = []
    for line in text.split("\n"):
        while True:
            width = draw.textbbox((0, 0), line, font=font)[2]
            if width <= max_width:
                lines.append(line)
                break
            else:
                # Перенос строки
                for i in range(len(line), 0, -1):
                    width = draw.textbbox((0, 0), line[:i], font=font)[2]
                    if width <= max_width:
                        lines.append(line[:i])
                        line = line[i:].strip()
                        break
    return lines

def create_card(title, artist, album, image_path):
    """Создаёт карточку с данными о треке."""
    # Размеры изображения
    WIDTH = 350
    PADDING = 50
    BG_COLOR = (44, 56, 85)  # Белый фон
    TEXT_COLOR = (255, 255, 255)  # Чёрный текст

    # Создание холста
    image = Image.new("RGB", (WIDTH, 1), BG_COLOR)
    draw = ImageDraw.Draw(image)

    # Загрузка шрифтов
    font_title = ImageFont.truetype(FONT_BOLD, size=35)  # Название трека
    font_album = ImageFont.truetype(FONT_ITALIC, size=25)  # Название альбома
    font_artist = ImageFont.truetype(FONT_REGULAR, size=30)  # Имя исполнителя

    # Создание холста для расчёта высоты
    temp_image = Image.new("RGB", (WIDTH, 1), BG_COLOR)
    temp_draw = ImageDraw.Draw(temp_image)

    # Перенос строк
    wrapped_title = wrap_text(title, font_title, WIDTH - 2 * PADDING, temp_draw)
    wrapped_album = wrap_text(album, font_album, WIDTH - 2 * PADDING, temp_draw)
    wrapped_artist = wrap_text(artist, font_artist, WIDTH - 2 * PADDING, temp_draw)

    # Рассчитываем высоту текста
    height = PADDING * 2 + 300
    for lines, font in [(wrapped_title, font_title), (wrapped_album, font_album), (wrapped_artist, font_artist)]:
        height += len(lines) * draw.textbbox((0, 0), "A", font=font)[2] + PADDING

    # Создание финального изображения
    image = Image.new("RGB", (WIDTH, height), BG_COLOR)
    draw = ImageDraw.Draw(image)
    
    if image_path:
        album_art = Image.open(image_path).resize((300, 300)).convert("RGB")
        mask = Image.new("L", (300, 300), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, 300, 300), fill=255)
        image.paste(album_art, ((WIDTH - 300) // 2, PADDING), mask)

    # Рисуем текст
    y = PADDING * 2 + 300
    for lines, font in [(wrapped_title, font_title), (wrapped_album, font_album), (wrapped_artist, font_artist)]:
        for line in lines:
            text_width = draw.textbbox((0, 0), line, font=font)[2]
            draw.text(((WIDTH - text_width) // 2, y), line, font=font, fill=TEXT_COLOR)
            y += draw.textbbox((0, 0), line, font=font)[3] - draw.textbbox((0, 0), line, font=font)[1]
        y += PADDING

    # Сохраняем изображение в память
    output = BytesIO()
    image.save(output, format="JPEG", quality=85)
    output.seek(0)
    return output

    return output

class media_files:
    def __init__(self):
        self.medias = []
        listdir = os.listdir("media")
        for x in listdir:
            if x.endswith(".mp3"):
                self.medias.append(f"media\\{x}")
    
    def scan(self, folder = None):
        self.medias = []
        try:
            folder_name = "media" + "" if folder is None else f"\\{folder}"
        except:
            folder_name = "media"
        for x in os.listdir(folder_name):
            if x.endswith(".mp3"):
                self.medias.append(f"{folder_name}\\{x}")
    
    def shuffle(self):
        random.shuffle(self.medias)

    def __call__(self, ID : int):
        return self.medias[ID]
    def __len__(self):
        return len(self.medias)
    
def radio_process(control_queue : Queue, media_queue : Queue):
    process = None
    stop_flag = False
    media_obj = media_files()
    if len(media_obj) < 1:
        raise SystemError("Media folder haven't mp3s | Can't scan media folder")
    media_ID = 0 

    while True:
        if process is None and stop_flag == False:
            ffmpeg_command = [
                "ffmpeg",
                "-re",  # Реальное время
                "-i", media_obj(media_ID),  # Исходный файл
                "-c:a", "libmp3lame",  # Кодек
                "-b:a", "128k",  # Битрейт
                "-f", "mp3",  # Формат
                "-headers", f"Authorization: Basic {KEY}",
                "-vn",
                "http://yourIP:25565/upload"  # Адрес трансляции
            ]

            # Запуск FFmpeg
            process = subprocess.Popen(ffmpeg_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) #
            data = ID3(media_obj(media_ID))
            try:
                media_queue.put([data.getall("TIT2"), data.getall("TPE1"), data.getall("TALB"), data.getall("APIC")], timeout=0.1) # 
            except:
                pass

        if process.poll() is not None:
            process.terminate()
            process = None
            media_ID = media_ID + 1
            if media_ID not in range(len(media_obj)):
                media_ID = 0

        try:
            command = control_queue.get_nowait()
        except:
            command = None

        if command is not None:
            command = command.split()

            if command[0] == "PLAY":
                stop_flag = False
                if len(command) > 1:
                    media_ID = command[1]
                    if process is not None:
                        process.terminate()
                        process = None
            elif command[0] == "UPDATE":
                if len(command) > 1:
                    media_obj.scan(command[1])
                else:
                    media_obj.scan()
                if process is not None:
                    process.terminate()
                    process = None
                if media_ID not in range(len(media_obj)):
                    media_ID = 0
            elif command[0] == "STOP":
                media_ID = 0
                if process is not None:
                    process.terminate()
                    process = None
                    stop_flag = True
            elif command[0] == "PAUSE":
                if process is not None:
                    process.terminate()
                    process = None
                    stop_flag = True
            elif command[0] == "NEXT":
                media_ID = media_ID + 1
                if process is not None:
                    process.terminate()
                    process = None
            elif command[0] == "SHUFFLE":
                media_ID = 0
                if process is not None:
                    process.terminate()
                    process = None
                media_obj.shuffle()

async def process_queue(bot : Bot, queue: Queue):
    """Фоновая задача для обработки сообщений из очереди."""
    while True:
        if not queue.empty():
            # Получаем сообщение из очереди
            message = queue.get()
            # Отправляем сообщение в указанный чат
            card = create_card(message[0][0].text[0], message[1][0].text[0], message[2][0].text[0], BytesIO(message[3][0].data))
            await bot.send_photo(chat_id=CHAT_ID, photo=BufferedInputFile(card.getbuffer(), filename=f"radio_card.jpg"))
        await asyncio.sleep(0.001)  # Задержка для оптимизации цикла

@router.message(F.text.startswith("/play"))
async def play(message: Message):
    if message.chat.id == CHAT_ID:
        args = message.text.split()[1:]
        try:
            control_queue.put(f"PLAY{"" if len(args) == 0 else f" {int(args[0])}"}")
        except ValueError:
            await message.reply(f"Номер пина '{args[0]}' не может быть использовано!\nПожалуйста, введите номер песни!")
        except queue.Full:
            await message.reply(f"Превышено кол-во запросов!\nПожалуйста, попробуйте позже!")

@router.message(F.text.startswith("/scan"))
async def scan(message: Message):
    if message.chat.id == CHAT_ID:
        args = message.text.split()[1:]
        try:
            control_queue.put(f"UPDATE{"" if len(args) == 0 else f" {" ".join(args)}"}")
        except queue.Full:
            await message.reply(f"Превышено кол-во запросов!\nПожалуйста, попробуйте позже!")

@router.message(F.text.startswith("/stop"))
async def stop(message: Message):
    if message.chat.id == CHAT_ID:
        try:
            control_queue.put("STOP")
        except queue.Full:
            await message.reply(f"Превышено кол-во запросов!\nПожалуйста, попробуйте позже!")

@router.message(F.text.startswith("/pause"))
async def pause(message: Message):
    if message.chat.id == CHAT_ID:
        try:
            control_queue.put("PAUSE")
        except queue.Full:
            await message.reply(f"Превышено кол-во запросов!\nПожалуйста, попробуйте позже!")

@router.message(F.text.startswith("/next"))
async def next(message: Message):
    if message.chat.id == CHAT_ID:
        try:
            control_queue.put("NEXT")
        except queue.Full:
            await message.reply(f"Превышено кол-во запросов!\nПожалуйста, попробуйте позже!")

@router.message(F.text.startswith("/shuffle"))
async def shuffle(message: Message):
    if message.chat.id == CHAT_ID:
        try:
            control_queue.put("SHUFFLE")
        except queue.Full:
            await message.reply(f"Превышено кол-во запросов!\nПожалуйста, попробуйте позже!")


async def main(control_queue, media_queue):
    global router
    radio = Process(target=radio_process, args=(control_queue, media_queue))
    radio.start()

    bot = Bot(token=AIOGRAM_TOKEN)
    dp = Dispatcher()
    
    dp.include_router(router)

    asyncio.create_task(process_queue(bot, media_queue))

    await dp.start_polling(bot)
    
if __name__ == "__main__":
    try:
        control_queue = Queue()
        media_queue = Queue()
        asyncio.run(main(control_queue, media_queue))
    except KeyboardInterrupt:
        print("Остановка бота.")
        control_queue.put_nowait("STOP")