from ansible.module_utils._text import to_native
from ansible.module_utils.ec2 import HAS_BOTO3, boto3_tag_list_to_ansible_dict
from ansible.errors import AnsibleError
from botocore.exceptions import ClientError
from ansible.plugins.lookup import LookupBase
import json
import csv
import logging
import os
import re
import sys
import yaml

try:
    from botocore.exceptions import ClientError
    import botocore
    import boto3
except ImportError:
    pass  # will be captured by imported HAS_BOTO3

def _boto3_conn(region, credentials, service):
    if 'boto_profile' in credentials:
        boto_profile = credentials.pop('boto_profile')
    else:
        boto_profile = None

    try:
        connection = boto3.session.Session(profile_name=boto_profile).client(service, region, **credentials)
    except (botocore.exceptions.ProfileNotFound, botocore.exceptions.PartialCredentialsError):
        if boto_profile:
            try:
                connection = boto3.session.Session(profile_name=boto_profile).client(service, region)
            # FIXME: we should probably do better passing on of the error information
            except (botocore.exceptions.ProfileNotFound, botocore.exceptions.PartialCredentialsError):
                raise AnsibleError("Insufficient credentials found.")
        else:
            raise AnsibleError("Insufficient credentials found.")
    return connection

class LookupModule(LookupBase):
    def run(self, terms, variables=None, boto_profile=None, aws_profile=None,
            aws_secret_key=None, aws_access_key=None, aws_security_token=None, region=None,
            csv_file=None, lb_name=None, vpcp1=None, vpcp2=None):

        if not HAS_BOTO3:
            raise AnsibleError('botocore and boto3 are required for aws_ssm lookup.')

        credentials = {}
        if aws_profile:
            credentials['boto_profile'] = aws_profile
        else:
            credentials['boto_profile'] = boto_profile
        credentials['aws_secret_access_key'] = aws_secret_key
        credentials['aws_access_key_id'] = aws_access_key
        credentials['aws_session_token'] = aws_security_token

        lbclient = _boto3_conn(region, credentials, 'elbv2')
        ec2 = _boto3_conn(region, credentials, 'ec2')

        lb_facts = lbclient.describe_load_balancers(
            Names=[
                lb_name,
            ],
        ).get("LoadBalancers")[0]
        
        csv_data = []
        lb_sgs_list = []

        with open(csv_file) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                csv_data.append(row)
            for row in csv_data:
                if row["LOAD BALANCER NAME"] == lb_name:
                    if lb_facts.get('Type', '') == 'application' and vpcp1 in lb_facts.get('LoadBalancerName', ''):
                        sg_name = ec2.describe_security_groups(
                            Filters=[
                                {
                                    'tag-key': 'Name'
                                    'Values': [
                                        vpcp1 + '-' + vpcp2 + '-SecurityGroup-' + row["SECURITY GROUP NAME"]
                                    ]
                                }
                            ]
                        ).get("SecurityGroups")[0].get("GroupName")
                        lb_sgs_list.append(sg_name)
        return lb_sgs_list


        ###TAG NAME  NOT GROUP NAME###