import os
import re
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Capstone.settings')
django.setup()

import openpyxl
from main.models import Course
#To run this script for a different course sheet -> import_courses.py <path_to_spreadsheet>
def parse_course(val):
    s = str(val).strip()
    if re.match(r'^\d+\s*[--]\s*\d+$', s):
        return None
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None

def import_courses(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active
    imported = 0
    skipped = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        code, title, credits_raw, description = row[0], row[1], row[2], row[3]
        if code is None or title is None:
            continue
        credits = parse_course(credits_raw)
        if credits is None:
            skipped.append((code, title, credits_raw))
            continue
        Course.objects.update_or_create(
            course_code=str(code).strip(),
            defaults={
               'course_name': str(title).strip(),
               'course_credits' : credits,
               'course_details' : str(description).strip() if description else '',
            }
        )
        imported += 1
    print(f"Imported {imported} courses.")
    print(f"Skipped {len(skipped)} courses with credit ranges:")
    for code, title, raw in skipped:
        print(f"  {code} - {title} (credits: {raw!r})")
if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python import_courses.py path/to/catalog.xlsx")
        sys.exit(1)
    import_courses(sys.argv[1])