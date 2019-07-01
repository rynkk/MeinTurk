from flask import render_template, url_for, flash, redirect, jsonify, json, request
from flask_mturk import app, db, client, ISO3166, SYSTEM_QUALIFICATION
from flask_mturk.forms import SurveyForm, QualificationsForm, FieldList, FormField, SelectField, QualificationsSubForm, FlaskForm
from flask_mturk.models import MiniGroup, MiniHIT, MiniLink
from datetime import datetime
import time
from apscheduler.schedulers.background import BackgroundScheduler


@app.route("/")
@app.route("/dashboard")
def dashboard():
    #for row in db.session.query(MiniHIT).all():
    #    print(row)
    balance = get_balance()
    hits = list_all_hits()
    return render_template('main/dashboard.html', surveys=hits, balance=balance)


@app.route("/survey", methods=['GET', 'POST'])
def survey():
    form = SurveyForm()

    percentage_interval = 5
    integer_list = [1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000]
    balance = get_balance()

    # we need to dynamically change the allowed options for the qual_select
    all_qualifications = SYSTEM_QUALIFICATION + list_custom_qualifications()
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
            hit_type_id = create_hit_type(accept_pay_worker_after, allotted_time_per_worker, payment_per_worker, title, keywords, description, qualifications)
            hit_id = create_hit_with_type(hit_type_id, html_question_value, time_till_expiration, 9, "batched")['HITId']

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
            create_hit(amount_workers, accept_pay_worker_after, time_till_expiration, allotted_time_per_worker, payment_per_worker, title, keywords, description, html_question_value, qualifications, project_name)
        return redirect(url_for('dashboard'))
    else:
        flash_errors(form)
    return render_template('main/survey.html', title='Neue Survey', form=form, balance=balance, qualifications=all_qualifications, qualification_percentage_interval=percentage_interval, qualification_integer_list=integer_list, cc_list=ISO3166,)


@app.route("/cleardb")
def cleardb():
    db.drop_all()
    db.create_all()
    return "cleared"


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
        hit = get_hit(row.MiniHIT.uid)
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
    delete_hits(hits_to_delete)
    print("Deleting HITs from local Database")
    db.session.delete(group_to_delete)
    db.session.commit()
    return "OK"


@app.route('/dashboard/deletehit/<awsid:id>')
def deletehit(id):
    query = db.session.query(MiniHIT).filter(MiniHIT.uid == id).first()

    if(query is not None):
        print("Deleting MiniHit")
        return "MiniHIT deleted"
    try:
        get_hit(id)
        delete_hit(id)
        return "HIT deleted"
    except client.exceptions.RequestError as err:
        return '<h3>' + str(err) + '</h3>'


@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    return error


def get_hit(hitid):
    response = client.get_hit(HITId=hitid)['HIT']
    return response


def create_hit(max, autoacc, lifetime, duration, reward, title, keywords, desc, question, qualreq, reqanno=""):
    response = client.create_hit(
        MaxAssignments=max,
        AutoApprovalDelayInSeconds=autoacc,
        LifetimeInSeconds=lifetime,
        AssignmentDurationInSeconds=duration,
        Reward=reward,
        Title=title,
        Keywords=keywords,
        Description=desc,
        Question=question,
        RequesterAnnotation=reqanno,
        QualificationRequirements=qualreq
    )['HIT']
    return response


def create_hit_with_type(hittypeid, question, lifetime, max, reqanno=""):
    response = client.create_hit_with_hit_type(
        HITTypeId=hittypeid,
        MaxAssignments=max,
        LifetimeInSeconds=lifetime,
        Question=question,
        RequesterAnnotation=reqanno
    )['HIT']
    return response


def create_hit_type(autoapp, duration, reward, title, keywords, desc, qualreq):
    response = client.create_hit_type(
        AutoApprovalDelayInSeconds=autoapp,
        AssignmentDurationInSeconds=duration,
        Reward=reward,
        Title=title,
        Keywords=keywords,
        Description=desc,
        QualificationRequirements=qualreq
    )
    return response['HITTypeId']


def get_balance():
    return client.get_account_balance()['AvailableBalance']


def list_all_hits():
    result = []
    paginator = client.get_paginator('list_hits')
    pages = paginator.paginate(PaginationConfig={'PageSize': 100})
    for page in pages:
        result += page['HITs']
    return result


def delete_hit(hit_id):
    return client.delete_hit(HITId=hit_id)


def delete_hits(hit_ids):
    for id in hit_ids:
        delete_hit(id)


def delete_minihits(hit_type_id):
    # DB QUERY UIDS AND DELETE EACH
    pass


def list_custom_qualifications():
    result = []
    paginator = client.get_paginator('list_qualification_types')
    pages = paginator.paginate(
        MustBeRequestable=False,
        MustBeOwnedByCaller=True,
        PaginationConfig={'PageSize': 100}
    )
    for page in pages:
        result += page['QualificationTypes']
    return result


def expire_hit(hit_id):
    client.update_expiration_for_hit(HITId=hit_id, ExpireAt=datetime(2015, 1, 1))


def forcedelete_hit(hit_id):
    expire_hit(hit_id)
    time.sleep(5)
    delete_hit(hit_id)


@app.route("/forcedelete_all_hits")
def forcedelete_all_hits():
    all_hits = list_all_hits()
    if(not all_hits):
        return "nothing to delete"

    print("**********EXPIRING HITS**********")
    for obj in all_hits:
        print("EXPIRING HIT with ID:", obj['HITId'])
        expire_hit(obj['HITId'])

    print("**********DELETING HITS**********")
    for obj in all_hits:
        if(obj['HITStatus'] == 'Reviewable'):
            print("Deleteing HIT with ID:", obj['HITId'])
            delete_hit(obj['HITId'])
        else:
            print("ERROR: HIT %s IS NOT EXPIRED" % (obj['HITId']))

    return "Done"


def flash_errors(form):
    for field, errors in form.errors.items():
        print(errors)
        for error in errors:
            flash(u"Error in the %s field - %s" % (
                getattr(form, field).short_name,
                errors
            ))


# Helper function to convert timeunit to int #
def seconds_from_string(string):
    if string == 'minutes':
        return 60
    if string == 'hours':
        return 60 * 60
    if string == 'days':
        return 24 * 60 * 60
    return -1


# Helper function to check if string is integer #
def is_number(string):
    try:
        int(string)
        return True
    except ValueError:
        return False


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


def update_mini_hits():  # TODO make old MiniHIT paused
    query = db.session.query(MiniGroup, MiniLink, MiniHIT)\
        .filter(MiniGroup.group_id == MiniLink.group_id)\
        .filter(MiniLink.active_hit == MiniHIT.uid)\
        .filter(MiniGroup.active).all()
    
    for row in query:
        active_hit_uid = row.MiniHIT.uid  # MiniHIT.uid == HITTypeId
        active_hit = get_hit(active_hit_uid)
        # print("Checking %s with HITStatus %s, from Group %s " % (active_hit_uid, active_hit['HITStatus'], row.MiniGroup.group_id))

        if(active_hit['HITStatus'] == 'Unassignable' or active_hit['HITStatus'] == 'Reviewable'):
            # print("Assignment done, creating new one")
            new_position = row.MiniHIT.position + 1
            # Fetching Group-specific data that is shared between MiniHITs and is needed for the new MiniHIT
            hittypeid = row.MiniGroup.group_id
            question = row.MiniGroup.layout
            lifetime = row.MiniGroup.lifetime

            # Getting the new MiniHIT-DB-entry
            new_mini_hit = MiniHIT.query.filter(MiniHIT.position == new_position)\
                                        .filter(MiniHIT.parent_id == hittypeid)\
                                        .first()
            if(new_mini_hit is None):
                # print("Actually not creating a new one because we reached the end, setting HITGroup to inactive")
                row.MiniGroup.active = False
                continue
            workers = new_mini_hit.workers

            # Creating a new HIT with the assigned attributes and saving its ID
            new_hit_id = create_hit_with_type(hittypeid, question, lifetime, workers, "batched")['HITId']
            # print("Creating hit with id", new_hit_id)
            # Using saved ID to update DB-schema
            new_mini_hit.uid = new_hit_id
            row.MiniLink.active_hit = new_hit_id
        db.session.commit()


db.create_all()

import os
if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':  # Make Scheduler be created once, else it will run twice which will screw up the database
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_mini_hits, 'interval', seconds=5)
    scheduler.start()
