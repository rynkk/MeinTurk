from flask import Flask, json
from flask_sqlalchemy import SQLAlchemy
from flask_ckeditor import CKEditor
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_babel import Babel

import boto3
import os
import logging
import logging.config
from .converters import IDConverter

app = Flask(__name__)

app.config['SECRET_KEY'] = 'f03b64dca19c7e6e86b419e8c3abf4db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///batches.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['CKEDITOR_HEIGHT'] = 600
app.url_map.converters['awsid'] = IDConverter

app.config.from_pyfile('settings.cfg')

babel = Babel(app)
db = SQLAlchemy(app)
ckeditor = CKEditor(app)

with open(os.path.join(app.root_path, "logger.cfg"), "r") as f:
    logging.config.dictConfig(json.load(f))

logging.getLogger('apscheduler').setLevel(logging.WARNING)
logger = logging.getLogger('init')
filename = os.path.join(app.instance_path, 'iso3166cc.json')
with open(filename) as f:
    ISO3166 = json.load(f)

filename = os.path.join(app.instance_path, 'system_qualification.json')
with open(filename, encoding='utf-8') as f:
    SYSTEM_QUALIFICATION = json.load(f)

if(app.config.get('SOFTBLOCK_QUALIFICATION_ID') is None):
    logger.critical("*** ERROR: SOFTBLOCK_QUALIFICATION_ID in config not set, unable to softblock workers using the CSV import. ***")
    logger.critical("*** ABORTING ***")
    exit()

if(app.config.get('MAX_BONUS') is None):
    logger.warning("*** WARNING: MAX_BONUS in config not set, defaulting to $5.0 ***")
    app.config['MAX_BONUS'] = 5.0

if(app.config.get('MAX_PAYMENT') is None):
    logger.warning("*** WARNING: MAX_PAYMENT in config not set, defaulting to $10.0 ***")
    app.config['MAX_PAYMENT'] = 10.0

if(app.config.get('DEFAULT_REJECTION_MESSAGE') is None):
    logger.warning("*** WARNING: DEFAULT_REJECTION_MESSAGE in config not set, using default text: 'Sorry, your answer did not match our quality standards' ***")
    app.config['DEFAULT_REJECTION_MESSAGE'] = 'Sorry, your answer did not match our quality standards'

# Connect to MTurk-Server
if app.config.get('SANDBOX') is None:
    logger.warning("*** WARNING: SANDBOX in config not set, default to True ***")
    logger.warning("*** Sandbox mode activated - Using the MTurk Sandbox server ***")
    endpoint_url = 'https://mturk-requester-sandbox.us-east-1.amazonaws.com'
elif app.config.get('SANDBOX') is True:
    logger.warning("*** Sandbox mode activated - Using the MTurk Sandbox server ***")
    endpoint_url = 'https://mturk-requester-sandbox.us-east-1.amazonaws.com'
elif app.config.get('SANDBOX') is False:
    logger.warning("*** Production mode activated - Using the live MTurk server ***")
    endpoint_url = 'https://mturk-requester.us-east-1.amazonaws.com'
else:
    logger.critical("*** ERROR: SANDBOX in config has invalid value, must be either True or False. ***")
    logger.critical("*** ABORTING ***")
    exit()


# connect to mturk client using AWS credentials

client = boto3.client('mturk', endpoint_url=endpoint_url, region_name='us-east-1',
                      aws_access_key_id=app.config['AWS_ACCESS_KEY_ID'],
                      aws_secret_access_key=app.config['AWS_SECRET_ACCESS_KEY'])

if client:
    logger.info(" *** Connected to MTurk-Server *** ")

from flask_mturk import routes

__all__ = ['routes', ]

from flask_mturk.models import MiniHIT, MiniGroup, TrackedHIT, CachedAnswer, Worker

admin = Admin(app, 'Database')


class HITView(ModelView):
    column_display_pk = True
    form_columns = ('id', 'status', 'group_id', 'position', 'workers')


class GroupView(ModelView):
    column_exclude_list = ('layout')
    column_display_pk = True


class TrackedView(ModelView):
    column_display_pk = True
    form_columns = ('id', 'active', 'hidden')


class AnswerView(ModelView):
    column_display_pk = True


class WorkerView(ModelView):
    column_display_pk = True


admin.add_view(WorkerView(Worker, db.session, 'Worker'))
admin.add_view(HITView(MiniHIT, db.session, 'MiniHIT'))
admin.add_view(GroupView(MiniGroup, db.session, 'MiniGroup'))
admin.add_view(TrackedView(TrackedHIT, db.session, 'TrackedHIT'))
admin.add_view(AnswerView(CachedAnswer, db.session, 'CachedAnswer'))
