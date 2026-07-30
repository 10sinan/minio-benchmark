import boto3

s3 = boto3.client(
    "s3",
    endpoint_url="http://localhost:9000",
    aws_access_key_id="minioadmin",
    aws_secret_access_key="minioadmin"
)

s3.create_bucket(Bucket="test-bucket")
with open("test.txt", "w") as f:
    f.write("merhaba minio")

s3.upload_file("test.txt", "test-bucket", "test.txt")
s3.download_file("test-bucket", "test.txt", "indirilen.txt")

print("başarılı!")