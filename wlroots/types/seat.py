# Copyright (c) 2019 Sean Vig

from pywayland.server import Display, Signal
from pywayland.protocol.wayland import WlSeat

from wlroots import ffi, lib


class Seat:
    def __init__(self, display: Display, name: str) -> None:
        """Allocates a new seat and adds a seat global to the display

        :param display:
            The Wayland server display to attach the seat to
        :param name:
            The name of the seat to create
        """
        ptr = lib.wlr_seat_create(display._ptr, name.encode())
        self._ptr = ffi.gc(ptr, lib.wlr_seat_destroy)

        self.request_set_cursor_event = Signal(ptr=ffi.addressof(self._ptr.events.request_set_cursor))

    def destroy(self) -> None:
        """Clean up the seat"""
        if self._ptr is not None:
            ffi.release(self._ptr)
            self._ptr = None

    def set_capabilities(self, capabilities: WlSeat.capability) -> None:
        """Updates the capabilities available on this seat

        Will automatically send them to all clients.

        :param capabilities:
            The Wayland seat capabilities to set on the seat.
        """
        lib.wlr_seat_set_capabilities(self._ptr, capabilities)

    def __enter__(self) -> "Seat":
        """Context manager to clean up the seat"""
        return self

    def __exit__(self, exc_type, exc_value, exc_tb) -> None:
        """Clean up the seat when exiting the context"""
        self.destroy()