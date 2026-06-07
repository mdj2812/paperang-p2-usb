#!/usr/bin/env python3
"""
Paperang P2 USB Printer CLI
Thin wrapper around paperang-p2-lib.
"""

import sys
import os
import argparse

from contextlib import contextmanager

from paperang import PaperangP2, load_profiles, list_profiles


PROFILES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'profiles.json')


# ── helpers ─────────────────────────────────────────────────────

def _add_profile_args(parser):
    parser.add_argument('--profile', help='Image profile')
    parser.add_argument('--density', type=int, help='Heat density 0-100')


def _add_image_args(parser):
    parser.add_argument('--threshold', type=int, help='Binarization threshold')
    parser.add_argument('--brightness', type=float, help='Brightness multiplier')
    parser.add_argument('--contrast', type=float, help='Contrast multiplier')


def _resolve(profiles, profile, args):
    """Resolve print parameters: CLI args override profile defaults."""
    ps = profiles.get(profile, {}) if profile else {}
    return {
        'heat_density': args.density if args.density is not None
                        else ps.get('heat_density', 75),
        'threshold': getattr(args, 'threshold', None) or ps.get('threshold', 128),
        'brightness': getattr(args, 'brightness', None) or ps.get('brightness', 1.0),
        'contrast': getattr(args, 'contrast', None) or ps.get('contrast', 1.0),
    }


@contextmanager
def connect_printer():
    """Context manager that yields a connected PaperangP2 and
    disposes USB resources on exit."""
    p = PaperangP2()
    p.connect()
    try:
        yield p
    finally:
        if p.dev:
            import usb.util
            usb.util.dispose_resources(p.dev)


# ── info handlers ───────────────────────────────────────────────

_INFO_FIELDS = [
    ("battery",     "Battery",          lambda p: p.get_battery()),
    ("status",      "Status",           lambda p: p.get_status()),
    ("voltage",     "Voltage",          lambda p: p.get_voltage()),
    ("temperature", "Temperature",      lambda p: p.get_temperature()),
    ("heat",        "Heat Density",     lambda p: p.get_heat_density()),
    ("paper",       "Paper Type",       lambda p: p.get_paper_type()),
    ("version",     "Firmware Version", lambda p: p.get_version()),
    ("model",       "Model",            lambda p: p.get_model()),
    ("serial",      "Serial Number",    lambda p: p.get_sn()),
    ("board",       "Board Version",    lambda p: p.get_board_version()),
    ("hw",          "Hardware Info",    lambda p: p.get_hw_info()),
    ("mac",         "Bluetooth MAC",    lambda p: p.get_bt_mac()),
    ("country",     "Country",          lambda p: p.get_country()),
    ("max_gap",     "Max Gap",          lambda p: p.get_max_gap()),
    ("power_down",  "Power Down Time",  lambda p: p.get_power_down_time()),
    ("factory",     "Factory Status",   lambda p: p.get_factory_status()),
]

_INFO_MAP = {k: (label, fn) for k, label, fn in _INFO_FIELDS}


def cmd_info(args):
    with connect_printer() as p:
        if args.field == "all":
            print("Paperang P2 Telemetry")
            print("=" * 30)
            for key, label, fn in _INFO_FIELDS:
                val = fn(p)
                print(f"  {label:.<20} {val}")
        else:
            label, fn = _INFO_MAP[args.field]
            val = fn(p)
            print(f"{label}: {val}")


# ── print handlers ──────────────────────────────────────────────

def cmd_print_text(args):
    profiles = load_profiles(PROFILES_PATH)
    params = _resolve(profiles, args.profile, args)
    with connect_printer() as p:
        p.print_text(
            args.content, font_size=args.font_size,
            heat_density=params['heat_density'])


def cmd_print_image(args):
    profiles = load_profiles(PROFILES_PATH)
    params = _resolve(profiles, args.profile, args)
    with connect_printer() as p:
        p.print_image(
            args.path, heat_density=params['heat_density'],
            threshold=params['threshold'], brightness=params['brightness'],
            contrast=params['contrast'])


def cmd_print_qr(args):
    profiles = load_profiles(PROFILES_PATH)
    params = _resolve(profiles, args.profile, args)
    with connect_printer() as p:
        p.print_qr(
            args.content, heat_density=params['heat_density'],
            max_width=args.qr_size)


def cmd_print_pickup(args):
    profiles = load_profiles(PROFILES_PATH)
    params = _resolve(profiles, args.profile, args)
    with connect_printer() as p:
        p.print_pickup_code(args.code, heat_density=params['heat_density'])


def cmd_print_test(args):
    _ = args  # unused, but kept for uniform handler signature
    with connect_printer() as p:
        p.print_test_page()


def cmd_print_pattern(args):
    with connect_printer() as p:
        p.print_pattern_test()


def cmd_print_density(args):
    with connect_printer() as p:
        p.print_heat_density_test()


def cmd_feed(args):
    with connect_printer() as p:
        p.feed(args.lines)


def cmd_profile_list(args):
    list_profiles(PROFILES_PATH)


# ── main ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Paperang P2 Printer Control',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  paperang_p2.py text "Hello"
  paperang_p2.py image photo.jpg --profile high_contrast
  paperang_p2.py qr "https://example.com"
  paperang_p2.py pickup "19-4308"
  paperang_p2.py test
  paperang_p2.py info all
  paperang_p2.py info battery
  paperang_p2.py feed 100
  paperang_p2.py profile list
        """)
    sub = parser.add_subparsers(dest='cmd', required=True)

    # ── print ──
    p_text = sub.add_parser('text', help='Print text')
    p_text.add_argument('content', help='Text to print')
    _add_profile_args(p_text)
    p_text.add_argument('--font-size', type=int, default=24, help='Font size (12-96, default 24)')
    p_text.set_defaults(func=cmd_print_text)

    p_img = sub.add_parser('image', help='Print image (local file or URL)')
    p_img.add_argument('path', help='Image file path or URL')
    _add_profile_args(p_img)
    _add_image_args(p_img)
    p_img.set_defaults(func=cmd_print_image)

    p_qr = sub.add_parser('qr', help='Print QR code')
    p_qr.add_argument('content', help='QR code content')
    _add_profile_args(p_qr)
    p_qr.add_argument('--qr-size', type=int, default=500, help='QR size in px (default 500)')
    p_qr.set_defaults(func=cmd_print_qr)

    p_pu = sub.add_parser('pickup', help='Print pickup code')
    p_pu.add_argument('code', help='Pickup code')
    _add_profile_args(p_pu)
    p_pu.set_defaults(func=cmd_print_pickup)

    p_t = sub.add_parser('test', help='Print test page')
    _add_profile_args(p_t)
    p_t.set_defaults(func=cmd_print_test)

    # These can't use the --profile handler since they don't have those args
    sub.add_parser('pattern', help='Print pattern test').set_defaults(func=cmd_print_pattern)
    sub.add_parser('density', help='Print heat density test').set_defaults(func=cmd_print_density)

    # ── info ──
    p_info = sub.add_parser('info', help='Read printer telemetry')
    choices = ['all'] + [k for k, _, _ in _INFO_FIELDS]
    p_info.add_argument('field', nargs='?', default='all', choices=choices,
                        help='Field to read (default: all)')
    p_info.set_defaults(func=cmd_info)

    # ── feed ──
    p_feed = sub.add_parser('feed', help='Feed paper')
    p_feed.add_argument('lines', nargs='?', type=int, default=100,
                        help='Lines to feed (default 100)')
    p_feed.set_defaults(func=cmd_feed)

    # ── profile ──
    p_prof = sub.add_parser('profile', help='Profile management')
    p_prof.add_argument('action', choices=['list'], help='Action')
    p_prof.set_defaults(func=cmd_profile_list)

    args = parser.parse_args()

    try:
        args.func(args)
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
