# DataPiece — Solo Dev Roadmap

## Principles

- **Data before features.** Each sprint ends with real One Piece data entered, not just code written. Working commands with zero data are worthless.
- **Hierarchy first.** You cannot enter appearances without panels. You cannot enter panels without pages. The dependency order is the sprint order.
- **Every table needs two command types:** a `add_*` to write and a `list_*` to read IDs back — because entering data for a child table requires knowing the parent's ID without opening the database manually.
- **One arc as the proving ground.** East Blue (Chapters 1–100) is the target dataset for the entire roadmap. Completing one arc cleanly beats half-entered data across all arcs.

---

## Dependency Order

```
Sagas → Arcs → Volumes → Chapters
                              ↓
             Locations → Pages → Panels
                                    ↓
DevilFruits ──→ Characters ──→ CharacterAppearances
Affiliations ──→ AffiliationHistory
Abilities

                 Characters ──→ FamilyRelationships
                            ──→ CrewmateRelationships
                            ──→ RomanticRelationships

              Characters + Chapters ──→ BountyEvents
                                    ──→ StatusEvents
              Characters + DevilFruits + Chapters ──→ FruitAcquisitions

                        Panels ──→ CharacterInteractions
                                       ↓
                        Characters ──→ InteractionCharacters
```

---

## Sprint 0 — Foundation `[DONE]`

- [x] Schema finalized (22 tables, all constraints, all FKs)
- [x] Infrastructure working (`DBQueryHandler`, `Console`, `Commands` registry)
- [x] All bugs fixed (SQL injection, empty input crash, command discovery, etc.)
- [x] 33 tests passing (unit + integration)
- [x] CI/CD pipeline in place

> **Before entering real data:** change `config/config.json` mode from `"test"` to `"production"` — test mode deletes the database on every restart.

---

## Sprint 1 — Structural Hierarchy

**Goal:** Navigate the full Saga → Arc → Volume → Chapter tree from the CLI.

### Commands to build

| Command | Signature | Table |
|---|---|---|
| `add_saga` | `add_saga <name> <order>` | `Sagas` |
| `list_sagas` | `list_sagas` | `Sagas` |
| `add_arc` | `add_arc <saga_id> <name> <order>` | `Arcs` |
| `list_arcs` | `list_arcs [saga_id]` | `Arcs` |
| `add_volume` | `add_volume <number> [release_date]` | `Volumes` |
| `list_volumes` | `list_volumes` | `Volumes` |
| `add_chapter` | `add_chapter <number> <volume> <arc_id> [name] [pub_date] [page_count]` | `Chapters` |
| `list_chapters` | `list_chapters <arc_id>` | `Chapters` |

### Data deliverable
East Blue Saga entered. All 5 arcs (Romance Dawn, Orange Town, Syrup Village, Baratie, Arlong Park). Volumes 1–12. Chapters 1–100 with names and publication dates.

### Exit criterion
`list_chapters 5` (Arlong Park arc) returns all its chapters cleanly.

---

## Sprint 2 — Locations, Pages, Panels

**Goal:** Fully describe the physical structure of any chapter down to individual panels.

### Commands to build

| Command | Signature | Table |
|---|---|---|
| `add_location` | `add_location <name>` | `Locations` |
| `list_locations` | `list_locations [search_term]` | `Locations` |
| `add_page` | `add_page <chapter_id> <page_number> [flags...]` | `Pages` |
| `set_page_flag` | `set_page_flag <page_id> <flag> <true\|false>` | `Pages` |
| `list_pages` | `list_pages <chapter_id>` | `Pages` |
| `add_panel` | `add_panel <page_id> <panel_number> <size> [location_id] [is_flashback] [is_imagined]` | `Panels` |
| `list_panels` | `list_panels <page_id>` | `Panels` |

### Notes
- `list_locations` with a search term (e.g. `list_locations Marine`) is essential — you will have 50+ locations and cannot remember their IDs.
- `set_page_flag` exists separately from `add_page` because flags are easier to set after scanning a page than to declare upfront.

### Data deliverable
All pages and panels for Chapters 1–10 fully entered.

### Exit criterion
`list_panels <page_id>` returns accurate panel counts matching the physical manga page.

---

## Sprint 3 — Character Master Data

**Goal:** All characters appearing in East Blue catalogued with static attributes.

### Commands to build

| Command | Signature | Table |
|---|---|---|
| `add_devil_fruit` | `add_devil_fruit <name> <type> [zoan_subtype]` | `DevilFruits` |
| `list_devil_fruits` | `list_devil_fruits` | `DevilFruits` |
| `add_character` | `add_character <name> [nickname] [gender] [race] [height] [is_main]` | `Characters` |
| `list_characters` | `list_characters [search_term]` | `Characters` |
| `set_character_fruit` | `set_character_fruit <character_id> <fruit_id>` | `Characters` |
| `set_character_alive` | `set_character_alive <character_id> <true\|false>` | `Characters` |
| `add_affiliation` | `add_affiliation <name> <type>` | `Affiliations` |
| `list_affiliations` | `list_affiliations [type]` | `Affiliations` |
| `add_ability` | `add_ability <name> <type> [haki_type]` | `Abilities` |
| `list_abilities` | `list_abilities [type]` | `Abilities` |

### Notes
- `list_characters` with search is critical — you will have 200+ characters and need fuzzy lookup by name.
- Enter devil fruits first, then link them via `set_character_fruit`.

### Data deliverable
Full East Blue cast catalogued: Straw Hats, major antagonists (Buggy, Kuro, Don Krieg, Arlong), key supporting cast (Coby, Helmeppo, Garp, Shanks). Devil fruits and abilities linked.

### Exit criterion
`list_characters Straw` returns the crew. `list_devil_fruits` shows Gomu Gomu no Mi linked to Luffy.

---

## Sprint 4 — Appearances + Affiliation History

**Goal:** The core analytical table. This is where the real data lives.

### Commands to build

| Command | Signature | Table |
|---|---|---|
| `add_appearance` | `add_appearance <character_id> <panel_id> [type] [is_speaking] [is_focus]` | `CharacterAppearances` |
| `list_appearances` | `list_appearances <panel_id>` | `CharacterAppearances` |
| `add_affiliation_history` | `add_affiliation_history <character_id> <affiliation_id> <from_chapter_id> [to_chapter_id]` | `AffiliationHistory` |
| `list_affiliation_history` | `list_affiliation_history <character_id>` | `AffiliationHistory` |

### Notes
- `add_appearance` will be the most-used command in the entire project. Consider a short alias like `ap`.
- Start with main characters per panel; add supporting cast in a second pass.

### Data deliverable
All appearances for Chapters 1–10 entered.

### First real query milestone

```sql
SELECT c.Name, COUNT(*) AS Appearances
FROM CharacterAppearances ca
JOIN Characters c  ON ca.CharacterID = c.CharacterID
JOIN Panels p      ON ca.PanelID = p.PanelID
JOIN Pages pg      ON p.PageID = pg.PageID
JOIN Chapters ch   ON pg.ChapterID = ch.ChapterID
WHERE ch.ChapterNumber BETWEEN 1 AND 10
GROUP BY c.CharacterID
ORDER BY Appearances DESC;
```

### Exit criterion
The query above returns meaningful, believable results. If it doesn't, the data entry process has a gap — fix the process, not the query.

---

## Sprint 5 — Relationships

**Goal:** Model the character graph — who is family, who is crew, who is romantically linked.

### Commands to build

| Command | Signature | Table |
|---|---|---|
| `add_family_rel` | `add_family_rel <char1_id> <char2_id> <type> [is_adoptive] [revealed_panel_id]` | `FamilyRelationships` |
| `add_crewmate_rel` | `add_crewmate_rel <char1_id> <char2_id> <affiliation_id> <start_panel_id> [revealed_panel_id]` | `CrewmateRelationships` |
| `add_romantic_rel` | `add_romantic_rel <char1_id> <char2_id> <status> [start_panel_id]` | `RomanticRelationships` |
| `list_relationships` | `list_relationships <character_id>` | all three tables |

### Notes
- `list_relationships` should query all three tables and print a unified summary — essential for QA.
- Crewmate joins are the most analytically rich: the moment each Straw Hat joins is a pivotal narrative anchor. Prioritise these.
- Romantic relationships in East Blue are sparse — don't over-invest here.

### Data deliverable
All crewmate joins in East Blue recorded with exact `StartPanelID`. All known family relationships for the East Blue cast entered. Garp/Dragon/Luffy family tree complete with `IsAdoptive` flags.

### Exit criterion
`list_relationships 1` (Luffy) returns: crewmates (Zoro, Nami, Usopp, Sanji) with join panels, family (Dragon as parent, Garp as grandfather, Ace as adoptive brother).

---

## Sprint 6 — Events

**Goal:** Track the three key character state changes: bounties, life/death status, devil fruit acquisitions.

### Commands to build

| Command | Signature | Table |
|---|---|---|
| `add_bounty` | `add_bounty <character_id> <chapter_id> <amount>` | `BountyEvents` |
| `add_status_event` | `add_status_event <character_id> <chapter_id> <status>` | `StatusEvents` |
| `add_fruit_acquisition` | `add_fruit_acquisition <character_id> <fruit_id> <chapter_id>` | `FruitAcquisitions` |
| `list_bounty_history` | `list_bounty_history <character_id>` | `BountyEvents` |
| `list_status_history` | `list_status_history <character_id>` | `StatusEvents` |

### Notes
- Bounty history is one of the most analytically satisfying datasets. Track the exact chapter of every bounty reveal.
- `add_fruit_acquisition` covers on-panel eating events (Luffy in Chapter 1). The static `Characters.DevilFruitID` covers general knowledge; this table covers *when it happened*.

### Data deliverable
All bounty reveals in East Blue entered. All on-panel fruit acquisitions entered.

### Second real query milestone

```sql
SELECT c.Name, be.Bounty, ch.ChapterNumber
FROM BountyEvents be
JOIN Characters c ON be.CharacterID = c.CharacterID
JOIN Chapters ch  ON be.ChapterID = ch.ChapterID
ORDER BY be.Bounty DESC;
```

### Exit criterion
The bounty timeline query returns correct data in the right order.

---

## Sprint 7 — Interactions

**Goal:** Record the fights, conversations, and alliances that drive the narrative.

### Commands to build

| Command | Signature | Table |
|---|---|---|
| `start_interaction` | `start_interaction <start_panel_id> <type>` | `CharacterInteractions` |
| `end_interaction` | `end_interaction <interaction_id> <end_panel_id> <outcome>` | `CharacterInteractions` |
| `add_participant` | `add_participant <interaction_id> <character_id> <role>` | `InteractionCharacters` |
| `list_interactions` | `list_interactions <chapter_id>` | `CharacterInteractions` |

### Notes
- `start_interaction` / `end_interaction` is intentionally two-step — you know when a fight starts before you know how it ends.
- Focus on fights first (highest analytical value). Conversations second.

### Data deliverable
All major fights in East Blue recorded with correct start/end panels and outcomes: Luffy vs. Buggy, Zoro vs. Mihawk, Luffy vs. Arlong, etc.

### Third real query milestone

```sql
SELECT c.Name,
       COUNT(*) AS Fights,
       SUM(CASE WHEN ic.Role = 'Initiator' THEN 1 ELSE 0 END) AS AsInitiator
FROM InteractionCharacters ic
JOIN Characters c             ON ic.CharacterID = c.CharacterID
JOIN CharacterInteractions ci ON ic.InteractionID = ci.InteractionID
WHERE ci.InteractionType = 'Fight'
GROUP BY c.CharacterID
ORDER BY Fights DESC;
```

### Exit criterion
Query returns fight counts per character with correct initiator/recipient breakdown.

---

## Sprint 8 — Data Quality + Analytics Validation

**Goal:** Ensure the East Blue dataset is internally consistent and actually answers the questions the project was built for. No new commands — pure QA and querying.

### Integrity checks

```sql
-- Panels with no appearances (forgotten entries?)
SELECT p.PanelID FROM Panels p
LEFT JOIN CharacterAppearances ca ON p.PanelID = ca.PanelID
WHERE ca.AppearanceID IS NULL;

-- Main characters with no affiliation recorded
SELECT c.Name FROM Characters c
LEFT JOIN AffiliationHistory ah ON c.CharacterID = ah.CharacterID
WHERE ah.HistoryID IS NULL AND c.IsMainCharacter = TRUE;

-- Characters entered but never linked to any panel
SELECT c.Name FROM Characters c
LEFT JOIN CharacterAppearances ca ON c.CharacterID = ca.CharacterID
WHERE ca.AppearanceID IS NULL;
```

### Analytics to validate

1. Panel appearances per character per arc — screen time analysis
2. Speaking vs. silent appearance ratio per character
3. Focus panels per character — narrative weight
4. Flashback panel percentage per chapter — pacing analysis
5. Location frequency map — where does East Blue take place?
6. Bounty-to-appearance correlation — does more screen time predict higher bounties?

### Deliverable
A written data quality report noting: what data is missing, what looks wrong, which schema fields were harder to fill than expected. This directly feeds the next arc's workflow.

### Exit criterion
All 6 queries return results. At least 4 of them are interesting enough to share.

---

## Sprint 9+ — Arc Expansion

Once East Blue is validated, repeat the sprint cycle for each subsequent arc. All commands are already built — subsequent arcs are pure data entry with occasional schema refinements based on Sprint 8 findings.

**Suggested order:** East Blue → Alabasta → Skypiea → Water 7 / Enies Lobby → Marineford → Fishman Island → Dressrosa → Whole Cake Island → Wano

---

## Summary

| Sprint | Focus | Commands | Data milestone |
|---|---|---|---|
| 0 | Foundation | — | Infrastructure complete |
| 1 | Hierarchy | 8 | 100 chapters + 5 arcs entered |
| 2 | Pages + Panels | 7 | Chapters 1–10 fully mapped |
| 3 | Characters | 10 | Full East Blue cast catalogued |
| 4 | Appearances | 4 | First analytical query working |
| 5 | Relationships | 4 | Crew joins + family tree |
| 6 | Events | 5 | Bounty timeline working |
| 7 | Interactions | 4 | All major fights recorded |
| 8 | Data quality | 0 (QA only) | 6 analytics validated |
| 9+ | Arc expansion | 0 (reuse) | One new arc per cycle |
