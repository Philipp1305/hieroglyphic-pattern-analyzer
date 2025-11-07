# HieroglyphicPatternAnalyzer

> An interdisciplinary project for analysing reoccuring sequences and patterns in egyptian hieroglyphs.

## Repository Structure

| Path        | Description                                                                              |
|-------------|------------------------------------------------------------------------------------------|
| `data/`     | Raw datasets and intermediate artefacts used during processing.                          |
| `src/`      | Application code for database access, reading-order utilities, pattern detection, and UI |
| `static/`   | Static assets for the web UI (CSS, JS, fonts, images).                                   |

## Installation

#### 1. Clone git repository.

#### 2. Install all dependencies

```bash
pip install -r requirements.txt
```

#### 3. Setup your database connection

You need a database user to connect to our database. To do this, create an ``.env`` file in the ``src/database`` directory. You will find an ``.env.example`` file there. Copy its structure into your newly created ``.env`` file and replace the variables with the credentials you received.

## Usage

## Acknowledgements
This project was developed as part of the course "Projektseminar Informatik und Archäologie" at the Freie Universität Berlin and was initialized by Prof. Dr. Agnès Voisard and Prof. Dr. Mara Hubert. Contributors are Margot Belot (Digital Humanities), Eren Kocadag (CS), and Philipp Schmidt (CS).