import os
from collections import Counter
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, IntegerField, DateField, PasswordField
from wtforms.validators import DataRequired, Optional, EqualTo
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt

from solver import generate_schedule

# --- App and Database Configuration ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'a-super-secret-key-that-is-long-and-random'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'scheduler.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# --- Database Models ---
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='Planner')

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    skills = db.Column(db.String(200), nullable=False)
    unavailable_days = db.Column(db.String(100), nullable=True, default='')
    location = db.Column(db.String(100), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    role = db.Column(db.String(100), nullable=True)
    preferences = db.relationship('LearnedPreference', backref='employee', cascade="all, delete-orphan")

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    required_skill = db.Column(db.String(50), nullable=False)
    priority = db.Column(db.Integer, nullable=False, default=1)
    estimated_time = db.Column(db.Integer, nullable=True)
    deadline = db.Column(db.Date, nullable=True)
    preferences = db.relationship('LearnedPreference', backref='task', cascade="all, delete-orphan")

class LearnedPreference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False, default=1)
    __table_args__ = (db.UniqueConstraint('employee_id', 'task_id', name='_employee_task_uc'),)

class Rule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(50), nullable=False)

# --- Web Forms ---
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class EmployeeForm(FlaskForm):
    name = StringField('Employee Name', validators=[DataRequired()])
    skills = StringField('Skills (comma-separated)', validators=[DataRequired()])
    location = StringField('Location', validators=[Optional()])
    department = StringField('Department', validators=[Optional()])
    role = StringField('Role', validators=[Optional()])
    submit = SubmitField('Save Employee')

class TaskForm(FlaskForm):
    name = StringField('Task Name', validators=[DataRequired()])
    required_skill = StringField('Required Skill', validators=[DataRequired()])
    priority = SelectField('Priority', choices=[('1', 'Low'), ('2', 'Medium'), ('3', 'High')], coerce=int, validators=[DataRequired()])
    estimated_time = IntegerField('Estimated Time (hours)', validators=[Optional()])
    deadline = DateField('Deadline', format='%Y-%m-%d', validators=[Optional()])
    submit = SubmitField('Save Task')

class RuleForm(FlaskForm):
    max_shifts_per_week = IntegerField('Max Shifts Per Week Per Employee', validators=[DataRequired()])
    submit = SubmitField('Save Rules')

# --- Helper Function ---
def get_solver_data():
    DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    SHIFTS = ["Morning", "Evening"]
    employees_from_db = db.session.execute(db.select(Employee)).scalars().all()
    tasks_from_db = db.session.execute(db.select(Task)).scalars().all()
    preferences_from_db = db.session.execute(db.select(LearnedPreference)).scalars().all()
    max_shifts_rule = db.session.execute(db.select(Rule).filter_by(name='max_shifts_per_week')).scalar_one_or_none()
    rules_dict = {'max_shifts_per_week': int(max_shifts_rule.value) if max_shifts_rule else 7}
    employees_dict = [{'id': e.id, 'name': e.name, 'skills': [s.strip() for s in e.skills.split(',')] if e.skills else [], 'unavailable_days': [d.strip() for d in e.unavailable_days.split(',')] if e.unavailable_days else []} for e in employees_from_db]
    tasks_dict = [{'id': t.id, 'name': t.name, 'required_skill': t.required_skill, 'priority': t.priority} for t in tasks_from_db]
    preferences_dict = {(p.employee_id, p.task_id): p.score for p in preferences_from_db}
    return employees_dict, tasks_dict, preferences_dict, DAYS, SHIFTS, rules_dict

# --- App Routes ---
@app.route('/')
def landing_page():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('landing_page.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.execute(db.select(User).filter_by(username=form.username.data)).scalar_one_or_none()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('landing_page'))

@app.route('/dashboard')
@login_required
def dashboard():
    employees_dict, tasks_dict, preferences_dict, DAYS, SHIFTS, rules_dict = get_solver_data()
    schedule_result, unscheduled_tasks = generate_schedule(employees_dict, tasks_dict, DAYS, SHIFTS, preferences_dict, rules_dict)
    utilization_counts = Counter(item['employee_name'] for item in schedule_result) if schedule_result else {}
    for emp in employees_dict:
        if emp['name'] not in utilization_counts:
            utilization_counts[emp['name']] = 0
    employees_on_leave = [emp for emp in employees_dict if emp['unavailable_days']]
    return render_template('dashboard.html', 
                           schedule=schedule_result, days=DAYS, shifts=SHIFTS,
                           utilization=utilization_counts, employees_on_leave=employees_on_leave,
                           task_count_scheduled=len(schedule_result) if schedule_result else 0,
                           task_count_unscheduled=len(unscheduled_tasks))

@app.route('/employee_management')
@login_required
def employee_management():
    employees = db.session.execute(db.select(Employee).order_by(Employee.name)).scalars().all()
    return render_template('employee_management.html', employees=employees)

@app.route('/task_management')
@login_required
def task_management():
    tasks = db.session.execute(db.select(Task).order_by(Task.priority.desc())).scalars().all()
    return render_template('task_management.html', tasks=tasks)

@app.route('/schedule_editor')
@login_required
def schedule_editor():
    employees_dict, tasks_dict, preferences_dict, DAYS, SHIFTS, rules_dict = get_solver_data()
    schedule_result, unscheduled_tasks = generate_schedule(employees_dict, tasks_dict, DAYS, SHIFTS, preferences_dict, rules_dict)
    return render_template('schedule_editor.html', schedule=schedule_result, unscheduled=unscheduled_tasks, days=DAYS, shifts=SHIFTS, employees=employees_dict)

@app.route('/rules', methods=['GET', 'POST'])
@login_required
def rules():
    form = RuleForm()
    max_shifts_rule = db.session.execute(db.select(Rule).filter_by(name='max_shifts_per_week')).scalar_one_or_none()
    if form.validate_on_submit():
        if max_shifts_rule:
            max_shifts_rule.value = str(form.max_shifts_per_week.data)
        else:
            new_rule = Rule(name='max_shifts_per_week', value=str(form.max_shifts_per_week.data))
            db.session.add(new_rule)
        db.session.commit()
        flash("Rules updated successfully!", "success")
        return redirect(url_for('rules'))
    if max_shifts_rule:
        form.max_shifts_per_week.data = int(max_shifts_rule.value)
    return render_template('rules.html', form=form)

@app.route('/reports')
@login_required
def reports():
    return render_template('reports.html')

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

@app.route('/add_employee', methods=['GET', 'POST'])
@login_required
def add_employee():
    form = EmployeeForm()
    if form.validate_on_submit():
        new_employee = Employee(name=form.name.data, skills=form.skills.data, location=form.location.data, department=form.department.data, role=form.role.data)
        db.session.add(new_employee)
        db.session.commit()
        flash(f"Employee '{form.name.data}' added.", "success")
        return redirect(url_for('employee_management'))
    return render_template('add_employee.html', form=form, title="Add New Employee")

@app.route('/edit_employee/<int:employee_id>', methods=['GET', 'POST'])
@login_required
def edit_employee(employee_id):
    employee = db.get_or_404(Employee, employee_id)
    form = EmployeeForm(obj=employee)
    if form.validate_on_submit():
        form.populate_obj(employee)
        db.session.commit()
        flash(f"Employee '{employee.name}' updated.", "success")
        return redirect(url_for('employee_management'))
    return render_template('add_employee.html', form=form, title=f"Edit {employee.name}")

@app.route('/delete_employee/<int:employee_id>', methods=['POST'])
@login_required
def delete_employee(employee_id):
    employee_to_delete = db.get_or_404(Employee, employee_id)
    db.session.delete(employee_to_delete)
    db.session.commit()
    flash(f"Employee '{employee_to_delete.name}' has been deleted.", "success")
    return redirect(url_for('employee_management'))

@app.route('/add_task', methods=['GET', 'POST'])
@login_required
def add_task():
    form = TaskForm()
    if form.validate_on_submit():
        new_task = Task(name=form.name.data, required_skill=form.required_skill.data, priority=form.priority.data, estimated_time=form.estimated_time.data, deadline=form.deadline.data)
        db.session.add(new_task)
        db.session.commit()
        flash(f"Task '{form.name.data}' added.", "success")
        return redirect(url_for('task_management'))
    return render_template('add_task.html', form=form, title="Add New Task")

@app.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task = db.get_or_404(Task, task_id)
    form = TaskForm(obj=task)
    if form.validate_on_submit():
        form.populate_obj(task)
        db.session.commit()
        flash(f"Task '{task.name}' updated.", "success")
        return redirect(url_for('task_management'))
    return render_template('add_task.html', form=form, title=f"Edit {task.name}")

@app.route('/delete_task_from_mgmt/<int:task_id>', methods=['POST'])
@login_required
def delete_task_from_mgmt(task_id):
    task_to_delete = db.get_or_404(Task, task_id)
    db.session.delete(task_to_delete)
    db.session.commit()
    flash(f"Task '{task_to_delete.name}' deleted.", "success")
    return redirect(url_for('task_management'))

@app.route('/manage_availability/<int:employee_id>', methods=['GET', 'POST'])
@login_required
def manage_availability(employee_id):
    employee = db.get_or_404(Employee, employee_id)
    if request.method == 'POST':
        unavailable_days = request.form.getlist('unavailable')
        employee.unavailable_days = ','.join(unavailable_days)
        db.session.commit()
        flash(f"Availability for {employee.name} updated.", "success")
        return redirect(url_for('employee_management'))
    current_unavailable_days = [d.strip() for d in employee.unavailable_days.split(',')] if employee.unavailable_days else []
    return render_template('manage_availability.html', employee=employee, days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], unavailable=current_unavailable_days)

@app.route('/update_assignment/<int:task_id>', methods=['POST'])
@login_required
def update_assignment(task_id):
    new_employee_id = int(request.form.get('employee_id'))
    preference = db.session.execute(db.select(LearnedPreference).filter_by(employee_id=new_employee_id, task_id=task_id)).scalar_one_or_none()
    if preference:
        preference.score += 1
    else:
        preference = LearnedPreference(employee_id=new_employee_id, task_id=task_id, score=1)
        db.session.add(preference)
    db.session.commit()
    flash("Preference learned! The schedule will be regenerated.", "success")
    return redirect(url_for('schedule_editor'))


# --- Database Initialization ---
with app.app_context():
    db.create_all()
    if not db.session.execute(db.select(User)).scalars().first():
        print("No users found. Creating a default admin user...")
        hashed_password = bcrypt.generate_password_hash('password').decode('utf-8')
        admin_user = User(username='admin', password=hashed_password, role='Admin')
        db.session.add(admin_user)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)

