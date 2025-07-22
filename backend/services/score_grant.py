from datetime import datetime, date

def score_grant(user, grant): #user in json, grant in json
    score = 0 
    if user["user_type"] in grant["target_group"]:
        score += 25
    if user["location"] in grant["location_eligible"]:
        score += 25
    if user["major"] in grant["sectors"] or any(i in grant["sectors"] for i in user["interests"]):
        score += 20
    if user["race"].lower() in [r.lower() for r in grant["eligibility_criteria"]]:
        score += 20
    raw_deadline = grant["deadline"]
    if raw_deadline:
        try:
            deadline_date = datetime.strptime(raw_deadline, "%Y-%m-%d").date()
            if deadline_date >= date.today():
                score += 10
        except ValueError:
            pass  # ignore if invalid format
    else:
        score += 10
    if any(interest.lower() in grant["description"].lower() for interest in user["interests"]):
        score += 15
    return score

