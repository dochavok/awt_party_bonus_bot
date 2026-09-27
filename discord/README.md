# The bot's Discord profile

What to enter in the Discord developer portal
(<https://discord.com/developers/applications>) for the bot's name, icon and
description. Nothing here is read by the bot's code.

## Icon

Use **`icon.jpg`** (512×512, a smiling baby hippo on white). Upload it under
**General Information → App Icon**; the **Bot** page uses the same image unless
you give it its own. Discord shows it in a circle.

The other two are the same hippo, kept in case they're wanted:

| File | Notes |
|---|---|
| `hippo-dark-background.png` | 756×756. The background is two shades of dark, which shows in the circle. |
| `hippo.webp` | WebP image. The developer portal only takes PNG, JPG or GIF, so it can't be uploaded as is. |

## Banner

Use **`banner-party-aura-small-hippo.png`** (680×240, the size Discord asks for): the
hippo, small, in the middle of glowing aura rings, with party bonuses (shields,
swords, hearts, plus signs) rising towards it. Upload it under **General
Information → App Banner**, and on the **Bot** page if it has its own banner.

In the bot's profile card, the round icon overlaps the banner's bottom-left, so
that corner is kept quiet. The banner's hippo is about two-thirds the size of the
icon's, so the two don't compete.

The other drafts, kept as alternatives:

| File | Notes |
|---|---|
| `banner-party-aura.png` | The same aura, with the hippo full height. |
| `banner-wizard-tower.png` | A starry night, a lit wizard's tower on the hills, and magic drifting to the hippo. |
| `banner-dice.png` | A red game-table with a gold border, scattered dice and a natural 20. |

## Name

- Live bot: **AWT Party Bonus**
- Test bot: **AWT Party Bonus (test)**, so the two are never confused (TS-13).

## Description

Paste this under **General Information → Description**. Discord shows it in the
bot's profile, and allows up to 400 characters (this is 353).

```
Works out party bonuses for Adventures from the Wizards Tower games. It counts everyone in your voice channel and adds up the skills, guild ranks, items and titles their characters give. /partybonus for the party's totals, /mybonus for yours, /breakdown to see how they're worked out. Set up with /character register and /add; /catalog lists everything.
```
