from flask_mturk import client
from datetime import datetime
import time


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

    # Paginated functions #
    def list_all_hits(self):
        result = []
        paginator = self.client.get_paginator('list_hits')
        pages = paginator.paginate(PaginationConfig={'PageSize': 100})
        for page in pages:
            result += page['HITs']
        return result

    def list_assignments_for_hit(self, hitid):
        result = []
        paginator = self.client.get_paginator('list_assignments_for_hit')
        pages = paginator.paginate(
            HITId=hitid,
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

    def list_assignments_for_hits(self, hit_ids):
        result = []
        for id in hit_ids:
            result += self.list_assignments_for_hit(id)
        return result

    def forcedelete_all_hits(self, retry=False):
        # TODO: fix, also cap retries at 10 instead of 2
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
            if(obj['HITStatus'] == 'Reviewable'):
                print("Deleteing HIT with ID:", obj['HITId'])
                self.delete_hit(obj['HITId'])
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
