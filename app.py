import os
from os.path import join
from os.path import dirname

from aws_cdk import core
from dotenv import load_dotenv

from stacks.lambda_stack import LambdaStack
from stacks.common import StackProps


##############################
# Configuration
##############################

# 環境変数の読み込み
dotenv_path = join(dirname(__file__), "./.env")
load_dotenv(dotenv_path)


props = StackProps(
    account=os.getenv("ACCOUNT"),
    region=os.getenv("REGION"),
    system_name=os.getenv("SYSTEM_NAME"),
    service_name=os.getenv("SERVICE_NAME"),
    function_name=os.getenv("FUNCTION_NAME"),
)


##############################
# Deploy stacks
##############################

app = core.App()

LambdaStack(app, f"{props.service_name}-{props.function_name}-stack", props=props)

app.synth()
