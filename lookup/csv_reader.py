from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import re
import csv
import sys
import yaml
import pprint
import collections

from ansible.plugins.lookup import LookupBase
from ansible.errors import AnsibleError, AnsibleParserError

class LookupModule(LookupBase):
    def run(self, terms, variables=None, csv_file=None, role=None, vpcp1=None, vpcp2=None):
        csv_data = []
        sgs_list = []
        with open(csv_file) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                csv_data.append(row)
            for i in csv_data:
                sgname = i["SECURITY GROUP NAME"]
                sgname = sgname.lower().title()
                sgname = re.sub(r"[^a-zA-Z0-9]", '', sgname)
                if i["INSTANCE ROLE TAG"].lower() == role.lower() and i["vpc_code"].lower() == vpcp1.lower():
                    sgs_list.append(vpcp1 + "-" + vpcp2 + "-SecurityGroup-" + sgname)
        return sgs_list