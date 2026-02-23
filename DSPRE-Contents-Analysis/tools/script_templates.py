#!/usr/bin/env python3
"""
script_templates.py

Generates common DSPRE script patterns as text that can be appended to .script
files. Outputs to stdout or a file.

Usage:
    python tools/script_templates.py item-pickup --item 77 --quantity 1 --flag 2571 --script-num 10
    python tools/script_templates.py npc-dialogue --message 0 --script-num 5
    python tools/script_templates.py hm-rocksmash --flag 2572 --script-num 11
    python tools/script_templates.py hm-cut --flag 2573 --script-num 12
    python tools/script_templates.py trainer-battle --trainer-id 50 --script-num 3 --flag 0
    python tools/script_templates.py list

Each template prints the exact text to paste into a .script file.
The --script-num is what the overworld CSV's `script` column should reference.

Standard-library only.
"""

from __future__ import annotations

import argparse
import sys
import textwrap


def template_item_pickup(script_num: int, item_id: int, quantity: int, flag: int) -> str:
    """
    Item ball on the ground. Player walks up, receives item, flag is set to
    prevent re-pickup. The overworld should have type=ITEM, flag=<flag>.

    Uses CommonScript 2033 which handles the "obtained ITEM" fanfare + message.
    """
    return textwrap.dedent(f"""\
        Script {script_num}:
        \tLockAll
        \tSetVar 0x8004 {item_id}
        \tSetVar 0x8005 {quantity}
        \tCheckItemSpace 0x8004 0x8005 0x800C
        \tCompareVarValue 0x800C 0
        \tJumpIf EQUAL Function#{script_num}_full
        \tCommonScript 2033
        \tSetFlag {flag}
        \tReleaseAll
        End

        Function {script_num}_full:
        \tMessage 0
        \tWaitButton
        \tCloseMessage
        \tReleaseAll
        End
        """)


def template_npc_dialogue(script_num: int, message: int) -> str:
    """Simple NPC that says one message then releases."""
    return textwrap.dedent(f"""\
        Script {script_num}:
        \tLockAll
        \tFacePlayer
        \tMessage {message}
        \tWaitButton
        \tCloseMessage
        \tReleaseAll
        End
        """)


def template_hm_rocksmash(script_num: int, flag: int) -> str:
    """
    Rock Smash obstacle. Checks if player can use Rock Smash, plays animation,
    sets flag to remove the rock permanently.

    The overworld should use the rock-smash rock overlay_entry and flag=<flag>.
    """
    return textwrap.dedent(f"""\
        Script {script_num}:
        \tLockAll
        \tCheckFlag {flag}
        \tJumpIf TRUE Function#{script_num}_done
        \tRockSmashItemCheck
        \tSetFlag {flag}
        \tReleaseAll
        End

        Function {script_num}_done:
        \tReleaseAll
        End
        """)


def template_hm_cut(script_num: int, flag: int) -> str:
    """
    Cut tree obstacle. Checks if player can Cut, plays animation, sets flag.
    """
    return textwrap.dedent(f"""\
        Script {script_num}:
        \tLockAll
        \tCheckFlag {flag}
        \tJumpIf TRUE Function#{script_num}_done
        \tCutAnimation 0
        \tSetFlag {flag}
        \tReleaseAll
        End

        Function {script_num}_done:
        \tReleaseAll
        End
        """)


def template_trainer_battle(script_num: int, trainer_id: int, flag: int) -> str:
    """
    Trainer NPC. When talked to / spotted, initiates a trainer battle.

    The overworld should have type=TRAINER. The flag (if non-zero) controls
    post-battle visibility (flag set = trainer hidden after defeat).

    Note: HGSS typically uses TrainerBattle command with the trainer ID.
    The exact command encoding depends on the game engine but the pattern is:
    """
    flag_lines = ""
    if flag:
        flag_lines = f"\tSetFlag {flag}\n"
    return textwrap.dedent(f"""\
        Script {script_num}:
        \tLockAll
        \tFacePlayer
        \tTrainerBattle {trainer_id}
        {flag_lines}\tReleaseAll
        End
        """)


def cmd_list() -> None:
    print("Available templates:")
    print("  item-pickup     -- Item ball on ground (GiveItem + flag)")
    print("  npc-dialogue    -- Simple NPC message")
    print("  hm-rocksmash    -- Rock Smash obstacle")
    print("  hm-cut          -- Cut tree obstacle")
    print("  trainer-battle  -- Trainer encounter")
    print()
    print("Each template outputs script text for pasting into a .script file.")
    print("Use --script-num to set the Script N: number the event CSV references.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate DSPRE script templates.")
    sub = parser.add_subparsers(dest="template")

    sub.add_parser("list", help="List available templates.")

    item = sub.add_parser("item-pickup", help="Item pickup script.")
    item.add_argument("--item", type=int, required=True, help="Item ID (numeric).")
    item.add_argument("--quantity", type=int, default=1, help="Quantity (default 1).")
    item.add_argument("--flag", type=int, required=True, help="Flag to set after pickup.")
    item.add_argument("--script-num", type=int, required=True, help="Script number.")

    npc = sub.add_parser("npc-dialogue", help="NPC dialogue script.")
    npc.add_argument("--message", type=int, default=0, help="Message index.")
    npc.add_argument("--script-num", type=int, required=True, help="Script number.")

    rs = sub.add_parser("hm-rocksmash", help="Rock Smash obstacle script.")
    rs.add_argument("--flag", type=int, required=True, help="Flag to set after smash.")
    rs.add_argument("--script-num", type=int, required=True, help="Script number.")

    ct = sub.add_parser("hm-cut", help="Cut tree obstacle script.")
    ct.add_argument("--flag", type=int, required=True, help="Flag to set after cut.")
    ct.add_argument("--script-num", type=int, required=True, help="Script number.")

    tb = sub.add_parser("trainer-battle", help="Trainer battle script.")
    tb.add_argument("--trainer-id", type=int, required=True, help="Trainer ID.")
    tb.add_argument("--flag", type=int, default=0, help="Post-defeat flag (0=none).")
    tb.add_argument("--script-num", type=int, required=True, help="Script number.")

    args = parser.parse_args()
    if not args.template:
        parser.print_help()
        sys.exit(1)

    if args.template == "list":
        cmd_list()
    elif args.template == "item-pickup":
        print(template_item_pickup(args.script_num, args.item, args.quantity, args.flag))
    elif args.template == "npc-dialogue":
        print(template_npc_dialogue(args.script_num, args.message))
    elif args.template == "hm-rocksmash":
        print(template_hm_rocksmash(args.script_num, args.flag))
    elif args.template == "hm-cut":
        print(template_hm_cut(args.script_num, args.flag))
    elif args.template == "trainer-battle":
        print(template_trainer_battle(args.script_num, args.trainer_id, args.flag))


if __name__ == "__main__":
    main()
