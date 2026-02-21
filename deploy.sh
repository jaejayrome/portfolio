#!/bin/bash

login_namespace="axbuvxeq7udm/Default/jerome.goh.jg@gmail.com"
tag_namespace="axbuvxeq7udm"
image_name="portfolio"
image_tag="latest"
registry="sin.ocir.io"

full_image_path="${registry}/${tag_namespace}/${image_name}:${image_tag}"

source .env

echo "$OCI_AUTH_TOKEN" | docker login $registry \
  --username "$login_namespace" \
  --password-stdin

docker build -t portfolio .
echo "Image Built"

docker tag $image_name ${full_image_path}
echo "Image Tagged"

docker push ${full_image_path}
echo "Push to OCI"
