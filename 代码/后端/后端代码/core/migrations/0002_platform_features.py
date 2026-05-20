from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='detectiontask',
            name='batch_session_id',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
        migrations.AddField(
            model_name='detectiontask',
            name='detection_mode',
            field=models.CharField(blank=True, default='fast', max_length=16),
        ),
        migrations.CreateModel(
            name='DetectionModelConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=64, unique=True)),
                ('value', models.JSONField(default=dict)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='UserReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('target_type', models.CharField(choices=[('manual_review', '人工审核任务'), ('detection_task', '检测任务'), ('feedback', '评论')], default='manual_review', max_length=32)),
                ('target_id', models.IntegerField()),
                ('report_type', models.CharField(default='violation', max_length=64)),
                ('reason', models.TextField()),
                ('status', models.CharField(choices=[('pending', '待处理'), ('resolved', '已处理'), ('dismissed', '已驳回')], default='pending', max_length=20)),
                ('admin_resolution', models.TextField(blank=True, default='')),
                ('handled_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.localtime)),
                ('handled_by', models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name='reports_handled', to='core.user')),
                ('reporter', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='reports_filed', to='core.user')),
            ],
        ),
        migrations.AddIndex(
            model_name='userreport',
            index=models.Index(fields=['status', 'created_at'], name='ur_status_created_idx'),
        ),
    ]
