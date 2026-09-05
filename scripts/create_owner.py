"""Create only the supplied owner, invite via Cognito, and pin immutable subject."""
import argparse,json
from pathlib import Path
import boto3
p=argparse.ArgumentParser();p.add_argument('--email',required=True);p.add_argument('--region',default='eu-west-1');p.add_argument('--stack',default='clara-private');a=p.parse_args()
s=boto3.Session(region_name=a.region);cf=s.client('cloudformation');cognito=s.client('cognito-idp');lam=s.client('lambda')
stack=cf.describe_stacks(StackName=a.stack)['Stacks'][0]
if stack['StackStatus'] not in ['CREATE_COMPLETE','UPDATE_COMPLETE']:raise SystemExit('Deployment is not ready')
outputs={o['OutputKey']:o['OutputValue'] for o in stack['Outputs']}
try:user=cognito.admin_get_user(UserPoolId=outputs['UserPoolId'],Username=a.email)
except cognito.exceptions.UserNotFoundException:
    response=cognito.admin_create_user(UserPoolId=outputs['UserPoolId'],Username=a.email,UserAttributes=[{'Name':'email','Value':a.email},{'Name':'email_verified','Value':'true'}],DesiredDeliveryMediums=['EMAIL'])
    user={'UserAttributes':response['User']['Attributes']}
sub=next(v['Value'] for v in user['UserAttributes'] if v['Name']=='sub')
env=lam.get_function_configuration(FunctionName=outputs['FunctionName'])['Environment']['Variables']
if env.get('CLARA_OWNER_SUB') and env['CLARA_OWNER_SUB']!=sub:raise SystemExit('Different owner already configured; refusing to replace')
env['CLARA_OWNER_SUB']=sub;lam.update_function_configuration(FunctionName=outputs['FunctionName'],Environment={'Variables':env})
root=Path(__file__).resolve().parents[1];private=root/'.private';private.mkdir(mode=0o700,exist_ok=True)
(private/'deployment.json').write_text(json.dumps({**outputs,'OwnerSub':sub,'Region':a.region,'Stack':a.stack},indent=2));(private/'deployment.json').chmod(0o600)
print('Owner created and immutable identity pinned. Cognito sends the initial sign-in invitation to the owner. MFA is required.')
print(outputs['SiteUrl'])
