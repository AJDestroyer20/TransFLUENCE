"""
Ableton → TransProj Parser using Direct XML

PATCH 002-008: Direct XML parsing approach
PATCH 007: Exhaustive clip/device search
PATCH 008: Plugin mapping integration
"""

import logging
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path

from core.transproj import TransProj, Track, Clip, Note, Plugin, Rack, DrumPad
from converters import PluginMapper

logger = logging.getLogger(__name__)


class AbletonParser:
    """
    Parse Ableton Live projects
    
    PATCH 002: Use direct XML parsing instead of broken Ableton() class
    PyAbleton 0.0.14 has annotation issues - we'll parse XML directly
    """
    
    def __init__(self):
        pass
    
    def parse(self, filepath: str) -> TransProj:
        """
        Parse .als file to TransProj
        
        PATCH 004: Validated approach - direct XML parsing is correct solution
        (PyAbleton's Ableton() class has broken __annotations__)
        
        Args:
            filepath: Path to .als file
            
        Returns:
            TransProj object
        """
        logger.info(f"Parsing Ableton project: {filepath}")
        
        # PATCH 002-004: Parse XML directly
        # .als files are gzipped XML
        try:
            with gzip.open(filepath, 'rb') as f:
                xml_content = f.read()
            root = ET.fromstring(xml_content)
            logger.debug("Decompressed .als file successfully")
        except:
            # Maybe it's already uncompressed
            logger.debug("File not gzipped, trying as plain XML")
            tree = ET.parse(filepath)
            root = tree.getroot()
        
        # Find LiveSet element
        liveset = root if root.tag == 'Ableton' else root.find('.//Ableton')
        if liveset is None:
            raise ValueError("Not a valid Ableton Live file")
        
        # Create TransProj
        transproj = TransProj(
            name=Path(filepath).stem,
            tempo=self._get_tempo(liveset),
            ableton_version=liveset.get('Creator', ''),
            is_session_view=self._detect_session_view(liveset)
        )
        
        logger.debug(f"Ableton version: {transproj.ableton_version}")
        logger.debug(f"Tempo: {transproj.tempo} BPM")
        logger.debug(f"View mode: {'Session' if transproj.is_session_view else 'Arrangement'}")
        
        # Parse tracks
        tracks_elem = liveset.find('.//Tracks')
        if tracks_elem:
            for track_elem in tracks_elem:
                if track_elem.tag in ['MidiTrack', 'AudioTrack', 'ReturnTrack']:
                    track = self._parse_track(track_elem, transproj.is_session_view)
                    if track:
                        transproj.tracks.append(track)
                        logger.debug(f"  Track: {track.name} ({len(track.clips)} clips, {sum(len(c.notes) for c in track.clips)} notes)")
        
        logger.info(f"✓ Parsed {len(transproj.tracks)} tracks, {transproj.total_clips()} clips, {transproj.total_notes()} notes")
        
        return transproj
    
    def _get_tempo(self, liveset: ET.Element) -> float:
        """Extract tempo from LiveSet"""
        tempo_elem = liveset.find('.//Tempo/Manual')
        if tempo_elem is not None:
            try:
                return float(tempo_elem.get('Value', '120'))
            except:
                pass
        return 120.0
    
    def _detect_session_view(self, liveset: ET.Element) -> bool:
        """Detect if project uses Session View"""
        tracks_elem = liveset.find('.//Tracks')
        if not tracks_elem:
            return False
        
        # Check for clips in ClipSlots
        for track_elem in tracks_elem:
            clip_slots = track_elem.find('.//ClipSlots')
            if clip_slots:
                for slot in clip_slots.findall('ClipSlot'):
                    # Check if slot has clip
                    value_elem = slot.find('Value')
                    if value_elem is not None:
                        if value_elem.find('MidiClip') is not None or value_elem.find('AudioClip') is not None:
                            return True
        
        return False
    
    def _parse_track(self, track_elem: ET.Element, is_session: bool) -> Track:
        """
        Parse single track
        
        PATCH 007: Exhaustive clip search - check ALL possible locations
        """
        # Get track name
        name_elem = track_elem.find('.//Name/EffectiveName')
        track_name = name_elem.get('Value', 'Track') if name_elem is not None else 'Track'
        
        track = Track(
            name=track_name,
            color=self._parse_color(track_elem),
            volume=self._get_volume(track_elem),
            pan=self._get_pan(track_elem),
            muted=self._is_muted(track_elem),
            solo=self._is_solo(track_elem)
        )
        
        # PATCH 007: Search clips EVERYWHERE (not just one location)
        logger.debug(f"Parsing track: {track_name}")
        
        # Try all possible clip locations
        clip_count = 0
        
        # 1. Session View (ClipSlotList)
        clip_slots = track_elem.find('.//ClipSlotList')
        if clip_slots:
            for scene_idx, slot in enumerate(clip_slots.findall('ClipSlot')):
                clips_found = self._parse_clip_slot(slot, track, scene_idx)
                clip_count += clips_found
        
        # 2. Arrangement (MainSequencer/ArrangerAutomation)
        events = track_elem.find('.//MainSequencer/ClipTimeable/ArrangerAutomation/Events')
        if events:
            for midi_clip in events.findall('.//MidiClip'):
                clip = self._parse_midi_clip(midi_clip)
                if clip:
                    track.clips.append(clip)
                    clip_count += 1
            
            for audio_clip in events.findall('.//AudioClip'):
                clip = self._parse_audio_clip(audio_clip)
                if clip:
                    track.clips.append(clip)
                    clip_count += 1
        
        # 3. Direct children (fallback)
        for midi_clip in track_elem.findall('.//MidiClip'):
            # Avoid duplicates from already-parsed locations
            if not any(c.name == self._get_clip_name(midi_clip) for c in track.clips):
                clip = self._parse_midi_clip(midi_clip)
                if clip:
                    track.clips.append(clip)
                    clip_count += 1
        
        for audio_clip in track_elem.findall('.//AudioClip'):
            if not any(c.name == self._get_clip_name(audio_clip) for c in track.clips):
                clip = self._parse_audio_clip(audio_clip)
                if clip:
                    track.clips.append(clip)
                    clip_count += 1
        
        # Count notes
        note_count = sum(len(c.notes) for c in track.clips)
        
        logger.debug(f"  → Found {clip_count} clips, {note_count} notes")
        
        # Parse devices
        self._parse_devices(track_elem, track)
        
        return track
    
    def _parse_clip_slot(self, slot_elem: ET.Element, track: Track, scene_idx: int) -> int:
        """Parse single clip slot, return count of clips found"""
        count = 0
        
        value_elem = slot_elem.find('Value')
        if value_elem is None:
            return 0
        
        # Check for MIDI clip
        midi_clip = value_elem.find('MidiClip')
        if midi_clip is not None:
            clip = self._parse_midi_clip(midi_clip, scene_index=scene_idx)
            if clip:
                track.clips.append(clip)
                count += 1
        
        # Check for Audio clip
        audio_clip = value_elem.find('AudioClip')
        if audio_clip is not None:
            clip = self._parse_audio_clip(audio_clip, scene_index=scene_idx)
            if clip:
                track.clips.append(clip)
                count += 1
        
        return count
    
    def _get_clip_name(self, clip_elem: ET.Element) -> str:
        """Get clip name for duplicate detection"""
        name_elem = clip_elem.find('.//Name')
        return name_elem.get('Value', '') if name_elem is not None else ''
    
    def _parse_session_clips(self, track_elem: ET.Element, track: Track):
        """Parse Session View clips from ClipSlots"""
        clip_slots = track_elem.find('.//ClipSlots')
        if not clip_slots:
            return
        
        for scene_idx, slot in enumerate(clip_slots.findall('ClipSlot')):
            value_elem = slot.find('Value')
            if value_elem is None:
                continue
            
            # Check for MIDI clip
            midi_clip = value_elem.find('MidiClip')
            if midi_clip is not None:
                clip = self._parse_midi_clip(midi_clip, scene_index=scene_idx)
                if clip:
                    track.clips.append(clip)
            
            # Check for Audio clip
            audio_clip = value_elem.find('AudioClip')
            if audio_clip is not None:
                clip = self._parse_audio_clip(audio_clip, scene_index=scene_idx)
                if clip:
                    track.clips.append(clip)
    
    def _parse_arrangement_clips(self, track_elem: ET.Element, track: Track):
        """Parse Arrangement clips from MainSequencer"""
        # Find ArrangerAutomation/Events
        events = track_elem.find('.//MainSequencer/ClipTimeable/ArrangerAutomation/Events')
        if not events:
            return
        
        # Parse MIDI clips
        for midi_clip in events.findall('.//MidiClip'):
            clip = self._parse_midi_clip(midi_clip)
            if clip:
                track.clips.append(clip)
        
        # Parse Audio clips
        for audio_clip in events.findall('.//AudioClip'):
            clip = self._parse_audio_clip(audio_clip)
            if clip:
                track.clips.append(clip)
    
    def _parse_midi_clip(self, clip_elem: ET.Element, scene_index: int = None) -> Clip:
        """Parse MIDI clip"""
        # Get clip name
        name_elem = clip_elem.find('.//Name')
        clip_name = name_elem.get('Value', 'MIDI Clip') if name_elem is not None else 'MIDI Clip'
        
        # Get time
        start_elem = clip_elem.find('.//CurrentStart')
        end_elem = clip_elem.find('.//CurrentEnd')
        
        start = float(start_elem.get('Value', '0')) if start_elem is not None else 0.0
        end = float(end_elem.get('Value', '4')) if end_elem is not None else 4.0
        
        clip = Clip(
            name=clip_name,
            start=start,
            duration=end - start,
            is_midi=True,
            scene_index=scene_index
        )
        
        # Parse notes
        key_tracks = clip_elem.find('.//Notes/KeyTracks')
        if key_tracks:
            for key_track in key_tracks.findall('KeyTrack'):
                # Get MIDI note number
                midi_key_elem = key_track.find('.//MidiKey')
                if midi_key_elem is None:
                    continue
                
                note_num = int(midi_key_elem.get('Value', '60'))
                
                # Get notes in this key
                notes_elem = key_track.find('.//Notes')
                if notes_elem:
                    for note_elem in notes_elem.findall('MidiNoteEvent'):
                        time = float(note_elem.get('Time', '0'))
                        duration = float(note_elem.get('Duration', '1'))
                        velocity = float(note_elem.get('Velocity', '100'))
                        
                        note = Note(
                            position=time,
                            duration=duration,
                            key=note_num,
                            velocity=velocity / 127.0
                        )
                        clip.notes.append(note)
        
        return clip
    
    def _parse_audio_clip(self, clip_elem: ET.Element, scene_index: int = None) -> Clip:
        """Parse Audio clip"""
        # Get clip name
        name_elem = clip_elem.find('.//Name')
        clip_name = name_elem.get('Value', 'Audio Clip') if name_elem is not None else 'Audio Clip'
        
        # Get time
        start_elem = clip_elem.find('.//CurrentStart')
        end_elem = clip_elem.find('.//CurrentEnd')
        
        start = float(start_elem.get('Value', '0')) if start_elem is not None else 0.0
        end = float(end_elem.get('Value', '4')) if end_elem is not None else 4.0
        
        clip = Clip(
            name=clip_name,
            start=start,
            duration=end - start,
            is_midi=False,
            scene_index=scene_index
        )
        
        # Get sample path
        sample_ref = clip_elem.find('.//SampleRef/FileRef')
        if sample_ref:
            path_elem = sample_ref.find('.//Path')
            if path_elem is not None:
                clip.audio_path = path_elem.get('Value', '')
        
        return clip
    
    def _parse_devices(self, track_elem: ET.Element, track: Track):
        """
        Parse devices (plugins/racks)
        
        PATCH 007: Exhaustive device search
        """
        # Find all possible device locations
        device_chains = []
        
        # 1. Main DeviceChain
        main_chain = track_elem.find('.//DeviceChain/Devices')
        if main_chain is not None:
            device_chains.append(main_chain)
        
        # 2. Direct Devices
        direct_devices = track_elem.find('.//Devices')
        if direct_devices is not None:
            device_chains.append(direct_devices)
        
        # Parse all devices found
        for devices_elem in device_chains:
            for device in devices_elem:
                device_type = device.tag
                device_name = self._get_device_name(device)
                
                logger.debug(f"    Device: {device_type} - {device_name}")
                
                # Classify device type
                if device_type == 'DrumGroupDevice':
                    # Drum Rack
                    rack = self._parse_drum_rack(device)
                    if rack:
                        track.racks.append(rack)
                        logger.debug(f"      → Drum Rack with {len(rack.drum_pads)} pads")
                
                elif device_type == 'InstrumentGroupDevice':
                    # Instrument Rack
                    rack = self._parse_instrument_rack(device)
                    if rack:
                        track.racks.append(rack)
                        logger.debug(f"      → Instrument Rack with {len(rack.plugins)} plugins")
                
                elif device_type == 'AudioEffectGroupDevice':
                    # FX Rack
                    rack = self._parse_fx_rack(device)
                    if rack:
                        track.racks.append(rack)
                        logger.debug(f"      → FX Rack with {len(rack.plugins)} effects")
                
                elif 'Instrument' in device_name or device_type in ['OriginalSimpler', 'MultiSampler']:
                    # Instrument
                    plugin = Plugin(
                        name=device_name,
                        manufacturer='Ableton',
                        is_instrument=True
                    )
                    track.instrument = plugin
                    logger.debug(f"      → Instrument")
                
                else:
                    # Regular FX
                    plugin = Plugin(
                        name=device_name,
                        manufacturer='Ableton',
                        is_instrument=False
                    )
                    track.effects.append(plugin)
                    logger.debug(f"      → Effect")
    
    def _parse_drum_rack(self, device_elem: ET.Element) -> Rack:
        """Parse Drum Rack (DrumGroupDevice)"""
        rack = Rack(name=self._get_device_name(device_elem))
        
        # Find drum pads in Branches
        branches = device_elem.find('.//Branches')
        if branches:
            for idx, branch in enumerate(branches):
                # Check if branch has content
                drum_branch = branch.find('.//DrumBranch')
                if drum_branch is None:
                    continue
                
                # Get device chain
                chain = drum_branch.find('.//DeviceChain')
                if chain is None:
                    continue
                
                devices = chain.find('.//Devices')
                if devices is None or len(devices) == 0:
                    continue
                
                # Extract sample path
                sample_path = ''
                for device in devices:
                    if device.tag in ['OriginalSimpler', 'MultiSampler']:
                        sample_path = self._get_sample_path(device)
                        break
                
                # Get pad name
                name_elem = drum_branch.find('.//Name')
                pad_name = name_elem.get('Value', f'Pad {idx + 1}') if name_elem is not None else f'Pad {idx + 1}'
                
                pad = DrumPad(
                    index=idx,
                    name=pad_name,
                    sample_path=sample_path,
                    midi_note=36 + idx  # C1 = 36
                )
                rack.drum_pads.append(pad)
        
        return rack
    
    def _parse_instrument_rack(self, device_elem: ET.Element) -> Rack:
        """Parse Instrument Rack"""
        rack = Rack(name=self._get_device_name(device_elem))
        
        # Find chains
        chains = device_elem.find('.//Chains')
        if chains:
            for chain in chains:
                devices = chain.find('.//DeviceChain/Devices')
                if devices:
                    for sub_device in devices:
                        plugin = Plugin(
                            name=self._get_device_name(sub_device),
                            manufacturer='Ableton',
                            is_instrument=True
                        )
                        rack.plugins.append(plugin)
        
        return rack
    
    def _parse_fx_rack(self, device_elem: ET.Element) -> Rack:
        """Parse FX Rack"""
        rack = Rack(name=self._get_device_name(device_elem))
        
        # Find chains
        chains = device_elem.find('.//Chains')
        if chains:
            for chain in chains:
                devices = chain.find('.//DeviceChain/Devices')
                if devices:
                    for sub_device in devices:
                        plugin = Plugin(
                            name=self._get_device_name(sub_device),
                            manufacturer='Ableton',
                            is_instrument=False
                        )
                        rack.plugins.append(plugin)
        
        return rack
    
    def _get_sample_path(self, device_elem: ET.Element) -> str:
        """Extract sample path from Simpler/Sampler"""
        sample_ref = device_elem.find('.//SampleRef/FileRef')
        if sample_ref:
            # Try relative path first
            rel_path = sample_ref.find('.//RelativePath')
            if rel_path is not None:
                value = rel_path.get('Value', '')
                if value:
                    return value
            
            # Try absolute path
            path_elem = sample_ref.find('.//Path')
            if path_elem is not None:
                return path_elem.get('Value', '')
        
        return ''
    
    def _get_device_name(self, device_elem: ET.Element) -> str:
        """Get device name"""
        name_elem = device_elem.find('.//UserName')
        if name_elem is not None:
            name = name_elem.get('Value', '')
            if name:
                return name
        
        # Fallback to device type
        return device_elem.tag.replace('Device', '').replace('Group', '')
    
    def _get_drum_pad_sample(self, chain_elem: ET.Element) -> str:
        """Get sample path from drum pad chain"""
        # Look for Simpler or Sampler device
        simpler = chain_elem.find('.//OriginalSimpler') or chain_elem.find('.//MultiSampler')
        if simpler:
            sample_ref = simpler.find('.//SampleRef/FileRef')
            if sample_ref:
                path_elem = sample_ref.find('.//Path')
                if path_elem is not None:
                    return path_elem.get('Value', '')
        return ''
    
    def _parse_color(self, track_elem: ET.Element) -> tuple:
        """Parse track color"""
        color_elem = track_elem.find('.//Color')
        if color_elem is not None:
            try:
                color_index = int(color_elem.get('Value', '0'))
                return self._color_index_to_rgb(color_index)
            except:
                pass
        return (128, 128, 128)
    
    def _color_index_to_rgb(self, index: int) -> tuple:
        """Convert Ableton color index to RGB"""
        colors = [
            (255, 0, 0),    # Red
            (255, 127, 0),  # Orange
            (255, 255, 0),  # Yellow
            (0, 255, 0),    # Green
            (0, 255, 255),  # Cyan
            (0, 0, 255),    # Blue
            (255, 0, 255),  # Magenta
            (255, 255, 255),  # White
        ]
        return colors[index % len(colors)]
    
    def _get_volume(self, track_elem: ET.Element) -> float:
        """Get track volume"""
        vol_elem = track_elem.find('.//Volume/Manual')
        if vol_elem is not None:
            try:
                return float(vol_elem.get('Value', '1.0'))
            except:
                pass
        return 1.0
    
    def _get_pan(self, track_elem: ET.Element) -> float:
        """Get track pan"""
        pan_elem = track_elem.find('.//Pan/Manual')
        if pan_elem is not None:
            try:
                return float(pan_elem.get('Value', '0.0'))
            except:
                pass
        return 0.0
    
    def _is_muted(self, track_elem: ET.Element) -> bool:
        """Check if track is muted"""
        mute_elem = track_elem.find('.//TrackIsFolded')
        if mute_elem is not None:
            return mute_elem.get('Value', 'false').lower() == 'true'
        return False
    
    def _is_solo(self, track_elem: ET.Element) -> bool:
        """Check if track is solo"""
        solo_elem = track_elem.find('.//Solo')
        if solo_elem is not None:
            return solo_elem.get('Value', 'false').lower() == 'true'
        return False


def parse_ableton_project(filepath: str) -> TransProj:
    """
    Convenience function to parse Ableton project
    
    Args:
        filepath: Path to .als file
        
    Returns:
        TransProj object
    """
    parser = AbletonParser()
    return parser.parse(filepath)


__all__ = ['AbletonParser', 'parse_ableton_project']
