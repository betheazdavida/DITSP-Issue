# Generated by Django 2.0.2 on 2018-04-16 06:54

import complaintManager.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Complaint',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(max_length=500)),
                ('status', models.CharField(choices=[('S', 'Submitted'), ('P', 'On Progress'), ('F', 'Finished')], default='S', max_length=5)),
                ('priority', models.PositiveIntegerField(default=1)),
                ('reported', models.DateTimeField(default=django.utils.timezone.now)),
                ('is_public', models.BooleanField()),
            ],
        ),
        migrations.CreateModel(
            name='ComplaintImages',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('src', models.ImageField(upload_to=complaintManager.models.get_upload_path_images)),
                ('complaint', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='complaintManager.Complaint')),
            ],
        ),
        migrations.CreateModel(
            name='Division',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=10)),
                ('name', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='Location',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('lat', models.FloatField()),
                ('lon', models.FloatField()),
            ],
        ),
        migrations.CreateModel(
            name='Log',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(auto_now_add=True)),
                ('description', models.TextField(max_length=500)),
                ('kind', models.CharField(choices=[('G', 'Umum'), ('C', 'Pembuatan'), ('MD', 'Penandaan Selesai'), ('MP', 'Penandaan Progress'), ('AW', 'Penambahan Pekerja'), ('AC', 'Perubahan oleh Admin'), ('ACRMD', 'Perubahan oleh Admin, yang Menghilangkan Penandaan Selesai')], default='G', max_length=10)),
                ('complaint', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='complaintManager.Complaint')),
                ('creator', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Member',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone', models.CharField(default='', max_length=20)),
                ('additional_division', models.ManyToManyField(to='complaintManager.Division')),
            ],
        ),
        migrations.CreateModel(
            name='Origin',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=10)),
                ('name', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=10)),
                ('name', models.CharField(max_length=50)),
                ('divisions', models.ManyToManyField(to='complaintManager.Division')),
                ('origin', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='complaintManager.Origin')),
            ],
        ),
        migrations.CreateModel(
            name='Worker',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('complaint', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='complaintManager.Complaint')),
                ('division', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='complaintManager.Division')),
            ],
        ),
        migrations.AddField(
            model_name='member',
            name='role',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='complaintManager.Role'),
        ),
        migrations.AddField(
            model_name='member',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='complaintimages',
            name='log',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='complaintManager.Log'),
        ),
        migrations.AddField(
            model_name='complaint',
            name='assigned_divisions',
            field=models.ManyToManyField(blank=True, to='complaintManager.Division'),
        ),
        migrations.AddField(
            model_name='complaint',
            name='leader',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='leader', to='complaintManager.Division'),
        ),
        migrations.AddField(
            model_name='complaint',
            name='location',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='complaintManager.Location'),
        ),
        migrations.AddField(
            model_name='complaint',
            name='member',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='complaintManager.Member'),
        ),
    ]
