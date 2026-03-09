import sys, subprocess, os, ctypes, time

LOG = r'C:\Users\Administrator\.claude\statusline-debug.log'

def log(msg):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(str(msg) + '\n')
        f.flush()

log('SCRIPT-START')

NODE = r'C:\Program Files\nodejs\node.exe'
HUD = r'C:\Users\Administrator\.claude\plugins\cache\claude-hud\claude-hud\0.0.9\dist\index.js'

kernel32 = ctypes.windll.kernel32

buf = b''
try:
    if sys.stdin.isatty():
        log('TTY')
    else:
        STD_INPUT = kernel32.GetStdHandle(-10)
        avail = ctypes.c_ulong(0)

        # 最多等 100ms
        deadline = time.time() + 0.1
        while time.time() < deadline:
            kernel32.PeekNamedPipe(STD_INPUT, None, 0, None, ctypes.byref(avail), None)
            if avail.value > 0:
                buf = os.read(sys.stdin.fileno(), avail.value)
                break
            time.sleep(0.005)

        log(f'avail={avail.value} buf={len(buf)}')
except Exception as e:
    log(f'ERR:{e}')


def get_console_width():
    """通过 CONOUT$ 读取真实控制台宽度，stdout 为管道时依然有效"""
    try:
        class COORD(ctypes.Structure):
            _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]
        class SMALL_RECT(ctypes.Structure):
            _fields_ = [("Left", ctypes.c_short), ("Top", ctypes.c_short),
                        ("Right", ctypes.c_short), ("Bottom", ctypes.c_short)]
        class CSBI(ctypes.Structure):
            _fields_ = [("dwSize", COORD), ("dwCursorPosition", COORD),
                        ("wAttributes", ctypes.c_ushort), ("srWindow", SMALL_RECT),
                        ("dwMaximumWindowSize", COORD)]

        GENERIC_READ   = 0x80000000
        FILE_SHARE_RW  = 0x3
        OPEN_EXISTING  = 3
        h = kernel32.CreateFileW("CONOUT$", GENERIC_READ, FILE_SHARE_RW,
                                 None, OPEN_EXISTING, 0, None)
        INVALID = ctypes.c_void_p(-1).value
        if h == INVALID:
            return 0
        csbi = CSBI()
        ok = kernel32.GetConsoleScreenBufferInfo(h, ctypes.byref(csbi))
        kernel32.CloseHandle(h)
        if ok:
            return csbi.srWindow.Right - csbi.srWindow.Left + 1
    except Exception as e:
        log(f'get_console_width err:{e}')
    return 0


if buf:
    try:
        cols = get_console_width()
        log(f'console_cols={cols}')
        env = {**os.environ}
        if cols > 0:
            env['COLUMNS'] = str(cols)
        p = subprocess.run([NODE, HUD], input=buf, capture_output=True, timeout=5, env=env)
        if p.stdout:
            output = p.stdout.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
            sys.stdout.buffer.write(output)
            sys.stdout.buffer.flush()
        else:
            log(f'node-stderr:{p.stderr[:200]}')
    except Exception as e:
        log(f'node-run-err:{e}')
else:
    sys.stdout.write('[hud] no stdin data\n')
    sys.stdout.flush()
