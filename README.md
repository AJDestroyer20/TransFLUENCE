# TransFLUENCE v2.0

**Complete Architecture Refactor**

Bidirectional Ableton Live ↔ FL Studio converter using mature libraries.

---

## What's New in v2.0

### Complete Rewrite

**Before (v1.x):**
- Manual XML parsing with XPath
- Hand-written binary FLP format
- Constant bugs with offsets, event IDs, checksums

**Now (v2.0):**
- **PyAbleton** for parsing .als files
- **PyFLP** for generating .flp files
- **TransProj** as universal bridge format

### Benefits

✅ **No more binary format bugs** - PyFLP handles serialization
✅ **Cleaner code** - PyAbleton provides clean object API
✅ **Better compatibility** - Libraries are actively maintained
✅ **Faster development** - Focus on conversion logic, not formats

---

## Installation

```bash
git clone https://github.com/AJDestroyer20/TransFLUENCE.git
cd TransFLUENCE
pip install -r requirements.txt
```

**Dependencies:**
- `pyflp>=2.3.0` - FL Studio binary format
- `pyableton>=0.2.0` - Ableton Live parser

---

## Usage

```bash
# Convert Ableton → FL Studio
python convert.py -i project.als

# Specify output
python convert.py -i project.als -o output.flp

# Verbose mode
python convert.py -i project.als -v
```

---

## Architecture

```
Ableton .als → PyAbleton → TransProj → PyFLP → FL Studio .flp
              (parser)    (universal)  (writer)
```

### TransProj

Universal intermediate format:
- **Track** - Channels with properties
- **Clip** - MIDI/Audio clips
- **Note** - Individual MIDI notes (in beats)
- **Plugin** - Instruments/FX
- **Rack** - Plugin chains/Drum racks

### Data Flow

```python
# 1. Parse Ableton
transproj = parse_ableton_project('project.als')
# → Uses PyAbleton internally

# 2. Write FL Studio
write_flstudio_project(transproj, 'project.flp')
# → Uses PyFLP internally
```

---

## Features

### Implemented

- ✅ Session View → Patterns
- ✅ Arrangement View → Patterns
- ✅ MIDI notes (proper timing)
- ✅ Track properties (name, volume, pan, color)
- ✅ Drum Racks → FPC
- ✅ Audio clips → Sampler
- ✅ MIDI tracks → 3xOsc synth

### In Progress

- 🔄 Plugin parameter mapping
- 🔄 VST state preservation
- 🔄 Automation curves

---

## Why the Refactor?

### Problems in v1.x

1. **Beats → Ticks conversion bugs**
   - Floats truncated prematurely
   - Notes at wrong positions

2. **Event ID validation issues**
   - DWord events (128-191) require exactly 4 bytes
   - Long data was being discarded

3. **Binary format complexity**
   - Manual event packing error-prone
   - Hard to maintain

### Solution: Use Libraries

**PyFLP:**
- Handles all binary serialization
- Proper note format (24 bytes)
- Plugin state management
- Event ordering/checksums

**PyAbleton:**
- Robust XML parsing
- Clean object API
- Active development

---

## Code Comparison

### Before (v1.x)

```python
# Manual binary packing
note_data = struct.pack('<I', position)  # 4 bytes
note_data += struct.pack('<H', duration)  # 2 bytes
note_data += struct.pack('<B', key)       # 1 byte
# ... 15 more fields, easy to mess up

events.append(FLPEvent(203, note_data))
# Hope the format is correct!
```

### After (v2.0)

```python
# PyFLP handles everything
pattern.notes.add(
    position=pos_ticks,
    length=dur_ticks,
    key=note.key,
    velocity=int(note.velocity * 100),
    channel=channel_id
)
# PyFLP serializes correctly automatically
```

---

## Migration from v1.x

v2.0 is a **complete rewrite**. Projects from v1.x will need to be reconverted.

**What's Preserved:**
- TransProj concept (improved)
- Plugin mappings
- Conversion logic

**What's New:**
- PyAbleton parser
- PyFLP writer
- Simplified codebase

---

## Requirements

Python 3.8+

**Required:**
- `pyflp>=2.3.0`
- `pyableton>=0.2.0`

**Optional:**
- `numpy` - For audio processing

---

## License

GPL-3.0

---

## Credits

- **PyFLP** - FL Studio binary format library
- **PyAbleton** - Ableton Live parser
- **DawVert** - convproj concept inspiration

---

## Links

- PyFLP: https://pyflp.readthedocs.io/
- PyAbleton: https://maranedah.github.io/pyableton/
- GitHub: https://github.com/AJDestroyer20/TransFLUENCE

