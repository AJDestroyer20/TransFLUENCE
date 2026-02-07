"""
TransProj → FL Studio Writer

PATCH 009: Plugin state generation
Write complete plugin data including parameters
"""

import logging
import struct
from pathlib import Path

from core.transproj import TransProj, Track, Clip, Note, Plugin, Rack
from converters import PluginMapper
from converters.plugin_state_generator import PluginStateFactory

logger = logging.getLogger(__name__)

try:
    from pyflp import Project  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    Project = None


class FLStudioWriter:
    """Write FL Studio projects using hybrid approach"""
    
    def __init__(self):
        self.ppq = 960  # FL Studio default PPQ
        self.use_pyflp = Project is not None  # Prefer PyFLP when available
    
    def write(self, transproj: TransProj, filepath: str):
        """
        Write TransProj to .flp file
        
        PATCH 008: Hybrid approach
        - Create binary manually (reliable)
        - Optionally inject with PyFLP (advanced features)
        
        Args:
            transproj: TransProj object
            filepath: Output .flp path
        """
        logger.info(f"Writing FL Studio project: {filepath}")
        logger.info(f"Input: {len(transproj.tracks)} tracks, {transproj.total_clips()} clips, {transproj.total_notes()} notes")
        self.ppq = transproj.ppq or self.ppq
        
        if self.use_pyflp:
            self._write_with_pyflp(transproj, filepath)
            return

        # Build binary FLP (fallback approach)
        data = self._build_flp_binary(transproj)

        # Write to file
        with open(filepath, 'wb') as f:
            f.write(data)

        file_size = len(data)
        logger.info(f"✓ Written {file_size:,} bytes to {filepath}")
    
    def _build_flp_binary(self, transproj: TransProj) -> bytes:
        """
        Build complete FLP binary
        
        PATCH 010: Critical binary format fixes
        - Correct event IDs
        - Project ID (event 156)
        - Proper tempo event
        - No duplicate event 66
        """
        data = bytearray()
        
        # === HEADER (FLhd) ===
        data.extend(b'FLhd')  # Magic
        data.extend(struct.pack('<I', 6))  # Header size
        data.extend(struct.pack('<H', 0))  # Format
        data.extend(struct.pack('<H', len(transproj.tracks)))  # Channels
        data.extend(struct.pack('<H', self.ppq))  # PPQ
        
        logger.debug(f"Header: format=0, channels={len(transproj.tracks)}, ppq={self.ppq}")
        
        # === DATA (FLdt) ===
        data.extend(b'FLdt')
        data_start = len(data)
        data.extend(struct.pack('<I', 0))  # Placeholder for size
        
        # PATCH 010 FIX 1: Version (event 199)
        data.append(199)  # VERSION event
        self._write_string(data, "21.0.3")  # FL Studio version string
        
        # PATCH 010 FIX 2: Project ID (event 156 - REQUIRED for modern FL)
        data.append(156)  # PROJECT_ID event
        data.extend(struct.pack('<I', 12345))  # Generic project ID
        
        # PATCH 010 FIX 3: Tempo (event 66 - ONLY HERE, not in patterns!)
        data.append(66)  # TEMPO event (DWord for modern FL)
        data.extend(struct.pack('<H', int(transproj.tempo)))
        logger.debug(f"Tempo: {int(transproj.tempo)} BPM")
        
        # Title (optional)
        if transproj.name:
            data.append(206)  # TITLE event
            self._write_utf16le_string(data, transproj.name)
        
        # === CHANNELS ===
        for idx, track in enumerate(transproj.tracks):
            self._normalize_track_plugins(track)
            self._write_channel(data, idx, track)
        
        # === PATTERNS ===
        pattern_count = 0
        total_notes = 0
        playlist_items = []
        
        for track_idx, track in enumerate(transproj.tracks):
            for clip in track.clips:
                if not clip.is_midi:
                    continue

                self._write_pattern(data, pattern_count, track_idx, track.name, clip)
                total_notes += len(clip.notes)
                playlist_items.append({
                    'pattern_id': pattern_count + 1,
                    'position': int(clip.start * self.ppq),
                    'length': int(clip.duration * self.ppq),
                    'track_idx': track_idx,
                })
                pattern_count += 1

        # === PLAYLIST ===
        self._write_playlist(data, playlist_items)
        
        # Update data size
        data_size = len(data) - data_start - 4
        struct.pack_into('<I', data, data_start, data_size)
        
        logger.info(f"Binary: {len(transproj.tracks)} channels, {pattern_count} patterns, {total_notes} notes")
        
        return bytes(data)
    
    def _write_string(self, data: bytearray, text: str, encoding: str = 'utf-8'):
        """Write string with varint length (for events like VERSION)."""
        text_bytes = text.encode(encoding)
        self._write_varint(data, len(text_bytes))
        data.extend(text_bytes)

    def _write_utf16le_string(self, data: bytearray, text: str, include_null: bool = True):
        """Write UTF-16LE string with varint length."""
        suffix = b'\x00\x00' if include_null else b''
        text_bytes = text.encode('utf-16le') + suffix
        self._write_varint(data, len(text_bytes))
        data.extend(text_bytes)
    
    def _write_channel(self, data: bytearray, idx: int, track: Track):
        """
        Write channel to FLP binary
        
        PATCH 010 FIX 4: Validate plugin data before writing
        """
        # NEW_CHAN
        data.append(64)
        data.extend(struct.pack('<H', idx))
        
        # Channel name
        name_bytes = track.name.encode('utf-16le') + b'\x00\x00'
        data.append(203)  # CHAN_NAME
        self._write_varint(data, len(name_bytes))
        data.extend(name_bytes)
        
        # Volume (0-128)
        vol = int(track.volume * 100)
        vol = min(128, max(0, vol))
        data.append(33)  # VOL
        data.append(vol)
        
        # Pan (0-128, 64=center)
        pan = int((track.pan + 1.0) * 64)
        pan = min(128, max(0, pan))
        data.append(34)  # PAN
        data.append(pan)
        
        # PATCH 010 FIX 4: Write plugin/generator state WITH VALIDATION
        plugin_state_written = False
        
        # Check for instrument
        if track.instrument:
            fl_plugin = PluginMapper.ableton_to_fl(
                track.instrument.name,
                is_instrument=True,
                device_type=track.instrument.device_type
            )
            plugin_params = self._map_plugin_params(track.instrument)
            plugin_state = self._generate_plugin_state(fl_plugin, track, is_instrument=True, params=plugin_params)
            
            # CRITICAL: Only write if data is valid and non-empty
            if plugin_state and len(plugin_state) > 0:
                data.append(205)  # CHAN_PLUGIN (generator state)
                self._write_varint(data, len(plugin_state))
                data.extend(plugin_state)
                plugin_state_written = True
                logger.debug(f"  Channel {idx}: {track.name} → {fl_plugin} (vol={vol}, pan={pan}, state={len(plugin_state)}b)")
            else:
                logger.warning(f"  Channel {idx}: {track.name} → {fl_plugin} - EMPTY STATE, skipped")
        
        # Check for drum rack
        elif track.racks:
            for rack in track.racks:
                if rack.is_drum_rack():
                    plugin_state = self._generate_drum_rack_state(rack)
                    # CRITICAL: Validate before writing
                    if plugin_state and len(plugin_state) > 0:
                        data.append(205)  # CHAN_PLUGIN
                        self._write_varint(data, len(plugin_state))
                        data.extend(plugin_state)
                        plugin_state_written = True
                        logger.debug(f"  Channel {idx}: {track.name} → FPC ({len(rack.drum_pads)} pads, state={len(plugin_state)}b)")
                    else:
                        logger.warning(f"  Channel {idx}: FPC state empty, skipped")
                    break
        
        # Check for audio clips (sampler)
        elif track.has_audio():
            audio_clip = next((c for c in track.clips if not c.is_midi and c.audio_path), None)
            if audio_clip:
                plugin_state = PluginStateFactory.generate(
                    'Sampler',
                    sample_path=audio_clip.audio_path,
                    volume=track.volume,
                    pan=(track.pan + 1.0) / 2.0
                )
                # CRITICAL: Validate
                if plugin_state and len(plugin_state) > 0:
                    data.append(205)  # CHAN_PLUGIN
                    self._write_varint(data, len(plugin_state))
                    data.extend(plugin_state)
                    plugin_state_written = True
                    logger.debug(f"  Channel {idx}: {track.name} → Sampler (audio, state={len(plugin_state)}b)")
        
        # Default to 3xOsc if MIDI but no instrument
        elif track.has_midi() and not plugin_state_written:
            plugin_state = PluginStateFactory.generate('3xOsc')
            # CRITICAL: Validate
            if plugin_state and len(plugin_state) > 0:
                data.append(205)
                self._write_varint(data, len(plugin_state))
                data.extend(plugin_state)
                logger.debug(f"  Channel {idx}: {track.name} → 3xOsc (default, state={len(plugin_state)}b)")
        
        # No plugin state - just log
        if not plugin_state_written and not track.has_midi():
            logger.debug(f"  Channel {idx}: {track.name} (empty, no generator)")
    
    def _generate_plugin_state(self, fl_plugin_name: str, track: Track, is_instrument: bool,
                               params: dict) -> bytes:
        """
        Generate plugin state for FL plugin
        
        Args:
            fl_plugin_name: FL Studio plugin name
            track: Source track
            is_instrument: Whether it's an instrument
            
        Returns:
            Binary plugin state
        """
        # Generate based on plugin type
        if fl_plugin_name == 'Sampler':
            # Find first audio clip
            audio_clip = next((c for c in track.clips if not c.is_midi and c.audio_path), None)
            if audio_clip:
                return PluginStateFactory.generate(
                    'Sampler',
                    sample_path=audio_clip.audio_path,
                    volume=track.volume,
                    pan=(track.pan + 1.0) / 2.0
                )
        
        elif fl_plugin_name == '3xOsc':
            return PluginStateFactory.generate('3xOsc')
        
        elif fl_plugin_name == 'Sytrus':
            # Complex synth - use generic for now
            return PluginStateFactory.generate(
                'Sytrus',
                params={'volume': track.volume}
            )
        
        # Generic state for unknown plugins
        return PluginStateFactory.generate(
            fl_plugin_name,
            params=params or {'volume': track.volume, 'pan': track.pan}
        )
    
    def _generate_drum_rack_state(self, rack: Rack) -> bytes:
        """
        Generate FPC state from drum rack
        
        Args:
            rack: Drum rack
            
        Returns:
            Binary FPC state
        """
        # Convert drum pads to FPC format
        pads = []
        for pad in rack.drum_pads[:16]:  # FPC has max 16 pads
            pads.append({
                'sample_path': pad.sample_path,
                'volume': pad.volume,
                'pan': pad.pan,
                'tune': 0.5,  # Default tuning
            })
        
        return PluginStateFactory.generate('FPC', pads=pads)

    def _map_plugin_params(self, plugin: Plugin) -> dict:
        """Map Ableton parameter names/values to FL Studio equivalents."""
        if not plugin.parameters:
            return {'volume': 100.0}

        mapped = {}
        for name, value in plugin.parameters.items():
            mapped_name = PluginMapper.map_parameter_name(name)
            mapped_value = PluginMapper.map_parameter_value(name, value)
            mapped[mapped_name] = mapped_value
        return mapped

    def _normalize_track_plugins(self, track: Track):
        """Normalize racks into track instrument/effects before writing."""
        if track.instrument:
            return

        for rack in track.racks:
            if rack.is_drum_rack():
                continue
            if rack.rack_type == 'InstrumentGroupDevice' and rack.plugins:
                track.instrument = rack.plugins[0]
                if len(rack.plugins) > 1:
                    track.effects.extend(rack.plugins[1:])
                    logger.warning(
                        "Instrument Rack has multiple devices; only first is generator, "
                        "remaining devices mapped as effects."
                    )
                return

    def _write_playlist(self, data: bytearray, playlist_items: list):
        """Write playlist items (pattern clips) to the FLP binary."""
        if not playlist_items:
            return

        clip_data = bytearray()
        for item in playlist_items:
            position = item['position']
            length = max(1, item['length'])
            pattern_id = item['pattern_id']
            track_idx = item['track_idx']
            flags = 0

            clip_data.extend(struct.pack('<IIIII', position, length, pattern_id, track_idx, flags))

        data.append(224)  # PLAYLIST_ITEMS (best-effort)
        self._write_varint(data, len(clip_data))
        data.extend(clip_data)
    
    def _write_pattern(self, data: bytearray, pattern_idx: int, track_idx: int, 
                       track_name: str, clip: Clip):
        """
        Write pattern to FLP binary
        
        PATCH 010 FIXES:
        - Pattern index starts at 1 (not 0)
        - NO event 66 here (that's TEMPO, not pattern length!)
        - Correct note byte offsets for Pan/Velocity
        """
        # PATCH 010 FIX: NEW_PAT starts at 1
        data.append(65)
        data.extend(struct.pack('<H', pattern_idx + 1))  # Pattern indices start at 1
        
        # Pattern name (event 193, not 207)
        if clip.is_session_clip():
            pattern_name = f"{track_name} - Scene {clip.scene_index + 1}"
        else:
            pattern_name = f"{track_name} - {clip.name}"
        
        data.append(193)  # PAT_NAME (correct event ID)
        self._write_utf16le_string(data, pattern_name)
        
        # PATCH 010 FIX: NO EVENT 66 HERE!
        # Event 66 is TEMPO (global), NOT pattern length
        # FL calculates pattern length from notes automatically
        
        # Notes (24 bytes each)
        note_data = bytearray()
        for note in clip.notes:
            pos_ticks, dur_ticks = note.to_ticks(self.ppq)
            
            note_bytes = bytearray(24)
            
            # PATCH 010 FIX: Correct byte offsets
            struct.pack_into('<I', note_bytes, 0, pos_ticks)    # 0-3: Position
            struct.pack_into('<H', note_bytes, 4, 0)            # 4-5: Flags
            struct.pack_into('<H', note_bytes, 6, track_idx)    # 6-7: Channel ID
            struct.pack_into('<I', note_bytes, 8, dur_ticks)    # 8-11: Length
            note_bytes[12] = note.key                           # 12: MIDI key
            
            # PATCH 010 CRITICAL FIX: Correct offsets!
            # OLD (WRONG): Pan at 17, Velocity at 18
            # NEW (CORRECT): Pan at 16, Velocity at 17
            note_bytes[16] = 64                                 # 16: Pan (center=64)
            note_bytes[17] = int(note.velocity * 127)           # 17: Velocity (0-127)
            # Byte 18 is ModX - leave as 0
            
            note_data.extend(note_bytes)
        
        if note_data:
            data.append(203)  # PATTERN_NOTES
            self._write_varint(data, len(note_data))
            data.extend(note_data)
        
        logger.debug(f"  Pattern {pattern_idx + 1}: {pattern_name} ({len(clip.notes)} notes)")
    
    def _write_varint(self, data: bytearray, value: int):
        """Write variable-length integer"""
        while True:
            byte = value & 0x7F
            value >>= 7
            if value != 0:
                byte |= 0x80
            data.append(byte)
            if value == 0:
                break
    
    def _inject_with_pyflp(self, filepath: str, transproj: TransProj):
        """
        Optional: Inject advanced features using PyFLP
        
        This could add:
        - Plugin state
        - Mixer routing
        - Automation
        - Playlist clips
        
        Currently not implemented - binary is sufficient
        """
        logger.info("PyFLP injection not yet implemented")
        pass

    def _write_with_pyflp(self, transproj: TransProj, filepath: str):
        """Write FL Studio project using PyFLP when available."""
        if Project is None:
            raise ImportError("pyflp is required for PyFLP-based writing")

        project = Project()
        if hasattr(project, "tempo"):
            project.tempo = transproj.tempo

        channels = getattr(project, "channels", None)
        if channels is None and hasattr(project, "channel_rack"):
            channels = project.channel_rack

        for track in transproj.tracks:
            if channels and hasattr(channels, "add"):
                channel = channels.add()
            elif channels and hasattr(channels, "append"):
                channel = None
            else:
                channel = None

            if channel is not None:
                if hasattr(channel, "name"):
                    channel.name = track.name
                if hasattr(channel, "volume"):
                    channel.volume = track.volume
                if hasattr(channel, "pan"):
                    channel.pan = track.pan

                if track.instrument:
                    fl_plugin = PluginMapper.ableton_to_fl(
                        track.instrument.name,
                        is_instrument=True,
                        device_type=track.instrument.device_type,
                    )
                    if hasattr(channel, "plugin"):
                        channel.plugin = fl_plugin
                    elif hasattr(channel, "generator"):
                        channel.generator = fl_plugin

        patterns = getattr(project, "patterns", None)
        playlist = getattr(project, "playlist", None)

        for track_idx, track in enumerate(transproj.tracks):
            for clip in track.clips:
                if not clip.is_midi:
                    continue

                pattern = None
                if patterns and hasattr(patterns, "add"):
                    pattern = patterns.add()
                if pattern is not None and hasattr(pattern, "name"):
                    pattern.name = f"{track.name} - {clip.name}"

                if pattern is not None and hasattr(pattern, "notes"):
                    for note in clip.notes:
                        if hasattr(pattern.notes, "add"):
                            note_obj = pattern.notes.add()
                        else:
                            note_obj = None
                        if note_obj is not None:
                            if hasattr(note_obj, "key"):
                                note_obj.key = note.key
                            if hasattr(note_obj, "position"):
                                note_obj.position = int(note.position * self.ppq)
                            if hasattr(note_obj, "length"):
                                note_obj.length = int(note.duration * self.ppq)
                            if hasattr(note_obj, "velocity"):
                                note_obj.velocity = int(note.velocity * 127)

                if playlist and hasattr(playlist, "items"):
                    items = playlist.items
                else:
                    items = None

                if items and hasattr(items, "add"):
                    item = items.add()
                    if hasattr(item, "pattern"):
                        item.pattern = pattern
                    if hasattr(item, "position"):
                        item.position = int(clip.start * self.ppq)
                    if hasattr(item, "length"):
                        item.length = int(clip.duration * self.ppq)
                    if hasattr(item, "track"):
                        item.track = track_idx

        if hasattr(project, "save"):
            project.save(filepath)
        elif hasattr(project, "write"):
            project.write(filepath)
        else:
            with open(filepath, "wb") as handle:
                handle.write(bytes(project))

        logger.info("✓ Written %s with PyFLP", filepath)


def write_flstudio_project(transproj: TransProj, filepath: str):
    """
    Convenience function to write FL Studio project
    
    Args:
        transproj: TransProj object
        filepath: Output .flp path
    """
    writer = FLStudioWriter()
    writer.write(transproj, filepath)


__all__ = ['FLStudioWriter', 'write_flstudio_project']
