#!/usr/bin/env python3
"""
Paperang P2 USB Printer CLI
Thin wrapper around paperang-p2-lib.
"""

import sys
import os
import argparse

# Add paperang-p2-lib to sys.path
_lib_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'paperang-p2-lib', 'src')
if os.path.isdir(_lib_dir) and _lib_dir not in sys.path:
    sys.path.insert(0, _lib_dir)

from paperang import PaperangP2, load_profiles, list_profiles


PROFILES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'profiles.json')


def main():
    parser = argparse.ArgumentParser(description='Paperang P2 Printer Control')
    parser.add_argument('-t', '--text', help='Print text')
    parser.add_argument('-i', '--image', help='Print image')
    parser.add_argument('-p', '--profile', help='Use profile (portrait, landscape, document, high_contrast, light)')
    parser.add_argument('--threshold', type=int, help='Binarization threshold 0-255 (higher = less black)')
    parser.add_argument('--brightness', type=float, help='Brightness multiplier (<1 = darker, >1 = brighter)')
    parser.add_argument('--contrast', type=float, help='Contrast multiplier (<1 = less contrast, >1 = more contrast)')
    parser.add_argument('-q', '--qr', help='Print QR code')
    parser.add_argument('--qr-size', type=int, default=500, help='QR code width in pixels (default 500, max 576)')
    parser.add_argument('-f', '--font-size', type=int, default=24, help='Font size')
    parser.add_argument('-d', '--density', type=int, help='Heat density 0-100')
    parser.add_argument('--test', action='store_true', help='Print test page')
    parser.add_argument('--pattern-test', action='store_true', help='Print pattern test (line/column/multi-packet)')
    parser.add_argument('--density-test', action='store_true', help='Print heat density test')
    parser.add_argument('--status', action='store_true', help='Get printer status')
    parser.add_argument('--battery', action='store_true', help='Get battery level')
    parser.add_argument('--list-profiles', action='store_true', help='List available profiles')
    parser.add_argument('--pickup-code', help='Print a pickup code in large bold style')

    args = parser.parse_args()

    # List profiles and exit
    if args.list_profiles:
        list_profiles(PROFILES_PATH)
        return 0

    # Load profile settings
    profiles = load_profiles(PROFILES_PATH)
    profile_settings = profiles.get(args.profile, {}) if args.profile else {}

    # Use profile values or defaults
    threshold = args.threshold if args.threshold is not None else profile_settings.get('threshold', 180)
    brightness = args.brightness if args.brightness is not None else profile_settings.get('brightness', 1.5)
    contrast = args.contrast if args.contrast is not None else profile_settings.get('contrast', 0.6)
    heat_density = args.density if args.density is not None else profile_settings.get('heat_density', 75)

    printer = PaperangP2()

    try:
        printer.connect()

        if args.test:
            printer.print_test_page()
        elif args.pattern_test:
            printer.print_pattern_test()
        elif args.density_test:
            printer.print_heat_density_test()
        elif args.status:
            status = printer.get_status()
            print(f"Status: {status}")
        elif args.battery:
            battery = printer.get_battery()
            print(f"Battery: {battery}")
        elif args.text:
            printer.print_text(args.text, font_size=args.font_size, heat_density=heat_density)
        elif args.image:
            printer.print_image(
                args.image, heat_density=heat_density,
                threshold=threshold, brightness=brightness,
                contrast=contrast)
        elif args.qr:
            printer.print_qr(args.qr, heat_density=heat_density, max_width=args.qr_size)
        elif args.pickup_code:
            printer.print_pickup_code(args.pickup_code, heat_density=heat_density)
        else:
            # Default test text
            test_text = """Paperang P2 Test Print
==================
Printer working!

Time: """ + os.popen('date "+%Y-%m-%d %H:%M:%S"').read().strip()
            printer.print_text(test_text, heat_density=heat_density)

        print("Print complete!")
        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
