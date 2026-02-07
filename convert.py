#!/usr/bin/env python3
"""
TransFLUENCE v2.0 - Ableton ↔ FL Studio Converter

Complete architecture refactor using PyAbleton and PyFLP.
No more manual binary format handling!
"""

import argparse
import sys
import logging
from pathlib import Path

from parsers.ableton_parser import parse_ableton_project
from writers.flstudio_writer import write_flstudio_project

VERSION = '2.0.0'


def setup_logging(verbose: bool = False):
    """Configure logging"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(levelname)-8s | %(message)s'
    )


def convert_file(input_file: str, output_file: str = None, verbose: bool = False) -> bool:
    """
    Convert single file
    
    Args:
        input_file: Input .als file
        output_file: Output .flp file (optional)
        verbose: Verbose output
        
    Returns:
        True if successful
    """
    logger = logging.getLogger('transfluence')
    
    try:
        # Validate input
        input_path = Path(input_file)
        if not input_path.exists():
            logger.error(f"Input file not found: {input_file}")
            return False
        
        # Determine output
        if not output_file:
            output_file = str(input_path.with_suffix('.flp'))
        
        # Parse Ableton → TransProj
        logger.info("Step 1/2: Parsing Ableton project...")
        transproj = parse_ableton_project(input_file)
        
        # Write TransProj → FL Studio
        logger.info("Step 2/2: Writing FL Studio project...")
        write_flstudio_project(transproj, output_file)
        
        # Verify
        output_path = Path(output_file)
        if not output_path.exists():
            logger.error("Output file was not created")
            return False
        
        size = output_path.stat().st_size
        logger.info(f"✓ Success: {size:,} bytes")
        
        return True
        
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        logger.error("Install: pip install pyflp")
        return False
    
    except Exception as e:
        logger.exception(f"Conversion failed: {e}")
        return False


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        prog='transfluence',
        description='TransFLUENCE v2.0 - Ableton ↔ FL Studio Converter',
        epilog='Built with PyAbleton and PyFLP'
    )
    
    parser.add_argument('-i', '--input', required=True,
                       help='Input .als file')
    parser.add_argument('-o', '--output',
                       help='Output .flp file')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Verbose output')
    parser.add_argument('--version', action='version',
                       version=f'TransFLUENCE v{VERSION}')
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    # Header
    print("=" * 70)
    print(f"TransFLUENCE v{VERSION}")
    print("Ableton Live ↔ FL Studio Converter")
    print("Architecture Refactor: PyAbleton + PyFLP")
    print("=" * 70)
    
    try:
        print(f"\nInput:  {args.input}")
        if args.output:
            print(f"Output: {args.output}")
        print("-" * 70)
        
        success = convert_file(args.input, args.output, args.verbose)
        
        print("\n" + "=" * 70)
        if success:
            print("SUCCESS")
            print("=" * 70)
            output = args.output or str(Path(args.input).with_suffix('.flp'))
            print(f"Output: {output}")
        else:
            print("FAILED")
            print("=" * 70)
        print("=" * 70)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n\nCancelled by user")
        return 130
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
