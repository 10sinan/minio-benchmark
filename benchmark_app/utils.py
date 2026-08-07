import logging
import streamlit as st


def safe_rerun():
    rerun_fn = getattr(st, "experimental_rerun", None)
    if callable(rerun_fn):
        try:
            rerun_fn()
        except Exception:
            logging.exception("safe_rerun failed")


def format_bytes(num_bytes):
    try:
        mb = num_bytes / (1024 * 1024)
        return f"{mb:.4f}MB"
    except Exception:
        return str(num_bytes)
