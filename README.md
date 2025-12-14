# Hieroglyphic Pattern Analyzer

**Computational reconstruction of reading order and pattern detection in Ancient Egyptian manuscripts**

An interdisciplinary project analyzing recurring sequences and patterns in Egyptian hieroglyphs from the Book of the Dead of Nu (British Museum EA 10477, Spell 145).

---

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Data Flow](#data-flow)
- [Database Schema](#database-schema)
- [Installation](#installation)
- [Usage](#usage)
- [Core Components](#core-components)
- [API Reference](#api-reference)
- [Development](#development)
- [Acknowledgements](#acknowledgements)

---

## Overview

### Research Question

*How can computational methods reconstruct the reading order and identify recurring hieroglyphic sequences in annotated Spell 145 of the Book of the Dead of Nu using spatial and categorical information derived from CVAT-generated JSON data?*

### What This Tool Does

1. **Reconstructs reading order** from 2D hieroglyphic annotations using spatial coordinates
2. **Detects recurring patterns** in hieroglyphic sequences using n-gram analysis and suffix trees
3. **Visualizes results** on the original papyrus images through an interactive web interface

### Dataset

- **Source**: Book of the Dead of Nu (BM EA 10477, 18th Dynasty, c. 1550-1295 BCE)
- **Focus**: Spell 145, Sheet 25 (traversing the portals of the Field of Reeds)
- **Content**: 2,432 manually annotated hieroglyphs across 59 vertical columns
- **Format**: COCO-style JSON from CVAT annotation tool
- **Size**: ~2.2 MB (annotations.json: 2.1 MB, analysis outputs: ~140 KB)
- **Accessibility**: Data stored in PostgreSQL database and local `data/` directory. Original papyrus images from British Museum (public domain).

---

## System Architecture

```mermaid
graph TB
    subgraph Browser["USER INTERFACE"]
        HomePage[Home Page]
        UploadPage[Upload Page]
        ViewPage[View/Sort Pages]
    end
    
    Browser <-->|WebSocket| FlaskServer
    
    subgraph FlaskServer["FLASK WEB SERVER"]
        subgraph AppLayer["Application Layer"]
            Routes[Routes]
            Services[Services]
        end
        
        subgraph ProcessLayer["Processing Layer"]
            Sort[sort.py<br/>Reading Order]
            NGram[ngram.py<br/>Pattern Detection]
            ProcessImg[process_image.py<br/>JSON Parser]
            Suffix[suffixtree.py<br/>Advanced Patterns]
            Visualize[visualize_columns.py]
        end
        
        subgraph DBLayer["Database Layer"]
            Connect[connect.py]
            Select[select.py]
            Insert[insert.py]
            Update[update.py]
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
        
        Images -->|contains| GlyphesRaw
        Images -->|has status| Status
        Gardiner -->|classifies| GlyphesRaw
        GlyphesRaw -->|sorted into| GlyphesSorted
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
        SortX[Sort by X]
        GroupCol[Group columns]
        SortY[Sort by Y]
        InsertSort[Insert T_GLYPHES_SORTED]
        Linear[Linear sequence]
        
        Fetch --> SortX --> GroupCol --> SortY --> InsertSort --> Linear
    end
    
    Stage3 --> Stage4
    
    subgraph Stage4["4. Pattern Detection"]
        Retrieve[Get sequence]
        NGram[ngram.py<br/>N-Gram Analysis]
        Suffix[suffixtree.py<br/>Suffix Tree]
        Store[Store results]
        
        Retrieve --> NGram --> Store
        Retrieve --> Suffix --> Store
    end
    
    Stage4 --> Stage5
    
    subgraph Stage5["5. Visualization"]
        Display[Web Interface]
    end
    
    Stage5 --> End([Results displayed])
```

---

## Database Schema

```mermaid
erDiagram
    T_IMAGES ||--o{ T_GLYPHES_RAW : contains
    T_IMAGES ||--|| T_IMAGES_STATUS : "has status"
    T_GARDINER_CODES ||--o{ T_GLYPHES_RAW : classifies
    T_GLYPHES_RAW ||--o| T_GLYPHES_SORTED : "sorted into"
    
    T_IMAGES {
        int id PK
        jsonb json
        text title
        bytea img
        text file_name
        text mimetype
        numeric reading_direction
        int id_status FK
    }
    
    T_IMAGES_STATUS {
        int id PK
        text status
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
```

---

## Installation

### Prerequisites

- Python 3.10+
- PostgreSQL 12+
- pip or uv package manager

### Step 1: Clone Repository

```bash
git clone <repository-url> hieroglyphic-pattern-analyzer
cd hieroglyphic-pattern-analyzer
```

### Step 2: Install Dependencies

```bash
# Using pip
pip install -r requirements.txt

# OR using uv (faster)
make uv-env
```

### Step 3: Configure Database

Create `.env` file in `src/database/`:

```env
DB_USER=your_username
DB_PASS=your_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=hieroglyphics_db
```

Test connection:
```bash
python -m src.database.connect
```

### Step 4: Create Database Schema

```sql
-- Create status lookup table
CREATE TABLE T_IMAGES_STATUS (
    id INT PRIMARY KEY,
    status TEXT NOT NULL
);

INSERT INTO T_IMAGES_STATUS (id, status) VALUES
(1, 'pending'),
(2, 'processed'),
(3, 'error');

-- Create main images table
CREATE TABLE T_IMAGES (
    id SERIAL PRIMARY KEY,
    json JSONB,
    title TEXT,
    img BYTEA,
    file_name TEXT,
    mimetype TEXT,
    reading_direction NUMERIC(1,0),
    id_status INT REFERENCES T_IMAGES_STATUS(id)
);

-- Create Gardiner codes reference
CREATE TABLE T_GARDINER_CODES (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    unicode TEXT
);

-- Create raw glyphs table
CREATE TABLE T_GLYPHES_RAW (
    id SERIAL PRIMARY KEY,
    id_original INT,
    id_image INT REFERENCES T_IMAGES(id),
    id_gardiner INT REFERENCES T_GARDINER_CODES(id),
    bbox_x FLOAT,
    bbox_y FLOAT,
    bbox_width FLOAT,
    bbox_height FLOAT
);

-- Create sorted glyphs table
CREATE TABLE T_GLYPHES_SORTED (
    id_glyph INT PRIMARY KEY REFERENCES T_GLYPHES_RAW(id),
    v_column INT NOT NULL,
    v_row INT NOT NULL
);
```

### Step 5: Run Application

```bash
make run
# OR
python -m src.app
```

Access at: **http://localhost:5001**

---

## Usage

### Complete Workflow

```bash
# 1. Start the web application
make run

# 2. Upload papyrus via browser at http://localhost:5001/upload
#    Returns image_id (e.g., 2)

# 3. Extract annotations from JSON
python -m src.process_image 2

# 4. Preview column detection
python -m src.sort 2 100 --preview

# 5. Run sorting algorithm
python -m src.sort 2 100

# 6. Visualize columns (optional)
python -m src.visualize_columns 2

# 7. Detect n-gram patterns
python -m src.ngram

# 8. View results at http://localhost:5001/papyri
```

### Workflow Diagram

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant Flask
    participant Database
    participant CLI
    
    User->>Browser: Navigate to /upload
    User->>Browser: Upload image + JSON
    Browser->>Flask: WebSocket: c2s:upload_papyrus
    Flask->>Database: INSERT INTO T_IMAGES
    Database-->>Flask: Return image_id=2
    Flask-->>Browser: Response {id: 2}
    
    User->>CLI: python -m src.process_image 2
    CLI->>Database: INSERT INTO T_GLYPHES_RAW
    
    User->>CLI: python -m src.sort 2 100
    CLI->>Database: INSERT INTO T_GLYPHES_SORTED
    
    User->>CLI: python -m src.ngram
    CLI-->>User: Save top_4_grams.csv
    
    User->>Browser: Navigate to /papyri
    Flask-->>Browser: Display results
```

---

## Development

### Repository Structure

```
hieroglyphic-pattern-analyzer/
├── data/                   # Sample datasets
│   ├── annotations.json
│   └── *.csv
├── src/
│   ├── app/               # Flask application
│   │   ├── __init__.py
│   │   ├── __main__.py
│   │   ├── routes/
│   │   ├── services/
│   │   ├── templates/
│   │   └── static/
│   ├── database/          # Database layer
│   │   ├── connect.py
│   │   ├── select.py
│   │   ├── insert.py
│   │   └── update.py
│   ├── process_image.py   # Annotation processor
│   ├── sort.py            # Reading order
│   ├── ngram.py           # N-gram analysis
│   ├── suffixtree.py      # Suffix tree (WIP)
│   └── visualize_columns.py
├── requirements.txt
├── Makefile
└── README.md
```

### Roadmap

**Completed**
- [x] Database schema design
- [x] COCO JSON parsing
- [x] Reading order algorithm
- [x] Column visualization
- [x] N-gram analysis
- [x] Flask web server
- [x] WebSocket integration

**In Progress**
- [ ] Suffix tree implementation
- [ ] Pattern visualization on images
- [ ] Frontend dynamic data loading

**Planned**
- [ ] String matching UI
- [ ] Fuzzy matching for scribal variations

---

## Acknowledgements

This project was developed as part of the course "Projektseminar Informatik und Archäologie" at Freie Universität Berlin.

**Supervisors**:  
Prof. Dr. Agnès Voisard  
Prof. Dr. Mara Hubert

**Contributors**:  
Margot Belot (Digital Humanities/DISTANT)  
Eren Kocadag (Computer Science)  
Philipp Schmidt (Computer Science)

**Institution**: Freie Universität Berlin

---

**Version**: 0.1.0-alpha  
**Last Updated**: December 14, 2025
