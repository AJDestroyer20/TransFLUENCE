"""
TransProj v2.0 - Universal DAW Project Format

Intermediate representation for DAW projects.
Bridge between PyAbleton (input) and PyFLP (output).

Design: Pure data classes, no business logic.
Logic goes in converters.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class Note:
    """Single MIDI note (universal format)"""
    position: float  # In beats
    duration: float  # In beats
    key: int        # MIDI note (0-127)
    velocity: float # 0.0-1.0 (normalized)
    
    def to_ticks(self, ppq: int = 96) -> tuple:
        """Convert to ticks for FL Studio"""
        return (
            int(self.position * ppq),
            int(self.duration * ppq)
        )


@dataclass
class Clip:
    """MIDI or Audio clip"""
    name: str
    start: float      # Beats
    duration: float   # Beats
    notes: List[Note] = field(default_factory=list)
    audio_path: str = ""  # For audio clips
    is_midi: bool = True
    scene_index: Optional[int] = None  # For Session View
    
    def is_session_clip(self) -> bool:
        return self.scene_index is not None


@dataclass
class Plugin:
    """Plugin/Device (instrument or FX)"""
    name: str
    manufacturer: str = "unknown"
    is_instrument: bool = False
    device_type: Optional[str] = None
    vst_id: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def is_native_ableton(self) -> bool:
        return self.manufacturer.lower() == "ableton"


@dataclass
class DrumPad:
    """Single pad in drum rack"""
    index: int
    name: str
    sample_path: str
    midi_note: int = 36  # C1
    volume: float = 1.0
    pan: float = 0.0


@dataclass
class Rack:
    """Plugin rack/chain"""
    name: str
    rack_type: Optional[str] = None
    plugins: List[Plugin] = field(default_factory=list)
    drum_pads: List[DrumPad] = field(default_factory=list)
    
    def is_drum_rack(self) -> bool:
        return len(self.drum_pads) > 0


@dataclass
class Track:
    """Single track (channel)"""
    name: str
    color: tuple = (128, 128, 128)  # RGB
    volume: float = 1.0  # 0.0-1.0
    pan: float = 0.0     # -1.0 to 1.0
    muted: bool = False
    solo: bool = False
    
    # Content
    clips: List[Clip] = field(default_factory=list)
    instrument: Optional[Plugin] = None
    effects: List[Plugin] = field(default_factory=list)
    racks: List[Rack] = field(default_factory=list)
    
    def has_midi(self) -> bool:
        return any(c.is_midi for c in self.clips)
    
    def has_audio(self) -> bool:
        return any(not c.is_midi for c in self.clips)


@dataclass
class TransProj:
    """
    Universal DAW Project
    
    Bridge format between PyAbleton and PyFLP
    """
    name: str = "Untitled"
    tempo: float = 120.0
    ppq: int = 96  # Pulses per quarter note
    tracks: List[Track] = field(default_factory=list)
    
    # Metadata
    ableton_version: str = ""
    is_session_view: bool = False
    
    def add_track(self, name: str) -> Track:
        """Create and add new track"""
        track = Track(name=name)
        self.tracks.append(track)
        return track
    
    def get_track(self, index: int) -> Optional[Track]:
        """Get track by index"""
        if 0 <= index < len(self.tracks):
            return self.tracks[index]
        return None
    
    def total_clips(self) -> int:
        """Count total clips"""
        return sum(len(t.clips) for t in self.tracks)
    
    def total_notes(self) -> int:
        """Count total notes"""
        count = 0
        for track in self.tracks:
            for clip in track.clips:
                count += len(clip.notes)
        return count


__all__ = [
    'TransProj',
    'Track',
    'Clip',
    'Note',
    'Plugin',
    'Rack',
    'DrumPad'
]
