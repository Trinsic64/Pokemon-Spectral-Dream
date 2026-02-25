"""NPC Editor Panel: AI-assisted dialogue generation."""

from __future__ import annotations

import threading

import customtkinter as ctk

from ..ai.client import AIClient
from ..ai.prompts import SYSTEM_PROMPT, build_user_prompt
from ..ai.parser import parse_response
from ..model.sub_events import SubEventChain


NPC_PURPOSES = [
    "Hint Giver",
    "Lore NPC",
    "Item Trader",
    "Move Tutor",
    "Quest NPC",
    "Flavor NPC",
    "Guide / Tutorial",
    "Rival Encounter",
]


class NPCPanel(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.ai_client = AIClient()
        self._last_result = None
        self._build()

    def _build(self):
        title = ctk.CTkLabel(self, text="NPC Editor (AI-Assisted)",
                             font=ctk.CTkFont(size=20, weight="bold"))
        title.pack(pady=(10, 5))

        self.target_label = ctk.CTkLabel(
            self, text="No header selected.",
            font=ctk.CTkFont(size=13), text_color="#f39c12")
        self.target_label.pack(pady=3)

        main = ctk.CTkFrame(self)
        main.pack(fill="both", expand=True, padx=10, pady=5)

        # === Left: NPC definition ===
        left = ctk.CTkFrame(main)
        left.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(left, text="NPC Definition",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(pady=5)

        # Purpose
        ctk.CTkLabel(left, text="Purpose:",
                     font=ctk.CTkFont(size=13)).pack(anchor="w", padx=15, pady=(5, 0))
        purpose_frame = ctk.CTkFrame(left, fg_color="transparent")
        purpose_frame.pack(fill="x", padx=10, pady=3)
        self.purpose_var = ctk.StringVar(value=NPC_PURPOSES[0])
        purpose_col1 = ctk.CTkFrame(purpose_frame, fg_color="transparent")
        purpose_col1.pack(side="left", fill="y", padx=5)
        purpose_col2 = ctk.CTkFrame(purpose_frame, fg_color="transparent")
        purpose_col2.pack(side="left", fill="y", padx=5)
        for i, purp in enumerate(NPC_PURPOSES):
            parent = purpose_col1 if i % 2 == 0 else purpose_col2
            ctk.CTkRadioButton(
                parent, text=purp, variable=self.purpose_var,
                value=purp, font=ctk.CTkFont(size=12),
            ).pack(anchor="w", padx=5, pady=1)

        # Sprite
        sprite_frame = ctk.CTkFrame(left, fg_color="transparent")
        sprite_frame.pack(fill="x", padx=10, pady=3)
        ctk.CTkLabel(sprite_frame, text="Sprite overlay:").pack(side="left", padx=5)
        self.sprite_var = ctk.IntVar(value=337)
        ctk.CTkEntry(sprite_frame, textvariable=self.sprite_var,
                     width=80).pack(side="left", padx=5)
        ctk.CTkLabel(sprite_frame, text="(337=generic NPC)",
                     text_color="#7f8c8d",
                     font=ctk.CTkFont(size=11)).pack(side="left", padx=5)

        # Description
        ctk.CTkLabel(left, text="Describe what the NPC should say/do:",
                     font=ctk.CTkFont(size=13)).pack(anchor="w", padx=15, pady=(10, 3))
        self.desc_text = ctk.CTkTextbox(left, height=150)
        self.desc_text.pack(fill="both", expand=True, padx=10, pady=5)
        self.desc_text.insert("0.0",
                              "A friendly old man who gives a hint about "
                              "the gym leader's weakness to Dark-type moves.")

        # Generate button
        self.gen_btn = ctk.CTkButton(
            left, text="Generate with AI",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40, fg_color="#9b59b6", hover_color="#8e44ad",
            command=self._generate)
        self.gen_btn.pack(pady=10, padx=20, fill="x")

        self.gen_status = ctk.CTkLabel(left, text="",
                                       font=ctk.CTkFont(size=12))
        self.gen_status.pack(pady=2)

        # === Right: preview + accept ===
        right = ctk.CTkFrame(main)
        right.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(right, text="Generated Preview",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(pady=5)

        ctk.CTkLabel(right, text="Dialogue:",
                     font=ctk.CTkFont(size=13)).pack(anchor="w", padx=10)
        self.dialogue_text = ctk.CTkTextbox(right, height=150)
        self.dialogue_text.pack(fill="both", expand=True, padx=10, pady=3)

        ctk.CTkLabel(right, text="Script Commands:",
                     font=ctk.CTkFont(size=13)).pack(anchor="w", padx=10)
        self.script_text = ctk.CTkTextbox(right, height=120)
        self.script_text.pack(fill="x", padx=10, pady=3)

        # Position
        pos_frame = ctk.CTkFrame(right, fg_color="transparent")
        pos_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(pos_frame, text="Position:").pack(side="left", padx=5)
        ctk.CTkLabel(pos_frame, text="X:").pack(side="left", padx=5)
        self.x_var = ctk.IntVar(value=10)
        ctk.CTkEntry(pos_frame, textvariable=self.x_var,
                     width=50).pack(side="left", padx=2)
        ctk.CTkLabel(pos_frame, text="Y:").pack(side="left", padx=5)
        self.y_var = ctk.IntVar(value=10)
        ctk.CTkEntry(pos_frame, textvariable=self.y_var,
                     width=50).pack(side="left", padx=2)
        ctk.CTkButton(pos_frame, text="Pick from Map", width=110,
                      command=self._pick_position).pack(side="left", padx=10)

        # Accept
        self.accept_btn = ctk.CTkButton(
            right, text="Accept & Add NPC",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40, fg_color="#2ecc71", hover_color="#27ae60",
            state="disabled",
            command=self._accept)
        self.accept_btn.pack(pady=10, padx=20, fill="x")

        self.result_label = ctk.CTkLabel(right, text="",
                                         font=ctk.CTkFont(size=12))
        self.result_label.pack(pady=3)

    def on_headers_changed(self):
        selected = self.app.selected_headers
        if selected:
            h = self.app.project.headers.headers.get(selected[0])
            if h:
                self.target_label.configure(
                    text=f"Target: {h.name} (H{h.number})",
                    text_color="#2ecc71")
        else:
            self.target_label.configure(
                text="No header selected.",
                text_color="#f39c12")

    def _generate(self):
        if not self.app.selected_headers:
            self.gen_status.configure(text="Select a header first!",
                                     text_color="#e74c3c")
            return

        api_key = self.app.setup_panel.api_var.get().strip()
        provider = self.app.setup_panel.api_provider.get()

        if not api_key:
            self.gen_status.configure(
                text="No API key set. Enter it in the Setup tab.",
                text_color="#e74c3c")
            return

        self.ai_client.configure(provider, api_key)
        self.gen_btn.configure(state="disabled")
        self.gen_status.configure(text="Generating...", text_color="#f39c12")

        h_num = self.app.selected_headers[0]
        h = self.app.project.headers.headers.get(h_num)

        description = self.desc_text.get("0.0", "end").strip()
        purpose = self.purpose_var.get()

        existing = []
        if h:
            ef = str(h.event_file).zfill(4)
            for ow in self.app.project.get_overworlds_for_event(ef):
                ow_type = ow.data.get("type", "NORMAL")
                existing.append(f"OW[{ow.index}] type={ow_type}")

        archive = self.app.project.text_archives.archives.get(
            h.text_archive if h else 0)
        next_msg = archive.message_count if archive else 0

        user_prompt = build_user_prompt(
            map_name=h.name if h else "Unknown",
            map_type=h.map_type if h else "Unknown",
            npc_purpose=purpose,
            description=description,
            existing_entities=existing,
            next_message_index=next_msg,
        )

        def do_generate():
            try:
                raw = self.ai_client.generate(SYSTEM_PROMPT, user_prompt)
                result = parse_response(raw)
                self.after(0, lambda: self._on_generated(result))
            except Exception as e:
                self.after(0, lambda: self._on_generate_error(str(e)))

        thread = threading.Thread(target=do_generate, daemon=True)
        thread.start()

    def _on_generated(self, result):
        self.gen_btn.configure(state="normal")
        self._last_result = result

        if not result.success:
            self.gen_status.configure(
                text=f"Generation issue: {result.error}",
                text_color="#f39c12")

        if result.dialogue_lines:
            self.gen_status.configure(
                text=f"Generated {len(result.dialogue_lines)} dialogue line(s)",
                text_color="#2ecc71")

        self.dialogue_text.delete("0.0", "end")
        for i, line in enumerate(result.dialogue_lines):
            self.dialogue_text.insert("end", f"[{i}] {line}\n")

        self.script_text.delete("0.0", "end")
        for cmd in result.script_commands:
            self.script_text.insert("end", f"{cmd}\n")

        if result.sprite_overlay:
            self.sprite_var.set(result.sprite_overlay)

        self.accept_btn.configure(state="normal" if result.dialogue_lines else "disabled")

    def _on_generate_error(self, error: str):
        self.gen_btn.configure(state="normal")
        self.gen_status.configure(text=f"Error: {error}", text_color="#e74c3c")

    def _pick_position(self):
        def on_click(x, y):
            self.x_var.set(x)
            self.y_var.set(y)
            if hasattr(self.app, 'preview_panel'):
                self.app.preview_panel.set_click_callback(None)

        if hasattr(self.app, 'preview_panel'):
            self.app.preview_panel.set_click_callback(on_click)
        self.app.set_tab("Map Preview")

    def _accept(self):
        if not self._last_result or not self.app.selected_headers:
            return

        h_num = self.app.selected_headers[0]
        h = self.app.project.headers.headers.get(h_num)
        if not h:
            return

        result = self._last_result
        ef = str(h.event_file).zfill(4)

        # Build deterministic sub-event chain for script bridge output.
        chain = SubEventChain(name=f"npc_h{h.number}_ow")

        # Add dialogue to text archive and keep message ids.
        inserted_message_ids: list[int] = []
        archive = self.app.project.text_archives.archives.get(h.text_archive)
        if archive:
            for line in result.dialogue_lines:
                msg_id = archive.add_message(line)
                inserted_message_ids.append(msg_id)
                chain.append("dialogue", message_id=msg_id)
            self.app.project.text_archives.save_archive(h.text_archive)
        else:
            # Keep chain valid even without a text archive by using placeholder IDs.
            for i, _line in enumerate(result.dialogue_lines):
                chain.append("dialogue", message_id=i)

        # If a path has been recorded in Pathing, include it in this NPC chain.
        path_lines = self.app.path_capture.to_action_lines()
        if path_lines:
            chain.append("movement_path", action_lines=path_lines)
        chain.append("end")
        artifact = self.app.script_bridge.build(chain)

        # Add overworld entity
        existing_ows = self.app.project.get_overworlds_for_event(ef)
        next_ow_id = max((e.index for e in existing_ows), default=-1) + 1

        existing_scripts = set()
        for ow in existing_ows:
            try:
                existing_scripts.add(int(ow.data.get("script", 0)))
            except ValueError:
                pass
        script_num = 1
        while script_num in existing_scripts:
            script_num += 1

        overlay = self.sprite_var.get()
        movement = result.movement_type

        edit = {
            "action": "add_overworld",
            "event_file": ef,
            "data": {
                "ow_id": str(next_ow_id),
                "overlay_entry": str(overlay),
                "type": "NORMAL",
                "movement": str(movement),
                "flag": "0",
                "script": str(script_num),
                "orientation": "1",
                "sight_range": "0",
                "x_range": "0",
                "y_range": "0",
                "x_map": str(self.x_var.get()),
                "x_matrix": "0",
                "y_map": str(self.y_var.get()),
                "y_matrix": "0",
                "z": "0",
            },
            "comment": f"NPC: {self.purpose_var.get()}",
            "generated_script": artifact.script_lines,
            "generated_movement": artifact.movement_lines,
            "generated_dialogue": result.dialogue_lines,
            "subevent_chain": chain.to_manifest(),
            "bridge_source": "deterministic_subevents",
        }
        self.app.add_pending_edit(edit)
        self.app.current_chain = chain
        self.app.latest_script_artifact = artifact

        self.result_label.configure(
            text=f"NPC added! OW[{next_ow_id}] script={script_num} "
                 f"at ({self.x_var.get()},{self.y_var.get()})",
            text_color="#2ecc71")
        self.accept_btn.configure(state="disabled")
