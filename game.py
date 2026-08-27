import random
import sys
import time
import os

WIDTH = 79
HEIGHT = 25

if sys.platform == "win32":
    import msvcrt
    import ctypes
    kernel32 = ctypes.windll.kernel32
    STD_OUTPUT_HANDLE = -11
    CARRIAGE_RETURN = ""

    def clear_screen():
        # Очистка экрана в Windows (аналог \033[2J)
        for _ in range(100):
            print()

    def hide_cursor():
        # Скрыть курсор в Windows (аналог \033[?25l)
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 0x0001 | 0x0002 | 0x0004)
        info = ctypes.create_string_buffer(22)
        kernel32.GetConsoleScreenBufferInfo(kernel32.GetStdHandle(-11), info)
        mode = ctypes.cast(info, ctypes.POINTER(ctypes.c_uint32)).contents.value
        ctypes.cast(info, ctypes.POINTER(ctypes.c_uint32)).contents.value = mode & ~0x0020

    def show_cursor():
        # Показать курсор в Windows (аналог \033[?25h)
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 0x0001 | 0x0002 | 0x0004)
        info = ctypes.create_string_buffer(22)
        kernel32.GetConsoleScreenBufferInfo(kernel32.GetStdHandle(-11), info)
        mode = ctypes.cast(info, ctypes.POINTER(ctypes.c_uint32)).contents.value
        ctypes.cast(info, ctypes.POINTER(ctypes.c_uint32)).contents.value = mode | 0x0020


    def move_cursor_home():
        h = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        csbi = ctypes.create_string_buffer(22)
        kernel32.GetConsoleScreenBufferInfo(h, csbi)
        # csbi layout (упрощённо): [0]=size, [4]=cursor pos (X,Y) как два int32
        cursor_pos = ctypes.cast(csbi, ctypes.POINTER(ctypes.c_uint32)).contents
        # В структуре CONSOLE_SCREEN_BUFFER_INFO курсор находится по смещению 4+8=12 байт (два int32)
        cursor = ctypes.cast(ctypes.addressof(csbi) + 12, ctypes.POINTER(ctypes.c_ulonglong)).contents.value
        x = cursor & 0xFFFF
        y = (cursor >> 16) & 0xFFFF
        # Просто ставим курсор в (0,0)
        class COORD(ctypes.Structure):
            _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]
        coord = COORD(0, 0)
        kernel32.SetConsoleCursorPosition(h, coord)
    def get_arrow_key():
        """
        Возвращает 'LEFT', 'RIGHT', 'UP', 'DOWN' или None, если нажатий нет.
        Работает неблокирующе в Windows.
        """
        if not msvcrt.kbhit():
            return None
        ch = msvcrt.getwch()  # может вернуть один или два символа для стрелок
        if ch == '\x1b':  # Esc
            return 'ESC'
        # Стрелки в Windows: первый байт — спецкод (обычно \xe0 или 0x00), второй — код клавиши
        if ch in ('\xe0', '\0'):
            ch2 = msvcrt.getwch()
            if ch2 == 'K':
                return 'LEFT'
            elif ch2 == 'M':
                return 'RIGHT'
            elif ch2 == 'H':
                return 'UP'
            elif ch2 == 'P':
                return 'DOWN'
        return None
else:
    import select
    import termios
    import tty

    CARRIAGE_RETURN = "\r"

    # Unix: оставляем ANSI-последовательности
    def clear_screen():
        print("\033[2J", end="", flush=True)

    def hide_cursor():
        print("\033[?25l", end="", flush=True)

    def show_cursor():
        print("\033[?25h", end="", flush=True)

    def move_cursor_home():
        print("\033[H", end="", flush=True)


    def get_arrow_key():
        """
        Возвращает 'LEFT', 'RIGHT', 'UP', 'DOWN' или None, если нажатий нет.
        Работает неблокирующе в Linux.
        """
        if not select.select([sys.stdin], [], [], 0)[0]:
            return None
        fd = sys.stdin.fileno()
        ch = os.read(fd, 1)
        if ch == b'\x1b':
            if select.select([sys.stdin], [], [], 0.05)[0]:
                ch2 = os.read(fd, 1)
                if ch2 == b'[':
                    ch3 = os.read(fd, 1)
                    if ch3 == b'A': return 'UP'
                    if ch3 == b'B': return 'DOWN'
                    if ch3 == b'C': return 'RIGHT'
                    if ch3 == b'D': return 'LEFT'
            else:
                return 'ESC'
        return None


def move_road(rows:list) -> list:
    last = rows.pop()
    line = [" "] * WIDTH
    x = random.randint(1, WIDTH - 1)
    line[x] = "#"
    rows.insert(0, line)
    return rows

def game():
    score = 0
    pause = 0.2
    car = WIDTH // 2
    rows = [[" "] * WIDTH for _ in range(HEIGHT)]
    rows[-1][car] = "A"
    for _ in range(10):
        x = random.randint(1, WIDTH - 1)
        y = random.randint(1, HEIGHT - 1)
        rows[y][x] = "#"
    while True:
        move_cursor_home()
        hide_cursor()
        key = get_arrow_key()
        if key:
            if key == 'ESC':
                break
            direction = key
            rows[-1][car] = " "
            if direction == 'LEFT':
                car = car - 1 if car > 1 else 1
            if direction == 'RIGHT':
                car = car + 1 if car < (WIDTH - 1) else WIDTH - 2
            if direction == 'UP':
                pause = pause - 0.1 if pause > 0.1 else 0.1
            if direction == 'DOWN':
                pause = pause + 0.1

        road = f"{CARRIAGE_RETURN}\n".join("|" + "".join(row) + "|" for row in rows)
        print(road, end="", flush=True)
        print(f"{CARRIAGE_RETURN}\n Счёт: {score}", flush=True)
        rows = move_road(rows)
        if rows[-1][car] == "#":
            break
        rows[-1][car] = "A"
        score += 1
        time.sleep(pause)

if __name__ == "__main__":
    if sys.platform != "win32":
        fd = sys.stdin.fileno()
        old_tty = termios.tcgetattr(fd)
        tty.setraw(fd)
    clear_screen()
    game()
    show_cursor()
    if sys.platform != "win32":
        termios.tcsetattr(fd, termios.TCSADRAIN, old_tty)