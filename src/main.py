#!/usr/bin/env python3

import os
import sys
import requests
import yaml
import traceback
import json

from .app import App
from .emulator import Emulator

from tkinter import messagebox


def poll_emulator(app: App, emu: Emulator):
    try:
        id_to_character = app.app_config["id_to_character"]

        if emu.process_is_running():
            prev_game_data = app.game_data

            process_info = f"\"{emu.proc.name}\" ({emu.proc.pid})"
            app.set_field('Emulator', f"Found. {process_info}")

            emu.rom_is_valid()
            rom_name = f"{emu.crc1}-{emu.crc2}"
            app.set_field('ROM CRC', rom_name)

            try:
                gameData = {
                    "screen": "",
                    "screen_id": -1,
                    "slots": []
                }

                gameScreen = int.from_bytes(
                    emu.read_game_bytes(0x800A4AD0 + 0x3, 1), "little")

                gameData["screen_id"] = gameScreen

                gameData["screen"] = app.app_config["game_screen"].get(
                    gameScreen, "Other")

                pObject = int.from_bytes(
                    emu.read_game_bytes(0x800466FC, 4), "little")
                pStruct = int.from_bytes(
                    emu.read_game_bytes(pObject + 0x84, 4), "little")
                print(f"pObject {pObject:X} | pStruct {pStruct:X}")

                for i in range(4):
                    slotData = {}

                    print(f"Object: 0x{pObject:08X}")
                    print(f"Struct: 0x{pStruct:08X}")

                    slotData["character_id"] = int.from_bytes(
                        emu.read_game_bytes(pStruct + 0x8, 4), 'little')

                    slotData["character_name"] = id_to_character.get(
                        slotData["character_id"], "Unknown")

                    slotData["costume"] = int.from_bytes(
                        emu.read_game_bytes(pStruct + 0x13, 1), 'little')

                    slotData["placement"] = int.from_bytes(
                        emu.read_game_bytes(0x80139BB0 + 0x4 * i, 1), 'little')

                    # Sonic uses a special flag for his classic costume
                    if id_to_character.get(slotData["character_id"]) == "Sonic":
                        classic_bit = int.from_bytes(
                            emu.read_game_bytes(app.app_config["sonic_classic_table_address"] + 0x3 - 0x1*i, 1), 'little')

                        if classic_bit != 0:
                            slotData["costume"] += 6

                    # TODO: Team=0x000C, PlayerType=0x0023

                    gameData["slots"].append(slotData)

                    nextObjPos = int.from_bytes(
                        emu.read_game_bytes(pStruct, 4), "little")

                    if (nextObjPos != 0):
                        pStruct = nextObjPos
                    else:
                        break

                if len(gameData["slots"]) != 4:
                    gameData = prev_game_data

                app.set_field("Game Data", json.dumps(gameData, indent=2))
                app.game_data = gameData

                # Post data to TSH
                if gameData["screen"] == "VS_BATTLE":
                    for t in [0, 1]:
                        if (gameData["slots"][t]["character_id"]):
                            json_data = {
                                "mains": {"ssb64": [[
                                    id_to_character.get(
                                        gameData["slots"][t]["character_id"]
                                    ),
                                    gameData["slots"][t]["costume"]
                                ]]}
                            }

                            response = requests.post(
                                f"http://127.0.0.1:5000/scoreboard{0}-update-team-{t-1}-{0}", json=json_data)

                            if response.status_code == 200:
                                print("Data posted successfully")
                            else:
                                print("Failed to post data. Status code:",
                                      response.status_code)

                # Increment Score
                print(prev_game_data.get("screen"), gameData.get("screen"))
                if prev_game_data.get("screen") != "RESULTS" and gameData.get("screen") == "RESULTS":
                    if gameData["slots"][0]["placement"] == 0:
                        requests.get(
                            f"http://127.0.0.1:5000/scoreboard{0}-team{1}-scoreup")
                    elif gameData["slots"][1]["placement"] == 0:
                        requests.get(
                            f"http://127.0.0.1:5000/scoreboard{0}-team{2}-scoreup")
            except Exception as e:
                print(traceback.format_exc())
        else:
            app.set_field('Emulator', 'Not Found.')
            app.set_field('ROM CRC', f'Not Found.')
            app.set_field('Game Data', "{}")

    except Exception as e:
        template = (
            "An error occurred when checking the emulator:\n\n"
            "Type: {0}\n"
            "Message:{1}"
        )
        message = traceback.format_exc()
        messagebox.showerror(title='Stream Tool', message=message)
        sys.exit(1)


def poll_tsh(app: App, emu: Emulator):
    try:
        resp = requests.get("http://127.0.0.1:5000/program-state")
        app.set_field("TSH", "Detected")
    except Exception as e:
        app.set_field("TSH", "Not detected")
        print(e)


def main():
    # https://pyinstaller.org/en/stable/runtime-information.html
    if getattr(sys, 'frozen', False):
        self_path = os.path.dirname(sys.executable)
    elif __file__:
        self_path = os.path.dirname(__file__)

    try:
        config = yaml.load(open("config.yml", 'r'), yaml.SafeLoader)
        print(f"Loaded config: {config}")
    except Exception as e:
        template = (
            "An error occurred when reading the config '{0}':\n\n"
            "Type: {1}\n"
            "Message:{2}"
        )
        message = template.format("", type(e).__name__, e.args)
        messagebox.showerror(title='Stream Tool', message=message)
        sys.exit(1)

    emulator = Emulator(config["process"])
    app = App(
        config,
        emulator,
        poll_emulator,
        poll_tsh
    )
    app.mainloop()


if __name__ == '__main__':
    main()
