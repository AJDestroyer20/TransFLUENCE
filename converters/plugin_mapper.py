"""
Plugin Mapping: Ableton ↔ FL Studio

Complete mapping system for devices, parameters, and racks
Based on PyFLP and PyAbleton documentation
"""

import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ============================================================================
# ABLETON → FL STUDIO DEVICE MAPPINGS
# ============================================================================

ABLETON_TO_FL_INSTRUMENTS = {
    # Native Ableton Instruments → FL Studio
    'OriginalSimpler': 'Sampler',           # Simple sampler
    'MultiSampler': 'DirectWave',           # Advanced sampler
    'Operator': '3xOsc',                    # FM synthesis → Basic synth
    'Analog': 'Sytrus',                     # Analog modeling → FM synth
    'Electric': '3xOsc',                    # Electric piano → Basic synth
    'Collision': 'FPC',                     # Physical modeling → Drum machine
    'Tension': 'Sytrus',                    # String modeling → FM synth
    'Wavetable': 'Harmor',                  # Wavetable → Advanced synth
    'DrumSynth': 'FPC',                     # Drum synth → Drum machine
    
    # Synth racks
    'InstrumentGroupDevice': 'Patcher',     # Instrument Rack → Patcher
}

ABLETON_TO_FL_EFFECTS = {
    # Ableton Effects → FL Studio Effects
    'AutoFilter': 'Fruity Love Philter',
    'AutoPan': 'Fruity Stereo Enhancer',
    'BeatRepeat': 'Fruity Slicer',
    'Cabinet': 'Fruity Guitar Amp',
    'Chorus': 'Fruity Chorus',
    'Compressor': 'Fruity Compressor',
    'Delay': 'Fruity Delay 3',
    'Distortion': 'Fruity Fast Dist',
    'Echo': 'Fruity Delay 3',
    'Eq8': 'Fruity Parametric EQ 2',
    'EQ Eight': 'Fruity Parametric EQ 2',
    'Erosion': 'Fruity Bitcrusher',
    'FilterDelay': 'Fruity Delay 3',
    'Flanger': 'Fruity Flanger',
    'GlueCompressor': 'Fruity Limiter',
    'Glue Compressor': 'Fruity Limiter',
    'GrainDelay': 'Fruity Granulizer',
    'Limiter': 'Fruity Limiter',
    'Looper': 'Fruity Slicer',
    'Overdrive': 'Fruity Fast Dist',
    'Phaser': 'Fruity Phaser',
    'PingPongDelay': 'Fruity Delay 3',
    'Redux': 'Fruity Bitcrusher',
    'Reverb': 'Fruity Reeverb 2',
    'Saturator': 'Fruity Waveshaper',
    'SimpleDelay': 'Fruity Delay 3',
    'Utility': 'Fruity Balance',
    'Vocoder': 'Vocodex',
    'DrumBuss': 'Maximus',
    'Drum Buss': 'Maximus',
    'Roar': 'Distructor',
    
    # FX racks
    'AudioEffectGroupDevice': 'Patcher',
}

ABLETON_TO_FL_DRUMS = {
    'DrumGroupDevice': 'FPC',
    'DrumSynth': 'FPC',
}


# ============================================================================
# PARAMETER NAME MAPPINGS (Ableton → FL Studio)
# ============================================================================

PARAMETER_MAPPINGS = {
    # Volume & Gain
    'Volume': 'Volume',
    'Level': 'Level',
    'Gain': 'Gain',
    'Output': 'Out',
    
    # Filter
    'FilterFreq': 'CutOff',
    'Frequency': 'Frequency',
    'Cutoff': 'Cutoff',
    'FilterRes': 'Resonance',
    'Resonance': 'Resonance',
    'FilterType': 'Type',
    
    # Envelope (ADSR)
    'Attack': 'ATT',
    'AttackTime': 'ATT',
    'Decay': 'DEC',
    'DecayTime': 'DEC',
    'Sustain': 'SUS',
    'SustainLevel': 'SUS',
    'Release': 'REL',
    'ReleaseTime': 'REL',
    
    # LFO
    'LfoRate': 'Speed',
    'LfoAmount': 'Depth',
    'LfoWaveform': 'Shape',
    
    # Effects common
    'DryWet': 'Mix',
    'Mix': 'Mix',
    'Blend': 'Mix',
    'Feedback': 'Feedback',
    'FeedbackAmount': 'Feedback',
    'Rate': 'Rate',
    'Speed': 'Speed',
    'Depth': 'Depth',
    'Amount': 'Amount',
    'Intensity': 'Mod',
    
    # Delay specific
    'DelayTime': 'Time',
    'Time': 'Time',
    'DelayFeedback': 'Feedback',
    'Sync': 'Sync',
    
    # Reverb specific
    'RoomSize': 'Size',
    'Size': 'Size',
    'DecayTime': 'Decay',
    'Damping': 'Damp',
    'HighDamp': 'Damp',
    'PreDelay': 'PreDelay',
    
    # Compressor specific
    'Threshold': 'Threshold',
    'Ratio': 'Ratio',
    'Knee': 'Knee',
    'MakeupGain': 'Gain',
    
    # EQ specific
    'Freq': 'Freq',
    'Q': 'Q',
    'BandGain': 'Gain',
    
    # Distortion
    'Drive': 'Drive',
    'Bias': 'Bias',
    'Shape': 'Shape',
}


# ============================================================================
# PARAMETER VALUE RANGES (for conversion)
# ============================================================================

PARAMETER_RANGES = {
    # Ableton (min, max) → FL Studio (min, max)
    'Volume': ((0, 1), (0, 100)),         # 0-1 → 0-100
    'Pan': ((-1, 1), (0, 100)),           # -1,1 → 0-100 (50 center)
    'FilterFreq': ((20, 20000), (0, 100)), # Hz → 0-100
    'Resonance': ((0, 1), (0, 100)),
    'DryWet': ((0, 1), (0, 100)),
    'Attack': ((0, 5), (0, 100)),         # Seconds → 0-100
    'Decay': ((0, 5), (0, 100)),
    'Sustain': ((0, 1), (0, 100)),
    'Release': ((0, 5), (0, 100)),
}


# ============================================================================
# FL STUDIO PLUGIN TYPES (from PyFLP docs)
# ============================================================================

FL_PLUGIN_TYPES = {
    # Generators (instruments)
    'generator': [
        '3xOsc', 'Sytrus', 'Harmor', 'Harmless', 'PoiZone', 
        'Sakura', 'Sawer', 'Toxic Biohazard', 'Drumaxx',
        'DirectWave', 'FPC', 'Sampler', 'FLEX',
    ],
    
    # Effects
    'effect': [
        'Fruity Parametric EQ 2', 'Fruity Compressor', 'Fruity Limiter',
        'Fruity Delay 3', 'Fruity Delay Bank', 'Fruity Reeverb 2',
        'Fruity Chorus', 'Fruity Flanger', 'Fruity Phaser',
        'Fruity Fast Dist', 'Fruity Waveshaper', 'Fruity Bitcrusher',
        'Fruity Love Philter', 'Fruity Stereo Enhancer', 'Fruity Balance',
        'Fruity Slicer', 'Fruity Granulizer', 'Vocodex',
    ],
    
    # Special
    'patcher': ['Patcher'],
}


# ============================================================================
# RACK MAPPINGS
# ============================================================================

RACK_MAPPINGS = {
    # Ableton Rack types → FL Studio equivalents
    'InstrumentGroupDevice': {
        'fl_type': 'Patcher',
        'description': 'Instrument Rack → Patcher with multiple generators',
    },
    'AudioEffectGroupDevice': {
        'fl_type': 'Patcher',
        'description': 'FX Rack → Patcher with multiple effects',
    },
    'DrumGroupDevice': {
        'fl_type': 'FPC',
        'description': 'Drum Rack → FPC (Fruity Pad Controller)',
        'max_pads': 16,  # FPC has 16 pads
        'note_start': 36,  # MIDI note C1
    },
}


# ============================================================================
# MAPPER CLASS
# ============================================================================

class PluginMapper:
    """Map plugins, parameters, and racks between Ableton and FL Studio"""
    
    @staticmethod
    def ableton_to_fl(ableton_name: str, is_instrument: bool = False,
                      device_type: Optional[str] = None) -> str:
        """
        Map Ableton device to FL Studio plugin
        
        Args:
            ableton_name: Ableton device name
            is_instrument: Whether it's an instrument
            
        Returns:
            FL Studio plugin name
        """
        lookup_name = device_type or ableton_name

        # Check drums first (special case)
        if lookup_name in ABLETON_TO_FL_DRUMS:
            return ABLETON_TO_FL_DRUMS[lookup_name]
        
        # Check instruments
        if is_instrument:
            return ABLETON_TO_FL_INSTRUMENTS.get(lookup_name, 'Sampler')
        
        # Check effects
        return ABLETON_TO_FL_EFFECTS.get(lookup_name, ableton_name)
    
    @staticmethod
    def map_parameter_name(param_name: str) -> str:
        """Map parameter name from Ableton to FL Studio"""
        return PARAMETER_MAPPINGS.get(param_name, param_name)
    
    @staticmethod
    def map_parameter_value(param_name: str, ableton_value: float) -> float:
        """
        Convert parameter value from Ableton range to FL Studio range
        
        Args:
            param_name: Parameter name
            ableton_value: Value in Ableton range
            
        Returns:
            Value in FL Studio range
        """
        if param_name not in PARAMETER_RANGES:
            return ableton_value
        
        (able_min, able_max), (fl_min, fl_max) = PARAMETER_RANGES[param_name]
        
        # Normalize to 0-1
        normalized = (ableton_value - able_min) / (able_max - able_min)
        
        # Scale to FL range
        fl_value = fl_min + (normalized * (fl_max - fl_min))
        
        return fl_value
    
    @staticmethod
    def get_rack_mapping(rack_type: str) -> dict:
        """Get rack mapping info"""
        return RACK_MAPPINGS.get(rack_type, {
            'fl_type': 'Patcher',
            'description': 'Unknown rack type',
        })
    
    @staticmethod
    def get_plugin_category(plugin_name: str) -> str:
        """
        Get FL Studio plugin category
        
        Returns:
            'generator', 'effect', 'patcher', or 'unknown'
        """
        for category, plugins in FL_PLUGIN_TYPES.items():
            if plugin_name in plugins:
                return category
        return 'unknown'
    
    @staticmethod
    def is_drum_device(device_name: str) -> bool:
        """Check if device is a drum device"""
        return device_name in ABLETON_TO_FL_DRUMS


__all__ = [
    'PluginMapper',
    'ABLETON_TO_FL_INSTRUMENTS',
    'ABLETON_TO_FL_EFFECTS',
    'ABLETON_TO_FL_DRUMS',
    'PARAMETER_MAPPINGS',
    'RACK_MAPPINGS',
]
