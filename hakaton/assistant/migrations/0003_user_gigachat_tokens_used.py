# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assistant", "0002_pending_token_digest_encryption"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="gigachat_tokens_used",
            field=models.PositiveBigIntegerField(
                default=0,
                help_text="Накопленная сумма usage.total_tokens по ответам GigaChat для этого аккаунта.",
                verbose_name="GigaChat tokens used",
            ),
        ),
    ]
