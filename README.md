# ai-scheduler-project

AI-Driven Workforce Scheduler Pro
This is a full-stack web application designed to solve the complex problem of manual workforce scheduling. It uses an AI-driven engine to automatically generate optimal weekly work schedules, taking into account employee skills, availability, and task priorities.

Live Demo: https://sanjana-ai-scheduler.onrender.com/

Features
This application is a complete, enterprise-grade tool with a full suite of features for effective workforce management.

🔐 Secure Login System: A complete authentication system ensures that only authorized planners can access the application.

🏠 Professional Dashboard: A central hub that provides a high-level overview of the weekly schedule, task progress, resource utilization, and upcoming employee leave.

👥 Employee Management Module: A dedicated interface to manage the workforce.

Add, edit, and delete employee profiles (name, role, department, location).

Tag employees with specific skills (e.g., Electrical, Inspection).

Manage weekly availability and set leave days.

📋 Task Management Module: A complete system for managing the project's workload.

Add, edit, and delete tasks.

Define task properties like required skill, priority (High, Medium, Low), estimated time, and deadlines.

✏️ Manual Editor & AI Learning Loop:

A manager can manually override any AI-generated assignment.

The system learns from these manual changes, and its future suggestions become smarter and more aligned with the manager's preferences.

⚙️ Rule Customization Panel:

Allows a manager to set global rules, such as the maximum number of shifts an employee can be assigned per week, to ensure fair workload balancing.

Technology Stack
This project was built as a full-stack application using a modern and robust technology stack.

Backend:

Language: Python

Web Framework: Flask

Database: SQLite

ORM: SQLAlchemy

Frontend:

Structure: HTML

Styling: Pico.css (a lightweight CSS framework)

Templating: Jinja2

AI Engine:

Library: Google OR-Tools

Technique: Constraint Optimization (CP-SAT Solver)

Authentication:

Flask-Login (Session Management)

Flask-Bcrypt (Password Hashing)

Version Control:

Git & GitHub

Local Setup & Installation
To run this project on your local machine, please follow these steps:

1. Prerequisites:

Python 3.x installed

pip and venv

2. Clone the Repository:

git clone https://github.com/your-username/ai-scheduler-project.git
cd ai-scheduler-project

3. Set up a Virtual Environment:

# Create the virtual environment
python -m venv venv

# Activate it (on Windows)
.\venv\Scripts\activate

# Activate it (on Mac/Linux)
source venv/bin/activate

4. Install Dependencies:
The requirements.txt file contains all the necessary Python packages.

pip install -r requirements.txt

5. Run the Application:
The application uses Flask's built-in server for local development.

flask run

The application will be available at http://127.0.0.1:5000.

Default Admin Login:

Username: admin

Password: password
