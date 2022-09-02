from bcse_app import models
from datetime import datetime, timedelta
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
from django.core import management
from django.utils import timezone
import subprocess

def backup_db():
  print('start db backup', datetime.today())
  #remove old backups from the file system
  #cmd = 'rm %s/*'% settings.DBBACKUP_STORAGE_OPTIONS['location']
  #subprocess.call(cmd, shell=True)
  management.call_command('dbbackup', '--compress')
  '''cmd = 's3cmd --access_key=%s --secret_key=%s -s put %s/default-* s3://%s' % (settings.AWS_ACCESS_KEY_ID,
                                                                               settings.AWS_SECRET_ACCESS_KEY,
                                                                               settings.DBBACKUP_STORAGE_OPTIONS['location'],
                                                                              settings.DBBACKUP_AWS_S3_BUCKET)
  '''
  #subprocess.call(cmd, shell=True)
  print('end db backup', datetime.today())

