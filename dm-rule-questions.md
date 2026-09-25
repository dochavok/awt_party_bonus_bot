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

## Q2. Cult of the Dragon: whose level counts, and does the High Priest benefit?

**Current rule:** The Cult's High Priest (one character) gives other Cult members: level under 10, +1 heart damage; level 10 or higher, +10 CM. Ordinary Cult members give nothing.

**Current assumption:**
- The **recipient's** level decides which of the two they get.
- The High Priest doesn't receive their own bonus (allies only).

**Question:** Is it the recipient's level or the High Priest's? Does the High Priest benefit too?

---

## Q3. GoTH: does Seraph's Affection replace Nuyaru's Love, or add to it?

**Boon text:**
- *Nuyaru's Love* (Trials of the Initiate): "Provide a +1 Combat bonus to all allies excluding yourself."
- *Seraph's Affection* (Trials of the Master): "Provide a +3 Combat bonus to all allies excluding yourself."

**Current assumption (how players have been counting it):** Seraph's Affection is an upgrade. A character with both boons gives +3 CM, not +4.

**Also assumed:** Different GoTH members each give their own boon. Two members with Seraph's Affection give their allies +6 between them.

**Question:** Is that right for both points?

---

## Q4. Which items and awards give a bonus to the party?

The bot will keep a fixed list of items and awards that give always-on bonuses to allies, the same way it does for skills. Players pick from the list; they don't type values in. Known or suspected so far:

| Item / award | What we think it gives | Unsure about |
|---|---|---|
| Wills ward stone | +5 CM to allies | Is that right? |
| NF (nobuFest pin) | Probably +1 | +1 to what (CM? CR?), and to whom? |
| Champion of Power | +5 to all challenge rolls, +5 CM | Is it an item, an award or a title? Does it go to allies only? |
| HoP | +1 or more | See Q5. |
| (unknown source) | 1 heart of healing at the end of each round, to allies | What gives this? |
| (unknown source) | 2 hearts of damage reduction, to allies | What gives this? |

**Question:** Please correct the table, and add every other item, pin, award or title that gives an always-on bonus to allies.

---

## Q5. What is HoP, and what does it give?

HoP has been counted as a bonus of at least +1, varying from member to member, going only to other HoP members.

**Questions:**
- What does HoP stand for, and is it a guild, a group or an award?
- What does it give (CM? CR?), and does the amount depend on rank or something else?
- Who receives it: only other HoP members, or all allies?

---

## Q6. Does a Guild Thief keep Rat Pack?

**Write-up text:**
- *Rat Pack* (Footpad): "Thieves' Guild Members gain +1 to any Street Work, Burglary, Escape or Combat Rolls for each other Thieves' Guild member present…"
- *Leadership* (Guild Leader, the highest-level Guild Thief present): "When you are present, all Thieves' Guild members gain +2 on their stealth, burglary & streetwork rolls."

**Current assumption:** Yes, they stack. Every member gives Rat Pack whatever their rank, so a Guild Thief gives Rat Pack **and** Leadership. In the bot, joining the Guild of Thieves grants Rat Pack, and adding the *Guild Thief* rank adds Leadership on top.

**Alternative:** Guild Thief replaces Footpad, and a Guild Thief no longer gives Rat Pack.
