#!/usr/bin/env python3

from __future__ import annotations

import sys
from time import sleep

from smbus2 import SMBus

# fmt: off
_hira2kata = str.maketrans(
    "をぁぃぅぇぉゃゅょっあいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわん"
    + "ｦｧｨｩｪｫｬｭｮｯｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ"
    + "ﾞﾟ"
    + "がぎぐげござじぜぞだぢづでどばびぶべぼぱぴぷぺぽ",
    2 * "ヲァィゥェォャュョッアイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワン"
    + "゛゜"
    + "ガギグゲゴザジゼゾダヂヅデドバビブベボパピプペポ"
)

_conv: dict[str, str] = {
    "ガ": "カ゛", "ギ": "キ゛", "グ": "ク゛", "ゲ": "ケ゛", "ゴ": "コ゛",
    "ザ": "サ゛", "ジ": "シ゛", "ズ": "ス゛", "ゼ": "セ゛", "ゾ": "ソ゛",
    "ダ": "タ゛", "ヂ": "チ゛", "ヅ": "ツ゛", "デ": "テ゛", "ド": "ト゛",
    "バ": "ハ゛", "ビ": "ヒ゛", "ブ": "フ゛", "ベ": "ヘ゛", "ボ": "ホ゛",
    "パ": "ハ゜", "ピ": "ヒ゜", "プ": "フ゜", "ペ": "ヘ゜", "ポ": "ホ゜",
    "℃": "゜C",
    "°": "゜",
    "”": '"',
    "’": "'",
    "~": "-",
    "‘": "`",
    "¥": "\\",
}

_chars: list[str | None] = [
    "\x00", "\x01", "\x02", "\x03", "\x04", "\x05", "\x06", "\x07",
    "\x08", "\x09", "\x0A", "\x0B", "\x0C", "\x0D", "\x0E", "\x0F",
    None, None, None, None, None, None, None, None,
    None, None, None, None, None, None, None, None,
    " ", "!", '"', "#", "$", "%", "&", "'",
    "(", ")", "*", "+", ",", "-", ".", "/",
    "0", "1", "2", "3", "4", "5", "6", "7",
    "8", "9", ":", ";", "<", "=", ">", "?",
    "@", "A", "B", "C", "D", "E", "F", "G",
    "H", "I", "J", "K", "L", "M", "N", "O",
    "P", "Q", "R", "S", "T", "U", "V", "W",
    "X", "Y", "Z", "[", "\\", "]", "^", "_",
    "`", "a", "b", "c", "d", "e", "f", "g",
    "h", "i", "j", "k", "l", "m", "n", "o",
    "p", "q", "r", "s", "t", "u", "v", "w",
    "x", "y", "z", "{", "|", "}", "→", "←",
    None, None, None, None, None, None, None, None,
    None, None, None, None, None, None, None, None,
    None, None, None, None, None, None, None, None,
    None, None, None, None, None, None, None, None,
    "\xA0", "。", "「", "」", "、", "・", "ヲ", "ァ",
    "ィ", "ゥ", "ェ", "ォ", "ャ", "ュ", "ョ", "ッ",
    "ー", "ア", "イ", "ウ", "エ", "オ", "カ", "キ",
    "ク", "ケ", "コ", "サ", "シ", "ス", "セ", "ソ",
    "タ", "チ", "ツ", "テ", "ト", "ナ", "ニ", "ヌ",
    "ネ", "ノ", "ハ", "ヒ", "フ", "ヘ", "ホ", "マ",
    "ミ", "ム", "メ", "モ", "ヤ", "ユ", "ヨ", "ラ",
    "リ", "ル", "レ", "ロ", "ワ", "ン", "゛", "゜",
    "α", "ä", "β", "ε", "μ", "σ", "ρ", "ℊ",
    "√", "⁻¹", "ｊ", "×", "￠", "￡", "ñ", "ö",
    "ｐ", "ｑ", "θ", "∞", "Ω", "ü", "Σ", "π",
    "ｘ", "ｙ", "千", "万", "円", "÷", "\xFE", "\xFF",
]
assert max(len(c) for c in _chars if c is not None) == 2
# fmt: on
_b2s = {i: c for i, c in enumerate(_chars) if c is not None}
_s2b = {c: i for i, c in enumerate(_chars) if c is not None}


def lcdenc(s: str) -> list[int]:
    s = s.translate(_hira2kata)

    for old, new in _conv.items():
        s = s.replace(old, new)

    result: list[int] = []
    for idx, c in enumerate(s):
        c2 = s[idx : idx + 2]
        if c2 in _s2b:
            result.append(_s2b[c2])
        elif c in _s2b:
            result.append(_s2b[c])
        else:
            result.append(ord(c))

    return result


class LCD1602:  # pylint: disable=missing-class-docstring
    RS = 0x01
    EN = 0x04
    BL = 0x08

    def __init__(
        self, bus: SMBus, *, ic2addr: int = 0x27, width: int = 16, lines: int = 2, backlight: bool = True
    ) -> None:
        self.bus: SMBus = bus

        self.ic2addr: int = ic2addr
        self.width: int = width
        self.lines: int = lines
        self.backlight: bool = backlight

        self.command(0b00110011)  # INITIALIZE to 8-bits mode
        self.command(0b00110010)  # INITIALIZE to 4-bits mode
        self.command(0b00101000)  # FUNCTION SET: 4D, 2R 5x8
        self.command(0b00001100)  # DISPLAY SWITCH: ON, Cursor OFF, Blink: OFF
        self.clear()  # CLEAR SCREEN

    # * Low Level API

    def _write4bit(self, data: int) -> None:
        if self.backlight:
            data |= self.BL
        self.bus.write_byte(self.ic2addr, data)

    def _pulse_enable(self, data: int) -> None:
        self._write4bit(data | self.EN)
        sleep(0.000001)
        self._write4bit(data & ~self.EN)
        sleep(0.000050)

    def _write8bit(self, value: int, mode: int) -> None:
        high = value & 0xF0 | mode
        low = (value << 4) & 0xF0 | mode
        self._pulse_enable(high)
        self._pulse_enable(low)

    def command(self, value: int) -> None:
        self._write8bit(value, 0)

    def data(self, value: int) -> None:
        self._write8bit(value, self.RS)

    # * User Level API

    def set_pos(self, x: int, y: int) -> None:
        x = max(0, min(x, self.width - 1))
        y = max(0, min(y, self.lines - 1))
        self.command(0x80 + 0x40 * y + x)  # 0b1YXXXXXX

    def clear(self) -> None:
        self.command(0b00000001)
        sleep(0.002)

    def print(self, text: str, *, x: int = 0, y: int = 0) -> None:
        self.set_pos(x, y)
        for char in lcdenc(text):
            self.data(char)

    def udf_char(self, loc: int, pic: list[int]) -> None:
        assert 0 <= loc <= 0x07
        assert len(pic) == 8

        self.command(0x40 | (loc << 3))
        sleep(0.000050)
        for p in pic:
            self.data(p)


def subcmd_test(lcd: LCD1602) -> None:
    lcd.set_pos(0, 0)
    for i in range(0, 256):
        lcd.data(i)
        if i % 32 == 31:
            input()
            lcd.set_pos(0, 0)
        elif i % 16 == 15:
            lcd.set_pos(0, 1)


def subcmd_udc(lcd: LCD1602) -> None:
    lcd.udf_char(
        0,
        [
            0b11111,
            0b10001,
            0b10001,
            0b10001,
            0b10001,
            0b10001,
            0b10001,
            0b11111,
        ],
    )


def main() -> None:
    with SMBus(1) as bus:
        argv = dict(enumerate(sys.argv))

        lcd = LCD1602(bus)

        if argv.get(1) == "test":
            return subcmd_test(lcd)

        if argv.get(1) == "udc":
            return subcmd_udc(lcd)

        for i in (0, 1):
            lcd.print(argv.get(i + 1, "").encode("ascii", "backslashreplace").decode("unicode-escape"), y=i)

    return None


if __name__ == "__main__":
    main()
