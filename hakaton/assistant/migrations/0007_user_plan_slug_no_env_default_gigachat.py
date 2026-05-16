from django.db import migrations, models


def forwards(apps, schema_editor):
    User = apps.get_model("assistant", "User")
    User.objects.filter(gigachat_plan_slug="env").update(gigachat_plan_slug="gigachat")


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("assistant", "0006_normalize_removed_gigachat_plan_slugs"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
        migrations.AlterField(
            model_name="user",
            name="gigachat_plan_slug",
            field=models.CharField(
                default="gigachat",
                help_text="Модель GigaChat для чата (slug из settings.GIGACHAT_PLAN_OPTIONS).",
                max_length=32,
                verbose_name="GigaChat plan",
            ),
        ),
    ]
