from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = '''
lookup: aws_ssm
author:
  - Rory McHugh <rory.mchugh-cic-uk(at)uk.ibm.com>
requirements:
  - ansible (needless to say)
  - boto3
  - botocore
short_description: Lookup the next computer name based on some arguments.
description:
  - Required parameters for this to work are
    - region
    - aws_profile
    - custom_computer_code
    - os_type
  - Returns a single string with a consistent computer name format e.g. SSVC-R-008
'''

EXAMPLES = '''
computer_name: "{{ lookup('computer_name', region=vars['region'], aws_profile=vars['profile'], custom_computer_code=vars['product'], os_type=vars['os'] ) }}"
'''

from ansible.module_utils._text import to_native
from ansible.module_utils.ec2 import HAS_BOTO3, boto3_tag_list_to_ansible_dict
from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()

try:
    from botocore.exceptions import ClientError
    import botocore
    import boto3
except ImportError:
    pass  # will be captured by imported HAS_BOTO3


def _boto3_conn(region, credentials):
    if 'boto_profile' in credentials:
        boto_profile = credentials.pop('boto_profile')
    else:
        boto_profile = None

    try:
        connection = boto3.session.Session(profile_name=boto_profile).client('ec2', region, **credentials)
        #connection = boto3.setup_default_session(profile_name=boto_profile).client('ec2', region, **credentials)
    except (botocore.exceptions.ProfileNotFound, botocore.exceptions.PartialCredentialsError):
        if boto_profile:
            try:
                connection = boto3.session.Session(profile_name=boto_profile).client('ec2', region)
            # FIXME: we should probably do better passing on of the error information
            except (botocore.exceptions.ProfileNotFound, botocore.exceptions.PartialCredentialsError):
                raise AnsibleError("Insufficient credentials found.")
        else:
            raise AnsibleError("Insufficient credentials found.")
    return connection


class LookupModule(LookupBase):
    def run(self, terms, variables=None, boto_profile=None, aws_profile=None,
            aws_secret_key=None, aws_access_key=None, aws_security_token=None, region=None,
            custom_computer_code=None, os_type=None, asg_name=None):
        '''
            :arg terms: a list of lookups to run.
                e.g. ['parameter_name', 'parameter_name_too' ]
            :kwarg variables: ansible variables active at the time of the lookup
            :kwarg aws_secret_key: identity of the AWS key to use
            :kwarg aws_access_key: AWS seret key (matching identity)
            :kwarg aws_security_token: AWS session key if using STS
            :returns: A single string
        '''

        if not HAS_BOTO3:
            raise AnsibleError('botocore and boto3 are required for aws_ssm lookup.')

        ret = []
        credentials = {}
        if aws_profile:
            credentials['boto_profile'] = aws_profile
        else:
            credentials['boto_profile'] = boto_profile
        credentials['aws_secret_access_key'] = aws_secret_key
        credentials['aws_access_key_id'] = aws_access_key
        credentials['aws_session_token'] = aws_security_token

        ec2 = _boto3_conn(region, credentials)
        
        filter_string = '{}-{}-*'.format(custom_computer_code.upper(), os_type[:1].upper())

        reservations = ec2.describe_instances(
            Filters=[
                {'Name': 'tag:ComputerName', 'Values': [filter_string]},
                {'Name': 'instance-state-name','Values': ['running','pending'] },
                {'Name': 'tag:aws:autoscaling:groupName','Values':[asg_name]}
            ]
        ).get('Reservations')
        computer_numbers =[]
        for res in reservations:
            instances = res.get('Instances')
            if len(instances) != 1: 
                raise AnsibleError('Unexpected number of instances found')
            else:
                raw_tags = instances[0].get('Tags')
                tags = { tag['Key']: tag['Value'] for tag in raw_tags }
                computer_name = tags.get('ComputerName', '')
                computer_name_split = computer_name.split('-')
                computer_number = int(computer_name_split[len(computer_name_split)-1])
                computer_numbers.append(computer_number)
    
        computer_numbers.sort()
        number_string = '01'
        if len(computer_numbers) > 0:
            set_numbers = set(computer_numbers)
            set_full_range = set([1,2,3])
            set_diff = set_full_range - set_numbers
            try:
                num = min(set_diff)
            except ValueError:
                raise AnsibleError('Too many instances')
            number_string = format(num, '02')
        computer_name = '{}-{}-{}'.format(custom_computer_code.upper(), os_type[:1].upper(), number_string)
        ret.append(computer_name)
        return ret

