from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('qr', '0002_qrcode_owner'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='qrcode',
            name='image_path',
        ),
    ]
