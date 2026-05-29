import ctypes
import time
import threading
from config import KEY_MAP, VK_LSHIFT, VK_LCONTROL, VK_SPACE, midi_to_note_name

SendInput = ctypes.windll.user32.SendInput
MapVirtualKey = ctypes.windll.user32.MapVirtualKeyW

# C struct definitions for Windows Input
PUL = ctypes.POINTER(ctypes.c_ulong)
class KeyBdInput(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort),
                ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]

class HardwareInput(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_ulong),
                ("wParamL", ctypes.c_short),
                ("wParamH", ctypes.c_ushort)]

class MouseInput(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long),
                ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]

class Input_I(ctypes.Union):
    _fields_ = [("ki", KeyBdInput),
                ("mi", MouseInput),
                ("hi", HardwareInput)]

class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong),
                ("ii", Input_I)]

KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

def press_key(hexKeyCode):
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    scan_code = MapVirtualKey(hexKeyCode, 0)
    ii_.ki = KeyBdInput(0, scan_code, KEYEVENTF_SCANCODE, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(1), ii_)
    SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

def release_key(hexKeyCode):
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    scan_code = MapVirtualKey(hexKeyCode, 0)
    ii_.ki = KeyBdInput(0, scan_code, KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(1), ii_)
    SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

def tap_key(hexKeyCode, duration=0.01):
    press_key(hexKeyCode)
    time.sleep(duration)
    release_key(hexKeyCode)

class BPSRInputSimulator:
    def __init__(self):
        self.current_octave_shift = 0 # 0: normal, 1: High, -1: Low
        self.sustain_active = False

    def toggle_high_octave(self):
        tap_key(VK_LSHIFT)
        self.current_octave_shift = 1
        
    def toggle_low_octave(self):
        tap_key(VK_LCONTROL)
        self.current_octave_shift = -1

    def reset_octave(self):
        if self.current_octave_shift == 1:
            tap_key(VK_LSHIFT)
        elif self.current_octave_shift == -1:
            tap_key(VK_LCONTROL)
        self.current_octave_shift = 0

    def set_octave_shift(self, target_shift):
        if self.current_octave_shift == target_shift:
            return
        self.reset_octave()
        if target_shift == 1:
            self.toggle_high_octave()
        elif target_shift == -1:
            self.toggle_low_octave()

    def set_sustain(self, active):
        if self.sustain_active != active:
            tap_key(VK_SPACE)
            self.sustain_active = active

    def press_note(self, midi_note):
        target_shift, base_note = self._get_mapping(midi_note)
        if base_note is None:
            return # Out of range
        
        self.set_octave_shift(target_shift)
        
        note_name = midi_to_note_name(base_note)
        vk_code = KEY_MAP.get(note_name)
        if vk_code:
            press_key(vk_code)
            # Release shortly after to prevent OS typematic key repeat (Ghost notes)
            threading.Timer(0.03, release_key, args=[vk_code]).start()

    def release_note(self, midi_note):
        # We handle release automatically after press to avoid OS key repeat spam
        pass

    def _get_mapping(self, midi_note):
        # Check if playable in CURRENT shift first to minimize toggling
        if self.current_octave_shift == 0 and 48 <= midi_note <= 83:
            return 0, midi_note
        elif self.current_octave_shift == 1 and 60 <= midi_note <= 95:
            return 1, midi_note - 12
        elif self.current_octave_shift == -1 and 36 <= midi_note <= 71:
            return -1, midi_note + 12
            
        # If not playable currently, map to the default shift
        if 48 <= midi_note <= 83:
            return 0, midi_note
        elif 84 <= midi_note <= 95:
            return 1, midi_note - 12
        elif 36 <= midi_note <= 47:
            return -1, midi_note + 12
        
        return 0, None

    def release_all(self):
        self.reset_octave()
        if self.sustain_active:
            self.set_sustain(False)
        for vk_code in KEY_MAP.values():
            release_key(vk_code)
