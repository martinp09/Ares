# Mission Control Style System Design

## Scope
Define the visual system for Mission Control in Ares. This is the UI polish layer only: colors, typography, texture, spacing, component styling, and interaction states. No backend wiring, no Supabase/database work, and no live provider integration.

## Goal
Make Mission Control feel like a dense operator cockpit with atmosphere:
- dark, technical, and serious
- pixel/CRT flavor without looking like a video game
- consistent across every screen
- readable at a glance under pressure

## Non-Goals
- No white/light surfaces
- No neon overload
- No sci-fi poster art
- No arcade/game HUD styling
- No glassmorphism-heavy UI
- No animated gimmicks that hurt readability
- No database or provider wiring

## Design Principles
1. Dark first, always.
2. Amber is the primary signal color.
3. Cyan is a secondary utility color only.
4. Texture is atmosphere, not decoration.
5. Hard edges beat soft mush.
6. Functional hierarchy comes before flair.
7. If a visual effect slows comprehension, kill it.

## Color System
Use layered black and charcoal surfaces with amber authority and rare cyan support.

### Core Tokens
- Background: #050505
- Surface 1: #0E0E0E
- Surface 2: #111111
- Surface 3: #171717
- Surface 4: #1F1F1F
- Border subtle: rgba(255, 255, 255, 0.06)
- Border warm: rgba(255, 140, 0, 0.22)
- Primary amber: #FF8C00
- Primary amber soft: #FFB77D
- Cyan utility: #85CFFF
- Cyan deep: #00B5FC
- Text primary: #E5E2E1
- Text secondary: #B7B5B4
- Text muted: #7C7A79
- Success: #4FE0A3
- Warning: #FFB454
- Error: #FF6F6F

### Usage Rules
- Amber is the main action, active, and focus color.
- Cyan is reserved for read-only status, technical metadata, and low-frequency highlights.
- Red is only for failures and destructive actions.
- Never use saturated rainbow accents.
- Never use white backgrounds or high-chroma fills that break the dark system.

## Typography
Use a two-font system so it feels technical without becoming cosplay.

### Font Pairing
- Headings: Space Grotesk
- UI labels, metadata, numbers, and table text: JetBrains Mono
- Optional fallback: Space Mono

### Rules
- Use mono for dense operational content, tags, statuses, and counts.
- Use Space Grotesk for larger screen titles and section headers only when it improves readability.
- Uppercase labels are allowed for system-style headings and nav items.
- Body copy should stay normal case and readable, not all-caps spam.
- Avoid playful or cartoonish type.

### Type Scale
- Page title: 40–56px
- Section title: 20–28px
- Card title: 16–20px
- Body: 14–16px
- Labels/meta: 11–12px

## Texture and Effects
Texture should whisper, not scream.

### Allowed Effects
- Low-opacity CRT scanlines
- Very subtle dither/noise
- Minimal text glow on active or important labels
- Hard-edged shadows or 1px/2px border accents
- Occasional stepped border language on emphasis blocks

### Forbidden Effects
- Heavy bloom
- Big neon glows
- Animated glitch everywhere
- Flicker that hurts legibility
- Blur-heavy glass panels
- Rounded soft-shadow SaaS mush
- Retro noise so strong it looks broken

### Texture Rules
- Scanlines: 3%–8% opacity max
- Dither: subtle and uniform, not patterned wallpaper
- Glow: only on primary active elements, not body text
- Shadows: short, crisp, and dark

## Layout System
The layout should feel dense and operational.

### Structure
- Left rail for primary navigation
- Top bar for global state and search
- Main workspace for the active screen
- Right rail for context, next action, and risk/status

### Spacing
- Use a tight but breathable rhythm: 8 / 12 / 16 / 24 / 32
- Section spacing should be obvious
- Cards should not float with giant margins
- Keep the cockpit compact and information-rich

### Density
- High information density is fine
- Clutter is not
- Every screen needs one clear primary action
- Secondary actions must visually recede

## Component Styling

### Navigation
- Dark rail background
- Active item should use amber fill or amber border
- Inactive items stay muted gray with hover lift only
- Badges should be small, amber, and functional
- Avoid icon-only navigation

### Buttons
Primary:
- amber fill
- dark text
- squared or minimally rounded
- crisp hover and active states

Secondary:
- dark surface
- amber border or text
- never competing with the primary action

Danger:
- red accent
- separated from normal actions

### Cards and Panels
- Dark surfaces with visible boundaries
- 1px or 2px borders preferred
- Slightly elevated via shadow, not blur
- Optional stepped or double-line accents for key panels
- Keep corners square or nearly square

### Tables and Lists
- Use zebra-like contrast only if needed, but stay dark
- Headers in muted uppercase mono
- Numbers aligned with tabular rhythm
- Status pills should be compact and color-coded
- Dense tables are acceptable if readable

### Metrics Blocks
- Big number, small label, small supporting detail
- Use amber for key counts
- Cyan only for secondary technical stats
- Avoid fake dashboard noise with random numbers

### Context Rail
- Show next action first
- Then risk / blockers
- Then recent activity / notes
- This rail should help the operator decide, not just decorate space

## Interaction States
- Hover: slightly brighter border or surface, no layout shift
- Active: amber fill or stronger border
- Focus: visible ring or outline, always present for keyboard use
- Disabled: dimmed and clearly inert
- Loading: subtle skeleton or status text, not blank space
- Error: red text/badge plus actionable recovery text

## Motion Rules
- Keep transitions fast: 150–220ms
- Motion should explain state change, not entertain
- Avoid bouncing, swirling, or game-like animation
- Respect reduced-motion settings
- If motion is not helping comprehension, remove it

## Accessibility Rules
- Maintain strong contrast on all dark surfaces
- No color-only meaning for status
- Interactive elements must be large enough to hit easily
- Keyboard focus must remain visible
- Empty states must explain what the user can do next
- Do not hide important status in tiny gray text

## Screen-Specific Application
### Intake / Happy Path Screen
- Make the submission → appointment → confirmation SMS → reminder SMS flow the hero
- Keep the checkpoints visible in sequence
- Show one primary action and one secondary action max
- Make failures and blocked steps obvious

### Dashboard
- Use the dashboard to show system posture, not marketing fluff
- Keep counts, statuses, and critical signals obvious

### Inbox
- Maintain a three-pane or two-pane operator feel if the width allows it
- Thread content should stay readable and not collapse into noise

### Settings / Assets
- Keep this area intentionally lower-energy
- Connect-later state should be visible but subdued
- No fake setup wizard energy

## What to Avoid
- White cards on black backgrounds
- Overusing orange until everything screams
- Blue/orange/purple rainbow soup
- Big animated headlines
- Meme cyberpunk visuals
- Game HUD meters with no operational value
- Rounded pastel SaaS visuals
- Overly futuristic typography that hurts trust

## Acceptance Criteria
- All Mission Control screens use the same dark terminal-like visual language
- The UI reads as a serious command center, not a game menu
- Amber and cyan are used consistently and sparingly
- Texture adds atmosphere without hurting legibility
- No white background surfaces remain in Mission Control
- The system feels polished, cohesive, and Hermes-native
