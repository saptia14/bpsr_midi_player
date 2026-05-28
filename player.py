import time
import threading
from input_simulator import BPSRInputSimulator

class MidiPlayer:
    def __init__(self):
        self.simulator = BPSRInputSimulator()
        self.events = []
        self.active_channels = set()
        
        self.is_playing = False
        self.is_paused = False
        self.stop_requested = False
        
        self.thread = None
        self.current_event_idx = 0
        self.start_time = 0.0
        self.pause_time = 0.0
        self.time_offset = 0.0
        
        self.sleep_threshold = 0.002 

    def load_events(self, events, active_channels=None):
        self.stop()
        self.events = events
        if active_channels is not None:
            self.active_channels = set(active_channels)
        self.current_event_idx = 0

    def set_active_channels(self, channels):
        self.active_channels = set(channels)

    def play(self, delay_seconds=0.0):
        if self.is_playing:
            return
            
        if self.is_paused:
            self.is_paused = False
            self.start_time += time.perf_counter() - self.pause_time
        else:
            if not self.events:
                return
            self.current_event_idx = 0
            # delay_seconds allows synchronization
            self.start_time = time.perf_counter() + delay_seconds
            self.time_offset = 0.0
            
        self.stop_requested = False
        self.is_playing = True
        self.thread = threading.Thread(target=self._playback_loop, daemon=True)
        self.thread.start()

    def pause(self):
        if self.is_playing and not self.is_paused:
            self.is_paused = True
            self.is_playing = False
            self.pause_time = time.perf_counter()
            self.simulator.release_all()

    def stop(self):
        self.stop_requested = True
        self.is_playing = False
        self.is_paused = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        self.simulator.release_all()
        self.current_event_idx = 0

    def _accurate_delay(self, target_time):
        while True:
            if self.stop_requested or self.is_paused:
                break
            now = time.perf_counter()
            diff = target_time - now
            if diff <= 0:
                break
            if diff > self.sleep_threshold:
                time.sleep(diff / 2.0)
            else:
                pass

    def _playback_loop(self):
        while self.current_event_idx < len(self.events):
            if self.stop_requested or self.is_paused:
                break

            ev = self.events[self.current_event_idx]
            
            target_time = self.start_time + ev['time']
            
            self._accurate_delay(target_time)
            
            if self.stop_requested or self.is_paused:
                break

            if 'channel' in ev and ev['channel'] in self.active_channels:
                if ev['type'] == 'note_on':
                    self.simulator.press_note(ev['note'])
                elif ev['type'] == 'note_off':
                    self.simulator.release_note(ev['note'])
                elif ev['type'] == 'sustain':
                    self.simulator.set_sustain(ev['value'])

            self.current_event_idx += 1

        if self.current_event_idx >= len(self.events):
            self.is_playing = False
            self.simulator.release_all()
