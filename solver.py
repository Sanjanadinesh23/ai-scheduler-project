from ortools.sat.python import cp_model

def generate_schedule(employees, tasks, days, shifts, preferences, rules):
    """
    Generates a weekly work schedule using Google OR-Tools.
    This version incorporates custom rules like max shifts per week.
    """
    model = cp_model.CpModel()

    # --- Create Variables ---
    assignment = {}
    for emp in employees:
        for day in days:
            for shift in shifts:
                for task in tasks:
                    assignment[(emp['id'], day, shift, task['id'])] = model.NewBoolVar(f"assign_e{emp['id']}_d{day}_s{shift}_t{task['id']}")

    # --- Add Constraints ---

    # Each task can be assigned to AT MOST one employee.
    for task in tasks:
        model.AddAtMostOne(
            assignment[(emp['id'], day, shift, task['id'])]
            for emp in employees for day in days for shift in shifts
        )

    # An employee must have the required skill for a task.
    for emp in employees:
        for day in days:
            for shift in shifts:
                for task in tasks:
                    if task['required_skill'] not in emp['skills']:
                        model.Add(assignment[(emp['id'], day, shift, task['id'])] == 0)

    # An employee cannot be scheduled on their unavailable days.
    for emp in employees:
        for day in emp['unavailable_days']:
            if day in days:
                for shift in shifts:
                    for task in tasks:
                        model.Add(assignment[(emp['id'], day, shift, task['id'])] == 0)

    # Each employee can do at most one task per shift.
    for emp in employees:
        for day in days:
            for shift in shifts:
                model.AddAtMostOne(
                    assignment[(emp['id'], day, shift, task['id'])] for task in tasks
                )
    
    # NEW: Enforce the "Max Shifts Per Week" rule.
    max_shifts = rules.get('max_shifts_per_week', 7) # Default to 7 if rule not found
    for emp in employees:
        total_shifts_for_employee = []
        for day in days:
            for shift in shifts:
                for task in tasks:
                    total_shifts_for_employee.append(assignment[(emp['id'], day, shift, task['id'])])
        model.Add(sum(total_shifts_for_employee) <= max_shifts)


    # --- Define the GOAL (Objective) ---
    model.Maximize(
        sum(
            assignment[(emp['id'], day, shift, task['id'])] * task['priority']
            for emp in employees for day in days for shift in shifts for task in tasks
        )
        +
        sum(
            assignment[(emp['id'], day, shift, task['id'])] * preferences.get((emp['id'], task['id']), 0)
            for emp in employees for day in days for shift in shifts for task in tasks
        )
    )

    # --- Solve the Model ---
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    # --- Extract and Return the Solution ---
    schedule = []
    assigned_task_ids = set()
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        for day in days:
            for shift in shifts:
                for emp in employees:
                    for task in tasks:
                        if solver.Value(assignment[(emp['id'], day, shift, task['id'])]) == 1:
                            schedule.append({
                                "day": day, "shift": shift,
                                "employee_id": emp['id'],
                                "employee_name": emp['name'],
                                "task_id": task['id'],
                                "task_name": task['name']
                            })
                            assigned_task_ids.add(task['id'])
        
        all_task_ids = {t['id'] for t in tasks}
        unscheduled_task_ids = all_task_ids - assigned_task_ids
        unscheduled_tasks = [t for t in tasks if t['id'] in unscheduled_task_ids]
        
        return schedule, unscheduled_tasks
    else:
        return [], tasks
