from django.contrib import admin
from .models import Account, Transaction, Category, Budget, Goal

# Registra os modelos para que apareçam no painel de administração
admin.site.register(Account)
admin.site.register(Transaction)
admin.site.register(Category)
admin.site.register(Budget)
admin.site.register(Goal)