"""Education system — training, AI tutorials, skills, certification."""

from __future__ import annotations

from app.civilization import repository as civ_repo

COURSE_CATALOG = [
    {"title": "Aura Platform Fundamentals", "type": "training", "skills": ["platform_ops"]},
    {"title": "AI Agent Collaboration", "type": "tutorial", "skills": ["ai_literacy", "coordination"]},
    {"title": "Governance & Compliance", "type": "training", "skills": ["governance"]},
    {"title": "Customer Success Excellence", "type": "training", "skills": ["customer_success"]},
    {"title": "Data Security Essentials", "type": "tutorial", "skills": ["security"]},
]


def enroll_employee(company_id: int, employee_key: str, course_title: str, course_type: str = "training") -> dict:
    training = civ_repo.create_training(company_id, employee_key, course_title, course_type)
    civ_repo.log_civ_action(company_id, "education.enroll", details=f"{employee_key}:{course_title}")
    return training


def enroll_from_catalog(company_id: int, employee_key: str) -> list[dict]:
    enrolled = []
    for course in COURSE_CATALOG[:3]:
        enrolled.append(enroll_employee(company_id, employee_key, course["title"], course["type"]))
        for skill in course.get("skills", []):
            civ_repo.upsert_skill(company_id, employee_key, skill, 1.0, course["type"])
    return enrolled


def advance_training(company_id: int, training_id: int, progress: float) -> dict | None:
    result = civ_repo.update_training_progress(company_id, training_id, progress)
    if result and result.get("certified"):
        civ_repo.create_certification(
            company_id,
            result["employee_key"],
            f"Certified: {result['course_title']}",
        )
        civ_repo.log_civ_action(company_id, "education.certify", details=result["course_title"])
    return result


def track_skill(company_id: int, employee_key: str, skill_name: str, level: float, category: str = "general") -> dict:
    skill = civ_repo.upsert_skill(company_id, employee_key, skill_name, level, category)
    civ_repo.log_civ_action(company_id, "education.skill", details=f"{employee_key}:{skill_name}")
    return skill


def education_summary(company_id: int) -> dict:
    training = civ_repo.list_training(company_id)
    skills = civ_repo.list_skills(company_id)
    certs = civ_repo.list_certifications(company_id)
    completed = [t for t in training if t.get("status") == "completed"]
    tutorials = [t for t in training if t.get("course_type") == "tutorial"]

    return {
        "catalog": COURSE_CATALOG,
        "training": training[:20],
        "skills": skills[:20],
        "certifications": certs[:20],
        "totals": {
            "enrolled": len(training),
            "completed": len(completed),
            "tutorials": len(tutorials),
            "skills_tracked": len(skills),
            "certifications": len(certs),
        },
    }
