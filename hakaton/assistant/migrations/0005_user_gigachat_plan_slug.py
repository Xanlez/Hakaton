# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assistant", "0004_remove_user_gigachat_tokens_used"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="gigachat_plan_slug",
            field=models.CharField(
                default="env",
                help_text='Режим GigaChat: slug из settings.GIGACHAT_PLAN_OPTIONS. «env» = scope/model как в .env.',
                max_length=32,
            ),
        ),
    ]
