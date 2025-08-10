from django.db import models
from django.contrib.auth.models import User

# O modelo `Account` representa uma conta bancária ou carteira
class Account(models.Model):
    # Relaciona a conta a um usuário
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Nome da conta (ex: "Conta Corrente", "Poupança")
    name = models.CharField(max_length=100)
    
    # Saldo atual da conta
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Nome do banco (opcional, para uma descrição mais completa)
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    
    # Status da conta (ativo/inativo)
    is_active = models.BooleanField(default=True)

    # Função que retorna o nome da conta como representação em string
    def __str__(self):
        return f"{self.name} - {self.user.username}"

    class Meta:
        verbose_name = "Conta"
        verbose_name_plural = "Contas"

# Tipos de transação (para definir se é uma receita ou despesa)
TRANSACTION_TYPES = (
    ('income', 'Receita'),
    ('expense', 'Despesa'),
)

# O modelo `Transaction` representa uma movimentação de dinheiro
class Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, null=True, blank=True)
    card = models.ForeignKey('Card', on_delete=models.CASCADE, null=True, blank=True)
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    
    description = models.CharField(max_length=255, blank=True)
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True, blank=True)
    
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Se a transação é para uma data futura
    is_future_payment = models.BooleanField(default=False)
    # Se a transação futura já foi paga
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.transaction_type} - {self.description} ({self.amount})"

    class Meta:
        verbose_name = "Transação"
        verbose_name_plural = "Transações"
        ordering = ['-date'] # Ordena as transações por data, da mais recente para a mais antiga

# O modelo `Category` representa uma categoria de transação
class Category(models.Model):
    # A categoria pode ser global (sem usuário) ou específica do usuário
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    
    # Novos campos para o ícone e a cor no dashboard
    icon_class = models.CharField(max_length=100, default='fi fi-rr-tags', help_text="Classe do ícone, ex: 'fi fi-rr-shopping-cart'")
    color_class = models.CharField(max_length=50, default='bg-blue-500', help_text="Classe da cor do ícone, ex: 'bg-blue-500'")

    def __str__(self):
        if self.user:
            return f"{self.name} ({self.user.username})"
        return self.name

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        unique_together = ('user', 'name')

# O modelo `Budget` representa um orçamento por categoria
class Budget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Orçamento de {self.amount} para {self.category.name} de {self.start_date} a {self.end_date}"

    class Meta:
        verbose_name = "Orçamento"
        verbose_name_plural = "Orçamentos"
        unique_together = ('user', 'category', 'start_date', 'end_date') # Garante que não hajam orçamentos duplicados

# O modelo `Goal` representa uma meta de poupança
class Goal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    target_amount = models.DecimalField(max_digits=10, decimal_places=2)
    current_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    due_date = models.DateField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"Meta: {self.name} - {self.current_amount}/{self.target_amount}"

    class Meta:
        verbose_name = "Meta"
        verbose_name_plural = "Metas"

# O modelo `Card` representa um cartão de crédito ou débito
class Card(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    brand = models.CharField(max_length=50)
    name_on_card = models.CharField(max_length=100)
    card_name = models.CharField(max_length=255, default='Meu Cartão')
    card_number_masked = models.CharField(max_length=16) # O número será salvo mascarado
    expiration_date = models.CharField(max_length=5) # Formato MM/YY
    limit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    def __str__(self):
        return f"Card de {self.name_on_card} - {self.user.username}"

    class Meta:
        verbose_name = "Cartão"
        verbose_name_plural = "Cartões"