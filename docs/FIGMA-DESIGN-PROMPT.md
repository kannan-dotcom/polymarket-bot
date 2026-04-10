# Figma Design Prompt - MY Stock Market Trading Platform

**Platform**: Web-based real-time stock trading dashboard for Bursa Malaysia (KLSE)
**Target Users**: Malaysian retail traders and investors analyzing ~129 KLSE-listed stocks
**Viewport**: Desktop-first (1480px max-width), responsive down to 600px mobile
**Design System**: Dark glassmorphism with neon accents

---

## 1. DESIGN SYSTEM

### 1.1 Color Palette

**Background Hierarchy (darkest to lightest):**
| Token | Hex | Usage |
|-------|-----|-------|
| bg-0 | `#0a0e17` | Page background (near-black navy) |
| bg-1 | `#0f1520` | Dropdown backgrounds, secondary surfaces |
| bg-2 | `#151c2b` | Table headers, input field backgrounds |
| bg-3 | `#1e2740` | Score bar tracks, inactive elements |
| bg-4 | `#283352` | Dividers inside components |

**Glass Surfaces:**
| Token | Value | Usage |
|-------|-------|-------|
| glass-bg | `rgba(255,255,255,0.08)` | Card fill |
| glass-bg-hover | `rgba(255,255,255,0.12)` | Card hover state |
| glass-bg-active | `rgba(255,255,255,0.18)` | Pressed/active state |
| glass-border | `rgba(255,255,255,0.12)` | Default border |
| glass-border-hover | `rgba(255,255,255,0.22)` | Hover border |
| glass-blur | `24px` | Backdrop blur for cards |

**Semantic Colors:**
| Token | Hex | Usage |
|-------|-----|-------|
| accent | `#3b82f6` | Primary action, links, TRADE badges, accent glow |
| accent-hover | `#2563eb` | Button hover state |
| green | `#22c55e` | BUY signals, positive P&L, bullish sentiment |
| red | `#ef4444` | SELL signals, negative P&L, bearish sentiment, HIGH risk |
| yellow | `#eab308` | HOLD signals, warnings, model conflicts, MEDIUM risk |
| cyan | `#06b6d4` | Dividend yields, AI labels, informational accents |
| purple | `#a855f7` | Ichimoku cloud, chart patterns, decorative accents |

Each semantic color has a muted variant at ~15% opacity for badge/chip backgrounds:
- `green-muted`: `rgba(34,197,94,0.15)`
- `red-muted`: `rgba(239,68,68,0.15)`
- `yellow-muted`: `rgba(234,179,8,0.15)`
- `cyan-muted`: `rgba(6,182,212,0.15)`
- `purple-muted`: `rgba(168,85,247,0.15)`
- `accent-muted`: `rgba(59,130,246,0.18)`

**Text Hierarchy:**
| Token | Value | Usage |
|-------|-------|-------|
| text-primary | `#ffffff` | Headings, stock names, key values |
| text-secondary | `rgba(255,255,255,0.70)` | Body text, descriptions |
| text-tertiary | `rgba(255,255,255,0.40)` | Labels, captions, inactive text |

**Background Gradients:**
- Page background includes two subtle radial gradients:
  - Top-left: `rgba(59,130,246,0.08)` blue glow at 20% horizontal
  - Bottom-right: `rgba(168,85,247,0.06)` purple glow at 80% horizontal
  - Both fixed to viewport (parallax-like effect)

### 1.2 Typography

**Font Family**: Inter (Google Fonts) with system-ui fallback
**Font Feature Settings**: `"tnum" 1` (tabular/monospaced numbers for data alignment), `"cv01" 1`
**Font Smoothing**: Antialiased (subpixel off for crispness on dark backgrounds)

| Element | Size | Weight | Tracking |
|---------|------|--------|----------|
| Page title (H1) | 13px | 700 | 0.8px |
| Section headers | 11px | 600 | 0.6px, UPPERCASE |
| Sector titles | 12px | 700 | 0.4px |
| Card values (large) | 20px | 700 | - |
| Card values (medium) | 16px | 700 | - |
| Card labels | 10px | 500 | 0.6px, UPPERCASE |
| Table headers | 10px | 600 | 0.5px, UPPERCASE |
| Table body | 12px | 400 | - |
| Badge text | 9px | 600-700 | 0.3-0.5px |
| Caption/sub text | 10px | 400 | - |
| Body text | 13px | 400 | - |

**Special**: The page title uses a 3-stop gradient text fill:
`linear-gradient(135deg, #3b82f6 0%, #06b6d4 50%, #a855f7 100%)`

### 1.3 Spacing Scale

| Token | Value |
|-------|-------|
| sp-1 | 4px |
| sp-2 | 8px |
| sp-3 | 12px |
| sp-4 | 16px |
| sp-5 | 20px |
| sp-6 | 24px |
| sp-8 | 32px |

### 1.4 Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| radius-sm | 8px | Badges, small cards, inputs |
| radius-md | 12px | Main glass cards, tables |
| radius-lg | 16px | Large containers |
| pill | 100px | Toggle buttons, status pills, filter buttons |

### 1.5 Shadows

| Token | Value | Usage |
|-------|-------|-------|
| shadow-sm | `0 1px 3px rgba(0,0,0,0.5)` | Glass card default |
| shadow-md | `0 4px 16px rgba(0,0,0,0.4), 0 1px 4px rgba(0,0,0,0.3)` | Card hover |
| shadow-lg | `0 8px 32px rgba(0,0,0,0.5), 0 2px 10px rgba(0,0,0,0.4)` | Dropdowns, overlays |
| shadow-glow | `0 0 20px rgba(59,130,246,0.2), 0 0 50px rgba(59,130,246,0.08)` | Accent glow |

### 1.6 Glass Card Component

Every card and panel uses this base treatment:
- Fill: `rgba(255,255,255,0.08)`
- Border: 1px `rgba(255,255,255,0.12)`
- Border radius: 12px
- Backdrop-filter: `blur(24px)`
- Box-shadow: shadow-sm + `inset 0 1px 0 rgba(255,255,255,0.06)` (top inner glow)
- Pseudo-element `::before`: 1px-high gradient line at top edge:
  `linear-gradient(90deg, transparent 5%, rgba(255,255,255,0.12) 50%, transparent 95%)`
  This creates a subtle "light reflection" along the top edge
- Hover: border brightens to 0.22 opacity, shadow elevates to shadow-md

---

## 2. PAGE LAYOUT (Top to Bottom)

### 2.1 Sticky Header Bar
- **Position**: Fixed to top, full-width, z-index 100
- **Background**: `rgba(10,14,23,0.90)` with `blur(20px)` - frosted glass effect
- **Bottom border**: 1px glass-border
- **Height**: ~40px
- **Layout**: Flexbox, space-between, vertically centered

**Left**: Gradient text logo "MY STOCK MARKET TRADING PLATFORM" (blue-cyan-purple gradient)

**Center**: Mode toggle - pill-shaped container with two buttons:
  - "DAILY TRADE" / "INVESTMENT"
  - Active state: gradient fill (`#3b82f6` to `#2563eb`), white text, inner glow
  - Inactive: transparent bg, tertiary text color
  - Switching modes changes the main data table columns (daily = technical signals, invest = fundamentals)

**Right**: Status indicators in a row:
  - Status pill: rounded capsule with colored dot (green=live, yellow-pulsing=scanning, red=error) + text
  - Cycle counter: "Cycle **42**"
  - Last scan time: "12s ago"

### 2.2 AI Stock Search Bar
- Full-width glass card below header
- **Internal layout**: Flex row with:
  - "AI" label in accent blue, bold, 14px
  - Text input: dark bg-2 fill, glass border, 13px text, placeholder "Search any KLSE stock... (e.g. Maybank, CIMB, 1155)"
  - Clear button (x): hidden until text entered, tertiary color
  - "Analyze" button: solid accent blue fill, white text, 12px bold, rounded-sm
    - Disabled state: 50% opacity
    - Loading state: small spinner (2px border spinning ring) + "Analyzing..."
    - Hover: lighter blue, translateY(-1px) lift, blue glow shadow

**Search Dropdown** (appears on focus/typing):
  - Absolute positioned below search bar
  - bg-1 background, glass border, large shadow
  - Max height 380px, scrollable
  - Header hint row: "Click a stock or type name and press Enter / Analyze"
  - Each result row shows:
    - Stock key (accent blue, bold, 70px min-width) e.g. "MAYBANK"
    - Full name (white text, flex-grow)
    - Sector (tertiary, small)
    - Price (tertiary, small, monospaced)
    - Score (color-coded: green >= 65, red <= 35, tertiary otherwise)
    - Direction badge (BUY green-muted bg / SELL red-muted bg / HOLD grey bg)
  - Hover/active state: accent-muted background
  - Keyboard navigation: arrow keys highlight rows, Enter selects

### 2.3 AI Analysis Panel
- Glass card, hidden by default, slides open below search bar
- Contains multiple sections divided by glass-border lines:

**Header Section:**
  - Flex row with:
    - Stock name (16px bold) + ticker/sector/price subtitle (11px tertiary)
    - Recommendation badge: large pill-shaped badge (14px bold, 0.8px tracking)
      - BUY: green-muted bg, green text, green 0.3 border
      - SELL: red-muted bg, red text, red 0.3 border
      - HOLD: neutral glass bg, tertiary text
      - TRADE: accent-muted bg, accent text, accent 0.3 border
    - Confidence percentage: large 20px number + "CONFIDENCE" 9px label below
    - Risk level pill: "LOW RISK" / "MEDIUM RISK" / "HIGH RISK"
      - LOW: green-muted, HIGH: red-muted with pulsing glow animation

**Narrative + News Confidence Row:**
  - Side-by-side layout:
    - Left: SVG donut gauge (64x64px) showing news confidence 0-100
      - Circular progress ring with color-coded stroke (green/yellow/red)
      - Number in center, label below
    - Right: AI narrative paragraph, 12px, 1.7 line-height, secondary text color

**Conflict Resolution Row** (conditional):
  - Yellow or green accent bar with warning/check icon + AI explanation text

**Metrics Grid:**
  - Auto-fit grid, min 110px columns
  - Each metric is a mini glass card with:
    - 9px uppercase label (tertiary)
    - 16px bold value (color-coded per metric type)
  - Metrics shown: Signal Score, Fund Score, RSI, Sentiment, Ichimoku, Pattern, P/E, Div Yield, Volatility

**Model Conflicts Section** (conditional):
  - Yellow-tinted background (6% opacity)
  - Warning icon + count header
  - List of conflicts: "Model: issue description" in red (severe) or yellow (warning)

**Price Targets Section:**
  - 3-column grid: Buy Zone / Hold Zone / Sell Zone
    - Each is a small glass card with label, large price, "Strong" sub-price
    - Buy: green 0.3 border, Sell: red 0.3 border, Hold: neutral border
  - Prediction bar below: accent-muted background strip showing:
    - Direction arrow (green up / red down)
    - "Predicted: MYR X.XX (+Y.YY%)"
    - Support/Resistance levels
    - Win probability

**Source Footer:**
  - Right-aligned, 9px tertiary text
  - Shows "Claude Sonnet AI" or "Rule-Based" + cache info + timestamp

### 2.4 Portfolio Summary Cards
- 5-column grid of glass cards
- Each card: label (10px tertiary uppercase) + value (20px bold) + subtitle (10px tertiary)
- Cards:
  1. **Balance**: Dollar amount, color-coded by P&L direction
  2. **Total P&L**: Dollar amount + ROI% subtitle
  3. **Win Rate**: Percentage + trade count subtitle
  4. **Max Drawdown**: Red percentage + open positions subtitle
  5. **KLSE Bursa Malaysia**: Exchange P&L + trade/win rate/stock count subtitle

### 2.5 Sentiment Cards Row (conditional)
- 5-column grid (similar to portfolio cards)
- Cards: Active Sources, Total Mentions, Most Bullish (green value), Most Bearish (red value), AI Analysis (cyan value showing +/- counts)
- Section header: "Forum Sentiment" + "LIVE" accent badge

### 2.6 Trending Stocks Bar
- Horizontal scrollable row of trending chips
- Legend row above: colored dots for Bullish/Bearish/Neutral
- Each chip:
  - Glass background, 8px radius, 180-260px width
  - Stock name (colored by sentiment), stats row (mentions, score, trend arrow)
  - Optional snippet row: 1-line excerpt from forum post with source tag

### 2.7 Fundamentals Overview (Investment mode only)
- 5-column grid of glass cards showing top 5 stocks by fundamental score
- Each card: stock key, score (color-coded), revenue growth, PE, margin

### 2.8 Portfolio Optimization (MVO Section)
- 4-column grid: Expected Return, Portfolio Volatility, Sharpe Ratio, Diversification Ratio
- Below: "Optimal Weights (Top 15)" list - each item is a small glass row with stock key, progress bar, percentage

### 2.9 Quick Filter Bar
- Horizontal row of pill-shaped filter buttons
- Options: All / Buy / Sell / Tradeable
- Active button: gradient blue fill with glow shadow
- Inactive: transparent with glass border

### 2.10 Sector-Grouped Stock Tables
- Stocks grouped by sector (Finance, Technology, Healthcare, Energy, etc.)
- Each sector block has:

**Sector Title Row:**
  - Sector name (12px bold)
  - Count badge: "28 stocks / 12 tradeable" in accent pill
  - Collapse arrow (rotates 90 degrees when collapsed)

**Data Table (Daily Trade mode):**
  | Column | Content |
  |--------|---------|
  | Stock | Name (bold) + ticker (10px tertiary) + EVENT badge if catalyst |
  | Price | Current price, decimal precision adapts to magnitude |
  | Risk | Badge (LOW green / MEDIUM yellow / HIGH red with pulse) + conflict pill count |
  | Targets | Buy target (green) + Sell target (red) + predicted move% with arrow |
  | Score | Number + thin 48px score bar (gradient fill: green/yellow/red) |
  | Signal | BUY/SELL/HOLD badge + optional TRADE badge |
  | Edge | Percentage, green if positive, red if negative |
  | Ichimoku | Score in colored pill + cloud position arrow (up/down) + TK cross indicator |
  | Pattern | Pattern name badge (bullish green / bearish red / neutral grey) + score |
  | Sentiment | Colored dot + score + mention count + optional AI consensus label |
  | RSI | Number, red if >70, green if <30 |
  | Mom | Momentum percentage, color-coded |
  | Vol | Volume (abbreviated K/M/B) + volume ratio "1.5x" |
  | Size | Position size in dollars |

**Data Table (Investment mode):**
  | Column | Content |
  |--------|---------|
  | Stock | Name + ticker + EVENT badge |
  | Price | Current price |
  | Risk | Risk badge |
  | Fund Score | Fundamental score, large bold, color-coded |
  | PE | P/E ratio (green <15, red >30) |
  | Rev Growth | Percentage with +/- color |
  | Margin | Profit margin percentage |
  | ROE | Return on equity |
  | D/E | Debt-to-equity (red >1.5, green <0.5) |
  | Div Yield | Yield% (cyan) + frequency abbreviation (Q/SA/A) |
  | Mkt Cap | Abbreviated (B/T) |
  | Signal | Badge + score |
  | Sentiment | Dot + score |

**Expandable Detail Row (opens on click):**
  - Full-width panel that slides open below the stock row
  - Dark background (bg-1 at 95% opacity)
  - Contains multiple sub-sections:

  **Price Targets Grid**: 3-column (Buy/Hold/Sell zones) with predicted price bar and support/resistance grid (8 stats in auto-fit grid)

  **Fundamentals Grid**: Revenue, Rev Growth, Net Income, Margin, P/E, ROE, D/E, Div Yield, DPS, Payout Ratio, Ex-Div Date, Mkt Cap, EPS, FCF, Fund Score

  **Events Banner** (conditional): Yellow-muted background with event type badges

  **Sub-Scores Grid**: 9 sub-signals displayed in auto-fit columns:
  Momentum, RSI, VWAP, EMA, Volume, Vol-Price (cyan), Ichimoku (purple/green/red), Pattern, Sentiment

  **Model Conflicts Banner** (conditional): Yellow background listing each conflict with severity coloring

  **Ichimoku Cloud Detail**: Tenkan, Kijun, Senkou A/B values + cloud signal + price position + TK cross

  **Chart Patterns Detail** (conditional): Purple-muted background with pattern badges showing name + strength%

  **Sentiment Detail** (conditional): Mentions, Buzz, Trend, AI consensus, LLM breakdown (positive/negative/noise percentages)

  **Technicals Grid**: Confidence, ATR, Volatility, EMA 12/26, SMA 50, VWAP + deviation, OBV trend

  **Signal Reasons**: Accent-muted bar listing all reasons that generated the signal

### 2.11 Model Conflicts Summary Panel
- Glass card with yellow "RISK" section badge
- Header: warning icon + count + "stocks analyzed" + severe count
- Scrollable list (max 300px) of conflict entries:
  - Stock key (accent), direction badge, score, list of model/issue pairs (red for severe, yellow for warning)

### 2.12 Forum Mentions Table
- Standard glass table with columns: Time, Source (cyan), Stock(s), Sentiment (colored label), AI Label (LLM classification with confidence%), Text (truncated 120 chars)

### 2.13 Company Events Table
- Standard glass table with columns: Time, Stock, Event (colored type badge), Impact (bullish/bearish/neutral), Source, Keyword

### 2.14 Recent Trades Table
- Standard glass table with columns: Time, Stock + ticker, Direction (colored "buy"/"sell"), Entry price, Size, Score, Edge%

### 2.15 Footer
- Centered text, 10px tertiary
- "PAPER TRADING MODE - No real money is at risk. Data from Yahoo Finance. Auto-refreshes every 30s."
- Top border 1px glass-border

---

## 3. COMPONENT LIBRARY

### 3.1 Glass Card
- Base component reused everywhere (portfolio cards, metric cards, search bar, analysis panel, table wrappers, filter container, sentiment cards, optimization cards, trending chips)
- States: default, hover (brighter border + elevated shadow), active

### 3.2 Badge System
| Variant | Background | Text | Border | Usage |
|---------|-----------|------|--------|-------|
| buy | green-muted | green | - | BUY signal |
| sell | red-muted | red | - | SELL signal |
| hold | rgba(255,255,255,0.06) | tertiary | - | HOLD signal |
| tradeable | accent-muted | accent | - | Tradeable indicator |
| nodata | rgba(255,255,255,0.04) | tertiary | - | Missing data |
| risk-low | green-muted | green | - | Low risk |
| risk-med | yellow-muted | yellow | - | Medium risk |
| risk-high | red-muted | red | pulsing glow | High risk |
| catalyst-bullish | green-muted | green | green 0.25 | Bullish event |
| catalyst-bearish | red-muted | red | red 0.25 | Bearish event |
| catalyst-neutral | yellow-muted | yellow | yellow 0.25 | Neutral event |
| section-badge | accent-muted | accent | - | Section labels (LIVE, AI, MVO, etc.) |
| conflict-warn | yellow 15% | yellow | - | Warning-level conflict |
| conflict-severe | red-muted | red | - | Severe conflict |

### 3.3 Score Bar
- Thin horizontal bar (48px wide x 4px tall)
- Track: bg-3
- Fill: width = score%, color by threshold (green >= 65, yellow 35-65, red <= 35)
- Rounded 3px

### 3.4 Status Dot
- 6px circle
- States: ok (green + green glow shadow), scanning (yellow + pulsing animation), error (red + red glow shadow)

### 3.5 Mode Toggle
- Pill-shaped container (bg-2 fill, glass border, 100px radius)
- Two button slots
- Active button: gradient fill + white text + glow shadow + pill radius
- Inactive: transparent + tertiary text

### 3.6 Quick Filter Button
- Pill-shaped (100px radius)
- Default: transparent bg, glass border, tertiary text
- Hover: accent border, primary text
- Active: gradient blue fill, accent border, white text, blue glow

### 3.7 Donut Gauge (News Confidence)
- 64x64px SVG
- Background ring: rgba(255,255,255,0.08)
- Progress ring: color-coded (green >= 70, yellow 40-70, red < 40)
- Center: bold number
- Below: label text

### 3.8 Recommendation Badge (Large)
- 14px bold text, 0.8px letter-spacing
- Padding: 6px 16px
- Rounded: radius-sm (8px)
- 4 color variants matching signal colors + 1px matching border

### 3.9 AI Metric Card
- Small centered glass card within grid
- Upper: 9px uppercase tertiary label
- Lower: 16px bold color-coded value
- Padding: 6px, glass-bg fill, glass border, radius-sm

### 3.10 Price Target Box
- Part of 3-column grid
- Glass background, glass border
- Color-coded left border (Buy: green 0.3, Sell: red 0.3, Hold: neutral)
- Label (9px uppercase), Price (14px bold), Sub-price (9px tertiary)

### 3.11 Trending Chip
- Glass card, 8px radius
- 180-260px width, flex-shrink: 0 (horizontal scroll)
- Name row + stats row (mentions, score, trend arrow) + optional snippet

### 3.12 Optimization Weight Bar
- Small glass row item
- Stock key (bold), flex progress bar (6px tall, accent fill), percentage (accent bold)

### 3.13 Ichimoku Indicator
- Small colored pill (bullish=green-muted, bearish=red-muted, neutral=grey)
- Score number inside
- Cloud position arrow beside (green up, red down)
- Optional TK cross indicator below (tiny "TK up/down" text)

### 3.14 Pattern Badge
- Small pill with pattern name
- Color variants: bullish (green), bearish (red), neutral (grey)
- Score number beside/below

---

## 4. INTERACTION PATTERNS

### 4.1 Search Flow
1. User focuses search input - dropdown appears showing top 15 stocks
2. User types - fuzzy matches filter in real-time on key, name, ticker, sector
3. Keyboard: Arrow Down/Up navigate, Enter selects, Escape closes
4. Click or Enter on a stock: input fills with "KEY - Name", dropdown closes, analysis auto-triggers
5. Analyze button lights up (full opacity) when a stock is selected
6. Loading state: button shows spinner + "Analyzing...", panel shows centered spinner
7. Results render in analysis panel below search

### 4.2 Mode Toggle
- Clicking "DAILY TRADE" or "INVESTMENT" switches active button with smooth transition
- Main stock tables re-render with different column sets
- Fundamentals overview cards show/hide based on mode

### 4.3 Sector Collapse
- Click sector title to toggle collapse
- Arrow rotates 90 degrees when collapsed
- Smooth display toggle

### 4.4 Row Expansion
- Click any stock row to expand detail panel below it
- Only one row expanded at a time (previous closes when new opens)
- Detail panel has dark bg to visually separate from table

### 4.5 Signal Filtering
- Quick filter buttons filter all sector tables simultaneously
- Active filter shows gradient button
- Options: All, Buy, Sell, Tradeable

### 4.6 Auto-Refresh
- Dashboard auto-refreshes all data every 30 seconds
- Primary data (scanner, risk, portfolio, exchanges, trades) loads first
- Secondary data (sentiment, trending, forum posts, events, fundamentals, optimization, conflicts) loads in parallel after

---

## 5. RESPONSIVE BREAKPOINTS

### Desktop (> 1100px)
- Full layout as described
- 4-5 column card grids
- Full table column sets

### Tablet (601px - 1100px)
- Portfolio/sentiment cards: 2 columns
- Fundamentals cards: 3 columns
- Tables may need horizontal scroll

### Mobile (< 600px)
- All card grids: single column
- Container padding reduces to sp-2/sp-3
- Header wraps to multiple lines
- Mode toggle buttons shrink (4px 10px padding, 10px font)
- Tables scroll horizontally

---

## 6. ANIMATIONS

| Animation | Duration | Easing | Usage |
|-----------|----------|--------|-------|
| pulse | 1.5s | ease-in-out, infinite | Scanning status dot (opacity 1 to 0.3) |
| riskPulse | 2s | ease-in-out, infinite | HIGH risk badges (red glow shadow pulses) |
| aispin | 0.7-0.8s | linear, infinite | Loading spinners (360deg rotation) |
| Card hover | 0.25s | default | Border-color, box-shadow, background transitions |
| Button hover | 0.2s | default | translateY(-1px) lift + shadow |
| Filter btn | 0.15s | default | Background, border, color transitions |
| Arrow collapse | 0.2s | default | 90deg rotation on sector toggle |

---

## 7. DATA VISUALIZATION CONCEPTS

### 7.1 Score Bar (inline in table)
- Mini 48x4px progress bar showing signal strength 0-100
- 3-color system: red (bearish) / yellow (neutral) / green (bullish)

### 7.2 News Confidence Donut
- SVG ring gauge with percentage fill
- 3-tier color coding: green (high) / yellow (moderate) / red (low)

### 7.3 Optimization Weight Bars
- Horizontal bars showing portfolio allocation percentages
- All in accent blue, tracks in bg-3

### 7.4 Sentiment Dots
- Tiny 6px glowing dots next to scores
- Glow shadow creates a neon indicator effect
- Bullish: green glow, Bearish: red glow, Neutral: no glow

### 7.5 Trend Arrows
- Unicode arrows (up/down/flat) color-coded
- Used in price predictions, mention trends, momentum

---

## 8. KEY DESIGN PRINCIPLES

1. **Information Density**: This is a data-heavy professional trading tool. Every pixel matters. Use small text (9-12px), tight spacing, and compact components to fit maximum information.

2. **Color = Meaning**: Green always means bullish/positive/buy. Red always means bearish/negative/sell. Yellow means caution/neutral/conflict. Blue means accent/action. Purple means technical analysis. Cyan means informational/dividend.

3. **Glass Morphism**: Every container uses the glass treatment (semi-transparent fill + backdrop blur + subtle border + top highlight line). This creates depth without heavy shadows.

4. **Tabular Numbers**: All numerical data uses `font-feature-settings: "tnum" 1` so columns of numbers align perfectly.

5. **Progressive Disclosure**: Overview tables show key metrics. Click to expand for full detail. Search for AI-powered deep analysis.

6. **Dark Theme Only**: The entire interface is dark. No light mode. The dark palette reduces eye strain for traders monitoring screens for extended periods and makes the neon semantic colors pop.

7. **Monospaced-Like Alignment**: Despite using Inter (proportional), tabular number features create the columnar alignment traders expect in financial data.

8. **Status Communication**: The header status system (dot + text + cycle + time) keeps users informed of data freshness without being intrusive.

---

## 9. FIGMA FRAME SUGGESTIONS

Create these frames to capture the full design:

1. **Design System** - Color swatches, typography scale, spacing scale, radius, shadows, glass card anatomy
2. **Component Library** - All badge variants, buttons (states), cards, inputs, dropdowns, gauges, bars
3. **Desktop - Default State** - Full dashboard with portfolio cards, filter bar, 2-3 sector tables with sample data
4. **Desktop - Search Active** - Search input focused with dropdown showing stock results
5. **Desktop - AI Analysis Open** - Analysis panel expanded with BUY recommendation, metrics grid, price targets
6. **Desktop - Row Expanded** - One stock row expanded showing full detail panel with sub-scores, fundamentals, patterns, conflicts
7. **Desktop - Investment Mode** - Mode toggled to Investment showing fundamentals columns and fund cards
8. **Desktop - Full Dashboard** - Scrolled view showing sentiment cards, trending bar, optimization section, conflicts panel, forum posts, events, trade log
9. **Tablet Responsive** - 1100px view with 2-column card grid
10. **Mobile Responsive** - 600px view with single-column layout
11. **States & Micro-interactions** - Button hover/press, card hover, filter active, loading spinner, risk pulse animation, search keyboard navigation
12. **Empty / Loading States** - "Waiting for first scan...", "No trades yet", spinner states
