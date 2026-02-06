# Tamil Panchangam Astrology Engine

## Overview
This project is a traditional Tamil Panchangam-based astrology system utilizing Drik Ganita calculations and Lahiri Ayanamsa. It focuses on providing accurate birth chart generation and comprehensive monthly predictions with a traditional South Indian square-style chart visualization. The system aims to merge traditional astrological principles with modern technological capabilities, offering users detailed insights into their astrological profiles and future predictions.

## User Preferences
I prefer iterative development with a focus on clear, concise explanations. Please ask before making any major architectural changes or introducing new external dependencies. I also prefer to keep the UI/UX consistent with the defined design system. Do not make changes to the `docs/` folder without explicit instruction.

## System Architecture

### Core Design Principles
The application follows a two-service model:
1.  **Base Chart Service**: Handles immutable birth chart data, computed once per birth.
2.  **Prediction Service**: Generates temporal predictions based on stored base chart data.

### Technology Stack
-   **Frontend**: React, TypeScript, Vite, TailwindCSS, shadcn/ui.
-   **Backend**: Express.js (Node.js) for API routing and in-memory storage.
-   **Astrology Engine**: FastAPI (Python) for astrological calculations, utilizing Swiss Ephemeris stubs.

### Key Features
-   **Calculation Method**: Drik Ganita for modern astronomical accuracy and Lahiri Ayanamsa as the standard.
-   **Chart Visualization**: Traditional South Indian square-style charts.
-   **AI Interpretation Engine**: Provides astrological interpretations with configurable explainability modes (minimal, standard, full) and strict JSON Schema validation. Supports v1, v2, and v3 engine versions.
-   **LLM Interpretation Layer (v3.0 Siddhar-Tradition Synthesizer)**: Produces deeply personalized predictions incorporating Dasha-Transit synthesis (interplay, not separate lists), Drishti (aspect) specificity with house names, deity-specific Pariharam remedies mapped to afflicted planets, lifecycle tone based on birth year (formative/emerging/established/senior), and per-life-area planetary focus variation (Career→Saturn/D10, Finance→Jupiter/D2, Health→Lagnadipathi/6th house, Personal Growth→Rahu-Ketu).
-   **Canonical PDF Report Builder**: Generates comprehensive 8-section PDF reports from stored data, ensuring no recalculation of astrology. Supports v3 sections: Guiding Theme, Dasha-Transit Synthesis, Mindfulness Windows, Veda Pariharam, Key Takeaways.

### Interpretation Engine Versions
-   **v1.0**: Legacy window_summary + life_areas with attribution.
-   **v2.0**: monthly_theme, overview, practices_and_reflection, closing + life_areas with opportunity/watch_out/one_action.
-   **v3.0**: yearly_mantra, dasha_transit_synthesis, life_areas (simplified), danger_windows, veda_remedy (primary_remedy, supporting_practice, specific_remedies), closing. Both UI and PDF render identical v3 content.

### Design System
-   **Typography**: Playfair Display (serif) for headers, Inter (sans-serif) for body/UI, and JetBrains Mono (monospace) for data/charts.
-   **Colors**: A warm amber primary color with semantic status colors for system health. Full dark mode support is implemented.

## External Dependencies
-   **Swiss Ephemeris**: Used by the Python FastAPI engine for astrological calculations.
-   **OpenAI GPT-4o-mini**: Integrated for the LLM interpretation layer, utilizing `urllib` for API calls.
-   **ReportLab Platypus**: Used for generating structured PDF reports.
-   **DuckDB**: Utilized for persistence of LLM interpretations, usage logs, and configuration, as well as for loading charts at startup.