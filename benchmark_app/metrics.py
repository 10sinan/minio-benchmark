import time
import queue

sonuc_kuyrugu = queue.Queue()

def kaydet(dosya_adi, sure, basarili):
    sonuc_kuyrugu.put({"dosya_adi": dosya_adi, "sure": sure, "basarili": basarili})

def tum_sonuclari_al():
    tum_sonuclar = []
    while not sonuc_kuyrugu.empty():
        tum_sonuclar.append(sonuc_kuyrugu.get())
    return tum_sonuclar