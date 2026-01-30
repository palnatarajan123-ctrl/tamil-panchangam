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
-   **AI Interpretation Engine**: Provides astrological interpretations with configurable explainability modes (minimal, standard, full) and strict JSON Schema validation.
-   **LLM Interpretation Layer**: Enhances predictions with language-based narratives using OpenAI GPT-4o-mini, focusing on fail-fast deterministic fallback, a cache-first strategy, and token budget enforcement.
-   **Canonical PDF Report Builder**: Generates comprehensive 8-section PDF reports from stored data, ensuring no recalculation of astrology.

### Design System
-   **Typography**: Playfair Display (serif) for headers, Inter (sans-serif) for body/UI, and JetBrains Mono (monospace) for data/charts.
-   **Colors**: A warm amber primary color with semantic status colors for system health. Full dark mode support is implemented.

## External Dependencies
-   **Swiss Ephemeris**: Used by the Python FastAPI engine for astrological calculations.
-   **OpenAI GPT-4o-mini**: Integrated for the LLM interpretation layer, utilizing `urllib` for API calls.
-   **ReportLab Platypus**: Used for generating structured PDF reports.
-   **DuckDB**: Utilized for persistence of LLM interpretations, usage logs, and configuration, as well as for loading charts at startup.