# Generated by Django 2.2.2 on 2019-06-25 16:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Leagues', '0007_auto_20190625_1113'),
    ]

    operations = [
        migrations.AddField(
            model_name='division',
            name='abbreviation',
            field=models.CharField(default='<', max_length=2),
        ),
        migrations.AddField(
            model_name='league',
            name='abbreviation',
            field=models.CharField(default=1, max_length=2),
            preserve_default=False,
        ),
    ]
