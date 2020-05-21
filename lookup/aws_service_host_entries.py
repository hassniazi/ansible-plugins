from ansible.module_utils._text import to_native
from ansible.module_utils.ec2 import HAS_BOTO3, boto3_tag_list_to_ansible_dict
from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

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
            private_ip=None):

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
        instance_facts = ec2.describe_instances(
            Filters=[
                {'Name': 'private-ip-address', 'Values': [private_ip]}
            ]
        ).get('Reservations')[0].get('Instances')[0]
        az = instance_facts.get('Placement', {}).get('AvailabilityZone')
        vpc_id = instance_facts.get('VpcId')
        vpc_endpoints = ec2.describe_vpc_endpoints(
            Filters=[
                {'Name': 'vpc-id', 'Values': [vpc_id]}
            ]
        ).get('VpcEndpoints', [])
        eni_map = {}
        service_map = {}
        for service in vpc_endpoints:
            service_name = service.get('ServiceName', '')
            network_interface_ids = service.get('NetworkInterfaceIds', [])
            for ni in network_interface_ids:
                eni_map[ni] = service_name
        for interface_id in eni_map:
            eni_facts = ec2.describe_network_interfaces(
                Filters=[
                    {'Name': 'network-interface-id', 'Values': [interface_id]}
                ]
            ).get('NetworkInterfaces', [])[0]
            if eni_facts.get('AvailabilityZone') == az:
                eni_private_ip = eni_facts.get('PrivateIpAddress', 'UNDEFINED')
                backwards_service_name = eni_map[interface_id]
                service_name = '.'.join(reversed(backwards_service_name.split('.')))
                service_map[service_name] = eni_private_ip
        host_entries = []
        for service_name, private_ip in service_map.iteritems():
            host_entry = '{} {}'.format(private_ip, service_name)
            host_entries.append(host_entry)
        return host_entries
        