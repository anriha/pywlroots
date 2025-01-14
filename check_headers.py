from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys
import tempfile

INCLUDE_PATH = pathlib.Path(__file__).parent / "wlroots" / "include"
WAYLAND_PROCOTOLS = [
    "stable/xdg-shell/xdg-shell.xml",
    "unstable/idle-inhibit/idle-inhibit-unstable-v1.xml",
    "unstable/pointer-constraints/pointer-constraints-unstable-v1.xml",
]
WLROOTS_PROTOCOLS = [
    "protocol/idle.xml",
    "protocol/wlr-output-power-management-unstable-v1.xml",
    "protocol/wlr-layer-shell-unstable-v1.xml",
]


def get_wayland_protocols_dir() -> pathlib.Path | None:
    args = ["pkgconf", "--variable=pkgdatadir", "wayland-protocols"]
    try:
        output = subprocess.check_output(args).decode().strip()
    except subprocess.CalledProcessError:
        return None

    if output:
        return pathlib.Path(output)
    return None


def header_filename(xml_file: pathlib.Path) -> str:
    return f"{xml_file.stem}-protocol.h"


def generate_protocol_header(
    input_xml: pathlib.Path, output_dir: pathlib.Path
) -> pathlib.Path:
    output_path = output_dir / header_filename(input_xml)
    subprocess.check_output(
        ["wayland-scanner", "server-header", str(input_xml), str(output_path)]
    )
    return output_path


def check(protocols: list[pathlib.Path]) -> None:
    expected_protocol_files = {
        header_filename(protocol_xml) for protocol_xml in protocols
    }
    protocol_files = {path.name for path in INCLUDE_PATH.iterdir()}

    if expected_protocol_files != protocol_files:
        unexpected_files = list(expected_protocol_files - protocol_files)
        extra_files = list(protocol_files - expected_protocol_files)
        raise ValueError(
            f"Unexpected protocol files: {unexpected_files}, Extra files: {extra_files}"
        )

    for protocol_xml in protocols:
        protocol_header_file = INCLUDE_PATH / header_filename(protocol_xml)
        with protocol_header_file.open() as f:
            protocol_header = f.readlines()

        with tempfile.TemporaryDirectory() as output_dir:
            generated_file = generate_protocol_header(
                protocol_xml, pathlib.Path(output_dir)
            )
            with generated_file.open() as f:
                generated_header = f.readlines()

        if len(protocol_header) != len(generated_header):
            raise ValueError(f"Mismatch line count in {protocol_xml.name}")

        for i, (generated_line, line) in enumerate(
            zip(generated_header, protocol_header)
        ):
            if generated_line != line:
                print("Expected:", generated_line.strip("\n"))
                print("Got:", line.strip("\n"))
                raise ValueError(f"Mismatch in {protocol_xml.name} in line {i}")


def generate(protocols: list[pathlib.Path]) -> None:
    for protocol_xml in protocols:
        generate_protocol_header(protocol_xml, INCLUDE_PATH)


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--wayland-dir", default=get_wayland_protocols_dir(), type=pathlib.Path
    )
    parser.add_argument("--wlroots-dir", required=True, type=pathlib.Path)
    parser.add_argument("--generate", action="store_true")
    args = parser.parse_args(argv)

    if args.wayland_dir is None or not args.wayland_dir.exists():
        raise ValueError(
            f"Wayland protocols directory does not exist: {args.wayland_dir}"
        )
    if not args.wlroots_dir.exists():
        raise ValueError(f"Wlroots directory does not exist: {args.wlroots_dir}")

    protocols = [args.wayland_dir / protocol for protocol in WAYLAND_PROCOTOLS] + [
        args.wlroots_dir / protocol for protocol in WLROOTS_PROTOCOLS
    ]

    for protocol in protocols:
        if not protocol.exists():
            raise ValueError(f"Protocol does not exist: {protocol}")

    return protocols, args.generate


if __name__ == "__main__":
    protocols, generate_headers = parse_args(sys.argv[1:])

    if generate_headers:
        generate(protocols)
    else:
        check(protocols)
