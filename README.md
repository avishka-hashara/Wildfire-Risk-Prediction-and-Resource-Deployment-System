# Wildfire Risk Prediction & Resource Deployment System

An intelligent AI-powered system designed to predict wildfire risks and optimize resource deployment and routing for emergency response teams.

## Overview

This project consists of two main components:
1. **Backend Engine**: A robust FastAPI backend combining Deep Learning (PyTorch), Fuzzy Logic (`skfuzzy`), and Graph Theory (`networkx`).
2. **Frontend Dashboard**: A responsive modern web dashboard built with React, Vite, and Tailwind CSS.

### Key Features
- **Machine Learning Prediction**: Utilizes a trained PyTorch neural network to predict the probability of a wildfire based on meteorological and environmental parameters.
- **Fuzzy Logic Expert System**: Evaluates the neural network's probability output alongside wind speed to calculate a human-readable, actionable `risk_level` (Safe, Watch, Alert, Evacuate).
- **Logistics & Routing**: Uses graph algorithms (NetworkX) to determine the fastest deployment route for emergency vehicles from fire stations to the risk zone.
- **Interactive Dashboard**: Provides a seamless user interface for operators to input environmental data and receive instant risk assessments and routing instructions.

## Project Structure

```
Wildfire_AI_Project/
├── 1_Data_Exploration.ipynb               # Jupyter notebook for initial data analysis and modeling
├── Algerian_forest_fires_dataset_*.csv    # Datasets used for training the model
├── app.py                                 # Main FastAPI backend application
├── wildfire_production_model.pth          # Pre-trained PyTorch neural network weights
├── wildfire_scaler.pkl                    # Scikit-learn scaler for data normalization
├── venv/                                  # Python virtual environment (if created locally)
└── wildfire-dashboard/                    # Frontend React/Vite application
    ├── src/                               # React components and styling
    ├── package.json                       # Node.js dependencies
    └── ...
```

## Setup Instructions

### Prerequisites
- Python 3.8+
- Node.js (for the frontend)

### 1. Backend Setup

Navigate to the project root and create a virtual environment:
```bash
python -m venv venv
```

Activate the virtual environment:
- **Windows**: `venv\Scripts\activate`
- **macOS/Linux**: `source venv/bin/activate`

Install the required Python dependencies:
```bash
pip install fastapi uvicorn torch networkx scikit-learn scikit-fuzzy joblib pandas numpy
```

Run the FastAPI server:
```bash
python app.py
```
*The backend will run on `http://127.0.0.1:8000` (or `http://localhost:8000`).*

### 2. Frontend Setup

Open a new terminal, navigate to the dashboard directory:
```bash
cd wildfire-dashboard
```

Install the Node.js dependencies:
```bash
npm install
```

Start the Vite development server:
```bash
npm run dev
```
*The frontend dashboard will be accessible via the local URL provided by Vite (usually `http://localhost:5173`).*

## API Endpoints

- `POST /predict_risk`: Accepts environmental data (Temperature, RH, Ws, Rain, FFMC, DMC, DC, ISI, BUI, FWI), scales it, passes it through the PyTorch model, evaluates risk via Fuzzy Logic, and calculates the optimal route. Returns a comprehensive JSON response with prediction, risk level, and routing information.

## Technologies Used
- **Backend**: Python, FastAPI, Uvicorn
- **AI / ML**: PyTorch, Scikit-learn, Scikit-Fuzzy (Fuzzy Logic Expert System)
- **Algorithms**: NetworkX (Dijkstra's Algorithm / Graph Routing)
- **Frontend**: React, Vite, Tailwind CSS, Axios
- **Data**: Based on the Algerian Forest Fires Dataset
