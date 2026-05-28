import mido

def parse_midi(file_path):
    """
    Parses a MIDI file and returns a sorted list of events with absolute timestamps.
    Events are dicts: {'time': float, 'type': str, 'note': int, 'velocity': int, 'channel': int, 'value': int}
    Types can be 'note_on', 'note_off', 'sustain'
    """
    try:
        mid = mido.MidiFile(file_path)
    except Exception as e:
        print(f"Error loading MIDI: {e}")
        return []

    tempo = 500000 # default 120 bpm
    ticks_per_beat = mid.ticks_per_beat

    # We will build absolute time for each event in each track, then merge
    all_events = []

    for i, track in enumerate(mid.tracks):
        current_time = 0.0
        current_ticks = 0
        current_tempo = tempo

        for msg in track:
            current_ticks += msg.time
            # Convert tick delta to seconds based on current tempo
            delta_sec = mido.tick2second(msg.time, ticks_per_beat, current_tempo)
            current_time += delta_sec

            if msg.type == 'set_tempo':
                current_tempo = msg.tempo
            
            elif msg.type == 'note_on':
                # note_on with velocity 0 is often used as note_off
                if msg.velocity == 0:
                    all_events.append({
                        'time': current_time,
                        'type': 'note_off',
                        'note': msg.note,
                        'channel': msg.channel
                    })
                else:
                    all_events.append({
                        'time': current_time,
                        'type': 'note_on',
                        'note': msg.note,
                        'velocity': msg.velocity,
                        'channel': msg.channel
                    })
            
            elif msg.type == 'note_off':
                all_events.append({
                    'time': current_time,
                    'type': 'note_off',
                    'note': msg.note,
                    'channel': msg.channel
                })
            
            elif msg.type == 'control_change' and msg.control == 64:
                # CC 64 is Sustain Pedal
                # >= 64 is ON, < 64 is OFF
                is_on = msg.value >= 64
                all_events.append({
                    'time': current_time,
                    'type': 'sustain',
                    'value': is_on,
                    'channel': msg.channel
                })

    # Sort all events by absolute time
    all_events.sort(key=lambda x: x['time'])
    
    return all_events

def get_channels_info(events):
    """
    Returns a sorted list of active channels in the parsed events.
    """
    channels = set()
    for ev in events:
        if 'channel' in ev:
            channels.add(ev['channel'])
    return sorted(list(channels))
