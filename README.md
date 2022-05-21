# Registers
A, B and CS(Code Selector)
# Instructions
mov ADDRESS BYTE [3-4 bytes]
mov REGISTER ADDRESS [3-4 bytes]
mov ADDRESS REGISTER [3-4 bytes]
add [1 byte]
sub [1 byte]
mul [1 byte]
div [1 byte]
reg REGISTER BYTE [3 bytes] - Sets register REGISTER to BYTE
hlt [1 byte] - Halts CPU
eseg [1 byte] - Turn on segmentation (Make sure you have a valid CS value)
jmp @(SEGMENT:)LABEL [2-3 bytes] - You must specify a segment selector if segmentation is enabled
jz @(SEGMENT:)LABEL [2-3 bytes] - Jump if A register is zero. You must specify a segment selector if segmentation is enabled
# Bytes
A valid byte can be a hexidecimal number of at most 0xFF, an integer or a character.
However for anything that isn't a hexadecimal number you must use a suffix.
d for decimal (97d), must be from 0 to 255
or
c for character (ac)
# Addresses
An address can be 1 or 2 bytes depending on if paging is enabled.
If it is, then 1 byte is reserved for the segment selector while the other contains the offset within that segment.
Otherwise it is a single byte with a physical address
# Paging
With paging disabled you can address up to 255 bytes of RAM!
Upon enabling paging you can access up to 8160 bytes of RAM of the megabyte available(Only 8160 because there are only 32 bytes allocated to page descriptors as of now)
***Enabling: ***
```s
mov 0x2 2 ;# Descriptors only contain one unused byte right now
mov 0x3 3
reg CS 0 ;# The page we want to use for a code selector, this will be 0 if your using loader.asm(It is loaded from the bios, which is loaded into page 0 on boot)
```
Thats it! Paging is now enabled!
Which means `mov 0x20 5d` is no longer valid but `mov 3:0x20 5d` is.
# Output
By default page 1 is memory mapped and written to the output

```py
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
```

Writing an ascii character to the buffer will output to the screen.
Note that the framebuffer isn't accessable if paging is disabled

The following will output the letter H to the screen!
```s
mov 1:0 Hc
```
