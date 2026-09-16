from django.db import models
from django.db.models import Q
from accounts.models import User


class Percakapan(models.Model):
    peserta_1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='percakapan_sebagai_1')
    peserta_2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='percakapan_sebagai_2')
    dibuat_pada = models.DateTimeField(auto_now_add=True)
    diperbarui_pada = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-diperbarui_pada']
        unique_together = ('peserta_1', 'peserta_2')

    def __str__(self):
        return f'{self.peserta_1} & {self.peserta_2}'

    def lawan_bicara(self, user):
        return self.peserta_2 if self.peserta_1 == user else self.peserta_1

    def pesan_terakhir(self):
        return self.pesan.last()

    @staticmethod
    def get_or_create_antara(user_a, user_b):
        percakapan = Percakapan.objects.filter(
            Q(peserta_1=user_a, peserta_2=user_b) | Q(peserta_1=user_b, peserta_2=user_a)
        ).first()
        if percakapan:
            return percakapan
        return Percakapan.objects.create(peserta_1=user_a, peserta_2=user_b)


class PesanPribadi(models.Model):
    percakapan = models.ForeignKey(Percakapan, on_delete=models.CASCADE, related_name='pesan')
    pengirim = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pesan_terkirim')
    isi = models.TextField()
    dikirim_pada = models.DateTimeField(auto_now_add=True)
    sudah_dibaca = models.BooleanField(default=False)

    class Meta:
        ordering = ['dikirim_pada']

    def __str__(self):
        return f'{self.pengirim}: {self.isi[:30]}'
