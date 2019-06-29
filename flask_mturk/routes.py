from flask import render_template, url_for, flash, redirect, jsonify, json, request
from flask_mturk import app, db, client, ISO3166, SYSTEM_QUALIFICATION
from flask_mturk.forms import SurveyForm, QualificationsForm, FieldList, FormField, SelectField, QualificationsSubForm, FlaskForm
from flask_mturk.models import MiniGroup, MiniHIT, MiniLink
import datetime
import time
from apscheduler.schedulers.background import BackgroundScheduler


def update_mini_hits():
    query = db.session.query(MiniGroup, MiniLink, MiniHIT.uid, MiniHIT.position)\
        .join(MiniLink, MiniGroup.group_id == MiniLink.group_id)\
        .join(MiniHIT, MiniLink.active_hit == MiniHIT.uid)\
        .filter(MiniGroup.active).all()
    for row in query:
        print(row)        
        active_hit_uid = row.uid  # MiniHIT.uid == HITTypeId
        active_hit = get_hit(active_hit_uid)
        
        if(active_hit['NumberOfAssignmentsAvailable'] == 0):
            print("Assignment done, creating new one")
            new_position = row.position + 1
            # Fetching Group-specific data that is shared between MiniHITs and is needed for the new MiniHIT
            hittypeid = row.MiniGroup.group_id
            question = row.MiniGroup.layout
            lifetime = row.MiniGroup.lifetime

            # Getting the new MiniHIT-DB-entry
            new_mini_hit = MiniHIT.query.filter(MiniHIT.position == new_position and MiniHIT.group_id == hittypeid).first()
            if(new_mini_hit is None):
                MiniGroup.active = False
                db.session.commit()
            workers = new_mini_hit.workers

            # Creating a new HIT with the assigned attributes and saving its ID
            new_hit_id = create_hit_with_type(hittypeid, question, lifetime, workers)['HITId']

            # Using saved ID to update DB-schema
            new_mini_hit.uid = new_hit_id
            row.MiniLink.active_hit = new_hit_id
            db.session.commit()


db.create_all()

scheduler = BackgroundScheduler()
scheduler.add_job(update_mini_hits, 'interval', seconds=30)
scheduler.start()


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


@app.route("/")
@app.route("/dashboard")
def dashboard():
    balance = get_balance()
    hits = list_all_hits()
    return render_template('main/dashboard.html', surveys=hits, balance=balance)


def flash_errors(form):
    for field, errors in form.errors.items():
        print(errors)
        for error in errors:
            flash(u"Error in the %s field - %s" % (
                getattr(form, field).short_name,
                errors
            ))


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
            hit_id = create_hit_with_type(hit_type_id, html_question_value, time_till_expiration, 9, project_name)['HIT']['HITId']

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
        # time.sleep(3)  # wait for mturk endpoint to process the hit

        # flash(f'Survey erstellt für {form.username.data}!', 'success')
        return redirect(url_for('dashboard'))
    else:
        flash_errors(form)
    return render_template('main/survey.html', title='Neue Survey', form=form, balance=balance, qualifications=all_qualifications, qualification_percentage_interval=percentage_interval, qualification_integer_list=integer_list, cc_list=ISO3166,)


def create_hit_minibatch():
    # TODO
    pass


def create_hit_standard():
    # TODO
    pass


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
    )
    return response


def create_hit_with_type(hittypeid, question, lifetime, max, reqanno=""):
    response = client.create_hit_with_hit_type(
        HITTypeId=hittypeid,
        MaxAssignments=max,
        LifetimeInSeconds=lifetime,
        Question=question,
        RequesterAnnotation=reqanno
    )
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
