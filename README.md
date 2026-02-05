# Hieroglyphic Pattern Analyzer

Computational reconstruction of reading order and pattern detection in Ancient Egyptian manuscripts.

## Table of Contents

- [Hieroglyphic Pattern Analyzer](#hieroglyphic-pattern-analyzer)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
    - [Research Question](#research-question)
    - [What This Tool Does](#what-this-tool-does)
    - [Dataset](#dataset)
  - [System Architecture](#system-architecture)
  - [Data Flow](#data-flow)
  - [Database Schema](#database-schema)
  - [Installation](#installation)
    - [Prerequisites](#prerequisites)
    - [Setup](#setup)
  - [Usage](#usage)
  - [Project Structure](#project-structure)
  - [Acknowledgements](#acknowledgements)

---

## Overview

### Research Question

*How can computational methods reconstruct the reading order and identify recurring hieroglyphic sequences in annotated Spell 145 of the Book of the Dead of Nu using spatial and categorical information derived from CVAT-generated JSON data?*

### What This Tool Does

1. Reconstructs reading order from 2D hieroglyphic annotations using spatial positioning
2. Detects recurring patterns in hieroglyphic sequences using n-gram analysis
3. Visualizes results through an interactive web interface

### Dataset

- **Source**: Book of the Dead of Nu (BM EA 10477, 18th Dynasty)
- **Focus**: Spell 145, Sheet 25
- **Content**: 2,432 manually annotated hieroglyphs across 59 vertical columns
- **Format**: COCO-style JSON from CVAT

---

## System Architecture

```mermaid
graph TB
    subgraph Browser["USER INTERFACE"]
        HomePage[Home Page]
        UploadPage[Upload Page]
        ViewPage[View/Sort Pages]
        PatternPage[Pattern Details]
    end
    
    Browser <-->|WebSocket/API| FlaskServer
    
    subgraph FlaskServer["FLASK WEB SERVER"]
        subgraph AppLayer["Application Layer"]
            SiteRoutes[Site Routes]
            APIRoutes[API Routes]
            WSRoutes[WebSocket Routes]
        end
        
        subgraph ProcessLayer["Processing Layer"]
            Sort[sort.py<br/>Reading Order]
            SuffixArr[suffixarray.py<br/>Pattern Detection]
            ProcessImg[process_image.py<br/>JSON Parser]
            Lookup[sentence_lookup_db.py<br/>TLA Corpus Matching]
            Cleanup[cleanup.py<br/>Data Cleanup]
        end
        
        subgraph DBLayer["Database Layer"]
            Connect[connect.py]
            Handler[handler/]
        end
        
        AppLayer --> ProcessLayer
        ProcessLayer --> DBLayer
    end
    
    DBLayer <--> Database
    
    subgraph Database["PostgreSQL"]
        Images[(T_IMAGES)]
        GlyphesRaw[(T_GLYPHES_RAW)]
        GlyphesSorted[(T_GLYPHES_SORTED)]
        Gardiner[(T_GARDINER_CODES)]
        Status[(T_IMAGES_STATUS)]
        SuffixPattern[(T_SUFFIXARRAY_PATTERNS)]
        SuffixOcc[(T_SUFFIXARRAY_OCCURENCES)]
        Sentences[(T_SENTENCES)]
        
        Images -->|contains| GlyphesRaw
        Images -->|has status| Status
        Gardiner -->|classifies| GlyphesRaw
        GlyphesSorted -->|sorted from| GlyphesRaw
        Images -->|patterns from| SuffixPattern
        SuffixPattern -->|occurrences| SuffixOcc
    end
```

---

## Data Flow

```mermaid
flowchart TD
    Start([User uploads<br/>image + JSON]) --> Stage1
    
    subgraph Stage1["1. Data Input"]
        JSON[COCO JSON Format]
    end
    
    Stage1 --> Stage2
    
    subgraph Stage2["2. Database Storage"]
        Extract[Extract JSON<br/>process_image.py]
        Map[Map Gardiner codes]
        InsertRaw[Insert T_GLYPHES_RAW]
        Extract --> Map --> InsertRaw
    end
    
    Stage2 --> Stage3
    
    subgraph Stage3["3. Reading Order"]
        Fetch[Fetch glyphs<br/>sort.py]
        CalcCenter[Calculate center of gravity]
        SortX[Sort by X center]
        GroupCol[Group columns]
        SortY[Sort by Y center]
        InsertSort[Insert T_GLYPHES_SORTED]
        Linear[Linear sequence]
        
        Fetch --> CalcCenter --> SortX --> GroupCol --> SortY --> InsertSort --> Linear
    end
    
    Stage3 --> Stage4
    
    subgraph Stage4["4. Pattern Detection"]
        Retrieve[Get sequence]
        SuffixArray[suffixarray.py<br/>Suffix Array Analysis]
        StorePattern[Store T_SUFFIXARRAY_PATTERNS]
        
        Retrieve --> SuffixArray --> StorePattern
    end
    
    Stage4 --> Stage5
    
    subgraph Stage5["5. Corpus Matching"]
        LookupSent[sentence_lookup_db.py<br/>Match TLA Corpus]
        Display[Display matches]
        
        StorePattern --> LookupSent --> Display
    end
    
    Stage5 --> End([Results displayed])
```

---

## Database Schema

```mermaid
erDiagram
    T_IMAGES ||--o{ T_GLYPHES_RAW : contains
    T_IMAGES ||--|| T_IMAGES_STATUS : "has status"
    T_IMAGES ||--o{ T_SUFFIXARRAY_PATTERNS : "patterns from"
    T_GARDINER_CODES ||--o{ T_GLYPHES_RAW : classifies
    T_GLYPHES_RAW ||--o| T_GLYPHES_SORTED : "sorted into"
    T_SUFFIXARRAY_PATTERNS ||--o{ T_SUFFIXARRAY_OCCURENCES : "has occurrences"
    T_SUFFIXARRAY_OCCURENCES ||--o{ T_SUFFIXARRAY_OCCURENCES_BBOXES : "has bboxes"
    
    T_IMAGES {
        int id PK
        jsonb json
        text title
        bytea img
        bytea img_preview
        text file_name
        text mimetype
        numeric reading_direction
        int id_status FK
        int sort_tolerance
    }
    
    T_IMAGES_STATUS {
        int id PK
        text status
        text status_code
    }
    
    T_GARDINER_CODES {
        int id PK
        text code
        text unicode
    }
    
    T_GLYPHES_RAW {
        int id PK
        int id_original
        int id_image FK
        int id_gardiner FK
        float bbox_x
        float bbox_y
        float bbox_width
        float bbox_height
    }
    
    T_GLYPHES_SORTED {
        int id_glyph PK
        int v_column
        int v_row
    }
    
    T_SUFFIXARRAY_PATTERNS {
        int id PK
        int id_image FK
        int_array gardiner_ids
        int length
        int count
    }
    
    T_SUFFIXARRAY_OCCURENCES {
        int id PK
        int id_pattern FK
        int_array glyph_ids
    }
    
    T_SUFFIXARRAY_OCCURENCES_BBOXES {
        int id PK
        int id_occ FK
        float bbox_x
        float bbox_y
        float bbox_width
        float bbox_height
    }
    
    T_SENTENCES {
        text id PK
        text mdc_compact
        text transcription
        text translation
        jsonb tokens
        int match_occurrence_count
    }
```

---

## Installation

### Prerequisites
- Python 3.10+
- PostgreSQL 12+

### Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure database (.env file in src/database/)
DB_USER=your_username
DB_PASS=your_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=hieroglyphics_db

# Run application
make run
```

Access at http://localhost:5001

---

## Usage

```bash
# Upload papyrus image + JSON at http://localhost:5001/upload
# Returns image_id (e.g., 2)

# Process annotations
python -m src.process_image 2

# Reconstruct reading order
python -m src.sort 2 100

# Detect patterns
python -m src.suffixarray 2

# View results at http://localhost:5001/papyri
```

---

## Project Structure

```
src/
├── app/                    # Flask web interface (routes, static, templates)
├── database/               # PostgreSQL connection and handlers
├── process_image.py        # COCO JSON parser
├── sort.py                 # Reading order algorithm
├── suffixarray.py          # Suffix array pattern detection
├── sentence_lookup_db.py   # TLA corpus matching
└── cleanup.py              # Data cleanup utilities
```

---

## Acknowledgements

Developed at Freie Universität Berlin as part of "Projektseminar Informatik und Archäologie."

**Contributors**: Margot Belot, Eren Kocadag, Philipp Schmidt  
**Supervisors**: Prof. Dr. Agnès Voisard, Prof. Dr. Mara Hubert
