#!/usr/bin/env python3

import configparser
import os
import re
import sys

from app import App
from emulator import Emulator
from tkinter import messagebox


def poll_emulator(app: App, emu: Emulator):
    try:
        if emu.process_is_running():
            process_info = f"\"{emu.proc.name}\" ({emu.proc.pid})"
            app.set_field('Emulator', f"Found. {process_info}")

            if emu.rom_is_valid():
                supported = 'Supported'
                try:
                    rom_name = emu.supported_config[emu.rom_id]['name']
                except Exception as e:
                    rom_name = f"{emu.crc1}-{emu.crc2}"
            else:
                supported = 'Not supported'
                rom_name = f"{emu.crc1}-{emu.crc2}"
            app.set_field('Game ROM', f"{supported}. \"{rom_name}\"")
        else:
            app.set_field('Emulator', 'Not Found.')
            app.set_field('Game ROM', f'Not Found.')

    except Exception as e:
        template = (
            "An error occurred when checking the emulator:\n\n"
            "Type: {0}\n"
            "Message:{1}"
        )
        message = template.format(type(e).__name__, e.args)
        messagebox.showerror(title='Stream Tool', message=message)
        sys.exit(1)


def update_port(emu: Emulator, port: int, text: str):
    emu.write_name(port+16, text)


def main(file):
    # https://pyinstaller.org/en/stable/runtime-information.html
    if getattr(sys, 'frozen', False):
        self_path = os.path.dirname(sys.executable)
    elif __file__:
        self_path = os.path.dirname(__file__)

    try:
        config = configparser.ConfigParser()
        config.read(os.path.join(self_path, file))

        if 'app' in config.sections():
            app_config = dict(config.items('app'))
        else:
            app_config = {}

        process_config = dict(config.items('process'))
        supported_config = {}

        for section in config.sections():
            if re.match(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{8}$', section):
                supported_config[section] = dict(config.items(section.upper()))

    except Exception as e:
        template = (
            "An error occurred when reading the config '{0}':\n\n"
            "Type: {1}\n"
            "Message:{2}"
        )
        message = template.format(file, type(e).__name__, e.args)
        messagebox.showerror(title='Stream Tool', message=message)
        sys.exit(1)

    emulator = Emulator(process_config, supported_config)
    app = App(app_config, emulator, poll_emulator, update_port)
    app.mainloop()


if __name__ == '__main__':
    main('stream-tool.ini')
