import os
import random

def fake_data(file_path, target_size_mb, chunk_size_mb):
    target_size_bytes = target_size_mb * 1024 * 1024
    chunk_size_bytes = chunk_size_mb * 1024 * 1024

    written_bytes = 0

    #Yazılan byte, hedeften azken bu döngüye devam et
    with open(file_path, "wb") as f:
        while written_bytes < target_size_bytes:
            remaining = target_size_bytes - written_bytes
            #100 105 manıtıgı
            current_chunk_size = min(chunk_size_bytes, remaining)

            chunk = os.urandom(current_chunk_size)
            f.write(chunk)

            written_bytes += current_chunk_size

    return written_bytes


if __name__ == "__main__":
    os.makedirs("generated_files", exist_ok=True)

    file_count = 10
    file_size_min_mb = 100
    file_size_max_mb = 500

    for i in range(file_count):
        boyut = random.randint(file_size_min_mb, file_size_max_mb)
        dosya_adi = f"file_{i}.bin"
        yol = os.path.join("generated_files", dosya_adi)
        result = fake_data(yol, target_size_mb=boyut, chunk_size_mb=1)
        print(f"Yazılan byte: {result}, konum: {yol}, boyut: {boyut}MB")