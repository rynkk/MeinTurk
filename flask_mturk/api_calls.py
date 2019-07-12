from flask_mturk import client
from datetime import datetime
import time
from botocore.exceptions import ClientError


class Api:
    def __init__(self, c):
        self.client = c

    # Elementary functions #
    def get_hit(self, hitid):
        return self.client.get_hit(HITId=hitid)['HIT']

    def expire_hit(self, hit_id):
        return self.client.update_expiration_for_hit(HITId=hit_id, ExpireAt=datetime(2015, 1, 1))

    def get_balance(self):
        return self.client.get_account_balance()['AvailableBalance']

    def delete_hit(self, hit_id):
        return self.client.delete_hit(HITId=hit_id)

    def approve_assignment(self, assignment_id):
        return client.approve_assignment(AssignmentId=assignment_id)

    def reject_assignment(self, assignment_id, reason):
        return client.reject_assignment(AssignmentId=assignment_id, RequesterFeedback=reason)

    def associate_qualification_with_worker(self, worker_id, qualification_id):
        return client.associate_qualification_with_worker(
            QualificationTypeId=qualification_id,
            WorkerId=worker_id,
            SendNotification=False,
        )

    def send_bonus(self, worker_id, assignment_id, bonus_amount, reason, token):
        return client.send_bonus(
            WorkerId=worker_id,
            BonusAmount=bonus_amount,
            AssignmentId=assignment_id,
            Reason=reason,
            UniqueRequestToken=token
        )

    def create_hit(self, max, autoacc, lifetime, duration, reward, title, keywords, desc, question, qualreq):
        response = self.client.create_hit(
            MaxAssignments=max,
            AutoApprovalDelayInSeconds=autoacc,
            LifetimeInSeconds=lifetime,
            AssignmentDurationInSeconds=duration,
            Reward=reward,
            Title=title,
            Keywords=keywords,
            Description=desc,
            Question=question,
            QualificationRequirements=qualreq
        )['HIT']
        return response

    def create_hit_with_type(self, hittypeid, question, lifetime, max, reqanno=""):
        response = self.client.create_hit_with_hit_type(
            HITTypeId=hittypeid,
            MaxAssignments=max,
            LifetimeInSeconds=lifetime,
            Question=question,
            RequesterAnnotation=reqanno
        )['HIT']
        return response

    def create_hit_type(self, autoapp, duration, reward, title, keywords, desc, qualreq):
        response = self.client.create_hit_type(
            AutoApprovalDelayInSeconds=autoapp,
            AssignmentDurationInSeconds=duration,
            Reward=reward,
            Title=title,
            Keywords=keywords,
            Description=desc,
            QualificationRequirements=qualreq
        )
        return response['HITTypeId']

    def create_qualification_type(self, name, keywords, description):
        response = client.create_qualification_type(
            Name=name,
            Keywords=keywords,
            Description=description,
            QualificationTypeStatus='Active',
        )['QualificationType']
        return response

    # Paginated functions #
    def list_all_hits(self):
        result = []
        paginator = self.client.get_paginator('list_hits')
        pages = paginator.paginate(PaginationConfig={'PageSize': 100})
        for page in pages:
            result += page['HITs']
        return result

    def list_assignments_for_hit(self, hitid, status=None):
        result = []
        if status is None:
            status = ['Submitted', 'Approved', 'Rejected']
        paginator = self.client.get_paginator('list_assignments_for_hit')
        pages = paginator.paginate(
            HITId=hitid,
            AssignmentStatuses=status,
            PaginationConfig={'PageSize': 100}
        )
        for page in pages:
            result += page['Assignments']
        return result

    def list_custom_qualifications(self):
        result = []
        paginator = self.client.get_paginator('list_qualification_types')
        pages = paginator.paginate(
            MustBeRequestable=False,
            MustBeOwnedByCaller=True,
            PaginationConfig={'PageSize': 100}
        )
        for page in pages:
            result += page['QualificationTypes']
        return result

    # Combined Functions #
    def forcedelete_hit(self, hit_id):
        self.expire_hit(hit_id)
        time.sleep(5)
        self.delete_hit(hit_id)

    def delete_hits(self, hit_ids):
        for id in hit_ids:
            self.delete_hit(id)

    def list_assignments_for_hits(self, hit_ids, status=None):
        result = []
        for id in hit_ids:
            result += self.list_assignments_for_hit(id, status)
        return result

    #  probably have to check every hit because of race condition where hit is expired but people just accepted it which will effectively allow them to answer multiple MiniHITs
    def grant_qualifications_for_hit(self, hit_id, qualification_id):
        assignments = self.list_assignments_for_hit(hit_id)
        for assignment in assignments:
            print("assigning qualification %s to Worker %s" % (qualification_id, assignment['WorkerId']))
            self.associate_qualification_with_worker(assignment['WorkerId'], qualification_id)

    def forcedelete_all_hits(self, retry=False):
        # TODO: fix, also cap retries at 10 instead of 2 Need to check if there are assignments that are not approved or rejected
        all_hits = self.list_all_hits()
        missed_one = False
        if(not all_hits):
            return "nothing to delete"

        print("**********EXPIRING HITS**********")
        for obj in all_hits:
            print("EXPIRING HIT with ID:", obj['HITId'])
            self.expire_hit(obj['HITId'])
            # Maybe add time.sleep(1)here

        print("**********DELETING HITS**********")
        for obj in all_hits:
            print(obj['HITStatus'])
            if(obj['HITStatus'] == 'Reviewable' or obj['HITStatus'] == 'Reviewing'):
                print("Deleteing HIT with ID:", obj['HITId'])
                try:
                    self.delete_hit(obj['HITId'])
                except ClientError:
                    print("HIT has unsubmitted or unapproved Assignments --- Skipping")
                continue

            if(retry):
                print("ERROR: HIT %s IS NOT EXPIRED --- ABORTING AFTER THIS TRY)" % (obj['HITId']))
                continue

            print("ERROR: HIT %s IS NOT EXPIRED --- RETRYING AFTER PROCESS IS FINISHED" % (obj['HITId']))
            missed_one = True
        if(missed_one):
            return self.forcedelete_all_hits(True)
        return "Done"


api = Api(client)
