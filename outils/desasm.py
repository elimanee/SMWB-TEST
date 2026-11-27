"""Petit désassembleur 65816 (processeur de la SNES), pour lire le code du jeu.

Usage :  python3 outils/desasm.py ROM.sfc 05:82B0 [nombre_d_instructions] [m=8|16] [x=8|16]
Suit REP/SEP pour la taille des immédiats (approximatif sur les branchements).
"""
import sys

from smwrom import snes_to_pc

# (mnémonique, mode) ; modes : imp, imm_m, imm_x, imm8, dp, dpx, dpy, dpi, dpil, dpix, dpiy, dpily,
# abs, absx, absy, absi, absix, absil, long, longx, rel, rell, sr, sriy, blk
OPS = {}
def _set(codes, name, mode):
    for c in codes:
        OPS[c] = (name, mode)
_grp = {
    'ORA': 0x00, 'AND': 0x20, 'EOR': 0x40, 'ADC': 0x60, 'STA': 0x80, 'LDA': 0xA0, 'CMP': 0xC0, 'SBC': 0xE0,
}
for n, b in _grp.items():
    _set([b + 0x01], n, 'dpix'); _set([b + 0x03], n, 'sr'); _set([b + 0x05], n, 'dp'); _set([b + 0x07], n, 'dpil')
    if n != 'STA': _set([b + 0x09], n, 'imm_m')
    _set([b + 0x0D], n, 'abs'); _set([b + 0x0F], n, 'long'); _set([b + 0x11], n, 'dpiy'); _set([b + 0x12], n, 'dpi')
    _set([b + 0x13], n, 'sriy'); _set([b + 0x15], n, 'dpx'); _set([b + 0x17], n, 'dpily'); _set([b + 0x19], n, 'absy')
    _set([b + 0x1D], n, 'absx'); _set([b + 0x1F], n, 'longx')
OPS[0x89] = ('BIT', 'imm_m')
for c, n in ((0x10, 'BPL'), (0x30, 'BMI'), (0x50, 'BVC'), (0x70, 'BVS'), (0x80, 'BRA'), (0x90, 'BCC'),
             (0xB0, 'BCS'), (0xD0, 'BNE'), (0xF0, 'BEQ')):
    OPS[c] = (n, 'rel')
OPS[0x82] = ('BRL', 'rell')
imp = {0x18: 'CLC', 0x38: 'SEC', 0x58: 'CLI', 0x78: 'SEI', 0xB8: 'CLV', 0xD8: 'CLD', 0xF8: 'SED',
       0x0A: 'ASL A', 0x2A: 'ROL A', 0x4A: 'LSR A', 0x6A: 'ROR A', 0x1A: 'INC A', 0x3A: 'DEC A',
       0xAA: 'TAX', 0xA8: 'TAY', 0x8A: 'TXA', 0x98: 'TYA', 0x9A: 'TXS', 0xBA: 'TSX', 0x9B: 'TXY', 0xBB: 'TYX',
       0xE8: 'INX', 0xC8: 'INY', 0xCA: 'DEX', 0x88: 'DEY', 0xEA: 'NOP', 0x60: 'RTS', 0x6B: 'RTL', 0x40: 'RTI',
       0x48: 'PHA', 0x68: 'PLA', 0xDA: 'PHX', 0xFA: 'PLX', 0x5A: 'PHY', 0x7A: 'PLY', 0x08: 'PHP', 0x28: 'PLP',
       0x8B: 'PHB', 0xAB: 'PLB', 0x0B: 'PHD', 0x2B: 'PLD', 0x4B: 'PHK', 0x5B: 'TCD', 0x7B: 'TDC', 0x1B: 'TCS',
       0x3B: 'TSC', 0xEB: 'XBA', 0xFB: 'XCE', 0xCB: 'WAI', 0xDB: 'STP'}
for c, n in imp.items():
    OPS[c] = (n, 'imp')
OPS[0xC2] = ('REP', 'imm8'); OPS[0xE2] = ('SEP', 'imm8')
OPS[0xA2] = ('LDX', 'imm_x'); OPS[0xA0] = ('LDY', 'imm_x'); OPS[0xE0] = ('CPX', 'imm_x'); OPS[0xC0] = ('CPY', 'imm_x')
for c, n, m in ((0xA6, 'LDX', 'dp'), (0xB6, 'LDX', 'dpy'), (0xAE, 'LDX', 'abs'), (0xBE, 'LDX', 'absy'),
                (0xA4, 'LDY', 'dp'), (0xB4, 'LDY', 'dpx'), (0xAC, 'LDY', 'abs'), (0xBC, 'LDY', 'absx'),
                (0x86, 'STX', 'dp'), (0x96, 'STX', 'dpy'), (0x8E, 'STX', 'abs'),
                (0x84, 'STY', 'dp'), (0x94, 'STY', 'dpx'), (0x8C, 'STY', 'abs'),
                (0x64, 'STZ', 'dp'), (0x74, 'STZ', 'dpx'), (0x9C, 'STZ', 'abs'), (0x9E, 'STZ', 'absx'),
                (0xE4, 'CPX', 'dp'), (0xEC, 'CPX', 'abs'), (0xC4, 'CPY', 'dp'), (0xCC, 'CPY', 'abs'),
                (0x24, 'BIT', 'dp'), (0x34, 'BIT', 'dpx'), (0x2C, 'BIT', 'abs'), (0x3C, 'BIT', 'absx'),
                (0x4C, 'JMP', 'abs'), (0x6C, 'JMP', 'absi'), (0x7C, 'JMP', 'absix'), (0x5C, 'JML', 'long'),
                (0xDC, 'JML', 'absil'), (0x20, 'JSR', 'abs'), (0xFC, 'JSR', 'absix'), (0x22, 'JSL', 'long'),
                (0x06, 'ASL', 'dp'), (0x16, 'ASL', 'dpx'), (0x0E, 'ASL', 'abs'), (0x1E, 'ASL', 'absx'),
                (0x26, 'ROL', 'dp'), (0x36, 'ROL', 'dpx'), (0x2E, 'ROL', 'abs'), (0x3E, 'ROL', 'absx'),
                (0x46, 'LSR', 'dp'), (0x56, 'LSR', 'dpx'), (0x4E, 'LSR', 'abs'), (0x5E, 'LSR', 'absx'),
                (0x66, 'ROR', 'dp'), (0x76, 'ROR', 'dpx'), (0x6E, 'ROR', 'abs'), (0x7E, 'ROR', 'absx'),
                (0xE6, 'INC', 'dp'), (0xF6, 'INC', 'dpx'), (0xEE, 'INC', 'abs'), (0xFE, 'INC', 'absx'),
                (0xC6, 'DEC', 'dp'), (0xD6, 'DEC', 'dpx'), (0xCE, 'DEC', 'abs'), (0xDE, 'DEC', 'absx'),
                (0x04, 'TSB', 'dp'), (0x0C, 'TSB', 'abs'), (0x14, 'TRB', 'dp'), (0x1C, 'TRB', 'abs'),
                (0x54, 'MVN', 'blk'), (0x44, 'MVP', 'blk'), (0xF4, 'PEA', 'abs'), (0xD4, 'PEI', 'dp'),
                (0x62, 'PER', 'rell'), (0x00, 'BRK', 'imm8'), (0x02, 'COP', 'imm8'), (0x42, 'WDM', 'imm8')):
    OPS[c] = (n, m)

SIZE = {'imp': 0, 'imm8': 1, 'dp': 1, 'dpx': 1, 'dpy': 1, 'dpi': 1, 'dpil': 1, 'dpix': 1, 'dpiy': 1,
        'dpily': 1, 'sr': 1, 'sriy': 1, 'rel': 1, 'abs': 2, 'absx': 2, 'absy': 2, 'absi': 2, 'absix': 2,
        'absil': 2, 'rell': 2, 'blk': 2, 'long': 3, 'longx': 3}
FMT = {'imp': '', 'dp': '${:02X}', 'dpx': '${:02X},X', 'dpy': '${:02X},Y', 'dpi': '(${:02X})',
       'dpil': '[${:02X}]', 'dpix': '(${:02X},X)', 'dpiy': '(${:02X}),Y', 'dpily': '[${:02X}],Y',
       'sr': '${:02X},S', 'sriy': '(${:02X},S),Y', 'abs': '${:04X}', 'absx': '${:04X},X', 'absy': '${:04X},Y',
       'absi': '(${:04X})', 'absix': '(${:04X},X)', 'absil': '[${:04X}]', 'long': '${:06X}', 'longx': '${:06X},X'}


def disasm(rom, addr, count=40, m16=False, x16=False):
    out = []
    pc = snes_to_pc(addr)
    for _ in range(count):
        op = rom[pc]
        name, mode = OPS.get(op, ('???', 'imp'))
        if mode == 'imm_m':
            n = 2 if m16 else 1
        elif mode == 'imm_x':
            n = 2 if x16 else 1
        else:
            n = SIZE[mode]
        arg = int.from_bytes(rom[pc + 1:pc + 1 + n], 'little') if n else 0
        if mode in ('imm_m', 'imm_x', 'imm8'):
            txt = '#$%0*X' % (n * 2, arg)
        elif mode == 'rel':
            dst = (addr + 2 + (arg - 256 if arg > 127 else arg)) & 0xFFFF | (addr & 0xFF0000)
            txt = '$%04X' % (dst & 0xFFFF)
        elif mode == 'rell':
            dst = (addr + 3 + (arg - 65536 if arg > 32767 else arg)) & 0xFFFF
            txt = '$%04X' % dst
        elif mode == 'blk':
            txt = '$%02X,$%02X' % (arg & 0xFF, arg >> 8)
        else:
            txt = FMT[mode].format(arg) if mode != 'imp' else ''
        if name == 'REP':
            if arg & 0x20: m16 = True
            if arg & 0x10: x16 = True
        if name == 'SEP':
            if arg & 0x20: m16 = False
            if arg & 0x10: x16 = False
        raw = rom[pc:pc + 1 + n].hex(' ')
        out.append('%02X:%04X  %-12s %s %s' % (addr >> 16, addr & 0xFFFF, raw, name, txt))
        pc += 1 + n
        addr = (addr & 0xFF0000) | ((addr + 1 + n) & 0xFFFF)
    return '\n'.join(out)


if __name__ == '__main__':
    rom = open(sys.argv[1], 'rb').read()
    a = int(sys.argv[2].replace(':', ''), 16)
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 40
    m16 = any(s == 'm=16' for s in sys.argv[4:]); x16 = any(s == 'x=16' for s in sys.argv[4:])
    print(disasm(rom, a, n, m16, x16))
