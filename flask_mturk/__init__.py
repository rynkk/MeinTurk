from flask import Flask, json
from flask_sqlalchemy import SQLAlchemy
from flask_ckeditor import CKEditor
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

import boto3
import os
from .converters import IDConverter

app = Flask(__name__)

app.config['SECRET_KEY'] = 'f03b64dca19c7e6e86b419e8c3abf4db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///batches.db'


app.url_map.converters['awsid'] = IDConverter
# app.config['CKEDITOR_SERVE_LOCAL'] = True
# app.config['CKEDITOR_EXTRA_PLUGINS'] = ['codemirror']
app.config['CKEDITOR_HEIGHT'] = 600


app.config.from_pyfile('settings.cfg')

db = SQLAlchemy(app)
ckeditor = CKEditor(app)


filename = os.path.join(app.instance_path, 'iso3166cc.json')
with open(filename) as f:
    ISO3166 = json.load(f)


filename = os.path.join(app.instance_path, 'system_qualification.json')
with open(filename, encoding='utf-8') as f:
    SYSTEM_QUALIFICATION = json.load(f)

if(app.config.get('SOFTBLOCK_QUALIFICATION_ID') is None):
    print("*** ERROR: SOFTBLOCK_QUALIFICATION_ID in config not set, unable to softblock workers using the CSV import. ***")
    print("*** ABORTING***")
    exit()

MAX_BONUS = app.config.get('MAX_BONUS')
if(MAX_BONUS is None):
    print("*** WARNING: MAX_BONUS in config not set, defaulting to $5.0")
    MAX_BONUS = 5.0

MAX_PAYMENT = app.config.get('MAX_PAYMENT')
if(MAX_PAYMENT is None):
    print("*** WARNING: MAX_PAYMENT in config not set, defaulting to $10.0")
    MAX_PAYMENT = 10.0

# Connect to MTurk-Server

endpoint_url = 'https://mturk-requester-sandbox.us-east-1.amazonaws.com'

# Uncomment this line to use in production
# endpoint_url = 'https://mturk-requester.us-east-1.amazonaws.com'
# connect to mturk client using AWS credentials

client = boto3.client('mturk', endpoint_url=endpoint_url, region_name='us-east-1',
                      aws_access_key_id=app.config['AWS_ACCESS_KEY_ID'],
                      aws_secret_access_key=app.config['AWS_SECRET_ACCESS_KEY'])

if client:
    print(" *** Connected to MTurk-Server *** ")

from flask_mturk import routes
from flask_mturk.models import MiniHIT, MiniGroup

admin = Admin(app, 'Database')


class HITView(ModelView):
    column_display_pk = True
    form_columns = ('id', 'active', 'group_id', 'position', 'workers')


class GroupView(ModelView):
    column_display_pk = True


admin.add_view(HITView(MiniHIT, db.session, 'MiniHIT'))
admin.add_view(GroupView(MiniGroup, db.session, 'MiniGroup'))
