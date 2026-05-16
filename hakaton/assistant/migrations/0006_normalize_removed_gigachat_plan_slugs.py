from django.db import migrations

ALLOWED_SLUGS = frozenset({"env", "gigachat", "gigachat-pro", "gigachat-max"})


def forwards(apps, schema_editor):
    User = apps.get_model("assistant", "User")
    User.objects.exclude(gigachat_plan_slug__in=ALLOWED_SLUGS).update(gigachat_plan_slug="env")


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("assistant", "0005_user_gigachat_plan_slug"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
