#!/usr/bin/env python3
"""
Comprehensive Health Assistant Application
Using Google Generative AI (Gemini)
Features: Prescription reading, meal planning, reminders, health tracking
"""

import streamlit as st
import google.generativeai as genai
from PIL import Image
import cv2
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import re
from langdetect import detect
from googletrans import Translator
import base64
from io import BytesIO
from dotenv import load_dotenv
import pytesseract
import platform
# Load environment variables BEFORE trying to use them
load_dotenv()


# Windows Tesseract path
if platform.system() == 'Windows':
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# ====== CONFIGURATION ======
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")  # Set your API key
if not GOOGLE_API_KEY:
    st.error("⚠️ Please set GOOGLE_API_KEY in .env file or environment variables")
    st.stop()

genai.configure(api_key=GOOGLE_API_KEY)

# Initialize Gemini model - using gemini-pro which is more widely available
try:
    model = genai.GenerativeModel('gemini-2.5-flash')
except:
    model = genai.GenerativeModel('gemini-1.5-flash')
translator = Translator()

# Add pytesseract import and configuration
import pytesseract
# Uncomment and set path if needed on Windows:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# ====== DATA STORAGE PATHS ======
DATA_DIR = Path("health_data")
DATA_DIR.mkdir(exist_ok=True)
PRESCRIPTIONS_FILE = DATA_DIR / "prescriptions.json"
MEALS_FILE = DATA_DIR / "meals.json"
MEDICATIONS_FILE = DATA_DIR / "medications.json"
WATER_FILE = DATA_DIR / "water_log.json"
EXERCISE_FILE = DATA_DIR / "exercise_log.json"
GOALS_FILE = DATA_DIR / "goals.json"
EMERGENCY_FILE = DATA_DIR / "emergency_contacts.json"

# ====== HELPER FUNCTIONS ======

def load_json_data(filepath):
    """Load JSON data from file"""
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json_data(filepath, data):
    """Save JSON data to file"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def extract_text_from_image(image):
    """Extract text from prescription image using OCR"""
    try:
        # Preprocess image
        img_array = np.array(image)
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # Threshold
        _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Extract text using Tesseract
        text = pytesseract.image_to_string(thresh)
        
        return text, thresh
    except Exception as e:
        st.error(f"OCR Error: {str(e)}")
        return None, None

def analyze_prescription(image):
    """Analyze prescription using OCR + Gemini"""
    try:
        # Step 1: Extract text using OCR
        with st.spinner("Extracting text from prescription..."):
            extracted_text, processed_img = extract_text_from_image(image)
            
            if not extracted_text:
                return "Error: Could not extract text from image"
            
            # Save extracted text
            ocr_dir = Path("output/ocr_extracts")
            ocr_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save extracted text
            with open(ocr_dir / f"prescription_{timestamp}.txt", 'w', encoding='utf-8') as f:
                f.write(extracted_text)
            
            # Save processed image
            if processed_img is not None:
                cv2.imwrite(str(ocr_dir / f"prescription_{timestamp}_processed.png"), processed_img)
        
        # Step 2: Analyze with Gemini
        with st.spinner("Analyzing prescription with AI..."):
            prompt = f"""
            Analyze this medical prescription text and provide:
            1. List of all medications with dosage and frequency
            2. Duration of treatment
            3. Special instructions (before/after food, timing, etc.)
            4. Purpose of each medication (if mentioned)
            5. Doctor's name and specialty (if visible)
            6. Any warnings or precautions
            7. Patient information (if available)
            
            Extracted Text from Prescription:
            {extracted_text}
            
            Format the response in a clear, structured way that's easy to understand.
            If some information is not clear, indicate it as "Not clearly visible".
            """
            
            response = model.generate_content(prompt)
            
            # Save analysis
            analysis_data = {
                "timestamp": timestamp,
                "extracted_text": extracted_text,
                "analysis": response.text,
                "ocr_file": f"prescription_{timestamp}.txt"
            }
            
            with open(ocr_dir / f"prescription_{timestamp}_analysis.json", 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, indent=2)
            
            return response.text
            
    except Exception as e:
        return f"Error analyzing prescription: {str(e)}\n\nPlease check:\n1. Image quality\n2. Tesseract installation\n3. API key validity"

def get_medication_info(medication_name):
    """Get detailed information about a medication"""
    prompt = f"""
    Provide comprehensive information about the medication: {medication_name}
    Include:
    1. What it's used for (main purpose)
    2. How it works
    3. Common side effects
    4. Important precautions
    5. Foods/drinks to avoid while taking it
    6. Best time to take it
    
    Keep the language simple and easy to understand for patients.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error getting medication info: {str(e)}"

def generate_meal_plan(health_conditions, dietary_preferences, goals):
    """Generate personalized meal plan"""
    prompt = f"""
    Create a 7-day meal plan for someone with:
    - Health conditions: {health_conditions}
    - Dietary preferences: {dietary_preferences}
    - Health goals: {goals}
    
    For each day, provide:
    - Breakfast, Lunch, Dinner, and 2 Snacks
    - Approximate calories
    - Key nutrients
    - Simple recipes with common ingredients
    
    Make it practical and easy to follow.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating meal plan: {str(e)}"

def get_exercise_recommendations(fitness_level, goals, health_conditions):
    """Get personalized exercise recommendations"""
    prompt = f"""
    Suggest exercises for someone with:
    - Fitness level: {fitness_level}
    - Goals: {goals}
    - Health conditions: {health_conditions}
    
    Provide:
    1. Weekly exercise schedule (7 days)
    2. Specific exercises with duration
    3. Warm-up and cool-down routines
    4. Safety precautions
    5. Progression tips
    
    Keep it safe and achievable.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error getting exercise recommendations: {str(e)}"

def get_health_tips(category="general"):
    """Get daily health tips"""
    prompt = f"""
    Provide 5 practical health tips about: {category}
    Make them actionable, evidence-based, and easy to implement.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error getting health tips: {str(e)}"

def translate_text(text, target_language):
    """Translate text to target language"""
    try:
        translation = translator.translate(text, dest=target_language)
        return translation.text
    except Exception as e:
        return f"Translation error: {str(e)}"

def calculate_bmi(weight_kg, height_cm):
    """Calculate BMI"""
    height_m = height_cm / 100
    bmi = weight_kg / (height_m ** 2)
    
    if bmi < 18.5:
        category = "Underweight"
    elif bmi < 25:
        category = "Normal"
    elif bmi < 30:
        category = "Overweight"
    else:
        category = "Obese"
    
    return round(bmi, 1), category

def calculate_water_intake(weight_kg, activity_level):
    """Calculate recommended daily water intake"""
    base_intake = weight_kg * 35  # ml per kg
    
    activity_multipliers = {
        "Sedentary": 1.0,
        "Light": 1.1,
        "Moderate": 1.2,
        "Active": 1.3,
        "Very Active": 1.4
    }
    
    multiplier = activity_multipliers.get(activity_level, 1.0)
    recommended_ml = base_intake * multiplier
    
    return int(recommended_ml)

# ====== STREAMLIT APP ======

def main():
    st.set_page_config(
        page_title="Health Assistant AI",
        page_icon="🏥",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state
    if 'user_profile' not in st.session_state:
        st.session_state.user_profile = load_json_data(DATA_DIR / "user_profile.json")
    
    if 'medications' not in st.session_state:
        st.session_state.medications = load_json_data(MEDICATIONS_FILE)
    
    if 'water_log' not in st.session_state:
        st.session_state.water_log = load_json_data(WATER_FILE)
    
    if 'goals' not in st.session_state:
        st.session_state.goals = load_json_data(GOALS_FILE)
    
    # Sidebar
    with st.sidebar:
        st.title("🏥 Health Assistant")
        st.markdown("---")
        
        # Language selector
        language = st.selectbox(
            "🌍 Language",
            ["en", "hi", "te", "ta", "bn", "mr", "gu", "kn", "ml", "pa"],
            format_func=lambda x: {
                "en": "English", "hi": "हिंदी", "te": "తెలుగు", 
                "ta": "தமிழ்", "bn": "বাংলা", "mr": "मराठी",
                "gu": "ગુજરાતી", "kn": "ಕನ್ನಡ", "ml": "മലയാളം", "pa": "ਪੰਜਾਬੀ"
            }[x]
        )
        
        st.markdown("---")
        
        # User profile
        st.subheader("👤 Your Profile")
        if st.session_state.user_profile:
            st.write(f"Name: {st.session_state.user_profile.get('name', 'Not set')}")
            st.write(f"Age: {st.session_state.user_profile.get('age', 'Not set')}")
        
        if st.button("Edit Profile"):
            st.session_state.show_profile_editor = True
    
    # Main content
    st.title("🏥 Your Personal Health Assistant")
    st.markdown("### Powered by Google Gemini AI")
    
    # Tabs
    tabs = st.tabs([
        "📋 Prescriptions",
        "🍽️ Meal Planner",
        "💊 Medications",
        "💧 Water Tracker",
        "🎯 Goals & Progress",
        "🏃 Exercise",
        "💡 Health Tips",
        "🆘 Emergency"
    ])
    
    # Tab 1: Prescriptions
    with tabs[0]:
        st.header("📋 Prescription Reader & Analyzer")
        
        uploaded_prescription = st.file_uploader(
            "Upload prescription image",
            type=['jpg', 'jpeg', 'png'],
            help="Upload a clear photo of your prescription"
        )
        
        if uploaded_prescription:
            image = Image.open(uploaded_prescription)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.image(image, caption="Your Prescription", use_container_width=True)
            
            with col2:
                if st.button("🔍 Analyze Prescription", type="primary"):
                    with st.spinner("Processing prescription..."):
                        analysis = analyze_prescription(image)
                        
                        if "Error" not in analysis:
                            st.success("Analysis complete!")
                            
                            # Show extracted text first
                            with st.expander("📄 Extracted Text (OCR)"):
                                ocr_dir = Path("output/ocr_extracts")
                                latest_file = sorted(ocr_dir.glob("prescription_*.txt"))[-1]
                                with open(latest_file, 'r', encoding='utf-8') as f:
                                    st.text(f.read())
                            
                            # Show AI analysis
                            st.markdown("### 🤖 AI Analysis")
                            st.markdown(analysis)
                            
                            # Save prescription
                            prescriptions = load_json_data(PRESCRIPTIONS_FILE)
                            prescription_id = datetime.now().strftime("%Y%m%d_%H%M%S")
                            prescriptions[prescription_id] = {
                                "date": datetime.now().isoformat(),
                                "analysis": analysis
                            }
                            save_json_data(PRESCRIPTIONS_FILE, prescriptions)
                        else:
                            st.error(analysis)
        
        # Show saved prescriptions
        st.subheader("📚 Previous Prescriptions")
        prescriptions = load_json_data(PRESCRIPTIONS_FILE)
        if prescriptions:
            for pid, data in sorted(prescriptions.items(), reverse=True)[:5]:
                with st.expander(f"Prescription from {data['date'][:10]}"):
                    st.markdown(data['analysis'])
        else:
            st.info("No prescriptions saved yet")
    
    # Tab 2: Meal Planner
    with tabs[1]:
        st.header("🍽️ Personalized Meal Planner")
        
        col1, col2 = st.columns(2)
        
        with col1:
            health_conditions = st.text_area(
                "Health Conditions",
                placeholder="e.g., Diabetes, High blood pressure"
            )
            dietary_preferences = st.text_area(
                "Dietary Preferences",
                placeholder="e.g., Vegetarian, No gluten"
            )
        
        with col2:
            goals = st.text_area(
                "Health Goals",
                placeholder="e.g., Weight loss, Muscle gain"
            )
        
        if st.button("🎯 Generate Meal Plan", type="primary"):
            with st.spinner("Creating your personalized meal plan..."):
                meal_plan = generate_meal_plan(
                    health_conditions or "None",
                    dietary_preferences or "None",
                    goals or "General health"
                )
                
                st.success("Meal plan ready!")
                st.markdown(meal_plan)
                
                # Save meal plan
                meals = load_json_data(MEALS_FILE)
                meal_id = datetime.now().strftime("%Y%m%d_%H%M%S")
                meals[meal_id] = {
                    "date": datetime.now().isoformat(),
                    "plan": meal_plan,
                    "conditions": health_conditions,
                    "preferences": dietary_preferences,
                    "goals": goals
                }
                save_json_data(MEALS_FILE, meals)
        
        # Show saved meal plans
        st.subheader("📚 Your Meal Plans")
        meals = load_json_data(MEALS_FILE)
        if meals:
            for mid, data in sorted(meals.items(), reverse=True)[:3]:
                with st.expander(f"Meal Plan from {data['date'][:10]}"):
                    st.markdown(data['plan'])
    
    # Tab 3: Medications
    with tabs[2]:
        st.header("💊 Medication Tracker & Reminders")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            med_name = st.text_input("Medication Name")
            med_dosage = st.text_input("Dosage (e.g., 500mg)")
            med_frequency = st.selectbox(
                "Frequency",
                ["Once daily", "Twice daily", "Three times daily", "As needed"]
            )
            med_time = st.time_input("Reminder Time")
            med_notes = st.text_area("Special Instructions")
        
        with col2:
            if st.button("➕ Add Medication"):
                if med_name:
                    medications = load_json_data(MEDICATIONS_FILE)
                    med_id = datetime.now().strftime("%Y%m%d_%H%M%S")
                    medications[med_id] = {
                        "name": med_name,
                        "dosage": med_dosage,
                        "frequency": med_frequency,
                        "time": str(med_time),
                        "notes": med_notes,
                        "added_date": datetime.now().isoformat()
                    }
                    save_json_data(MEDICATIONS_FILE, medications)
                    st.success(f"Added {med_name}")
                    st.rerun()
        
        # Show medications
        st.subheader("📋 Your Medications")
        medications = load_json_data(MEDICATIONS_FILE)
        
        if medications:
            for med_id, med in medications.items():
                with st.expander(f"💊 {med['name']} - {med['dosage']}"):
                    st.write(f"**Frequency:** {med['frequency']}")
                    st.write(f"**Time:** {med['time']}")
                    st.write(f"**Notes:** {med['notes']}")
                    
                    if st.button(f"ℹ️ Learn More", key=f"info_{med_id}"):
                        with st.spinner("Fetching medication information..."):
                            info = get_medication_info(med['name'])
                            st.markdown(info)
                    
                    if st.button(f"🗑️ Remove", key=f"del_{med_id}"):
                        del medications[med_id]
                        save_json_data(MEDICATIONS_FILE, medications)
                        st.rerun()
        else:
            st.info("No medications added yet")
    
    # Tab 4: Water Tracker
    with tabs[3]:
        st.header("💧 Water Intake Tracker")
        
        # Calculate recommended intake
        if st.session_state.user_profile.get('weight'):
            weight = st.session_state.user_profile['weight']
            activity = st.session_state.user_profile.get('activity_level', 'Moderate')
            recommended = calculate_water_intake(weight, activity)
            
            st.info(f"🎯 Recommended daily intake: {recommended}ml ({recommended//250} glasses)")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💧 +250ml", use_container_width=True):
                today = datetime.now().strftime("%Y-%m-%d")
                water_log = load_json_data(WATER_FILE)
                if today not in water_log:
                    water_log[today] = 0
                water_log[today] += 250
                save_json_data(WATER_FILE, water_log)
                st.rerun()
        
        with col2:
            if st.button("💧💧 +500ml", use_container_width=True):
                today = datetime.now().strftime("%Y-%m-%d")
                water_log = load_json_data(WATER_FILE)
                if today not in water_log:
                    water_log[today] = 0
                water_log[today] += 500
                save_json_data(WATER_FILE, water_log)
                st.rerun()
        
        with col3:
            if st.button("🔄 Reset Today", use_container_width=True):
                today = datetime.now().strftime("%Y-%m-%d")
                water_log = load_json_data(WATER_FILE)
                if today in water_log:
                    del water_log[today]
                save_json_data(WATER_FILE, water_log)
                st.rerun()
        
        # Show today's progress
        water_log = load_json_data(WATER_FILE)
        today = datetime.now().strftime("%Y-%m-%d")
        today_intake = water_log.get(today, 0)
        
        st.metric("Today's Intake", f"{today_intake}ml")
        
        if st.session_state.user_profile.get('weight'):
            progress = (today_intake / recommended) * 100
            st.progress(min(progress / 100, 1.0))
            st.write(f"Progress: {progress:.1f}%")
        
        # Chart
        if len(water_log) > 1:
            df = pd.DataFrame([
                {"date": k, "intake": v} 
                for k, v in sorted(water_log.items())[-7:]
            ])
            fig = px.bar(df, x="date", y="intake", title="Last 7 Days Water Intake")
            st.plotly_chart(fig, use_container_width=True)
    
    # Tab 5: Goals & Progress
    with tabs[4]:
        st.header("🎯 Health Goals & Motivation")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Set Your Goals")
            goal_type = st.selectbox(
                "Goal Type",
                ["Weight Loss", "Weight Gain", "Fitness", "Nutrition", "Habit Building"]
            )
            goal_target = st.text_input("Target (e.g., Lose 5kg, Walk 10000 steps)")
            goal_deadline = st.date_input("Target Date")
            
            if st.button("➕ Add Goal"):
                goals = load_json_data(GOALS_FILE)
                goal_id = datetime.now().strftime("%Y%m%d_%H%M%S")
                goals[goal_id] = {
                    "type": goal_type,
                    "target": goal_target,
                    "deadline": str(goal_deadline),
                    "created": datetime.now().isoformat(),
                    "status": "active"
                }
                save_json_data(GOALS_FILE, goals)
                st.success("Goal added!")
                st.rerun()
        
        with col2:
            st.subheader("💪 Motivational Message")
            if st.button("Get Motivation"):
                prompt = "Generate a short, powerful motivational message for someone working on their health goals."
                try:
                    response = model.generate_content(prompt)
                    st.success(response.text)
                except Exception as e:
                    st.error(f"Error: {e}")
        
        # Show goals
        st.subheader("📋 Your Goals")
        goals = load_json_data(GOALS_FILE)
        
        if goals:
            for gid, goal in goals.items():
                if goal['status'] == 'active':
                    with st.expander(f"🎯 {goal['type']}: {goal['target']}"):
                        st.write(f"**Deadline:** {goal['deadline']}")
                        days_left = (datetime.fromisoformat(goal['deadline'] + "T00:00:00") - datetime.now()).days
                        st.write(f"**Days left:** {days_left}")
                        
                        if st.button("✅ Complete", key=f"complete_{gid}"):
                            goals[gid]['status'] = 'completed'
                            save_json_data(GOALS_FILE, goals)
                            st.balloons()
                            st.rerun()
    
    # Tab 6: Exercise
    with tabs[5]:
        st.header("🏃 Exercise Recommendations")
        
        fitness_level = st.select_slider(
            "Current Fitness Level",
            options=["Beginner", "Intermediate", "Advanced"]
        )
        
        exercise_goals = st.multiselect(
            "Exercise Goals",
            ["Weight Loss", "Muscle Building", "Endurance", "Flexibility", "General Fitness"]
        )
        
        health_concerns = st.text_area(
            "Any health concerns or limitations?",
            placeholder="e.g., Knee pain, back issues"
        )
        
        if st.button("🎯 Get Exercise Plan", type="primary"):
            with st.spinner("Creating your exercise plan..."):
                plan = get_exercise_recommendations(
                    fitness_level,
                    ", ".join(exercise_goals),
                    health_concerns or "None"
                )
                st.success("Exercise plan ready!")
                st.markdown(plan)
                
                # Save plan
                exercise_log = load_json_data(EXERCISE_FILE)
                ex_id = datetime.now().strftime("%Y%m%d_%H%M%S")
                exercise_log[ex_id] = {
                    "date": datetime.now().isoformat(),
                    "plan": plan,
                    "level": fitness_level,
                    "goals": exercise_goals
                }
                save_json_data(EXERCISE_FILE, exercise_log)
    
    # Tab 7: Health Tips
    with tabs[6]:
        st.header("💡 Daily Health Tips & Articles")
        
        tip_category = st.selectbox(
            "Select Category",
            ["General Health", "Nutrition", "Exercise", "Mental Health", 
             "Sleep", "Stress Management", "Heart Health", "Diabetes Management"]
        )
        
        if st.button("📚 Get Health Tips", type="primary"):
            with st.spinner("Fetching health tips..."):
                tips = get_health_tips(tip_category)
                st.markdown(tips)
        
        # Translate option
        if 'tips' in locals():
            target_lang = st.selectbox("Translate to:", ["None", "Hindi", "Telugu", "Tamil"])
            if target_lang != "None" and st.button("🌍 Translate"):
                lang_codes = {"Hindi": "hi", "Telugu": "te", "Tamil": "ta"}
                translated = translate_text(tips, lang_codes[target_lang])
                st.markdown(translated)
    
    # Tab 8: Emergency
    with tabs[7]:
        st.header("🆘 Emergency Contacts & Health Info")
        
        st.subheader("👤 Your Health Information")
        
        blood_type = st.selectbox(
            "Blood Type",
            ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
        )
        
        allergies = st.text_area("Allergies", placeholder="List any allergies")
        chronic_conditions = st.text_area("Chronic Conditions", placeholder="Diabetes, Hypertension, etc.")
        current_medications = st.text_area("Current Medications")
        
        if st.button("💾 Save Health Info"):
            profile = load_json_data(DATA_DIR / "user_profile.json")
            profile.update({
                "blood_type": blood_type,
                "allergies": allergies,
                "chronic_conditions": chronic_conditions,
                "current_medications": current_medications
            })
            save_json_data(DATA_DIR / "user_profile.json", profile)
            st.success("Health information saved!")
        
        st.markdown("---")
        st.subheader("📞 Emergency Contacts")
        
        # Add emergency contact
        with st.expander("➕ Add Emergency Contact"):
            contact_name = st.text_input("Name")
            contact_relation = st.text_input("Relation")
            contact_phone = st.text_input("Phone Number")
            
            if st.button("Add Contact"):
                if contact_name and contact_phone:
                    contacts = load_json_data(EMERGENCY_FILE)
                    contact_id = datetime.now().strftime("%Y%m%d_%H%M%S")
                    contacts[contact_id] = {
                        "name": contact_name,
                        "relation": contact_relation,
                        "phone": contact_phone
                    }
                    save_json_data(EMERGENCY_FILE, contacts)
                    st.success("Contact added!")
                    st.rerun()
        
        # Display contacts
        contacts = load_json_data(EMERGENCY_FILE)
        if contacts:
            for cid, contact in contacts.items():
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.write(f"**{contact['name']}**")
                with col2:
                    st.write(f"{contact['relation']} - {contact['phone']}")
                with col3:
                    if st.button("🗑️", key=f"del_contact_{cid}"):
                        del contacts[cid]
                        save_json_data(EMERGENCY_FILE, contacts)
                        st.rerun()
    
    # Profile Editor Modal
    if st.session_state.get('show_profile_editor'):
        with st.sidebar:
            st.markdown("---")
            st.subheader("Edit Profile")
            
            name = st.text_input("Name", value=st.session_state.user_profile.get('name', ''))
            age = st.number_input("Age", min_value=1, max_value=120, 
                                 value=st.session_state.user_profile.get('age', 25))
            weight = st.number_input("Weight (kg)", min_value=20.0, max_value=200.0,
                                    value=st.session_state.user_profile.get('weight', 70.0))
            height = st.number_input("Height (cm)", min_value=100.0, max_value=250.0,
                                    value=st.session_state.user_profile.get('height', 170.0))
            activity = st.selectbox("Activity Level",
                                   ["Sedentary", "Light", "Moderate", "Active", "Very Active"],
                                   index=["Sedentary", "Light", "Moderate", "Active", "Very Active"].index(
                                       st.session_state.user_profile.get('activity_level', 'Moderate')))
            
            if st.button("💾 Save Profile"):
                profile = {
                    "name": name,
                    "age": age,
                    "weight": weight,
                    "height": height,
                    "activity_level": activity
                }
                save_json_data(DATA_DIR / "user_profile.json", profile)
                st.session_state.user_profile = profile
                st.session_state.show_profile_editor = False
                st.success("Profile updated!")
                st.rerun()
            
            if st.button("Cancel"):
                st.session_state.show_profile_editor = False
                st.rerun()
    
    # BMI Calculator in sidebar
    if st.session_state.user_profile.get('weight') and st.session_state.user_profile.get('height'):
        with st.sidebar:
            st.markdown("---")
            st.subheader("📊 Your BMI")
            bmi, category = calculate_bmi(
                st.session_state.user_profile['weight'],
                st.session_state.user_profile['height']
            )
            st.metric("BMI", f"{bmi}")
            st.write(f"Category: **{category}**")

if __name__ == "__main__":
    main()