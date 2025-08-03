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
    
    user_accounts = Account.objects.filter(user=user).order_by('name')
    user_cards = Card.objects.filter(user=user).order_by('name_on_card')
    
    transactions_by_account = {}
    expenses_by_account = {}
    chart_data_by_account = {}
    
    today = timezone.localdate()
    month_start = today.replace(day=1)

    for account in user_accounts:
        transactions_by_account[account.id] = Transaction.objects.filter(account=account).order_by('-date')[:5]
        
        all_transactions_for_account_this_month = Transaction.objects.filter(
            account=account,
            date__gte=month_start
        )
        
        monthly_expenses_for_account = Decimal(0)
        total_transactions_sum = Decimal(0)
        
        for transaction in all_transactions_for_account_this_month:
            if transaction.transaction_type == 'expense':
                monthly_expenses_for_account += transaction.amount
                total_transactions_sum -= transaction.amount
            elif transaction.transaction_type == 'income':
                total_transactions_sum += transaction.amount

        expenses_by_account[account.id] = monthly_expenses_for_account
        
        transactions_this_month = Transaction.objects.filter(
            account=account,
            date__gte=month_start
        ).order_by('date')
        
        balance_before_month = account.balance - total_transactions_sum

        dates = []
        balances = []
        
        current_balance = balance_before_month

        dates.append(month_start.strftime('%d/%m'))
        balances.append(float(current_balance))

        for transaction in transactions_this_month:
            if transaction.transaction_type == 'expense':
                current_balance -= transaction.amount
            elif transaction.transaction_type == 'income':
                current_balance += transaction.amount
            dates.append(transaction.date.strftime('%d/%m'))
            balances.append(float(current_balance))
            
        chart_data_by_account[account.id] = {
            'labels': dates,
            'data': balances,
        }
    
    data = {
        'title': 'Carteiras',
        'user_accounts': user_accounts,
        'user_cards': user_cards,
        'transactions_by_account': transactions_by_account,
        'expenses_by_account': expenses_by_account,
        'chart_data_by_account': chart_data_by_account,
    }
    
    return render(request, "home/wallets.html", data)

@login_required
def wallet_detail(request, account_id):
    user = request.user
    account = get_object_or_404(Account, pk=account_id, user=user)
    transactions = Transaction.objects.filter(account=account).order_by('-date')
    
    data = {
        'title': 'Detalhes da Carteira',
        'account': account,
        'transactions': transactions,
    }
    
    return render(request, "home/wallet_detail.html", data)

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
        
        if len(card_number_raw) >= 8:
            first_four = card_number_raw[:4]
            last_four = card_number_raw[-4:]
            card_number_masked = f"{first_four}********{last_four}"
        else:
            card_number_masked = card_number_raw
        
        Card.objects.create(
            user=request.user,
            card_name=card_name, # Corrigido: o valor é passado para o modelo
            name_on_card=name_on_card,
            card_number_masked=card_number_masked,
            expiration_date=expiration_date,
            brand=brand
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
def signin(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/signin.html", data)
def signup(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/signup.html", data)
def support(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/support.html", data)
def supportCreateTicket(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/supportCreateTicket.html", data)
def supportTicketDetails(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/supportTicketDetails.html", data)
def supportTickets(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/supportTickets.html", data)
def verifiedId(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/verifiedId.html", data)
def verifyEmail(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/verifyEmail.html", data)
def verifyId(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/verifyId.html", data)
def verifyingId(request): data = {'title': 'Add Bank', 'subTitle': 'Add Bank'}; return render(request, "home/verifyingId.html", data)