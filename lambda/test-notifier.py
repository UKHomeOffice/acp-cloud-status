import unittest
from notifier import Notifier
import json
from unittest import mock

with open('test_cases/no_resources.json') as json_file:
    no_resources_event = json.load(json_file)

with open('test_cases/resources_no_tags.json') as json_file:
    resources_no_tags_event = json.load(json_file)

with open('test_cases/resources_and_tags.json') as json_file:
    resources_and_tags_event = json.load(json_file)


class NotifierTestCase(unittest.TestCase):
    def setUp(self):
        self.notifier = Notifier(region='eu-west-2',
                                 account='123456789012',
                                 sns_topic_prefix='acp_health_status_')


class TestNotifierGetServices(NotifierTestCase):

    def test_resources_and_tags(self):
        services = self.notifier.get_services(resources_and_tags_event)
        self.assertTrue(services == ['test-service-1', 'test-service-2'])

    def test_no_resources(self):
        services = self.notifier.get_services(no_resources_event)
        self.assertTrue(services == [])

    @mock.patch('boto3.Session.client')
    def test_resources_no_tags(self, mock_client):

        mock_client().get_resources().return_value = {
           "PaginationToken": "",
           "ResourceTagMappingList": [
              {
                 "ResourceARN": "arn:aws:ec2:us-east-1:123456789012:instance/i-abcd1111",
                 "Tags": [
                    {
                       "Key": "Env",
                       "Value": "test"
                    },
                    {
                       "Key": "PROJECT-SERVICE",
                       "Value": "test-service-1"
                    }
                 ]
              }
           ],
           "ResponseMetadata": {
              "RequestId": "6fd99a75-73b9-4556-9f9c-2dea3b710fa9",
              "HTTPStatusCode": 200,
              "HTTPHeaders": {
                 "x-amzn-requestid": "6fd99a75-73b9-4556-9f9c-2dea3b710fa9",
                 "content-type": "application/x-amz-json-1.1",
                 "content-length": "371",
                 "date": "Wed, 03 Mar 2021 14:25:05 GMT"
              },
              "RetryAttempts": 0
           }
        }

        services = self.notifier.get_services(resources_no_tags_event)

        self.assertTrue(services == ['test-service-1'])



