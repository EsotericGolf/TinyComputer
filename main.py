import os
from computer import Computer, MemoryRange
import assembler

com = Computer()

asm = assembler.Assembler(True, "cpu.asm")

cur = 33

bytes = asm.interpret() # Parses the file and returns the program bytes

buf = [0] * 32

# Called when an address in the mapping is accessed
def IO(ram, write, address, byte):
  global buf

  if not write:
    return buf[address - 255]
    
  buf[address - 255] = byte

  os.system("clear")

  for ch in buf:
    print(chr(ch), end="", flush=True)

# Mapped to page 1
com.ram.map(MemoryRange(255, 255 + 0x20), IO)

com.cpu.cs = 0x0

com.ram.write(255 * 6, bytes, None)
com.boot()
