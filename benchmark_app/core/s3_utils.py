import logging
import boto3
from boto3.session import Config


def s3_client_olustur(endpoint_url, access_key, secret_key):
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
            max_pool_connections=50,
        ),
    )


def baglanti_kontrolu(endpoint_url, access_key, secret_key, bucket_name):
    s3 = s3_client_olustur(endpoint_url, access_key, secret_key)
    s3.list_buckets()
    s3.head_bucket(Bucket=bucket_name)


def list_prefixes(bucket_name, endpoint, access_key, secret_key):
    try:
        s3 = s3_client_olustur(endpoint, access_key, secret_key)
        resp = s3.list_objects_v2(Bucket=bucket_name, Delimiter="/")
        prefixes = [p["Prefix"].rstrip("/") for p in resp.get("CommonPrefixes", [])]
        return prefixes
    except Exception as e:
        logging.debug("Prefix listelenemedi: %s", e)
        return []


def delete_prefix(bucket_name, prefix, endpoint, access_key, secret_key):
    try:
        s3 = s3_client_olustur(endpoint, access_key, secret_key)
        prefix_key = prefix if prefix.endswith("/") else f"{prefix}/"
        to_delete = []
        kwargs = {"Bucket": bucket_name, "Prefix": prefix_key}
        while True:
            resp = s3.list_objects_v2(**kwargs)
            for obj in resp.get("Contents", []):
                to_delete.append({"Key": obj["Key"]})
            if not resp.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = resp.get("NextContinuationToken")

        if to_delete:
            for item in to_delete:
                key = item["Key"]
                try:
                    s3.delete_object(Bucket=bucket_name, Key=key)
                    logging.info("Silindi: %s", key)
                except Exception:
                    logging.exception("Tek tek silme hatası: %s", key)
        return True
    except Exception as e:
        logging.exception("Prefix silme hatası: %s", e)
        return False
