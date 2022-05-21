from collections.abc import MutableSequence
from assembler import Assembler
from math import floor
import time


class AccessError(Exception):
		pass


class CPUError(Exception):
		pass


class MemoryRange:
		def __init__(self, start, end):
				self.start = start
				self.end = end
				self.size = end - start
				self.accessor = None


class RAM(MutableSequence):
		def map(self, range, rw):
				range.accessor = rw
				self.mappings.append(range)

		def identitymap(self, range, other, otherrange):
				def Accessor(mem, write, addr, byte):
						if write:
								other.raw = True
								other[addr - range.start] = byte
								return

						other.raw = True
						return other[addr - range.start]

				self.map(range, Accessor)

		def write(self, addr, bytes, selector):
			page = self.cpu.cpu.readpage(selector)

			if page != None:
				print(page.access)
				input()
				if page.access == 0:
					raise Exception("Access Exception")


			for i in range(len(bytes)):
						self[addr + i] = bytes[i]

		def __getitem__(self, key):
				for mapping in self.mappings:
						if key >= mapping.start and key <= mapping.end and not self.raw:
								return mapping.accessor(self, False, key, None)

				self.raw = False
				return self.data[key]

		def __setitem__(self, key, item):
				if item.__class__ == str and len(item) > 1:
						raise Exception("Value must be a byte")
				elif item.__class__ == int and item > 255:
						raise Exception("Value must be a byte")

				for mapping in self.mappings:
						if key >= mapping.start and key <= mapping.end and not self.raw:
								mapping.accessor(self, True, key, item)

								return

				self.raw = False
				self.data[key] = item

		def insert(self, key, item):
				raise Exception("Cannot append to RAM")

		def __len__(self):
				return self.size

		def __delitem__(self, key):
				self.data[key] = 0

		def __init__(self, cpu, size):
			self.cpu = cpu
			self.data = [0] * size	# One megabyte
			self.size = size
			self.mappings = []
			self.raw = False


class ROM(RAM):
	def insert(self, key, item):
		raise Exception("Cannot append to ROM")

	def __setitem__(self, key, item):
		if item.__class__ == str and len(item) > 1:
			raise Exception("Value must be a byte")
		elif item.__class__ == int and item > 255:
			raise Exception("Value must be a byte")

		if self.readonly:
			raise Exception("Cannot write to read-only ROM")

		for mapping in self.mappings:
			if key >= mapping.start and key <= mapping.end and not self.raw:
				mapping.accessor(self, True, key, item)

				return

		self.raw = False
		self.data[key] = item

	def lock(self):
		self.readonly = True

	def __init__(self, cpu, size):
		self.cpu = cpu
		self.data = [0] * size	# One megabyte
		self.size = size
		self.mappings = []
		self.readonly = False


# Helper class for making pages
class Page:
		# Serializes to 1 byte
		# index

	def serialize(self):
		return [self.base]

	def __init__(self, cpu, index):
		# I had to use spaces to indent here
		# Because python sucks and for some reason pure tabs is "inconsistant use of tabs and spaces"
		self.base = 255 * index
		self.access = cpu.readraw(None, 5)
		# print("Page Access: ", self.access)

# Manages stuff like memory translation
class MMU:
		def _isinrange(self, range, addr):
				return addr >= range.start and addr <= range.end

		# Translates addr into a physical address
		# Does nothing if protections aren't enabled
		def translate(self, selector, addr):

				if self.cpu.flags & 1:

						if self._isinrange(MemoryRange(0, 32), addr) and selector == 0:
								return addr

						page = self.cpu.readpage(selector or 0)

						if addr + page.base >= page.base + 255:
								raise AccessError(
										"Accessing offset %i of page selector 0x%X exceeded page boundary"
										% (addr, selector))

						# addr is an offset into the page
						return abs(page.base + addr)

						#if not self._isinrange(MemoryRange(seg.base, seg.base + seg.size), addr):
						#raise AccessError("Unable to access memory at 0x%X using page selector 0x%X" % (addr, page or 0))

				return addr

		def __init__(self, cpu):
				self.cpu = cpu


class CPU:
		# Not really useful, programs don't know where python added pages are
		# And it interferes with programs that expect certain pages in certain places
		def addpage(self, page, access):
		# We don't need a page to write to the page descriptor block
			self.write(None, self.segselector, page.base)
			self.segselector += 1
			self.write(None, self.segselector, access)
			self.segselector += 1

		def readpage(self, selector):
			if selector == None:
				return None
		
				# Must be physical
			return Page(self, selector)

		# Read an address from the program
		def readaddr(self, location):
				first = self.read(self.cs, location)

				if self.flags & 1:
						page = int(first)

						# Read address using page and return it
						return {"page": page, "address": self.read(self.cs, location + 1)}

				if self.addrsize == 2:
						second = self.read(self.cs, location + 1)
				else:
						second = first
						first = 0

				return {"page": None, "address": int(str(first) + str(second))}


	# Read an address from the program
		def readaddrraw(self, location):
				first = self.readraw(self.cs, location)

				if self.flags & 1:
						page = int(first)

						# Read address using page and return it
						return {"page": page, "address": self.readraw(self.cs, location + 1)}

				if self.addrsize == 2:
						second = self.readraw(self.cs, location + 1)
				else:
						second = first
						first = 0

				return {"page": None, "address": int(str(first) + str(second))}

		def read(self, page, address):
				return self.ram[self.mmu.translate(page, address)]

		def readraw(self, page, address):
				return self.ram[address]

		# Set a register based off of its identification byte
		def setregister(self, reg, byte):
				if reg == 0x1:
						self.a = byte
				elif reg == 0x2:
						self.b = byte
				elif reg == 0x3:
						self.cs = byte
				else:
						raise Exception("Unknown register identifier 0x%X" % reg)

		# Same as above but for reading
		def getregister(self, reg):
				if reg == 0x1:
						return self.a
				elif reg == 0x2:
						return self.b
				else:
						raise Exception("Unknown register identifier 0x%X" % reg)

		# Write to an address with a page(Always passed even if pageation is off)
		def write(self, page, address, byte):
			if page and self.readpage(page).access == 0:
				print("Access: ", self.readpage(page).access)
				raise AccessError()
		
			self.ram[self.mmu.translate(page, address)] = byte

		# Processes one full instruction
		def cycle(self):
				op = self.readraw(self.cs, self.pc)

				if self.debug:
						print("Executing opcode 0x%X" % op)

				# nop
				if op == 0x0:
						self.pc += 1
						return

				# move page ADDRESS BYTE
				if op == 0x1:
						self.pc += 1
						addr = self.readaddrraw(self.pc)
						self.pc += self.addrsize
						byte = self.readraw(self.cs, self.pc)
						self.pc += 1
						self.write(addr["page"] or self.cs, addr["address"], byte)
						return

				# move page ADDRESS = REGISTER
				if op == 0x12:
						self.pc += 1
						addr = self.readaddr(self.pc)
						self.pc += self.addrsize
						byte = self.read(self.cs, self.pc)
						self.pc += 1
						self.write(addr["page"] or self.cs, addr["address"],
											 self.getregister(byte))

						return

				# move REGISTER = page ADDRESS
				if op == 0x13:
						self.pc += 1
						reg = self.read(self.cs, self.pc)
						self.pc += 1
						addr = self.readaddr(self.pc)
						self.pc += self.addrsize

						byte = self.read(addr["page"] or self.cs, addr["address"])

						self.setregister(reg, byte)

						return

				# move page ADDRESS = [REGISTER]
				if op == 0x14:
						self.pc += 1
						addr = self.readaddr(self.pc)
						self.pc += self.addrsize
						reg = self.read(self.cs, self.pc)
						self.pc += 1
						byte = self.getregister(reg)

						self.write(addr["page"] or self.cs, addr["address"],
											 self.read(self.cs, byte))
						return

				# move page [REGISTER] = page ADDRESS
				if op == 0x15:
						self.pc += 1
						seg = self.read(self.cs, self.pc)
						self.pc += 1
						reg = self.read(self.cs, self.pc)
						assignee = self.getregister(reg)
						self.pc += 1
						addr = self.readaddr(self.pc)
						self.pc += self.addrsize

						self.write(seg, assignee,
											 self.read(addr["page"] or self.cs, addr["address"]))
						return

				# move page [REGISTER] = page [REGISTER]
				if op == 0x16:
						self.pc += 1
						seg = self.read(self.cs, self.pc)
						self.pc += 1
						reg = self.read(self.cs, self.pc)
						assignee = self.getregister(reg)
						self.pc += 1
						seg2 = self.read(self.cs, self.pc)
						self.pc += 1
						reg2 = self.read(self.cs, self.pc)
						addr = self.getregister(reg2)
						self.pc += 1

						if self.debug:
								print("Moving 0x%X:0x%X to 0x%X:0x%X" %
											(seg2, self.read(seg2, addr), seg, assignee))

						self.write(seg, assignee, self.read(seg2, addr))
						return

				# move REGISTER | PAGE [REGISTER]
				if op == 0x17:
						self.pc += 1
						assignee = self.read(self.cs, self.pc)
						self.pc += 1
						page = self.read(self.cs, self.pc)
						self.pc += 1
						addr = self.getregister(self.readraw(self.cs, self.pc))
						self.pc += 1

						self.setregister(assignee, self.read(page, addr))
						return

				# jump page ADDRESS
				if op == 0x3:
						self.pc += 1
						addr = self.readaddrraw(self.pc)
						self.pc += self.addrsize
						self.cs = addr["page"]
						self.pc = self.mmu.translate(addr["page"], addr["address"])
						if self.cs != 0:	# HACK
								self.pc -= 29

						return

				# jump if zero page ADDRESS
				# Jumps if the A register is zero
				if op == 0x34:
						if not self.a == 0:
								self.pc += self.addrsize + 1
								return

						self.pc += 1
						addr = self.readaddr(self.pc)
						self.pc += self.addrsize
						self.cs = addr["page"]
						self.pc = self.mmu.translate(addr["page"], addr["address"])
						if self.cs != 0:	# HACK
								self.pc -= 29

						return

				# reg REGISTER BYTE
				if op == 0x4:
						self.pc += 1
						reg = self.readraw(self.cs, self.pc)
						self.pc += 1
						byte = self.readraw(self.cs, self.pc)
						self.pc += 1

						self.setregister(reg, byte)
						return

				# reg REGISTER REGISTER
				if op == 0x45:
						self.pc += 1
						reg = self.read(self.cs, self.pc)
						self.pc += 1
						reg2 = self.read(self.cs, self.pc)
						self.pc += 1

						self.setregister(reg, self.getregister(reg2))
						return

				# add
				# Adds register A and B
				# Result goes back into A
				if op == 0x5:
						self.pc += 1
						self.a = self.a + self.b
						return

				# sub
				if op == 0x56:
						self.pc += 1
						self.a = self.a - self.b
						return

				# mul
				if op == 0x57:
						self.pc += 1
						self.a = self.a * self.b
						return

				# div
				if op == 0x58:
						self.pc += 1
						self.a = self.a / self.b
						return

				# enable paging (Allows addressing more than 255 bytes of memory)
				if op == 0x0F:
						self.addrsize = 2	# Address size is now 2 bytes, one byte for page selector and another for the offset in it
						self.pc += 1
						self.flags |= 1
						return

				# disable paging
				if op == 0x0E:
						self.addrsize = 1	# Address size is now 1 byte
						self.flags ^= 1
						self.pc += 1
															# Convert physical address to a page offset
						return

				# Halts the CPU
				if op == 0xFF:
						self.pc += 1
						self.halted = True
						return

				raise CPUError("Unrecognized opcode: 0x%X" % op)

		def __init__(self, com, mode):
				self.ram = com.ram	# 1 megabyte
				self.pc = 33	# Program counter (Uses page)
				self.mmu = MMU(self)
				self.halted = False
				self.com = com

				# Changes address size, added 1 byte mode to make it easier to reach mem limits(So I can simulate ways of working with them)
				if mode != 2 and mode != 1:
						raise Exception("Addressing mode must be either 1 or 2")

				self.segselector = 0

				self.cs = 0
				self.ds = 0

				self.a = 0
				self.b = 0

				self.addrsize = 1
				self.flags = 0	# flags & 1 = pages enabled

				# If paging is enabled programs might still need to modify the page descriptors
				self.addpage(Page(self, 0), 0xFF)

				self.debug = False


class Computer:
		def _loadbios(self):
				for i in range(33, len(self.bios) + 32 + 1):
						self.ram[i] = self.bios[i - 33]

				self.userstart = len(
						self.bios) + 32 + 1	# Where the user program starts

		def boot(self):
				while not self.cpu.halted:
						self.cpu.cycle()

		# Finds an unused page
		def _free(self, start, pages):
				for index in range(start, start + pages):
						clear = False
						for i in range(255 * index, 255 * index + 255):
								self.ram.raw = True
								if self.ram[i] != 0:
										break

						if clear:
								return (255 * index, 255)

		def load(self, rom, bytes):
				addr = self._free(3, 1)

				if bytes > addr[1]:
						raise Exception("Bytes exceeded page boundary")

				for i in range(bytes):
						self.ram.raw = True
						self.ram[addr[0] + i] = bytes[i]

		# Continues execution
		def run(self):
				self.cpu.halted = False

				while not self.cpu.halted:
						self.cpu.cycle()

		def __init__(self):
				self.ram = RAM(self, (1024 * 1024))
				self.cpu = CPU(self, 1)
				self.bios = ROM(self, 128)
				self.loader = ROM(self, 128)
				self.bytemode = True	# If this is set when loading images it will try to choose a spot with enough room!
				biosasm = Assembler(True, "bios.asm")
				loaderasm = Assembler(True, "loader.asm")

				bytes = biosasm.interpret()

				for i in range(len(bytes)):
						self.bios[i] = bytes[i]

				bytes = loaderasm.interpret()

				for i in range(len(bytes)):
						self.loader[i] = bytes[i]

				self.bios.lock()
				self.loader.lock()

				self.storage = ROM(self, 
						1024
				)	# KB of storage, need to make some hardware classes for permanent storage.

				self.ram.identitymap(
						MemoryRange(1020, 1020 + 0xFF), self.loader, MemoryRange(0, 0xFF))

				self._loadbios()
