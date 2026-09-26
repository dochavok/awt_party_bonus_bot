"""/request (CT-9): a player asks the maintainer for something."""

from awt_bonus.commands._base import Context, Failed, Refused, private
from awt_bonus.commands._types import Reply
from awt_bonus.ports import PostFailed

REQUEST_LENGTH = 1000
"""The longest request text allowed."""

MESSAGE_LENGTH = 2000
"""Discord's limit for one message (OUT-3b)."""


async def request(ctx: Context) -> Reply:
    """Post the player's text, with their name, to the configured channel (CT-9, AD-1)."""
    text = ctx.required("text")
    if len(text) > REQUEST_LENGTH:
        raise Refused(f"A request is at most {REQUEST_LENGTH:,} characters long.")

    member = await ctx.discord.member(ctx.user)
    who = f"{member.display_name} (<@{ctx.user}>)" if member is not None else f"<@{ctx.user}>"
    current = await ctx.store.current_character(ctx.user)
    playing = f", playing {current.name}" if current is not None else ""
    quoted = "\n".join(f"> {line}" for line in text.splitlines())
    post = f"**Request** from {who}{playing}:\n{quoted}"
    if len(post) > MESSAGE_LENGTH:
        raise Refused("That request is too long for one message. Please shorten it.")

    channel = ctx.settings.request_channel
    try:
        await ctx.discord.post(channel, post)
    except PostFailed as error:
        raise Failed(
            f"Your request couldn't be posted: {error}. Please tell the maintainer another way."
        ) from error
    return private(f"Sent to #{channel} for the maintainer. Thanks!")
