# Rule Questions for the DMs

Questions about how party bonuses work, collected while designing the AWT Party Bonus Bot. Until the DMs answer, the bot uses the **current assumption** listed with each question.

Only **always-on** bonuses that help **allies** are in scope. Bonuses marked 1/combat, Task, or once per day are not tracked by the bot.

---

## Q1. Do Commander "Presence" skills count as auras for Devotion III?

**Card text:** Devotion III (Holy Knight): "Increase Aura bonuses by +1."

**Skills in question:**
- *Commanding Presence* (Commander): "+5 to CM for all allies who are in the same range as you."
- *Inspiring Presence* (Commander): "Add +5 to all CRs made by allies (Does not stack)."

A character can have both Holy Knight and Commander skills, so a Holy Knight with Devotion III can also have these.

**Current assumption:** No. Read literally, only skills named "Aura" are auras: Holy Aura, Bolstering Aura, Protective Aura, Aura of Defense, Aura of Hope. The Presence skills stay at +5.

**If the answer is yes:** Commanding Presence and Inspiring Presence become +6 for a character who also has Devotion III.

---

## Q2. Cult of the Dragon: whose level counts, and does the High Inquisitor benefit?

**Current rule:** The Cult's High Inquisitor (one character) gives other Cult members: level under 10, +1 heart damage; level 10 or higher, +10 CM. Ordinary Cult members give nothing.

**Current assumption:**
- The **recipient's** level decides which of the two they get.
- The High Inquisitor doesn't receive their own bonus (allies only).

**Question:** Is it the recipient's level or the High Inquisitor's? Does the High Inquisitor benefit too?

---

## Q3. GoTH: does Seraph's Affection replace Nuyaru's Love, or add to it?

**Boon text:**
- *Nuyaru's Love* (Trials of the Initiate): "Provide a +1 Combat bonus to all allies excluding yourself."
- *Seraph's Affection* (Trials of the Master): "Provide a +3 Combat bonus to all allies excluding yourself."

**Current assumption (how players have been counting it):** Seraph's Affection is an upgrade. A character with both boons gives +3 CM, not +4.

**Also assumed:** Different GoTH members each give their own boon. Two members with Seraph's Affection give their allies +6 between them.

**Question:** Is that right for both points?

**Answered (2026-09-26):** yes to both. Seraph's Affection replaces Nuyaru's Love; it doesn't add to it, so a character with both gives +3 CM. Each GoTH member gives their own boon (every giver counts, rule 4.1).

---

## Q4. Which items and titles give a bonus to the party?

The bot will keep a fixed list of items and titles that give always-on bonuses to allies, the same way it does for skills. Players pick from the list; they don't type values in. Known or suspected so far:

| Item / title | What we think it gives | Unsure about |
|---|---|---|
| Will's Ward Stone (item) | +5 CM to allies | Is that right? |
| NF (nobuFest pin) (item) | +1 CM, to NF pin holders only, the holder included; stacks (answered: to whom) | Is it +1 CM? |
| Champion of Power (title) | +5 to all challenge rolls, +5 CM to allies | Is that right? |
| Hero of Passion (title) | +1 or more, to other HoP holders only | See Q5. |
| Helping Hands / v2.0 (titles) | Raise the holder's buffs and heals by 1 / 2 | See Q7. |
| Power Supporter, Charitable Adventurer, Element Savant, Joy-Maker, Story Teller, Spook Survivor (titles) | No party bonus | |

**Question:** Please correct the table, and add every other item, pin or title that gives an always-on bonus to allies.

**Answered (2026-09-27):** the table is right. Will's Ward Stone gives +5 CM to allies, the NF pin +1 CM (to NF pin holders only, the holder included, stacking) and Champion of Power +5 to all challenge rolls and +5 CM. Hero of Passion is answered in Q5, and Helping Hands in Q7. The other items and titles are in the catalog (requirements section 8.4); new ones are added there as they come up, through `/request`.

---

## Q5. What does the Hero of Passion (HoP) title give?

HoP is **Hero of Passion**, a title. It goes only to other HoP holders. It has been counted as a bonus of at least +1, varying from holder to holder.

**Answered (2026-09-26):** +3 CM to the holder, and +1 CM to each other HoP holder present. The bot counts only the +1 to other holders; the +3 is self-only, so it's part of the holder's own CM (requirements section 2), and the title's card text says so.

**Questions:**
- What does it give (CM? CR?)?
- Is it always the same amount, or does it vary (e.g. by how many times the title was earned)? If it varies, what are the possible values?

---

## Q6. Does a Guild Thief keep Rat Pack?

**Write-up text:**
- *Rat Pack* (Footpad): "Thieves' Guild Members gain +1 to any Street Work, Burglary, Escape or Combat Rolls for each other Thieves' Guild member present…"
- *Leadership* (Guild Leader, the highest-level Guild Thief present): "When you are present, all Thieves' Guild members gain +2 on their stealth, burglary & streetwork rolls."

**How the bot handles it:** thieves add their rank: *Footpad*, *Burglar* or *Guild Thief*. Each higher rank replaces the lower ones, and every rank grants Rat Pack.

**Current assumption:** Yes, a Guild Thief keeps Rat Pack. A Guild Thief gives Rat Pack **and** Leadership.

**Alternative:** a Guild Thief gives only Leadership, and no longer gives Rat Pack.

**Answered (2026-09-27):** the current assumption is right. A Guild Thief keeps Rat Pack, and gives Rat Pack and Leadership.

---

## Q7. What does Helping Hands actually do, and what does it apply to?

This one needs a careful answer, because **the written title and the way players have been counting it disagree**, and the two readings give very different numbers.

### What we have

- **The title text:** Helping Hands: "Anytime you buff or heal an ally/allies the numerical value is increased by 1." Helping Hands v2.0 is the same with +2.
- **How players have been counting it:** the player-made bonus summaries list it as a flat party bonus: Helping Hands as **+1 healing** to allies, and v2.0 as **+2 healing**.

Read literally, the title gives **nothing on its own**. It only makes the holder's *other* buffs and heals bigger. The player summaries treat it as a bonus in its own right.

### Part 1: What does it really do?

| Reading | What a holder gives the party | Example: a holder whose only other bonus is Bolstering Aura (+2 CM) |
|---|---|---|
| **A. Modifier (the title text)** | Nothing by itself; +1 (v2.0: +2) to the numbers of their own buffs and heals | Bolstering Aura +3 CM; no healing |
| **B. Flat healing (the player summaries)** | +1 (v2.0: +2) heart of healing to allies, every round | Bolstering Aura +2 CM, plus +1 heart healing |
| **C. Both** | Flat healing **and** raises their other buffs and heals | Bolstering Aura +3 CM, plus +1 heart healing |

**Question 1:** Which reading is right: A, B or C?

### Part 2: If it's a modifier (A or C), what does it apply to?

"Buff or heal" could mean a lot or a little. For each of these, does Helping Hands raise it?

| The holder's bonus | Example | Raised by Helping Hands? |
|---|---|---|
| Always-on skill auras | Holy Aura +2 → +3 | ? |
| Guild abilities and ranks | Support +2 → +3; Leadership +2 → +3 | ? |
| Titles and items | Champion of Power +5 → +6; Will's Ward Stone +5 → +6 | ? |
| Bonuses with two numbers | Champion of Power: +5 CR **and** +5 CM → both +6? | ? |
| Once-per-combat buffs and heals (not tracked by the bot) | Healing Hands (Physician's Guild) | Probably yes, but players track these themselves |

**Also:**
- Does it add to Devotion III? (A Holy Knight with both would give Holy Aura +4.)
- Does v2.0 **replace** Helping Hands (+2 total), or add to it (+3)?

**Answered (2026-09-26):** Helping Hands (+1) and Helping Hands v2.0 (+3, replacing Helping Hands) raise only the buffs and heals their holder casts, such as once-per-combat heals. They don't raise auras or any other always-on bonus. The bot doesn't track cast buffs and heals, so in the bot both titles give no party bonus: they're listed with their card text and change no totals.

**Before this answer, the bot assumed** reading **A**, raising every always-on bonus the holder gives allies by +1 (v2.0: +2) on each number.

**Why it matters:** under reading A, Helping Hands can get large. A Paladin with Aura of Hope, Devotion III and Helping Hands v2.0 gives every ally **+13 CM** (10 + 1 + 2), where the player summaries would only have shown +2 healing.

---

## Q8. If a character is summoned, do that character's bonuses count for the party?

Through gameplay, another player's character can sometimes be brought into a game (summoned) even though that character's player isn't playing.

**Questions:**
- Does a summoned character **give** its party bonuses (auras, guild abilities, items, titles) to the party?
- Does it **receive** the party's bonuses?
- Does it count as a character here, or as a summon (which, like minions and allied NPCs, neither gives nor receives bonuses)?

**Current assumption:** No. The bot counts only characters whose players are in the voice channel. A summoned character neither gives nor receives party bonuses, like the minions, summons and allied NPCs in section 2 of the requirements.

**Why it matters:** the bot can't count a character whose player isn't in the voice channel. If summoned characters do count, the bot needs a way for someone in the game to bring them into the party.
