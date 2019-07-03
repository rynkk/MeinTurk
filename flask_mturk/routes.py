from flask import render_template, url_for, flash, redirect, jsonify, json, request
from flask_mturk import app, db, ISO3166, SYSTEM_QUALIFICATION
from flask_mturk.forms import SurveyForm, QualificationsForm, FieldList, FormField, SelectField, QualificationsSubForm, FlaskForm
from flask_mturk.models import MiniGroup, MiniHIT, MiniLink
from datetime import datetime
import time
from apscheduler.schedulers.background import BackgroundScheduler
from .api_calls import api
from .helper import is_number, seconds_from_string


@app.route("/")
@app.route("/dashboard")
def dashboard():
    balance = api.get_balance()
    hits = api.list_all_hits()
    groups = MiniGroup.query.all()
    order = []
    createdhit = request.args.get('createdhit')

    for group in groups:
        batch = {'batch_id': group.group_id, 'hits': []}
        for hit in group.minihits:
            batch['hits'].append({'id': hit.uid, 'workers': hit.workers, 'position': hit.position})
        order.append(batch)
    # TODO: Outsource logic to client?

    return render_template('main/dashboard.html', surveys=hits, ordering=order, balance=balance, createdhit=createdhit)


@app.route("/survey", methods=['GET', 'POST'])
def survey():
    form = SurveyForm()

    percentage_interval = 5
    integer_list = [1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000]
    balance = api.get_balance()

    # we need to dynamically change the allowed options for the qual_select
    all_qualifications = SYSTEM_QUALIFICATION + api.list_custom_qualifications()
    selector_choices = [(qual['QualificationTypeId'], qual["Name"]) for qual in all_qualifications]

    # if post then add choices for each entry of qualifications_select.selects so that form qual_select can validate
    if request.method == "POST":
        for select in form.qualifications_select.selects:
            select.selector.choices = selector_choices

    if form.validate_on_submit():

        # standard fields #
        project_name = form.project_name.data
        title = form.title.data
        description = form.description.data
        keywords = form.keywords.data
        payment_per_worker = str(form.payment_per_worker.data)
        amount_workers = form.amount_workers.data

        html_question_value = """<?xml version="1.0"?><HTMLQuestion xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2011-11-11/HTMLQuestion.xsd"><HTMLContent><![CDATA[<!DOCTYPE html><html><head><title>HIT</title><meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/><script type='text/javascript' src='https://s3.amazonaws.com/mturk-public/externalHIT_v1.js'></script></head><body><form name="mturk_form" method="post" id="mturk_form" action="https://www.mturk.com/mturk/externalSubmit"><input type="hidden" value="" name="assignmentId" id="assignmentId" />"""\
                              + form.editor_field.data \
                              + """<p class="text-center"><input type="submit" id="submitButton" class="btn btn-primary" value="Submit" /></p></form><script language="Javascript">turkSetAssignmentID();</script></body></html>]]></HTMLContent><FrameHeight>0</FrameHeight></HTMLQuestion>"""

        # seconds fields #
        time_till_expiration = form.time_till_expiration.int_field.data * seconds_from_string(form.time_till_expiration.unit_field.data)
        allotted_time_per_worker = form.allotted_time_per_worker.int_field.data * seconds_from_string(form.allotted_time_per_worker.unit_field.data)
        accept_pay_worker_after = form.accept_pay_worker_after.int_field.data * seconds_from_string(form.accept_pay_worker_after.unit_field.data)

        # qualification fields #
        # https://docs.aws.amazon.com/AWSMechTurk/latest/AWSMturkAPI/ApiReference_QualificationRequirementDataStructureArticle.html#CustomQualificationsandSystemQualifications #
        project_visibility = form.project_visibility.data

        qualifications = []
        for select in form.qualifications_select.selects:
            obj = create_qualification_object(select.selector.data, select.first_select.data, select.second_select.data, project_visibility)
            qualifications.append(obj)

        # master and adult qualification fields #
        must_be_master = form.must_be_master.data
        if must_be_master == "yes":
            id = '2ARFPLSP75KLA8M8DH1HTEQVJT3SY6'  # Sandbox
            # id = '2F1QJWKUDD8XADTFD2Q0G6UTO95ALH'  # Production
            obj = create_qualification_object(id, 'Exists', "None", "DiscoverPreviewAndAccept")
            qualifications.append(obj)

        adult_content = form.adult_content.data
        if adult_content:
            id = '00000000000000000060'
            obj = create_qualification_object(id, 'EqualTo', 1, "DiscoverPreviewAndAccept")
            qualifications.append(obj)

        # conditional fields #
        # is_starting_instantly = form.starting_date_set.data # maybe get rid of ability to postpone releases
        # start_date = form.starting_date.data  # convert to right timezone
        is_minibatched = form.minibatch.data
        # minibatch_qualification_name = form.qualification_name.data

        # TODO
        # if(form.minibatch.data and form.qualification_name.data == ""):
        #    now = datetime.datetime.now()
        #    print('This is the qualificationname:' + form.project_name.data + "_" + now.strftime("%Y-%m-%dT%H:%M:%S"))

        if(is_minibatched):
            # TODO create custom minibatch-qualification and add it to the list, make it ActionsGuarded  "DiscoverPreviewAndAccept"
            hit_type_id = api.create_hit_type(accept_pay_worker_after, allotted_time_per_worker, payment_per_worker, title, keywords, description, qualifications)
            hit_id = api.create_hit_with_type(hit_type_id, html_question_value, time_till_expiration, 9, 'batched')['HITId']

            minigroup = MiniGroup(hit_type_id, True, html_question_value, time_till_expiration)
            minihit = MiniHIT(hit_type_id, 1, 9, hit_id)
            minilink = MiniLink(hit_type_id, hit_id)
            db.session.add(minigroup)
            db.session.add(minihit)
            db.session.add(minilink)
            amount_workers_last_hit = amount_workers % 9
            amount_workers_hits = amount_workers - amount_workers_last_hit - 9  # - 9 because we already created one HIT with 9 workers
            print("HitType=", hit_type_id)
            print("Workers total", amount_workers)
            print("Workers minus the last hit", amount_workers_hits + 9)
            print("Workers last hit", amount_workers_last_hit)
            print("adding active minihit to DB")
            amount_full_hits = int(amount_workers_hits / 9)
            for i in range(amount_full_hits):
                print("adding inactive minihit", i + 1, "to DB")
                db.session.add(MiniHIT(hit_type_id, i + 2, 9))

            print("adding last minihit with", amount_workers_last_hit, "workers")
            db.session.add(MiniHIT(hit_type_id, amount_full_hits + 2, amount_workers_last_hit))
            db.session.commit()

        else:
            hit = api.create_hit(amount_workers, accept_pay_worker_after, time_till_expiration, allotted_time_per_worker, payment_per_worker, title, keywords, description, html_question_value, qualifications)
            hit_type_id = hit['HITTypeId']
            hit_id = hit['HITId']

        # flash(f'Survey erstellt für {form.username.data}!', 'success')

        api.get_hit(hit_id)  # This makes the redirect wait until the HIT is actually created in the AWS-Database
        return redirect(url_for('dashboard', createdhit=hit_type_id))
    else:
        flash_errors(form)
    return render_template('main/survey.html', title='Neue Survey', form=form, balance=balance, qualifications=all_qualifications, qualification_percentage_interval=percentage_interval, qualification_integer_list=integer_list, cc_list=ISO3166,)


@app.route("/cleardb")
def cleardb():
    db.drop_all()
    db.create_all()
    return "200 OK"


@app.route("/deletebatch/<awsid:typeid>")
def deletebatch(typeid):
    query = db.session.query(MiniGroup, MiniHIT).filter(MiniGroup.group_id == typeid and MiniHIT.parent_id == typeid).all()
    if not query:
        return "No such Batch"
    group_to_delete = query[0].MiniGroup
    hits_to_delete = []
    for row in query:
        if(row.MiniHIT.uid is None):
            print("HIT was not created yet --- Skipping")
            continue
        hit = api.get_hit(row.MiniHIT.uid)
        if(hit['HITStatus'] == 'Disposed'):
            print("HIT exists locally but not in MTURK-Database --- Skipping")
            continue

        if(hit['HITStatus'] in ['Reviewable', 'Reviewed']):
            print("Queueing %s for deletion" % (row.MiniHIT.uid))
            hits_to_delete.append(row.MiniHIT.uid)
        else:
            print("Tried to delete Batch with active HITs --- Aborting")
            return "Abort"

    print("Deleting queued HITs from MTURK-Database")
    api.delete_hits(hits_to_delete)
    print("Deleting HITs from local Database")
    db.session.delete(group_to_delete)
    db.session.commit()
    return "200 OK"


@app.route('/dashboard/deletehit/<awsid:id>')
def deletehit(id):
    query = db.session.query(MiniHIT).filter(MiniHIT.uid == id).one()

    if(query is not None):
        print("Deleting MiniHit")
        return "MiniHIT deleted"
    try:
        api.get_hit(id)
        api.delete_hit(id)
        return "HIT deleted"
    except api.client.exceptions.RequestError as err:
        return '<h3>' + str(err) + '</h3>'


@app.route('/forcedeleteallhits')
def forcedeleteallhits():
    api.forcedelete_all_hits()
    return "200 OK"


@app.route('/db/delete-queued', methods=['POST'])
def delete_queued_from_db():
    # TODO: test behaviour if trying to delete hit that was created
    group_id = request.args.get('group_id')
    position = request.args.get('position')

    # Deleting requested QUEUED HIT, throws exception if HIT was created already
    to_delete = MiniHIT.query\
        .filter(MiniHIT.parent_id == group_id)\
        .filter(MiniHIT.position == position)\
        .filter(MiniHIT.uid.is_(None)).one()

    db.session.delete(to_delete)

    # We need to correct the indice of the following HITs to maintain database integrity
    to_index = MiniHIT.query\
        .filter(MiniHIT.parent_id == group_id)\
        .filter(MiniHIT.position > position).all()

    for hit in to_index:
        hit.position -= 1

    db.session.commit()
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}


@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    return error


# Helper function to create a qualification object from 4 values #
# https://docs.aws.amazon.com/AWSMechTurk/latest/AWSMturkAPI/ApiReference_QualificationRequirementDataStructureArticle.html #
def create_qualification_object(id, comparator, value, restriction):
    qual_obj = {}
    qual_obj['QualificationTypeId'] = id
    qual_obj['Comparator'] = comparator
    qual_obj['ActionsGuarded'] = restriction

    if value == "None":                   # we are done if second_select did not provide data
        return qual_obj

    if is_number(value):                       # int-> IntegerValues
        int_array = [int(value)]
        qual_obj['IntegerValues'] = int_array
    else:                                       # string-> LocaleValues
        locale_data = {}
        locale_data['Country'] = value
        locale_array = [locale_data]
        qual_obj['LocaleValues'] = locale_array
    return qual_obj


def flash_errors(form):
    for field, errors in form.errors.items():
        print(errors)
        for error in errors:
            flash(u"Error in the %s field - %s" % (
                getattr(form, field).short_name,
                errors
            ))


def update_mini_hits():  # TODO make old MiniHIT paused
    query = db.session.query(MiniGroup, MiniLink, MiniHIT)\
        .filter(MiniGroup.group_id == MiniLink.group_id)\
        .filter(MiniLink.active_hit == MiniHIT.uid)\
        .filter(MiniGroup.active).all()

    for row in query:
        active_hit_uid = row.MiniHIT.uid  # MiniHIT.uid == HITTypeId
        active_hit = api.get_hit(active_hit_uid)
        print("Checking %s with HITStatus %s, from Group %s " % (active_hit_uid, active_hit['HITStatus'], row.MiniGroup.group_id))

        if(active_hit['HITStatus'] == 'Unassignable' or active_hit['HITStatus'] == 'Reviewable'):
            print("Assignment done, creating new one")
            new_position = row.MiniHIT.position + 1
            # Fetching Group-specific data that is shared between MiniHITs and is needed for the new MiniHIT
            hittypeid = row.MiniGroup.group_id
            question = row.MiniGroup.layout
            lifetime = row.MiniGroup.lifetime

            # Getting the new MiniHIT-DB-entry
            new_mini_hit = MiniHIT.query.filter(MiniHIT.position == new_position)\
                                        .filter(MiniHIT.parent_id == hittypeid)\
                                        .one()
            if(new_mini_hit is None):
                print("Actually not creating a new one because we reached the end, setting HITGroup to inactive")
                row.MiniGroup.active = False
                continue
            workers = new_mini_hit.workers

            # Creating a new HIT with the assigned attributes and saving its ID
            new_hit_id = api.create_hit_with_type(hittypeid, question, lifetime, workers, 'batched')['HITId']
            print("Creating hit with id", new_hit_id)
            # Using saved ID to update DB-schema
            new_mini_hit.uid = new_hit_id
            row.MiniLink.active_hit = new_hit_id
    db.session.commit()


db.create_all()

import os
if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':  # Make Scheduler be created once, else it will run twice which will screw up the database
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_mini_hits, 'interval', seconds=15)
    scheduler.start()
