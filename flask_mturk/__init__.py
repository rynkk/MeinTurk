from flask import Flask, json
from flask_sqlalchemy import SQLAlchemy
from flask_ckeditor import CKEditor
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_babel import Babel

import boto3
import os
from .converters import IDConverter

app = Flask(__name__)

app.config['SECRET_KEY'] = 'f03b64dca19c7e6e86b419e8c3abf4db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///batches.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.url_map.converters['awsid'] = IDConverter
app.config['CKEDITOR_HEIGHT'] = 600


app.config.from_pyfile('settings.cfg')
babel = Babel(app)
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
    print("*** ABORTING ***")
    exit()

if(app.config.get('MAX_BONUS') is None):
    print("*** WARNING: MAX_BONUS in config not set, defaulting to $5.0 ***")
    app.config['MAX_BONUS'] = 5.0

if(app.config.get('MAX_PAYMENT') is None):
    print("*** WARNING: MAX_PAYMENT in config not set, defaulting to $10.0 ***")
    app.config['MAX_PAYMENT'] = 10.0

if(app.config.get('DEFAULT_REJECTION_MESSAGE ') is None):
    print("*** WARNING: DEFAULT_REJECTION_MESSAGE in config not set, using default text: 'Sorry, your answer did not match our quality standards' ***")
    app.config['DEFAULT_REJECTION_MESSAGE'] = 'Sorry, your answer did not match our quality standards'

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

__all__ = ['routes', ]

from flask_mturk.models import MiniHIT, MiniGroup, HiddenHIT, CachedAnswer, Worker

admin = Admin(app, 'Database')


class HITView(ModelView):
    column_display_pk = True
    form_columns = ('id', 'status', 'group_id', 'position', 'workers')


class GroupView(ModelView):
    column_exclude_list = ('layout')
    column_display_pk = True


class HiddenView(ModelView):
    column_display_pk = True
    form_columns = ('id',)


class AnswerView(ModelView):
    column_display_pk = True


class WorkerView(ModelView):
    column_display_pk = True


admin.add_view(WorkerView(Worker, db.session, 'Worker'))
admin.add_view(HITView(MiniHIT, db.session, 'MiniHIT'))
admin.add_view(GroupView(MiniGroup, db.session, 'MiniGroup'))
admin.add_view(HiddenView(HiddenHIT, db.session, 'HiddenHIT'))
admin.add_view(AnswerView(CachedAnswer, db.session, 'CachedAnswer'))
