import os
import random

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


def generate_files(folder_path, file_count, file_size_min_mb, file_size_max_mb, chunk_size_mb=1):
    os.makedirs(folder_path, exist_ok=True)

    for i in range(file_count):
        boyut = random.uniform(file_size_min_mb, file_size_max_mb)
        dosya_adi = f"file_{i}.bin"
        yol = os.path.join(folder_path, dosya_adi)
        fake_data(yol, target_size_mb=boyut, chunk_size_mb=chunk_size_mb)
        print(f"Üretildi: {dosya_adi}, boyut: {boyut:.4f}MB")


if __name__ == "__main__":
    generate_files(
        folder_path="generated_files",
        file_count=10,
        file_size_min_mb=100,
        file_size_max_mb=500
    )