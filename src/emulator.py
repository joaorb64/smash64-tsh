import re
import psutil
from ReadWriteMemory import ReadWriteMemory


class Emulator():
    def __init__(self, process_config, supported_config):
        self.process_config = process_config
        self.supported_config = supported_config
        self.offsets = {}
        self.proc = None
        self.exe = None
        self.rom_id = None

    def decode_name(self, data: bytes):
        # TODO: handle omega and music note
        return self.swap_bytes(data, 4).decode()

    def encode_name(self, data: str):
        # TODO: handle omega and music note
        encoded = re.sub(r'[^\x20-\x7E]', '?', data)[:20]
        buffer = bytes(encoded, encoding='utf-8').ljust(20, b'\0')
        return self.swap_bytes([hex(c) for c in buffer], 4)

    def get_emu_base(self):
        offset = int(self.process_config['base'], 0)
        base = self.proc.get_pointer(self.exe + offset)
        addr = self.proc.readByte(base, 4)
        return bytes([int(byte, 0) for byte in addr])

    def get_tag_base(self, index: int = 0):
        base = int.from_bytes(self.get_emu_base(), 'little')
        tag_offset = int(self.supported_config[self.rom_id]['tags'], 0)
        index_offset = 60 * index
        ptr = self.proc.get_pointer(base + tag_offset + index_offset)
        return ptr

    def process_is_running(self):
        if self.proc is not None and psutil.pid_exists(self.proc.pid):
            return True

        try:
            rwm = ReadWriteMemory()
            process = rwm.get_process_by_name(self.process_config['name'])

            if process:
                self.proc = process
                self.proc.open()
                self.exe = self.proc.get_modules()[0]
                return True
        except Exception as e:
            return False

        return False

    def read_emu_bytes(self, offset: int, size: int = 1):
        base = int.from_bytes(self.get_emu_base(), 'little')
        ptr = self.proc.get_pointer(base + offset)
        raw_bytes = self.proc.readByte(ptr, size)
        return bytes([int(byte, 0) for byte in raw_bytes])

    def read_name(self, index: int):
        if self.rom_id is not None:
            ptr = self.get_tag_base(index)
            raw_bytes = self.proc.readByte(ptr, 20)
            return self.decode_name(raw_bytes)
        else:
            return None

    def read_rom_crc(self, offset: int):
        ptr = self.proc.get_pointer(self.exe + int(offset, 0))
        raw_bytes = self.proc.readByte(ptr, 4)
        value = bytes([int(byte, 0) for byte in raw_bytes])
        return f"{int.from_bytes(value, 'little'):x}".upper()

    def rom_is_valid(self):
        if self.process_is_running():
            self.crc1 = self.read_rom_crc(self.process_config['crc1'])
            self.crc2 = self.read_rom_crc(self.process_config['crc2'])
            rom_crcs = f"{self.crc1}-{self.crc2}"

            if rom_crcs in self.supported_config:
                self.rom_id = rom_crcs

            return rom_crcs in self.supported_config
        else:
            return False

    def swap_bytes(self, data: list, size: int = 4):
        swapped = []
        while len(data) % size != 0:
            data.append(b'\0')
        for i in range(0, len(data), size):
            [swapped.append(int(j, 0)) for j in data[i:i+size][::-1]]
        return bytes(swapped)

    def write_name(self, index: int, data: list):
        if self.rom_id is not None:
            ptr = self.get_tag_base(index)
            self.proc.writeByte(ptr, bytes(self.encode_name(data)))
