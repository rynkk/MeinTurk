from flask import render_template, url_for, flash, redirect, jsonify, json, request, abort, Response
from flask_mturk import app, db, ISO3166, SYSTEM_QUALIFICATION, MAX_BONUS
from flask_mturk.forms import SurveyForm, QualificationsForm, FieldList, FormField, SelectField, QualificationsSubForm, FlaskForm, UploadForm
from flask_mturk.models import MiniGroup, MiniHIT
import csv
import io
import datetime
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

    # Often the API is not quick enough and does not add the created HIT
    # to the list_all_hits, so if it is not there yet we need to add it manually
    createdhit = request.args.get('createdhit')
    if(createdhit is not None):
        new_hit = api.get_hit(createdhit)
        if new_hit not in hits:
            hits.append(new_hit)

    for group in groups:
        batch = {'batch_id': group.id, 'hits': []}
        for hit in group.minihits:
            batch['hits'].append({'id': hit.id, 'workers': hit.workers, 'position': hit.position})
        order.append(batch)
    # TODO: Outsource logic to client?

    uform = UploadForm()

    return render_template('main/dashboard.html', surveys=hits, ordering=order, balance=balance, uploadform=uform, createdhit=createdhit)


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
        # project_name = form.project_name.data
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

        # softblock qualification #
        id = app.config.get('SOFTBLOCK_QUALIFICATION_ID')
        obj = create_qualification_object(id, "DoesNotExist", "None", "DiscoverPreviewAndAccept")
        qualifications.append(obj)

        # conditional fields #
        is_minibatched = form.minibatch.data

        if(is_minibatched):
            if(form.qualification_name.data == ""):
                now = datetime.datetime.now()
                print('This is the qualificationname:' + form.project_name.data + "_" + now.strftime("%Y-%m-%dT%H:%M:%S"))
                qualification_name = 'ParticipatedIn%s%s' % (form.project_name.data, now.strftime("%Y-%m-%dT%H:%M:%S"))
            else:
                qualification_name = form.qualification_name.data

            response = api.create_qualification_type(qualification_name, keywords, "MiniBatch-Qualification for %s" % title)
            qualification_id = response['QualificationTypeId']
            obj = create_qualification_object(qualification_id, "DoesNotExist", "None", "DiscoverPreviewAndAccept")
            qualifications.append(obj)

        if(is_minibatched):
            hit_type_id = api.create_hit_type(accept_pay_worker_after, allotted_time_per_worker, payment_per_worker, title, keywords, description, qualifications)
            minigroup = MiniGroup(active=True, layout=html_question_value, lifetime=time_till_expiration, type_id=hit_type_id, batch_qualification=qualification_id)
            db.session.add(minigroup)
            db.session.flush()
            group_id = minigroup.id
            hit_id = api.create_hit_with_type(hit_type_id, html_question_value, time_till_expiration, 9, 'batch%s' % group_id)['HITId']
            minihit = MiniHIT(group_id=group_id, active=True, position=1, workers=9, id=hit_id)
            db.session.add(minihit)
            amount_workers_last_hit = amount_workers % 9
            amount_workers_hits = amount_workers - amount_workers_last_hit - 9  # - 9 because we already created one HIT with 9 workers
            # print("GroupId=", group_id)
            # print("Workers total", amount_workers)
            # print("Workers minus the last hit", amount_workers_hits + 9)
            # print("Workers last hit", amount_workers_last_hit)
            # print("adding active minihit to DB")
            amount_full_hits = int(amount_workers_hits / 9)
            for i in range(amount_full_hits):
                print("adding inactive minihit", i + 1, "to DB")
                empty_minihit = MiniHIT(group_id=group_id, active=False, position=i + 2, workers=9, id=None)
                db.session.add(empty_minihit)
            if(amount_workers_last_hit != 0):
                print("adding last minihit with", amount_workers_last_hit, "workers")
                empty_minihit = MiniHIT(group_id=group_id, active=False, position=amount_full_hits + 2, workers=amount_workers_last_hit, id=None)
                db.session.add(empty_minihit)
            db.session.commit()

        else:
            hit = api.create_hit(amount_workers, accept_pay_worker_after, time_till_expiration, allotted_time_per_worker, payment_per_worker, title, keywords, description, html_question_value, qualifications)
            hit_type_id = hit['HITTypeId']
            hit_id = hit['HITId']

        # flash(f'Survey erstellt für {form.username.data}!', 'success')

        return redirect(url_for('dashboard', createdhit=hit_id))
    else:
        flash_errors(form)
    return render_template('main/survey.html', title='Neue Survey', form=form, balance=balance, qualifications=all_qualifications, qualification_percentage_interval=percentage_interval, qualification_integer_list=integer_list, cc_list=ISO3166,)


@app.route("/createsoftblock")
def softblock():
    qualification = api.create_qualification_type("Thank you!", "thanks", "For you splendid performance we award you this special qualification. Thank you again!")
    return jsonify(qualification)


@app.route("/cleardb")
def cleardb():
    db.drop_all()
    db.create_all()
    return "200 OK"


@app.route("/export/<id>")
@app.route("/export/<id>/<batched>")
def export(id, batched=False):
    batched = (batched == 'True' or batched == 'true')
    fieldnames = ['HITId', 'AssignmentId', 'WorkerId', 'Answer', 'Approve', 'Reject', 'Bonus', 'Reason', 'Softblock']

    assignments = get_assignments(id, batched, ['Submitted'])  # Add only submitted (non-rejected/-approved) Assignments to export

    si = io.StringIO()
    csv_writer = csv.DictWriter(si, fieldnames)
    csv_writer.writeheader()
    for a in assignments:
        csv_writer.writerow({'HITId': a['HITId'], 'AssignmentId': a['AssignmentId'], 'WorkerId': a['WorkerId'], 'Answer': a['Answer']})

    return Response(si.getvalue(), mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=results.csv"})


@app.route("/upload", methods=['POST'])
def upload():
    form = UploadForm()

    if form.validate_on_submit():

        csvfile = form.file.data
        csvdata = io.StringIO(csvfile.read().decode('utf-8'))

        csvreader = csv.DictReader(csvdata)
        # checking if the csv contains valid data
        errors = {}
        assignments = get_assignments(form.hit_identifier.data, form.hit_batched.data)  # maybe make status Submitted
        if not assignments:
            return json.dumps({'success': False, 'errortype': 'main', 'errors': {'main': 'No Assignments found.'}}), 404, {'ContentType': 'application/json'}
        for index, row in enumerate(csvreader, 1):
            try:
                hitid = row['HITId']
                assignmentid = row['AssignmentId']
                workerid = row['WorkerId']
                approve = row['Approve']
                reject = row['Reject']
                bonus = row['Bonus']
                reason = row['Reason']
                row['Softblock']
            except KeyError as e:
                return json.dumps({'success': False, 'errortype': 'main', 'errors': {'main': 'CSV header not formatted properly: </br> Missing header %s' % e}}), 422, {'ContentType': 'application/json'}

            # TODO:Check if assignment to be approved/rejected is Submitted and not rejected/approved already
            if approve and reject:
                errors.setdefault(index, []).append('Approve and Reject are both set.')
            if not approve and not reject:
                errors.setdefault(index, []).append('Approve and Reject are both not set.')

            valid_hit_assignment_worker = False
            for assignment in assignments:
                if assignment['AssignmentId'] == assignmentid\
                        and assignment['WorkerId'] == workerid\
                        and assignment['HITId'] == hitid:
                    valid_hit_assignment_worker = True

                    # No duplicates allowed
                    if 'DuplicateCheck' in assignment:
                        errors.setdefault(index, []).append('Duplicate HIT/Assignment/Worker combination.')
                    else:
                        assignment['DuplicateCheck'] = True

            if not valid_hit_assignment_worker:
                errors.setdefault(index, []).append('Non-valid HIT/Assignment/Worker combination.')
            if bonus and not is_number(bonus):
                errors.setdefault(index, []).append('Bonus not a valid number.')
            if is_number(bonus) and float(bonus) > MAX_BONUS:
                errors.setdefault(index, []).append('Bonus is too high. MAX: %s.' % MAX_BONUS)
            if bonus and not reason:
                errors.setdefault(index, []).append('Bonus assigned but no reason given.')

        if errors:
            return json.dumps({'success': False, 'errortype': 'document', 'errors': errors}), 422, {'ContentType': 'application/json'}

        total_approved = 0
        total_rejected = 0
        total_softblocked = 0
        total_bonus = 0.0

        # Going back to beginning of CSV if data appeared valid
        csvdata.seek(0)
        csvreader = csv.DictReader(csvdata)
        for row in csvreader:
            print(row)
            hitid = row['HITId']
            assignmentid = row['AssignmentId']
            workerid = row['WorkerId']
            approve = row['Approve']
            reject = row['Reject']
            bonus = row['Bonus']
            reason = row['Reason']
            softblock = row['Softblock']
            unique_token_bonus = assignmentid + workerid

            if approve:
                api.approve_assignment(assignmentid)
                total_approved += 1
            if reject:  # Maybe add custom reason slot to csv
                api.reject_assignment(assignmentid, "We are sorry to inform you that your answer did not match our quality standards.")
                total_rejected += 1
            if bonus:
                api.send_bonus(workerid, assignmentid, bonus, reason, unique_token_bonus)
                total_bonus += float(bonus)

            if softblock:
                softblock_id = app.config.get('SOFTBLOCK_QUALIFICATION_ID')
                api.associate_qualification_with_worker(workerid, softblock_id)
                total_softblocked += 1

        data = {}
        data['approved'] = total_approved
        data['rejected'] = total_rejected
        data['softblocked'] = total_softblocked
        data['bonus'] = total_bonus

        return json.dumps({'success': True, 'data': data}), 200, {'ContentType': 'application/json'}

    return json.dumps({'success': False, 'errortype': 'form', 'errors': form.errors}), 400, {'ContentType': 'application/json'}


def get_assignments(id, batched, status=None):
    if(batched):
        hits = db.session.query(MiniHIT.id)\
            .filter(MiniHIT.group_id == id)\
            .filter(MiniHIT.id.isnot(None)).all()
        ids = []
        for hit in hits:
            ids.append(hit.id)
        assignments = api.list_assignments_for_hits(ids, status)
    else:
        assignments = api.list_assignments_for_hit(id, status)

    for assignment in assignments:

        answer_xml = assignment['Answer']
        start = answer_xml.index("<FreeText>") + len("<FreeText>")
        end = answer_xml.index("</FreeText>")
        assignment['Answer'] = answer_xml[start:end]

    return assignments


@app.route("/list_assignments/<id>")
@app.route("/list_assignments/<id>/<batched>")
def list_assignments(id, batched=False):

    assignments = get_assignments(id, batched)
    return jsonify(assignments)


@app.route("/deletebatch/<awsid:batchid>")
def deletebatch(batchid):
    query = db.session.query(MiniGroup, MiniHIT).filter(MiniGroup.gid == batchid and MiniHIT.group_id == batchid).all()
    if not query:
        return "No such Batch"
    group_to_delete = query[0].MiniGroup
    hits_to_delete = []
    for row in query:
        if(row.MiniHIT.id is None):
            print("HIT was not created yet --- Skipping")
            continue
        hit = api.get_hit(row.MiniHIT.id)
        if(hit['HITStatus'] == 'Disposed'):
            print("HIT exists locally but not in MTURK-Database --- Skipping")
            continue

        if(hit['HITStatus'] in ['Reviewable', 'Reviewed']):
            print("Queueing %s for deletion" % (row.MiniHIT.id))
            hits_to_delete.append(row.MiniHIT.id)
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
    query = db.session.query(MiniHIT).filter(MiniHIT.id == id).one()

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

    to_delete = MiniHIT.query\
        .filter(MiniHIT.group_id == group_id)\
        .filter(MiniHIT.position == position)\
        .filter(MiniHIT.id.is_(None)).one_or_none()

    if(to_delete is None):
        return json.dumps({'success': False, 'error': 'ERROR'}), 423, {'ContentType': 'application/json'}

    db.session.delete(to_delete)

    # We need to correct the indice of the following HITs to maintain database integrity
    to_index = MiniHIT.query\
        .filter(MiniHIT.group_id == group_id)\
        .filter(MiniHIT.position > position).all()

    for hit in to_index:
        hit.position -= 1

    db.session.commit()
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}

    # Deleting requested QUEUED HIT, throws exception if HIT was created already


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
    query = db.session.query(MiniGroup, MiniHIT)\
        .filter(MiniGroup.id == MiniHIT.group_id)\
        .filter(MiniHIT.active)\
        .filter(MiniGroup.active).all()

    for row in query:
        active_hit_id = row.MiniHIT.id  # MiniHIT.uid == HITTypeId
        active_hit = api.get_hit(active_hit_id)
        print("Checking %s with HITStatus %s, from Group %s " % (active_hit_id, active_hit['HITStatus'], row.MiniGroup.id))

        if(active_hit['HITStatus'] == 'Unassignable' or active_hit['HITStatus'] == 'Reviewable'):
            print("Assignment done, granting users qualifications")
            api.grant_qualifications_for_hit(active_hit_id, row.MiniGroup.batch_qualification)
            print("Assignment done, creating new one")
            new_position = row.MiniHIT.position + 1

            # Fetching Group-specific data that is shared between MiniHITs and is needed for the new MiniHIT
            group_id = row.MiniGroup.id
            hittypeid = row.MiniGroup.type_id
            question = row.MiniGroup.layout
            lifetime = row.MiniGroup.lifetime

            # Because the current MiniHIT is expired we set it to inactive
            row.MiniHIT.active = False

            # Getting the new MiniHIT-DB-entry
            new_mini_hit = MiniHIT.query.filter(MiniHIT.position == new_position)\
                                        .filter(MiniHIT.group_id == group_id)\
                                        .first()

            # Checking if there is a following MiniHIT
            if(new_mini_hit is None):
                print("Actually not creating a new one because we reached the end, setting HITGroup to inactive")
                row.MiniGroup.active = False
                continue

            workers = new_mini_hit.workers

            # Creating a new HIT with the assigned attributes and saving its ID
            new_hit_id = api.create_hit_with_type(hittypeid, question, lifetime, workers, 'batch%r' % group_id)['HITId']
            print("Creating hit with id", new_hit_id)
            # Using saved ID to update DB-schema
            new_mini_hit.id = new_hit_id
            new_mini_hit.active = True
    db.session.commit()


db.create_all()

import os
if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':  # Make Scheduler be created once, else it will run twice which will screw up the database
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_mini_hits, 'interval', seconds=15)
    scheduler.start()
