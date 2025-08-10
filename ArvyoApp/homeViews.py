from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal
import json
from .models import Account, Transaction, Category, Card

# Importa o filtro personalizado 'get_item'
from django.template import Library
register = Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

# Views do Dashboard (Página Inicial)
@login_required
def index(request):
    user = request.user
    
    total_balance = sum(account.balance for account in Account.objects.filter(user=user, is_active=True))
    recent_transactions = Transaction.objects.filter(account__user=user).order_by('-date')[:5]

    today = timezone.localdate()
    start_of_month = today.replace(day=1)
    
    all_transactions_this_month = Transaction.objects.filter(
        account__user=user,
        date__gte=start_of_month
    )

    monthly_expenses = Decimal(0)
    monthly_income = Decimal(0)

    for transaction in all_transactions_this_month:
        if transaction.transaction_type == 'expense':
            monthly_expenses += transaction.amount
        elif transaction.transaction_type == 'income':
            monthly_income += transaction.amount
            
    total_change = monthly_income - monthly_expenses
    
    data = {
        'title': 'Painel',
        'subTitle': 'Bem-vindo à Gestão Financeira Arvyo',
        'total_balance': total_balance,
        'total_change': total_change,
        'monthly_expenses': monthly_expenses,
        'monthly_income': monthly_income,
        'recent_transactions': recent_transactions,
    }
    
    return render(request, "home/index.html", data)

# Views de Carteiras
@login_required
def wallets(request):
    user = request.user

    # Busca todas as contas e cartões do usuário separadamente
    user_accounts = Account.objects.filter(user=user)
    user_cards = Card.objects.filter(user=user)

    # Calculos de despesas e transações, adaptados para contas e cartões
    expenses_by_account = {}
    transactions_by_account = {}
    expenses_by_card = {}
    transactions_by_card = {}

    for account in user_accounts:
        transactions = Transaction.objects.filter(account=account, user=user).order_by('-date')
        total_expense = transactions.filter(transaction_type='expense').aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
        
        expenses_by_account[account.id] = total_expense
        transactions_by_account[account.id] = transactions
        
    for card in user_cards:
        transactions = Transaction.objects.filter(card=card, user=user).order_by('-date')
        total_expense = transactions.filter(transaction_type='expense').aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
        
        # Adiciona o limite disponível ao objeto do cartão
        card.available_limit = card.limit - total_expense
        
        expenses_by_card[card.id] = total_expense
        transactions_by_card[card.id] = transactions
    
    context = {
        'user_accounts': user_accounts,
        'user_cards': user_cards,
        'expenses_by_account': expenses_by_account,
        'transactions_by_account': transactions_by_account,
        'expenses_by_card': expenses_by_card,
        'transactions_by_card': transactions_by_card,
    }

    return render(request, 'home/wallets.html', context)

@login_required
def wallet_detail(request, wallet_type, pk):
    if wallet_type == 'account':
        wallet = get_object_or_404(Account, pk=pk, user=request.user)
        transactions = Transaction.objects.filter(account=wallet, user=request.user).order_by('-date')
    elif wallet_type == 'card':
        wallet = get_object_or_404(Card, pk=pk, user=request.user)
        transactions = Transaction.objects.filter(card=wallet, user=request.user).order_by('-date')
    else:
        # Se o tipo de carteira for inválido, redireciona de volta para a página de carteiras.
        return redirect('wallets')

    context = {'wallet': wallet, 'transactions': transactions, 'wallet_type': wallet_type}
    return render(request, 'home/wallet_detail.html', context)

def addBank(request):
    if request.method == 'POST':
        # Processa o formulário de adicionar conta bancária
        account_name = request.POST.get('account_name')
        bank_name = request.POST.get('bank_name')
        initial_balance = request.POST.get('initial_balance')

        # Converte o saldo inicial para Decimal
        try:
            initial_balance = Decimal(initial_balance)
        except (ValueError, TypeError):
            initial_balance = Decimal(0.00) # Define 0 como padrão em caso de erro

        # Cria uma nova conta
        Account.objects.create(
            user=request.user,
            name=account_name,
            bank_name=bank_name,
            balance=initial_balance,
            is_active=True
        )

        return redirect('bankAddSuccessful') # Redireciona para a página de sucesso
    
    # Se a requisição for GET, apenas renderiza a página do formulário
    data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}
    return render(request, "home/addBank.html", data)

@login_required
def settingsBank(request):
    user_accounts = Account.objects.filter(user=request.user)
    
    user_cards = Card.objects.filter(user=request.user) 
    
    data = {
        'user_accounts': user_accounts,
        'user_cards': user_cards,
    }
    
    return render(request, "home/settingsBank.html", data)

# A view addCard corrigida
def addCard(request):
    if request.method == 'POST':
        name_on_card = request.POST.get('name_on_card')
        card_name = request.POST.get('card_name')
        card_number_raw = request.POST.get('card_number_masked').replace(" ", "")
        brand = request.POST.get('brand')
        expiration_date = request.POST.get('expiration_date')
        
        # --- LINHA ADICIONADA/MODIFICADA ---
        limit_str = request.POST.get('limit') # Captura o valor do limite como string
        card_limit = Decimal(limit_str) if limit_str else Decimal('0.00') # Converte para Decimal
        # --- FIM DA LINHA ADICIONADA/MODIFICADA ---
        
        if len(card_number_raw) >= 8:
            first_four = card_number_raw[:4]
            last_four = card_number_raw[-4:]
            card_number_masked = f"{first_four}********{last_four}"
        else:
            card_number_masked = card_number_raw
        
        Card.objects.create(
            user=request.user,
            card_name=card_name,
            name_on_card=name_on_card,
            card_number_masked=card_number_masked,
            expiration_date=expiration_date,
            brand=brand,
            limit=card_limit # --- Adicionado o campo 'limit' aqui ---
        )
        return redirect('wallets')
    
    data = {'title': 'Add Card', 'subTitle': 'Adicionar Cartão'}
    return render(request, "home/addCard.html", data)

@login_required
def delete_bank_account(request, account_id):
    account = get_object_or_404(Account, id=account_id, user=request.user)
    account.delete()
    return redirect('settingsBank')

@login_required
def delete_credit_card(request, card_id):
    card = get_object_or_404(Card, id=card_id, user=request.user)
    card.delete()
    return redirect('settingsBank')

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.models import User

def signin(request):
    # Se o usuário já estiver logado, redireciona para a página inicial
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        email_or_username = request.POST.get('email')
        password = request.POST.get('password')

        # Tenta encontrar o usuário pelo email ou username
        try:
            user = User.objects.get(email=email_or_username)
            username = user.username
        except User.DoesNotExist:
            username = email_or_username

        # Usa a função de autenticação do Django
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Se o usuário for válido, ele é logado
            login(request, user)
            return redirect('index')
        else:
            # Se a autenticação falhar, exibe uma mensagem de erro
            messages.error(request, "Email/Usuário ou senha inválidos.")

    # Renderiza a página de login (para requisições GET ou falhas no POST)
    return render(request, "home/signin.html")

def index2(request): data = {'title': 'About Us', 'subTitle': 'About Us'}; return render(request,"home/index2.html", data)
def addNewAccount(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/addNewAccount.html", data)
def affiliates(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/affiliates.html", data)
def analytics(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/analytics.html", data)
def analyticsBalance(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/analyticsBalance.html", data)
def analyticsExpenses(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/analyticsExpenses.html", data)
def analyticsIncome(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/analyticsIncome.html", data)
def analyticsIncomeVsExpenses(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/analyticsIncomeVsExpenses.html", data)
def analyticsTransactionHistory(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/analyticsTransactionHistory.html", data)
def bankAddSuccessful(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/bankAddSuccessful.html", data)
def blank(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/blank.html", data)
def budgets(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/budgets.html", data)
def chart(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/chart.html", data)
def demo(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/demo.html", data)
def goals(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/goals.html", data)
def idFrontAndBackUpload(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/idFrontAndBackUpload.html", data)
def locked(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/locked.html", data)
def notifications(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/notifications.html", data)
def otpCode(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/otpCode.html", data)
def otpPhone(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/otpPhone.html", data)
def pageError(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/pageError.html", data)
def privacy(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/privacy.html", data)
def profile(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/profile.html", data)
def reset(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/reset.html", data)
def settings(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/settings.html", data)
def settingsApi(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/settingsApi.html", data)
def settingsCategories(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/settingsCategories.html", data)
def settingsCurrencies(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/settingsCurrencies.html", data)
def settingsGeneral(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/settingsGeneral.html", data)
def settingsProfile(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/settingsProfile.html", data)
def settingsSecurity(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/settingsSecurity.html", data)
def settingsSession(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/settingsSession.html", data)
def signup(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/signup.html", data)
def support(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/support.html", data)
def supportCreateTicket(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/supportCreateTicket.html", data)
def supportTicketDetails(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/supportTicketDetails.html", data)
def supportTickets(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/supportTickets.html", data)
def verifiedId(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/verifiedId.html", data)
def verifyEmail(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/verifyEmail.html", data)
def verifyId(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/verifyId.html", data)
def verifyingId(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/verifyingId.html", data)