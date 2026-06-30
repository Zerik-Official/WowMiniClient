"""
Channel routing map builder from parsed configuration.
"""

from __future__ import annotations

from common.types import ChatDirection, WowChatConfig, global_state


def build_channel_maps(config: WowChatConfig) -> None:
    """
    Populate global routing maps from parsed channel configs.

    Args:
        config: Parsed application configuration.
    """
    for entry in config.channels:
        direction = entry.chat_direction
        if direction in (ChatDirection.BOTH, ChatDirection.DISCORD_TO_WOW):
            global_state.discord_to_wow[entry.discord.channel].add(entry.wow)
        if direction in (ChatDirection.BOTH, ChatDirection.WOW_TO_DISCORD):
            key = (entry.wow.type, entry.wow.channel.lower() if entry.wow.channel else None)
            global_state.wow_to_discord[key].add(
                (entry.discord.channel, entry.discord),
            )
            if entry.wow.filters and entry.wow.filters.enabled:
                global_state.wow_channel_filters[key] = entry.wow.filters

    guild = config.guild
    if guild:
        for event_key, notif in guild.notification_configs.items():
            if notif.enabled:
                channel = notif.channel or config.discord.bot_system_channel or "guild-chat"
                global_state.guild_events_to_discord[event_key].add(channel)
