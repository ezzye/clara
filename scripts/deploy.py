"""Deploy dedicated resources. No owner data or credentials are committed."""
import argparse,hashlib,json,time,zipfile
from pathlib import Path
import boto3
p=argparse.ArgumentParser();p.add_argument('--region',default='eu-west-1');p.add_argument('--stack',default='clara-private');p.add_argument('--owner-sub',default='');a=p.parse_args()
root=Path(__file__).resolve().parents[1];session=boto3.Session(region_name=a.region)
account=session.client('sts').get_caller_identity()['Account'];s3=session.client('s3');cf=session.client('cloudformation')
bucket=f'{a.stack}-code-{account}-{a.region}'
try:s3.head_bucket(Bucket=bucket)
except s3.exceptions.ClientError as e:
    if e.response['ResponseMetadata']['HTTPStatusCode']!=404:raise
    kwargs={'Bucket':bucket}
    if a.region!='us-east-1':kwargs['CreateBucketConfiguration']={'LocationConstraint':a.region}
    s3.create_bucket(**kwargs)
s3.put_public_access_block(Bucket=bucket,PublicAccessBlockConfiguration={'BlockPublicAcls':True,'IgnorePublicAcls':True,'BlockPublicPolicy':True,'RestrictPublicBuckets':True})
s3.put_bucket_encryption(Bucket=bucket,ServerSideEncryptionConfiguration={'Rules':[{'ApplyServerSideEncryptionByDefault':{'SSEAlgorithm':'AES256'}}]})
s3.put_bucket_policy(Bucket=bucket,Policy=json.dumps({'Version':'2012-10-17','Statement':[{'Effect':'Deny','Principal':'*','Action':'s3:*','Resource':[f'arn:aws:s3:::{bucket}',f'arn:aws:s3:::{bucket}/*'],'Condition':{'Bool':{'aws:SecureTransport':'false'}}}]}))
archive=root/'.build/clara.zip';sha=hashlib.sha256(archive.read_bytes()).hexdigest();key=f'releases/{sha}.zip';s3.upload_file(str(archive),bucket,key)
params=[{'ParameterKey':k,'ParameterValue':v} for k,v in {'CodeBucket':bucket,'CodeKey':key,'AuthPrefix':f'{a.stack}-{account}','OwnerSub':a.owner_sub}.items()]
kwargs=dict(StackName=a.stack,TemplateBody=(root/'infra/template.yaml').read_text(),Parameters=params,Capabilities=['CAPABILITY_IAM'])
try:existing_stack=cf.describe_stacks(StackName=a.stack)['Stacks'][0];exists=True
except cf.exceptions.ClientError as e:
    if 'does not exist' not in str(e):raise
    exists=False
if exists:
    existing_outputs={o['OutputKey']:o['OutputValue'] for o in existing_stack.get('Outputs',[])}
    fn=existing_outputs.get('FunctionName')
    actual_owner=session.client('lambda').get_function_configuration(FunctionName=fn).get('Environment',{}).get('Variables',{}).get('CLARA_OWNER_SUB','') if fn else ''
    if actual_owner and a.owner_sub and a.owner_sub!=actual_owner:raise SystemExit('Refusing to replace the configured owner')
    if actual_owner:
        for item in params:
            if item['ParameterKey']=='OwnerSub':item['ParameterValue']=actual_owner
    try:cf.update_stack(**kwargs)
    except cf.exceptions.ClientError as e:
        if 'No updates are to be performed' not in str(e):raise
else:cf.create_stack(**kwargs,EnableTerminationProtection=True)
print('Deployment submitted. Poll stack status before using the site.',flush=True)
