import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProducerProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('business_name', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('address', models.TextField()),
                ('postcode', models.CharField(max_length=10)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='producer_profile',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),

        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('slug', models.SlugField(unique=True)),
                ('description', models.TextField(blank=True)),
            ],
            options={
                'verbose_name_plural': 'categories',
            },
        ),

        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('price', models.DecimalField(decimal_places=2, max_digits=8)),
                ('stock', models.PositiveIntegerField(default=0)),
                ('allergens', models.TextField(blank=True, help_text='List any allergens, e.g. "Contains nuts"')),
                ('is_organic', models.BooleanField(default=False)),
                ('harvest_date', models.DateField(blank=True, null=True)),
                ('best_before', models.DateField(blank=True, null=True)),
                ('farm_origin', models.CharField(blank=True, max_length=200)),
                ('is_seasonal', models.BooleanField(default=False)),
                ('seasonal_months', models.CharField(blank=True, help_text='e.g. June, July, August', max_length=200)),
                ('lead_time_hours', models.PositiveIntegerField(default=48, help_text='Minimum order lead time in hours')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('producer', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='products',
                    to='marketplace.producerprofile',
                )),
                ('category', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='products',
                    to='marketplace.category',
                )),
            ],
        ),
    ]
