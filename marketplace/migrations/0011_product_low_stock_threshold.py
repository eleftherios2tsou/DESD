from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0010_weeklyordertemplate_weeklyorderitem'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='low_stock_threshold',
            field=models.PositiveIntegerField(
                default=5,
                help_text='Send alert when stock falls below this level',
            ),
        ),
    ]
