# UWM Course Planner (Capstone Project)

A Django and SQLite web app with the goal of assisting UWM students plan their semesters using feedback from other students. Students review courses with difficulty and time commitment ratings as well as written reviews. Each course page shows the average ratings, similar courses, and an AI-generated summary of its reviews. The schedule calculator combines those ratings to estimate the work load of a semester.

## Features
**Course Search**
- Search the full UWM course catalog by code, title or major with pagination

**Course details pages**
- Shows average difficulty and time scores, professors, all reviews, an AI summary, and similar courses

**Reviews**
- Logged in students rate a course and professor on difficulty and time as well as leave a written review with tags
- Users can edit or delete past reviews as well up voting helpful reviews

**Review feed** 
- Browse all reviews, upvote helpful ones, and comment on them (AJAX endpoints). 

**Schedule calculator**
- Pick courses to see the combined workload.
- Logged-in users can save the selection to their profile. 

**Similar courses**
- TF-IDF + cosine-similarity recommendations built only from catalog titles and descriptions (no review or user data)
- computed offline. 

**AI review summaries**
- Google Gemini condenses a course's reviews into a summary with pros, cons and themes.
-  Optional; generated offline. 

**Accounts** 
- Registration with a major, email verification code, login/logout, password reset by email, and a profile page. 

**Admin**
- Django admin for users, majors, professors, courses and reviews. 

## Tech Stack
- **Python 3.12**
- **Djano 6.x**
- **SQLite**
- **scikit-learn / NumPy** (cosine simlarity)
- **google-genai + Pydantic** for Ai review summaries
- **openpyxl** for reading course catalog from excel spreadsheets
- **python-dotenv** for loading secrets
- Plain Django templats + CSS

## Fresh-start setup

### 1. Install requisites
- **Python 3.12 or newer.** Check with `python3 --version` (macOS/Linux) or `py --version` (Windows). Download it from <https://www.python.org/downloads/> if needed.
- **Git.** Check with `git --version`.

### 2. Clone the repo
```bash
git clone https://github.com/hoffm673/CapstoneProject.git
cd CapstoneProject
```
### 3. Create virtual environment
```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```
 
```powershell
# Windows (PowerShell)
py -m venv .venv
.venv\Scripts\Activate.ps1
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```
 
If `requirements.txt` isn't in the repo yet, install the packages directly:
 
```bash
pip install "Django>=6.0,<7" python-dotenv openpyxl scikit-learn numpy pydantic google-genai
```

### 5. Create you .env file(optional for local use)
```dotenv
# Email (leave blank to print emails to the terminal instead)
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
 
# AI review summaries (leave blank to disable)
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.1-flash-lite
```

### 6. Build new database

**a) Create the tables:**
```bash
python manage.py migrate
```
**b) Import course catalog:**
```bash
python import_courses.py/data/courses.csv
```
**c) Build the similar-course recommendations:**
```bash
python manage.py build_similar_courses
```
**d) (Optional) Add test reviews :**
```bash
oython seedreviews.py
```

### 7. Create an admin account
```bash
python manage.py createsuperuser
```

### 8.  Run the development
```bash
python manage.py runserver
```


