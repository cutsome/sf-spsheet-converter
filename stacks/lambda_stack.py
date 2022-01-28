import os

from aws_cdk import core
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_iam as iam
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets

from stacks.common import StackProps


class LambdaStack(core.Stack):

    def __init__(
        self,
        scope: core.Construct,
        construct_id: str,
        props: StackProps,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ###########################################
        # AWS ECR
        ###########################################

        # create docker repository
        repository_name = f"{props.system_name}/{props.service_name}/{props.function_name}"
        repo = ecr.Repository(
            self,
            id=f"{props.system_name}-{props.service_name}-{props.function_name}-repo",
            repository_name=repository_name,
        )

        # output repository uri
        core.CfnOutput(
            self,
            id=f"{props.function_name}-RepositoryURL",
            export_name=f"{props.function_name}-RepositoryUri",
            value=repo.repository_uri,
        )

        ###########################################
        # AWS IAM
        ###########################################

        # create execution role
        role = iam.Role(
            self,
            id=f"{props.system_name}-{props.function_name}-role",
            role_name=f"{props.system_name}-{props.function_name}-role",
            assumed_by=iam.ServicePrincipal(service="lambda.amazonaws.com")
        )
        role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole"
            )
        )
        role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonEC2ContainerRegistryFullAccess"
            )
        )

        ###########################################
        # AWS Lambda
        ###########################################

        # create lambda function
        repository_arn = repo.from_repository_arn(
            self,
            f"{props.system_name}-{props.service_name}-{props.function_name}-repo-arn",
            repository_arn=f"arn:aws:ecr:{props.region}:{props.account}:repository/{repository_name}",
        )
        role_arn = role.from_role_arn(
            self,
            id=f"{props.system_name}-{props.function_name}-role-arn",
            role_arn=role.role_arn,
        )
        function = lambda_.Function(
            self,
            f"{props.service_name}-{props.function_name}",
            code=lambda_.Code.from_ecr_image(
                repository=repository_arn,
                tag="latest",
            ),
            handler=lambda_.Handler.FROM_IMAGE,
            runtime=lambda_.Runtime.FROM_IMAGE,
            role=role_arn,
            architecture=lambda_.Architecture.ARM_64,
            function_name=props.function_name,
            environment={
                "ACCOUNT": os.getenv("ACCOUNT", ""),
                "REGION": os.getenv("REGION", ""),
                "SYSTEM_NAME": os.getenv("SYSTEM_NAME", ""),
                "SERVICE_NAME": os.getenv("SERVICE_NAME", ""),
                "FUNCTION_NAME": os.getenv("FUNCTION_NAME", ""),
                "SP_KEY_1": os.getenv("SP_KEY_1", ""),
                "SP_KEY_2": os.getenv("SP_KEY_2", ""),
            },
            memory_size=2048,
            timeout=core.Duration.minutes(2),
        )

        ###########################################
        # AWS EventBridge
        ###########################################

        # create event bridge
        lambda_arn = function.from_function_arn(
            self,
            id=f"{props.service_name}-{props.function_name}-arn",
            function_arn=function.function_arn,
        )
        events.Rule(
            self,
            id=f"{props.service_name}-{props.function_name}-rule",
            rule_name=f"{props.service_name}-{props.function_name}-rule",
            # UTC
            schedule=events.Schedule.cron(
                minute="0",
                hour="0/6",
                day="*",
                month="*",
                year="*",
            ),
            targets=[targets.LambdaFunction(lambda_arn)],
        )
