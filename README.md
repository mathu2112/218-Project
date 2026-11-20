# Humanitarian Air Bridge

## Project Overview

Humanitarian Air Bridge is an AI-based humanitarian logistics simulation developed for the CSCI218 Foundations of Artificial Intelligence group project at the University of Wollongong in Dubai.

The simulation allows users to act as humanitarian logistics coordinators and allocate limited resources to emergency-affected locations.

The system uses fuzzy logic to generate AI-based resource allocation recommendations. Users can compare their decisions with the AI's recommendations and review the results.

## Main Features

- Interactive humanitarian logistics simulation
- Emergency requests with different urgency levels
- Allocation of medicine, shelter, and nutrition supplies
- Limited supply hub stock and transport capacity
- AI recommendations using fuzzy logic
- Human versus AI allocation comparison
- Visual results and allocation analysis
- Restart simulation functionality

## Technologies Used

- Python
- FastAPI
- Uvicorn
- Pandas
- HTML
- CSS
- JavaScript
- CSV datasets
- Git and GitHub


## Installation Instructions

### 1. Download the Project

Clone the GitHub repository:

```bash
git clone <REPOSITORY_URL>
```

Alternatively, download the repository as a ZIP file from GitHub and extract it.

Open the project folder in VS Code or a terminal.

### 2. Install Python

Install Python 3.14 or a compatible Python version.

Check that Python is installed:

```bash
python --version
```

### 3. Install Dependencies

Open a terminal in the main project directory and run:

```bash
python -m pip install -r requirements.txt
```

This installs the required Python packages.

### 4. Start the Application

From the main project directory, run:

```bash
python -m uvicorn web_server:app --reload --port 8001
```

Keep the terminal running while using the simulation.

### 5. Open the Website

Open Google Chrome or another modern browser.

Enter the following address:

http://127.0.0.1:8001/home.html

The Humanitarian Air Bridge homepage will appear.

**Note:** The Python server must be running for the simulation to work correctly. Opening the HTML file directly without the server will not enable the backend functionality.

## How to Play

1. Open the Humanitarian Air Bridge homepage.
2. Click **Play Simulation**.
3. Review the available emergency requests.
4. Select an emergency request.
5. Examine the available supply hub resources and transport capacity.
6. Choose how much medicine, shelter, and nutrition to allocate.
7. Review the fuzzy-logic AI recommendation.
8. Confirm the allocation.
9. Open the Results page to compare the human allocation with the AI recommendation.
10. Return to the homepage and select **Restart Simulation** to clear previous allocations and begin again.

## AI Technique: Fuzzy Logic

The system uses fuzzy logic to support humanitarian resource allocation decisions.

The AI evaluates emergency-related factors to generate a priority score and suggest resource allocations.

These recommendations help users make informed decisions when resources and transport capacity are limited.

The AI acts as a decision-support component. The user remains responsible for confirming allocations.

## Evaluation

The project includes evaluation modules for comparing allocation approaches and analysing simulation performance.

The evaluation code is located in:

```text
backend/evaluation/
```

## Limitations

- The simulation uses predefined CSV datasets.
- Resource availability and emergency scenarios are simulated rather than obtained from live humanitarian systems.
- Simulation progress is maintained by the running backend and may be lost when the server restarts.
- The current implementation is designed primarily for local demonstration and educational use.

## Team Contributions

Individual team contributions are recorded in the GitHub repository's commit history and documented in the project report.
