
from django.db import migrations


def add_review_tags(apps, schema_editor):
    ReviewTag = apps.get_model('main', 'ReviewTag')

    tags = [
        "Tough Grader",
        "Took for Fun",
        "Heavy Workload",
        "Easy A",
        "Attendance Mandatory",
        "Helpful Professor",
        "Lots of Homework",
        "Exam Heavy",
        "Interesting Content",
        "Would Recommend"
    ]

    for tag in tags:
        ReviewTag.objects.get_or_create(tag_name=tag)


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0006_reviewtag_review_review_tags'),
    ]

    operations = [
        migrations.RunPython(add_review_tags, migrations.RunPython.noop),
    ]
