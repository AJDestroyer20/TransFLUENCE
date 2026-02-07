"""
Plugin State Generator for FL Studio

Generates plugin state data for native FL plugins
Based on FLP format specifications
"""

import logging
import struct
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ============================================================================
# FL STUDIO PLUGIN STATE FORMATS
# ============================================================================

class PluginStateGenerator:
    """Generate plugin state data for FL Studio plugins"""
    
    @staticmethod
    def generate_sampler_state(sample_path: str = '', volume: float = 1.0, pan: float = 0.5) -> bytes:
        """
        Generate Sampler plugin state
        
        Args:
            sample_path: Path to sample file
            volume: Volume 0.0-1.0
            pan: Pan 0.0-1.0 (0.5 = center)
            
        Returns:
            Binary plugin state data
        """
        data = bytearray()
        
        # Sampler magic header
        data.extend(b'SMPL')  # Magic
        data.extend(struct.pack('<I', 1))  # Version
        
        # Sample path
        if sample_path:
            path_bytes = sample_path.encode('utf-8')
            data.extend(struct.pack('<I', len(path_bytes)))
            data.extend(path_bytes)
        else:
            data.extend(struct.pack('<I', 0))
        
        # Parameters
        data.append(int(volume * 100))  # Volume 0-100
        data.append(int(pan * 100))     # Pan 0-100
        
        logger.debug(f"Generated Sampler state: {len(data)} bytes")
        return bytes(data)
    
    @staticmethod
    def generate_3xosc_state(osc1_vol: float = 1.0, osc1_wave: int = 0,
                             osc2_vol: float = 0.0, osc3_vol: float = 0.0) -> bytes:
        """
        Generate 3xOsc plugin state
        
        Args:
            osc1_vol: Oscillator 1 volume (0-1)
            osc1_wave: Waveform (0=sine, 1=tri, 2=saw, 3=square)
            osc2_vol: Oscillator 2 volume
            osc3_vol: Oscillator 3 volume
            
        Returns:
            Binary plugin state data
        """
        data = bytearray()
        
        # 3xOsc magic header
        data.extend(b'3OSC')  # Magic
        data.extend(struct.pack('<I', 1))  # Version
        
        # Oscillator 1
        data.append(1)  # Enabled
        data.append(osc1_wave)  # Waveform
        data.append(int(osc1_vol * 100))  # Volume
        data.append(64)  # Pan (center)
        
        # Oscillator 2
        data.append(int(osc2_vol > 0))  # Enabled if volume > 0
        data.append(0)  # Waveform
        data.append(int(osc2_vol * 100))
        data.append(64)
        
        # Oscillator 3
        data.append(int(osc3_vol > 0))
        data.append(0)
        data.append(int(osc3_vol * 100))
        data.append(64)
        
        logger.debug(f"Generated 3xOsc state: {len(data)} bytes")
        return bytes(data)
    
    @staticmethod
    def generate_fpc_state(pads: List[Dict]) -> bytes:
        """
        Generate FPC (Fruity Pad Controller) state
        
        Args:
            pads: List of pad dicts with 'sample_path', 'volume', 'pan'
            
        Returns:
            Binary plugin state data
        """
        data = bytearray()
        
        # FPC magic header
        data.extend(b'FPC ')  # Magic (note space)
        data.extend(struct.pack('<I', 1))  # Version
        data.extend(struct.pack('<I', min(len(pads), 16)))  # Pad count (max 16)
        
        # Write up to 16 pads
        for i in range(16):
            if i < len(pads):
                pad = pads[i]
                
                # Pad enabled
                data.append(1)
                
                # Sample path
                sample_path = pad.get('sample_path', '')
                if sample_path:
                    path_bytes = sample_path.encode('utf-8')
                    data.extend(struct.pack('<H', len(path_bytes)))
                    data.extend(path_bytes)
                else:
                    data.extend(struct.pack('<H', 0))
                
                # Parameters
                data.append(int(pad.get('volume', 1.0) * 100))
                data.append(int(pad.get('pan', 0.5) * 100))
                data.append(int(pad.get('tune', 0.5) * 100))  # Tuning
                
            else:
                # Empty pad
                data.append(0)  # Disabled
                data.extend(struct.pack('<H', 0))  # No path
                data.extend(b'\x64\x64\x64')  # Default params
        
        logger.debug(f"Generated FPC state: {len(data)} bytes, {min(len(pads), 16)} pads")
        return bytes(data)
    
    @staticmethod
    def generate_fruity_compressor_state(threshold: float = 0.5, ratio: float = 0.3,
                                         attack: float = 0.1, release: float = 0.3) -> bytes:
        """
        Generate Fruity Compressor state
        
        Args:
            threshold: Threshold 0-1
            ratio: Ratio 0-1
            attack: Attack time 0-1
            release: Release time 0-1
            
        Returns:
            Binary plugin state data
        """
        data = bytearray()
        
        data.extend(b'COMP')  # Magic
        data.extend(struct.pack('<I', 1))  # Version
        
        # Parameters (all 0-100)
        data.append(int(threshold * 100))
        data.append(int(ratio * 100))
        data.append(int(attack * 100))
        data.append(int(release * 100))
        data.append(50)  # Knee (default)
        data.append(0)   # Makeup gain
        
        logger.debug(f"Generated Compressor state: {len(data)} bytes")
        return bytes(data)
    
    @staticmethod
    def generate_fruity_delay_state(time: float = 0.25, feedback: float = 0.5,
                                     mix: float = 0.5) -> bytes:
        """
        Generate Fruity Delay 3 state
        
        Args:
            time: Delay time 0-1
            feedback: Feedback amount 0-1
            mix: Dry/wet mix 0-1
            
        Returns:
            Binary plugin state data
        """
        data = bytearray()
        
        data.extend(b'DLY3')  # Magic
        data.extend(struct.pack('<I', 1))  # Version
        
        # Parameters
        data.append(int(time * 100))
        data.append(int(feedback * 100))
        data.append(int(mix * 100))
        data.append(0)  # Ping pong (off)
        data.append(0)  # Stereo (off)
        
        logger.debug(f"Generated Delay state: {len(data)} bytes")
        return bytes(data)
    
    @staticmethod
    def generate_fruity_reverb_state(size: float = 0.5, decay: float = 0.5,
                                      mix: float = 0.3) -> bytes:
        """
        Generate Fruity Reeverb 2 state
        
        Args:
            size: Room size 0-1
            decay: Decay time 0-1
            mix: Dry/wet mix 0-1
            
        Returns:
            Binary plugin state data
        """
        data = bytearray()
        
        data.extend(b'REV2')  # Magic
        data.extend(struct.pack('<I', 1))  # Version
        
        # Parameters
        data.append(int(size * 100))
        data.append(int(decay * 100))
        data.append(int(mix * 100))
        data.append(50)  # Damping
        data.append(0)   # Pre-delay
        
        logger.debug(f"Generated Reverb state: {len(data)} bytes")
        return bytes(data)
    
    @staticmethod
    def generate_fruity_eq_state(bands: List[Dict]) -> bytes:
        """
        Generate Fruity Parametric EQ 2 state
        
        Args:
            bands: List of EQ band dicts with 'freq', 'gain', 'q'
            
        Returns:
            Binary plugin state data
        """
        data = bytearray()
        
        data.extend(b'PEQ2')  # Magic
        data.extend(struct.pack('<I', 1))  # Version
        data.extend(struct.pack('<I', min(len(bands), 7)))  # Band count (max 7)
        
        # Write up to 7 bands
        for i in range(7):
            if i < len(bands):
                band = bands[i]
                data.append(1)  # Enabled
                data.append(int(band.get('freq', 0.5) * 100))
                data.append(int(band.get('gain', 0.5) * 100))
                data.append(int(band.get('q', 0.5) * 100))
                data.append(band.get('type', 0))  # Type (0=peak, 1=low shelf, etc)
            else:
                data.extend(b'\x00\x32\x32\x32\x00')  # Disabled band
        
        logger.debug(f"Generated EQ state: {len(data)} bytes, {min(len(bands), 7)} bands")
        return bytes(data)
    
    @staticmethod
    def generate_generic_state(plugin_name: str, params: Dict[str, float]) -> bytes:
        """
        Generate generic plugin state
        
        Args:
            plugin_name: Plugin name
            params: Parameter dict {name: value}
            
        Returns:
            Binary plugin state data
        """
        data = bytearray()
        
        # Generic header
        data.extend(b'PLGN')  # Magic
        data.extend(struct.pack('<I', 1))  # Version
        
        # Plugin name
        name_bytes = plugin_name.encode('utf-8')
        data.extend(struct.pack('<H', len(name_bytes)))
        data.extend(name_bytes)
        
        # Parameters
        data.extend(struct.pack('<I', len(params)))
        for name, value in params.items():
            # Parameter name
            param_bytes = name.encode('utf-8')
            data.extend(struct.pack('<H', len(param_bytes)))
            data.extend(param_bytes)
            
            # Parameter value (float)
            data.extend(struct.pack('<f', value))
        
        logger.debug(f"Generated generic state for {plugin_name}: {len(data)} bytes")
        return bytes(data)


# ============================================================================
# PLUGIN STATE FACTORY
# ============================================================================

class PluginStateFactory:
    """Factory to generate appropriate plugin state for FL plugins"""
    
    GENERATORS = {
        'Sampler': PluginStateGenerator.generate_sampler_state,
        '3xOsc': PluginStateGenerator.generate_3xosc_state,
        'FPC': PluginStateGenerator.generate_fpc_state,
    }
    
    EFFECTS = {
        'Fruity Compressor': PluginStateGenerator.generate_fruity_compressor_state,
        'Fruity Delay 3': PluginStateGenerator.generate_fruity_delay_state,
        'Fruity Reeverb 2': PluginStateGenerator.generate_fruity_reverb_state,
        'Fruity Parametric EQ 2': PluginStateGenerator.generate_fruity_eq_state,
    }
    
    @classmethod
    def generate(cls, plugin_name: str, **kwargs) -> bytes:
        """
        Generate plugin state for given plugin
        
        Args:
            plugin_name: FL Studio plugin name
            **kwargs: Plugin-specific parameters
            
        Returns:
            Binary plugin state data
        """
        # Try generators first
        if plugin_name in cls.GENERATORS:
            return cls.GENERATORS[plugin_name](**kwargs)
        
        # Try effects
        if plugin_name in cls.EFFECTS:
            return cls.EFFECTS[plugin_name](**kwargs)
        
        # Fallback to generic
        logger.warning(f"No specific generator for {plugin_name}, using generic")
        return PluginStateGenerator.generate_generic_state(plugin_name, kwargs.get('params', {}))


__all__ = ['PluginStateGenerator', 'PluginStateFactory']
