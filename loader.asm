[Paged] ; The bios enables paging before jumping here
reg CS 2
reg CS 0x6
jmp 0x6:0
loop:
jmp @2:loop ; Its a good idea to loop or hlt once you are done.
db 0xAA ; Required to let the bios know where it ends
