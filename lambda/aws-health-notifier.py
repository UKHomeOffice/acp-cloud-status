#!/usr/bin/env python
import json
import boto3

def get_ns(event):
    event['detail']

def main(event, context):
    print(type(event))
    print(event)
    print(context)
