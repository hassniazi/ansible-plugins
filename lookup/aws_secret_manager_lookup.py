# -*- coding: utf-8 -*-

from ansible.module_utils._text import to_native
from ansible.module_utils.ec2 import HAS_BOTO3, boto3_tag_list_to_ansible_dict
from ansible.errors import AnsibleError
from botocore.exceptions import ClientError
from ansible.plugins.lookup import LookupBase
import json

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
        connection = boto3.session.Session(profile_name=boto_profile).client('secretsmanager', region, **credentials)
    except (botocore.exceptions.ProfileNotFound, botocore.exceptions.PartialCredentialsError):
        if boto_profile:
            try:
                connection = boto3.session.Session(profile_name=boto_profile).client('secretsmanager', region)
            # FIXME: we should probably do better passing on of the error information
            except (botocore.exceptions.ProfileNotFound, botocore.exceptions.PartialCredentialsError):
                raise AnsibleError("Insufficient credentials found.")
        else:
            raise AnsibleError("Insufficient credentials found.")
    return connection

class LookupModule(LookupBase):

    def run(self, terms, variables=None, boto_profile=None, aws_profile=None,
            aws_secret_key=None, aws_access_key=None, aws_security_token=None, region=None,
            secret_name=None):

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

        client = _boto3_conn(region, credentials)
        

    # In this sample we only handle the specific exceptions for the 'GetSecretValue' API.
    # See https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
    # We rethrow the exception by default.

        try:
            get_secret_value_response = client.get_secret_value(
                SecretId=secret_name
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'DecryptionFailureException':
                # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
                # Deal with the exception here, and/or rethrow at your discretion.
                raise AnsibleError("Secrets Manager can't decrypt the protected secret text using the provided KMS key")
                #raise e
            elif e.response['Error']['Code'] == 'InternalServiceErrorException':
                # An error occurred on the server side.
                # Deal with the exception here, and/or rethrow at your discretion.
                raise AnsibleError("An error occurred on the server side")
                #raise e
            elif e.response['Error']['Code'] == 'InvalidParameterException':
                # You provided an invalid value for a parameter.
                # Deal with the exception here, and/or rethrow at your discretion.
                raise AnsibleError("You provided an invalid value for a parameter")
                #raise e
            elif e.response['Error']['Code'] == 'InvalidRequestException':
                # You provided a parameter value that is not valid for the current state of the resource.
                # Deal with the exception here, and/or rethrow at your discretion.
                raise AnsibleError("You provided a parameter value that is not valid for the current state of the resource")
                #raise e
            elif e.response['Error']['Code'] == 'ResourceNotFoundException':
                # We can't find the resource that you asked for.
                # Deal with the exception here, and/or rethrow at your discretion.
                raise AnsibleError("the secret does not exist")
                #raise e
        
        secret_string = get_secret_value_response.get('SecretString')
        if secret_string:
            try:
                secret_dict = json.loads(secret_string)
                if len(secret_dict.values()) == 1:
                    return [secret_dict.values()[0]]
                else:
                    raise AnsibleError('Unexpected value {} returned.'.format(secret_dict.values()))
            except ValueError:
                return [secret_string]
        else:
            raise AnsibleError('Secret not found.')

    