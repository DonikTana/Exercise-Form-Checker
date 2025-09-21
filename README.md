# 🏋️‍♂️ AI-Based Exercise Tracker Web App

This project is a **real-time AI-powered fitness tracking web application** built with **Flask, Mediapipe, OpenCV, and SQLite**.  
It allows users to **track exercises via webcam, count repetitions automatically, calculate calories burned, and visualize progress** with charts.

---

## ✨ Features
- 🔐 **User Authentication** – Register & Login with password hashing  
- 🎥 **Real-Time Pose Detection** – Tracks body landmarks using Mediapipe  
- 🔄 **Exercise Tracking** – Supports **Bicep Curls** and **Sit-ups** with automatic rep counting  
- 🔥 **Calories Burned Calculation** – Estimates calories per exercise  
- 📊 **Progress Charts** – View calories burned per day & exercise counts over time  
- 🗄️ **Database Integration** – Logs stored using **SQLite + SQLAlchemy**  
- 📂 **Dashboard** – View recent activity logs  

---

## 🛠️ Tech Stack
- **Backend:** Flask, SQLAlchemy  
- **Database:** SQLite  
- **Authentication:** Flask-Bcrypt  
- **AI/Computer Vision:** Mediapipe, OpenCV, NumPy  
- **Visualization:** Matplotlib  
- **Frontend:** HTML (Jinja2 templates), Bootstrap (optional)  

---

## 🚀 Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/DonikTana/Exercise-Form-Checker.git
cd exercise-tracker

2. Create a Virtual Environment & Install Dependencies
python -m venv venv
source venv/bin/activate   # On Linux/Mac
venv\Scripts\activate      # On Windows
pip install -r requirements.txt

3. Run the Application
python app.py



📂Project Structure
exercise-tracker/
│── app.py                # Main Flask app
│── exercise_logs.db      # SQLite database
│── templates/            # HTML templates
│── static/               # Static files (CSS, JS, images)
│── requirements.txt      # Python dependencies
│── README.md             # Project documentation


🔮 Future Improvements

Add more exercises (push-ups, squats, planks, etc.)

Calorie calculation based on age, weight, height

Mobile-friendly responsive UI

Export logs to CSV/Excel

Community leaderboard & challenges

