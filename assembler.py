
class Assembler:

    def isreg(self, name):
        return name == "A" or name == "B"

    def reg(self, name):
        if name == "A":
            return 0x1
        elif name == "B":
            return 0x2
        elif name == "CS":
            return 0x3

    def num(self, subject, cur):
        if subject.endswith("d"):
            return int(subject.strip("d"))

        if subject.endswith("c"):
            if subject[0:2] == "\\s":
                return 0x20
            
            return ord(subject[0:1])

        if (subject == "$+"):
            return cur + 1

        return int(subject, base=16)

    def appendaddr(self, seg, bytes, addr):
        if seg:
            if len(addr) < 2:
                raise Exception("Segment selector is required")

            bytes.append(self.num(addr[0], len(bytes) + 2))
            bytes.append(self.num(addr[1], len(bytes) + 1))
        else:
            bytes.append(self.num(addr[0], len(bytes) + 1))

    def interpret(self):
        bytes = []
        paged = False
        labels = {}
        revisit = []

        for line in self.src:
            line = line.split(";")[0] # Fast and sloppy way to implement comments but it works
            spl = line.replace("\n", "").split(" ")
            
            while "" in spl:
                spl.remove("")

            if len(spl) == 0:
                continue

            if spl[0] == "[Paged]":
                paged = True

            if spl[0].endswith(":"):
                labels[spl[0].strip(":")] = len(bytes) + 32
                continue

            if spl[0] == "db":
                bytes.append(self.num(spl[1], len(bytes) + 1))

            if spl[0] == "hlt":
                bytes.append(0xFF)

            if spl[0] == "epge":
                bytes.append(0x0F)
                #bytes.append(None) # Might cause some issues later?
                #revisit.append({ "type": "eseg", "label": spl[1].strip("@"), "index": len(bytes) - 1, "segmented": segmented })
                paged = True

            if spl[0] == "dpge":
                bytes.append(0x0E)
                paged = False

            if spl[0] == "jmp":
                bytes.append(0x3)

                if spl[1].startswith("@"):
                    if paged:
                        bytes.append(self.num(spl[1].strip("@").split(":")[0], len(bytes) + 1))
                    
                    bytes.append(None) # Might cause some issues later?
                    revisit.append({ "type": "jump", "label": spl[1].strip("@").split(":")[1], "index": len(bytes) - 1, "segmented": paged })
                    continue

                self.appendaddr(paged, bytes, spl[1].split(":"))

            if spl[0] == "jz":
                bytes.append(0x34)

                if spl[1].startswith("@"):
                    if paged:
                        bytes.append(self.num(spl[1].strip("@").split(":")[0], len(bytes) + 1))
                    
                    bytes.append(None)
                    revisit.append({ "type": "jump", "label": spl[1].strip("@").split(":")[1], "index": len(bytes) - 1, "segmented": paged })
                    continue

                self.appendaddr(paged, bytes, spl[1].split(":"))

            if spl[0] == "reg":
                bytes.append(0x4)

                bytes.append(self.reg(spl[1]))

                if self.isreg(spl[2]):
                    bytes[len(bytes) - 2] = 0x45
                    bytes.append(self.reg(spl[2]))
                    continue

                bytes.append(self.num(spl[2], len(bytes) + 1))
            
            if spl[0] == "mov":

                if self.isreg(spl[2]) and not spl[1].startswith("["):
                    bytes.append(0x12)
                    self.appendaddr(paged, bytes, spl[1].split(":"))
                    bytes.append(self.reg(spl[2]))
                    continue

                if self.isreg(spl[1]):
                    if not spl[2].startswith("["):
                        bytes.append(0x13)
                    else:
                        bytes.append(0x17)
                        bytes.append(self.reg(spl[1]))
                        spl = spl[2].replace("[", "").replace("]", "").split(":")
                        bytes.append(self.num(spl[0], len(bytes) + 2))
                        bytes.append(self.reg(spl[1]))
                        continue
                    
                    bytes.append(self.reg(spl[1]))
                    self.appendaddr(paged, bytes, spl[2].split(":"))
                    continue

                if spl[1].startswith("[") and spl[1].endswith("]"):
                    if spl[2].startswith("[") and spl[2].endswith("]"):
                        bytes.append(0x16)
                        regaddr = spl[1].replace("[", "").replace("]", "")
                        bytes.append(self.num(regaddr.split(":")[0], len(bytes) + 4))
                        bytes.append(self.reg(regaddr.split(":")[1]))

                        other = spl[2].replace("[", "").replace("]", "")
                        bytes.append(self.num(other.split(":")[0], len(bytes) + 2))
                        bytes.append(self.reg(other.split(":")[1]))
                        continue


                    bytes.append(0x15)
                    regaddr = spl[1].replace("[", "").replace("]", "")
                    bytes.append(self.num(regaddr.split(":")[0], len(bytes) + 4))
                    bytes.append(self.reg(regaddr.split(":")[1]))

                    self.appendaddr(paged, bytes, spl[2].split(":"))
                    continue

                if spl[2].startswith("[") and spl[2].endswith("]"):
                    bytes.append(0x14)
                    self.appendaddr(paged, bytes, spl[1].split(":"))
                    bytes.append(self.reg(spl[2].replace("[", "").replace("]", "")))
                    continue

                #if self.isreg(spl[1].split(":")[1]):
                    #pass

                if spl[2].startswith("\"") and spl[len(spl) - 1].endswith("\""):
                        string = " ".join(spl[2:]).replace("\"", "")
                        addr = spl[1].split(":")

                        for ch in string:
                            bytes.append(0x1)
                            self.appendaddr(paged, bytes, addr)
                            bytes.append(ord(ch))

                            num = self.num(addr[1], None)
                            addr[1] = str(num + 1) + "d"

                        continue

                bytes.append(0x1)
                
                self.appendaddr(paged, bytes, spl[1].split(":"))
                
                bytes.append(self.num(spl[2], len(bytes) + 1))

            if spl[0] == "add":
                bytes.append(0x5)
            
            if spl[0] == "sub":
                bytes.append(0x56)

            if spl[0] == "mul":
                bytes.append(0x57)
            
            if spl[0] == "div":
                bytes.append(0x58)

        for jmp in revisit:
            # If the loop is in a segmented area, then it cant just directly go to it!
            if jmp["segmented"]:
                bytes[jmp["index"]] = labels[jmp["label"]] - 33 + 30
            else:
                bytes[jmp["index"]] = labels[jmp["label"]] + 1

        bytes.append(0xFF)

        return bytes

    def __init__(self, isfile, file):
        if not isfile:
            self.src = file.split("\n")
            return
        
        handle = open(file, "r")
        self.src = handle.readlines()
