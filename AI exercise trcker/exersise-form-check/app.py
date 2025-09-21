from flask import Flask, render_template, request, redirect, url_for, session, Response, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime
import pytz
import cv2
import mediapipe as mp
import numpy as np
import io
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from collections import defaultdict
import os

app = Flask(__name__)
app.secret_key = 'super_secret_key'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///exercise_logs.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

IST = pytz.timezone("Asia/Kolkata")

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class ExerciseLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    exercise_type = db.Column(db.String(50), nullable=False)
    count = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(IST).replace(tzinfo=None))

# MediaPipe setup
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.7, min_tracking_confidence=0.7)
cap = None
tracking_active = False
current_exercise = 'bicep'
exercise_count = 0
state = False
stabilization_counter = 0

exercises = {
    'bicep': {
        'points': [mp_pose.PoseLandmark.LEFT_SHOULDER,
                   mp_pose.PoseLandmark.LEFT_ELBOW,
                   mp_pose.PoseLandmark.LEFT_WRIST],
        'angles': {'min': 60, 'max': 150},
        'name': 'Bicep Curls'
    },
    'situp': {
        'points': [mp_pose.PoseLandmark.LEFT_SHOULDER,
                   mp_pose.PoseLandmark.LEFT_HIP,
                   mp_pose.PoseLandmark.LEFT_KNEE],
        'angles': {'min': 40, 'max': 120},
        'name': 'Sit-ups'
    }
}

calories_per_rep = {
    'Bicep Curls': 0.3,
    'Sit-ups': 0.5
}

def calculate_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    ba, bc = a - b, c - b
    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
    angle = np.arccos(np.clip(cosine_angle, -1, 1))
    return np.degrees(angle)

def save_to_database():
    global exercise_count, current_exercise
    if exercise_count > 0 and 'user_id' in session:
        new_log = ExerciseLog(
            user_id=session['user_id'],
            exercise_type=exercises[current_exercise]['name'],
            count=exercise_count
        )
        db.session.add(new_log)
        db.session.commit()

def generate_frames():
    global tracking_active, current_exercise, exercise_count, state, stabilization_counter
    while True:
        if cap and cap.isOpened() and tracking_active:
            success, frame = cap.read()
            if not success:
                continue
            frame = cv2.flip(frame, 1)
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(image)

            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark
                exercise = exercises[current_exercise]
                try:
                    a = [landmarks[exercise['points'][0]].x, landmarks[exercise['points'][0]].y]
                    b = [landmarks[exercise['points'][1]].x, landmarks[exercise['points'][1]].y]
                    c = [landmarks[exercise['points'][2]].x, landmarks[exercise['points'][2]].y]
                    angle = calculate_angle(a, b, c)

                    if angle < exercise['angles']['min']:
                        if not state and stabilization_counter >= 5:
                            state = True
                            stabilization_counter = 0
                        stabilization_counter += 1
                    elif angle > exercise['angles']['max']:
                        if state and stabilization_counter >= 5:
                            exercise_count += 1
                            state = False
                            stabilization_counter = 0
                        stabilization_counter += 1

                    cv2.putText(frame, f"Count: {exercise_count}", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    cv2.putText(frame, exercise['name'], (10, 70),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                except Exception as e:
                    print(f"Pose detection error: {str(e)}")

            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

# Routes
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        if User.query.filter_by(username=username).first():
            return render_template('register.html', error="Username already exists.")
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')
@app.route('/calories_chart')
def calories_chart():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    logs = ExerciseLog.query.filter_by(user_id=session['user_id']).all()

    if not logs:
        return "No data available to plot.", 404

    daily_calories = defaultdict(float)
    for log in logs:
        date_str = log.timestamp.date().isoformat()
        calories = log.count * calories_per_rep.get(log.exercise_type, 0)
        daily_calories[date_str] += calories

    sorted_dates = sorted(daily_calories.keys())
    calories_values = [daily_calories[date] for date in sorted_dates]

    plt.figure(figsize=(10, 5))
    plt.bar(sorted_dates, calories_values, color='orange')
    plt.xticks(rotation=45)
    plt.title('Calories Burned Per Day')
    plt.xlabel('Date')
    plt.ylabel('Calories')
    plt.tight_layout()
    plt.grid(axis='y')

    img_bytes = io.BytesIO()
    plt.savefig(img_bytes, format='png')
    img_bytes.seek(0)
    plt.close()
    return send_file(img_bytes, mimetype='image/png')

@app.route('/exercise_chart')
def exercise_chart():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    logs = ExerciseLog.query.filter_by(user_id=session['user_id']).order_by(ExerciseLog.timestamp).all()
    
    if not logs:
        return "No data available to plot.", 404

    # Organize data
    exercise_data = defaultdict(list)
    for log in logs:
        exercise_data[log.exercise_type].append((log.timestamp, log.count))

    # Create plot
    plt.figure(figsize=(10, 5))
    for exercise_type, data in exercise_data.items():
        timestamps, counts = zip(*data)
        plt.plot(timestamps, counts, label=exercise_type)

    plt.title('Exercise Count Over Time')
    plt.xlabel('Time')
    plt.ylabel('Count')
    plt.legend()
    plt.tight_layout()
    plt.grid(True)

    # Format x-axis with date formatting
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d\n%H:%M'))
    plt.gcf().autofmt_xdate()

    # Save plot to BytesIO and send as response
    img_bytes = io.BytesIO()
    plt.savefig(img_bytes, format='png')
    img_bytes.seek(0)
    plt.close()
    return send_file(img_bytes, mimetype='image/png')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username, password = request.form['username'], request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('dashboard'))
        return render_template('login.html', error="Invalid username or password.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    logs = ExerciseLog.query.filter_by(user_id=session['user_id']).order_by(ExerciseLog.timestamp.desc()).limit(10).all()
    return render_template('dashboard.html', logs=logs)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/toggle_tracking')
def toggle_tracking():
    global tracking_active, cap
    if 'user_id' not in session:
        return '', 403
    new_state = request.args.get('active') == 'true'
    if tracking_active and not new_state:
        save_to_database()
    tracking_active = new_state
    if tracking_active and cap is None:
        cap = cv2.VideoCapture(0)
    elif not tracking_active and cap:
        cap.release()
        cap = None
    return '', 204

@app.route('/switch_exercise')
def switch_exercise():
    global current_exercise, exercise_count, state, stabilization_counter
    save_to_database()
    current_exercise = 'situp' if current_exercise == 'bicep' else 'bicep'
    exercise_count = 0
    state = False
    stabilization_counter = 0
    return '', 204

@app.route('/reset_counter')
def reset_counter():
    global exercise_count
    exercise_count = 0
    return '', 204

def run_app():
    with app.app_context():
        db.create_all()
    app.run(debug=True, threaded=True)

if __name__ == '__main__':
    run_app()
