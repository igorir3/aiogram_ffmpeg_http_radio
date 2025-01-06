import asyncio
from aiohttp import web
from collections import deque
import hashlib

BUFFER_SIZE = 512  # Размер буфера
AUDIO_BUFFER = deque(maxlen=5)  # Глобальный буфер для аудио
CLIENTS = set()  # Список подключённых клиентов

# Учетные данные для авторизации
AUTH_USERNAME = "admin"
AUTH_PASSWORD = "1234"
HASHED_KEY = hashlib.sha256(f"{AUTH_USERNAME}:{AUTH_PASSWORD}".encode("utf-8")).hexdigest()


def check_authorization(request):
    """Проверяет заголовок Authorization."""
    auth_header = request.headers.get("Authorization", None)
    if not auth_header or not auth_header.startswith("Basic "):
        return False

    # Декодируем базовую аутентификацию
    encoded_credentials = auth_header.split("Basic ")[1]
    return HASHED_KEY == encoded_credentials


async def stream_handler(request):
    """Принимает поток от FFmpeg."""
    global AUDIO_BUFFER

    if not check_authorization(request):
        raise web.HTTPUnauthorized(text="Unauthorized: Invalid credentials")

    print("FFmpeg подключён для передачи потока.")
    try:
        async for chunk in request.content.iter_chunked(BUFFER_SIZE):
            AUDIO_BUFFER.append(chunk)
    except asyncio.CancelledError:
        print("FFmpeg отключился.")
    finally:
        return web.Response(text="Поток завершён.")


async def broadcast_audio(request):
    """Транслирует поток подключённым клиентам."""
    global CLIENTS

    response = web.StreamResponse(
        status=200,
        reason="OK",
        headers={
            "Content-Type": "audio/mpeg",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
    await response.prepare(request)

    # Добавляем клиента
    queue = asyncio.Queue()
    CLIENTS.add(queue)
    print(f"Клиент подключён: {request.remote}. Всего клиентов: {len(CLIENTS)}")

    try:
        while True:
            # Получаем данные из очереди клиента
            chunk = await queue.get()
            await response.write(chunk)
    except asyncio.CancelledError:
        print(f"Клиент отключён: {request.remote}.")
    finally:
        CLIENTS.remove(queue)
        return response


async def distribute_audio():
    """Распространяет аудио из глобального буфера клиентам."""
    while True:
        if AUDIO_BUFFER:
            chunk = AUDIO_BUFFER.popleft()
            # Рассылаем данные всем клиентам
            for client_queue in list(CLIENTS):
                await client_queue.put(chunk)
        else:
            await asyncio.sleep(0.001)


async def main():
    app = web.Application()
    app.router.add_post("/upload", stream_handler)  # Для передачи от FFmpeg
    app.router.add_get("/stream", broadcast_audio)  # Для клиентов

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 25565)
    print("Сервер запущен на порту 25565.")
    await site.start()

    # Запуск фоновой задачи для распространения данных
    asyncio.create_task(distribute_audio())

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Сервер остановлен.")