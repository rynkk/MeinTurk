import csv
from datetime import datetime
import io

from apscheduler.schedulers.background import BackgroundScheduler
from flask import render_template, url_for, flash, redirect, jsonify, json, request, Response
from flask_mturk import app, db, ISO3166, SYSTEM_QUALIFICATION, MAX_BONUS, MAX_PAYMENT
from flask_mturk.forms import SurveyForm, UploadForm
from flask_mturk.models import MiniGroup, MiniHIT, HiddenHIT, CachedAnswer

from .api_calls import api
from .helper import is_number, seconds_from_string

# Use APPconfig instead of constants like MAX_BONUS
@app.route("/")
@app.route("/dashboard")
def dashboard():
    balance = api.get_balance()
    hits = api.list_all_hits()
    all_qualifications = SYSTEM_QUALIFICATION + api.list_custom_qualifications()
    groups = MiniGroup.query.filter(MiniGroup.status != 'cached').all()
    order = []

    # Often the API is not quick enough and does not add the created HIT
    # to the list_all_hits, so if it is not there yet we need to add it manually
    # Alternative: use Waiter:
    createdhit = request.args.get('createdhit')
    if(createdhit is not None):
        new_hit = api.get_hit(createdhit)
        if new_hit not in hits:
            hits.append(new_hit)

    hidden_hits = db.session.query(HiddenHIT.id).all()

    for group in groups:
        batch = {'batch_id': group.id, 'batch_goal': group.assignments_goal, 'batch_status': group.status, 'hidden': group.hidden, 'hits': []}
        for hit in group.minihits:
            batch['hits'].append({'id': hit.id, 'workers': hit.workers, 'position': hit.position})
        order.append(batch)
    # TODO: Outsource logic to client?

    uform = UploadForm()

    return render_template('main/dashboard.html', surveys=hits, ordering=order, balance=balance, uploadform=uform, createdhit=createdhit, quals=all_qualifications, hidden_hits=hidden_hits)


@app.route("/survey", methods=['GET', 'POST'])
def survey():
    form = SurveyForm()

    percentage_interval = 5
    integer_list = [1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000]
    balance = api.get_balance()

    # we need to dynamically change the allowed options for the qual_select
    all_qualifications_w_sys = SYSTEM_QUALIFICATION + api.list_custom_qualifications()
    # remove softblock-qualification
    all_qualifications = [q for q in all_qualifications_w_sys if not (q['QualificationTypeId'] == app.config.get('SOFTBLOCK_QUALIFICATION_ID'))]
    print(all_qualifications)
    selector_choices = [(qual['QualificationTypeId'], qual["Name"]) for qual in all_qualifications]

    # if post then add choices for each entry of qualifications_select.selects so that form qual_select can validate
    if request.method == "POST":
        if form.payment_per_worker.data > MAX_PAYMENT:
            return
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
            obj = create_qualification_object(id, 'EqualTo', 1, "PreviewAndAccept")
            qualifications.append(obj)

        # softblock qualification # Deactivated till app done
        # id = app.config.get('SOFTBLOCK_QUALIFICATION_ID')
        # obj = create_qualification_object(id, "DoesNotExist", "None", "DiscoverPreviewAndAccept")
        # qualifications.append(obj)

        # conditional fields #
        is_minibatched = form.minibatch.data

        if(is_minibatched):
            if(form.qualification_name.data == ""):
                now = datetime.now()
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
            minigroup = MiniGroup(status='active', project_name=project_name, hidden=False, assignments_submitted=0, assignments_goal=amount_workers, layout=html_question_value, lifetime=time_till_expiration, type_id=hit_type_id, batch_qualification=qualification_id)
            db.session.add(minigroup)
            db.session.flush()
            group_id = minigroup.id
            hit_id = api.create_hit_with_type(hit_type_id, html_question_value, time_till_expiration, 9, 'batch%s' % group_id)['HITId']
            minihit = MiniHIT(group_id=group_id, status='active', position=1, workers=9, id=hit_id)
            db.session.add(minihit)
            db.session.flush()
            add_hits_to_db(group_id, amount_workers - 9)  # -9 because we already created one HIT with 9 workers
            db.session.commit()
        else:
            hit = api.create_hit(amount_workers, accept_pay_worker_after, time_till_expiration, allotted_time_per_worker, payment_per_worker, title, keywords, description, html_question_value, qualifications)
            hit_type_id = hit['HITTypeId']
            hit_id = hit['HITId']

        # flash(f'Survey erstellt für {form.username.data}!', 'success')

        return redirect(url_for('dashboard', createdhit=hit_id))
    else:
        flash_errors(form)
    return render_template('main/survey.html', title='Neue Survey', form=form, balance=balance, qualifications=all_qualifications, qualification_percentage_interval=percentage_interval, qualification_integer_list=integer_list, cc_list=ISO3166, max_payment=MAX_PAYMENT)


@app.route("/qualifications")
def qualifications_page():
    balance = api.get_balance()
    qualifications = api.list_custom_qualifications()
    return render_template('main/qualification_list.html', title='Qualifications', balance=balance, qualifications=qualifications)


@app.route("/worker")
def worker_page():
    balance = api.get_balance()
    return render_template('main/worker_list.html', title='Workers', balance=balance)


@app.route("/cached")
def cached_page():
    balance = api.get_balance()
    groups = MiniGroup.query.filter(MiniGroup.status == 'cached').all()
    cached_batches = []
    for group in groups:
        batch = {'name': group.project_name, 'id': group.id, 'goal': group.assignments_goal, 'submitted': group.assignments_submitted}
        cached_batches.append(batch)

    return render_template('main/cached_list.html', title='Cached Batches', balance=balance, batches=cached_batches)


@app.route("/cache_batch/<int:batchid>")  # , methods=['PATCH'])
def cache_batch(batchid):
    group = MiniGroup.query\
        .filter(MiniGroup.id == batchid)\
        .filter(MiniGroup.status != 'cached')\
        .one_or_none()
    if group is None:
        return json.dumps({'success': False}), 404, {'ContentType': 'application/json'}

    hits = MiniHIT.query.filter(MiniHIT.group_id == group.id).all()
    ids = []
    for hit in hits:
        # Check if there are still pending or non approved/rejected Answers
        if hit.id is None:
            # if hit is queued but not published, delete them
            db.session.delete(hit)
            continue
        response = api.get_hit(hit.id)
        ids.append(hit.id)

        if response['NumberOfAssignmentsPending'] > 0:
            return json.dumps({'success': False, 'error': 'Batch still has pending assignments.'}), 423, {'ContentType': 'application/json'}
        if response['MaxAssignments'] != response['NumberOfAssignmentsCompleted'] + response['NumberOfAssignmentsAvailable']:
            return json.dumps({'success': False, 'error': 'Batch still has non-completed assignments.'}), 423, {'ContentType': 'application/json'}
        if response['HITStatus'] != 'Reviewable':
            return json.dumps({'success': False, 'error': 'Cannot cache Batch with active HITs.'}), 423, {'ContentType': 'application/json'}
        assignments = get_assignments(hit.id, False)
        bonus_payments = api.list_bonus_payments_for_hit(hit.id)
        for a in assignments:
            print(a)
            approved = True if a['AssignmentStatus'] == 'Approved' else False
            bonus_obj = next((payment for payment in bonus_payments if payment['WorkerId'] == a['WorkerId'] and payment['AssignmentId'] == a['AssignmentId']), None)

            # Convert bonus to Cents to prepare it for the DB
            if(bonus_obj):
                bonus = int(float(bonus_obj['BonusAmount']) * 100)
                reason = bonus_obj['Reason']
            else:
                bonus = ""
                reason = ""
            time_taken = (a['SubmitTime'] - a['AcceptTime']).total_seconds()

            ca = CachedAnswer(hit_id=hit.id, assignment_id=a['AssignmentId'],
                              worker_id=a['WorkerId'], answer=a['Answer'],
                              approved=approved, bonus=bonus, reason=reason,
                              accept_date=a['AcceptTime'], time_taken=time_taken)
            db.session.add(ca)

        hit.status = 'cached'
    group.status = 'cached'
    db.session.commit()
    api.delete_hits(ids)
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}


@app.route("/assignment_goal/<int:batchid>")
@app.route("/assignment_goal/<int:batchid>/<int:goal>", methods=['PATCH'])
def update_goal(batchid, goal=None):
    group = MiniGroup.query.filter(MiniGroup.id == batchid).one_or_none()
    if not group:
        return json.dumps({'success': False, 'error': 'Could not find Batch with id %s.' % batchid}), 200, {'ContentType': 'application/json'}

    if request.method == 'GET':
        return json.dumps({'success': True, 'goal': group.assignments_goal}), 200, {'ContentType': 'application/json'}
    elif request.method == 'POST':
        group.assignments_goal = goal
        db.session.commit()
        return json.dumps({'success': True, 'goal': goal}), 200, {'ContentType': 'application/json'}


@app.route("/export/<int:id>/<type_>")
@app.route("/export/<awsid:id>/<type_>")
def export(id, type_):
    #             time_taken = (a['SubmitTime'] - a['AcceptTime']).total_seconds()
    print(type_)
    batched = is_number(id)
    fieldnames = ['HITId', 'AssignmentId', 'WorkerId', 'Status', 'Answer', 'TimeTaken', 'Approve', 'Reject', 'Bonus', 'Reason', 'Softblock']

    if type_ == 'all':
        assignments = get_assignments(id, batched)  # Add submitted, rejected and approved Assignments to export
        # probably add payments for every id here
        softblocked_workers = api.list_workers_with_qualification_type(app.config.get('SOFTBLOCK_QUALIFICATION_ID'))
        filename = "results_all.csv"

    elif type_ == 'submitted':
        assignments = get_assignments(id, batched, ['Submitted'])  # Add only submitted Assignments to export
        filename = "results_new.csv"

    si = io.StringIO()
    csv_writer = csv.DictWriter(si, fieldnames)
    csv_writer.writeheader()

    for a in assignments:
        row = {'HITId': a['HITId'], 'AssignmentId': a['AssignmentId'], 'WorkerId': a['WorkerId'], 'Status': a['AssignmentStatus'], 'Answer': a['Answer']}
        time_taken = int((a['SubmitTime'] - a['AcceptTime']).total_seconds())
        row['TimeTaken'] = time_taken

        if a['AssignmentStatus'] == 'Submitted':
            csv_writer.writerow(row)
        else:
            # Might be faster to list payments for entire HIT/entire MiniGroup
            bonus = api.list_bonus_payments_for_assignment(a['AssignmentId'])

            if len(bonus) == 1:
                bonus = bonus[0]
                row['Bonus'] = bonus['BonusAmount']
                row['Reason'] = bonus['Reason']

            if a['AssignmentStatus'] == 'Approved':
                row['Approve'] = 'x'
            else:
                row['Reject'] = 'x'

            if any(worker['WorkerId'] == a['WorkerId'] for worker in softblocked_workers):
                row['Softblock'] = 'x'
            csv_writer.writerow(row)
    return Response(si.getvalue(), mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=%s" % filename})


@app.route("/export_cached/<int:id>")
def export_cached(id):
    group = MiniGroup.query\
                     .filter(MiniGroup.id == id)\
                     .filter(MiniGroup.status == 'cached')\
                     .one_or_none()
    if(group is None):
        return json.dumps({'success': False}), 200, {'ContentType': 'application/json'}

    softblocked_workers = api.list_workers_with_qualification_type(app.config.get('SOFTBLOCK_QUALIFICATION_ID'))
    assignments = []

    for hit in group.minihits:
        for answer in hit.answers:
            a = {'HITId': answer.hit_id, 'AssignmentId': answer.assignment_id,
                 'WorkerId': answer.worker_id, 'Answer': answer.answer,
                 'TimeTaken': answer.time_taken, 'Reason': answer.reason}

            if answer.bonus != "" and answer.bonus:
                a['Bonus'] = answer.bonus / 100,

            if answer.approved:
                a['Status'] = 'Approved'
                a['Approve'] = 'x'
            else:
                a['Status'] = 'Rejected'
                a['Reject'] = 'x'

            if any(worker['WorkerId'] == answer.worker_id for worker in softblocked_workers):
                a['Softblock'] = 'x'
            assignments.append(a)

    si = io.StringIO()
    fieldnames = ['HITId', 'AssignmentId', 'WorkerId', 'Status', 'Answer', 'TimeTaken', 'Approve', 'Reject', 'Bonus', 'Reason', 'Softblock']

    csv_writer = csv.DictWriter(si, fieldnames)
    csv_writer.writeheader()

    for row in assignments:
        csv_writer.writerow(row)

    return Response(si.getvalue(), mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=result_cached.csv"})


@app.route("/upload", methods=['POST'])
def upload():
    form = UploadForm()

    if form.validate_on_submit():
        print("OK")
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
                assignmentstatus = row['Status']
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
            if assignmentstatus not in ['Approved', 'Submitted', 'Rejected']:
                errors.setdefault(index, []).append('Non-valid Assignment status: "%s".' % assignmentstatus)
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
        warnings = {}
        csvdata.seek(0)
        csvreader = csv.DictReader(csvdata)
        for index, row in enumerate(csvreader, 1):
            if row['Status'] != 'Submitted':
                # Skipping line if already approved/rejected
                continue
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
                error = api.approve_assignment(assignmentid)
                if error is None:
                    total_approved += 1
                else:
                    warnings.setdefault(index, []).append('Could not approve assignment, maybe it was auto-approved already?')
            if reject:  # Maybe add custom reason slot to csv
                error = api.reject_assignment(assignmentid, "We are sorry to inform you that your answer did not match our quality standards.")
                if error is None:
                    total_rejected += 1
                else:
                    warnings.setdefault(index, []).append('Could not reject assignment, maybe it was auto-approved already?')
            if bonus:
                error = api.send_bonus(workerid, assignmentid, bonus, reason, unique_token_bonus)
                if error is None:
                    total_bonus += float(bonus)
                else:
                    warnings.setdefault(index, []).append('Could not send bonus. You can only send one bonus per Assignment!')

            if softblock:
                # errorhandling for softblock
                softblock_id = app.config.get('SOFTBLOCK_QUALIFICATION_ID')
                api.associate_qualification_with_worker(workerid, softblock_id)
                total_softblocked += 1

        data = {}
        data['approved'] = total_approved
        data['rejected'] = total_rejected
        data['softblocked'] = total_softblocked
        data['bonus'] = total_bonus

        return json.dumps({'success': True, 'data': data, 'warnings': warnings}), 200, {'ContentType': 'application/json'}

    return json.dumps({'success': False, 'errortype': 'form', 'errors': form.errors}), 400, {'ContentType': 'application/json'}


@app.route("/db/toggle_hit_visibility/<awsid:id>", methods=['PATCH'])
@app.route("/db/toggle_hit_visibility/<int:id>/<batched>", methods=['PATCH'])
def toggle_hit_visibility(id, batched=False):
    batched = (batched == 'True' or batched == 'true')
    if batched:
        group = MiniGroup.query.filter(MiniGroup.id == id).one_or_none()
        if group:
            group.hidden = not group.hidden
            hidden = group.hidden
        else:
            return json.dumps({'success': False, 'error': 'No such group.'}), 404, {'ContentType': 'application/json'}
    else:
        hit = HiddenHIT.query.filter(HiddenHIT.id == id).one_or_none()
        if hit is None:
            hit = HiddenHIT(id=id)
            db.session.add(hit)
            hidden = True
        else:
            db.session.delete(hit)
            hidden = False

    db.session.commit()
    return json.dumps({'success': True, 'hidden': hidden}), 200, {'ContentType': 'application/json'}


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


@app.route("/list_assignments/<awsid:id>")
@app.route("/list_assignments/<int:id>/<batched>")
def list_assignments(id, batched=False):
    assignments = get_assignments(id, batched)
    return jsonify(assignments)


@app.route("/list_payments/<awsid:id>")
def list_payments(id):
    payments = api.list_bonus_payments_for_hit(id)
    return jsonify(payments)


@app.route("/deletebatch/<awsid:batchid>", methods=['DELETE'])
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


@app.route('/dashboard/deletehit/<awsid:id>', methods=['DELETE'])
def deletehit(id):
    query = db.session.query(MiniHIT).filter(MiniHIT.id == id).one_or_none()

    if(query is not None):
        print("Deleting MiniHit")
        return "MiniHIT deleted"
    try:
        api.get_hit(id)
        api.delete_hit(id)
        return "HIT deleted"
    except api.client.exceptions.RequestError as err:
        return '<h3>' + str(err) + '</h3>'


@app.route('/db/delete-queued/<int:group_id>/<int:position>', methods=['DELETE'])
def delete_queued_from_db(group_id, position):

    to_delete = MiniHIT.query\
        .filter(MiniHIT.status != 'cached')\
        .filter(MiniHIT.group_id == group_id)\
        .filter(MiniHIT.position == position).one_or_none()
    if to_delete is None:
        return json.dumps({'success': False, 'type': 'not_found', 'error': 'No MiniHIT at position %s of Group %s found!' % (position, group_id)}), 404, {'ContentType': 'application/json'}

    unnecessary_keys = ['AssignmentDurationInSeconds', 'AutoApprovalDelayInSeconds', 'Description', 'HITGroupId',
                        'Keywords', 'QualificationRequirements', 'Question', 'Reward', 'Title']

    if to_delete.id is not None:
        # try catch if id not valid blub
        hit = api.get_hit(to_delete.id)
        hit['workers'] = to_delete.workers
        hit['position'] = to_delete.position
        for key in unnecessary_keys:
            if key in hit:
                del hit[key]
        return json.dumps({'success': False, 'type': 'locked', 'hit': hit, 'error': 'MiniHIT at position %s of Group %s was already published!' % (position, group_id)}), 423, {'ContentType': 'application/json'}

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


@app.route('/db/toggle_group_status/<int:group_id>', methods=['PATCH'])
def toggle_group_status(group_id):
    group = MiniGroup.query.filter(MiniGroup.id == group_id)\
                           .filter(MiniGroup.status != 'cached').one_or_none()
    if(group is None):
        return json.dumps({'success': False, 'error': 'Group does not exist.'}), 404, {'ContentType': 'application/json'}
    if group.status == 'active':
        group.status = 'inactive'
    else:
        group.status = 'active'
    status = group.status
    db.session.commit()
    return json.dumps({'success': True, 'status': status}), 200, {'ContentType': 'application/json'}


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


# Doesnt commit
def add_hits_to_db(groupid, assignments):
    max_pos = db.session.query(db.func.max(MiniHIT.position))\
        .filter(MiniHIT.group_id == groupid)\
        .filter(MiniHIT.status != 'cached').scalar()
    if max_pos is None:
        return "Error"
    max_pos += 1

    part = assignments % 9
    full = int((assignments - part) / 9)
    for i in range(full):
        print("Adding new queued HITs to DB a 9 Workers")
        minihit = MiniHIT(group_id=groupid, status='inactive', position=max_pos + i, workers=9, id=None)
        db.session.add(minihit)
    if part > 0:
        print("Adding new queued HITs to DB with %s Workers" % part)
        minihit = MiniHIT(group_id=groupid, status='inactive', position=max_pos + full, workers=part, id=None)
        db.session.add(minihit)


def update_mini_hits():
    query = db.session.query(MiniGroup, MiniHIT)\
        .filter(MiniGroup.id == MiniHIT.group_id)\
        .filter(MiniHIT.status == 'active')\
        .filter(MiniGroup.status == 'active').all()

    for row in query:
        active_hit_id = row.MiniHIT.id
        active_hit = api.get_hit(active_hit_id)
        # print("Checking %s with HITStatus %s, from Group %s " % (active_hit_id, active_hit['HITStatus'], row.MiniGroup.id))

        # Reviewable: if (expired AND pending==0) or (maxassignments-available+pending == 0)
        if(active_hit['HITStatus'] == 'Reviewable'):

            # Need to get Done HIT to check how many Assignments were submitted
            hit = api.get_hit(active_hit_id)
            max_ass = hit['MaxAssignments']
            pending_ass = hit['NumberOfAssignmentsPending']  # Should always be 0 due to Reviewable Status (adding just in case)
            available_ass = hit['NumberOfAssignmentsAvailable']
            submitted = max_ass - (available_ass + pending_ass)
            # if available_ass + pending_ass == 0:
            #     print("*** All Assignments were submitted ***")
            # else:
            #     print("*** HIT expired ***")
            # print("*** Adding #submittedAssignments to MiniGroup: %s***" % submitted)
            row.MiniGroup.assignments_submitted += submitted
            # print("*** Granting users qualifications ***")
            api.grant_qualifications_for_hit(active_hit_id, row.MiniGroup.batch_qualification)
            # print("*** Creating new MiniHIT ***")
            new_position = row.MiniHIT.position + 1

            # Fetching Group-specific data that is shared between MiniHITs and is needed for the new MiniHIT
            group_id = row.MiniGroup.id
            hittypeid = row.MiniGroup.type_id
            question = row.MiniGroup.layout
            lifetime = row.MiniGroup.lifetime

            # Getting the new MiniHIT-DB-entry
            new_mini_hit = MiniHIT.query.filter(MiniHIT.position == new_position)\
                                        .filter(MiniHIT.group_id == group_id)\
                                        .one_or_none()

            # Checking if there is a following MiniHIT
            if(new_mini_hit is None):
                # print("No queued HIT left. Checking if we reached the submission goal...")
                submissions = row.MiniGroup.assignments_submitted
                goal = row.MiniGroup.assignments_goal
                if submissions >= goal:
                    # print("Goal reached: Submitted: %s, Goal: %s. Making Group inactive" % (submissions, goal))
                    row.MiniGroup.status = 'inactive'
                    continue
                else:
                    needed = goal - submissions
                    # print("Goal not reached: Submitted: %s, Goal: %s, Needed: %s." % (submissions, goal, needed))
                    add_hits_to_db(group_id, needed)
                    db.session.flush()
                    # Getting the new MiniHIT-DB-entry
                    new_mini_hit = \
                        MiniHIT.query.filter(MiniHIT.position == new_position)\
                        .filter(MiniHIT.group_id == group_id)\
                        .one()

            # Because the current MiniHIT is expired we set it to inactive
            row.MiniHIT.status = 'inactive'

            workers = new_mini_hit.workers

            # Creating a new HIT with the assigned attributes and saving its ID
            new_hit_id = api.create_hit_with_type(hittypeid, question, lifetime, workers, 'batch%r' % group_id)['HITId']
            # print("Creating hit with id", new_hit_id)
            # Using saved ID to update DB-schema
            new_mini_hit.id = new_hit_id
            new_mini_hit.status = 'active'
    db.session.commit()


db.create_all()

import os
if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':  # Make Scheduler be created once, else it will run twice which will screw up the database
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_mini_hits, 'interval', seconds=15)
    scheduler.start()


######################################################################
#                          DEBUGGING ROUTES                          #
######################################################################

@app.route('/delete_hit/<awsid:hitid>')
def delete_route(hitid):
    return api.delete_hit(hitid)


@app.route('/expire_hit/<awsid:hitid>')
def expire_route(hitid):
    return jsonify(api.expire_hit(hitid))


@app.route('/get_hit/<awsid:hitid>')
def get_route(hitid):
    return jsonify(api.get_hit(hitid))


@app.route('/approve_all/<awsid:hitid>')
def approve_route(hitid):
    assignments = api.list_assignments_for_hit(hitid)
    for assignment in assignments:
        if(assignment['AssignmentStatus'] == 'Submitted'):
            api.approve_assignment(assignment['AssignmentId'])
    return "200 OK"


@app.route('/forcedeleteallhits')
def forcedeleteallhits():
    api.forcedelete_all_hits()
    return "200 OK"


@app.route("/createsoftblock")
def softblock():
    qualification = api.create_qualification_type("Thank you!", "thanks", "For you splendid performance we award you this special qualification. Thank you again!")
    return jsonify(qualification)


@app.route("/cleardb/<secretkey>")
def cleardb(secretkey):
    if secretkey != app.config.get('SECRET_KEY'):
        return "403 Forbidden"
    db.drop_all()
    db.create_all()
    return "200 OK"


@app.route("/delete_all_qualifications")
def delete_all_qualifications():
    api.delete_all_qualification_types()
    return "200 OK"
