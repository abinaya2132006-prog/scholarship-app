from flask import Flask, render_template, request
import sqlite3
import pickle
import pandas as pd

app = Flask(__name__)

# Load ML model and feature columns
with open('scholarship_model.pkl','rb') as f:
    ml_model = pickle.load(f)

with open('model_columns.pkl','rb') as f:
    model_columns = pickle.load(f)

# Initialize database
def init_db():
    conn = sqlite3.connect('students.db')
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            percentage INTEGER,
            community TEXT,
            income INTEGER,
            gender TEXT,
            course TEXT,
            first_graduate TEXT,
            tn_resident TEXT,
            result TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/check', methods=['POST'])
def check():
    # Get form data
    percentage = int(request.form.get('percentage',0))
    community = request.form.get('community')
    income = int(request.form.get('income',0))
    gender = request.form.get('gender')
    course = request.form.get('course')
    first_graduate = request.form.get('first_graduate')
    tn_resident = request.form.get('tn_resident')

    # Encode for ML
    input_dict = {
        'percentage': percentage,
        'income': income,
        'community_BC': 1 if community=='BC' else 0,
        'community_General': 1 if community=='General' else 0,
        'community_MBC': 1 if community=='MBC' else 0,
        'community_OBC': 1 if community=='OBC' else 0,
        'community_SC': 1 if community=='SC' else 0,
        'community_ST': 1 if community=='ST' else 0,
        'gender_Female': 1 if gender=='Female' else 0,
        'gender_Male': 1 if gender=='Male' else 0,
        'course_Diploma': 1 if course=='Diploma' else 0,
        'course_UG': 1 if course=='UG' else 0,
        'course_ITI': 1 if course=='ITI' else 0,
        'first_graduate_No': 1 if first_graduate=='No' else 0,
        'first_graduate_Yes': 1 if first_graduate=='Yes' else 0,
        'tn_resident_No': 1 if tn_resident=='No' else 0,
        'tn_resident_Yes': 1 if tn_resident=='Yes' else 0
    }

    input_df = pd.DataFrame([input_dict])

    # Add missing columns
    for col in model_columns:
        if col not in input_df.columns:
            input_df[col] = 0

    # Reorder columns
    input_df = input_df[model_columns]

    # ML prediction
    prediction = ml_model.predict(input_df)[0]
    eligible = True if prediction==1 else False

    # Scholarships logic
    scholarships = []
    if eligible:
        scholarships.append("Central Government Scholarship")
        if tn_resident.lower() == "yes":
            scholarships.append("Tamil Nadu State Scholarship")
        if community in ["SC","ST","OBC","MBC","BC"]:
            scholarships.append("Community Based Scholarship")
        if gender.lower() == "female":
            scholarships.append("Girl Child Scholarship")
        if first_graduate.lower() == "yes":
            scholarships.append("First Graduate Scholarship")
        if course.lower() in ["ug","diploma"]:
            scholarships.append(f"{course} Merit Scholarship")

    result_text = "Eligible" if eligible else "Not Eligible"

    # Save to database
    conn = sqlite3.connect('students.db')
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO students
        (percentage, community, income, gender, course, first_graduate, tn_resident, result)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (percentage, community, income, gender, course, first_graduate, tn_resident, result_text))
    conn.commit()
    conn.close()

    return render_template('result.html', eligible=eligible, scholarships=scholarships)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
