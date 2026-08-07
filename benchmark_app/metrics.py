import queue

sonuc_kuyrugu = queue.Queue()

def kuyrugu_temizle():
    with sonuc_kuyrugu.mutex:
        sonuc_kuyrugu.queue.clear()

def kaydet(dosya_adi, sure, basarili, islem_tipi, boyut_byte=None):
    sonuc_kuyrugu.put({
        "dosya_adi": dosya_adi,
        "sure": sure,
        "basarili": basarili,
        "islem_tipi": islem_tipi,
        "boyut_byte": boyut_byte,
    })

def tum_sonuclari_al():
    tum_sonuclar = []
    while not sonuc_kuyrugu.empty():
        tum_sonuclar.append(sonuc_kuyrugu.get())
    return tum_sonuclar