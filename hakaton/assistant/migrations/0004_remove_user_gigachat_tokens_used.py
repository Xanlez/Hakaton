# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("assistant", "0003_user_gigachat_tokens_used"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="gigachat_tokens_used",
        ),
    ]
