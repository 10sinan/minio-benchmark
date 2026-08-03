import queue

sonuc_kuyrugu = queue.Queue()

def kaydet(dosya_adi, sure, basarili, islem_tipi):
    sonuc_kuyrugu.put({
        "dosya_adi": dosya_adi,
        "sure": sure,
        "basarili": basarili,
        "islem_tipi": islem_tipi
    })

def tum_sonuclari_al():
    tum_sonuclar = []
    while not sonuc_kuyrugu.empty():
        tum_sonuclar.append(sonuc_kuyrugu.get())
    return tum_sonuclar