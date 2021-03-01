#!/usr/bin/env python
import boto3
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

aws_region = os.environ['AWS_REGION']
aws_account = os.environ['AWS_ACCOUNT_ID']
sns_topic_prefix = os.environ['SNS_TOPIC_PREFIX']


def get_services(event, session):

    services = []

    try:
        affected_entities = event['detail']['affectedEntities']
    except KeyError as e:
        logging.error(f"Cannot get ns, {e} element missing from event")
        return services

    tags = {}

    tag_client = session.client('resourcegroupstaggingapi', region_name=os.environ['AWS_REGION'])

    for entity in affected_entities:
        try:
            tags = entity['tags']
            logging.info(f"Found tags for {entity}: {tags}")
        except KeyError as e:
            logging.error(f"{e} not found for {entity} - searching manually")
            if entity[:4]['entityValue'] == 'arn:':
                resource_details = tag_client.get_resources(ResourceARNList=[entity['entityValue']])
                tags = resource_details['ResourceTagMappingList'][0]['Tags']
                logging.info(f"Found tags for {entity}: {tags}")
            else:
                logging.error(f"{entity['entityValue']} not in ARN format, skipping tag retrieval")

        project_service = ''

        if type(tags) is list:
            for tag in tags:
                if tag['Key'] == 'PROJECT-SERVICE':
                    project_service = tag['Value']
            if not project_service:
                logging.error(f"{entity} has no 'PROJECT-SERVICE' tag, found {tags}")
        if type(tags) is dict:
            try:
                project_service = tags['PROJECT-SERVICE']
            except KeyError as e:
                logging.error(f"{entity} has no {e} tag, found {tags}")

        if project_service:
            logging.info(f"Found service for {entity}: {project_service}")
            services.append(project_service)

        return services


def get_topics(sns_client, topics, region, account, prefix, next_token=''):

    topic_response = sns_client.list_topics(NextToken=next_token)

    if topic_response['Topics']:
        for topic in topic_response['Topics']:
            prefix_string = f"arn:aws:sns:{region}:{account}:{prefix}"
            prefix_length = len(prefix_string)
            if topic['TopicArn'][:prefix_length] == prefix_string:
                logging.info(f"Found ACP Health topic: {topic['TopicArn']}")
                topics[topic['TopicArn'][prefix_length:]] = topic['TopicArn']

    if topic_response['NextToken']:
        get_topics(sns_client, topics, region, account, prefix, topic_response['NextToken'])
    else:
        return topics


def parse_services(topics, project_service):

    try:
        topic_arn = topics[project_service]
    except KeyError as e:
        message = f"{e} not found - total SNS topics found: {[list(topics.keys())]}"
        logging.error(message)
        return

    return topic_arn


def trigger_sns(topic, sns_client):

    sns_client.publish(TopicArn=topic)


def main(event, context):

    session = boto3.Session()

    affected_services = get_services(event, session)

    sns_client = session.client('sns', region_name=aws_region)

    topics = {}

    all_health_topics = get_topics(sns_client, topics, aws_region, aws_account, sns_topic_prefix)

    if affected_services:
        for service in affected_services:
            topic_arn = parse_services(all_health_topics, service)
            if topic_arn:
                trigger_sns(topic_arn, sns_client)
    else:
        for topic_arn in all_health_topics.values():
            trigger_sns(topic_arn, sns_client)
