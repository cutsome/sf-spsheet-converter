FROM public.ecr.aws/lambda/python:3.9
#
# パッケージインストール
#
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install --upgrade pip && \
  pip install -r requirements.txt
#
# ソースコードコピー
#
COPY app/ ${LAMBDA_TASK_ROOT}
#
# Lambda Handler 実行
#
CMD ["lambda.handler"]
