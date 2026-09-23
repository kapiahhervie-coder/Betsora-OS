from django.contrib import admin

# Register your models here.


from .models import Zona, Lencana, SumberDigital, RefleksiSiswa, LencanaDiperoleh

admin.site.register(Zona)
admin.site.register(Lencana)
admin.site.register(SumberDigital)
admin.site.register(RefleksiSiswa)
admin.site.register(LencanaDiperoleh)
