#!/usr/bin/env python
import boto3
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class Notifier:

    def __init__(self,
                 region,
                 account,
                 sns_topic_prefix):

        self.region = region
        self.account = account
        self.sns_topic_prefix = sns_topic_prefix

        self.session = boto3.Session(region_name=self.region)

    def get_services(self, event):

        services = []

        try:
            affected_entities = event['detail']['affectedEntities']
        except KeyError as e:
            logging.info(f"Cannot get services, {e} element missing from {event['detail']['eventArn']}")
            return services

        tags = {}

        tag_client = self.session.client('resourcegroupstaggingapi')

        for entity in affected_entities:
            if 'tags' in entity:
                tags = entity['tags']
            else:
                logging.error(f"'tags' not found for {entity['entityValue']} - searching manually")
                if entity['entityValue'][:4] == 'arn:':
                    resource_details = tag_client.get_resources(ResourceARNList=[entity['entityValue']])
                    if resource_details['ResourceTagMappingList']:
                        if resource_details['ResourceTagMappingList'][0]['Tags']:
                            tags = resource_details['ResourceTagMappingList'][0]['Tags']
                            logging.info(f"Found tags for {entity['entityValue']}: {tags}")
                        else:
                            logging.info(f"API returned no tags for {entity['entityValue']}")
                    else:
                        logging.info(f"Tagging API returned no resources for ARN {entity['entityValue']}")
                else:
                    logging.error(f"{entity['entityValue']} not in ARN format, skipping tag retrieval")

            if tags:
                logging.info(f"Found tags for {entity['entityValue']}: {tags}")

                project_service = ''

                if type(tags) is list:
                    for tag in tags:
                        if tag['Key'] == 'PROJECT-SERVICE':
                            project_service = tag['Value']
                    if not project_service:
                        logging.error(f"{entity['entityValue']} has no 'PROJECT-SERVICE' tag, found {tags}")
                if type(tags) is dict:
                    try:
                        project_service = tags['PROJECT-SERVICE']
                    except KeyError as e:
                        logging.error(f"{entity}['entityValue'] has no {e} tag, found {tags}")

                if project_service:
                    logging.info(f"Found service for {entity['entityValue']}: {project_service}")
                    services.append(project_service)

        return services

    def get_topics(self, sns_client, topics, next_token=''):

        topic_response = sns_client.list_topics(NextToken=next_token)

        if topic_response['Topics']:
            for topic in topic_response['Topics']:
                prefix_string = f"arn:aws:sns:{self.region}:{self.account}:{self.sns_topic_prefix}"
                prefix_length = len(prefix_string)
                if topic['TopicArn'][:prefix_length] == prefix_string:
                    logging.info(f"Found ACP Health topic: {topic['TopicArn']}")
                    topics[topic['TopicArn'][prefix_length:]] = topic['TopicArn']

        if 'NextToken' in topic_response:
            self.get_topics(sns_client, topics, topic_response['NextToken'])
        else:
            return topics

    def parse_topics(self, topics, project_service):

        if project_service in topics:
            return topics[project_service]
        else:
            logging.error(f"{project_service} not found - total SNS topics found: {[list(topics.keys())]}")

    def trigger_sns(self, topic_arn, sns_client, event):

        sns_client.publish(TopicArn=topic_arn,
                           Subject='ACP Cloud Health Alert',
                           Message=event)

    def process_event(self, event):

        affected_services = self.get_services(event)

        sns_client = self.session.client('sns')

        topics = {}

        all_health_topics = self.get_topics(sns_client, topics)

        if affected_services:
            for service in affected_services:
                topic_arn = self.parse_topics(all_health_topics, service)
                if topic_arn:
                    self.trigger_sns(topic_arn, sns_client, event)
        else:
            for topic_arn in all_health_topics.values():
                self.trigger_sns(topic_arn, sns_client, event)


def main(event):

    notifier = Notifier(region=os.environ['AWS_REGION'],
                        account=os.environ['AWS_ACCOUNT'],
                        sns_topic_prefix=os.environ['SNS_TOPIC_PREFIX'])

    notifier.process_event(event)
