import os
import random
import logging
import shutil

def fake_data(file_path, target_size_mb, chunk_size_mb):
    target_size_bytes = int(target_size_mb * 1024 * 1024)
    chunk_size_bytes = int(chunk_size_mb * 1024 * 1024)

    written_bytes = 0

    with open(file_path, "wb") as f:
        while written_bytes < target_size_bytes:
            remaining = target_size_bytes - written_bytes
            current_chunk_size = min(chunk_size_bytes, remaining)

            chunk = os.urandom(current_chunk_size)
            f.write(chunk)

            written_bytes += current_chunk_size

    return written_bytes


def generate_files(
    folder_path,
    file_count=None,
    file_size_min_mb=None,
    file_size_max_mb=None,
    chunk_size_mb=1,
    matrix_ayarlari=None,
):
    os.makedirs(folder_path, exist_ok=True)

    # Clear existing contents of the target folder so repeated runs don't accumulate files
    try:
        for name in os.listdir(folder_path):
            path = os.path.join(folder_path, name)
            if os.path.islink(path) or os.path.isfile(path):
                try:
                    os.remove(path)
                except Exception as e:
                    logging.warning("Failed to remove file %s: %s", path, e)
            elif os.path.isdir(path):
                try:
                    shutil.rmtree(path)
                except Exception as e:
                    logging.warning("Failed to remove dir %s: %s", path, e)
    except Exception as e:
        logging.warning("Failed to list/clear directory %s: %s", folder_path, e)

    file_idx = 0

    if matrix_ayarlari:
        # Matrix mode
        for group_idx, ayar in enumerate(matrix_ayarlari):
            count = ayar.get("count", 0)
            min_mb = ayar.get("min_mb", 1)
            max_mb = ayar.get("max_mb", 1)
            for _ in range(count):
                boyut = random.uniform(min_mb, max_mb)
                dosya_adi = f"file_{file_idx}.bin"
                yol = os.path.join(folder_path, dosya_adi)
                fake_data(yol, target_size_mb=boyut, chunk_size_mb=chunk_size_mb)
                logging.info("Üretildi: %s (Grup %d), boyut: %.4fMB", dosya_adi, group_idx, boyut)
                file_idx += 1
    else:
        # Standard mode
        for _ in range(file_count or 0):
            boyut = random.uniform(file_size_min_mb, file_size_max_mb)
            dosya_adi = f"file_{file_idx}.bin"
            yol = os.path.join(folder_path, dosya_adi)
            fake_data(yol, target_size_mb=boyut, chunk_size_mb=chunk_size_mb)
            logging.info("Üretildi: %s, boyut: %.4fMB", dosya_adi, boyut)
            file_idx += 1


if __name__ == "__main__":
    generate_files(
        folder_path="generated_files",
        file_count=10,
        file_size_min_mb=100,
        file_size_max_mb=500
    )