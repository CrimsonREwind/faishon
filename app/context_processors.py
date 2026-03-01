# context_processors.py
# Makes the user's total fAishon coin balance available in every template
from django.db.models import Sum

def coin_balance(request):
    if request.user.is_authenticated:
        total = request.user.donations.aggregate(total=Sum('coins_earned'))['total'] or 0
        count = request.user.donations.count()
        return {'coin_balance': total, 'total_donations': count}
    return {'coin_balance': 0, 'total_donations': 0}

