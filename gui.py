import customtkinter as ctk
from tkinter import filedialog
import os
import tempfile
from midi_parser import parse_midi, get_channels_info
from player import MidiPlayer
from network_sync import NetworkManager

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Blue Protocol MIDI Bard Player - Multiplayer")
        self.geometry("650x750")
        self.player = MidiPlayer()
        self.network = NetworkManager(
            on_state_change=self.on_network_state,
            on_play_cmd=self.on_network_play,
            on_stop_cmd=self.on_network_stop,
            on_midi_received=self.on_network_midi
        )
        
        self.events = []
        self.channels = []
        self.channel_vars = []
        self.host_checkbox_vars = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Global File Header (Always visible)
        self.global_file_frame = ctk.CTkFrame(self)
        self.global_file_frame.grid(row=0, column=0, padx=20, pady=(20, 0), sticky="ew")
        
        self.file_label = ctk.CTkLabel(self.global_file_frame, text="No file selected", font=ctk.CTkFont(weight="bold"))
        self.file_label.pack(side="left", padx=10, pady=10)
        
        self.led_label = ctk.CTkLabel(self.global_file_frame, text="🔴 Stopped", font=ctk.CTkFont(weight="bold"), width=120)
        self.led_label.pack(side="left", padx=20, pady=10)
        
        self.load_btn = ctk.CTkButton(self.global_file_frame, text="Load MIDI File", command=self.load_file)
        self.load_btn.pack(side="right", padx=10, pady=10)
        
        # Timeline / Progress
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        
        self.time_label = ctk.CTkLabel(self.progress_frame, text="00:00 / 00:00", width=80)
        self.time_label.pack(side="left", padx=5)
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=5)
        self.progress_bar.set(0)

        # Tabs
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        
        self.tab_solo = self.tabview.add("Solo Play")
        self.tab_multi = self.tabview.add("Multiplayer Lobby")

        self.setup_solo_tab()
        self.setup_multi_tab()
        
        self.update_led_loop()

    def setup_solo_tab(self):
        self.tab_solo.grid_columnconfigure(0, weight=1)
        self.tab_solo.grid_rowconfigure(1, weight=1)

        self.control_frame = ctk.CTkFrame(self.tab_solo)
        self.control_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.control_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.play_btn = ctk.CTkButton(self.control_frame, text="Play Solo", command=self.play_solo, fg_color="green", hover_color="darkgreen")
        self.play_btn.grid(row=0, column=0, padx=10, pady=10)
        self.pause_btn = ctk.CTkButton(self.control_frame, text="Pause", command=self.player.pause, fg_color="orange", hover_color="darkorange")
        self.pause_btn.grid(row=0, column=1, padx=10, pady=10)
        self.stop_btn = ctk.CTkButton(self.control_frame, text="Stop", command=self.player.stop, fg_color="red", hover_color="darkred")
        self.stop_btn.grid(row=0, column=2, padx=10, pady=10)

        self.channel_frame = ctk.CTkScrollableFrame(self.tab_solo, label_text="Solo Active Channels")
        self.channel_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

    def setup_multi_tab(self):
        self.tab_multi.grid_columnconfigure(0, weight=1)
        self.tab_multi.grid_rowconfigure(2, weight=1)

        # Connection Setup
        self.conn_frame = ctk.CTkFrame(self.tab_multi)
        self.conn_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.conn_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.nick_entry = ctk.CTkEntry(self.conn_frame, placeholder_text="Nickname")
        self.nick_entry.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.room_entry = ctk.CTkEntry(self.conn_frame, placeholder_text="Room Code")
        self.room_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        self.host_btn = ctk.CTkButton(self.conn_frame, text="Host Room", command=self.host_room)
        self.host_btn.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.join_btn = ctk.CTkButton(self.conn_frame, text="Join Room", command=self.join_room)
        self.join_btn.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # Status
        self.status_label = ctk.CTkLabel(self.tab_multi, text="Not Connected", text_color="gray")
        self.status_label.grid(row=1, column=0, pady=5)

        # Lobby List
        self.lobby_frame = ctk.CTkScrollableFrame(self.tab_multi, label_text="Lobby Players (Host assigns channels here)")
        self.lobby_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

        # Host Controls
        self.host_control_frame = ctk.CTkFrame(self.tab_multi)
        self.host_control_frame.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
        self.host_control_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.sync_play_btn = ctk.CTkButton(self.host_control_frame, text="SYNC PLAY (4s delay)", command=self.sync_play, fg_color="purple", hover_color="#5e0082", state="disabled")
        self.sync_play_btn.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        self.sync_stop_btn = ctk.CTkButton(self.host_control_frame, text="STOP SINC", command=self.sync_stop, fg_color="red", hover_color="darkred", state="disabled")
        self.sync_stop_btn.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

    # --- Actions ---

    def update_led_loop(self):
        if self.player.is_syncing:
            self.led_label.configure(text="🟡 Syncing...", text_color="yellow")
        elif self.player.is_playing:
            self.led_label.configure(text="🟢 Playing", text_color="green")
        else:
            self.led_label.configure(text="🔴 Stopped", text_color="gray")
            
        current = self.player.get_current_time()
        total = self.player.get_total_time()
        
        if total > 0:
            progress = max(0.0, min(1.0, current / total))
            self.progress_bar.set(progress)
            
            curr_m = int(current // 60)
            curr_s = int(current % 60)
            tot_m = int(total // 60)
            tot_s = int(total % 60)
            self.time_label.configure(text=f"{curr_m:02d}:{curr_s:02d} / {tot_m:02d}:{tot_s:02d}")
        else:
            self.progress_bar.set(0)
            self.time_label.configure(text="00:00 / 00:00")
            
        self.after(200, self.update_led_loop)

    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("MIDI Files", "*.mid *.midi")])
        if file_path:
            filename = os.path.basename(file_path)
            self.file_label.configure(text=filename)
            self.player.stop()
            self._parse_and_load(file_path)
            
            # If hosting, share to room
            if self.network.room_code and self.network.is_host:
                self.network.share_midi(file_path, filename)
            
            # Update lobby UI to show new checkboxes if host
            if self.network.room_code:
                self._update_lobby_ui(self.network.room_state)

    def _parse_and_load(self, file_path):
        self.events = parse_midi(file_path)
        self.channels = get_channels_info(self.events)
        self.build_solo_channel_ui()
        self.player.load_events(self.events, self.channels)

    def build_solo_channel_ui(self):
        for widget in self.channel_frame.winfo_children():
            widget.destroy()
        self.channel_vars = []
        for ch in self.channels:
            var = ctk.BooleanVar(value=True)
            cb = ctk.CTkCheckBox(self.channel_frame, text=f"Channel {ch}", variable=var, command=self.update_solo_channels)
            cb.pack(pady=5, anchor="w", padx=10)
            self.channel_vars.append((ch, var))

    def update_solo_channels(self):
        active = [ch for ch, var in self.channel_vars if var.get()]
        self.player.set_active_channels(active)

    def play_solo(self):
        self.update_solo_channels()
        if self.events:
            self.player.play()

    # --- Networking ---

    def host_room(self):
        nick = self.nick_entry.get() or "Host"
        room = self.room_entry.get() or "1234"
        self.network.connect()
        self.network.host_room(room, nick)
        self.status_label.configure(text=f"Hosting Room: {room} | Waiting for players...", text_color="green")
        self.sync_play_btn.configure(state="normal")
        self.sync_stop_btn.configure(state="normal")
        self.host_btn.configure(state="disabled")
        self.join_btn.configure(state="disabled")

    def join_room(self):
        nick = self.nick_entry.get() or "Player"
        room = self.room_entry.get()
        if not room:
            return
        self.network.connect()
        self.network.join_room(room, nick)
        self.status_label.configure(text=f"Joined Room: {room}", text_color="green")
        self.host_btn.configure(state="disabled")
        self.join_btn.configure(state="disabled")

    def sync_play(self):
        if self.events and self.network.is_host:
            self.player.stop()
            self.network.send_play(delay_seconds=4.0)
            
    def sync_stop(self):
        if self.network.is_host:
            self.network.send_stop()

    # --- Callbacks from NetworkManager (Run in background thread, schedule UI updates) ---

    def on_network_state(self, state):
        self.after(0, self._update_lobby_ui, state)

    def on_network_play(self, global_start_time, my_channels):
        self.after(0, self._trigger_play, global_start_time, my_channels)

    def on_network_stop(self):
        self.after(0, self.player.stop)

    def on_network_midi(self, filename, data):
        self.after(0, self._save_and_load_midi, filename, data)

    def _update_lobby_ui(self, state):
        for widget in self.lobby_frame.winfo_children():
            widget.destroy()
            
        fn = state.get("filename")
        if fn:
            ctk.CTkLabel(self.lobby_frame, text=f"🎵 Shared Song: {fn}", font=ctk.CTkFont(weight="bold")).pack(pady=5)

        self.host_checkbox_vars = {}

        for p in state["players"]:
            frame = ctk.CTkFrame(self.lobby_frame)
            frame.pack(fill="x", pady=5, padx=5)
            
            is_me = p['client_id'] == self.network.client_id
            name = f"{p['nickname']} (Me)" if is_me else p['nickname']
            
            # Status dot
            status_color = "green" if p.get("connected", True) else "red"
            status_text = "🟢" if p.get("connected", True) else "🔴"
            
            status_lbl = ctk.CTkLabel(frame, text=status_text, width=20)
            status_lbl.pack(side="left", padx=(10, 0), pady=10)
            
            lbl = ctk.CTkLabel(frame, text=name, width=120, anchor="w", font=ctk.CTkFont(weight="bold"))
            lbl.pack(side="left", padx=(5, 10), pady=10)
            
            if self.network.is_host:
                ch_frame = ctk.CTkScrollableFrame(frame, height=40, fg_color="transparent", orientation="horizontal")
                ch_frame.pack(side="left", fill="x", expand=True, padx=5)
                
                if not self.channels:
                    ctk.CTkLabel(ch_frame, text="Load a MIDI file first to assign channels.", text_color="gray").pack(side="left")
                else:
                    self.host_checkbox_vars[p['client_id']] = {}
                    for ch in self.channels:
                        var = ctk.BooleanVar(value=(ch in p["channels"]))
                        self.host_checkbox_vars[p['client_id']][ch] = var
                        
                        def on_toggle(cid=p['client_id']):
                            chs = [c for c, v in self.host_checkbox_vars[cid].items() if v.get()]
                            self.network.assign_channels(cid, chs)
                            
                        cb = ctk.CTkCheckBox(ch_frame, text=f"Ch {ch}", variable=var, command=on_toggle)
                        cb.pack(side="left", padx=10, pady=5)
            else:
                assigned_text = ", ".join(map(str, p['channels'])) if p['channels'] else "None"
                lbl2 = ctk.CTkLabel(frame, text=f"Assigned Channels: {assigned_text}", text_color="cyan")
                lbl2.pack(side="left", padx=10, pady=10)

    def _trigger_play(self, global_start_time, my_channels):
        delay = global_start_time - self.network.get_global_time()
        print(f"Network Play Triggered! Delaying start by {delay:.3f}s for Channels {my_channels}")
        self.player.stop()
        self.player.set_active_channels(my_channels)
        self.player.play(delay_seconds=delay)

    def _save_and_load_midi(self, filename, data):
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, filename)
        with open(file_path, "wb") as f:
            f.write(data)
        
        self.file_label.configure(text=f"{filename} (Received)")
        self._parse_and_load(file_path)

    def destroy(self):
        self.player.stop()
        self.network.disconnect()
        super().destroy()

if __name__ == "__main__":
    app = App()
    app.mainloop()
