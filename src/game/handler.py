"""
Game packet handlers per expansion. Facade re-exporting handler classes.
"""

from game.core.vanilla import GamePacketHandler
from game.core.tbc import GamePacketHandlerTBC
from game.core.wotlk import GamePacketHandlerWotLK
from game.core.cata import GamePacketHandlerCataclysm
from game.core.mop import GamePacketHandlerMoP

__all__ = [
    "GamePacketHandler",
    "GamePacketHandlerTBC",
    "GamePacketHandlerWotLK",
    "GamePacketHandlerCataclysm",
    "GamePacketHandlerMoP",
]
