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

## Q2. Bonuses never apply to their giver: is that right for everything?

The skill cards all say "allies", so the bot never applies a bonus to the character who gives it, whether CM, CR, damage, damage reduction or healing.

**Current assumption:** Yes, with no exceptions. For example, a character giving 2 hearts of damage reduction to allies doesn't get it themselves.

**Question:** Do any org bonuses or items (e.g. Support, Cult of the Dragon, Wills ward stone) apply to the giver as well?

---

## Q3. Cult of the Dragon: whose level counts, and does the High Priest benefit?

**Current rule:** The Cult's High Priest (one character) gives other Cult members: level under 10, +1 heart damage; level 10 or higher, +10 CM. Ordinary Cult members give nothing.

**Current assumption:**
- The **recipient's** level decides which of the two they get.
- The High Priest doesn't receive their own bonus (allies only).

**Question:** Is it the recipient's level or the High Priest's? Does the High Priest benefit too?

---

## Q4. GoTH: does Seraph's Affection replace Nuyaru's Love, or add to it?

**Boon text:**
- *Nuyaru's Love* (Trials of the Initiate): "Provide a +1 Combat bonus to all allies excluding yourself."
- *Seraph's Affection* (Trials of the Master): "Provide a +3 Combat bonus to all allies excluding yourself."

**Current assumption (how players have been counting it):** Seraph's Affection is an upgrade. A character with both boons gives +3 CM, not +4.

**Also assumed:** Different GoTH members each give their own boon. Two members with Seraph's Affection give their allies +6 between them.

**Question:** Is that right for both points?

---

## Q5. Which items and awards give a bonus to the party?

The bot will keep a fixed list of items and awards that give always-on bonuses to allies, the same way it does for skills. Players pick from the list; they don't type values in. Known or suspected so far:

| Item / award | What we think it gives | Unsure about |
|---|---|---|
| Wills ward stone | +5 CM to allies | Is that right? |
| NF (nobuFest pin) | Probably +1 | +1 to what (CM? CR?), and to whom? |
| Champion of Power | +5 to all challenge rolls, +5 CM | Is it an item, an award or a title? Does it go to allies only? |
| HoP | +1 or more | See Q6. |
| (unknown source) | 1 heart of healing at the end of each round, to allies | What gives this? |
| (unknown source) | 2 hearts of damage reduction, to allies | What gives this? |

**Question:** Please correct the table, and add every other item, pin, award or title that gives an always-on bonus to allies.

---

## Q6. What is HoP, and what does it give?

HoP has been counted as a bonus of at least +1, varying from member to member, going only to other HoP members.

**Questions:**
- What does HoP stand for, and is it a guild, a group or an award?
- What does it give (CM? CR?), and does the amount depend on rank or something else?
- Who receives it: only other HoP members, or all allies?
