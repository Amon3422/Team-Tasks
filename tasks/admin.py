from django.contrib import admin
from .models import Membership, Task, Team
# Register your models here.

admin.site.register(Membership)
admin.site.register(Task)
admin.site.register(Team)