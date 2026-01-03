# Tamil Panchangam Astrology Engine - Design Guidelines

## Design Approach

**Hybrid Approach**: Traditional Vedic aesthetic meets modern data visualization
- Primary inspiration: Blend Notion's clarity for data display + traditional Vedic motifs
- Cultural context: Respectful incorporation of Tamil/South Indian design elements without overwhelming functionality

## Typography

**Font Stack**:
- Headers: 'Playfair Display' (serif, traditional gravitas) - weights 600, 700
- Body/UI: 'Inter' (sans-serif, clean data display) - weights 400, 500, 600
- Data/Charts: 'JetBrains Mono' (monospace for precise astronomical values)

**Hierarchy**:
- H1: text-4xl font-bold (main titles)
- H2: text-2xl font-semibold (section headers)
- H3: text-xl font-medium (subsections)
- Body: text-base (forms, descriptions)
- Data labels: text-sm font-medium tracking-wide uppercase (chart labels, timestamps)

## Layout System

**Spacing Units**: Tailwind primitives of 2, 4, 6, 8, 12, 16
- Component padding: p-6 or p-8
- Section spacing: space-y-8 or space-y-12
- Form field gaps: gap-4 or gap-6
- Container max-width: max-w-7xl

## Core Components

### Navigation
- Sticky top navigation with three primary links: "Generate Chart", "Monthly Predictions", "Reports"
- Right-aligned utility links: "Health Status", "Documentation"
- Clean, minimal header with subtle border-b

### Hero Section
**NO traditional hero image** - Instead, use an abstract, geometric representation of a South Indian chart as SVG background pattern with low opacity

Content:
- Centered layout with max-w-3xl
- H1: "Tamil Panchangam Astrology Engine"
- Subheading explaining Drik Ganita and Lahiri Ayanamsa
- Two prominent CTA buttons: "Create Birth Chart" and "View Sample Prediction"
- Small trust indicator: "Traditional Vedic calculations with astronomical precision"

### Form Components (Birth Chart Input)

**Multi-step form layout**:
1. Personal Details (Name, Date of Birth)
2. Time & Location (Time picker, Location autocomplete with timezone)
3. Calculation Preferences (optional advanced settings)

Form styling:
- Labels: text-sm font-medium above inputs
- Inputs: Clean borders, focus:ring-2, rounded-lg, p-3
- Date/Time pickers: Custom styled with clear visual hierarchy
- Location input: Autocomplete with dropdown suggestions
- Submit button: Large, prominent, w-full on mobile

### Chart Visualization Area

**South Indian Square Chart Display**:
- Fixed aspect ratio container (square)
- SVG-rendered traditional 12-house grid
- House numbers in corners (Tamil numerals optional enhancement)
- Planet symbols with degrees precisely positioned
- Legend sidebar explaining planetary positions
- Tabbed interface for D1 (Rasi) and D9 (Navamsa) charts

### Data Tables

**Planetary Positions Table**:
- Striped rows for readability
- Columns: Planet | Sign | Degree | Nakshatra | Pada | Lord
- Monospace font for numerical values
- Responsive: Horizontal scroll on mobile

**Dasha Timeline**:
- Visual timeline component with nested periods
- Color-coded dasha levels (Maha > Antar > Pratyantar)
- Date ranges clearly displayed
- Current dasha highlighted

### Prediction Display

**Monthly Prediction Layout**:
- Calendar grid showing daily Pancha Pakshi
- Expandable day cards with transit details
- Side panel showing significant transits for the month
- Download PDF button prominently placed

### Report Builder Interface

- Preview pane (left 60%) showing live PDF preview
- Controls pane (right 40%) with customization options
- Toggle switches for sections to include
- Export format selector (PDF/Print)

## Layout Patterns

**Dashboard View** (after chart generation):
- Top: Chart summary card with key details
- Middle: Tabbed content (Chart | Positions | Dashas | Predictions)
- Sidebar: Quick actions and saved charts list

**Two-column layouts** where appropriate:
- Chart input form (left) + Preview/Instructions (right)
- Chart visualization (left) + Interpretations (right)

## Animations

Use sparingly:
- Form step transitions: Slide fade
- Chart rendering: Gentle fade-in after calculation
- Loading states: Subtle spinner for calculations

## Images

**Background textures only**:
- Subtle mandala pattern watermark at very low opacity (5-10%) on chart pages
- Abstract geometric patterns inspired by kolam designs in footers
- NO photographic images - this is a data-focused application

**No large hero image** - the focus is on functionality and precision

## Accessibility

- ARIA labels on all form inputs
- Keyboard navigation for chart generation flow
- High contrast mode for chart visualizations
- Screen reader descriptions for chart house positions

## Special Considerations

**Cultural Authenticity**:
- Optional Tamil language labels for advanced users
- Respect for traditional chart orientation (South at top for South Indian style)
- Precise astronomical terminology with tooltips

**Data Integrity Indicators**:
- Timestamp display for all calculations
- Ayanamsa value clearly shown
- Calculation method badge ("Drik Ganita • Lahiri")

**Status & Health**:
- Service health indicator in footer (green dot + "All systems operational")
- Last calculation timestamp
- Ephemeris data version display

This design balances cultural authenticity with modern usability, ensuring complex astrological data remains accessible while honoring traditional presentation methods.