import customtkinter as ctk
from tkinter import filedialog
import os
from midi_parser import parse_midi, get_channels_info
from player import MidiPlayer

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Blue Protocol MIDI Bard Player")
        self.geometry("500x600")
        self.player = MidiPlayer()
        self.events = []
        self.channels = []
        self.channel_vars = []

        # UI Setup
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # Title
        self.title_label = ctk.CTkLabel(self, text="BPSR MIDI Bard Player", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # File Selection
        self.file_frame = ctk.CTkFrame(self)
        self.file_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.file_frame.grid_columnconfigure(0, weight=1)

        self.file_label = ctk.CTkLabel(self.file_frame, text="No file selected")
        self.file_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.load_btn = ctk.CTkButton(self.file_frame, text="Load MIDI", command=self.load_file)
        self.load_btn.grid(row=0, column=1, padx=10, pady=10)

        # Controls
        self.control_frame = ctk.CTkFrame(self)
        self.control_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        self.control_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.play_btn = ctk.CTkButton(self.control_frame, text="Play", command=self.play, fg_color="green", hover_color="darkgreen")
        self.play_btn.grid(row=0, column=0, padx=10, pady=10)

        self.pause_btn = ctk.CTkButton(self.control_frame, text="Pause", command=self.pause, fg_color="orange", hover_color="darkorange")
        self.pause_btn.grid(row=0, column=1, padx=10, pady=10)

        self.stop_btn = ctk.CTkButton(self.control_frame, text="Stop", command=self.stop, fg_color="red", hover_color="darkred")
        self.stop_btn.grid(row=0, column=2, padx=10, pady=10)

        # Channel Selector
        self.channel_frame = ctk.CTkScrollableFrame(self, label_text="Active Channels")
        self.channel_frame.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")

        # Global hotkey info
        self.info_label = ctk.CTkLabel(self, text="Ensure Blue Protocol is in focus when playing!\nKeys mapped: Base C3-B5. Auto Octave Toggles.", text_color="gray")
        self.info_label.grid(row=4, column=0, padx=20, pady=10)

    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("MIDI Files", "*.mid *.midi")])
        if file_path:
            filename = os.path.basename(file_path)
            self.file_label.configure(text=filename)
            self.stop()
            
            self.events = parse_midi(file_path)
            self.channels = get_channels_info(self.events)
            self.build_channel_ui()
            
            self.player.load_events(self.events, self.channels)

    def build_channel_ui(self):
        # Clear existing
        for widget in self.channel_frame.winfo_children():
            widget.destroy()
            
        self.channel_vars = []
        for ch in self.channels:
            var = ctk.BooleanVar(value=True)
            cb = ctk.CTkCheckBox(self.channel_frame, text=f"Channel {ch}", variable=var, command=self.update_channels)
            cb.pack(pady=5, anchor="w", padx=10)
            self.channel_vars.append((ch, var))

    def update_channels(self):
        active = [ch for ch, var in self.channel_vars if var.get()]
        self.player.set_active_channels(active)

    def play(self):
        if not self.events:
            return
        self.player.play()

    def pause(self):
        self.player.pause()

    def stop(self):
        self.player.stop()

    def destroy(self):
        self.player.stop()
        super().destroy()

if __name__ == "__main__":
    app = App()
    app.mainloop()
