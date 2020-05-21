from ansible.module_utils._text import to_native
from ansible.module_utils.ec2 import HAS_BOTO3, boto3_tag_list_to_ansible_dict
from ansible.errors import AnsibleError
from botocore.exceptions import ClientError
from ansible.plugins.lookup import LookupBase
from time import sleep
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
            aws_secret_key=None, aws_access_key=None, aws_security_token=None, region=None, myvpc=None, mysubnet=None, myregion=None):

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
        ec2client = _boto3_conn(region, credentials, 'ec2')

        attempts = 4 #amount of retries
        while attempts > 0:
            try:
                #attempt the boto call here
                nat_facts = ec2client.describe_nat_gateways().get('NatGateways')
            except botocore.exceptions.ClientError:
                attempts -= 1
                sleep(2) #how long to wait between retries
                pass
            break
        
        myNAT = myvpc + '-' + mysubnet + '-' + myregion + '-NAT'        
        for nat in nat_facts:
            raw_tags = nat.get('Tags')
            tags = { tag['Key']: tag['Value'] for tag in raw_tags }
            if tags.get('Name', '') == myNAT:
                nat_ip = nat.get('NatGatewayAddresses')[0].get('PrivateIp', '')
        return [nat_ip]

