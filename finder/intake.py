"""Optional host-owned academic inputs for eligibility/draft demonstrations.

Ordinary conversation and opportunity browsing do not use a form.
"""
from __future__ import annotations

from typing import get_args

from pydantic import ValidationError

from .models import City, Major, Student

MAJORS = get_args(Major)
CITIES = get_args(City)
DETAIL_FIELDS = ("year", "gpa", "training_kind", "required_months", "available_from")
FIELD_PROMPTS = {
    "year": "Study year (1-6)",
    "gpa": "GPA on a 4-point scale (0-4; do not enter a 5-point GPA)",
    "training_kind": "Training type (coop or summer)",
    "required_months": "Required duration in months (1-12)",
    "available_from": "Available from (YYYY-MM-DD)",
}


def choose(label, options, read=None):
    read = read or input
    print(label + ": " + " | ".join(f"{i}. {value}" for i, value in enumerate(options, 1)))
    while True:
        value = read(label + " (number or full name): ").strip()
        if value.isascii() and value.isdigit() and 1 <= int(value) <= len(options):
            return options[int(value) - 1]
        match = next((option for option in options if option.casefold() == value.casefold()), None)
        if match:
            return match
        print("Please choose one of the listed options; no value has been assumed.")


def new_student(major=None):
    # S000 is an anonymous local session label, never a loaded test fixture.
    # Each interactive session gets its own database directory in app.py.
    return Student(id="S000", major=major)


def collect_details(student, read=None):
    read = read or input
    raw = student.model_dump(mode="json")
    print("Enter fictional details for this demo. Enter keeps the current value; 'clear' removes it.")
    if student.major is None:
        raw["major"] = choose("Major", MAJORS, read)
    for field in DETAIL_FIELDS:
        while True:
            current = raw[field] if raw[field] is not None else "unknown"
            value = read(f"{FIELD_PROMPTS[field]} [{current}]: ").strip()
            if not value:
                break
            candidate = {**raw, field: None if value.lower() == "clear" else value}
            try:
                raw = Student.model_validate(candidate).model_dump(mode="json")
                break
            except ValidationError:
                print("Invalid value. Use the displayed range/format, or press Enter to leave it unchanged.")
    return Student.model_validate(raw)
