"""
core/__init__.py — S3 işlemleri ve temel yardımcılar paketi.
"""
from core.uploader import upload_files
from core.downloader import download_files
from core.deleter import benchmark_delete
from core.generator import generate_files
from core.s3_utils import baglanti_kontrolu, list_prefixes, delete_prefix
from core.metadata_ops import benchmark_list_objects, benchmark_head_object
