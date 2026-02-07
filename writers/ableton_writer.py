"""
TransProj → Ableton Live Writer

Best-effort XML writer for .als files (gzipped XML).
"""

import gzip
import logging
import xml.etree.ElementTree as ET
from pathlib import Path

from core.transproj import TransProj, Clip, Note, Track

logger = logging.getLogger(__name__)


class AbletonWriter:
    """Write Ableton Live .als projects from TransProj."""

    def write(self, transproj: TransProj, filepath: str):
        root = ET.Element("Ableton", Version="1")
        liveset = ET.SubElement(root, "LiveSet")

        tempo = ET.SubElement(liveset, "Tempo")
        ET.SubElement(tempo, "Manual", Value=str(transproj.tempo))

        tracks_elem = ET.SubElement(liveset, "Tracks")
        for track in transproj.tracks:
            track_elem = ET.SubElement(tracks_elem, "MidiTrack")
            self._write_track(track_elem, track)

        xml_bytes = ET.tostring(root, encoding="utf-8")
        with gzip.open(filepath, "wb") as handle:
            handle.write(xml_bytes)

        logger.info("✓ Written Ableton project: %s", filepath)

    def _write_track(self, track_elem: ET.Element, track: Track):
        name_elem = ET.SubElement(track_elem, "Name")
        ET.SubElement(name_elem, "EffectiveName", Value=track.name)

        volume_elem = ET.SubElement(track_elem, "Volume")
        ET.SubElement(volume_elem, "Manual", Value=str(track.volume))

        pan_elem = ET.SubElement(track_elem, "Pan")
        ET.SubElement(pan_elem, "Manual", Value=str(track.pan))

        clip_slots = ET.SubElement(track_elem, "ClipSlotList")
        for idx, clip in enumerate(track.clips):
            if not clip.is_midi:
                continue
            slot = ET.SubElement(clip_slots, "ClipSlot")
            value_elem = ET.SubElement(slot, "Value")
            midi_clip = self._write_midi_clip(value_elem, clip, idx)
            midi_clip.set("Value", "true")

    def _write_midi_clip(self, parent: ET.Element, clip: Clip, index: int) -> ET.Element:
        midi_clip = ET.SubElement(parent, "MidiClip")
        name_elem = ET.SubElement(midi_clip, "Name")
        ET.SubElement(name_elem, "Value", Value=clip.name)

        ET.SubElement(midi_clip, "CurrentStart", Value=str(clip.start))
        ET.SubElement(midi_clip, "CurrentEnd", Value=str(clip.start + clip.duration))

        notes_elem = ET.SubElement(midi_clip, "Notes")
        key_tracks = ET.SubElement(notes_elem, "KeyTracks")

        notes_by_key = {}
        for note in clip.notes:
            notes_by_key.setdefault(note.key, []).append(note)

        for key, notes in notes_by_key.items():
            key_track = ET.SubElement(key_tracks, "KeyTrack")
            ET.SubElement(key_track, "MidiKey", Value=str(key))
            notes_container = ET.SubElement(key_track, "Notes")
            for note in notes:
                self._write_note(notes_container, note)

        return midi_clip

    def _write_note(self, notes_elem: ET.Element, note: Note):
        note_elem = ET.SubElement(notes_elem, "MidiNoteEvent")
        note_elem.set("Time", str(note.position))
        note_elem.set("Duration", str(note.duration))
        note_elem.set("Velocity", str(int(note.velocity * 127)))


def write_ableton_project(transproj: TransProj, filepath: str):
    """Convenience function to write Ableton project."""
    writer = AbletonWriter()
    writer.write(transproj, filepath)


__all__ = ["AbletonWriter", "write_ableton_project"]
