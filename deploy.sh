# read .env
ENV=$(cat .env | grep -v '#' | xargs)
export $ENV


# configuragion
WORK_DIR=$(cd $(dirname $0); pwd)
IMAGE_VER="latest"
ECR_REGISTRY="$ACCOUNT.dkr.ecr.$REGION.amazonaws.com"
ECR_REPOSITORY="$SYSTEM_NAME/$SERVICE_NAME/$FUNCTION_NAME"


# ecr push
cd $WORK_DIR
aws ecr get-login-password --region ap-northeast-1 | docker login --username AWS --password-stdin $ECR_REGISTRY
docker build . -t $ECR_REGISTRY/$ECR_REPOSITORY:v1.0.0 -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_VER
docker push $ECR_REGISTRY/$ECR_REPOSITORY:v1.0.0
docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_VER


# lambda deploy
aws lambda update-function-code --function-name $FUNCTION_NAME --image-uri $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_VER
