'''
https://gist.github.com/darahayes/7f2d52ffc190929f14db79ee7d176ed8
'''

import boto3
import base64

from ansible.errors import AnsibleError

def __boto3_conn(region, credentials):
    if 'boto_profile' in credentials:
        boto_profile = credentials.pop('boto_profile')
    else:
        boto_profile = None
    try:
        connection = boto3.session.Session(profile_name=boto_profile).client('kms', region, **credentials)
    except (botocore.exceptions.ProfileNotFound, botocore.exceptions.PartialCredentialsError):
        if boto_profile:
            try:
                connection = boto3.session.Session(profile_name=boto_profile).client('kms', region)
            except (botocore.exceptions.ProfileNotFound, botocore.exceptions.PartialCredentialsError):
                raise AnsibleError("Insufficient credentials found.")
        else:
            raise AnsibleError("Insufficient credentials found.")
    return connection




def kms_decrypt(ciphertext, region=None, aws_profile=None, aws_secret_key=None, aws_access_key=None, aws_session_token=None):
    '''
    Decrypt a string using KMS
    '''
    credentials = {}
    if aws_secret_key and aws_access_key and aws_session_token:
        credentials['aws_secret_access_key'] = aws_secret_key
        credentials['aws_access_key_id'] = aws_access_key
        credentials['aws_session_token'] = aws_session_token
    elif aws_profile:
        credentials['boto_profile'] = aws_profile
    kms = __boto3_conn(region, credentials)
    return kms.decrypt(CiphertextBlob=base64.b64decode(ciphertext)).get('Plaintext')

def kms_encrypt(plaintext, key, region=None, aws_profile=None, aws_secret_key=None, aws_access_key=None, aws_session_token=None):
    '''
    Encrypt a string using KMS
    '''
    credentials = {}
    if aws_secret_key and aws_access_key and aws_session_token:
        credentials['aws_secret_access_key'] = aws_secret_key
        credentials['aws_access_key_id'] = aws_access_key
        credentials['aws_session_token'] = aws_session_token
    elif aws_profile:
        credentials['boto_profile'] = aws_profile
    kms = __boto3_conn(region, credentials)
    return base64.b64encode(kms.encrypt(KeyId=key,Plaintext=plaintext).get('CiphertextBlob'))

class FilterModule(object): 
    '''
    AWS KMS Filter
    '''
    def filters(self):
        return { 
            'kms_encrypt': kms_encrypt, 
            'kms_decrypt': kms_decrypt
        } 