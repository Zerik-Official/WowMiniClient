"""ASCII banner printed when the client or the setup wizard starts."""

# Standard library
from __future__ import annotations
import io
import sys

RELEASE_DATE: str = "31/10/2026"
VERSION: str = "1.0.0"

BANNER: str = rf"""
██╗    ██╗ ██████╗ ██╗    ██╗                                     
██║    ██║██╔═══██╗██║    ██║                                     
██║ █╗ ██║██║   ██║██║ █╗ ██║                                     
██║███╗██║██║   ██║██║███╗██║                                     
╚███╔███╔╝╚██████╔╝╚███╔███╔╝                                     
 ╚══╝╚══╝  ╚═════╝  ╚══╝╚══╝                                      
                                                                  
        ███╗   ███╗██╗███╗   ██╗██╗                               
        ████╗ ████║██║████╗  ██║██║                               
        ██╔████╔██║██║██╔██╗ ██║██║                               
        ██║╚██╔╝██║██║██║╚██╗██║██║                               
        ██║ ╚═╝ ██║██║██║ ╚████║██║                               
        ╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═╝                               
                                                                  
                     ██████╗██╗     ██╗███████╗███╗   ██╗████████╗
                    ██╔════╝██║     ██║██╔════╝████╗  ██║╚══██╔══╝
                    ██║     ██║     ██║█████╗  ██╔██╗ ██║   ██║   
                    ██║     ██║     ██║██╔══╝  ██║╚██╗██║   ██║   
                    ╚██████╗███████╗██║███████╗██║ ╚████║   ██║   
                     ╚═════╝╚══════╝╚═╝╚══════╝╚═╝  ╚═══╝   ╚═╝
----------------------------------------------------------------------------
Release date: {RELEASE_DATE}   |   Version: {VERSION}   | By: Zerik-Official
----------------------------------------------------------------------------
"""

def _ensure_utf8_stdout() -> None:
    """
    Switch stdout to UTF-8 when it uses a legacy encoding.

    Windows consoles and redirected output default to a code page such as
    cp1252, which cannot encode the box-drawing characters of the banner.
    """
    encoding: str = (getattr(sys.stdout, "encoding", None) or "").lower()
    if encoding.replace("-", "") == "utf8":
        return
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def print_banner() -> None:
    """Print the ASCII banner to the console."""
    _ensure_utf8_stdout()
    print(BANNER)