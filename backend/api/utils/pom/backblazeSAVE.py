import boto3  
from botocore.exceptions import ClientError
from botocore.config import Config
from dotenv import load_dotenv  
import os
import sys

load_dotenv()

b2_key_id = os.getenv("B2_KEY_ID")
b2_app_key = os.getenv("B2_APP_KEY")
b2_bucket_name = "imgwebsite"


def get_b2_client(endpoint, keyID, applicationKey):
        b2_client = boto3.client(service_name='s3',
                                 endpoint_url=endpoint,                # Backblaze endpoint
                                 aws_access_key_id=keyID,              # Backblaze keyID
                                 aws_secret_access_key=applicationKey,
                                 config=Config(
                                     signature_version='s3v4'
                                 )
        )
        return b2_client

def list_buckets(b2_client, raw_object=False):
    try:
        my_buckets_response = b2_client.list_buckets()

        print('\nBUCKETS')
        for bucket_object in my_buckets_response[ 'Buckets' ]:
            print(bucket_object[ 'Name' ])

        if raw_object:
            print('\nFULL RAW RESPONSE:')
            print(my_buckets_response)

    except ClientError as ce:
        print('error', ce)
def upload_file(bucket, directory, file, b2, b2path=None):
    file_path = directory + '/' + file
    remote_path = b2path
    if remote_path is None:
        remote_path = file
    try:
        response = b2.Bucket(bucket).upload_file(file_path, remote_path)
    except ClientError as ce:
        print('error', ce)

    return response

def upload_file_to_backblaze(local_file_path, remote_file_path):
    print(b2_key_id)
    print(b2_app_key)
    try:
        b2_client = get_b2_client(
            endpoint="https://s3.us-east-005.backblazeb2.com",
            keyID=b2_key_id,
            applicationKey=b2_app_key
        )
        b2_client.put_object(
            Bucket=b2_bucket_name,
            Key='hello.txt',
            Body='Hello, world!'
        )

        # Upload the file
        # b2_client.upload_file(
        #     Filename=local_file_path,
        #     Bucket=b2_bucket_name,
        #     Key=remote_file_path
        # )
        print(f"File {local_file_path} uploaded to Backblaze as {remote_file_path}")

    except ClientError as e:
        print(f"Failed to upload file: {e}")
